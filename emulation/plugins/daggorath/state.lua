-- State reporting module for Dungeons of Daggorath.
-- Captures numeric game state and command-area pixels from RAM each frame,
-- dedups each against a snapshot, and writes tagged records to the state FIFO.
--
-- Public API: state.beginWatching(stateFile, config)
--   stateFile: FIFO file handle (io.open("w"))
--   config: { frame_sampling_rate = N } (default: 1 = every frame)
--
-- Wire format (fixed-size, no delimiter — the pixel payload is binary):
--   "S" + 21-byte frame                              state only changed
--   "T" + 1-byte comColor + 1024 pixel bytes         text only changed
--   "B" + 21-byte frame + 1-byte comColor + 1024 px  both changed
--   "M" + 1024-byte maze                             maze changed
--   "C" + 128-byte creature array                    creatures changed
--   "O" + 70-byte object record                      objects changed
--   "H" + 24-byte holes/ladders record               holes/ladders changed

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
local DISPLAY_LOOK = 0xCE66
local DISPLAY_EXAMINE = 0xD495
local TORCH_PTR_HI = 0x0224
local TORCH_PTR_LO = 0x0225

-- World-channel addresses. The maze, creature array, and object array are
-- fixed RAM regions; the current level filters floor objects.
local MAZE_START = 0x05F4
local CREATURE_ARRAY_START = 0x03D4
local OBJECT_ARRAY_BASE = 0x0B15
local NEXT_OBJ_SLOT_HI = 0x020F
local NEXT_OBJ_SLOT_LO = 0x0210
local LEFT_HAND_HI = 0x021D
local LEFT_HAND_LO = 0x021E
local RIGHT_HAND_HI = 0x021F
local RIGHT_HAND_LO = 0x0220
local FIRST_PACK_HI = 0x0229
local FIRST_PACK_LO = 0x022A
local CURRENT_LEVEL_ADDR = 0x0281

-- World-channel sizes (the shared wire contract with state.py).
local MAZE_BYTES = 1024
local CREATURE_SLOTS = 32
local CREATURE_SLOT_BYTES = 17
local CREATURE_FIELDS = 4
local CREATURE_BYTES = CREATURE_SLOTS * CREATURE_FIELDS
local OBJECT_SLOT_BYTES = 14
local OBJECT_RAW_BYTES = 3
local FLOOR_OBJECT_RAW_BYTES = 5
local HAND_COUNT = 2
local PACK_CAPACITY = 8
local FLOOR_OBJECT_CAPACITY = 8
local HANDS_BYTES = HAND_COUNT * OBJECT_RAW_BYTES
local PACK_BYTES = PACK_CAPACITY * OBJECT_RAW_BYTES
local FLOOR_OBJECTS_BYTES = FLOOR_OBJECT_CAPACITY * FLOOR_OBJECT_RAW_BYTES
local OBJECTS_BYTES = HANDS_BYTES + PACK_BYTES + FLOOR_OBJECTS_BYTES

-- Creature slot field offsets (17-byte slots).
local CREATURE_ALIVE_OFFSET = 12
local CREATURE_TYPE_OFFSET = 13
local CREATURE_Y_OFFSET = 15
local CREATURE_X_OFFSET = 16

-- Object slot field offsets (14-byte slots).
local OBJECT_Y_OFFSET = 2
local OBJECT_X_OFFSET = 3
local OBJECT_LEVEL_OFFSET = 4
local OBJECT_LOCATION_OFFSET = 5
local OBJECT_PROPER_OFFSET = 9
local OBJECT_CLASS_OFFSET = 10
local OBJECT_REVEAL_OFFSET = 11

-- Sentinel class byte marking an empty object slot (real classes are 0-5).
local OBJECT_SENTINEL = 0xFF
local EMPTY_OBJECT_IDENTITY = string.char(
    OBJECT_SENTINEL, OBJECT_SENTINEL, OBJECT_SENTINEL)
local EMPTY_FLOOR_OBJECT = string.char(
    OBJECT_SENTINEL, OBJECT_SENTINEL, OBJECT_SENTINEL,
    OBJECT_SENTINEL, OBJECT_SENTINEL)

-- Holes and ladders. The game keeps them in a hand-authored ROM table, one
-- list per level boundary: a run of 3-byte entries (type, Y, X) ended by an
-- 0x80 sentinel. currentHoles points at the current level's ceiling list; the
-- next list after it is the floor list. Each boundary holds at most four.
local CURRENT_HOLES_HI = 0x0286
local CURRENT_HOLES_LO = 0x0287
local HOLE_LADDER_RAW_BYTES = 3
local HOLE_LADDER_CAPACITY = 4
local HOLE_LADDER_LIST_END = 0x80
local HOLES_LADDERS_BYTES = 2 * HOLE_LADDER_CAPACITY * HOLE_LADDER_RAW_BYTES
local HOLE_LADDER_SENTINEL = 0xFF
local EMPTY_HOLE_LADDER = string.char(
    HOLE_LADDER_SENTINEL, HOLE_LADDER_SENTINEL, HOLE_LADDER_SENTINEL)

-- Schema: ordered array of { name, addr, width } tables. The lit torch's three
-- fields use { name, torchOffset, width } instead of addr — they are read
-- through torchPtr, the game's pointer to the lit torch (0 = none lit).
-- The byte order is the shared contract with DaggorathStateSchema.FIELDS in Python.
local SCHEMA = {
    { name = "gameMode",             addr = 0x0277, width = 1 },
    { name = "atFloor",              addr = 0x0281, width = 1 },
    { name = "atCellX",              addr = 0x0214, width = 1 },
    { name = "atCellY",              addr = 0x0213, width = 1 },
    { name = "atHeading",            addr = 0x0223, width = 1 },
    { name = "ambientLightPhysical",   addr = 0x0226, width = 1 },
    { name = "ambientLightMagical",    addr = 0x0227, width = 1 },
    { name = "effectiveLightPhysical", addr = 0x026E, width = 1 },
    { name = "effectiveLightMagical",  addr = 0x026F, width = 1 },
    { name = "torchMinutes",         torchOffset = 6,  width = 1 },
    { name = "torchPhysicalLight",   torchOffset = 7,  width = 1 },
    { name = "torchMagicLight",      torchOffset = 8,  width = 1 },
    { name = "playerWeight",         addr = 0x0215, width = 2 },
    { name = "playerStrength",       addr = 0x0217, width = 2 },
    { name = "m0221",                addr = 0x0221, width = 2 },
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
local _mazeSnapshot = nil
local _creatureSnapshot = nil
local _objectSnapshot = nil
local _holesLaddersSnapshot = nil
local _frameSubscription = nil

local function _getMemorySpace()
    local cpu = nil
    for tag, device in pairs(manager.machine.devices) do
        if tag == ":maincpu" then cpu = device break end
    end
    if not cpu then return nil end

    for name, space in pairs(cpu.spaces) do
        if name == "program" then return space end
    end

    return nil
end

local function _isLive()
    local fn = _memory:read_u8(DISPLAY_FN_HI) * 256 + _memory:read_u8(DISPLAY_FN_LO)
    return fn == DISPLAY_LOOK or fn == DISPLAY_EXAMINE
end

-- Read all fields and serialize as a 21-byte string. Returns nil if any read
-- fails, so the caller can skip the frame instead of crashing.
local function _sampleState()
    local ok, result = pcall(function()
        -- Resolve the lit torch once: torchPtr is 0 when no torch is lit, in
        -- which case every torch field reports 0.
        local torchBase = _memory:read_u8(TORCH_PTR_HI) * 256
            + _memory:read_u8(TORCH_PTR_LO)

        local raw = {}
        for _, field in ipairs(SCHEMA) do
            if field.torchOffset then
                local value = 0
                if torchBase ~= 0 then
                    value = _memory:read_u8(torchBase + field.torchOffset)
                end
                raw[#raw + 1] = string.char(value)
            elseif field.width == 2 then
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

-- Read an object's identity bytes (class, proper type, reveal threshold).
local function _readObjectIdentity(slot)
    return string.char(
        _memory:read_u8(slot + OBJECT_CLASS_OFFSET),
        _memory:read_u8(slot + OBJECT_PROPER_OFFSET),
        _memory:read_u8(slot + OBJECT_REVEAL_OFFSET))
end

-- Read an object's next-chain pointer (slot + 0:1, big-endian).
local function _readObjectNextPointer(slot)
    return _memory:read_u8(slot) * 256 + _memory:read_u8(slot + 1)
end

-- Read the maze as a flat 1024-byte string (row-major, one byte per cell).
local function _sampleMaze()
    local ok, result = pcall(function()
        local bytes = {}
        for offset = 0, MAZE_BYTES - 1 do
            bytes[#bytes + 1] = string.char(_memory:read_u8(MAZE_START + offset))
        end
        return table.concat(bytes)
    end)
    if not ok then return nil end
    return result
end

-- Read the creature array as a flat 128-byte string: per slot, alive, type,
-- X, Y (the wire order matches the perceived channel).
local function _sampleCreatures()
    local ok, result = pcall(function()
        local bytes = {}
        for slot = 0, CREATURE_SLOTS - 1 do
            local base = CREATURE_ARRAY_START + slot * CREATURE_SLOT_BYTES
            bytes[#bytes + 1] = string.char(
                _memory:read_u8(base + CREATURE_ALIVE_OFFSET),
                _memory:read_u8(base + CREATURE_TYPE_OFFSET),
                _memory:read_u8(base + CREATURE_X_OFFSET),
                _memory:read_u8(base + CREATURE_Y_OFFSET))
        end
        return table.concat(bytes)
    end)
    if not ok then return nil end
    return result
end

-- Read the object record: two hands, then the pack, then the floor objects,
-- each a fixed-capacity sub-array with sentinel-filled empty slots.
local function _sampleObjects()
    local ok, result = pcall(function()
        local bytes = {}

        -- Hands: leftHand and rightHand pointers.
        local handPointers = {
            _memory:read_u8(LEFT_HAND_HI) * 256 + _memory:read_u8(LEFT_HAND_LO),
            _memory:read_u8(RIGHT_HAND_HI) * 256 + _memory:read_u8(RIGHT_HAND_LO),
        }
        for _, pointer in ipairs(handPointers) do
            if pointer == 0 then
                bytes[#bytes + 1] = EMPTY_OBJECT_IDENTITY
            else
                bytes[#bytes + 1] = _readObjectIdentity(pointer)
            end
        end

        -- Pack: walk the firstPackObject chain (LIFO).
        local packPointer = _memory:read_u8(FIRST_PACK_HI) * 256
            + _memory:read_u8(FIRST_PACK_LO)
        for _ = 1, PACK_CAPACITY do
            if packPointer == 0 then
                bytes[#bytes + 1] = EMPTY_OBJECT_IDENTITY
            else
                bytes[#bytes + 1] = _readObjectIdentity(packPointer)
                packPointer = _readObjectNextPointer(packPointer)
            end
        end

        -- Floor: arena scan for location 0 on the current level.
        local nextObjSlot = _memory:read_u8(NEXT_OBJ_SLOT_HI) * 256
            + _memory:read_u8(NEXT_OBJ_SLOT_LO)
        local currentLevel = _memory:read_u8(CURRENT_LEVEL_ADDR)
        local floorCount = 0
        local slot = OBJECT_ARRAY_BASE
        while slot < nextObjSlot and floorCount < FLOOR_OBJECT_CAPACITY do
            if _memory:read_u8(slot + OBJECT_LOCATION_OFFSET) == 0
                and _memory:read_u8(slot + OBJECT_LEVEL_OFFSET) == currentLevel then
                bytes[#bytes + 1] = _readObjectIdentity(slot)
                bytes[#bytes + 1] = string.char(
                    _memory:read_u8(slot + OBJECT_X_OFFSET),
                    _memory:read_u8(slot + OBJECT_Y_OFFSET))
                floorCount = floorCount + 1
            end
            slot = slot + OBJECT_SLOT_BYTES
        end
        for _ = floorCount, FLOOR_OBJECT_CAPACITY - 1 do
            bytes[#bytes + 1] = EMPTY_FLOOR_OBJECT
        end

        return table.concat(bytes)
    end)
    if not ok then return nil end
    return result
end

-- Read the holes/ladders record: the ceiling list, then the floor list, each
-- a run of (type, Y, X) entries ended by the game's 0x80 sentinel and capped
-- at HOLE_LADDER_CAPACITY, with empty slots sentinel-filled.
local function _sampleHolesLadders()
    local ok, result = pcall(function()
        local bytes = {}
        local pointer = _memory:read_u8(CURRENT_HOLES_HI) * 256
            + _memory:read_u8(CURRENT_HOLES_LO)

        for _ = 1, 2 do
            local count = 0
            while true do
                local holeType = _memory:read_u8(pointer)
                pointer = pointer + 1
                if holeType >= HOLE_LADDER_LIST_END then
                    break
                end
                if count < HOLE_LADDER_CAPACITY then
                    bytes[#bytes + 1] = string.char(
                        holeType,
                        _memory:read_u8(pointer),
                        _memory:read_u8(pointer + 1))
                end
                pointer = pointer + 2
                count = count + 1
            end
            for _ = count, HOLE_LADDER_CAPACITY - 1 do
                bytes[#bytes + 1] = EMPTY_HOLE_LADDER
            end
        end

        return table.concat(bytes)
    end)
    if not ok then return nil end
    return result
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

-- Write one fixed-size world record to the FIFO in a single call.
local function _writeWorldRecord(kind, payload)
    local ok = pcall(function()
        _stateFile:write(kind .. payload)
        _stateFile:flush()
    end)
    if not ok then
        print("[state] Failed to write record " .. kind)
    end
end

-- Per-frame notifier: sample, dedup, and write tagged records.
local function _onFrame()
    _framesElapsed = _framesElapsed + 1

    if manager.machine.paused then
        return
    end

    -- Re-acquire the memory space every frame: MAME rebuilds the machine on
    -- reset, invalidating the previously cached space.
    _memory = _getMemorySpace()
    if not _memory then
        return
    end

    -- Skip frames that aren't multiples of the sampling rate
    if _framesElapsed % _frameSamplingRate ~= 0 then
        return
    end

    -- Readiness gate: only sample during live play (LOOK or EXAMINE).
    if not _isLive() then
        return
    end

    local frame = _sampleState()
    if not frame then
        return
    end

    local stateChanged = (_stateSnapshot == nil) or (frame ~= _stateSnapshot)

    local pixels = _readCommandAreaPixels()
    local comColor = _memory:read_u8(COM_COLOR)
    local pixelChanged = (_pixelSnapshot == nil)
        or (pixels ~= _pixelSnapshot)
        or (comColor ~= _comColorSnapshot)

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

    -- World channels: maze, creatures, and objects are each compared to their
    -- own snapshot and written only when they differ.
    local maze = _sampleMaze()
    if maze and maze ~= _mazeSnapshot then
        _writeWorldRecord("M", maze)
        _mazeSnapshot = maze
    end

    local creatures = _sampleCreatures()
    if creatures and creatures ~= _creatureSnapshot then
        _writeWorldRecord("C", creatures)
        _creatureSnapshot = creatures
    end

    local objects = _sampleObjects()
    if objects and objects ~= _objectSnapshot then
        _writeWorldRecord("O", objects)
        _objectSnapshot = objects
    end

    local holesLadders = _sampleHolesLadders()
    if holesLadders and holesLadders ~= _holesLaddersSnapshot then
        _writeWorldRecord("H", holesLadders)
        _holesLaddersSnapshot = holesLadders
    end
end

-- Public: start watching game state.
function state.beginWatching(stateFile, config)
    _stateFile = stateFile
    _framesElapsed = 0
    _memory = nil
    _stateSnapshot = nil
    _pixelSnapshot = nil
    _comColorSnapshot = nil
    _mazeSnapshot = nil
    _creatureSnapshot = nil
    _objectSnapshot = nil
    _holesLaddersSnapshot = nil

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
    _mazeSnapshot = nil
    _creatureSnapshot = nil
    _objectSnapshot = nil
    _holesLaddersSnapshot = nil
end

return state