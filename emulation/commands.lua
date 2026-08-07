-- Command dispatch module for Dungeons of Daggorath.
-- Receives 1-byte command indices from the command socket, looks up the
-- corresponding command phrase, and dispatches it to the game's text parser.
--
-- Public API: commands.beginProcessing(socket)
--   socket: emu.file "r" socket (opened by autoboot)

local commands = {}

-- Grammar constants (alphabetical order)
local COMMAND_WORDS = { "ATTACK", "CLIMB", "DROP", "MOVE", "REVEAL", "STOW", "TURN", "USE" }

local COMMAND_DIRECTIONS = {
    ATTACK  = { "LEFT", "RIGHT" },
    CLIMB   = { "UP", "DOWN" },
    DROP    = { "LEFT", "RIGHT" },
    MOVE    = { "BACK", "LEFT", "RIGHT" },
    REVEAL  = { "LEFT", "RIGHT" },
    STOW    = { "LEFT", "RIGHT" },
    TURN    = { "LEFT", "RIGHT", "AROUND" },
    USE     = { "LEFT", "RIGHT" },
}

local OBJECT_CLASSES = { "FLASK", "RING", "SCROLL", "SHIELD", "SWORD", "TORCH" }

local OBJECT_PROPER_NAMES = {
    FLASK  = { "ABYE", "EMPTY", "HALE", "THEWS" },
    RING   = { "ENERGY", "FINAL", "FIRE", "GOLD", "ICE", "JOULE", "RIME", "SUPREME", "VULCAN" },
    SCROLL = { "SEER", "VISION" },
    SHIELD = { "BRONZE", "LEATHER", "MITHRIL" },
    SWORD  = { "ELVISH", "IRON", "WOODEN" },
    TORCH  = { "DEAD", "LUNAR", "PINE", "SOLAR" },
}

-- Build the 31 object specifiers: bare class, then each proper name + class.
local function _build_object_specifiers()
    local specifiers = {}
    for _, class in ipairs(OBJECT_CLASSES) do
        specifiers[#specifiers + 1] = class
        for _, name in ipairs(OBJECT_PROPER_NAMES[class]) do
            specifiers[#specifiers + 1] = name .. " " .. class
        end
    end
    return specifiers
end

-- Build the full ordered list of 154 command phrases.
-- The order is the shared contract with commands.py.
local function _build_command_phrases()
    local phrases = {}
    local specifiers = _build_object_specifiers()

    -- Direction-bearing commands (order matches command table §1)
    local direction_words = {
        "MOVE", "TURN", "CLIMB",
        "ATTACK", "USE", "DROP", "STOW", "REVEAL",
    }

    for _, word in ipairs(direction_words) do
        local dirs = COMMAND_DIRECTIONS[word]
        if word == "MOVE" then
            -- MOVE has a bare form plus directions
            phrases[#phrases + 1] = word
        end
        for _, dir in ipairs(dirs) do
            phrases[#phrases + 1] = word .. " " .. dir
        end
    end

    -- Standalone (no direction, no specifier)
    phrases[#phrases + 1] = "EXAMINE"
    phrases[#phrases + 1] = "LOOK"

    -- GET and PULL (direction × 31 specifiers each)
    for _, word in ipairs({ "GET", "PULL" }) do
        for _, dir in ipairs({ "LEFT", "RIGHT" }) do
            for _, spec in ipairs(specifiers) do
                phrases[#phrases + 1] = word .. " " .. dir .. " " .. spec
            end
        end
    end

    -- INCANT (ring proper names, all except EMPTY)
    for _, name in ipairs(OBJECT_PROPER_NAMES["RING"]) do
        if name ~= "EMPTY" then
            phrases[#phrases + 1] = "INCANT " .. name
        end
    end

    return phrases
end

local COMMAND_PHRASES = _build_command_phrases()

-- Internal state
local _socket = nil
local _keyboard = nil
local _inputPrimed = false

-- Per-frame notifier: prime on first frame, then read commands.
local function _onFrame()
    -- Prime the CoCo's input buffer on the first frame
    if not _inputPrimed then
        _inputPrimed = true
        _keyboard:post("\r")
        _keyboard:post("\r")
        return
    end

    -- Non-blocking read of one byte
    local raw = _socket:read(1)
    if not raw or #raw == 0 then
        return
    end

    local commandIndex = string.byte(raw)

    -- Lua is 1-indexed; Python sends 0-based indices
    local luaIndex = commandIndex + 1

    if luaIndex < 1 or luaIndex > #COMMAND_PHRASES then
        print("[commands] Invalid command index: " .. commandIndex)
        return
    end

    _keyboard:post(COMMAND_PHRASES[luaIndex] .. "\r")
end

-- Public: start processing commands.
function commands.beginProcessing(socket)
    _socket = socket
    _keyboard = manager.machine.natkeyboard
    if not _keyboard then
        print("[commands] ERROR: natkeyboard port not available")
        return
    end
    _inputPrimed = false

    emu.add_machine_frame_notifier(_onFrame)
end

return commands