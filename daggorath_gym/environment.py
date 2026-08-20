"""Gymnasium environment for Dungeons of Daggorath (1982) on MAME."""

import gymnasium as gym
from gymnasium import spaces
import numpy as np

from .emulator import MameOperator, IpcConfig
from .commands import (
    NUM_OBJECT_SPECIFIERS,
    NUM_TEMPLATES,
    DaggorathCommand,
    derive_command_index,
)
from .state import PERCEIVED_SPACE, DaggorathState


class DaggorathEnv(gym.Env):
    """A Gymnasium environment that wraps Dungeons of Daggorath via MAME.

    Action space: MultiDiscrete([26, 31]) — a (template, object) pair.
    Observation space: Dict — the perceived state (scalars + world channels).
    Lifecycle: owns a MameOperator; creates it on reset(), stops on close().
    Status: reward is a placeholder 0.0 (the reward wrapper computes the real
    value); termination/truncation still raise NotImplementedError.
    """

    def __init__(self, mame_config=None, ipc_config=None):
        super(DaggorathEnv, self).__init__()

        self._mame_config = mame_config
        self._ipc_config = ipc_config

        # Action space: (template, object) — the command shape plus the object
        # specifier index shared with the observation.
        self.action_space = spaces.MultiDiscrete([NUM_TEMPLATES, NUM_OBJECT_SPECIFIERS])

        # Observation space: the perceived state (scalars + gated world channels)
        self.observation_space = PERCEIVED_SPACE

        self._emulator: MameOperator | None = None

        # The most recent true (ungated) state. The environment holds it so
        # the reward wrapper can read it through the environment object —
        # never through `info` or the observation (see reward/plan.md).
        self._current_state: DaggorathState | None = None

    # ---- Gym interface ---------------------------------------------------

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        """Start a new episode.

        Args:
            seed: Random seed (not yet wired to an RNG).
            options: Optional configuration dict (not yet used).

        Returns:
            (observation, info) tuple. Info contains {"seed": seed}
            when seed is provided.
        """
        if self._emulator is not None:
            self._emulator.stop()

        self._emulator = MameOperator(
            mame_config=self._mame_config,
            ipc_config=self._ipc_config,
        )
        self._emulator.start()

        state = self._emulator.recv()
        self._current_state = state

        info: dict = {}
        if seed is not None:
            info["seed"] = seed

        return state.as_perceived(), info

    def step(self, action: np.ndarray) -> tuple[np.ndarray, float, bool, bool, dict]:
        # Map the factored action to a wire command index. A syntactically
        # invalid pair (INCANT + non-ring) yields None and is a no-op — no
        # command is sent, and the frame still advances.
        command_index = derive_command_index(int(action[0]), int(action[1]))
        if command_index is not None:
            self._emulator.send(DaggorathCommand(index=command_index))

        # Receive next game state
        state = self._emulator.recv()
        self._current_state = state

        reward = self._compute_reward(state)
        terminated = self._check_terminated(state)
        truncated = self._check_truncated(state)

        return state.as_perceived(), reward, terminated, truncated, {}

    def close(self):
        if self._emulator is not None:
            self._emulator.stop()
            self._emulator = None

    # ---- helpers ---------------------------------------------------------

    @property
    def current_state(self) -> DaggorathState | None:
        """The most recent true (ungated) state, for the reward wrapper."""
        return self._current_state

    def _compute_reward(self, state) -> float:
        # The environment returns a placeholder reward; the agent-side reward
        # wrapper (reward.py) reads true state and computes the real scalar.
        return 0.0

    def _check_terminated(self, state) -> bool:
        raise NotImplementedError(
            "Termination conditions not designed. See plans/termination.md (TBD)."
        )

    def _check_truncated(self, state) -> bool:
        raise NotImplementedError(
            "Truncation conditions not designed."
        )
