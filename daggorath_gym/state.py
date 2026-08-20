"""Game state representation for Dungeons of Daggorath.

Receives raw byte frames from the Lua state module, deserializes them
into immutable DaggorathState value objects. Derives agent-facing values
(heart rate) that are not shipped over the wire. Defines the true-state
schema (FIELDS) and the perceived-state schema (PERCEIVED_SPACE) that the
environment exposes as the observation.
"""

import struct

import numpy as np
from gymnasium import spaces

# Schema: ordered tuple of (name, offset, width) 3-tuples.
# The byte order is the shared contract with Lua's SCHEMA.
FIELDS: list[tuple[str, int, int]] = [
    ("game_mode", 0, 1),
    ("at_floor", 1, 1),
    ("at_cell_x", 2, 1),
    ("at_cell_y", 3, 1),
    ("at_heading", 4, 1),
    ("ambient_light_physical", 5, 1),
    ("ambient_light_magical", 6, 1),
    ("effective_light_physical", 7, 1),
    ("effective_light_magical", 8, 1),
    ("torch_minutes", 9, 1),
    ("torch_physical_light", 10, 1),
    ("torch_magic_light", 11, 1),
    ("player_weight", 12, 2),
    ("player_strength", 14, 2),
    ("m0221", 16, 2),
    ("heart_beat_interval", 18, 1),
    ("player_fainting", 19, 1),
    ("evil_wizard_dead", 20, 1),
]

# Total frame length in bytes: 15 u8 + 3 u16 = 15 + 6 = 21
FRAME_LEN = 21

# Number of fields
NUM_FIELDS = len(FIELDS)

# Perceived-state dimensions. Creature slots and map size are the game's own
# bounds; the pack and floor-object caps are our fixed-capacity choices
# (fixed slots, zero-padded — the perception plan's option A).
CREATURE_SLOTS = 32
MAP_SIZE = 32
HAND_COUNT = 2
PACK_CAPACITY = 8
FLOOR_OBJECT_CAPACITY = 8

# World-channel wire sizes. The maze is 32×32 raw edge bytes (row-major); the
# creature record is 32 slots × 4 fields; the object record is hands + pack +
# floor objects, each a fixed-capacity sub-array. These are the shared contract
# with state.lua's world-channel constants.
MAZE_BYTES = MAP_SIZE * MAP_SIZE
CREATURE_FIELDS = 4
CREATURE_BYTES = CREATURE_SLOTS * CREATURE_FIELDS
OBJECT_RAW_BYTES = 3
FLOOR_OBJECT_RAW_BYTES = 5
HANDS_BYTES = HAND_COUNT * OBJECT_RAW_BYTES
PACK_BYTES = PACK_CAPACITY * OBJECT_RAW_BYTES
FLOOR_OBJECTS_BYTES = FLOOR_OBJECT_CAPACITY * FLOOR_OBJECT_RAW_BYTES
OBJECTS_BYTES = HANDS_BYTES + PACK_BYTES + FLOOR_OBJECTS_BYTES

# Holes/ladders wire sizes: two lists (ceiling then floor) × capacity 4 ×
# a 3-byte entry (type, Y, X). The capacity matches the hand-authored ROM table.
HOLE_LADDER_RAW_BYTES = 3
HOLE_LADDER_CAPACITY = 4
HOLES_LADDERS_BYTES = 2 * HOLE_LADDER_CAPACITY * HOLE_LADDER_RAW_BYTES

# The perceived state — what the policy sees — is the true state passed
# through the perception gates (line-of-sight, display mode, light), reported
# in absolute coordinates; agent-side wrappers translate to relative. Only the
# scalars are sampled today, so the world channels are zeroed stubs until
# creatures, objects, and maze land on the wire.
PERCEIVED_SPACE = spaces.Dict({
    "scalars": spaces.Box(low=0, high=65535, shape=(NUM_FIELDS,), dtype=np.uint16),
    "hands": spaces.Box(low=0, high=255, shape=(HAND_COUNT,), dtype=np.uint8),
    "pack": spaces.Box(low=0, high=255, shape=(PACK_CAPACITY,), dtype=np.uint8),
    "creatures": spaces.Box(low=0, high=255, shape=(CREATURE_SLOTS, 4), dtype=np.uint8),
    "objects": spaces.Box(low=0, high=255, shape=(FLOOR_OBJECT_CAPACITY, 3), dtype=np.uint8),
    "map": spaces.Box(low=0, high=255, shape=(2, MAP_SIZE, MAP_SIZE), dtype=np.uint8),
})


class DaggorathStateSchema:
    """Flyweight schema: shared field definitions, created once at module import.

    Converts raw byte frames to dicts for DaggorathState construction.
    """

    def unpack(self, data: bytes) -> dict[str, int]:
        """Deserialize a raw byte frame into a dict of {field_name: value}.

        Args:
            data: Exactly FRAME_LEN bytes of raw state data.

        Returns:
            Dict mapping field names to integer values.

        Raises:
            ValueError: If data length does not match FRAME_LEN.
        """
        if len(data) != FRAME_LEN:
            raise ValueError(
                f"Expected {FRAME_LEN} bytes, got {len(data)}"
            )

        result: dict[str, int] = {}
        for name, offset, width in FIELDS:
            if width == 1:
                result[name] = data[offset]
            else:
                result[name] = struct.unpack_from("<H", data, offset)[0]
        return result


# Module-level schema instance (flyweight)
_schema = DaggorathStateSchema()


def decode_maze(payload: bytes) -> np.ndarray:
    """Decode a 1024-byte maze record into a (32, 32) uint8 grid.

    The wire is row-major: cell (Y, X) lives at byte Y * 32 + X, so the
    reshaped array is indexed as [y][x].
    """
    return np.frombuffer(payload, dtype=np.uint8).reshape(MAP_SIZE, MAP_SIZE)


def decode_creatures(payload: bytes) -> np.ndarray:
    """Decode a 128-byte creature record into a (32, 4) uint8 array.

    Each slot is alive, type, X, Y — the wire order matching the perceived
    channel. Dead and empty slots zero the alive byte.
    """
    return np.frombuffer(payload, dtype=np.uint8).reshape(CREATURE_SLOTS, CREATURE_FIELDS)


def decode_objects(payload: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Decode a 70-byte object record into hands, pack, and floor objects.

    Returns three uint8 arrays: hands (2, 3), pack (8, 3), and floor objects
    (8, 5) — each entry's first byte is the class, with 0xFF marking empty.
    """
    hands = np.frombuffer(payload, dtype=np.uint8, count=HANDS_BYTES).reshape(
        HAND_COUNT, OBJECT_RAW_BYTES
    )
    pack_start = HANDS_BYTES
    pack = np.frombuffer(payload, dtype=np.uint8, count=PACK_BYTES, offset=pack_start).reshape(
        PACK_CAPACITY, OBJECT_RAW_BYTES
    )
    floor_start = HANDS_BYTES + PACK_BYTES
    floor_objects = np.frombuffer(
        payload, dtype=np.uint8, count=FLOOR_OBJECTS_BYTES, offset=floor_start
    ).reshape(FLOOR_OBJECT_CAPACITY, FLOOR_OBJECT_RAW_BYTES)
    return hands, pack, floor_objects


def decode_holes_ladders(payload: bytes) -> np.ndarray:
    """Decode a 24-byte holes/ladders record into a (2, 4, 3) uint8 array.

    Axis 0 is the list — index 0 the ceiling list (climb up), index 1 the
    floor list (climb down). Each entry is type (0 hole, 1 ladder), Y, X;
    empty slots carry a 0xFF type.
    """
    return np.frombuffer(payload, dtype=np.uint8).reshape(
        2, HOLE_LADDER_CAPACITY, HOLE_LADDER_RAW_BYTES
    )


class DaggorathState:
    """Immutable value object holding one meaningful change of game state.

    Attributes are set via __slots__ for memory efficiency. After
    construction, the instance is frozen — any attempt to set an
    attribute raises AttributeError.

    `heart_rate` is a derived attribute (beats per second) computed from
    `heart_beat_interval`; it is not part of the wire format or as_perceived().
    The world attributes — `maze`, `creatures`, `hands`, `pack`, `objects`,
    `holes_ladders` — hold the true, ungated state decoded from the M/C/O/H
    records, and are None until the corresponding record has arrived.
    """

    __slots__ = (
        tuple(name for name, _, _ in FIELDS)
        + (
            "heart_rate",
            "command_text",
            "maze",
            "creatures",
            "hands",
            "pack",
            "objects",
            "holes_ladders",
        )
    )

    def __init__(
        self,
        data: bytes,
        command_text: str = "",
        maze: bytes | None = None,
        creatures: bytes | None = None,
        objects: bytes | None = None,
        holes_ladders: bytes | None = None,
    ) -> None:
        values = _schema.unpack(data)
        for name, _, _ in FIELDS:
            object.__setattr__(self, name, values[name])

        interval = values["heart_beat_interval"]
        object.__setattr__(self, "heart_rate", 0.0 if interval == 0 else 60.0 / interval)

        object.__setattr__(self, "command_text", command_text)

        object.__setattr__(self, "maze", decode_maze(maze) if maze is not None else None)
        object.__setattr__(
            self, "creatures", decode_creatures(creatures) if creatures is not None else None
        )
        if objects is None:
            object.__setattr__(self, "hands", None)
            object.__setattr__(self, "pack", None)
            object.__setattr__(self, "objects", None)
        else:
            hands, pack, floor_objects = decode_objects(objects)
            object.__setattr__(self, "hands", hands)
            object.__setattr__(self, "pack", pack)
            object.__setattr__(self, "objects", floor_objects)

        object.__setattr__(
            self,
            "holes_ladders",
            decode_holes_ladders(holes_ladders) if holes_ladders is not None else None,
        )

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(
            f"DaggorathState is immutable; cannot set '{name}'"
        )

    def as_perceived(self) -> dict[str, np.ndarray]:
        """Return the state as perceived by the player, as a Dict observation.

        The scalars are the eighteen always-present self-fields. The world
        channels (hands, pack, creatures, objects, map) are zeroed stubs —
        they are decoded onto the wire but not yet gated, so their zeros must
        not be read as an empty world. The perception gates (line-of-sight,
        display mode, light) will fill them once the specifier derivation and
        the gates land.
        """
        return {
            "scalars": np.array(
                [getattr(self, name) for name, _, _ in FIELDS],
                dtype=np.uint16,
            ),
            "hands": np.zeros(HAND_COUNT, dtype=np.uint8),
            "pack": np.zeros(PACK_CAPACITY, dtype=np.uint8),
            "creatures": np.zeros((CREATURE_SLOTS, 4), dtype=np.uint8),
            "objects": np.zeros((FLOOR_OBJECT_CAPACITY, 3), dtype=np.uint8),
            "map": np.zeros((2, MAP_SIZE, MAP_SIZE), dtype=np.uint8),
        }