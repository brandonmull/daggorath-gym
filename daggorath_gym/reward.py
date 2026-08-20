"""Reward for Dungeons of Daggorath — the agent-side reward wrapper.

WHY THIS EXISTS (the background of thought)
----------------------------------------
The environment is the objective world: it holds the true state (creatures,
objects, maze, every player field) and reports only what the player perceives.
The reward is a *separate, agent-side* component that reads that true state and
assigns it value. This is the project's "fact vs valuation" boundary
(reward/conversation.md): the environment answers "what is true / what
happened"; the reward answers "what is any of it worth". The policy never sees
true state; the reward is *supposed* to.

Reward must collapse into ONE scalar per step (Stable-Baselines3 stores reward
as a flat float array and does scalar arithmetic on it), so this module adds up
three layers, each doing a distinct job:

  - SPIKES           — the objective itself: what was achieved. One-shot, large,
                       temporally-local rewards for kills and the win/loss.
  - POTENTIALS       — potential-based shaping: how good the situation is now.
                       The term gamma*Phi(next) - Phi(current) scores the
                       situation and densifies the gradient between spikes. It is
                       provably policy-invariant: it never changes the optimal
                       policy, only the speed of learning.
  - INFORMATION GAIN — intrinsic motivation: what was learned. Novelty-bounded
                       rewards for the unknown -> known transition, tracked in an
                       episode-scoped memory.

Plus a small REJECT penalty for commands the game refuses with "???" — the
player's own negative feedback, priced from the environment-reported fact
`command_rejected`.

WHY SPIKES + POTENTIALS ARE BOTH NEEDED
---------------------------------------
With only the survival potential, the optimal policy is to stand still: m0221
does not rise unless the agent exerts, so the survival margin stays high forever
— no risk, no death, steady reward, and no gradient pulling the agent into the
dungeon. The spikes (kills, the win) are what the agent is actually chasing; the
potentials just densify the path to them.

WHY THE SURVIVAL POTENTIAL USES THE MARGIN, NOT HEART RATE
----------------------------------------------------------
Attacking raises m0221 (exertion) exactly like being hit does. Penalising a high
heart rate would punish the very combat that wins fights. The margin
player_strength - m0221 sidesteps this: strength grows with kills, m0221 tracks
accumulated exertion, and their difference is the distance to death.

WHY INFORMATION GAIN MUST BE NOVELTY-BOUNDED
--------------------------------------------
Without a "first time only" gate, the agent stands still and stares at what it
already knows, farming the same reward forever. The memory records what has
been learned so far (visited cells, per-type kill counts) and pays only the
unknown -> known transition.

DEFERRED (placeholders below, not yet implemented)
--------------------------------------------------
- Structural DISCOVERY (+0.1 per salient feature: junction, door, dead end,
  corridor termination) — needs a line-of-sight feature extractor in
  navigation.py.
- Reveal novelty (first reveal of each (class, proper) pair) — needs a
  coefficient, and object power on the wire to scale by power as the plan
  intends.
- Creature type/instance "seen" and "heard" novelty — "heard" needs the
  deferred sound channel.
- The remaining six potentials (strength, sight, holdings, safety, strain,
  incapacity) — only survival has a formula today.
- Pick-up spike — objects/plan.md defers it (holdings would double-count).

See reward/plan.md and reward/conversation.md for the full design.
"""

import math

import gymnasium as gym

from .state import DaggorathState


# ---- Coefficients (light, tunable — reward/plan.md "Coefficients") -------
# The scale rule is terminal >> discovery >> advance: terminal events dominate,
# discovery is a meaningful tenth, advance is a dense hundredth. These numbers
# are starting points, not final.
_WIN_REWARD = 1.0          # the win: INCANT FINAL transforms the held ring
_DEATH_REWARD = -1.0       # death: game_mode flips to FF
_KILL_REWARD = 0.2         # per creature killed (not in the plan table; tunable)
_WIZARD_KILL_REWARD = 0.5  # the milestone before the win (tunable)
_ADVANCE_REWARD = 0.01     # each newly entered cell
_REJECT_REWARD = -0.1      # a command the game refused with "???"
_GAMMA = 0.99              # discount inside the potential-based shaping term

# The win is two-stage: killing the wizard (evil_wizard_dead -> FF) is a spike,
# NOT terminal; the terminal is INCANT FINAL writing 0x12 (FINAL) into the held
# ring's proper-type field. See objects/plan.md "The win is two stages".
_FINAL_RING_TOKEN = 0x12


def _detect_kills(previous, current):
    """Return the creature-type tokens of slots that just died (alive -> dead).

    A kill is a creature slot's alive byte going non-zero to zero across the
    step. The type is read from the PREVIOUS state — the type of the creature
    that was alive and is now dead. Returns a tuple, one token per kill.
    """
    if previous.creatures is None or current.creatures is None:
        return ()
    killed = []
    for slot in range(current.creatures.shape[0]):
        was_alive = previous.creatures[slot, 0] != 0
        is_alive = current.creatures[slot, 0] != 0
        if was_alive and not is_alive:
            killed.append(int(previous.creatures[slot, 1]))
    return tuple(killed)


def _survival_potential(state):
    """Phi — the distance to death, the only potential with a formula today."""
    return state.player_strength - state.m0221


def _holds_final_ring(state):
    """True when a hand holds the FINAL ring (proper-type token 0x12)."""
    if state.hands is None:
        return False
    for hand in state.hands:
        if int(hand[1]) == _FINAL_RING_TOKEN:
            return True
    return False


class DaggorathReward:
    """The pure reward computation: state transition + episode memory -> scalar.

    Holds the episode-scoped novelty memory (visited cells, per-type kill
    counts) and turns a previous -> current transition into one number. Pure
    Python — no gymnasium or MAME dependency — so it is unit-testable on
    hand-built states. `DaggorathRewardWrapper` (below) is the thin gymnasium
    adapter that feeds it real environment states.
    """

    def __init__(self):
        # Episode-scoped memory, reset per episode in reset(). The memory IS the
        # "novelty gate": it records what has already been learned, so the
        # information-gain layer pays only the unknown -> known transition.
        self._visited_cells = set()  # (floor, x, y) cells already entered
        self._kill_counts = {}       # creature type -> kill count this episode

    def reset(self):
        """Clear the episode-scoped memory for a fresh episode.

        Called from the wrapper's reset(): the memory is per-episode, so a new
        game starts with no cells visited and no kills counted.
        """
        self._visited_cells.clear()
        self._kill_counts.clear()

    def compute(self, previous, current, terminated):
        """Return the scalar reward for a previous -> current transition.

        Args:
            previous: the true state before the step (from reset or last step).
            current: the true state after the step.
            terminated: the environment's objective game-over fact — True when
                the episode ends by death or the win.
        """
        killed_types = _detect_kills(previous, current)

        reward = 0.0
        reward += self._spike_reward(previous, current, terminated, killed_types)
        reward += self._survival_shaping(previous, current)
        reward += self._information_gain(current, killed_types)
        reward += self._reject_penalty(previous, current)
        return reward

    # ---- layers ---------------------------------------------------------

    def _spike_reward(self, previous, current, terminated, killed_types):
        """The objective: kills, the wizard, and the terminal events."""
        reward = 0.0

        # Terminal events. The environment reports the game-over fact; the
        # wrapper assigns its value. Death is game_mode -> FF; the win is the
        # held FINAL ring (proper-type 0x12). Truncation carries no spike.
        if terminated:
            if current.game_mode == 0xFF:
                reward += _DEATH_REWARD
            elif _holds_final_ring(current):
                reward += _WIN_REWARD

        # Kill spike: every kill pays, so the agent learns early that combat
        # pays off. One-shot and temporally local — it fires once at the kill
        # and then vanishes, so it teaches without a standing incentive to
        # stay in combat.
        reward += _KILL_REWARD * len(killed_types)

        # Wizard kill: the milestone before the win. Tracked through the
        # dedicated evil_wizard_dead flag (0 -> FF) rather than the creature
        # slot, so it reads as the game's own "the wizard is dead" signal.
        # (The wizard's slot also dies, so it nets +0.2 kill +0.5 milestone —
        # appropriate for the climactic kill.)
        if previous.evil_wizard_dead == 0 and current.evil_wizard_dead == 0xFF:
            reward += _WIZARD_KILL_REWARD

        # DEFERRED (placeholder): pick-up spike. objects/plan.md defers it —
        # the holdings potential would double-count the same gain.

        return reward

    def _survival_shaping(self, previous, current):
        """Potential-based shaping: gamma*Phi(current) - Phi(previous).

        Pays when the survival margin rises, charges when it falls. Because it
        is potential-based it never changes the optimal policy — it only
        densifies the gradient between spikes so every step carries signal.
        """
        return _GAMMA * _survival_potential(current) - _survival_potential(previous)

    def _information_gain(self, current, killed_types):
        """Intrinsic motivation: novelty-bounded rewards for learning."""
        reward = 0.0

        # Advance: each newly entered cell pays a trickle, keeping the agent
        # moving through long corridors. Keyed by (floor, x, y) so a cell pays
        # once per episode — re-entering it, or returning after a descent,
        # never re-pays.
        cell = (current.at_floor, current.at_cell_x, current.at_cell_y)
        if cell not in self._visited_cells:
            self._visited_cells.add(cell)
            reward += _ADVANCE_REWARD

        # Combat novelty: each kill of a type pays 1/sqrt(N), where N is the
        # type's kill count. Facts are learned in one exposure; skills are
        # learned by repetition. The first fight is maximally novel, the tenth
        # pays a third as much, the hundredth is familiar.
        for creature_type in killed_types:
            count = self._kill_counts.get(creature_type, 0) + 1
            self._kill_counts[creature_type] = count
            reward += 1.0 / math.sqrt(count)

        # DEFERRED (placeholder): structural DISCOVERY (+0.1 per salient
        # feature — junction, door, dead end, corridor termination). Needs a
        # line-of-sight feature extractor in navigation.py; novelty keyed by
        # feature identity. Discovery dominates advance: a junction is worth a
        # meaningful tenth, a new cell a dense hundredth.
        #
        # DEFERRED (placeholder): reveal novelty — the first reveal of each
        # (class, proper) pair. reward/plan.md intends it to scale with the
        # object's power, which needs power on the wire (we ship class/proper/
        # reveal only) and a coefficient.
        #
        # DEFERRED (placeholder): creature type/instance "seen" novelty —
        # one-shot flags for the first sighting of each type and each instance.
        # "Heard" additionally needs the deferred sound channel.

        return reward

    def _reject_penalty(self, previous, current):
        """The player's own negative feedback: a command the game refused.

        The environment reports `command_rejected` (derived from the game's
        "???" in the command area). It is a *level* — the "???" lingers for a
        few frames until the game redraws — so we charge only on the
        False -> True edge, once per rejection, never per frame.
        """
        if not previous.command_rejected and current.command_rejected:
            return _REJECT_REWARD
        return 0.0


class DaggorathRewardWrapper(gym.Wrapper):
    """Plugs the reward computation around the environment.

    Overrides reset() and step() to hold the previous -> current transition and
    to replace the environment's placeholder reward with the computed scalar.
    """

    def __init__(self, env):
        super().__init__(env)
        self._reward = DaggorathReward()
        self._previous_state = None

    def reset(self, *, seed=None, options=None):
        # Why override reset()? Two reasons:
        #   1. The first step's shaping term is gamma*Phi(s1) - Phi(s0), which
        #      needs Phi(s0) — the potential of the initial state. Capturing
        #      the post-reset state here gives the first step its "previous".
        #   2. The novelty memory is episode-scoped, so it must clear here.
        observation, info = self.env.reset(seed=seed, options=options)
        self._previous_state = self.env.current_state
        self._reward.reset()
        return observation, info

    def step(self, action):
        previous_state = self._previous_state
        observation, _, terminated, truncated, info = self.env.step(action)
        current_state = self.env.current_state
        reward = self._reward.compute(previous_state, current_state, terminated)
        self._previous_state = current_state
        return observation, reward, terminated, truncated, info
