#!/usr/bin/env python3
"""Test MameBridge with daggorath_gym (uses default emulation/autoboot.lua)."""

import os, sys, importlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force-reload to bypass stale editable-install cache
import daggorath_gym
importlib.reload(daggorath_gym)
from daggorath_gym import MameBridge

print("[test] Starting bridge...", flush=True)
bridge = MameBridge(timeout=30)
bridge.start()
print("[test] CONNECTED!", flush=True)

msg = bridge.recv()
print(f"[test] MSG: {msg}", flush=True)

bridge.close()
print("[test] DONE", flush=True)