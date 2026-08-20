"""Command phrase enumeration for Dungeons of Daggorath.

Builds the ordered list of 154 valid command phrases at import time.
The phrase list's order is the shared contract with Lua's COMMAND_PHRASES.
"""

from dataclasses import dataclass

# Grammar constants (alphabetical order, mirrors commands.lua)
_COMMAND_WORDS = ["ATTACK", "CLIMB", "DROP", "MOVE", "REVEAL", "STOW", "TURN", "USE"]

_COMMAND_DIRECTIONS = {
    "ATTACK": ["LEFT", "RIGHT"],
    "CLIMB": ["UP", "DOWN"],
    "DROP": ["LEFT", "RIGHT"],
    "MOVE": ["BACK", "LEFT", "RIGHT"],
    "REVEAL": ["LEFT", "RIGHT"],
    "STOW": ["LEFT", "RIGHT"],
    "TURN": ["LEFT", "RIGHT", "AROUND"],
    "USE": ["LEFT", "RIGHT"],
}

_OBJECT_CLASSES = ["FLASK", "RING", "SCROLL", "SHIELD", "SWORD", "TORCH"]

_OBJECT_PROPER_NAMES = {
    "FLASK": ["ABYE", "EMPTY", "HALE", "THEWS"],
    "RING": ["ENERGY", "FINAL", "FIRE", "GOLD", "ICE", "JOULE", "RIME", "SUPREME", "VULCAN"],
    "SCROLL": ["SEER", "VISION"],
    "SHIELD": ["BRONZE", "LEATHER", "MITHRIL"],
    "SWORD": ["ELVISH", "IRON", "WOODEN"],
    "TORCH": ["DEAD", "LUNAR", "PINE", "SOLAR"],
}

# ROM fact: proper-type token → (class name, proper name). The token is the
# index into the Proper Names table at D8F4 (commands.md Appendix D) and is
# stored in the object's proper-type field (slot + 9).
_PROPER_TYPE_BY_TOKEN = {
    0x00: ("RING", "SUPREME"),
    0x01: ("RING", "JOULE"),
    0x02: ("SWORD", "ELVISH"),
    0x03: ("SHIELD", "MITHRIL"),
    0x04: ("SCROLL", "SEER"),
    0x05: ("FLASK", "THEWS"),
    0x06: ("RING", "RIME"),
    0x07: ("SCROLL", "VISION"),
    0x08: ("FLASK", "ABYE"),
    0x09: ("FLASK", "HALE"),
    0x0A: ("TORCH", "SOLAR"),
    0x0B: ("SHIELD", "BRONZE"),
    0x0C: ("RING", "VULCAN"),
    0x0D: ("SWORD", "IRON"),
    0x0E: ("TORCH", "LUNAR"),
    0x0F: ("TORCH", "PINE"),
    0x10: ("SHIELD", "LEATHER"),
    0x11: ("SWORD", "WOODEN"),
    0x12: ("RING", "FINAL"),
    0x13: ("RING", "ENERGY"),
    0x14: ("RING", "ICE"),
    0x15: ("RING", "FIRE"),
    0x16: ("RING", "GOLD"),
    0x17: ("FLASK", "EMPTY"),
    0x18: ("TORCH", "DEAD"),
}


def _build_object_specifiers():
    """Build the 31 object specifiers: bare class, then each proper name + class."""
    specifiers = []
    for cls in _OBJECT_CLASSES:
        specifiers.append(cls)
        for name in _OBJECT_PROPER_NAMES[cls]:
            specifiers.append(f"{name} {cls}")
    return specifiers


# The 31 object specifiers in the shared observation/action index order:
# the six bare classes first (0–5), then every proper name + class (6–30),
# class-major. This is a separate ordering from the command phrases, which
# interleave each class with its own proper names.
_OBJECT_SPECIFIER_INDEX = list(_OBJECT_CLASSES) + [
    f"{name} {cls}" for cls in _OBJECT_CLASSES for name in _OBJECT_PROPER_NAMES[cls]
]

# Built at import: proper-type token → the full "proper name + class"
# specifier index — the revealed branch of the specifier derivation.
_SPECIFIER_INDEX_BY_TOKEN = {
    token: _OBJECT_SPECIFIER_INDEX.index(f"{name} {class_name}")
    for token, (class_name, name) in _PROPER_TYPE_BY_TOKEN.items()
}


def derive_specifier_index(class_byte: int, proper_token: int, reveal_threshold: int) -> int:
    """Derive the perceived object specifier index (0–30) from raw bytes.

    The class byte is the bare specifier index while unrevealed — the six
    class bytes 0–5 are themselves the bare-class indices, so dropping the
    proper type means returning the class byte. Once revealed (reveal
    threshold 0), the index is the full "proper name + class" specifier,
    looked up by the proper-type token. An empty slot's 0xFF class byte falls
    through the unrevealed branch to 0xFF.
    """
    if reveal_threshold != 0:
        return class_byte
    return _SPECIFIER_INDEX_BY_TOKEN[proper_token]


def _build_command_phrases():
    """Build the full ordered list of 154 command phrases.

    The order is the shared contract with Lua's COMMAND_PHRASES.
    """
    phrases = []
    specifiers = _build_object_specifiers()

    # Direction-bearing commands (order matches command table §1 in plan)
    direction_words = [
        "MOVE", "TURN", "CLIMB",
        "ATTACK", "USE", "DROP", "STOW", "REVEAL",
    ]

    for word in direction_words:
        dirs = _COMMAND_DIRECTIONS[word]
        if word == "MOVE":
            # MOVE has a bare form plus directions
            phrases.append(word)
        for d in dirs:
            phrases.append(f"{word} {d}")

    # Standalone (no direction, no specifier)
    phrases.append("EXAMINE")
    phrases.append("LOOK")

    # GET and PULL (direction × 31 specifiers each)
    for word in ("GET", "PULL"):
        for d in ("LEFT", "RIGHT"):
            for spec in specifiers:
                phrases.append(f"{word} {d} {spec}")

    # INCANT (ring proper names, all except EMPTY)
    for name in _OBJECT_PROPER_NAMES["RING"]:
        if name != "EMPTY":
            phrases.append(f"INCANT {name}")

    return phrases


# The ordered phrase list — shared contract with Lua's COMMAND_PHRASES
_COMMAND_PHRASES = _build_command_phrases()

# Total number of valid command phrases
NUM_COMMANDS = len(_COMMAND_PHRASES)


@dataclass(frozen=True)
class DaggorathCommand:
    """A validated command index wrapping a game command.

    Construction validates that the index is in range 0–153 and raises
    ValueError otherwise. The phrase property returns the human-readable
    command string.
    """

    index: int

    def __post_init__(self):
        if self.index < 0 or self.index >= NUM_COMMANDS:
            raise ValueError(
                f"Command index {self.index} out of range [0, {NUM_COMMANDS - 1}]"
            )

    @property
    def phrase(self) -> str:
        """The human-readable command string (e.g., 'ATTACK LEFT')."""
        return _COMMAND_PHRASES[self.index]