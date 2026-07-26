-- Test: dual socket — "w" on 15000 (known stable) + "r" on 15001 (testing read-only)
print("[MAME Lua] Opening write socket on 15000 ...")
local sock_w = emu.file("w")
local err_w = sock_w:open("socket.127.0.0.1:15000")
if err_w then
    print("[MAME Lua] ERROR w: " .. tostring(err_w))
    return
end
print("[MAME Lua] Write socket OK")

print("[MAME Lua] Opening read socket on 15001 ...")
local sock_r = emu.file("r")
local err_r = sock_r:open("socket.127.0.0.1:15001")
if err_r then
    print("[MAME Lua] ERROR r: " .. tostring(err_r))
    return
end
print("[MAME Lua] Read socket OK")

sock_w:write("{\"event\":\"hello\"}\n")
print("[MAME Lua] Sent: hello")

local frame = 0
local count = 0

emu.add_machine_frame_notifier(function()
    frame = frame + 1
    if frame % 60 == 0 then
        count = count + 1
        local msg = string.format("{\"event\":\"ping\",\"count\":%d}\n", count)
        local ok = pcall(function() sock_w:write(msg) end)
        if ok then
            print(string.format("[MAME Lua] [%d] Sent ping", count))
        end
    end

    -- Read from action socket (non-blocking, just test it doesn't crash)
    local response = sock_r:read(256)
    if response and #response > 0 then
        print(string.format("[MAME Lua] Read: %s", response:gsub("\r?\n$", "")))
    end
end)

print("[MAME Lua] Dual-socket test running")