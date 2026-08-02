#!/usr/bin/env python3
"""TCP server that launches MAME and communicates via two sockets.

- Port 15000: receives game state from Lua (emu.file("w"))
- Port 15001: sends action commands to Lua (emu.file("r"))

No dependency on the gym module — fully standalone.

Usage:
    python sandbox/server.py
"""

import json
import os
import socket
import subprocess
import sys

HOST = "127.0.0.1"
STATE_PORT = 15000
ACTION_PORT = 15001
TIMEOUT = 30


def run() -> None:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rompath = os.path.join(root, "emulation", "roms")
    hashpath = os.path.join(root, "emulation", "hash")
    autoboot_script = os.path.join(root, "sandbox", "client.lua")

    # Bind state socket (port 15000)
    state_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    state_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        state_sock.bind((HOST, STATE_PORT))
    except OSError as exc:
        print(f"ERROR: Could not bind state port {STATE_PORT} — {exc}", file=sys.stderr)
        sys.exit(1)
    state_sock.listen(1)
    print(f"State server listening on {HOST}:{STATE_PORT}")

    # Bind action socket (port 15001)
    action_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    action_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        action_sock.bind((HOST, ACTION_PORT))
    except OSError as exc:
        print(f"ERROR: Could not bind action port {ACTION_PORT} — {exc}", file=sys.stderr)
        sys.exit(1)
    action_sock.listen(1)
    print(f"Action server listening on {HOST}:{ACTION_PORT}")

    # Launch MAME
    mame_cmd = [
        "mame", "coco3", "daggorath",
        "-rompath", rompath,
        "-hashpath", hashpath,
        "-autoboot_script", autoboot_script,
        "-cfg_directory", os.path.join(root, ".venv", "mame-cfg"),
        "-skip_gameinfo",
        "-nonvram_save",
        "-window",
        "-sound", "sdl",
    ]
    print(f"Launching MAME: {' '.join(mame_cmd)}")
    mame_process = subprocess.Popen(mame_cmd)

    state_conn = None
    action_conn = None

    try:
        print("Waiting for MAME Lua state connection...")
        state_conn, addr = state_sock.accept()
        print(f"State connected from {addr[0]}:{addr[1]}")

        print("Waiting for MAME Lua action connection...")
        action_conn, addr2 = action_sock.accept()
        print(f"Action connected from {addr2[0]}:{addr2[1]}\n")

        leftover = b""
        count = 0

        while True:
            try:
                chunk = state_conn.recv(4096)
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

                # Send an action command back after each message
                if count % 2 == 0 and action_conn:
                    cmd = json.dumps({"action": "ATTACK"}) + "\n"
                    try:
                        action_conn.sendall(cmd.encode("utf-8"))
                        print(f"    -> Sent: {cmd.strip()}")
                    except OSError:
                        pass

    except socket.timeout:
        print(f"\nTIMEOUT: No client connected within {TIMEOUT} seconds.", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nShutting down (Ctrl+C)...")
    finally:
        if state_conn:
            state_conn.close()
        if action_conn:
            action_conn.close()
        state_sock.close()
        action_sock.close()

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