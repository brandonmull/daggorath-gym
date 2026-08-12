-- return-key experiment: posts a single Return keystroke and captures
-- the command area screen buffer to observe what \r writes.
--
-- Requires SANDBOX_DIR env var for Lua module path (set by run.py).

local sandboxDir = os.getenv("SANDBOX_DIR")
if sandboxDir then
    package.path = sandboxDir .. "/?.lua;" .. package.path
end

local shared = require("shared")

local exports = {}
exports.name = "return-key"
exports.version = "0.0.1"
exports.license = "MIT"
exports.author = { name = "Daggorath Gym" }

local BOOT_DELAY = 180
local RETURN_FRAME = 600

local memory = nil
local keyboard = nil
local frame = 0
local logFile = nil
local acquiredFrame = 0
local posted = false
local resetSubscription = nil
local frameSubscription = nil

local function _acquire()
    if not manager.machine then return end
    local cpu = manager.machine.devices[":maincpu"]
    if cpu then memory = cpu.spaces["program"] end
    keyboard = manager.machine.natkeyboard
end

local function _onReset()
    _acquire()
    frame = 0
    posted = false
end

local function _onFrame()
    if not manager.machine then return end
    if manager.machine.paused then memory = nil; return end

    if not memory then
        _acquire()
        if not memory then return end
        acquiredFrame = frame
    end

    frame = frame + 1

    if frame - acquiredFrame < BOOT_DELAY then return end

    local displayFunction = memory:read_u8(0x02B2) * 256 + memory:read_u8(0x02B3)

    if displayFunction == 0xCE66 then
        if not posted and frame >= RETURN_FRAME and keyboard then
            posted = true
            keyboard:post("\r")
        end
        shared.captureCommandAreaPixels(logFile, frame, memory)
    end
end

function exports.startplugin()
    logFile = io.open(os.getenv("LOG_FILE"), "w")
    if not logFile then return end

    resetSubscription = emu.add_machine_reset_notifier(_onReset)
    frameSubscription = emu.add_machine_frame_notifier(_onFrame)
end

return exports