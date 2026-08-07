"""Integration tests for MameOperator — requires a running MAME instance.

These tests validate the state pipeline end-to-end: MAME boots, Lua
reads RAM and sends raw bytes, Python deserializes into DaggorathState.

Prerequisites:
    - MAME installed and on PATH
    - ROMs present at emulation/roms/
    - Hash files present at emulation/hash/

Growth plan:
    - Currently tests the state channel only (MAME → Python).
    - When readiness detection is implemented, add assertions that the
      first frame occurs after the game transitions from demo to live.
    - When command execution detection is implemented, add a round-trip:
      send a command → observe the resulting state change.
"""

import os
import sys
import importlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force-reload to bypass stale editable-install cache
import daggorath_gym
importlib.reload(daggorath_gym)
from daggorath_gym.emulator import MameOperator, SocketConfig
from daggorath_gym.state import FIELDS, DaggorathState

# Each test gets its own port range to avoid collisions.
_SOCKET = SocketConfig(state_port=15100, command_port=15101)


def test_operator_starts_and_stops():
    """MameOperator can start, receive a state frame, and stop cleanly."""
    operator = MameOperator(socket_config=_SOCKET)
    try:
        operator.start()
        state = operator.recv()
        assert isinstance(state, DaggorathState)
    finally:
        operator.stop()


def test_state_has_valid_values():
    """Received state fields fall within sensible ranges for a booted game."""
    operator = MameOperator(socket_config=_SOCKET)
    try:
        operator.start()
        state = operator.recv()

        # Game mode: demo (0xFF) or live (0x00) — both are valid at startup
        assert state.game_mode in (0x00, 0xFF)

        # Dungeon floor: 0–4 per the memory map
        assert 0 <= state.at_floor <= 4
    finally:
        operator.stop()


def test_state_to_array_shape():
    """to_array() produces a schema-consistent output from real MAME data."""
    operator = MameOperator(socket_config=_SOCKET)
    try:
        operator.start()
        state = operator.recv()
        arr = state.to_array()

        assert isinstance(arr, np.ndarray)
        assert len(arr) == len(FIELDS)
        assert arr.dtype == np.uint16
    finally:
        operator.stop()