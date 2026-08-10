# Screen Reading

The command area is a small strip at the bottom of the screen where the game echoes what you type and prints responses: "PULL LEFT TORCH", "???", "!!!" — everything you need to know what just happened. Right now we can detect that the game finished printing there. But we can't read what it said, because the game stores it as raw pixels, not text.

## Plan

1. **Gather everything we need while the game runs.**
   - The game keeps a list of displayable characters in ROM. There are 64 entries, 5 bytes each. We grab that at startup.
   - We post a known command — "PULL LEFT TORCH" — and wait for the command area to update.
   - Once the command area updates, we save a handful of snapshots to capture the finished message.

2. **Now stop the game and figure out the decoding.**
   - We already have the font list and the command area snapshots. No more MAME — we just work on the data.
   - For each position in the command area, compare the bytes against every font entry to find the best match.
   - Ground truth: we know we posted "PULL LEFT TORCH." If our decoder prints that, it's correct.

3. **Package the decoder for reuse.**
   - Wrap the matching logic in a function that takes command area bytes and returns text.
   - Validate it against the captured log to confirm it reads "PULL LEFT TORCH."
   - Run a second capture with an invalid command to confirm "???" is also readable.

<br>

## Technical Details

### 1. Gather everything we need while the game runs.

To decode text, we need three things: every letter the game can draw, a screen capture with readable text in it, and a way to know exactly when that text appears. If we collect all three in a single run, we can stop MAME and work on the decoding separately.

**The font table.** The game's font lives in ROM at `DB1B`. Each character is 5 pixels wide and 7 rows tall, and the game only needs to know whether each pixel is on or off — 35 bits total. That fits in 5 bytes with room to spare, so the font stores 64 characters in just 320 bytes. The plugin reads this once at startup and dumps it as hex. Nothing else needs the font table; this one dump is all the decoding script will need.

**The trigger.** To capture the command area at the right moment, we post a command we know the exact text of — `PULL LEFT TORCH` — and watch for the game to finish with it. We warm up first by priming the keyboard at frame 300 (posting two Enter keystrokes to break out of the demo loop), then send the command at frame 750. The signal at `perfectMatch` (0x027B) goes to 0xFF the moment the parser finishes consuming the command, which we proved in the command-detection sandbox. We can't capture the screen buffer until after `perfectMatch` fires, because that's exactly when the echoed command will be visible.

**The capture.** The command area's location in the screen buffer is described by a set of addresses at 0x0390:

| Address | Field | Description |
|---------|-------|-------------|
| 0x0390–0x0391 | `comStart` | Start address in screen buffer (big-endian) |
| 0x0392–0x0393 | `comSize` | Size in characters (typically 128) |
| 0x0394–0x0395 | `comTextCursor` | Cursor position |
| 0x0396 | `comColor` | Color byte (0xFF = white background, XOR'd with font data) |

Once `perfectMatch` fires, we read `comSize` bytes starting at `comStart` for 60 frames — long enough to capture the echoed command and any game response that follows. Each frame logs the descriptor values and `displayFunction` (0x02B2–0x02B3) alongside the raw bytes. The output is a single log file: font table first, then frame-delimited screen buffer dumps.

---

### 2. Now stop the game and figure out the decoding.

The command area is just a rectangle of the screen buffer — raw bytes that the video hardware turns into colored dots. Each character the game prints is 5 pixels wide and 7 pixels tall, and the screen stores these as short rows of pixel data stacked on top of each other with a 32-byte gap between rows (because the full screen is 256 pixels across, which takes 32 bytes at 4 pixels per byte). Our job is to walk across those rows, extract each character's pixels, and figure out which letter it is.

The game builds each character on screen by combining three things: a 5-byte font pattern from ROM, a color value that controls whether the text is light or dark, and the CoCo's G6R display mode which packs 4 pixels into every byte. If we know how the game puts those pieces together, we can take them apart in reverse.

**How the game draws a character.** The font table at ROM `DB1B` stores 64 character patterns. Each pattern packs all 7 rows of a character into just 5 bytes by squeezing the 35 on/off pixel bits together and discarding the gaps. The drawing routine at `PrintRegChar` (ROM CA17) executes a series of small, precise steps to turn those 5 compressed bytes into pixels on the screen:

1. **Decompress.** The 5 packed bytes are expanded into 7 separate bytes, one per row. Each byte now holds 5 meaningful bits — one for each pixel in the row — with the remaining bits zeroed out.

2. **Shift into position.** Each row byte is shifted left by 2 bit positions. Since each character is drawn into an 8-pixel-wide slot but the font only defines 5 pixels, this centers the visible pixels within the slot by leaving 1.5 pixels of empty space on each side.

3. **Apply color.** The shifted byte is XOR'd with `comColor`. XOR is a bit-flipping operation: a 1 in the color byte flips the corresponding bit in the row byte, a 0 leaves it unchanged. When `comColor` is 0xFF (all 1s), every bit flips — white pixels become black and black become white. This single trick handles both light-on-dark and dark-on-light text without needing a second font.

4. **Write to screen.** The resulting byte is stored to the command area's region of the screen buffer. The next row of the same character goes 32 bytes later in memory — the stride between consecutive scanlines in this text display area.

**How we decode a character.** For each position in the command area, we read 7 bytes at 32-byte intervals — that's one complete character image. We XOR with `comColor` to undo the color inversion, shift right by 2 bits and apply a 5-bit mask to recover the original font row data. Then we compare these 7 rows against each of the 64 font entries to find the best match, using Hamming distance (number of differing bits). If the closest match is clear and the distance is below our threshold, we output that character; otherwise we output `?` to indicate uncertainty.

This work happens entirely offline. A standalone Python script reads the log file captured in step 1, and every tweak — bit alignment, color handling, scanline stride, match threshold — is a code change and re-run. No MAME restarts. We know we posted `PULL LEFT TORCH`, so when the decoder prints that string we know the matching logic is correct.

---

### 3. Package the decoder for reuse.

The decoding logic is useless if we have to re-derive it every time. The whole point of this sandbox is to produce a function we can drop into the production environment and call whenever a message appears on screen. That means wrapping it cleanly and validating it against known inputs.

**The function.** Once the matching logic works, we wrap it in a single callable: `decode_command_area(bytes, font_table, com_color) -> str`. It takes raw screen buffer bytes, the font table dumped in step 1, and the command area's color byte, and returns the decoded text. No side effects, no MAME dependency — just bytes in, string out.

**Validation.** Two tests prove the decoder is correct. First, we decode the capture from step 1 and confirm the output is `PULL LEFT TORCH` — that validates the happy path with known ground truth. Second, we run a new capture with `BOGUS\r` — an invalid command — and confirm the output includes `???`. If both pass, the decoder handles any message the game prints.
