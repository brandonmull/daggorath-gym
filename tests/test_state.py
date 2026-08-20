"""Unit tests for daggorath_gym.state — no MAME needed.

Tests validate behavior through the schema rather than against hardcoded
counts or byte positions. The schema (FIELDS) is the single source of
truth. When fields are added, removed, or reordered, the schema changes
and the tests adapt — they only fail if the schema is internally
inconsistent.
"""

import numpy as np
import pytest

from daggorath_gym.navigation import (
    DIRECTION_NORTH,
    EDGE_MAGIC_DOOR,
    EDGE_NORMAL_DOOR,
    EDGE_OPEN,
    EDGE_WALL,
)

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
    HOLE_LADDER_CAPACITY,
    HOLE_LADDER_RAW_BYTES,
    HOLES_LADDERS_BYTES,
    MAP_SIZE,
    MAZE_BYTES,
    OBJECT_RAW_BYTES,
    OBJECTS_BYTES,
    PACK_BYTES,
    PACK_CAPACITY,
    _DISPLAY_EXAMINE,
    _DISPLAY_LOOK,
    DaggorathState,
    decode_creatures,
    decode_holes_ladders,
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


def test_command_rejected_false_by_default():
    """command_rejected is False when the command area shows no rejection."""
    assert DaggorathState(_build_test_frame()).command_rejected is False


def test_command_rejected_detects_reject_text():
    """command_rejected is True when the command area shows the game's '???'."""
    state = DaggorathState(_build_test_frame(), command_text="???")
    assert state.command_rejected is True


def test_command_rejected_false_for_normal_text():
    """command_rejected is False for an accepted command echo."""
    state = DaggorathState(_build_test_frame(), command_text="PULL LEFT TORCH")
    assert state.command_rejected is False


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


def test_decode_holes_ladders_shape_and_layout():
    """decode_holes_ladders yields a (2, 4, 3) array, ceiling then floor."""
    payload = bytearray(HOLES_LADDERS_BYTES)
    payload[0] = 0x01  # ceiling entry 0: ladder
    payload[1] = 0x00  # Y
    payload[2] = 0x17  # X
    payload[12] = 0x00  # floor entry 0: hole (byte 12 = ceiling list's 12 bytes)
    payload[13] = 0x0F
    payload[14] = 0x04
    holes_ladders = decode_holes_ladders(bytes(payload))
    assert holes_ladders.shape == (2, HOLE_LADDER_CAPACITY, HOLE_LADDER_RAW_BYTES)
    assert holes_ladders[0][0][0] == 0x01
    assert holes_ladders[0][0][1] == 0x00
    assert holes_ladders[0][0][2] == 0x17
    assert holes_ladders[1][0][0] == 0x00
    assert holes_ladders[1][0][1] == 0x0F
    assert holes_ladders[1][0][2] == 0x04


def test_world_channels_are_none_when_absent():
    """A state without world records reports None for every world channel."""
    state = DaggorathState(_build_test_frame())
    assert state.maze is None
    assert state.creatures is None
    assert state.hands is None
    assert state.pack is None
    assert state.objects is None
    assert state.holes_ladders is None


def test_world_channels_decode_when_present():
    """A state built from world records exposes the decoded true state."""
    state = DaggorathState(
        _build_test_frame(),
        maze=bytes(MAZE_BYTES),
        creatures=bytes(CREATURE_BYTES),
        objects=bytes(OBJECTS_BYTES),
        holes_ladders=bytes(HOLES_LADDERS_BYTES),
    )
    assert state.maze.shape == (MAP_SIZE, MAP_SIZE)
    assert state.creatures.shape == (CREATURE_SLOTS, CREATURE_FIELDS)
    assert state.hands.shape == (HAND_COUNT, OBJECT_RAW_BYTES)
    assert state.pack.shape == (PACK_CAPACITY, OBJECT_RAW_BYTES)
    assert state.objects.shape == (FLOOR_OBJECT_CAPACITY, FLOOR_OBJECT_RAW_BYTES)
    assert state.holes_ladders.shape == (2, HOLE_LADDER_CAPACITY, HOLE_LADDER_RAW_BYTES)


# ---- perception gating ------------------------------------------------------
# Hand-built true states exercise as_perceived(): hands derivation, the pack
# mode gate, creature/object light gating, and the two map planes.


def _build_frame(**field_values) -> bytes:
    """Build a zero-filled frame with the named fields set.

    Width-2 fields are written little-endian, matching the wire format.
    """
    frame = bytearray(FRAME_LEN)
    offsets = {name: (offset, width) for name, offset, width in FIELDS}
    for name, value in field_values.items():
        offset, width = offsets[name]
        if width == 1:
            frame[offset] = value & 0xFF
        else:
            frame[offset] = value & 0xFF
            frame[offset + 1] = (value >> 8) & 0xFF
    return bytes(frame)


def _pack_cell(north, east, south, west):
    """Pack four edge types into a maze byte (LL_DD_RR_UU)."""
    return (west << 6) | (south << 4) | (east << 2) | north


def _build_corridor_maze():
    """A 32×32 rock maze with a straight north-south corridor at x=16, y=4..16."""
    maze = bytearray([0xFF] * MAZE_BYTES)
    for y in range(4, 17):
        north = EDGE_OPEN if y > 4 else EDGE_WALL
        south = EDGE_OPEN if y < 16 else EDGE_WALL
        maze[y * MAP_SIZE + 16] = _pack_cell(north, EDGE_WALL, south, EDGE_WALL)
    return bytes(maze)


def _build_creatures_bytes(slots):
    """Build a creature record from {slot: (alive, type, X, Y)} entries."""
    creatures = bytearray(CREATURE_BYTES)
    for slot, (alive, creature_type, x, y) in slots.items():
        base = slot * CREATURE_FIELDS
        creatures[base] = alive
        creatures[base + 1] = creature_type
        creatures[base + 2] = x
        creatures[base + 3] = y
    return bytes(creatures)


def _build_objects_bytes(hands=(), pack=(), floor=()):
    """Build an object record from hands/pack (class, proper, reveal) and
    floor (class, proper, reveal, X, Y) entries; empty slots are 0xFF."""
    payload = bytearray([0xFF] * OBJECTS_BYTES)
    for index, (class_byte, proper, reveal) in enumerate(hands):
        offset = index * OBJECT_RAW_BYTES
        payload[offset] = class_byte
        payload[offset + 1] = proper
        payload[offset + 2] = reveal
    for index, (class_byte, proper, reveal) in enumerate(pack):
        offset = HANDS_BYTES + index * OBJECT_RAW_BYTES
        payload[offset] = class_byte
        payload[offset + 1] = proper
        payload[offset + 2] = reveal
    for index, (class_byte, proper, reveal, x, y) in enumerate(floor):
        offset = HANDS_BYTES + PACK_BYTES + index * FLOOR_OBJECT_RAW_BYTES
        payload[offset] = class_byte
        payload[offset + 1] = proper
        payload[offset + 2] = reveal
        payload[offset + 3] = x
        payload[offset + 4] = y
    return bytes(payload)


def _build_holes_ladders_bytes(ceiling=(), floor=()):
    """Build a holes/ladders record from (type, Y, X) entries per list."""
    payload = bytearray([0xFF] * HOLES_LADDERS_BYTES)
    for index, (hole_type, y, x) in enumerate(ceiling):
        offset = index * HOLE_LADDER_RAW_BYTES
        payload[offset] = hole_type
        payload[offset + 1] = y
        payload[offset + 2] = x
    for index, (hole_type, y, x) in enumerate(floor):
        offset = HOLE_LADDER_CAPACITY * HOLE_LADDER_RAW_BYTES + index * HOLE_LADDER_RAW_BYTES
        payload[offset] = hole_type
        payload[offset + 1] = y
        payload[offset + 2] = x
    return bytes(payload)


def test_as_perceived_hands_derivation():
    """Hands report specifier indices: unrevealed → bare class, revealed → full."""
    frame = _build_frame(display_function=_DISPLAY_LOOK)
    objects = _build_objects_bytes(hands=((4, 0x11, 1), (4, 0x11, 0)))
    state = DaggorathState(frame, objects=objects)
    perceived = state.as_perceived()
    assert perceived["hands"].tolist() == [4, 26]  # SWORD, WOODEN SWORD


def test_as_perceived_hands_empty_slot():
    """An empty hand slot reports the 0xFF sentinel."""
    frame = _build_frame(display_function=_DISPLAY_LOOK)
    objects = _build_objects_bytes(hands=((0xFF, 0xFF, 0xFF), (0xFF, 0xFF, 0xFF)))
    state = DaggorathState(frame, objects=objects)
    perceived = state.as_perceived()
    assert perceived["hands"].tolist() == [0xFF, 0xFF]


def test_as_perceived_pack_examine_only():
    """The pack appears in EXAMINE and is hidden (0xFF) in LOOK."""
    objects = _build_objects_bytes(pack=((5, 0x0E, 1),))  # unrevealed TORCH → 5
    examine = DaggorathState(_build_frame(display_function=_DISPLAY_EXAMINE), objects=objects)
    assert examine.as_perceived()["pack"].tolist() == [5] + [0xFF] * (PACK_CAPACITY - 1)

    look = DaggorathState(_build_frame(display_function=_DISPLAY_LOOK), objects=objects)
    assert look.as_perceived()["pack"].tolist() == [0xFF] * PACK_CAPACITY


def test_as_perceived_creature_visibility():
    """Creatures are gated by alive, line-of-sight, and magic reach."""
    frame = _build_frame(
        display_function=_DISPLAY_LOOK,
        effective_light_physical=3,
        effective_light_magical=1,
        at_cell_x=16,
        at_cell_y=16,
        at_heading=DIRECTION_NORTH,
    )
    creatures = _build_creatures_bytes({
        0: (0xFF, 0x00, 16, 15),  # physical, in corridor → shipped
        1: (0xFF, 0x0B, 16, 16),  # magical, depth 0 < reach_magic → shipped
        2: (0xFF, 0x0B, 16, 14),  # magical, depth 2 >= reach_magic → hidden
        3: (0x00, 0x00, 16, 15),  # dead → hidden
        4: (0xFF, 0x00, 17, 16),  # off corridor → hidden
    })
    state = DaggorathState(frame, maze=_build_corridor_maze(), creatures=creatures)
    perceived = state.as_perceived()

    assert perceived["creatures"][0].tolist() == [0xFF, 0x00, 16, 15]
    assert perceived["creatures"][1].tolist() == [0xFF, 0x0B, 16, 16]
    assert perceived["creatures"][2].tolist() == [0, 0, 0, 0]
    assert perceived["creatures"][3].tolist() == [0, 0, 0, 0]
    assert perceived["creatures"][4].tolist() == [0, 0, 0, 0]


def test_as_perceived_floor_object_gating():
    """Floor objects ship [specifier, X, Y] only at visible cells."""
    frame = _build_frame(
        display_function=_DISPLAY_LOOK,
        effective_light_physical=3,
        effective_light_magical=0,
        at_cell_x=16,
        at_cell_y=16,
        at_heading=DIRECTION_NORTH,
    )
    objects = _build_objects_bytes(floor=(
        (4, 0x11, 1, 16, 15),  # unrevealed SWORD, visible → [4, 16, 15]
        (5, 0x0E, 1, 17, 16),  # off corridor → hidden
        (0xFF, 0xFF, 0xFF, 0xFF, 0xFF),  # empty → hidden
    ))
    state = DaggorathState(frame, maze=_build_corridor_maze(), objects=objects)
    perceived = state.as_perceived()

    assert perceived["objects"][0].tolist() == [4, 16, 15]
    assert perceived["objects"][1].tolist() == [0, 0, 0]
    assert perceived["objects"][2].tolist() == [0, 0, 0]


def test_as_perceived_map_blackout():
    """Zero physical light blanks the dungeon channels entirely."""
    frame = _build_frame(
        display_function=_DISPLAY_LOOK,
        effective_light_physical=0,
        effective_light_magical=0,
        at_cell_x=16,
        at_cell_y=16,
        at_heading=DIRECTION_NORTH,
    )
    state = DaggorathState(
        frame,
        maze=_build_corridor_maze(),
        creatures=_build_creatures_bytes({0: (0xFF, 0x00, 16, 16)}),
        objects=_build_objects_bytes(floor=((4, 0x11, 1, 16, 15),)),
        holes_ladders=_build_holes_ladders_bytes(),
    )
    perceived = state.as_perceived()

    assert np.all(perceived["map"] == 0xFF)
    assert np.all(perceived["creatures"] == 0)
    assert np.all(perceived["objects"] == 0)


def test_as_perceived_map_edge_fill_and_magic_door_rewrite():
    """Map plane 0 carries edge bytes, rewriting magic doors past the magic reach."""
    frame = _build_frame(
        display_function=_DISPLAY_LOOK,
        effective_light_physical=3,
        effective_light_magical=1,
        at_cell_x=16,
        at_cell_y=16,
        at_heading=DIRECTION_NORTH,
    )
    maze = bytearray([0xFF] * MAZE_BYTES)
    maze[16 * MAP_SIZE + 16] = _pack_cell(EDGE_OPEN, EDGE_WALL, EDGE_WALL, EDGE_MAGIC_DOOR)
    maze[15 * MAP_SIZE + 16] = _pack_cell(EDGE_OPEN, EDGE_WALL, EDGE_OPEN, EDGE_MAGIC_DOOR)
    maze[14 * MAP_SIZE + 16] = _pack_cell(EDGE_OPEN, EDGE_WALL, EDGE_OPEN, EDGE_NORMAL_DOOR)
    state = DaggorathState(frame, maze=bytes(maze))
    perceived = state.as_perceived()

    # Depth 0 — below the magic reach, the magic door is untouched.
    assert perceived["map"][0, 16, 16] == _pack_cell(EDGE_OPEN, EDGE_WALL, EDGE_WALL, EDGE_MAGIC_DOOR)
    # Depth 1 — at/after the magic reach, the magic door reads as a wall.
    assert perceived["map"][0, 15, 16] == _pack_cell(EDGE_OPEN, EDGE_WALL, EDGE_OPEN, EDGE_WALL)
    # Depth 2 — a normal door is never rewritten.
    assert perceived["map"][0, 14, 16] == _pack_cell(EDGE_OPEN, EDGE_WALL, EDGE_OPEN, EDGE_NORMAL_DOOR)
    # Unseen cell stays 0xFF.
    assert perceived["map"][0, 13, 16] == 0xFF


def test_as_perceived_map_feature_fill():
    """Map plane 1 carries the per-cell hole/ladder feature byte."""
    frame = _build_frame(
        display_function=_DISPLAY_LOOK,
        effective_light_physical=3,
        effective_light_magical=0,
        at_cell_x=16,
        at_cell_y=16,
        at_heading=DIRECTION_NORTH,
    )
    holes = _build_holes_ladders_bytes(
        ceiling=((1, 16, 16),),  # ladder in ceiling at (16, 16)
        floor=((0, 15, 16),),    # hole in floor at (16, 15)
    )
    state = DaggorathState(frame, maze=_build_corridor_maze(), holes_ladders=holes)
    perceived = state.as_perceived()

    assert perceived["map"][1, 16, 16] == 2   # ladder-ceiling
    assert perceived["map"][1, 15, 16] == 3   # hole-floor
    assert perceived["map"][1, 14, 16] == 0   # none
    assert perceived["map"][1, 13, 16] == 0xFF  # unseen

def test_holds_final_ring_true():
    """holds_final_ring is True when a hand holds the FINAL ring (0x12)."""
    objects = _build_objects_bytes(hands=((1, 0x12, 0),))  # RING, FINAL
    state = DaggorathState(_build_test_frame(), objects=objects)
    assert state.holds_final_ring is True


def test_holds_final_ring_false():
    """holds_final_ring is False when no hand holds the FINAL ring."""
    objects = _build_objects_bytes(hands=((4, 0x11, 0),))  # WOODEN SWORD
    state = DaggorathState(_build_test_frame(), objects=objects)
    assert state.holds_final_ring is False
    assert DaggorathState(_build_test_frame()).holds_final_ring is False
