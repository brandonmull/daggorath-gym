-- RAM addresses for the game variables
local RAM_HEARTCOUNTER = 0x02AE
local RAM_HEARTCOUNTERREL = 0x02AF
local RAM_FAINTING = 0x0228
local RAM_WIZARDDEAD = 0x022B

local function create(space, socket, url)
    socket:connect("127.0.0.1", 15000)
    socket:send("{\"event\":\"observerCreated\"}\n")

    return function()
        local heartCounter = space:read_u8(RAM_HEARTCOUNTER)
        local heartCounterRel = space:read_u8(RAM_HEARTCOUNTERREL)
        local fainting = space:read_u8(RAM_FAINTING)
        local wizardDead = space:read_u8(RAM_WIZARDDEAD)
        local message = string.format(
            "{" ..
                "\"event\":\"observerTriggered\"," ..
                "\"heartCounter\":%d," ..
                "\"heartCounterRel\":%d," ..
                "\"fainting\":%d," ..
                "\"wizardDead\":%d," ..
            "}\n",
            heartCounter,
            heartCounterRel,
            fainting,
            wizardDead
        )

        -- print(message)
        socket:send(message)
    end
end

return { create = create }