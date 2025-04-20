local function enter()
    input.set_value("P1_START", 1)  -- Simulate pressing the Enter key
    emu.wait(0.1)  -- Wait for 100 milliseconds
    input.set_value("P1_START", 0)  -- Release the Enter key
end

-- Keyboard arrows/directions
local function up()
    input.set_value("P1_UP", 1) 
    emu.wait(0.1)
    input.set_value("P1_UP", 0)
end

local function down()
    input.set_value("P1_DOWN", 1)
    emu.wait(0.1)
    input.set_value("P1_DOWN", 0)
end

local function left()
    input.set_value("P1_LEFT", 1)
    emu.wait(0.1)
    input.set_value("P1_LEFT", 0)
end

local function right()
    input.set_value("P1_RIGHT", 1)
    emu.wait(0.1)
    input.set_value("P1_RIGHT", 0)
end

-- Game-specific commands - letter keys for Daggorath commands
-- These map to common commands in the game
local function attack()
    -- Letter A for attack
    input.set_value("KEYCODE_A", 1)
    emu.wait(0.1)
    input.set_value("KEYCODE_A", 0)
end

local function move()
    -- Letter M for move
    input.set_value("KEYCODE_M", 1)
    emu.wait(0.1)
    input.set_value("KEYCODE_M", 0)
end

local function look()
    -- Letter L for look
    input.set_value("KEYCODE_L", 1)
    emu.wait(0.1)
    input.set_value("KEYCODE_L", 0)
end

local function climb()
    -- Letter C for climb
    input.set_value("KEYCODE_C", 1)
    emu.wait(0.1)
    input.set_value("KEYCODE_C", 0)
end

local function use()
    -- Letter U for use
    input.set_value("KEYCODE_U", 1)
    emu.wait(0.1)
    input.set_value("KEYCODE_U", 0)
end

local function incant()
    -- Letter I for incant
    input.set_value("KEYCODE_I", 1)
    emu.wait(0.1)
    input.set_value("KEYCODE_I", 0)
end

-- Debugging function - prints detailed input state
local function print_input_state()
    local state = {}
    state["P1_START"] = input.get_value("P1_START")
    state["P1_UP"] = input.get_value("P1_UP")
    state["P1_DOWN"] = input.get_value("P1_DOWN")
    state["P1_LEFT"] = input.get_value("P1_LEFT")
    state["P1_RIGHT"] = input.get_value("P1_RIGHT")
    state["KEYCODE_A"] = input.get_value("KEYCODE_A")
    state["KEYCODE_M"] = input.get_value("KEYCODE_M")
    state["KEYCODE_L"] = input.get_value("KEYCODE_L")
    state["KEYCODE_C"] = input.get_value("KEYCODE_C")
    state["KEYCODE_U"] = input.get_value("KEYCODE_U")
    state["KEYCODE_I"] = input.get_value("KEYCODE_I")
    
    print("Current input state:")
    for k, v in pairs(state) do
        print("  " .. k .. ": " .. tostring(v))
    end
end

return { 
    enter = enter,
    up = up,
    down = down,
    left = left,
    right = right,
    attack = attack,
    move = move,
    look = look,
    climb = climb,
    use = use,
    incant = incant,
    print_input_state = print_input_state
}