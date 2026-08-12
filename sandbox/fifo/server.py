#!/usr/bin/env python3
"""FIFO (named pipe) IPC server — bypasses MAME's emu.file socket layer.

Creates two named pipes:
- /tmp/daggorath-fifo-state  — Lua writes game state, Python reads it
- /tmp/daggorath-fifo-command — Python writes commands, Lua reads them

Usage:
    python sandbox/fifo/server.py
"""

import os
import subprocess
import sys
import time

STATE_FIFO = "/tmp/daggorath-fifo-state"
COMMAND_FIFO = "/tmp/daggorath-fifo-command"


def _remove_stale(path: str) -> None:
    if os.path.exists(path):
        os.unlink(path)


def run() -> None:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Clean up and create FIFOs
    for path in [STATE_FIFO, COMMAND_FIFO]:
        _remove_stale(path)
        os.mkfifo(path)
    print(f"FIFOs created: {STATE_FIFO}, {COMMAND_FIFO}")

    # Open both with O_RDWR so MAME's Lua io.open() calls never block.
    # Python reads from state_fd and writes to command_fd.
    state_fd = os.open(STATE_FIFO, os.O_RDWR)
    print(f"State FIFO opened (fd={state_fd})")

    command_fd = os.open(COMMAND_FIFO, os.O_RDWR)
    print(f"Command FIFO opened (fd={command_fd})")

    # Launch MAME
    autoboot_script = os.path.join(root, "sandbox", "fifo", "client.lua")
    mame_cmd = [
        "mame", "coco3", "daggorath",
        "-rompath", os.path.join(root, "emulation", "roms"),
        "-hashpath", os.path.join(root, "emulation", "hash"),
        "-autoboot_script", autoboot_script,
        "-cfg_directory", os.path.join(root, ".mame"),
        "-skip_gameinfo",
        "-nonvram_save",
        "-window",
        "-sound", "none",
    ]
    env = os.environ.copy()
    env["STATE_FIFO"] = STATE_FIFO
    env["COMMAND_FIFO"] = COMMAND_FIFO

    print(f"Launching MAME: {' '.join(mame_cmd)}")
    mame_process = subprocess.Popen(mame_cmd, env=env)

    try:
        leftover = b""
        count = 0

        while True:
            if mame_process.poll() is not None:
                print(f"\nMAME exited with code {mame_process.returncode}")
                # Drain remaining state data
                try:
                    remaining = os.read(state_fd, 4096)
                    if remaining:
                        leftover += remaining
                        while b"\n" in leftover:
                            line, leftover = leftover.split(b"\n", 1)
                            if line.strip():
                                count += 1
                                print(f"[{count}] {line.decode('utf-8', errors='replace')}")
                except OSError:
                    pass
                break

            try:
                chunk = os.read(state_fd, 4096)
            except OSError:
                time.sleep(0.01)
                continue

            if not chunk:
                time.sleep(0.01)
                continue

            leftover += chunk

            while b"\n" in leftover:
                line, leftover = leftover.split(b"\n", 1)
                if not line.strip():
                    continue

                count += 1
                print(f"[{count}] {line.decode('utf-8', errors='replace')}")

                # Echo a command back every 2 messages
                if count % 2 == 0:
                    cmd = b'{"action":"ATTACK"}\n'
                    try:
                        os.write(command_fd, cmd)
                        print(f"    -> Sent: ATTACK")
                    except OSError as exc:
                        print(f"    -> Write error: {exc}")

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        os.close(state_fd)
        os.close(command_fd)
        _remove_stale(STATE_FIFO)
        _remove_stale(COMMAND_FIFO)

        if mame_process.poll() is None:
            print("Terminating MAME...")
            mame_process.terminate()
            try:
                mame_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                mame_process.kill()
                mame_process.wait()

        print("Cleanup complete. Goodbye.")


if __name__ == "__main__":
    run()