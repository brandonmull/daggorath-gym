"""Gymnasium environment for Dungeons of Daggorath (1982) on MAME."""

import gymnasium as gym
from gymnasium import spaces
import numpy as np

from .emulator import MameOperator, IpcConfig
from .commands import DaggorathCommand, NUM_COMMANDS
from .state import NUM_FIELDS


class DaggorathEnv(gym.Env):
    """A Gymnasium environment that wraps Dungeons of Daggorath via MAME.

    Action space: Discrete(154) — one index per valid command phrase.
    Observation space: Box(12, uint16) — raw game state fields from RAM.
    Lifecycle: owns a MameOperator; creates it on reset(), stops on close().
    Status: reward and termination raise NotImplementedError (awaiting design).
    """

    def __init__(self, mame_config=None, ipc_config=None):
        super(DaggorathEnv, self).__init__()

        self._mame_config = mame_config
        self._ipc_config = ipc_config

        # Action space: 154 discrete game commands
        self.action_space = spaces.Discrete(NUM_COMMANDS)

        # Observation space: 12 state fields as uint16
        self.observation_space = spaces.Box(
            low=0, high=65535, shape=(NUM_FIELDS,), dtype=np.uint16
        )

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

        return state.to_array(), info

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]:
        # Send command to MAME
        cmd = DaggorathCommand(index=action)
        self._emulator.send(cmd)

        # Receive next game state
        state = self._emulator.recv()

        reward = self._compute_reward(state)
        terminated = self._check_terminated(state)
        truncated = self._check_truncated(state)

        return state.to_array(), reward, terminated, truncated, {}

    def close(self):
        if self._emulator is not None:
            self._emulator.stop()
            self._emulator = None

    # ---- helpers ---------------------------------------------------------

    def _compute_reward(self, state) -> float:
        raise NotImplementedError(
            "Reward function not designed. See plans/reward.md (TBD)."
        )

    def _check_terminated(self, state) -> bool:
        raise NotImplementedError(
            "Termination conditions not designed. See plans/termination.md (TBD)."
        )

    def _check_truncated(self, state) -> bool:
        raise NotImplementedError(
            "Truncation conditions not designed."
        )
