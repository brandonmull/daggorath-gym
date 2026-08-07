-- Daggorath autoboot — self-contained script, no external requires.
-- Two unidirectional emu.file sockets to Python.
--   Port 15000 = state (w) — game state reporting
--   Port 15001 = command (r) — command dispatch
--
-- Opens both sockets and hands them off to the state and commands modules.

local socketConfig = {
    listenHost = os.getenv("SOCKET_LISTEN_HOST") or "127.0.0.1",
    statePort = tonumber(os.getenv("SOCKET_STATE_PORT") or "15000"),
    commandPort = tonumber(os.getenv("SOCKET_COMMAND_PORT") or "15001")
}

local function openSocket(mode, port)
    local socket = emu.file(mode)
    local err = socket:open("socket." .. socketConfig.listenHost .. ":" .. port)
    if err then
        print("[Autoboot] socket error: " .. tostring(err))
        return nil, err
    end
    return socket
end

-- Open state socket (MAME → Python, write-only)
print("[Autoboot] Opening state socket " .. socketConfig.statePort)
local stateErr, stateSocket = openSocket("w", socketConfig.statePort)
if stateErr then
    print("[Autoboot] state socket error: " .. tostring(stateErr))
    return
end

-- Open command socket (Python → MAME, read-only)
print("[Autoboot] Opening command socket " .. socketConfig.commandPort)
local commandErr, commandSocket = openSocket("r", socketConfig.commandPort)
if commandErr then
    print("[Autoboot] command socket error: " .. tostring(commandErr))
    return
end

print("[Autoboot] Sockets ready")

-- Hand off to modules
local state = require("state")
state.beginWatching(stateSocket, { frame_sampling_rate = 1 })

local commands = require("commands")
commands.beginProcessing(commandSocket)

print("[Autoboot] Running")