"""Integration tests for DaggorathEnv — requires a running MAME instance.

Tests the Gymnasium environment interface: start/reset, observation shape,
and clean shutdown. Step is blocked until reward/termination are designed.

Prerequisites:
    - MAME installed and on PATH
    - ROMs present at emulation/roms/
    - Hash files present at emulation/hash/

Growth plan:
    - When readiness detection is implemented, assert that reset() returns
      a live-game observation (game_mode == 0x00).
    - When reward is designed, add step() tests: send command, receive
      observation, verify reward/terminated/truncated behavior.
    - When truncation is designed, add time-limit tests.
"""

import os
import sys
import importlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force-reload to bypass stale editable-install cache
import daggorath_gym
importlib.reload(daggorath_gym)
from daggorath_gym.emulator import IpcConfig
from daggorath_gym.environment import DaggorathEnv
from daggorath_gym.state import FIELDS

_IPC = IpcConfig(state_fifo_path="/tmp/daggorath-test-env", command_port=15201)


def test_reset_returns_valid_observation():
    """reset() produces a uint16 observation array matching the state schema."""
    env = DaggorathEnv(ipc_config=_IPC)
    try:
        observation, info = env.reset()

        assert isinstance(observation, np.ndarray)
        assert observation.dtype == np.uint16
        assert len(observation) == len(FIELDS)
    finally:
        env.close()


def test_close_cleans_up():
    """close() shuts down the emulator without error."""
    env = DaggorathEnv(ipc_config=_IPC)
    env.reset()
    env.close()


# step() is blocked until reward and termination are designed.
# Both _compute_reward and _check_terminated raise NotImplementedError.
# When those are implemented, add tests here for the full step cycle.