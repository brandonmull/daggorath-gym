-- Simple autoboot script that connects to a socket and sends a verification message
print("Daggorath autoboot script starting...")

-- Import the paths module
local paths = require("paths")

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
        
        -- Close connection
        client:close()
        print("Connection closed")
        return true
    else
        print("Connection error: " .. tostring(err))
        return false
    end
end

-- Try to connect once at startup
connect_socket()

print("Autoboot script completed")