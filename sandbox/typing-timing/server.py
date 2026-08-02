#!/usr/bin/env python3
"""Verify natkeyboard:post() works with the CoCo keyboard.
Usage: env/bin/python3 sandbox/typing-timing/server.py
"""
import os
import subprocess

SANDBOX_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(SANDBOX_DIR))
EMU_DIR = os.path.join(ROOT, "emulation")
CFG_DIR = os.path.join(ROOT, ".venv", "mame-cfg")

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
    "-skip_gameinfo",
    "-window",
], env=env)
