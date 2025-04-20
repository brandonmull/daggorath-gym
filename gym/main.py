import gymnasium as gym
from gymnasium import spaces
import numpy as np
import subprocess
import time
import shlex
import os
from .paths import EMU_PATH
from .config import get_cmd

class DaggorathEnv(gym.Env):
    def __init__(self):
        super(DaggorathEnv, self).__init__()

        # Define action and observation space
        # Assuming the game has a discrete action space
        self.action_space = spaces.Discrete(4)  # Example: 4 possible actions
        self.observation_space = spaces.Box(low=0, high=255, shape=(1,), dtype=np.uint8)  # Example observation shape

        # Start MAME process
        self.process = None

    def reset(self, **kwargs):
        # Start MAME with configuration from config.py
        command = get_cmd()

        try:
            self.process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                bufsize=1  # Line buffered
            )
            
            # Initialize connection with the game (wait for it to start)
            time.sleep(1)  # Allow some time for the game to start
            
            # Get initial observation
            observation = self.get_observation()
            info = {}
            
            return observation, info

        except FileNotFoundError as e:
            print(f"FileNotFoundError: {e}")
            raise
        except Exception as e:
            print(f"An error occurred: {e}")
            raise

    def step(self, action):
        # Send action to the game
        self.send_action(action)

        # Read the game state from the MAME process output
        observation = self.get_observation()
        reward = self.calculate_reward(observation)
        terminated = False  # Define termination condition
        truncated = False   # Define truncation condition
        info = {}           # Additional info

        return observation, reward, terminated, truncated, info

    def get_observation(self):
        # Return the current observation (e.g., heart rate)
        # In a real implementation, this would read from the MAME process
        return np.array([0], dtype=np.uint8)  # Placeholder for initial observation

    def send_action(self, action):
        # Implement action sending logic to MAME (e.g., simulate key presses)
        pass  # Replace with actual action handling

    def calculate_reward(self, observation):
        # Define your reward function based on observation
        return 0  # Placeholder reward function

    def close(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)  # Wait up to 5 seconds for process to terminate
            except subprocess.TimeoutExpired:
                self.process.kill()  # Force kill if it doesn't terminate