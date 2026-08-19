#!/usr/bin/env python3
"""Launch MAME with the state-field-verification plugin and check its log.

The plugin pokes known values into RAM; the production state sampler writes
tagged records to a log file. This script decodes those records with the
production deserializer and asserts the poked values round-trip correctly.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

DURATION = 30
PIXEL_BYTES = 1024

script_dir = Path(__file__).resolve().parent
sandbox_dir = script_dir.parent
project_root = sandbox_dir.parent
rom_path = project_root / "emulation" / "roms"
hash_path = project_root / "emulation" / "hash"
plugins_path = project_root / "emulation" / "plugins"
scratch_dir = project_root / ".mame"
log_file = script_dir / "log.txt"

scratch_dir.mkdir(exist_ok=True)

mame_cmd = [
    "mame", "coco3", "daggorath",
    "-rompath", str(rom_path),
    "-hashpath", str(hash_path),
    "-pluginspath", f"{sandbox_dir};/usr/local/share/games/mame/plugins",
    "-plugin", "state-field-verification",
    "-cfg_directory", str(scratch_dir),
    "-skip_gameinfo",
    "-nonvram_save",
    "-window",
    "-sound", "none",
]

env = os.environ.copy()
env["LOG_FILE"] = str(log_file)
env["DAGGORATH_PLUGINS_DIR"] = str(plugins_path)

print("Launching MAME...", file=sys.stderr)
mame_process = subprocess.Popen(
    mame_cmd,
    cwd=str(project_root / "emulation"),
    env=env,
    stdout=None,
    stderr=None,
)

print(f"Waiting {DURATION}s...", file=sys.stderr)
time.sleep(DURATION)

if mame_process.poll() is None:
    print("Terminating MAME...", file=sys.stderr)
    mame_process.terminate()
    try:
        mame_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        mame_process.kill()
        mame_process.wait()

# ---- analysis -------------------------------------------------------------

sys.path.insert(0, str(project_root))
from daggorath_gym.state import DaggorathState, FRAME_LEN

RECORD_LENGTHS = {
    ord("S"): 1 + FRAME_LEN,
    ord("T"): 1 + 1 + PIXEL_BYTES,
    ord("B"): 1 + FRAME_LEN + 1 + PIXEL_BYTES,
}

EXPECTED = {
    "torch_minutes": 100,
    "torch_physical_light": 7,
    "torch_magic_light": 3,
    "ambient_light": 0x0102,
    "m0221": 0x000A,
}


def decode_records(data):
    records = []
    i = 0
    while i < len(data):
        tag = data[i]
        length = RECORD_LENGTHS.get(tag)
        if length is None:
            i += 1
            continue
        if i + length > len(data):
            break
        record = data[i:i + length]
        if tag in (ord("S"), ord("B")):
            records.append(DaggorathState(record[1:1 + FRAME_LEN]))
        i += length
    return records


def main():
    if not log_file.exists():
        print(f"FAIL: no log file at {log_file}", file=sys.stderr)
        return 1

    records = decode_records(log_file.read_bytes())
    print(f"Decoded {len(records)} state records", file=sys.stderr)

    observed = {name: set() for name in EXPECTED}
    for state in records:
        for name in EXPECTED:
            observed[name].add(getattr(state, name))

    failures = []
    for name, want in EXPECTED.items():
        if want in observed[name]:
            print(f"PASS  {name} == {want}")
        else:
            preview = sorted(observed[name])[:8]
            print(f"FAIL  {name}: expected {want}, saw {preview}...")
            failures.append(name)

    if failures:
        print(f"\nRESULT: FAIL ({len(failures)} field(s) not observed)")
        return 1
    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
