import gymnasium as gym
from daggorath import DaggorathEnv

def main():
    # Create an instance of the Daggorath environment
    env = DaggorathEnv()

    # Reset the environment to get the initial observation
    observation = env.reset()

    done = False
    while not done:
        # Sample a random action from the action space
        action = env.actionSpace.sample()

        # Step the environment with the chosen action
        observation, reward, done, info = env.step(action)

        # Print the observation and reward for debugging
        print(f"Observation: {observation}, Reward: {reward}, Done: {done}")

    # Close the environment when done
    env.close()

if __name__ == "__main__":
    main()
