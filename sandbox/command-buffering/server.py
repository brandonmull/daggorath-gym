#!/usr/bin/env python3
"""Command buffering sandbox: flood Daggorath's input buffer and observe
head/tail positions to measure drain rate and overflow behavior.

Usage: python sandbox/command-buffering/server.py
"""
import os
import socket
import subprocess
import sys

HOST = "127.0.0.1"
PORT = 15000
SANDBOX_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(SANDBOX_DIR))
EMU_DIR = os.path.join(ROOT, "emulation")
CFG_DIR = os.path.join(ROOT, ".venv", "mame-cfg")


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)
    server.settimeout(120)

    env = os.environ.copy()
    env["AUTOBOOT_DIR"] = EMU_DIR

    print("Launching MAME...")
    mame = subprocess.Popen([
        "mame", "coco3", "daggorath",
        "-rompath", os.path.join(ROOT, "emulation", "roms"),
        "-hashpath", os.path.join(ROOT, "emulation", "hash"),
        "-autoboot_script", os.path.join(SANDBOX_DIR, "autoboot.lua"),
        "-autoboot_delay", "1",
        "-cfg_directory", CFG_DIR,
        "-skip_gameinfo", "-nonvram_save",
        "-window", "-sound", "none",
    ], env=env)

    exit_code = 1
    try:
        conn, addr = server.accept()
        print(f"Connected ({addr})\n")
        print(f"{'Frame':>6} | {'Head':>5} | {'Tail':>5} | {'Fill':>5} | {'Match':>6} | Event")
        print("-" * 70)

        buf = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                text = line.decode().strip()
                if not text:
                    continue

                if text.startswith("READY"):
                    print(f"{'':>6} | {'':>5} | {'':>5} | {'':>5} | {'':>6} | Sandbox ready")
                elif text.startswith("PRIME:"):
                    _, frame = text.split(":")
                    print(f"{int(frame):>6} | {'':>5} | {'':>5} | {'':>5} | {'':>6} | Priming buffer")
                elif text.startswith("LIVE:"):
                    parts = text[5:].split(",")
                    frame = int(parts[0])
                    head = int(parts[1].split("=")[1])
                    tail = int(parts[2].split("=")[1])
                    fill = (tail - head) % 256
                    print(f"{frame:>6} | {head:>5} | {tail:>5} | {fill:>5} | {'':>6} | Live — starting flood")
                elif text.startswith("FLOOD_END:"):
                    parts = text[10:].split(",")
                    frame = int(parts[0])
                    posted = int(parts[1].split("=")[1])
                    head = int(parts[2].split("=")[1])
                    tail = int(parts[3].split("=")[1])
                    fill = (tail - head) % 256
                    print(f"{frame:>6} | {head:>5} | {tail:>5} | {fill:>5} | {'':>6} | Flood done: {posted} commands posted")
                elif text.startswith("BUF:"):
                    parts = text[4:].split(",")
                    frame = int(parts[0])
                    head = int(parts[1].split("=")[1])
                    tail = int(parts[2].split("=")[1])
                    fill = int(parts[3].split("=")[1])
                    match = int(parts[4].split("=")[1])
                    print(f"{frame:>6} | {head:>5} | {tail:>5} | {fill:>5} | {match:>6} |")
                elif text.startswith("DONE:"):
                    parts = text[5:].split(",")
                    frame = int(parts[0])
                    head = int(parts[1].split("=")[1])
                    tail = int(parts[2].split("=")[1])
                    fill = (tail - head) % 256
                    print(f"{frame:>6} | {head:>5} | {tail:>5} | {fill:>5} | {'':>6} | Done — final state")
                    exit_code = 0
                    break
                else:
                    print(f"{'':>6} | {'':>5} | {'':>5} | {'':>5} | {'':>6} | {text}")

        if exit_code != 0:
            print("\nNo DONE message received — MAME may have crashed or timed out")

    except socket.timeout:
        print("Timeout waiting for MAME connection")
    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        server.close()
        print("\nDone.")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())