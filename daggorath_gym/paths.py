"""Filesystem paths for the Daggorath Gym project."""

import os

PROJECT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ROM_PATH = os.path.join(PROJECT_PATH, "emulation", "roms")
HASH_PATH = os.path.join(PROJECT_PATH, "emulation", "hash")

# -pluginspath replaces MAME's default search path, so it must list both the
# project's plugins directory and MAME's system plugins directory — boot.lua
# (MAME's plugin bootstrap) lives in the system one.
PLUGINS_PATH = (
    os.path.join(PROJECT_PATH, "emulation", "plugins")
    + ";/usr/local/share/games/mame/plugins"
)