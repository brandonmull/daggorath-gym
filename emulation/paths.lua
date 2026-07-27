-- Centralized configuration for MAME Lua scripts

local paths = {}

-- Network settings (matches gym/mame_bridge.py defaults)
paths.socket = {
    host = "127.0.0.1",
    state_port = 15000,   -- MAME -> Python (emu.file "w")
    action_port = 15001,  -- Python -> MAME (emu.file "r")
}

return paths