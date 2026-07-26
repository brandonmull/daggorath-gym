import os
from .paths import EMU_PATH, ROOT_PATH

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(ROOT_PATH, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# MAME command defaults — mirrors sandbox/server.py proven flags.
# MameBridge uses these as baseline; individual kwargs override them.
cmd = [
    "mame", "coco3", "daggorath",

    # Core options
    "-autoboot_script", os.path.join(EMU_PATH, "autoboot.lua"),
    "-skip_gameinfo",
    "-nonvram_save",

    # ROM and path options (local project paths — MameBridge provides these)
    "-rompath", os.path.join(ROOT_PATH, "emu", "roms"),
    "-hashpath", os.path.join(ROOT_PATH, "emu", "hash"),

    # Video
    "-window",

    # Audio (SDL backend — best quality on WSLg)
    "-sound", "sdl",
]


def get_cmd():
    """Return the default command configuration (used by tests / standalone)."""
    return cmd