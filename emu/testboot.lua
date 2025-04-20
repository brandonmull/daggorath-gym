-- Test script for Daggorath inputs and debugging
print("Daggorath test script starting...")

-- Import the paths module
local paths = require("paths")
local commands = require("commands")
local observer = require("observer")

-- Create TCP socket for communication
local socket = require("socket")
local client = socket.tcp()
client:settimeout(paths.socket.timeout)

-- Connect to debug socket
local function connect_socket()
    local host = paths.socket.host
    local port = paths.socket.port
    
    print("Attempting to connect to " .. host .. ":" .. port .. "...")
    local success, err = client:connect(host, port)
    if success then
        print("Successfully connected to " .. host .. ":" .. port)
        return true
    else
        print("Connection error: " .. tostring(err))
        return false
    end
end

-- Debug function to dump memory regions
local function dump_memory_regions()
    print("Available memory regions:")
    for name, region in pairs(manager.machine.memory.regions) do
        print("  - " .. name .. " size: " .. tostring(region:size()))
    end
end

-- Debug function to dump system info
local function dump_system_info()
    print("System information:")
    print("  - Machine name: " .. manager.machine.system.name)
    print("  - Description: " .. manager.machine.system.description)
    print("  - Year: " .. manager.machine.system.year)
    print("  - Manufacturer: " .. manager.machine.system.manufacturer)
end

-- Get CPU memory space
local function get_memory_space()
    local cpu = manager.machine.devices[":maincpu"]
    if not cpu then
        print("ERROR: CPU not found")
        return nil
    end
    
    local space = cpu.spaces["program"]
    if not space then
        print("ERROR: Program space not found")
        return nil
    end
    
    return space
end

-- Connect to socket
local connected = connect_socket()
if not connected then
    print("Could not connect to socket, continuing without connection")
end

-- Dump debug information
print("Starting debug information dump...")
dump_system_info()
dump_memory_regions()

-- Test input commands
local function test_inputs()
    print("Testing input commands...")
    
    -- Get current input state
    commands.print_input_state()
    
    -- Test each command with a short delay between them
    print("Pressing ENTER")
    commands.enter()
    emu.wait(1)
    
    print("Pressing UP arrow")
    commands.up()
    emu.wait(1)
    
    print("Pressing DOWN arrow")
    commands.down()
    emu.wait(1)
    
    print("Pressing LEFT arrow")
    commands.left()
    emu.wait(1)
    
    print("Pressing RIGHT arrow")
    commands.right()
    emu.wait(1)
    
    print("Input test complete")
    commands.print_input_state()
end

-- Set up periodic observer
local space = get_memory_space()
if space then
    print("Setting up memory observer...")
    local observer_callback = observer.create(space, client, nil)
    
    -- Register periodic callback to observe memory
    emu.register_periodic(function()
        observer_callback()
    end, 1000) -- Run every 1000ms
end

-- Run input tests after a delay
emu.register_start(function()
    print("Machine started, scheduling tests...")
    emu.register_frame_done(function()
        print("Frame done callback registered")
        emu.wait(3)
        test_inputs()
        return false -- Don't run again
    end, true) -- Run once
end)

print("Test script setup complete")


