-- Shared command area capture logic for screen-reading experiments.
--
-- The command area begins at comStart. It holds 4 text rows.
-- Each text row is 32 characters wide and 8 scanlines tall.
-- A scanline is 32 bytes wide — one byte per character position.
-- Successive scanlines are 32 bytes apart.
--
-- Which scanlines belong to which text row:
--   Text row 1: first 8 scanlines
--   Text row 2: next 8 scanlines
--   Text row 3: next 8 scanlines
--   Text row 4: last 8 scanlines
--
-- Example: the 4th character in the 2nd text row.
--   The 2nd row begins at the 9th scanline, 256 bytes from comStart
--   (8 preceding scanlines × 32 bytes each).
--   The 4th character starts 3 bytes into that scanline.
--   Top pixel row of the character:           comStart + 256 + 3
--   Next pixel row (one scanline down):        comStart + 288 + 3
--   This repeats for all 8 scanlines of the text row.
--
-- For the code, scanlines and character positions are zero-based.
-- Address for scanline s, character position c:  comStart + s × 32 + c
--
--
-- The capture function logs the command area pixels to a file.
-- It only writes a frame when the pixels differ from the previous
-- logged frame. Identical frames are tracked and summarized as a
-- single UNCHANGED line.
--
-- Output format:
--   FRAME,<frame>,<areaStart>,<areaSize>,<cursor>,<color>,<displayFn>,<match>
--   DATA,<scanline>,<32 hex bytes>
--   ...
--   UNCHANGED,<firstFrame>,<lastFrame>
--
-- The entire frame is built in memory (table.concat) and written in
-- a single call to avoid hitting MAME's io.write buffer limit.

local TEXT_ROWS = 4
local CHARS_PER_ROW = 32
local SCANLINES_PER_ROW = 8
local TOTAL_SCANLINES = TEXT_ROWS * SCANLINES_PER_ROW

local commandAreaSnapshot = {
    pixels = nil,   -- 1024 bytes from the most recent logged frame
    frame = nil,    -- the frame number when those pixels appeared
}

local function _readPixels(memory)
    local areaStart = memory:read_u8(0x0390) * 256 + memory:read_u8(0x0391)
    local pixels = {}
    for scanlineIndex = 0, TOTAL_SCANLINES - 1 do
        local scanlineStart = areaStart + scanlineIndex * CHARS_PER_ROW
        for characterColumn = 0, CHARS_PER_ROW - 1 do
            pixels[#pixels + 1] = memory:read_u8(scanlineStart + characterColumn)
        end
    end
    return pixels
end

local function _pixelsMatch(current, previous)
    if #current ~= #previous then
        return false
    end
    for i = 1, #current do
        if current[i] ~= previous[i] then
            return false
        end
    end
    return true
end

local function _writeFrame(logFile, frame, memory)
    local areaStart = memory:read_u8(0x0390) * 256 + memory:read_u8(0x0391)
    local areaSize   = memory:read_u8(0x0392) * 256 + memory:read_u8(0x0393)
    local cursor     = memory:read_u8(0x0394) * 256 + memory:read_u8(0x0395)
    local color      = memory:read_u8(0x0396)
    local displayFn  = memory:read_u8(0x02B2) * 256 + memory:read_u8(0x02B3)
    local match      = memory:read_u8(0x027B)

    local logPieces = {string.format("FRAME,%d,%d,%d,%d,%d,%d,%d\n",
        frame, areaStart, areaSize, cursor, color, displayFn, match)}

    for scanlineIndex = 0, TOTAL_SCANLINES - 1 do
        local scanlineStart = areaStart + scanlineIndex * CHARS_PER_ROW
        logPieces[#logPieces + 1] = string.format("DATA,%d,", scanlineIndex)

        for characterColumn = 0, CHARS_PER_ROW - 1 do
            local byte = memory:read_u8(scanlineStart + characterColumn)
            logPieces[#logPieces + 1] = string.format("%02X", byte)
        end

        logPieces[#logPieces + 1] = "\n"
    end

    logFile:write(table.concat(logPieces))
    logFile:flush()
end

local function captureCommandAreaPixels(logFile, frame, memory)
    local currentPixels = _readPixels(memory)

    if commandAreaSnapshot.pixels and _pixelsMatch(currentPixels, commandAreaSnapshot.pixels) then
        -- Screen has not changed. Nothing to write.
        return
    end

    -- Screen changed. Summarize any identical frames we skipped,
    -- then write the new frame and update the snapshot.
    if commandAreaSnapshot.frame then
        local skippedFrames = frame - commandAreaSnapshot.frame - 1
        if skippedFrames > 0 then
            logFile:write(string.format("UNCHANGED,%d,%d\n",
                commandAreaSnapshot.frame + 1, frame - 1))
            logFile:flush()
        end
    end

    _writeFrame(logFile, frame, memory)
    commandAreaSnapshot.pixels = currentPixels
    commandAreaSnapshot.frame = frame
end

return {
    captureCommandAreaPixels = captureCommandAreaPixels,
}