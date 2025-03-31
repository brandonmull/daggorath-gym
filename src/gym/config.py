cmd = [
    "mame", "coco3", "daggorath",

    # Core options
    "-verbose",                                   # Show verbose output
    "-autoboot_delay", "1",                       # Delay before autoboot script runs (seconds)
    "-autoboot_script", "./src/emu/testboot.lua",   # Lua script to run at startup
    
    # ROM and path options
    "-rompath", "/usr/share/games/mame/roms",     # ROM search path
    "-hashpath", "/usr/share/games/mame/hash",     # ROM search path
    "-pluginspath", "/usr/share/games/mame/plugins", # Plugins path
     
    # Video options
    "-window",                                    # Run in a window (not fullscreen)
    "-resolution", "1280x960",                    # Window resolution
    #  "-waitvsync",                                 # Wait for vertical sync
    #  "-refresh", "60",                             # Refresh rate
    #  "-prescale", "1",                             # Scale before any effects
     
    # Audio options
    #  "-sound", "sdl",                              # Use SDL sound output
    #  "-samplerate", "48000",                       # Audio sample rate
    #  "-volume", "-5",                              # Initial volume (-32 to 0)
]