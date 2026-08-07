-- State reporting module for Dungeons of Daggorath.
-- Captures 12 game state fields from RAM each frame, serializes as raw bytes,
-- and writes them to the state socket.
--
-- Public API: state.beginWatching(socket, config)
--   socket: emu.file "w" socket (opened by autoboot)
--   config: { frame_sampling_rate = N } (default: 1 = every frame)

local state = {}

-- Schema: ordered array of { name, addr, width } tables.
-- The byte order is the shared contract with DaggorathStateSchema.FIELDS in Python.
local SCHEMA = {
    { name = "gameMode",             addr = 0x0277, width = 1 },
    { name = "atFloor",              addr = 0x0281, width = 1 },
    { name = "atCellX",              addr = 0x0214, width = 1 },
    { name = "atCellY",              addr = 0x0213, width = 1 },
    { name = "atHeading",            addr = 0x0223, width = 1 },
    { name = "ambientLight",         addr = 0x0226, width = 2 },
    { name = "playerWeight",         addr = 0x0215, width = 2 },
    { name = "playerStrength",       addr = 0x0217, width = 2 },
    { name = "heartBeatInterval",    addr = 0x02AF, width = 1 },
    { name = "heartBeatCountdown",   addr = 0x02AE, width = 1 },
    { name = "playerFainting",       addr = 0x0228, width = 1 },
    { name = "evilWizardDead",       addr = 0x022B, width = 1 },
}

-- Internal state
local _socket = nil
local _memory = nil
local _framesElapsed = 0
local _frameSamplingRate = 1

-- Read all fields and serialize as raw bytes.
local function _sampleState()
    local raw = {}
    for _, field in ipairs(SCHEMA) do
        if field.width == 2 then
            -- 6809 is big-endian (MSB at addr, LSB at addr+1).
            -- Wire format is little-endian: LSB first, then MSB.
            local lo = _memory:read_u8(field.addr + 1)
            local hi = _memory:read_u8(field.addr)
            raw[#raw + 1] = string.char(lo, hi)
        else
            raw[#raw + 1] = string.char(_memory:read_u8(field.addr))
        end
    end
    return table.concat(raw)
end

-- Per-frame notifier: sample and write if this is a sampled frame.
local function _onFrame()
    _framesElapsed = _framesElapsed + 1

    -- Lazy-initialize memory space on first sampled frame
    if not _memory then
        local cpu = manager.machine.devices[":maincpu"]
        if cpu then
            _memory = cpu.spaces["program"]
        end
        if not _memory then
            return -- CPU not ready yet
        end
    end

    -- Skip frames that aren't multiples of the sampling rate
    if _framesElapsed % _frameSamplingRate ~= 0 then
        return
    end

    local raw = _sampleState()
    pcall(function() _socket:write(raw .. "\n") end)
end

-- Public: start watching game state.
function state.beginWatching(socket, config)
    _socket = socket
    _framesElapsed = 0
    _memory = nil

    if config and config.frame_sampling_rate then
        _frameSamplingRate = config.frame_sampling_rate
    else
        _frameSamplingRate = 1
    end

    emu.add_machine_frame_notifier(_onFrame)
end

return state