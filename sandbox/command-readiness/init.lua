-- Command-readiness plugin: logs Daggorath RAM signals every frame
-- through the demo→live transition to determine exactly when the game
-- becomes ready for agent commands.
--
-- Key finding from plugin-lifecycle sandbox:
--   emu.add_machine_*_notifier() return values MUST be saved in Lua variables.
--   Discarding them allows Lua GC to auto-unsubscribe.
--
-- Signals logged every frame after 180-frame boot delay:
--   0x0277  gameMode        FF = demo, 00 = live play
--   0x02BC  inputHead       ring buffer read index
--   0x02BD  inputTail       ring buffer write index
--   0x02B2  displayFnLo     low byte of displayFunction (0x66 = normal screen CE66)
--   0x02B3  displayFnHi     high byte of displayFunction (0xCE = normal screen)

local exports = {}
exports.name = "command-readiness"
exports.version = "0.0.1"
exports.license = "MIT"
exports.author = { name = "Daggorath Gym" }

local FLUSH_INTERVAL = 60
local BOOT_DELAY = 180

local memory = nil
local keyboard = nil
local frame = 0
local logFile = nil
local buffer = {}
local acquiredFrame = 0
local primed = false
local resetSubscription = nil
local frameSubscription = nil

local function _acquire()
    if not manager.machine then return end
    local cpu = manager.machine.devices[":maincpu"]
    if cpu then memory = cpu.spaces["program"] end
    keyboard = manager.machine.natkeyboard
end

local function _flush()
    if logFile and #buffer > 0 then
        logFile:write(table.concat(buffer))
        logFile:flush()
        buffer = {}
    end
end

local function _onReset()
    logFile:write("RESET\n")
    logFile:flush()
    _acquire()
    frame = 0
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

    -- Auto-prime at frame 300 (well past boot delay)
    if not primed and frame >= 300 and keyboard then
        primed = true
        keyboard:post("\r")
        keyboard:post("\r")
    end

    if frame - acquiredFrame < BOOT_DELAY then return end

    local gm = memory:read_u8(0x0277)
    local ih = memory:read_u8(0x02BC)
    local it = memory:read_u8(0x02BD)
    local dfl = memory:read_u8(0x02B2)
    local dfh = memory:read_u8(0x02B3)

    buffer[#buffer + 1] = string.format("%d,%d,%d,%d,%d,%d\n", frame, gm, ih, it, dfl, dfh)

    if #buffer >= FLUSH_INTERVAL then _flush() end
end

function exports.startplugin()
    logFile = io.open(os.getenv("LOG_FILE"), "w")
    logFile:write("frame,gameMode,inputHead,inputTail,displayFnLo,displayFnHi\n")
    logFile:flush()
    resetSubscription = emu.add_machine_reset_notifier(_onReset)
    frameSubscription = emu.add_machine_frame_notifier(_onFrame)
end

return exports