# Command Buffering

## Goal

Determine whether a command buffer is needed during the TYPING state in `emulation/commands.lua`. The current implementation uses a single-slot buffer — if a new command byte arrives while typing, it replaces any buffered byte (most recent wins). This may be unnecessary if the RL agent never sends commands faster than they're typed.

## Approach

### Test 1: Measure typing duration

Type the longest command phrase (e.g., `"GET LEFT LEATHER SHIELD\n"` — ~22 characters including spaces and ENTER) and measure how many frames it takes at current timing values. This establishes a ceiling: if the RL agent steps slower than this, no buffering is needed.

### Test 2: Observe overlapping sends

Run a Python script that sends commands at increasing rates:
- Send a command every N frames (N = 1, 5, 10, 20, 30)
- On the Lua side, log whether a byte was waiting in the socket when a byte was already being typed
- Measure whether any commands are lost or overwritten

### Test 3: Check the Gymnasium contract

In normal Gymnasium usage, `env.step(action)` blocks until the next observation, which only arrives after a frame of game state. If the typing takes longer than one frame, the agent's next `step()` call happens *after* typing completes. This means the buffer may be unreachable in practice. Verify this with a timing test.

## Success Criteria

- [ ] Longest phrase typing duration measured in frames
- [ ] Overlap between sends and TYPING state observed (or not)
- [ ] Decision: keep buffer, remove buffer, or replace with queue
- [ ] If buffer is kept, verify single-slot vs queue behavior

## Notes

- The `commands.lua` state machine reads from the socket in IDLE state, after `POST_ENTER_DELAY` expires
- The RL agent's `step()` is synchronous — it calls `bridge.send()` then blocks on `bridge.recv()`
- If `POST_ENTER_DELAY + typing time` < `1 frame`, no overlapping sends can occur
- The sandbox can simulate sends at known intervals without a full RL loop