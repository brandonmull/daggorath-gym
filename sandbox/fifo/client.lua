-- FIFO write stress test: uses standard Lua io.open("w") on named pipe.
-- Tests whether sustained FIFO writes at high frame rates survive
-- without the freezing/crashing that emu.file("w") experiences.
--
-- State FIFO: Lua opens for writing, sends pings at frame counter speed
-- No read side — command channel stays on emu.file("r") (stable, non-blocking)

local STATE_FIFO = os.getenv("STATE_FIFO") or "/tmp/daggorath-fifo-state"

print("[FIFO-Lua] Opening state FIFO: " .. STATE_FIFO)
local stateFile = io.open(STATE_FIFO, "w")
if not stateFile then
    print("[FIFO-Lua] ERROR: Could not open state FIFO for writing")
    return
end
stateFile:setvbuf("line")  -- flush on each newline
print("[FIFO-Lua] State FIFO opened OK")

-- Send initial hello
stateFile:write('{"event":"hello-fifo"}\n')
print("[FIFO-Lua] Sent: hello-fifo")

local frame = 0
local count = 0

emu.add_machine_frame_notifier(function()
    frame = frame + 1

    -- Send ping every frame for maximum write throughput
    count = count + 1
    local ok = pcall(function()
        stateFile:write(string.format('{"event":"frame","frame":%d}\n', frame))
    end)

    -- Log every 60th ping so we can see progress
    if count % 60 == 0 then
        if ok then
            print(string.format("[FIFO-Lua] [%d] %d pings sent OK", count, frame))
        else
            print(string.format("[FIFO-Lua] [%d] WRITE FAILED", count))
        end
    end
end)

print("[FIFO-Lua] Stress test running — writing every frame at 60 Hz")