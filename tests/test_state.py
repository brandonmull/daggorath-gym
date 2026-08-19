"""Unit tests for daggorath_gym.state — no MAME needed.

Tests validate behavior through the schema rather than against hardcoded
counts or byte positions. The schema (FIELDS) is the single source of
truth. When fields are added, removed, or reordered, the schema changes
and the tests adapt — they only fail if the schema is internally
inconsistent.
"""

import numpy as np
import pytest

from daggorath_gym.state import (
    CREATURE_BYTES,
    CREATURE_FIELDS,
    CREATURE_SLOTS,
    FIELDS,
    FLOOR_OBJECT_CAPACITY,
    FLOOR_OBJECT_RAW_BYTES,
    FRAME_LEN,
    HAND_COUNT,
    HANDS_BYTES,
    MAP_SIZE,
    MAZE_BYTES,
    OBJECT_RAW_BYTES,
    OBJECTS_BYTES,
    PACK_BYTES,
    PACK_CAPACITY,
    DaggorathState,
    decode_creatures,
    decode_maze,
    decode_objects,
)


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


# ---- world-channel decoding -------------------------------------------------

def test_decode_maze_shape_and_orientation():
    """decode_maze yields a (32, 32) grid, row-major with cell (X, Y) at [y][x]."""
    payload = bytearray(MAZE_BYTES)
    payload[3 * MAP_SIZE + 7] = 0xAB  # cell (X=7, Y=3)
    maze = decode_maze(bytes(payload))
    assert maze.shape == (MAP_SIZE, MAP_SIZE)
    assert maze[3][7] == 0xAB


def test_decode_creatures_shape_and_order():
    """decode_creatures yields a (32, 4) array in alive/type/X/Y order."""
    payload = bytearray(CREATURE_BYTES)
    payload[0] = 0xFF  # slot 0 alive
    payload[1] = 0x0B  # slot 0 type (Wizard)
    payload[2] = 12    # slot 0 X
    payload[3] = 34    # slot 0 Y
    creatures = decode_creatures(bytes(payload))
    assert creatures.shape == (CREATURE_SLOTS, CREATURE_FIELDS)
    assert creatures[0][0] == 0xFF
    assert creatures[0][1] == 0x0B
    assert creatures[0][2] == 12
    assert creatures[0][3] == 34


def test_decode_objects_shapes():
    """decode_objects yields hands (2, 3), pack (8, 3), and floor (8, 5)."""
    hands, pack, floor_objects = decode_objects(bytes(OBJECTS_BYTES))
    assert hands.shape == (HAND_COUNT, OBJECT_RAW_BYTES)
    assert pack.shape == (PACK_CAPACITY, OBJECT_RAW_BYTES)
    assert floor_objects.shape == (FLOOR_OBJECT_CAPACITY, FLOOR_OBJECT_RAW_BYTES)


def test_decode_objects_layout():
    """decode_objects splits the record into hands, pack, and floor correctly."""
    payload = bytearray(OBJECTS_BYTES)
    floor_start = HANDS_BYTES + PACK_BYTES
    payload[floor_start] = 0x04  # first floor entry's class (SWORD)
    payload[floor_start + 3] = 9  # X
    payload[floor_start + 4] = 5  # Y
    _hands, _pack, floor_objects = decode_objects(bytes(payload))
    assert floor_objects[0][0] == 0x04
    assert floor_objects[0][3] == 9
    assert floor_objects[0][4] == 5


def test_world_channels_are_none_when_absent():
    """A state without world records reports None for every world channel."""
    state = DaggorathState(_build_test_frame())
    assert state.maze is None
    assert state.creatures is None
    assert state.hands is None
    assert state.pack is None
    assert state.objects is None


def test_world_channels_decode_when_present():
    """A state built from world records exposes the decoded true state."""
    state = DaggorathState(
        _build_test_frame(),
        maze=bytes(MAZE_BYTES),
        creatures=bytes(CREATURE_BYTES),
        objects=bytes(OBJECTS_BYTES),
    )
    assert state.maze.shape == (MAP_SIZE, MAP_SIZE)
    assert state.creatures.shape == (CREATURE_SLOTS, CREATURE_FIELDS)
    assert state.hands.shape == (HAND_COUNT, OBJECT_RAW_BYTES)
    assert state.pack.shape == (PACK_CAPACITY, OBJECT_RAW_BYTES)
    assert state.objects.shape == (FLOOR_OBJECT_CAPACITY, FLOOR_OBJECT_RAW_BYTES)