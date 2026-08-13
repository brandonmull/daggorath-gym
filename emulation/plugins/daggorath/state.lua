-- State reporting module for Dungeons of Daggorath.
-- Captures numeric game state and command-area pixels from RAM each frame,
-- dedups each against a snapshot, and writes tagged records to the state FIFO.
--
-- Public API: state.beginWatching(stateFile, config)
--   stateFile: FIFO file handle (io.open("w"))
--   config: { frame_sampling_rate = N } (default: 1 = every frame)
--
-- Wire format (fixed-size, no delimiter — the pixel payload is binary):
--   "S" + 14-byte frame                              state only changed
--   "T" + 1-byte comColor + 1024 pixel bytes         text only changed
--   "B" + 14-byte frame + 1-byte comColor + 1024 px  both changed

local state = {}

local CHARS_PER_ROW = 32
local SCANLINES_PER_ROW = 8
local TEXT_ROWS = 4
local TOTAL_SCANLINES = TEXT_ROWS * SCANLINES_PER_ROW

local COM_START_HI = 0x0390
local COM_START_LO = 0x0391
local COM_COLOR = 0x0396
local DISPLAY_FN_HI = 0x02B2
local DISPLAY_FN_LO = 0x02B3
local DISPLAY_LIVE = 0xCE66

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
    { name = "playerFainting",       addr = 0x0228, width = 1 },
    { name = "evilWizardDead",       addr = 0x022B, width = 1 },
}

-- Internal state
local _stateFile = nil
local _memory = nil
local _framesElapsed = 0
local _frameSamplingRate = 1
local _stateSnapshot = nil
local _pixelSnapshot = nil
local _comColorSnapshot = nil
local _frameSubscription = nil

-- Diagnostic log (file + flush, survives a segfault).
local _logFile = nil
local function _log(msg)
    if not _logFile then
        _logFile = io.open("/tmp/daggorath-state-log.txt", "w")
    end
    if _logFile then
        _logFile:write(msg .. "\n")
        _logFile:flush()
    end
end

local function _getMemorySpace()
    local cpu = nil
    for tag, device in pairs(manager.machine.devices) do
        if tag == ":maincpu" then cpu = device break end
    end
    _log("getMem: cpu=" .. tostring(cpu ~= nil))
    if not cpu then return nil end

    for name, space in pairs(cpu.spaces) do
        if name == "program" then
            _log("getMem: program space found")
            return space
        end
    end

    _log("getMem: no program space")
    return nil
end

local function _isLive()
    _log("isLive: before hi read")
    local hi = _memory:read_u8(DISPLAY_FN_HI)
    _log("isLive: after hi read, before lo read")
    local lo = _memory:read_u8(DISPLAY_FN_LO)
    _log("isLive: hi=" .. tostring(hi) .. " lo=" .. tostring(lo))
    return (hi * 256 + lo == DISPLAY_LIVE)
end

-- Read all fields and serialize as a 14-byte string. Returns nil if any read
-- fails, so the caller can skip the frame instead of crashing.
local function _sampleState()
    local ok, result = pcall(function()
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
    end)
    if not ok then
        return nil
    end
    return result
end

-- Read the command-area pixel block as a flat 1024-byte string.
local function _readCommandAreaPixels()
    local areaStart = _memory:read_u8(COM_START_HI) * 256
        + _memory:read_u8(COM_START_LO)

    local pixels = {}
    for scanline = 0, TOTAL_SCANLINES - 1 do
        local scanlineStart = areaStart + scanline * CHARS_PER_ROW
        for column = 0, CHARS_PER_ROW - 1 do
            pixels[#pixels + 1] = string.char(
                _memory:read_u8(scanlineStart + column))
        end
    end
    return table.concat(pixels)
end

-- Write one tagged record to the FIFO in a single call.
local function _writeRecord(kind, frame, comColor, pixels)
    local pieces = { kind }
    if frame then
        pieces[#pieces + 1] = frame
    end
    if comColor then
        pieces[#pieces + 1] = string.char(comColor)
    end
    if pixels then
        pieces[#pieces + 1] = pixels
    end

    local ok = pcall(function()
        _stateFile:write(table.concat(pieces))
        _stateFile:flush()
    end)
    if not ok then
        print("[state] Failed to write record " .. kind)
    end
end

-- Per-frame notifier: sample, dedup, and write tagged records.
local function _onFrame()
    _framesElapsed = _framesElapsed + 1
    _log("frame " .. _framesElapsed)

    if manager.machine.paused then
        _log("paused")
        return
    end

    -- Re-acquire the memory space every frame: MAME rebuilds the machine on
    -- reset, invalidating the previously cached space.
    _memory = _getMemorySpace()
    if not _memory then
        _log("failed to acquire memory space")
        return
    end

    -- Skip frames that aren't multiples of the sampling rate
    if _framesElapsed % _frameSamplingRate ~= 0 then
        _log("skipping frame " .. _framesElapsed)
        return
    end

    if not _isLive() then
        _log("not live")
        return
    end

    local frame = _sampleState()
    if not frame then
        _log("failed to sample state")
        return
    end

    _log("sampled")
    local stateChanged = (_stateSnapshot == nil) or (frame ~= _stateSnapshot)

    -- The command area exists only in live play: displayFunction (0x02B2–0x02B3)
    -- is 0xCE66 when the normal playing screen is active and 0x0000 during the
    -- demo loop. Reading the command area during the demo would dereference a
    -- garbage COM_START pointer.
    local displayFn = _memory:read_u8(DISPLAY_FN_HI) * 256
        + _memory:read_u8(DISPLAY_FN_LO)
    local isLive = (displayFn == DISPLAY_LIVE)

    local pixels = nil
    local comColor = nil
    local pixelChanged = false
    if isLive then
        pixels = _readCommandAreaPixels()
        comColor = _memory:read_u8(COM_COLOR)
        pixelChanged = (_pixelSnapshot == nil)
            or (pixels ~= _pixelSnapshot)
            or (comColor ~= _comColorSnapshot)
    end

    if stateChanged and pixelChanged then
        _writeRecord("B", frame, comColor, pixels)
        _stateSnapshot = frame
        _pixelSnapshot = pixels
        _comColorSnapshot = comColor
    elseif stateChanged then
        _writeRecord("S", frame, nil, nil)
        _stateSnapshot = frame
    elseif pixelChanged then
        _writeRecord("T", nil, comColor, pixels)
        _pixelSnapshot = pixels
        _comColorSnapshot = comColor
    end
    -- else: nothing changed — write no record
    _log("wrote")
end

-- Public: start watching game state.
function state.beginWatching(stateFile, config)
    _stateFile = stateFile
    _framesElapsed = 0
    _memory = nil
    _stateSnapshot = nil
    _pixelSnapshot = nil
    _comColorSnapshot = nil

    if config and config.frame_sampling_rate then
        _frameSamplingRate = config.frame_sampling_rate
    else
        _frameSamplingRate = 1
    end

    _frameSubscription = emu.add_machine_frame_notifier(_onFrame)
end

-- Public: clear machine references so the next frame re-acquires them.
-- MAME rebuilds the machine on reset, invalidating the cached memory space.
function state.onReset()
    _memory = nil
    _stateSnapshot = nil
    _pixelSnapshot = nil
    _comColorSnapshot = nil
end

return state