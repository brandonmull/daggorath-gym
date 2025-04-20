# Daggorath Gym Environment

A Gymnasium environment for Dungeons of Daggorath using MAME.

## Installation

1. Make sure you have MAME installed with the Dungeons of Daggorath ROM
2. Install the Python package:
   ```
   pip install -e .
   ```
3. Set up the local hash files:
   ```
   python emu/setup_hash.py
   ```

## Usage

```python
import gym
import daggorath_gym

env = gym.make('Daggorath-v0')
observation, info = env.reset()

for _ in range(1000):
    action = env.action_space.sample()  # Your agent's action
    observation, reward, terminated, truncated, info = env.step(action)
    
    if terminated or truncated:
        observation, info = env.reset()

env.close()
```

## Important Note on MAME Hash Files

The environment uses a local copy of MAME hash files to prevent corruption of your system's files. If you experience any issues with ROM loading or corruption, run the setup script:

```
python emu/setup_hash.py
```

This will create local copies of the necessary hash files in the `emu/hash` directory.

## Technical Details: Hash File Protection

### The Issue

MAME sometimes modifies hash files (like `coco_cart.xml`) when run with certain debug options. This can corrupt system-wide hash files located in `/usr/share/games/mame/hash/`, potentially causing issues with other MAME games.

### Our Solution

We've implemented several safeguards:

1. **Local Hash Directory**: The environment now uses a local hash directory (`emu/hash/`) instead of the system-wide one.
   
2. **Setup Script**: The `emu/setup_hash.py` script helps users create and populate the local hash directory from their existing MAME installation.

3. **Safety Checks**: The `test_gym.py` script checks for improper configurations that might lead to file corruption and warns users.

### If Your Hash Files Were Corrupted

If your system's hash files were corrupted, you can restore them by:

1. Using your system's package manager to reinstall MAME
   ```
   sudo apt-get reinstall mame-data  # For Debian/Ubuntu
   ```

2. Downloading the original files from the MAME repository:
   ```
   wget https://raw.githubusercontent.com/mamedev/mame/master/hash/coco_cart.xml -O /usr/share/games/mame/hash/coco_cart.xml
   ```

3. Using the setup script to create a local copy that won't affect your system files:
   ```
   python emu/setup_hash.py
   ``` 