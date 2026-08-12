#!/usr/bin/env python3
"""Unix domain socket server that launches MAME and tests UDS support.

Creates two UDS endpoints:
- /tmp/daggorath-uds-state  — receives data from Lua (emu.file("w"))
- /tmp/daggorath-uds-action — sends data to Lua (emu.file("r"))

Usage:
    python sandbox/uds/server.py
"""

import json
import os
import socket
import subprocess
import sys

STATE_PATH = "/tmp/daggorath-uds-state"
ACTION_PATH = "/tmp/daggorath-uds-action"
TIMEOUT = 30


def _remove_stale(path: str) -> None:
    """Remove a stale UDS file if it exists."""
    if os.path.exists(path):
        os.unlink(path)


def run() -> None:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    emulation_dir = os.path.join(root, "sandbox", "uds")

    # Clean up any stale socket files from previous runs
    _remove_stale(STATE_PATH)
    _remove_stale(ACTION_PATH)

    # Bind state UDS
    state_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        state_socket.bind(STATE_PATH)
    except OSError as exc:
        print(f"ERROR: Could not bind state UDS {STATE_PATH} — {exc}", file=sys.stderr)
        sys.exit(1)
    state_socket.listen(1)
    print(f"State server listening on {STATE_PATH}")

    # Bind action UDS
    action_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        action_socket.bind(ACTION_PATH)
    except OSError as exc:
        print(f"ERROR: Could not bind action UDS {ACTION_PATH} — {exc}", file=sys.stderr)
        sys.exit(1)
    action_socket.listen(1)
    print(f"Action server listening on {ACTION_PATH}")

    # Launch MAME as a CLIENT connecting to our UDS endpoints
    autoboot_script = os.path.join(emulation_dir, "client.lua")
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
    print(f"Launching MAME: {' '.join(mame_cmd)}")
    mame_process = subprocess.Popen(mame_cmd)

    state_connection = None
    action_connection = None

    try:
        print("Waiting for MAME Lua state connection (UDS)...")
        state_connection, _ = state_socket.accept()
        print("State connected via UDS")

        print("Waiting for MAME Lua action connection (UDS)...")
        action_connection, _ = action_socket.accept()
        print("Action connected via UDS\n")

        leftover = b""
        count = 0

        while True:
            try:
                chunk = state_connection.recv(4096)
            except ConnectionResetError:
                print("\nState connection lost (reset).")
                break

            if not chunk:
                print("\nState connection lost (EOF).")
                break

            leftover += chunk

            while b"\n" in leftover:
                line, leftover = leftover.split(b"\n", 1)
                if not line.strip():
                    continue

                count += 1
                print(f"[{count}] {line.decode('utf-8')}")

                if count % 2 == 0 and action_connection:
                    cmd = json.dumps({"action": "ATTACK"}) + "\n"
                    try:
                        action_connection.sendall(cmd.encode("utf-8"))
                        print(f"    -> Sent: {cmd.strip()}")
                    except OSError:
                        pass

    except socket.timeout:
        print(f"\nTIMEOUT: No client connected within {TIMEOUT} seconds.", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nShutting down (Ctrl+C)...")
    finally:
        for connection in (state_connection, action_connection):
            if connection:
                connection.close()
        state_socket.close()
        action_socket.close()
        _remove_stale(STATE_PATH)
        _remove_stale(ACTION_PATH)

        if mame_process.poll() is None:
            print("Terminating MAME...")
            mame_process.terminate()
            try:
                mame_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                mame_process.kill()
                mame_process.wait()

        print("Sockets closed. Goodbye.")


if __name__ == "__main__":
    run()