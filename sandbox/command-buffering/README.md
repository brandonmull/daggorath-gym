# Command Buffering

## Goal

How fast can we send commands to the in-game parser? If there's a rate limit, do we need to manage command rate ourselves?

## Findings

`natkeyboard:post()` does **not** write to the CoCo's 32-byte `inputBuf` ring buffer at `02D1`. Posting commands every frame showed `inputHead` and `inputTail` both stuck at 0 — natkeyboard injects keystrokes at a lower level, bypassing the ring buffer entirely.

Commands posted every frame do reach the in-game console, but they appear slower on screen than the frame rate would suggest. This indicates some rate limiting within `natkeyboard:post()` or the game's parser itself — the bottleneck is not the ring buffer, but the delivery or consumption speed.

## Conclusion

No Lua-side command buffering is needed. The agent can post commands via `natkeyboard:post()` at whatever rate it chooses — any rate limiting happens downstream, in the emulator or the game, not in our code.