#!/usr/bin/env python3
"""Test Lua module loading in MAME's embedded interpreter.

Usage:
    env/bin/python3 sandbox/lua-module-loading/server.py
"""

import os
import socket
import subprocess
import sys

HOST = "127.0.0.1"
PORT = 15000
SANDBOX_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(SANDBOX_DIR))


def run() -> int:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    server.settimeout(30)

    env = os.environ.copy()
    env["AUTOBOOT_DIR"] = SANDBOX_DIR

    mame = subprocess.Popen([
        "mame", "coco3", "daggorath",
        "-rompath", os.path.join(ROOT, "emulation", "roms"),
        "-hashpath", os.path.join(ROOT, "emulation", "hash"),
        "-autoboot_script", os.path.join(SANDBOX_DIR, "autoboot.lua"),
        "-cfg_directory", os.path.join(ROOT, ".venv", "mame-cfg"),
        "-skip_gameinfo", "-nonvram_save",
        "-window", "-sound", "none",
    ], env=env)

    try:
        conn, _ = server.accept()
        buf = b""
        while b"\n" not in buf:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
        conn.close()

        line = buf.decode().strip()
        if line == "PASS":
            print("PASS: require() works in MAME's Lua")
            return 0
        else:
            print(f"FAIL: {line}")
            return 1

    except socket.timeout:
        print("FAIL: MAME didn't connect within 30s")
        return 1
    finally:
        server.close()
        if mame.poll() is None:
            mame.terminate()
            mame.wait()


if __name__ == "__main__":
    sys.exit(run())