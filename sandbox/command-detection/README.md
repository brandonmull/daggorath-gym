# Command Detection Sandbox

Discovers what RAM addresses reliably signal that the in-game parser has consumed a posted command — purely from memory reads, no visual processing.

## Quick Start

```bash
python sandbox/command-detection/server.py
```

Posts `PULL LEFT TORCH`, `USE LEFT`, and `MOVE` at frames 750/1200/1700. Runs for 60 seconds, outputting a frame-by-frame CSV log.

## Architecture

```
sandbox/command-detection/
├── plugin.json          # MAME plugin descriptor
├── init.lua             # Plugin: GC-fixed notifiers, command posting, 16-field RAM logging
├── server.py            # Python launcher — detached, reads log.txt
├── analyze_log.py       # Analysis script for log.txt
├── log.txt              # Frame-by-frame RAM trace (CSV, ~6000 lines for 60s)
└── README.md            # This file
```

The plugin architecture follows the pattern validated in `sandbox/plugin-lifecycle/`:
- Notifier subscription return values saved in module-local Lua variables (GC auto-unsubscribe fix)
- `machine.paused` gating for memory access safety
- 180-frame boot delay before logging
- Keyboard auto-prime at frame 300 to trigger demo→live transition

## RAM Signals Logged

| Signal | Address | Width | Description |
|--------|---------|-------|-------------|
| gameMode | 0x0277 | 1 byte | 0xFF=demo, 0x00=live |
| perfectMatch | 0x027B | 1 byte | 0xFF = parser matched a complete command |
| foundMatch | 0x0278 | 1 byte | Word-match counter during parsing |
| numWords | 0x0279 | 1 byte | Number of words in current match table |
| inputHead | 0x02BC | 1 byte | Ring buffer read index |
| inputTail | 0x02BD | 1 byte | Ring buffer write index |
| displayFunction | 0x02B2-0x02B3 | 2 bytes | Screen redraw function (0xCE66 = normal) |
| whereToPrint | 0x02B7 | 1 byte | 0=command-area, non-0=output redirected |
| nextToParse | 0x02F1-0x02F2 | 2 bytes | Pointer to next input byte to parse |
| comStart | 0x0390-0x0391 | 2 bytes | Command area start address in screen buffer |
| comSize | 0x0392-0x0393 | 2 bytes | Command area character count |
| comTextCursor | 0x0394-0x0395 | 2 bytes | Cursor position within command area |
| inputBuf | 0x02D1-0x02F0 | 32 bytes | Ring buffer (hex dump) |
| commandAreaText | _deref comStart_ | variable | Screen buffer bytes at comStart (ASCII rendering) |

**Endianness note:** The 6809 CPU is big-endian. For any 16-bit value spanning two addresses, the high byte lives at the lower address. Values are reconstructed as `byte_at_lower_addr * 256 + byte_at_higher_addr`.

## Findings

### Command Consumption Signal: `perfectMatch` (0x027B)

`perfectMatch` flips from 0 to 0xFF exactly when the parser matches a complete, valid command — it is the cleanest RAM signal for "command consumed."

| Command | Posted Frame | perfectMatch=255 Frame | Delay |
|---------|-------------|----------------------|-------|
| PULL LEFT TORCH | 750 | 901 | 151 frames (~2.5s) |
| USE LEFT | 1200 | 1283 | 83 frames (~1.4s) |
| MOVE | 1700 | 1750 | 50 frames (~0.8s) |

Subsequent commands process faster than the first — likely because the game's task scheduler is already warmed up and the parser state machine is initialized.

### Accompanying Signals at perfectMatch=255

When `perfectMatch` hits 0xFF, three other signals change simultaneously:

- **`foundMatch` = 1** — the parser found at least one match for the input
- **`numWords` = 0** — the word-matching table is exhausted (command fully resolved)
- **`whereToPrint` briefly = 255** — game redirects text output to echo the command

These four signals together form a reliable **command-consumed fingerprint**.

### Ring Buffer Behavior

The ring buffer at 0x02D1-0x02F0 **does receive `natkeyboard:post()` data** — this contradicts the finding from `sandbox/command-buffering/`, which had the GC auto-unsubscribe bug and missed all ring buffer activity.

- Head and tail advance in lockstep — bytes are consumed by the game's input routine as fast as natkeyboard delivers them
- The buffer never accumulates a backlog; head == tail at nearly all times
- After a command's `\r` is consumed, head/tail stabilize until the next command arrives
- Consumption rate is approximately 6-8 characters per second (~10 frames per byte at 60fps)

### `nextToParse` (0x02F1-0x02F2)

This pointer changes when the game begins processing input:

- **0xFFFF** before any command is posted (sentinel / uninitialized)
- **Jumps to a value in the 0x1000-0x27FF range** (first screen buffer) when the first byte of a command is consumed by the input routine
- **Decrements by ~2 per character** as the parser advances through the input
- **Stays constant** between commands (the parser is idle)

This is a useful secondary signal: `nextToParse` changing from 0xFFFF means "game is actively consuming input." But `perfectMatch` is the primary signal for "command fully consumed."

### Command Area Text Buffer

`comStart` resolves to **0x2400** (9216) after the endianness fix — a valid address in the CoCo's screen buffer range (0x1000–0x3FFF). The command area is 128 characters (comSize = 128) and the cursor (comTextCursor) advances from 97 → 113 during command echo, then returns to 97.

However, reading the bytes at `comStart` yields **pixel data, not ASCII text**. Daggorath uses the CoCo's high-resolution graphics mode where characters are drawn as bitmap patterns — the screen buffer stores raw pixel bytes, not character codes. Rendering text from the screen buffer would require knowing the game's font bitmap table. For command detection purposes, the cursor position and the consumption signals above are sufficient — the actual command text in the screen buffer is not needed.

### `commandAreaCursor` (0x0394-0x0395)

The text cursor tracks the echo cycle:
- **97** at rest (empty prompt line)
- **Advances to ~113** as the echoed command text fills the line
- **Returns to 97** when the command is processed and the line wraps/clears

This is a convenient visual-proxy signal for command echo, but `perfectMatch` is more precise for detection.

## Recommendations for Production Use

For the production Lua bridge (`emulation/`), command consumption should be detected by monitoring:

1. **`perfectMatch` (0x027B)** — primary signal: 0→0xFF transition means a command was consumed
2. **`foundMatch` (0x0278)** — confirms the match was valid (=1 at perfectMatch time)
3. **`whereToPrint` (0x02B7)** — confirms the echo cycle (=255 briefly at perfectMatch)

These three addresses together provide a reliable, low-latency signal that the game has processed the posted command and is ready for the next one.

## Known Limitations

- **Command area text is unreadable** — the screen buffer stores pixel data in graphics mode, not ASCII. Detecting what command was consumed from screen memory alone is not practical.
- **PerfectMatch does not distinguish success from failure** — the game prints `???` for unrecognized commands, but `perfectMatch` only fires for _matched_ commands. A botched command that the parser rejects may not trigger this signal. (Future sandbox: post an invalid command and observe the RAM state.)
- **Timing varies** — first command takes ~2.5s, subsequent commands ~0.8–1.4s. A fixed timeout per command should be tuned for the worst case (~3s).