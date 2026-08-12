# Screen Reading Module

_See [overview.md](overview.md) for project context and architecture._

This document addresses two design questions:

1. **How do we capture command-area text?** — reading raw pixels from RAM, no OCR
2. **How do we decode those pixels back into text?** — reversing the game's own character drawing routine

## Purpose

The command area is a strip at the bottom of the screen where the game echoes typed commands and prints responses — `???` on bad input, `!!!` on a hit, creature alerts, inventory readouts. The rest of the state module reports numbers from RAM; this module recovers the game's *words*. It replaces the blind yes/no of `perfectMatch` with the actual text the game prints.

No computer vision, no OCR. The game draws every letter with its own `PrintRegChar` routine using a fixed font table. We read the raw pixel bytes it wrote and reverse that exact arithmetic.

## Architecture

The module splits across both sides of the wire, but the decode logic lives only in Python:

```
state.lua (capture)                 state FIFO                 screen.py (decode)
───────────────                     ──────────                 ──────────
reads command-area pixels    ──→    T/B record     ──→    decode_text_row()
from comStart (1024 bytes)          (tag + comColor            → readable text
                                    + pixel bytes)
```

The Lua side only moves bytes. The font table — 32 characters, 7 rows × 5 bits — lives once, in Python. No duplication of the font in Lua.

## Screen Geometry

The command area begins at the address in `comStart` (0x0390–0x0391, big-endian). It holds 4 text rows, each 32 characters wide and 8 scanlines tall. A scanline is 32 bytes — one byte per character position. Successive scanlines are 32 bytes apart. The 8th scanline of each row is blank spacing.

The whole region is `4 rows × 8 scanlines × 32 bytes = 1024 bytes`, read as a flat block ordered by scanline.

| Address | Field | Purpose |
|---------|-------|---------|
| 0x0390–0x0391 | `comStart` | Start address of the command area in the screen buffer |
| 0x0396 | `comColor` | Color XOR used to draw text (0xFF = white background) |
| 0x02B2–0x02B3 | `displayFunction` | Readiness gate — 0xCE66 means the normal screen is live |

## Decoding Math

`PrintRegChar` draws a character in four steps. The decoder runs them in reverse:

```
draw                        decode
────                        ──────
decompress 5 packed bytes   →  compare 7 recovered rows against
   into 7 rows of 5 bits         the stored font (Hamming distance)
shift left 2 (center)       →  shift right 2, mask low 5 bits
XOR with comColor           →  XOR with comColor (same operation)
write at 32-byte stride     →  read at 32-byte stride
```

The decoder walks each of the 32 character columns in a text row, reads 7 bytes at 32-byte intervals, un-XORs and un-shifts them, and matches the result against every font entry by counting differing bits. The closest match within a threshold is the character; anything outside the threshold reads as `?`.

## Capture

The capture logic lives in `state.lua` as part of the per-frame state sampler. It reads `comStart` and `comColor` each frame and copies the 1024-byte region, then hands those bytes to the same change-detection snapshot used for the numeric state (see `state-module.md`).

```
readCommandAreaPixels()
    → reads comStart from 0x0390–0x0391
    → copies 1024 bytes from the command area (32 scanlines × 32 bytes)
    → returns the pixel block plus comColor
```

Capture is gated by `displayFunction == 0xCE66` — during the demo loop there is no meaningful command-area text to read.

## Decoding

The decoder lives in Python in a new module, `daggorath_gym/screen.py`. It is ported from the validated `sandbox/screen-reading/shared.py`.

Its public surface is small:

```
FONT_PATTERNS
    → 32 entries, each a (character, 7 rows of 5 bits) pair
    → space, A–Z, !, _, ?, .

decode_character(pixel_block, char_offset, com_color)
    → reads 7 bytes at 32-byte intervals starting at char_offset
    → un-XORs with com_color, shifts right 2, masks to 5 bits
    → finds the font entry with the fewest differing bits
    → returns that character, or ? if the match is too distant

decode_text_row(pixel_block, text_row, com_color)
    → decodes each of the 32 columns in one text row
    → returns the row as a string
```

The font table is a constant, not dumped from ROM at runtime — the patterns are fixed and verified against `code.md`.

## Module Names

| Side | File | Module | Notes |
|------|------|--------|-------|
| Lua | `state.lua` | `readCommandAreaPixels` (function) | Capture stays in the state module — it is another field being sampled |
| Python | `screen.py` | `FONT_PATTERNS`, `decode_character`, `decode_text_row` | Python-only decoding; no Lua counterpart |

## Testing Strategy

The decoder is validated end-to-end against a known trigger, reusing the sandbox captures:

- Decode the `pull-left-torch` log and confirm `PULL LEFT TORCH` appears — the happy path with known ground truth
- Decode a `BOGUS\r` capture and confirm `???` appears — the invalid-command path

Both cases already passed in `sandbox/screen-reading/`; they become regression tests when the decoder moves into production.

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `sandbox/screen-reading/` | Validated capture + decode pipeline (`shared.lua`, `shared.py`, two experiments) |
| `docs/references/game/code.md` | `PrintRegChar` disassembly and the font table |
| `docs/plans/state-module.md` | How the captured pixels flow into the state wire format |