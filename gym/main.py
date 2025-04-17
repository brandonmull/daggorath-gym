import gymnasium as gym
from gymnasium import spaces
import numpy as np
import subprocess
import time
import shlex
import os
from .paths import EMU_PATH

class DaggorathEnv(gym.Env):
    def __init__(self):
        super(DaggorathEnv, self).__init__()

        # Define action and observation space
        # Assuming the game has a discrete action space
        self.actionSpace = spaces.Discrete(4)  # Example: 4 possible actions
        self.observationSpace = spaces.Box(low=0, high=255, shape=(1,), dtype=np.uint8)  # Example observation shape

        # Start MAME process
        self.process = None

    def reset(self):
        # Start MAME with the Lua script and specify the ROM and hash paths
        command = [
            "mame", "coco3", "daggorath",
            "-rompath", "C:/Emulators/Mame/roms",
            "-hashpath", "C:/Emulators/Mame/hash",
            "-debug"
        ]

        try:
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = self.process.communicate()  # Wait for the process to complete and capture output

            if stderr:
                print(f"Error output: {stderr}")  # Print any error messages
            else:
                print(f"Standard output: {stdout}")  # Print standard output if needed

        except FileNotFoundError as e:
            print(f"FileNotFoundError: {e}")  # Print the specific error message
        except Exception as e:
            print(f"An error occurred: {e}")  # Print any other exceptions

        # Reset the environment state
        time.sleep(1)  # Allow some time for the game to start
        return self.getObservation()

    def step(self, action):
        # Send action to the game (this part may vary based on how actions are handled in the game)
        self.sendAction(action)

        # Read the game state from the Lua script output
        output = self.process.stdout.readline()
        if output:
            # Process the output to extract game state information
            if output.startswith("heartrate:"):
                heartRate = int(output.split(":")[1])
                observation = np.array([heartRate], dtype=np.uint8)  # Example observation
                reward = self.calculateReward(heartRate)  # Define your reward function
                done = False  # Define your termination condition
                return observation, reward, done, {}

        return self.getObservation(), 0, False, {}

    def getObservation(self):
        # Return the current observation (e.g., heart rate)
        return np.array([0], dtype=np.uint8)  # Placeholder for initial observation

    def sendAction(self, action):
        # Implement action sending logic to MAME (e.g., simulate key presses)
        pass  # Replace with actual action handling

    def calculateReward(self, heartRate):
        # Define your reward function based on heart rate or other game metrics
        return heartRate  # Example reward based on heart rate

    def close(self):
        if self.process:
            self.process.terminate()