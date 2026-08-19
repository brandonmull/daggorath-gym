# RAM Signals

> ## ⚠️ READ-TIME CRASH WARNING
>
> **Do not read any signal below until the game has booted.** A frame notifier fires on frame 1, when the 6809 has executed almost no instructions and the GIME MMU (mapping the 64 KB CPU space onto 512 KB of physical RAM) is still in its power-on state. `read_u8` through that uninitialized mapping raises a native **SIGSEGV** — a C++ crash, not a Lua error, so `pcall` won't catch it and `print()` output is lost on the way down.
>
> The safe pattern for every read:
>
> 1. Return immediately while `manager.machine.paused` is true.
> 2. Gate on the readiness signal itself — **displayFunction** (`0x02B2–0x02B3`) — and check it **before** touching any other RAM. Only when it is `0xCE66` or `0xD495` (live play — the dungeon or the inventory view) is the rest of the map safe.
> 3. Never sample state first and gate afterward — sampling is itself a read, and doing it before the gate is the crash.
>
> This is why the readiness gate sits *above* the state schema in the frame handler, not below it.

Project-wide catalog of RAM addresses with known behavior. Each entry is headed by the question it answers — signal names and addresses follow.

<br>

<br>

## How do I know the game is ready for commands?

**displayFunction** at `0x02B2–0x02B3`. A 16-bit pointer to the game's active screen-drawing routine. This is the primary readiness gate: once it hits `0xCE66` (or `0xD495`), a live-play screen is active and the command area is visible.

Read as big-endian: `byte_at_0x02B2 * 256 + byte_at_0x02B3`.

| Value | Meaning |
|-------|---------|
| 0x0000 | Demo loop — game is playing canned input, screen redrawing is disabled or redirected |
| 0xCE66 | Live play — the dungeon view (LOOK): the normal playing screen (3D view, status bar, command area) |
| 0xD495 | Live play — the inventory view (EXAMINE) |

The transition from 0x0000 happens when the game exits the demo loop, regardless of how that exit is triggered (keyboard priming, clicking the MAME window, or any future automation). It never returns to 0x0000; in live play it moves between `0xCE66` (LOOK, set by `CmdLOOK` at C751) and `0xD495` (EXAMINE, set by `CmdEXAMINE` at D481) as the player switches views.


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