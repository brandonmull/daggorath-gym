import gymnasium as gym
from gymnasium import spaces
import numpy as np

from .bridge import MameBridge


class DaggorathEnv(gym.Env):
    """Gymnasium environment for Dungeons of Daggorath (1982) on MAME."""

    def __init__(self):
        super(DaggorathEnv, self).__init__()

        # Action space: discrete game commands
        self.action_space = spaces.Discrete(4)  # TODO: expand as commands are wired

        # Observation space: 11 fields from the observer (heart, position, etc.)
        self.observation_space = spaces.Box(
            low=0, high=255, shape=(11,), dtype=np.uint8
        )

        self._bridge: MameBridge | None = None

    # ---- Gym interface ---------------------------------------------------

    def reset(self, **kwargs):
        if self._bridge is not None:
            self._bridge.close()

        self._bridge = MameBridge()
        self._bridge.start()

        obs = self._bridge.recv()
        return self._obs_to_array(obs), {}

    def step(self, action):
        # Send action to MAME
        cmd = self._action_to_command(action)
        self._bridge.send(cmd)

        # Receive next game state
        obs = self._bridge.recv()

        reward = self._compute_reward(obs)
        terminated = False          # TODO: detect game over from state
        truncated = False

        return self._obs_to_array(obs), reward, terminated, truncated, {}

    def close(self):
        if self._bridge is not None:
            self._bridge.close()
            self._bridge = None

    # ---- helpers ---------------------------------------------------------

    @staticmethod
    def _obs_to_array(obs: dict) -> np.ndarray:
        """Convert the JSON observation dict into a flat numpy array."""
        return np.array(
            [
                obs.get("heartCounter", 0),
                obs.get("heartCounterRel", 0),
                obs.get("fainting", 0),
                obs.get("wizardDead", 0),
                obs.get("playerX", 0),
                obs.get("playerY", 0),
                obs.get("playerHP", 0),
                obs.get("playerStamina", 0),
                obs.get("gameState", 0),
                obs.get("activeObject", 0),
                0,  # placeholder for future fields
            ],
            dtype=np.uint8,
        )

    @staticmethod
    def _action_to_command(action: int) -> dict:
        """Map a discrete action index to a JSON command.

        TODO: once commands.lua dispatch is implemented, update this mapping.
        """
        actions = ["MOVE_FORWARD", "TURN_LEFT", "ATTACK", "USE_ITEM"]
        return {"action": actions[action % len(actions)]}

    @staticmethod
    def _compute_reward(obs: dict) -> float:
        # Simple placeholder — reward based on player HP
        hp = obs.get("playerHP", 255)
        return float(hp) / 255.0