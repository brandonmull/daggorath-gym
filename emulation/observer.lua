-- RAM observer for Dungeons of Daggorath
-- Captures game state from emulated memory and formats it as JSON.

local RAM = {
    heartCounter    = 0x02AE,  heartCounterRel = 0x02AF,
    fainting        = 0x0228,  wizardDead      = 0x022B,
    playerX         = 0x020F,  playerY         = 0x0210,
    playerHP        = 0x0227,  playerStamina   = 0x0229,
    gameState       = 0x0226,  activeObject    = 0x0253,
}

local OBSERVE_INTERVAL = 60

local state_sock = nil
local memspace = nil
local frame = 0
local sent = 0

local observer = {}

function observer.set_socket(sock)
    state_sock = sock
end

function observer.tick()
    frame = frame + 1
    if frame % OBSERVE_INTERVAL ~= 0 then return end

    -- Lazy-init memory space inside frame callback (safe)
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
        pcall(function() state_sock:write(msg) end)
        sent = sent + 1
        print("[Observer] [" .. sent .. "] observation")
    else
        sent = sent + 1
        pcall(function() state_sock:write('{"event":"ping","count":' .. sent .. '}\n') end)
        print("[Observer] [" .. sent .. "] ping (no CPU)")
    end
end

return observer