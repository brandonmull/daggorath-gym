-- Test: require() a sibling module in MAME's embedded Lua.
-- Assumes AUTOBOOT_DIR env var points to this script's directory.

-- Module path setup — must happen before any require() calls
local emu_dir = os.getenv("AUTOBOOT_DIR")
if emu_dir then
    package.path = emu_dir .. "/?.lua;" .. package.path
end

local HOST, PORT = "127.0.0.1", 15000

local sock = emu.file("w")
if sock:open("socket." .. HOST .. ":" .. PORT) then
    print("[Test] socket error")
    return
end

local ok, result = pcall(function()
    return require("hello")
end)

if ok then
    pcall(function() sock:write("PASS\n") end)
else
    pcall(function() sock:write("FAIL\n") end)
end
print("[Test] " .. (ok and "PASS" or "FAIL"))