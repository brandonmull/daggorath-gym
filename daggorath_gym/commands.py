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


def _build_object_specifiers():
    """Build the 31 object specifiers: bare class, then each proper name + class."""
    specifiers = []
    for cls in _OBJECT_CLASSES:
        specifiers.append(cls)
        for name in _OBJECT_PROPER_NAMES[cls]:
            specifiers.append(f"{name} {cls}")
    return specifiers


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