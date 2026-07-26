-- Daggorath key mappings
-- Functions return the keycode so autoboot.lua can handle press/release timing.

local commands = {}

-- Movement
commands.up      = function() return "P1_UP" end
commands.down    = function() return "P1_DOWN" end
commands.left    = function() return "P1_LEFT" end
commands.right   = function() return "P1_RIGHT" end
commands.enter   = function() return "P1_START" end

-- Game commands (letter keys)
commands.attack  = function() return "KEYCODE_A" end
commands.move    = function() return "KEYCODE_M" end
commands.look    = function() return "KEYCODE_L" end
commands.climb   = function() return "KEYCODE_C" end
commands.use     = function() return "KEYCODE_U" end
commands.incant  = function() return "KEYCODE_I" end

return commands