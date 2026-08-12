# Screen Reading

The command area is a small strip at the bottom of the screen where the game echoes what you type and prints responses: "PULL LEFT TORCH", "???", "!!!" — everything you need to know what just happened. Right now we can detect that the game finished printing there. But we can't read what it said, because the game stores it as raw pixels, not text.

## Plan

This sandbox is split into two experiments, each with its own `run.py` and `analyze.py`. Both share `shared.lua` (screen capture) and `shared.py` (decoding).

**return-key** — What does a single `\r` keystroke write to the screen buffer?
- The game boots without auto-priming. You click the window to enter live mode.
- A single `\r` is posted, and the screen buffer is captured every frame.
- `analyze.py` traces the cursor movement and decodes whatever text appears.

**pull-left-torch** — Does the decoder produce readable text?
- The game auto-primes at frame 300, then posts "PULL LEFT TORCH" at frame 750.
- When `perfectMatch` fires (command consumed), the screen buffer is captured.
- `analyze.py` decodes all 4 text rows and searches for "PULL LEFT TORCH."
- If the decoder prints that, it works. A future experiment with `BOGUS\r` would confirm `???` is also readable.

<br>

## The Algorithms

Two pieces of the game's own code make screen reading possible. One draws text on screen; the other reverses that process to read it back.

### PrintRegChar

The game calls this routine whenever it needs to put a letter on screen. It takes a character code, fetches the right pattern from the font table, and paints pixels into the screen buffer. Every smudge of text we're trying to read was put there by this routine — if we know what math it used to place the pixels, we know what math to undo.

### DecodeCommandArea

This is the function we're building. It reads raw bytes from the screen buffer and figures out which characters are there by matching pixel patterns against the font. It's PrintRegChar run in reverse: take the screen bytes, strip away the color and positioning transforms, and compare what's left against the known character shapes.

The rest of this document builds out the details — first the data we need to collect, then exactly how each algorithm transforms bytes into pixels and back again.

<br>

## Technical Details

### 1. Gather everything we need while the game runs.

The game's font is documented in the disassembly — 32 characters, each 7 rows of 5 bits. Those patterns live in `shared.py` as `FONT_PATTERNS`. No runtime font dump is needed; the patterns are fixed and verified against `code.md`.

Screen captures are handled by a shared Lua module (`shared.lua`). It reads the command area from the addresses below, writes a FRAME metadata line followed by 32 DATA lines (one per scanline, 32 hex bytes each), and skips frames where nothing changed — summarized as a single `UNCHANGED` line.

| Address | Field | Description |
|---------|-------|-------------|
| 0x0390–0x0391 | `comStart` | Start address in screen buffer (big-endian) |
| 0x0392–0x0393 | `comSize` | Size in characters (typically 128) |
| 0x0394–0x0395 | `comTextCursor` | Cursor position |
| 0x0396 | `comColor` | Color byte (0xFF = white background, XOR'd with font data) |
| 0x02B2–0x02B3 | `displayFunction` | Readiness gate: 0x0000 = demo, 0xCE66 = live play |

The two experiments differ only in what keystrokes they post and when. The return-key experiment waits for a manual click to enter live mode, then posts a single `\r`. The pull-left-torch experiment auto-primes at frame 300 and posts `PULL LEFT TORCH\r` at frame 750. Both capture continuously while the game is live.

---

### 2. Now stop the game and figure out the decoding.

```
  The command area holds 4 text rows. Each row is 32 characters wide
  and 8 scanlines tall. Characters use 7 of those scanlines; the 8th
  is blank spacing between rows of text.

  Text Row 1 (comStart):
    scan 0:  . . . . . . . .       . . . . . . . .
    scan 1:  . . . . . . . .       . . . . . . . .
    scan 2:  . . . . . . . .       . . . . . . . .
    scan 3:  . . . . . . . .       . . . . . . . .
    scan 4:  . . . . . . . .       . . . . . . . .
    scan 5:  . . . . . . . .       . . . . . . . .
    scan 6:  . . . . . . . .       . . . . . . . .
    scan 7:  . . . . . . . .       . . . . . . . .   (spacing)

  Text Row 2 (comStart + 256):
    scan  8:  . . . . . . . .       . . . . . . . .
    scan  9:  . . . . . . . .       . . . . . . . .
    ...
    scan 14:  . . . . . . . .       . . . . . . . .
    scan 15:  . . . . . . . .       . . . . . . . .   (spacing)

  Text Row 3 starts at comStart + 512.
  Text Row 4 starts at comStart + 768.
```

Our job is to walk across each character position, extract its 7 pixel-row bytes, and figure out which letter they represent. Those 7 bytes are spaced 32 bytes apart in memory — one per scanline, across the width of the command area.

The game builds each character on screen by combining three things: a 5-byte font pattern from ROM, a color value that controls whether the text is light or dark, and the CoCo's G6R display mode which packs 4 pixels into every byte. If we know how the game puts those pieces together, we can take them apart in reverse.

**How the game draws a character.** The font table at ROM `DB1B` stores 64 character patterns. Each pattern packs all 7 rows of a character into just 5 bytes by squeezing the 35 on/off pixel bits together and discarding the gaps. The drawing routine at `PrintRegChar` (ROM CA17) executes a series of small, precise steps to turn those 5 compressed bytes into pixels on the screen:

1. **Decompress.** The 5 packed bytes are expanded into 7 separate bytes, one per row. Each byte now holds 5 meaningful bits — one for each pixel in the row — with the remaining bits zeroed out.

2. **Shift into position.** Each row byte is shifted left by 2 bit positions. Since each character is drawn into an 8-pixel-wide slot but the font only defines 5 pixels, this centers the visible pixels within the slot by leaving 1.5 pixels of empty space on each side.

3. **Apply color.** The shifted byte is XOR'd with `comColor`. XOR is a bit-flipping operation: a 1 in the color byte flips the corresponding bit in the row byte, a 0 leaves it unchanged. When `comColor` is 0xFF (all 1s), every bit flips — white pixels become black and black become white. This single trick handles both light-on-dark and dark-on-light text without needing a second font.

4. **Write to screen.** The resulting byte is stored to the command area's region of the screen buffer. The next row of the same character goes 32 bytes later in memory — the stride between consecutive scanlines in this text display area.

Here is the letter A flowing through each stage of the pipeline:

```
  ROM bytes      decompress      << 2        XOR 0xFF       screen
  (5 bytes)      (7×5 bits)    (8 bits)      (8 bits)     (1 byte/row)

  0x31             →  00100  →  00010000  →  11101111  →  ███.████   row 0
  0x15             →  01010  →  00101000  →  11010111  →  ██.█.███   row 1
  0x18             →  10001  →  01000100  →  10111011  →  █.███.██   row 2
  0x18             →  10001  →  01000100  →  10111011  →  █.███.██   row 3
                   →  11111  →  01111100  →  10000011  →  █.....██   row 4
  0xFE             →  10001  →  01000100  →  10111011  →  █.███.██   row 5
  0x31             →  10001  →  01000100  →  10111011  →  █.███.██   row 6

  (40 bits)         (centered) (inverted)  (at 32-byte
  packed                                        stride)
```

Each ROM byte unpacks into 1 or 2 rows depending on how the 5-bit patterns fall across byte boundaries. Byte 0x31 (rows 0–1) contributes 3 bits to row 0 and 2 bits to row 1. Byte 0x15 (rows 1–2) contributes 3 bits to row 1 and 2 bits to row 2. And so on — 35 bits across 5 bytes, reassembled into 7 rows of 5 bits each. Shifting left by 2 centers them in an 8-bit slot. XOR with 0xFF inverts the colors. The resulting seven bytes land in the screen buffer, each 32 bytes apart.

**How we decode a character.** We reverse the pipeline. The 7 bytes that make up one character are spaced 32 bytes apart in the screen buffer — one pixel row per scanline. To decode a character at column C in text row R, we start at offset `R * 256 + C` (each text row uses 8 scanlines × 32 bytes = 256 bytes). From there, we read at 32-byte intervals, apply the reverse transforms, and compare against the font.

```
  Decode walk for column C in text row 0:

    screen bytes                recovered rows
    (read from buffer)          (un-XOR, >>2, &0x1F)

    offset + C + 0×32: ████.███  →  00100
    offset + C + 1×32: ███.█.██  →  01010
    offset + C + 2×32: ██.███.█  →  10001
    offset + C + 3×32: ██.███.█  →  10001
    offset + C + 4×32: ██.....█  →  11111
    offset + C + 5×32: ██.███.█  →  10001
    offset + C + 6×32: ██.███.█  →  10001

    Compare these 7 rows against each of the 32 font entries.
    Closest match (fewest differing bits) → character "A".
```

We compare the recovered 7 rows against every font entry using Hamming distance (number of differing bits). If the nearest match is within 8 bits of perfect, we output that character; otherwise we output `?`. This process repeats for every character column in every text row until all four rows of the command area are decoded.

This work happens entirely offline. A standalone Python script reads the log file captured in step 1, and every tweak — bit alignment, color handling, scanline stride, match threshold — is a code change and re-run. No MAME restarts. We know we posted `PULL LEFT TORCH`, so when the decoder prints that string we know the matching logic is correct.

---

### 3. Package the decoder for reuse.

The decoding logic is useless if we have to re-derive it every time. The whole point of this sandbox is to produce a function we can drop into the production environment and call whenever a message appears on screen. That means wrapping it cleanly and validating it against known inputs.

**The function.** The decoder lives in `shared.py` as `decode_text_row(screen_bytes, text_row, com_color, characters_per_row=32)`. It takes raw screen buffer bytes, a zero-based text row index, and the command area's color byte, and returns the decoded text. The font table is baked in — no separate dump needed. No side effects, no MAME dependency — just bytes in, string out.

**Validation.** Two tests prove the decoder is correct. First, we decode the capture from step 1 and confirm the output is `PULL LEFT TORCH` — that validates the happy path with known ground truth. Second, we run a new capture with `BOGUS\r` — an invalid command — and confirm the output includes `???`. If both pass, the decoder handles any message the game prints.


## Conclusion

The command area text can be read directly from RAM — no computer vision, no OCR, just arithmetic.

**The math works.** `PrintRegChar` draws each character by taking a 5-byte font pattern, shifting it left by 2 bits, XORing with `comColor`, and writing 7 bytes into the screen buffer at a 32-byte stride. Our decoder reverses this — XOR, shift right by 2, match against 32 font entries — and out comes readable text. We verified it with `PULL LEFT TORCH` appearing in the command area after it was posted.

**This unlocks the feedback channel.** The AI can now read every message the game prints — `???` on bad input, `!!!` on a hit, creature alerts, inventory readouts. It replaces a blind yes/no from `perfectMatch` with the game's actual words.

**The pipeline is reusable.** The shared `shared.lua` (capture) and `shared.py` (decode) modules mean any future sandbox or production code that needs screen text can just import them. The Lua module includes `commandAreaSnapshot` deduplication — frames are only written to disk when the screen changes. The Python module handles all 4 text rows via `decode_text_row()`. The only per-experiment code is what keystrokes to post and when.
