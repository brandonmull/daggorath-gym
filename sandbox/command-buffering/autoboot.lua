-- Command buffering sandbox: post commands every frame and observe
-- the input ring buffer.
--
-- RAM addresses (from emulation/docs/ram.md):
--   02BC       inputHead    next read index
--   02BD       inputTail    next write index
--   02D1:02F0  inputBuf     32-byte ring buffer
--   0277       gameMode     00=live, FF=demo

local HOST, PORT = "127.0.0.1", 15000

local emu_dir = os.getenv("AUTOBOOT_DIR")
if emu_dir then
    package.path = emu_dir .. "/?.lua;" .. package.path
end

local sock = emu.file("w")
if sock:open("socket." .. HOST .. ":" .. PORT) then
    print("[Buffer] socket error"); return
end

local mem = nil
local frame = 0
local nk = manager.machine.natkeyboard
local phase = "prime"     -- prime | wait_live | flood
local flood_start = 0
local count = 0
local log_frame = 0

local CMDS = { "PULL RIGHT WOODEN SWORD\r", "STOW RIGHT WOODEN SWORD\r" }

local function log(msg)
    print("[Buffer] " .. msg)
    pcall(function() sock:write(msg .. "\n") end)
end

emu.add_machine_frame_notifier(function()
    frame = frame + 1
    if not mem then
        local cpu = manager.machine.devices[":maincpu"]
        if cpu then mem = cpu.spaces["program"] end
        if not mem then return end
    end

    local head = mem:read_u8(0x02BC)
    local tail = mem:read_u8(0x02BD)
    local mode = mem:read_u8(0x0277)
    local fill = (tail - head) % 256

    -- Phase 1: prime
    if phase == "prime" then
        nk:post("\r")
        nk:post("\r")
        phase = "wait_live"
        log(string.format("PRIME:%d", frame))
        return
    end

    -- Phase 2: wait for live gameplay
    if phase == "wait_live" then
        if mode == 0x00 then
            phase = "flood"
            flood_start = frame
            log(string.format("LIVE:%d,head=%d,tail=%d", frame, head, tail))
        end
        return
    end

    -- Phase 3: flood — post alternating commands every frame
    if phase == "flood" then
        count = count + 1
        local idx = (count % 2) + 1   -- Lua is 1-indexed
        nk:post(CMDS[idx])
    end

    -- Periodic buffer state
    if frame - log_frame >= 10 then
        log_frame = frame
        log(string.format("%d,head=%d,tail=%d,fill=%d,count=%d",
            frame, head, tail, fill, count))
    end
end)

log("READY")