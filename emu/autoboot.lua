-- Simple autoboot script with observer for Daggorath
print("Daggorath autoboot script starting...")

-- Import the paths module
local paths = require("paths")
local observer = require("observer")

-- Set up basic socket functionality
local socket = require("socket")

-- Create TCP socket for communication
local client = socket.tcp()
client:settimeout(paths.socket.timeout)

-- Connect function with error handling
local function connect_socket()
    local host = paths.socket.host
    local port = paths.socket.port
    
    print("Attempting to connect to " .. host .. ":" .. port .. "...")
    local success, err = client:connect(host, port)
    if success then
        print("Successfully connected to " .. host .. ":" .. port)
        
        -- Send verification message
        local message = '{"event":"gameStarted","status":"ready"}'
        client:send(message .. "\n")
        print("Sent message: " .. message)
        return true
    else
        print("Connection error: " .. tostring(err))
        return false
    end
end

-- Try to connect at startup
local connected = connect_socket()

-- Setup the observer to monitor game state
local function setup_observer()
    -- Only set up observer if we're connected
    if not connected then
        print("Not setting up observer due to connection issues")
        return
    end
    
    print("Setting up game state observer...")
    
    -- Get the CPU memory space
    local cpu = manager.machine.devices[":maincpu"]
    if not cpu then
        print("ERROR: CPU not found, cannot set up observer")
        return
    end
    
    local space = cpu.spaces["program"]
    if not space then
        print("ERROR: Program space not found, cannot set up observer")
        return
    end
    
    -- Create the observer function
    local observer_callback = observer.create(space, client, nil)
    
    -- Register a periodic callback to run the observer
    emu.register_periodic(function()
        -- Safely call the observer function to avoid crashes
        local status, err = pcall(observer_callback)
        if not status then
            print("Observer error: " .. tostring(err))
        end
    end, 1000) -- Update every 1000ms (1 second)
    
    print("Observer setup complete")
end

-- Set up the observer
setup_observer()

print("Autoboot script completed")