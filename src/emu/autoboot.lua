local lfs = require("lfs")
local dir = lfs.currentdir() .. "\\lua"
lfs.chdir(dir)
print("lua directory: " .. dir)

-- Update the package paths to include the directories where LuaSocket is installed
package.path = package.path .. ";./?.lua;./share/lua/5.3/?.lua;"
package.cpath = package.cpath .. ";./lib/lua/5.3/?.so"

-- Require the LuaSocket module
local observer = require("observer")
local socket = require("socket")
local url = require("socket.url")
local space = manager.machine.devices[":maincpu"].spaces["program"]

emu.register_frame(observer.create(space, socket, url))
-- emu.add_machine_frame_notifier(observer)