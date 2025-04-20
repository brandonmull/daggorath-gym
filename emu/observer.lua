-- RAM addresses for the game variables
local RAM_HEARTCOUNTER = 0x02AE
local RAM_HEARTCOUNTERREL = 0x02AF
local RAM_FAINTING = 0x0228
local RAM_WIZARDDEAD = 0x022B
-- Additional RAM addresses for monitoring
local RAM_PLAYER_X = 0x020F
local RAM_PLAYER_Y = 0x0210
local RAM_PLAYER_HP = 0x0227
local RAM_PLAYER_STAMINA = 0x0229
local RAM_GAME_STATE = 0x0226
local RAM_ACTIVE_OBJECT = 0x0253

local function create(space, socket, url)
    socket:connect("127.0.0.1", 15000)
    socket:send("{\"event\":\"observerCreated\",\"message\":\"Observer initialized and connected\"}\n")
    
    -- Print debugging information on startup
    local cpu = manager.machine.devices[":maincpu"]
    print("Observer created")
    print("CPU state:", cpu and "Found" or "Not found")
    print("Memory space:", space and "Found" or "Not found")
    
    return function()
        -- Basic monitoring variables
        local heartCounter = space:read_u8(RAM_HEARTCOUNTER)
        local heartCounterRel = space:read_u8(RAM_HEARTCOUNTERREL)
        local fainting = space:read_u8(RAM_FAINTING)
        local wizardDead = space:read_u8(RAM_WIZARDDEAD)
        
        -- Additional monitoring variables
        local playerX = space:read_u8(RAM_PLAYER_X)
        local playerY = space:read_u8(RAM_PLAYER_Y)
        local playerHP = space:read_u8(RAM_PLAYER_HP)
        local playerStamina = space:read_u8(RAM_PLAYER_STAMINA)
        local gameState = space:read_u8(RAM_GAME_STATE)
        local activeObject = space:read_u8(RAM_ACTIVE_OBJECT)
        
        local message = string.format(
            "{" ..
                "\"event\":\"observerTriggered\"," ..
                "\"timestamp\":\"%s\"," ..
                "\"heartCounter\":%d," ..
                "\"heartCounterRel\":%d," ..
                "\"fainting\":%d," ..
                "\"wizardDead\":%d," ..
                "\"playerX\":%d," ..
                "\"playerY\":%d," ..
                "\"playerHP\":%d," ..
                "\"playerStamina\":%d," ..
                "\"gameState\":%d," ..
                "\"activeObject\":%d" ..
            "}\n",
            os.date("%Y-%m-%d %H:%M:%S"),
            heartCounter,
            heartCounterRel,
            fainting,
            wizardDead,
            playerX,
            playerY,
            playerHP,
            playerStamina,
            gameState,
            activeObject
        )

        -- Debug output to MAME console
        print("Observer data: " .. message)
        socket:send(message)
    end
end

return { create = create }