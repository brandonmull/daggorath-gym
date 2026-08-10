-- Command-detection plugin: discovers RAM signals that indicate command
-- input has been consumed by the in-game parser. Posts startup commands
-- after the game becomes live, logs comprehensive RAM every frame.
--
-- Key finding from plugin-lifecycle sandbox:
--   emu.add_machine_*_notifier() return values MUST be saved in Lua variables.
--   Discarding them allows Lua GC to auto-unsubscribe.
--
-- Signals logged every frame after 180-frame boot delay:
--   0x0277  gameMode         FF=demo, 00=live
--   0x027B  perfectMatch     FF if input was a perfect match (important for command detection)
--   0x0278  foundMatch       used to check for multiple matches when decoding
--   0x0279  numWords         number of words in table being matched
--   0x02BC  inputHead        ring buffer read index
--   0x02BD  inputTail        ring buffer write index
--   0x02B2  displayFnLo      low byte of displayFunction
--   0x02B3  displayFnHi      high byte of displayFunction
--   0x02B7  whereToPrint     0=command-area, non-0=descriptor given
--   0x02F1:0x02F2  nextToParse  pointer to next input byte to parse
--   0x0390:0x0391  comStart   command area screen buffer start address
--   0x0392:0x0393  comSize    command area size in characters
--   0x0394:0x0395  comTextCur  command area text cursor position
--   0x02D1:0x02F0  inputBuf   32-byte ring buffer (hex dump)
--   comStart..comStart+comSize-1  command area text bytes from screen buffer (ASCII)

local exports = {}
exports.name = "command-detection"
exports.version = "0.0.1"
exports.license = "MIT"
exports.author = { name = "Daggorath Gym" }

local FLUSH_INTERVAL = 60
local BOOT_DELAY = 180
local PRIME_FRAME = 300

-- Commands posted after game is confirmed live (frame ~725).
-- Wider spacing to ensure each command fully processes before the next arrives.
local COMMAND_SCHEDULE = {
    { frame = 750,  text = "PULL LEFT TORCH\r" },
    { frame = 1200, text = "USE LEFT\r" },
    { frame = 1700, text = "MOVE\r" },
}

local memory = nil
local keyboard = nil
local frame = 0
local logFile = nil
local buffer = {}
local acquiredFrame = 0
local primed = false
local commandIndex = 1
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
    commandIndex = 1
end

local function _formatHexByte(b)
    return string.format("%02X", b)
end

local function _readRingBuffer()
    local parts = {}
    for i = 0, 31 do
        parts[#parts + 1] = _formatHexByte(memory:read_u8(0x02D1 + i))
    end
    return table.concat(parts)
end

local function _readCommandAreaText(commandAreaStart, commandAreaSize)
    if commandAreaSize <= 0 or commandAreaSize > 512 then
        return ""
    end
    local parts = {}
    for offset = 0, commandAreaSize - 1 do
        local byte = memory:read_u8(commandAreaStart + offset)
        if byte >= 32 and byte < 127 then
            parts[#parts + 1] = string.char(byte)
        elseif byte == 0 then
            parts[#parts + 1] = "."
        else
            parts[#parts + 1] = string.format("[%02X]", byte)
        end
    end
    return table.concat(parts)
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

    -- Auto-prime at fixed frame to trigger demo-to-live transition
    if not primed and frame >= PRIME_FRAME and keyboard then
        primed = true
        keyboard:post("\r")
        keyboard:post("\r")
    end

    -- Post scheduled commands
    if commandIndex <= #COMMAND_SCHEDULE then
        local scheduled = COMMAND_SCHEDULE[commandIndex]
        if frame >= scheduled.frame and keyboard then
            keyboard:post(scheduled.text)
            buffer[#buffer + 1] = string.format("CMD,%d,%d,%s\n",
                frame, commandIndex, scheduled.text:gsub("[\r\n]", ""))
            commandIndex = commandIndex + 1
        end
    end

    if frame - acquiredFrame < BOOT_DELAY then return end

    local gameMode = memory:read_u8(0x0277)
    local perfectMatch = memory:read_u8(0x027B)
    local foundMatch = memory:read_u8(0x0278)
    local numWords = memory:read_u8(0x0279)
    local inputHead = memory:read_u8(0x02BC)
    local inputTail = memory:read_u8(0x02BD)
    local displayFunctionLow = memory:read_u8(0x02B2)
    local displayFunctionHigh = memory:read_u8(0x02B3)
    local whereToPrint = memory:read_u8(0x02B7)

    -- 6809 is big-endian: the high byte lives at the lower RAM address.
    local nextToParseHighByte = memory:read_u8(0x02F1)
    local nextToParseLowByte = memory:read_u8(0x02F2)
    local nextToParse = nextToParseHighByte * 256 + nextToParseLowByte

    local comStartHighByte = memory:read_u8(0x0390)
    local comStartLowByte = memory:read_u8(0x0391)
    local commandAreaStart = comStartHighByte * 256 + comStartLowByte

    local comSizeHighByte = memory:read_u8(0x0392)
    local comSizeLowByte = memory:read_u8(0x0393)
    local commandAreaSize = comSizeHighByte * 256 + comSizeLowByte

    local comTextCursorHighByte = memory:read_u8(0x0394)
    local comTextCursorLowByte = memory:read_u8(0x0395)
    local commandAreaCursor = comTextCursorHighByte * 256 + comTextCursorLowByte

    local ringBufferHex = _readRingBuffer()
    local commandAreaText = _readCommandAreaText(commandAreaStart, commandAreaSize)

    buffer[#buffer + 1] = string.format(
        "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%s,%s\n",
        frame,
        gameMode,
        perfectMatch,
        foundMatch,
        numWords,
        inputHead,
        inputTail,
        displayFunctionLow,
        displayFunctionHigh,
        whereToPrint,
        nextToParse,
        commandAreaStart,
        commandAreaSize,
        commandAreaCursor,
        ringBufferHex,
        commandAreaText
    )

    if #buffer >= FLUSH_INTERVAL then _flush() end
end

function exports.startplugin()
    logFile = io.open(os.getenv("LOG_FILE"), "w")
    logFile:write("frame,gameMode,perfectMatch,foundMatch,numWords,inputHead,inputTail,displayFunctionLow,displayFunctionHigh,whereToPrint,nextToParse,comStart,comSize,comTextCursor,inputBufHex,comAreaText\n")
    logFile:flush()
    resetSubscription = emu.add_machine_reset_notifier(_onReset)
    frameSubscription = emu.add_machine_frame_notifier(_onFrame)
end

return exports