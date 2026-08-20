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
from gymnasium import spaces

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force-reload to bypass stale editable-install cache
import daggorath_gym
importlib.reload(daggorath_gym)
from daggorath_gym.commands import NUM_OBJECT_SPECIFIERS, NUM_TEMPLATES
from daggorath_gym.emulator import IpcConfig
from daggorath_gym.environment import DaggorathEnv
from daggorath_gym.state import FIELDS

_IPC = IpcConfig(state_fifo_path="/tmp/daggorath-test-env", command_port=15201)
_IPC_CONTRACT = IpcConfig(
    state_fifo_path="/tmp/daggorath-test-env-contract", command_port=15203
)


def test_reset_returns_valid_observation():
    """reset() produces the perceived-state Dict with self-fields in scalars."""
    env = DaggorathEnv(ipc_config=_IPC)
    try:
        observation, info = env.reset()

        assert isinstance(observation, dict)
        assert observation["scalars"].dtype == np.uint16
        assert len(observation["scalars"]) == len(FIELDS)
    finally:
        env.close()


def test_close_cleans_up():
    """close() shuts down the emulator without error."""
    env = DaggorathEnv(ipc_config=_IPC)
    env.reset()
    env.close()


def test_gymnasium_consumer_contract():
    """The Gymnasium surface a consumer touches before training is coherent.

    Mirrors the metadata a stable-baselines3-style client inspects before
    calling learn(): action/observation space shape and dtype, an in-range
    sampled action, and reset() returning an observation that the space
    accepts. Keeps step() untested — reward/termination are NotImplemented.
    """
    env = DaggorathEnv(ipc_config=_IPC_CONTRACT)
    try:
        # ---------- action space ----------
        assert isinstance(env.action_space, spaces.MultiDiscrete)
        assert env.action_space.nvec.tolist() == [NUM_TEMPLATES, NUM_OBJECT_SPECIFIERS]

        action = env.action_space.sample()
        assert action.shape == (2,)
        assert 0 <= int(action[0]) < NUM_TEMPLATES
        assert 0 <= int(action[1]) < NUM_OBJECT_SPECIFIERS

        # ---------- observation space ----------
        assert isinstance(env.observation_space, spaces.Dict)
        assert env.observation_space["scalars"].shape == (len(FIELDS),)
        assert env.observation_space["scalars"].dtype == np.uint16

        # ---------- reset ----------
        observation, info = env.reset()
        assert isinstance(observation, dict)
        assert env.observation_space.contains(observation)
        assert isinstance(info, dict)
    finally:
        env.close()


# step() is blocked until reward and termination are designed.
# Both _compute_reward and _check_terminated raise NotImplementedError.
# When those are implemented, add tests here for the full step cycle.