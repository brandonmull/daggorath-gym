-- UDS test: try Unix domain sockets with emu.file.
-- If this works, it replaces TCP sockets for same-machine IPC.
--
-- Tests several syntax variants for the emu.file:open() address string:
--   1. "socket.<path>"          — direct path, analogous to "socket.<host>:<port>"
--   2. "socket.unix:<path>"     — unix: scheme
--   3. "socket.local:<path>"    — local: scheme
--
-- All tests write results to LOG_FILE so we can inspect them.

local LOG_PATH = os.getenv("LOG_FILE") or "/tmp/daggorath-uds-test.log"
local LOG = io.open(LOG_PATH, "w")

local function log(msg)
    print("[UDS-Lua] " .. msg)
    if LOG then
        LOG:write(msg .. "\n")
        LOG:flush()
    end
end

local STATE_PATH = os.getenv("UDS_STATE_PATH") or "/tmp/daggorath-uds-state"
local ACTION_PATH = os.getenv("UDS_ACTION_PATH") or "/tmp/daggorath-uds-action"

-- ---------- Test 1: "socket.<path>" ----------
log("=== Test 1: socket.<path> ===")
local sock1 = emu.file("w")
local err1 = sock1:open("socket." .. STATE_PATH)
if err1 then
    log("Test 1 FAILED: " .. tostring(err1))
else
    log("Test 1 OK — write socket opened with socket.<path>")
end

local sock1r = emu.file("r")
local err1r = sock1r:open("socket." .. ACTION_PATH)
if err1r then
    log("Test 1 read FAILED: " .. tostring(err1r))
else
    log("Test 1 OK — read socket opened with socket.<path>")
    sock1r:close()
end

-- ---------- Test 2: "unix:<path>" ----------
log("=== Test 2: unix:<path> ===")
local sock2 = emu.file("w")
local err2 = sock2:open("unix:" .. STATE_PATH)
if err2 then
    log("Test 2 FAILED: " .. tostring(err2))
else
    log("Test 2 OK — write socket opened with unix:<path>")
    sock2:close()
end

-- ---------- Test 3: "local:<path>" ----------
log("=== Test 3: local:<path> ===")
local sock3 = emu.file("w")
local err3 = sock3:open("local:" .. STATE_PATH)
if err3 then
    log("Test 3 FAILED: " .. tostring(err3))
else
    log("Test 3 OK — write socket opened with local:<path>")
    sock3:close()
end

-- ---------- Functional test with whichever syntax worked ----------
-- If Test 1 passed, do a ping/pong exchange to validate full duplex.
if not err1 and not err1r then
    log("=== Functional test ===")
    sock1:write("{\"event\":\"hello-uds\"}\n")
    log("Sent: hello-uds")

    local frame = 0
    local count = 0
    emu.add_machine_frame_notifier(function()
        frame = frame + 1
        if frame % 60 == 0 then
            count = count + 1
            local msg = string.format("{\"event\":\"ping\",\"count\":%d}\n", count)
            local ok = pcall(function() sock1:write(msg) end)
            if ok then
                log(string.format("[%d] Sent ping", count))
            end
        end

        -- Try reading from action socket
        local response = sock1r:read(256)
        if response and #response > 0 then
            log(string.format("Read: %s", response:gsub("\r?\n$", "")))
        end
    end)
    log("Functional test running — ping every 60 frames")
else
    log("Skipping functional test — Test 1 did not pass")
end

log("Client initialization complete")
if LOG then
    LOG:close()
end