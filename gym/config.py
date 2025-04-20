import os
from .paths import GYM_PATH, EMU_PATH, ROOT_PATH

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(ROOT_PATH, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Combined command with debug options enabled by default
cmd = [
    "mame", "coco3", "daggorath",

    # Core options
    "-verbose",                                   # Show verbose output
    "-debug",                                     # Enable debug output
    "-logfile", os.path.join(LOGS_DIR, "mame.log"), # Specify log file location
    "-autoboot_delay", "4",                       # Delay before autoboot script runs (seconds)
    "-autoboot_script", os.path.join(EMU_PATH, "autoboot.lua"),   # Use our enhanced autoboot script
    
    # ROM and path options
    "-rompath", "/usr/share/games/mame/roms",     # ROM search path
    "-hashpath", "/usr/share/games/mame/hash",     # Hash path
    "-pluginspath", "/usr/share/games/mame/plugins", # Plugins path
     
    # Video options
    "-window",                                    # Run in a window (not fullscreen)
    "-resolution", "1280x960",                    # Window resolution
    #  "-waitvsync",                                 # Wait for vertical sync
    #  "-refresh", "60",                             # Refresh rate
    #  "-prescale", "1",                             # Scale before any effects
     
    # Audio options
    "-sound", "none",    # Disable sound completely
    # "-samplerate", "48000",                       # Audio sample rate
    # "-volume", "-5",                              # Initial volume (-32 to 0)
]

def get_cmd():
    """Return the command configuration"""
    return cmd