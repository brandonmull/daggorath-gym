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
from .state import PERCEIVED_SPACE


class DaggorathEnv(gym.Env):
    """A Gymnasium environment that wraps Dungeons of Daggorath via MAME.

    Action space: MultiDiscrete([26, 31]) — a (template, object) pair.
    Observation space: Dict — the perceived state (scalars + world channels).
    Lifecycle: owns a MameOperator; creates it on reset(), stops on close().
    Status: reward and termination raise NotImplementedError (awaiting design).
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

        reward = self._compute_reward(state)
        terminated = self._check_terminated(state)
        truncated = self._check_truncated(state)

        return state.as_perceived(), reward, terminated, truncated, {}

    def close(self):
        if self._emulator is not None:
            self._emulator.stop()
            self._emulator = None

    # ---- helpers ---------------------------------------------------------

    def _compute_reward(self, state) -> float:
        raise NotImplementedError(
            "Reward function not designed. See plans/reward/plan.md."
        )

    def _check_terminated(self, state) -> bool:
        raise NotImplementedError(
            "Termination conditions not designed. See plans/termination.md (TBD)."
        )

    def _check_truncated(self, state) -> bool:
        raise NotImplementedError(
            "Truncation conditions not designed."
        )
