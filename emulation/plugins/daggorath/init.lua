-- Daggorath plugin entry point.
-- Opens the state FIFO for writing and the command socket for reading,
-- then hands both off to the state and commands modules.
--
-- Notifier subscriptions are saved to module-local variables to prevent
-- Lua's garbage collector from auto-unsubscribing them.

local exports = {}
exports.name = "daggorath"
exports.version = "0.0.1"
exports.license = "MIT"
exports.author = { name = "Daggorath Gym" }

local commands = require("commands")
local state = require("state")

local resetSubscription = nil
local stopSubscription = nil

local function _onReset()
    -- Re-acquire memory handles after machine reset
    -- The state module handles lazy memory acquisition on next frame
end

local function _onStop()
    -- Clean up when emulation stops
end

function exports.startplugin()
    -- Open the state FIFO for writing
    local stateFifoPath = os.getenv("STATE_FIFO_PATH") or "/tmp/daggorath-state"
    local stateFile = io.open(stateFifoPath, "w")
    if not stateFile then
        print("[daggorath] ERROR: Could not open state FIFO: " .. stateFifoPath)
        return
    end
    print("[daggorath] State FIFO opened: " .. stateFifoPath)

    -- Open the command socket for reading
    local commandHost = os.getenv("COMMAND_HOST") or "127.0.0.1"
    local commandPort = os.getenv("COMMAND_PORT") or "15001"
    local commandSocket = emu.file("r")
    local err = commandSocket:open("socket." .. commandHost .. ":" .. commandPort)
    if err then
        print("[daggorath] ERROR: Could not open command socket: " .. tostring(err))
        return
    end
    print("[daggorath] Command socket opened: " .. commandHost .. ":" .. commandPort)

    -- Hand off to domain modules
    state.beginWatching(stateFile, { frame_sampling_rate = 1 })
    commands.beginProcessing(commandSocket)

    -- Save notifier subscriptions (GC fix: must store return values or GC auto-unsubscribes)
    resetSubscription = emu.add_machine_reset_notifier(_onReset)
    stopSubscription = emu.add_machine_stop_notifier(_onStop)

    print("[daggorath] Plugin ready")
end

return exports