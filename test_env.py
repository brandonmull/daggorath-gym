#!/usr/bin/env python3
"""Continuous DaggorathEnv test — runs many steps so you can watch it work."""

import os, sys, importlib, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import daggorath_gym
importlib.reload(daggorath_gym)
from daggorath_gym.env import DaggorathEnv

STEPS = 30

env = DaggorathEnv()
print("[env] Reset...", flush=True)
obs, info = env.reset()
print(f"[env] Obs: {obs}\n", flush=True)

for i in range(STEPS):
    action = i % 4
    obs, reward, term, trunc, info = env.step(action)
    print(f"[{i+1:2d}/{STEPS}] action={action}  obs={obs}  reward={reward:.2f}", flush=True)

env.close()
print("\n[env] Done", flush=True)