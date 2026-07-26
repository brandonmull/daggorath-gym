-- Daggorath autoboot — self-contained script, no external requires.
-- Two unidirectional emu.file sockets to Python.
--   Port 15000 = state (w)
--   Port 15001 = actions (r)

local HOST, STATE, ACTION = "127.0.0.1", 15000, 15001

-- ---- RAM addresses --------------------------------------------------------
local RAM = {
    heartCounter    = 0x02AE,  heartCounterRel = 0x02AF,
    fainting        = 0x0228,  wizardDead      = 0x022B,
    playerX         = 0x020F,  playerY         = 0x0210,
    playerHP        = 0x0227,  playerStamina   = 0x0229,
    gameState       = 0x0226,  activeObject    = 0x0253,
}

-- ---- key mappings ---------------------------------------------------------
local KEYS = {
    ATTACK  = "KEYCODE_A",  MOVE    = "KEYCODE_M",
    LOOK    = "KEYCODE_L",  CLIMB   = "KEYCODE_C",
    USE     = "KEYCODE_U",  INCANT  = "KEYCODE_I",
    UP      = "P1_UP",      DOWN    = "P1_DOWN",
    LEFT    = "P1_LEFT",    RIGHT   = "P1_RIGHT",
    ENTER   = "P1_START",
}

-- ---- sockets --------------------------------------------------------------
print("[Autoboot] Opening state socket " .. STATE)
local sock_w = emu.file("w")
local err = sock_w:open("socket." .. HOST .. ":" .. STATE)
if err then print("[Autoboot] state err: " .. tostring(err)); return end

print("[Autoboot] Opening action socket " .. ACTION)
local sock_r = emu.file("r")
local err2 = sock_r:open("socket." .. HOST .. ":" .. ACTION)
if err2 then print("[Autoboot] action err: " .. tostring(err2)); return end

pcall(function() sock_w:write('{"event":"gameStarted"}\n') end)
print("[Autoboot] Sockets ready")

-- ---- main loop ------------------------------------------------------------
local frame, sent, memspace = 0, 0, nil
local held_key, hold_frames = nil, 0
local HOLD = 3  -- frames to hold a key down

emu.add_machine_frame_notifier(function()
    frame = frame + 1

    -- ---------- key release (frame-counted) --------------------------------
    if held_key then
        hold_frames = hold_frames - 1
        if hold_frames <= 0 then
            input.set_value(held_key, 0)
            held_key = nil
        end
    end

    -- ---------- read action commands ---------------------------------------
    if held_key == nil then  -- only accept new actions when not holding a key
        local raw = sock_r:read(256)
        if raw and #raw > 0 then
            local cmd_str = raw:gsub("\r?\n$", "")
            if #cmd_str > 0 then
                local action = string.match(cmd_str, '"action":"([^"]+)"')
                if action then
                    local key = KEYS[action]
                    if key then
                        input.set_value(key, 1)
                        held_key = key
                        hold_frames = HOLD
                        print("[Autoboot] Key: " .. action)
                    end
                end
            end
        end
    end

    -- ---------- observer (every 60 frames) ---------------------------------
    if frame % 60 == 0 then
        if not memspace then
            local cpu = manager.machine.devices[":maincpu"]
            if cpu then memspace = cpu.spaces["program"] end
        end

        if memspace then
            local msg = string.format(
                '{"event":"observerTriggered","timestamp":"%s","heartCounter":%d,"heartCounterRel":%d,"fainting":%d,"wizardDead":%d,"playerX":%d,"playerY":%d,"playerHP":%d,"playerStamina":%d,"gameState":%d,"activeObject":%d}\n',
                os.date("%Y-%m-%d %H:%M:%S"),
                memspace:read_u8(RAM.heartCounter),    memspace:read_u8(RAM.heartCounterRel),
                memspace:read_u8(RAM.fainting),        memspace:read_u8(RAM.wizardDead),
                memspace:read_u8(RAM.playerX),         memspace:read_u8(RAM.playerY),
                memspace:read_u8(RAM.playerHP),        memspace:read_u8(RAM.playerStamina),
                memspace:read_u8(RAM.gameState),       memspace:read_u8(RAM.activeObject)
            )
            pcall(function() sock_w:write(msg) end)
            sent = sent + 1
        else
            sent = sent + 1
            pcall(function() sock_w:write('{"event":"ping","count":' .. sent .. '}\n') end)
        end
    end
end)

print("[Autoboot] Running")