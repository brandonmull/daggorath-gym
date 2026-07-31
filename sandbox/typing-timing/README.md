# Typing Timing

## Goal

Find the minimum viable `KEY_HOLD`, `CHAR_GAP`, and `POST_ENTER_DELAY` values for typing command phrases into the CoCo text parser. The current guesses (3, 2, 10) in `emulation/commands.lua` need validation — they may be too fast (parser drops characters) or too slow (agent wastes frames waiting).

## Approach

### Test 1: Character registration

Type a single character per frame cycle with minimal hold time, then read the game's text buffer from RAM to see if it registered. Increase `KEY_HOLD` until the character appears reliably.

If the text buffer address is known from `emulation/docs/ram.md`, we can observe directly. If not, we can type a full command that has a visible side effect (e.g., `MOVE` changes `at_cell_x`/`at_cell_y`) and verify the game acted on it.

### Test 2: Phrase typing speed

Type a complete phrase (e.g., `"MOVE\n"`) at varying speeds:
- Vary `CHAR_GAP` from 0 to 10 frames
- Vary `POST_ENTER_DELAY` from 0 to 30 frames
- After each attempt, read RAM to confirm the game processed the command

Binary search: start fast, slow down until reliable.

### Test 3: Multi-command throughput

Type two commands in sequence (e.g., `MOVE\n` then `MOVE\n`) and verify both executed. This tests whether `POST_ENTER_DELAY` is long enough for the game to finish processing before accepting new input.

## Success Criteria

- [ ] `KEY_HOLD`: minimum frames for a single keystroke to register
- [ ] `CHAR_GAP`: minimum frames between keystrokes without dropped characters
- [ ] `POST_ENTER_DELAY`: minimum frames after ENTER before next command is accepted
- [ ] Values documented in `emulation/docs/` or `plans/`

## Notes

- MAME runs at ~60 fps, so 1 frame ≈ 16.7ms
- The game's text parser is on a 6809 at ~0.89 MHz — it may need generous delays
- The old `autoboot.lua` used `HOLD = 3` for single keystrokes, which is our starting point
- If the text buffer RAM address is known, this becomes a direct read test instead of a side-effect test