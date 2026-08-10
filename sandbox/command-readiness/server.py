#!/usr/bin/env python3
"""Launches MAME with the command-readiness plugin and reads log.txt after 30 seconds."""

import os
import subprocess
import sys
import time
from pathlib import Path

DURATION = 30

script_dir = Path(__file__).resolve().parent
sandbox_dir = script_dir.parent
project_root = sandbox_dir.parent
rom_path = project_root / "emulation" / "roms"
hash_path = project_root / "emulation" / "hash"
scratch_dir = project_root / ".mame"
log_file = script_dir / "log.txt"

scratch_dir.mkdir(exist_ok=True)

mame_cmd = [
    "mame", "coco3", "daggorath",
    "-rompath", str(rom_path),
    "-hashpath", str(hash_path),
    "-pluginspath", f"{sandbox_dir};C:/Emulators/Mame/plugins",
    "-plugin", "command-readiness",
    "-cfg_directory", str(scratch_dir),
    "-skip_gameinfo",
    "-nonvram_save",
    "-window",
    "-sound", "none",
]

env = os.environ.copy()
env["LOG_FILE"] = str(log_file)

print("Launching MAME...", file=sys.stderr)
mame_process = subprocess.Popen(
    mame_cmd,
    cwd=str(project_root / "emulation"),
    env=env,
    stdout=None,
    stderr=None,
)

print(f"Waiting {DURATION}s...", file=sys.stderr)
try:
    time.sleep(DURATION)
except KeyboardInterrupt:
    print("\nInterrupted.", file=sys.stderr)

if mame_process.poll() is None:
    print("Terminating MAME...", file=sys.stderr)
    mame_process.terminate()
    try:
        mame_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        mame_process.kill()
        mame_process.wait()

if log_file.exists():
    content = log_file.read_text()
    lines = content.splitlines()
    print(f"\n=== {log_file} ({len(lines)} lines) ===", file=sys.stderr)
    for line in lines[:10]:
        print(f"  {line}", file=sys.stderr)
    if len(lines) > 20:
        print(f"  ...", file=sys.stderr)
        for line in lines[-5:]:
            print(f"  {line}", file=sys.stderr)
else:
    print(f"\nNo log file at {log_file}", file=sys.stderr)

print("Done.", file=sys.stderr)