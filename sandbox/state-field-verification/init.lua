-- State-field-verification plugin.
-- Pokes known values into Daggorath RAM and verifies that the production
-- state.lua sampler reads them back correctly — proving the new state fields
-- (torch minutes/physical/magic via torchPtr, effective_light, m0221,
-- ambient_light) come from the right addresses with the right byte order.

local exports = {}
exports.name = "state-field-verification"
exports.version = "0.0.1"
exports.license = "MIT"
exports.author = { name = "Daggorath Gym" }

-- Load the production state module. MAME does not add the plugin search path
-- to package.path, so prepend it from the environment (lua-module-loading).
local pluginsDir = os.getenv("DAGGORATH_PLUGINS_DIR")
if pluginsDir then
    package.path = pluginsDir .. "/?.lua;" .. package.path
end
local state = require("daggorath/state")

local memory = nil
local keyboard = nil
local frame = 0
local primed = false
local poked = false
local frameSubscription = nil

local function _acquire()
    if not manager.machine then return end
    for tag, device in pairs(manager.machine.devices) do
        if tag == ":maincpu" then
            memory = device.spaces["program"]
            break
        end
    end
    keyboard = manager.machine.natkeyboard
end

local function _isLive()
    if not memory then return false end
    return memory:read_u8(0x02B2) * 256 + memory:read_u8(0x02B3) == 0xCE66
end

local function _pokeRam()
    -- Poke a lit torch into a free object slot: torchPtr points one slot past
    -- the last allocated object (nextObjSlot), plus a margin. The game does
    -- not allocate there while the player stands idle, so the values persist.
    local nextObjSlot = memory:read_u8(0x020F) * 256 + memory:read_u8(0x0210)
    local torchBase = nextObjSlot + 0x14

    memory:write_u8(0x0224, math.floor(torchBase / 256))  -- torchPtr hi
    memory:write_u8(0x0225, torchBase % 256)               -- torchPtr lo

    memory:write_u8(torchBase + 6, 100)  -- torch minutes
    memory:write_u8(torchBase + 7, 7)    -- torch physical light
    memory:write_u8(torchBase + 8, 3)    -- torch magic light

    memory:write_u8(0x0226, 0x01)  -- ambient physical light
    memory:write_u8(0x0227, 0x02)  -- ambient magic light

    memory:write_u8(0x0221, 0x00)  -- m0221 hi (10, below player strength — avoids faint/death)
    memory:write_u8(0x0222, 0x0A)  -- m0221 lo
end

local function _onFrame()
    if manager.machine.paused then memory = nil; return end

    if not memory then
        _acquire()
        if not memory then return end
    end

    frame = frame + 1

    -- Auto-prime the keyboard at frame 300 to trigger the demo→live transition.
    if not primed and frame >= 300 and keyboard then
        primed = true
        keyboard:post("\r")
        keyboard:post("\r")
    end

    -- Poke once the game reaches live play (the production sampler gates on
    -- the same displayFunction value, so it samples the poked values next frame).
    if not poked and _isLive() then
        poked = true
        _pokeRam()
        print("[verify] poked RAM at frame " .. frame)
    end
end

function exports.startplugin()
    local logFile = io.open(os.getenv("LOG_FILE"), "w")
    state.beginWatching(logFile, { frame_sampling_rate = 1 })
    frameSubscription = emu.add_machine_frame_notifier(_onFrame)
    print("[verify] ready")
end

return exports
