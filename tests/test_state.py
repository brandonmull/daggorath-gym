"""Unit tests for daggorath_gym.state — no MAME needed.

Tests validate behavior through the schema rather than against hardcoded
counts or byte positions. The schema (FIELDS) is the single source of
truth. When fields are added, removed, or reordered, the schema changes
and the tests adapt — they only fail if the schema is internally
inconsistent.
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


# ---- derived attributes ----------------------------------------------------

def test_heart_rate():
    """heart_rate is 60 / heart_beat_interval, and 0 when the interval is zero."""
    frame = bytearray(FRAME_LEN)

    # interval = 20 → 60 / 20 = 3.0 beats/sec
    for name, offset, width in FIELDS:
        frame[offset] = 0
    interval_offset = dict((n, o) for n, o, _ in FIELDS)["heart_beat_interval"]
    frame[interval_offset] = 20
    state = DaggorathState(bytes(frame))
    assert state.heart_rate == 3.0

    # interval = 0 → no active heart
    frame[interval_offset] = 0
    state = DaggorathState(bytes(frame))
    assert state.heart_rate == 0.0


def test_command_text_defaults_to_empty():
    """command_text defaults to an empty string when not provided."""
    state = DaggorathState(_build_test_frame())
    assert state.command_text == ""


def test_command_text_is_stored():
    """command_text carries the decoded command-area text when provided."""
    state = DaggorathState(_build_test_frame(), command_text="PULL LEFT TORCH")
    assert state.command_text == "PULL LEFT TORCH"


# ---- immutability ----------------------------------------------------------

def test_immutability():
    """DaggorathState rejects attribute assignment after construction."""
    state = DaggorathState(_build_test_frame())
    with pytest.raises(AttributeError):
        state.game_mode = 0


# ---- agent interface -------------------------------------------------------

def test_as_perceived():
    """as_perceived returns the perceived-state Dict with self-fields in scalars."""
    state = DaggorathState(_build_test_frame())
    perceived = state.as_perceived()
    assert isinstance(perceived, dict)
    assert perceived["scalars"].dtype == np.uint16
    assert len(perceived["scalars"]) == len(FIELDS)