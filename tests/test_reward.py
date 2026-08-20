"""Unit tests for daggorath_gym.reward — no MAME needed.

The reward layers are exercised on hand-built DaggorathState transitions:
survival shaping, kill/wizard/terminal spikes, advance and combat novelty
(memory), the reject penalty's edge detection, and memory reset.
"""

import math

import pytest

from daggorath_gym.reward import (
    DaggorathReward,
    _ADVANCE_REWARD,
    _DEATH_REWARD,
    _GAMMA,
    _KILL_REWARD,
    _REJECT_REWARD,
    _WIN_REWARD,
    _WIZARD_KILL_REWARD,
    _detect_kills,
)
from daggorath_gym.state import (
    CREATURE_BYTES,
    FRAME_LEN,
    FIELDS,
    OBJECTS_BYTES,
    DaggorathState,
)


def _build_frame(**field_values):
    """Build a zero-filled frame with the named fields set (little-endian)."""
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


def _build_creatures_bytes(slots):
    """Build a creature record from {slot: (alive, type, X, Y)} entries."""
    creatures = bytearray(CREATURE_BYTES)
    for slot, (alive, creature_type, x, y) in slots.items():
        base = slot * 4
        creatures[base] = alive
        creatures[base + 1] = creature_type
        creatures[base + 2] = x
        creatures[base + 3] = y
    return bytes(creatures)


def _build_objects_bytes(hands=()):
    """Build an object record from hands (class, proper, reveal) entries."""
    payload = bytearray([0xFF] * OBJECTS_BYTES)
    for index, (class_byte, proper, reveal) in enumerate(hands):
        offset = index * 3
        payload[offset] = class_byte
        payload[offset + 1] = proper
        payload[offset + 2] = reveal
    return bytes(payload)


# ---- survival shaping -----------------------------------------------------

def test_survival_shaping_rise_and_fall():
    """The survival term pays when the margin rises, charges when it falls."""
    reward = DaggorathReward()
    previous = DaggorathState(_build_frame(player_strength=100, m0221=0))
    stronger = DaggorathState(_build_frame(player_strength=110, m0221=0))
    wounded = DaggorathState(_build_frame(player_strength=100, m0221=30))

    assert reward._survival_shaping(previous, stronger) == pytest.approx(
        _GAMMA * 110 - 100
    )
    assert reward._survival_shaping(previous, wounded) == pytest.approx(
        _GAMMA * 70 - 100
    )


# ---- spikes ---------------------------------------------------------------

def test_detect_kills():
    """A slot going alive -> dead yields the dead creature's type token."""
    previous = DaggorathState(
        _build_frame(),
        creatures=_build_creatures_bytes({0: (0xFF, 3, 1, 1), 1: (0xFF, 7, 2, 2)}),
    )
    current = DaggorathState(
        _build_frame(),
        creatures=_build_creatures_bytes({0: (0x00, 3, 1, 1), 1: (0xFF, 7, 2, 2)}),
    )
    assert _detect_kills(previous, current) == (3,)


def test_kill_spike():
    """Each kill pays the kill spike."""
    reward = DaggorathReward()
    previous = DaggorathState(_build_frame())
    current = DaggorathState(_build_frame())
    assert reward._spike_reward(previous, current, False, (3,)) == pytest.approx(
        _KILL_REWARD
    )
    assert reward._spike_reward(previous, current, False, (3, 7)) == pytest.approx(
        2 * _KILL_REWARD
    )


def test_wizard_kill_spike():
    """evil_wizard_dead flipping 0 -> FF pays the milestone spike."""
    reward = DaggorathReward()
    previous = DaggorathState(_build_frame(evil_wizard_dead=0))
    current = DaggorathState(_build_frame(evil_wizard_dead=0xFF))
    assert reward._spike_reward(previous, current, False, ()) == pytest.approx(
        _WIZARD_KILL_REWARD
    )


def test_death_terminal():
    """A terminated death pays the death reward."""
    reward = DaggorathReward()
    previous = DaggorathState(_build_frame())
    dead = DaggorathState(_build_frame(game_mode=0xFF))
    assert reward._spike_reward(previous, dead, True, ()) == pytest.approx(
        _DEATH_REWARD
    )


def test_win_terminal():
    """A terminated win (held FINAL ring) pays the win reward."""
    reward = DaggorathReward()
    previous = DaggorathState(_build_frame())
    won = DaggorathState(
        _build_frame(), objects=_build_objects_bytes(hands=((1, 0x12, 0),))
    )
    assert reward._spike_reward(previous, won, True, ()) == pytest.approx(
        _WIN_REWARD
    )


# ---- information gain -----------------------------------------------------

def test_advance_pays_once_per_cell():
    """A newly entered cell pays once; re-entering it pays nothing."""
    reward = DaggorathReward()
    cell_state = DaggorathState(_build_frame(at_floor=0, at_cell_x=5, at_cell_y=6))
    assert reward._information_gain(cell_state, ()) == pytest.approx(
        _ADVANCE_REWARD
    )
    assert reward._information_gain(cell_state, ()) == 0.0


def test_combat_novelty_decays():
    """Combat novelty is 1/sqrt(N): the first kill is novel, later ones fade."""
    reward = DaggorathReward()
    cell_state = DaggorathState(_build_frame())
    assert reward._information_gain(cell_state, (3,)) == pytest.approx(
        _ADVANCE_REWARD + 1.0
    )
    assert reward._information_gain(cell_state, (3,)) == pytest.approx(
        1 / math.sqrt(2)
    )


def test_reset_clears_memory():
    """reset() forgets visited cells and kill counts."""
    reward = DaggorathReward()
    cell_state = DaggorathState(_build_frame(at_cell_x=5, at_cell_y=6))
    reward._information_gain(cell_state, (3,))
    reward.reset()
    assert reward._information_gain(cell_state, ()) == pytest.approx(
        _ADVANCE_REWARD
    )
    assert reward._information_gain(cell_state, (3,)) == pytest.approx(1.0)


# ---- reject penalty -------------------------------------------------------

def test_reject_penalty_edge_detected():
    """The reject penalty charges only on the False -> True edge."""
    reward = DaggorathReward()
    previous = DaggorathState(_build_frame())
    rejected = DaggorathState(_build_frame(), command_text="???")
    assert reward._reject_penalty(previous, rejected) == pytest.approx(
        _REJECT_REWARD
    )
    assert reward._reject_penalty(rejected, rejected) == 0.0


# ---- full compute ---------------------------------------------------------

def test_compute_sums_layers():
    """compute() adds shaping and advance together."""
    reward = DaggorathReward()
    previous = DaggorathState(_build_frame(player_strength=100))
    current = DaggorathState(
        _build_frame(player_strength=100, at_cell_x=3, at_cell_y=4)
    )
    total = reward.compute(previous, current, False)
    assert total == pytest.approx((_GAMMA * 100 - 100) + _ADVANCE_REWARD)
