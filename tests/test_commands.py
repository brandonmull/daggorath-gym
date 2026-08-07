"""Unit tests for daggorath_gym.commands — no MAME needed.

Tests validate the command phrase list through behavioral properties and
spot-checks rather than hardcoded counts. The list is built from grammar
constants; its exact length will change as the grammar grows. Tests
should remain valid across those changes.

Growth plan:
    - Phase 1 (current): essential commands for dungeon level 1 — movement,
      inventory, combat, and torch use. Spot-checks verify these are present.
    - Phase 2: expand object specifiers when the agent encounters SHIELD,
      FLASK, SCROLL, and RING variants. Add spot-checks for those phrases.
    - Phase 3: add INCANT phrases (all 9 ring proper names except EMPTY)
      when the magic system is targeted. Add REVEAL phrases when hidden
      object properties become relevant.
    - End goal: every phrase that a competent agent needs at the current
      training stage is verified present. Reference grammar:
      docs/references/game/commands.md
"""

import pytest

from daggorath_gym.commands import _COMMAND_PHRASES, DaggorathCommand


# ---- structural checks -----------------------------------------------------

def test_all_phrases_are_unique():
    """No duplicate phrases in the list."""
    assert len(set(_COMMAND_PHRASES)) == len(_COMMAND_PHRASES)


def test_no_whitespace_errors():
    """Phrases contain no leading/trailing whitespace or double spaces."""
    for phrase in _COMMAND_PHRASES:
        assert phrase == phrase.strip()
        assert "  " not in phrase


def test_every_command_word_has_phrases():
    """Each of the game's 13 command words appears in at least one phrase."""
    command_words = {
        "ATTACK", "CLIMB", "DROP", "EXAMINE", "GET", "INCANT",
        "LOOK", "MOVE", "PULL", "REVEAL", "STOW", "TURN", "USE",
    }
    found = set()
    for phrase in _COMMAND_PHRASES:
        first_word = phrase.split(" ")[0]
        found.add(first_word)
    assert found == command_words


# ---- spot-checks: essential commands for dungeon level 1 -------------------
# These are the commands a newly-spawned agent needs to navigate, manage
# inventory, and fight. The set grows as deeper game mechanics are targeted.

_LEVEL_1_ESSENTIALS = [
    # Movement
    "MOVE",
    "MOVE BACK",
    "MOVE LEFT",
    "MOVE RIGHT",
    "TURN LEFT",
    "TURN RIGHT",
    "TURN AROUND",
    "CLIMB UP",
    "CLIMB DOWN",
    # Inventory browsing
    "EXAMINE",
    "LOOK",
    # Pick up / retrieve
    "GET LEFT TORCH",
    "GET RIGHT TORCH",
    "GET LEFT SWORD",
    "GET RIGHT SWORD",
    "DROP LEFT",
    "DROP RIGHT",
    "PULL LEFT TORCH",
    "PULL RIGHT TORCH",
    "PULL LEFT SWORD",
    "PULL RIGHT SWORD",
    "STOW LEFT",
    "STOW RIGHT",
    # Combat and torch lighting
    "ATTACK LEFT",
    "ATTACK RIGHT",
    "USE LEFT",
    "USE RIGHT",
]


def test_level_1_essentials_are_present():
    """Every essential level-1 command exists in the phrase list."""
    for phrase in _LEVEL_1_ESSENTIALS:
        assert phrase in _COMMAND_PHRASES, f"missing essential command: {phrase}"


# ---- DaggorathCommand value object -----------------------------------------

def test_command_index_and_phrase():
    """DaggorathCommand stores its index and returns the matching phrase."""
    cmd = DaggorathCommand(index=0)
    assert cmd.index == 0
    assert cmd.phrase == _COMMAND_PHRASES[0]


def test_command_rejects_negative_index():
    """DaggorathCommand raises ValueError for negative indices."""
    with pytest.raises(ValueError):
        DaggorathCommand(index=-1)


def test_command_rejects_out_of_range_index():
    """DaggorathCommand raises ValueError for indices beyond the list."""
    with pytest.raises(ValueError):
        DaggorathCommand(index=len(_COMMAND_PHRASES))