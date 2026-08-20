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

from .commands import derive_specifier_index
from .navigation import REACH_CAP, rewrite_magic_doors, walk_corridor

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
    ("display_function", 21, 2),
]

# Total frame length in bytes: 15 u8 + 4 u16 = 15 + 8 = 23
FRAME_LEN = 23

# Number of fields
NUM_FIELDS = len(FIELDS)

# Display-mode values (shared with state.lua's DISPLAY_LOOK / DISPLAY_EXAMINE).
# The mode gates the perception channels: LOOK draws the dungeon, EXAMINE draws
# the inventory.
_DISPLAY_LOOK = 0xCE66
_DISPLAY_EXAMINE = 0xD495

# Creature type tokens drawn on the magic-light channel — scorpion, wraith,
# galdrog, demon, wizard. The other seven types are physical (see creatures plan).
_MAGICAL_CREATURE_TYPES = frozenset({0x06, 0x08, 0x09, 0x0A, 0x0B})

# Proper-type token of the FINAL ring — the win's terminal: INCANT FINAL
# writes this token into the held ring's proper-type field (objects/plan.md).
_FINAL_RING_TOKEN = 0x12

# Perceived-state dimensions. Creature slots and map size are the game's own
# bounds; the pack and floor-object caps are our fixed-capacity choices
# (fixed slots, 0xFF-padded — the perception plan's option A).
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
# in absolute coordinates; agent-side wrappers translate to relative.
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


def _derive_specifier_slots(raw: np.ndarray) -> np.ndarray:
    """Map an (N, 3) raw-object array to an (N,) specifier-index array.

    Each raw entry is (class, proper token, reveal threshold); empty slots
    carry a 0xFF class byte and map to the 0xFF empty sentinel.
    """
    specifiers = np.full(raw.shape[0], 0xFF, dtype=np.uint8)
    for index in range(raw.shape[0]):
        class_byte = int(raw[index, 0])
        if class_byte == 0xFF:
            continue
        specifiers[index] = derive_specifier_index(
            class_byte, int(raw[index, 1]), int(raw[index, 2])
        )
    return specifiers


def _build_feature_lookup(holes_ladders: np.ndarray) -> dict[tuple[int, int], int]:
    """Map each hole/ladder cell to its per-cell feature byte (1-4).

    Ceiling entries produce hole-ceiling (1) or ladder-ceiling (2); floor
    entries produce hole-floor (3) or ladder-floor (4). Empty slots carry a
    0xFF type and are skipped.
    """
    lookup: dict[tuple[int, int], int] = {}
    for list_index, base in ((0, 1), (1, 3)):
        for entry in holes_ladders[list_index]:
            feature_type = int(entry[0])
            if feature_type == 0xFF:
                continue
            lookup[(int(entry[2]), int(entry[1]))] = base + feature_type
    return lookup


class DaggorathState:
    """Immutable value object holding one meaningful change of game state.

    Attributes are set via __slots__ for memory efficiency. After
    construction, the instance is frozen — any attempt to set an
    attribute raises AttributeError.

    `heart_rate` is a derived attribute (beats per second) computed from
    `heart_beat_interval`; `command_rejected` is derived from `command_text`
    (True when the command area shows the game's "???" rejection); and
    `holds_final_ring` is True when a hand holds the FINAL ring (the win's
    terminal). None of them is part of the wire format or as_perceived().
    The world attributes — `maze`, `creatures`, `hands`, `pack`, `objects`,
    `holes_ladders` — hold the true, ungated state decoded from the M/C/O/H
    records, and are None until the corresponding record has arrived.
    """

    __slots__ = (
        tuple(name for name, _, _ in FIELDS)
        + (
            "heart_rate",
            "command_text",
            "command_rejected",
            "holds_final_ring",
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

        # The game prints "???" in the command area when it rejects the last
        # command — a true-state fact the reward wrapper prices, not a
        # perception channel.
        object.__setattr__(self, "command_rejected", "???" in command_text)

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

        # The win's terminal: a hand holding the FINAL ring (0x12), set by
        # INCANT FINAL. A derived true-state fact used by both the env's
        # termination check and the reward wrapper's +1 spike.
        object.__setattr__(
            self,
            "holds_final_ring",
            self.hands is not None
            and any(int(hand[1]) == _FINAL_RING_TOKEN for hand in self.hands),
        )

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

        The scalars are the nineteen always-present fields, including the
        display mode. The world channels are gated: hands are always present;
        the pack appears only in EXAMINE; creatures, objects, and the map
        appear only in LOOK with physical light, within the line-of-sight
        corridor walk. Empty object slots and unseen map cells use the 0xFF
        sentinel.
        """
        scalars = np.array(
            [getattr(self, name) for name, _, _ in FIELDS],
            dtype=np.uint16,
        )

        # Hands — always present, empty slots are 0xFF.
        if self.hands is None:
            hands = np.full(HAND_COUNT, 0xFF, dtype=np.uint8)
        else:
            hands = _derive_specifier_slots(self.hands)

        # Pack — EXAMINE only; LOOK (or an unknown mode) hides the inventory.
        if self.display_function == _DISPLAY_EXAMINE and self.pack is not None:
            pack = _derive_specifier_slots(self.pack)
        else:
            pack = np.full(PACK_CAPACITY, 0xFF, dtype=np.uint8)

        # Dungeon — LOOK with physical light; blackout or any other mode
        # yields no visible cells.
        visible: dict[tuple[int, int], int] = {}
        if (
            self.display_function == _DISPLAY_LOOK
            and self.effective_light_physical > 0
            and self.maze is not None
        ):
            visible = walk_corridor(
                self.maze,
                self.at_cell_x,
                self.at_cell_y,
                self.at_heading,
                self.effective_light_physical,
            )

        reach_magic = min(self.effective_light_magical, REACH_CAP)

        # Creatures — alive slots whose cell is in the walk; magical types
        # must additionally be within the magic reach.
        creatures = np.zeros((CREATURE_SLOTS, 4), dtype=np.uint8)
        if self.creatures is not None:
            for slot in range(CREATURE_SLOTS):
                alive = int(self.creatures[slot, 0])
                if alive == 0:
                    continue
                creature_type = int(self.creatures[slot, 1])
                cell = (int(self.creatures[slot, 2]), int(self.creatures[slot, 3]))
                if cell not in visible:
                    continue
                if (
                    creature_type in _MAGICAL_CREATURE_TYPES
                    and visible[cell] >= reach_magic
                ):
                    continue
                creatures[slot] = self.creatures[slot]

        # Floor objects — visible cells ship [specifier, X, Y].
        objects = np.zeros((FLOOR_OBJECT_CAPACITY, 3), dtype=np.uint8)
        if self.objects is not None:
            for index in range(FLOOR_OBJECT_CAPACITY):
                entry = self.objects[index]
                class_byte = int(entry[0])
                if class_byte == 0xFF:
                    continue
                cell = (int(entry[3]), int(entry[4]))
                if cell not in visible:
                    continue
                specifier = derive_specifier_index(
                    class_byte, int(entry[1]), int(entry[2])
                )
                objects[index] = (specifier, cell[0], cell[1])

        # Map — plane 0 edge bytes, plane 1 feature bytes; 0xFF unseen.
        # A magic door past the magic reach reads as a wall.
        map_planes = np.full((2, MAP_SIZE, MAP_SIZE), 0xFF, dtype=np.uint8)
        if self.maze is not None:
            feature_lookup = (
                _build_feature_lookup(self.holes_ladders)
                if self.holes_ladders is not None
                else {}
            )
            for (x, y), depth in visible.items():
                edge = int(self.maze[y, x])
                if depth >= reach_magic:
                    edge = rewrite_magic_doors(edge)
                map_planes[0, y, x] = edge
                map_planes[1, y, x] = feature_lookup.get((x, y), 0)

        return {
            "scalars": scalars,
            "hands": hands,
            "pack": pack,
            "creatures": creatures,
            "objects": objects,
            "map": map_planes,
        }