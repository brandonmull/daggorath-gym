# Command Grammar Verification

## Goal

Verify that the 154-item command space in `daggorath_gym/commands.py` is correct — specifically that every command phrase is valid per the game's parser, and that no valid phrases are missing.

## Background

The current count: 9 movement + 2 view + 4 combat + 11 magic + 4 simple inventory + 62 GET + 62 PULL = 154.

This hinges on: 6 class names + 25 proper-name entries = 31 object specs. ROM data at `D8F4` lists tokens 0x00–0x18 (25 entries confirmed).

## Approach

### Test 1: Count the ROM table

Cross-reference `emulation/docs/commands.md` Appendix D against the disassembly in `emulation/docs/code.md` at ROM address `D8F4`. Verify:
- The table has exactly 25 entries
- Each entry has a class field that matches one of the 6 class names
- No entries are duplicates or unused (e.g., `EMPTY FLASK` might only appear after a flask is emptied)

### Test 2: Verify grammar completeness

For each command template from Appendix C:
```
ATTACK LEFT | ATTACK RIGHT          (2)
CLIMB UP | CLIMB DOWN               (2)
DROP LEFT | DROP RIGHT              (2)
EXAMINE                             (1)
GET LEFT <object> | GET RIGHT <object>  (2 × 31 = 62)
INCANT <proper-name>                (9 ring names only)
LOOK                                (1)
MOVE | MOVE BACK | MOVE LEFT | MOVE RIGHT  (4)
PULL LEFT <object> | PULL RIGHT <object>   (2 × 31 = 62)
REVEAL LEFT | REVEAL RIGHT          (2)
STOW LEFT | STOW RIGHT              (2)
TURN LEFT | TURN RIGHT | TURN AROUND  (3)
USE LEFT | USE RIGHT                (2)
ZLOAD | ZSAVE                       (2, excluded from action space)
```

Confirm our `COMMAND_SCHEMA` list matches this exactly: 2+2+2+1+62+9+1+4+62+2+2+3+2 = 154 (excluding ZLOAD/ZSAVE).

### Test 3: Check for state-dependent validity

Some commands may only be valid in certain game states (e.g., `CLIMB UP` requires a ladder in the current cell, `INCANT STEEL` requires holding a RING). The flat enumeration includes them all — the RL agent will learn through negative rewards which are invalid. Verify this assumption is correct: the game's parser accepts any valid phrase regardless of game state, and simply prints `???` or takes no action if impossible.

## Success Criteria

- [ ] ROM proper-names table count verified (25 entries, tokens 0x00–0x18)
- [ ] Grammar template → phrase count verified (154, excluding ZLOAD/ZSAVE)
- [ ] `commands.py` `COMMAND_SCHEMA` list checked against the grammar
- [ ] `emulation/commands.lua` `ACTIONS` list checked against the Python list (same order)
- [ ] State-dependent validity documented (if any commands are conditional)

## Notes

- ZLOAD/ZSAVE are cassette save/load commands — not useful for RL training, intentionally excluded
- The game's parser checks commands against internal tables at ROM `D8F4` (proper names) and `D96B` (class names)
- If the game ever encounters an unknown object type (e.g., a mod or hack), the parser would reject it — not relevant for stock Daggorath