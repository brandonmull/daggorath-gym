"""Game state representation for Dungeons of Daggorath.

Receives raw byte frames from the Lua state module, deserializes them
into immutable DaggorathState value objects. Derives agent-facing values
(heart rate) that are not shipped over the wire.
"""

import struct

import numpy as np

# Schema: ordered tuple of (name, offset, width) 3-tuples.
# The byte order is the shared contract with Lua's SCHEMA.
FIELDS: list[tuple[str, int, int]] = [
    ("game_mode", 0, 1),
    ("at_floor", 1, 1),
    ("at_cell_x", 2, 1),
    ("at_cell_y", 3, 1),
    ("at_heading", 4, 1),
    ("ambient_light", 5, 2),
    ("player_weight", 7, 2),
    ("player_strength", 9, 2),
    ("heart_beat_interval", 11, 1),
    ("player_fainting", 12, 1),
    ("evil_wizard_dead", 13, 1),
]

# Total frame length in bytes: 8 u8 + 3 u16 = 8 + 6 = 14
FRAME_LEN = 14

# Number of fields
NUM_FIELDS = len(FIELDS)


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


class DaggorathState:
    """Immutable value object holding one meaningful change of game state.

    Attributes are set via __slots__ for memory efficiency. After
    construction, the instance is frozen — any attempt to set an
    attribute raises AttributeError.

    `heart_rate` is a derived attribute (beats per second) computed from
    `heart_beat_interval`; it is not part of the wire format or to_array().
    """

    __slots__ = tuple(name for name, _, _ in FIELDS) + ("heart_rate", "command_text")

    def __init__(self, data: bytes, command_text: str = "") -> None:
        values = _schema.unpack(data)
        for name, _, _ in FIELDS:
            object.__setattr__(self, name, values[name])

        interval = values["heart_beat_interval"]
        object.__setattr__(self, "heart_rate", 0.0 if interval == 0 else 60.0 / interval)

        object.__setattr__(self, "command_text", command_text)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError(
            f"DaggorathState is immutable; cannot set '{name}'"
        )

    def to_array(self) -> np.ndarray:
        """Return raw state fields as a uint16 numpy array (shape (11,))."""
        return np.array(
            [getattr(self, name) for name, _, _ in FIELDS],
            dtype=np.uint16,
        )