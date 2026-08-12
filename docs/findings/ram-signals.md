# RAM Signals

Project-wide catalog of RAM addresses with known behavior. Each entry is headed by the question it answers — signal names and addresses follow.

<br>

<br>

## How do I know the game is ready for commands?

**displayFunction** at `0x02B2–0x02B3`. A 16-bit pointer to the game's active screen-drawing routine. This is the primary readiness gate: once it hits `0xCE66`, the normal playing screen is active and the command area is visible.

Read as big-endian: `byte_at_0x02B2 * 256 + byte_at_0x02B3`.

| Value | Meaning |
|-------|---------|
| 0x0000 | Demo loop — game is playing canned input, screen redrawing is disabled or redirected |
| 0xCE66 | Live play — normal playing screen is active (3D view, status bar, command area) |

The transition from 0x0000 to 0xCE66 happens when the game exits the demo loop, regardless of how that exit is triggered (keyboard priming, clicking the MAME window, or any future automation). Once the value becomes 0xCE66, it stays there for the remainder of the session.


<br>

<br>

## How do I know a command was accepted?

**perfectMatch** at `0x027B`. A 1-byte flag set by the game's command parser when it successfully matches a complete input line against the command word tables.

| Value | Meaning |
|-------|---------|
| 0x00 | No match — no input processed, parser still working, or input was invalid |
| 0xFF | Parser found a complete, valid command match |

This signal fires once per command — it flips from 0 to 0xFF at the moment the parser finishes consuming a `\r`-terminated line and matching it against the command word tables. It resets to 0 shortly after as the parser returns to idle.

Three other signals change at the same moment, forming a reliable command-consumed fingerprint:

- **foundMatch** (0x0278) = 1 — at least one word matched
- **numWords** (0x0279) = 0 — the word-matching table is exhausted
- **whereToPrint** (0x02B7) = 255 — the game redirects text output to echo the command

`perfectMatch` only fires for *matched* commands. An unrecognised command that produces `???` does not set this flag.