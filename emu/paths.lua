-- Centralized path definitions for MAME Lua scripts

local paths = {}

-- Basic MAME paths
paths.mame = "/usr/share/games/mame"
paths.plugins = paths.mame .. "/plugins"
paths.roms = paths.mame .. "/roms"
paths.hash = paths.mame .. "/hash"

-- Lua paths
paths.lua = "/usr/local/share/lua/5.3"
paths.lua_c = "/usr/local/lib/lua/5.3"
paths.lua_modules = {
    -- Lua module locations (.lua files)
    paths.lua .. "/?.lua",
    paths.lua .. "/?/init.lua",
    
    -- Lua C module locations (.so files)
    paths.lua_c .. "/?.so",
    paths.lua_c .. "/?/core.so"
}

-- Network settings
paths.socket = {
    host = "127.0.0.1",
    port = 15000,
    timeout = 1
}

return paths
