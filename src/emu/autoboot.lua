-- Set up paths for LuaSocket and other modules
local current_dir = emu.subst_env(manager.machine.options.value("homepath"))
print("Home path: " .. current_dir)

-- Determine common paths where LuaSocket might be installed
local home_dir = os.getenv("HOME") or os.getenv("USERPROFILE")
local plugins_dir = home_dir .. "/.mame/plugins"
local ws_dir = emu.subst_env(manager.machine.options.value("pluginspath"))

print("Plugins directory: " .. plugins_dir)
print("Workspace plugins: " .. ws_dir)

-- Define all potential paths where modules could be found
local potential_paths = {
    -- Current directory
    "./?.lua",
    "./?/init.lua",
    
    -- Standard Lua paths
    "./share/lua/5.3/?.lua",
    "./share/lua/5.3/?/init.lua",
    
    -- MAME plugins directory
    plugins_dir .. "/?.lua",
    plugins_dir .. "/?/init.lua",
    plugins_dir .. "/share/lua/5.3/?.lua",
    plugins_dir .. "/share/lua/5.3/?/init.lua",
    
    -- MAME workspace plugins
    ws_dir .. "/?.lua",
    ws_dir .. "/?/init.lua"
}

local potential_cpaths = {
    -- Current directory
    "./?.so",
    "./?/init.so",
    "./lib/lua/5.3/?.so",
    "./lib/lua/5.3/socket/?.so",
    
    -- MAME plugins directory
    plugins_dir .. "/?.so",
    plugins_dir .. "/lib/lua/5.3/?.so",
    plugins_dir .. "/lib/lua/5.3/socket/?.so",
    
    -- MAME workspace plugins
    ws_dir .. "/?.so",
    ws_dir .. "/lib/lua/5.3/?.so"
}

-- Print socket-specific paths for verification
print("Socket path to check: " .. plugins_dir .. "/lib/lua/5.3/socket/core.so")

-- Add all potential paths to package.path
for _, path in ipairs(potential_paths) do
    package.path = package.path .. ";" .. path
end

-- Add all potential cpaths to package.cpath
for _, cpath in ipairs(potential_cpaths) do
    package.cpath = package.cpath .. ";" .. cpath
end

print("Lua path: " .. package.path)
print("Lua cpath: " .. package.cpath)

-- Require the necessary modules with error handling
local observer, socket, url
local success, result = pcall(function()
    observer = require("observer")
    socket = require("socket")
    url = require("socket.url")
    return true
end)

if not success then
    print("Error loading modules: " .. tostring(result))
    return
end

-- Create TCP socket for communication
local client = socket.tcp()
client:settimeout(0.1) -- Non-blocking with short timeout

-- Connect function with error handling
local function connect_socket()
    local success, err = client:connect("127.0.0.1", 15000)
    if success then
        print("Successfully connected to 127.0.0.1:15000")
        return true
    elseif err ~= "timeout" then
        print("Connection error: " .. tostring(err))
        return false
    end
    return false
end

-- Try to connect once at startup
connect_socket()

-- Get the CPU memory space
local space = manager.machine.devices[":maincpu"].spaces["program"]

-- Register a frame callback that monitors the game state
local frame_callback = observer.create(space, client, url)
emu.register_frame(function()
    -- Check connection status and try to reconnect if needed
    if not client:getpeername() then
        connect_socket()
    end
    
    -- Call the observer frame function
    pcall(frame_callback)
end)