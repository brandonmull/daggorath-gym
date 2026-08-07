"""Unit tests for daggorath_gym.state — no MAME needed.

Tests validate behavior through the schema rather than against hardcoded
counts or byte positions. The schema (FIELDS) is the single source of
truth. When fields are added, removed, or reordered, the schema changes
and the tests adapt — they only fail if the schema is internally
inconsistent.

Growth plan:
    - As new RAM addresses are discovered in the disassembly, add fields
      to FIELDS. The round-trip and consistency tests will validate them
      without any test changes.
    - When per-field bounds (min/max) are known, add them to the schema
      and test that round-trip values stay within those bounds.
    - The to_array test ensures the RL agent's observation interface
      stays synchronized with whatever shape FIELDS defines.
"""

import numpy as np
import pytest

from daggorath_gym.state import FIELDS, FRAME_LEN, DaggorathState


# ---- helpers ---------------------------------------------------------------

def _build_test_frame() -> bytes:
    """Build a valid frame where each field gets its field-index as value.

    The frame is constructed from FIELDS itself — no hardcoded positions.
    """
    frame = bytearray(FRAME_LEN)
    for field_index, (_name, offset, width) in enumerate(FIELDS):
        if width == 1:
            frame[offset] = field_index & 0xFF
        else:
            frame[offset] = field_index & 0xFF
            frame[offset + 1] = (field_index >> 8) & 0xFF
    return bytes(frame)


# ---- schema consistency ----------------------------------------------------

def test_frame_length_matches_schema():
    """FRAME_LEN equals the sum of all field widths."""
    expected = sum(width for _, _, width in FIELDS)
    assert FRAME_LEN == expected


def test_offsets_are_contiguous():
    """Every field starts exactly where the previous field ended."""
    position = 0
    for name, offset, width in FIELDS:
        assert offset == position, f"expected {name} at offset {position}, got {offset}"
        position += width
    assert position == FRAME_LEN


# ---- deserialization -------------------------------------------------------

def test_round_trip():
    """Every field in the schema survives a round trip through DaggorathState."""
    data = _build_test_frame()
    state = DaggorathState(data)
    for field_index, (name, _offset, _width) in enumerate(FIELDS):
        assert getattr(state, name) == field_index


def test_rejects_wrong_length():
    """DaggorathState raises ValueError for data that does not match FRAME_LEN."""
    with pytest.raises(ValueError):
        DaggorathState(b"short")

    with pytest.raises(ValueError):
        DaggorathState(bytes(FRAME_LEN + 1))


def test_strips_single_trailing_newline():
    """A frame ending with a single newline is accepted (newline-delimited wire format)."""
    data = _build_test_frame() + b"\n"
    state = DaggorathState(data)
    assert state.game_mode == 0  # first field gets index 0


# ---- agent interface -------------------------------------------------------

def test_to_array():
    """to_array returns a uint16 numpy array whose shape matches the schema."""
    state = DaggorathState(_build_test_frame())
    arr = state.to_array()
    assert isinstance(arr, np.ndarray)
    assert len(arr) == len(FIELDS)
    assert arr.dtype == np.uint16