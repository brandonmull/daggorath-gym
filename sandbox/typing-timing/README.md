# Typing Timing

## Goal

Can we send typed commands to the in-game console? And if so, what — if any — timing coordination is required between the agent and the emulator?

## Running

```bash
source .venv/bin/activate
python sandbox/typing-timing/server.py
```

Launches MAME with `-autoboot_delay 1` and the script below. Commands appear on the in-game console for visual verification.

## autoboot.lua

```lua
local frame = 0
local nk = manager.machine.natkeyboard
emu.add_machine_frame_notifier(function()
    frame = frame + 1
    if frame == 1 then
        nk:post("\r")
        nk:post("\r")
        nk:post("PULL LEFT TORCH\r")
        nk:post("USE LEFT TORCH\r")
    end
end)
```

## Findings

- `natkeyboard:post()` delivers whole `\r`-terminated strings. No per-character coordination is needed — post a complete command (including ENTER) in one call.
- The CoCo's input buffer is a FIFO. Commands posted before the game is ready sit in the buffer and are consumed in order when the game's input loop catches up. This means the agent can post commands without waiting for the game to process the previous one.
- No `KEY_HOLD`, `CHAR_GAP`, or `POST_ENTER_DELAY` is needed.
- `-autoboot_delay "1"` is the minimum. The keyboard buffer isn't initialized before the 1-second mark.
- Two blank `\r` posts are required before any real commands. The first `\r` is consumed by the title screen. Without the second, the first real command loses its first 1-2 characters.

## Conclusion

The agent can post complete `\r`-terminated commands via `natkeyboard:post()` without any timing coordination. The only setup requirements are a 1-second autoboot delay and two blank `\r` priming posts before the first real command.