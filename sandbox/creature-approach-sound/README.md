# Creature Approach Sound

## Goal

Determine when the approach sound actually fires. `docs/plans/sound/plan.md` records the disassembly gate as a 2-cell corridor (`min(|dx|,|dy|) ≤ 2`), but that contradicts lived experience of hearing creatures off-axis. Place creatures at known offsets, log when the approach sound plays, and deliver the real gating rule to `sound/plan.md`.

## Status

Prepared, not built. The static trace below is the hypothesis; the experiment in TODO will confirm or correct it before the rule is recorded in `sound/plan.md`.

## Static finding (the hypothesis to confirm)

`T_MoveCreature` (D041) computes each creature's approach sound at D168–D195, reached only after the creature successfully steps to a new cell (D162 stores the new Y/X). The gate, on the creature's new offset from the player:

- `distance = max(|dy|, |dx|)` — Chebyshev distance.
- Silent if `distance > 8` — `CMPA #$08` / `BGT` at D17E–D180.
- Silent if `min(|dy|, |dx|) > 2` — `CMPB #$02` / `BGT` at D182–D184.
- Silent 50% of the time — `BITA #$01` on the `SWI_7` LFSR low byte, `BEQ` skips (D186–D18A).
- `volume = 255 − 31 × distance` — `LDB #$1F`, `MUL`, `COMB` at D18E–D191.
- Sound number = creature type (`LDA 13,Y` at D192), played via `SWI_1C`.

The arithmetic is unambiguous: the swap at D17A/D17C places the larger axis in A and the smaller in B before both comparisons, so the disassembly genuinely gates to `min ≤ 2`. The contradiction to resolve is whether the game in practice fires off-axis (`min > 2`) — a second code path, a misread of which register holds the minimum, or a difference in the running ROM.

## TODO

Write a Lua plugin (mirroring `command-readiness`) that boots the game to live play — auto-prime at frame 300, gate on `displayFunction == 0xCE66` — then places one creature near a stationary player and logs every approach-sound decision. For each event, log the creature's offset `(dy, dx)` and whether the gate passed or the sound played.

## Recommendations

Each is a default; all are changeable.

1. **Detection — debugger breakpoints at D186 and D194.** A breakpoint at `0xD186` fires only when both corridor checks pass (the gate's decision, before the coin flip); a breakpoint at `0xD194` fires only when the coin flip also won (the sound actually playing). At each hit, read the creature's Y/X (offsets `0x0F`/`0x10` of its 17-byte struct, first slot `0x03D4`) and the player's (`0x0213`/`0x0214`), and log `(dy, dx, event)`. The debugger's Lua API is not yet transcribed in `docs/references/mame/`, so verify it before coding. *(Alternative: watch the volume register `m0261` at `0x0261` — every `SWI_1C` stores its volume there — but the same-cell attack (D079) and object sounds (D2E1) also write it, so the signal is racy.)*
2. **Creature placement — one creature, spider (type 0).** Place it in the first slot: alive `0x0C` → FF, type `0x0D` → 0, Y `0x0F` / X `0x10` at the target offset. A single creature makes every breakpoint hit attributable.
3. **Movement — do not freeze.** `wizardDead` (`0x022B`) = FF makes `T_MoveCreature` skip all actions (D044–D046 → D06A), which also suppresses the approach sound. The creature must actually step for D168 to run: keep the player still (send no commands) and let the creature wander, or relocate its Y/X each frame.
4. **Off-axis coverage — relocate the creature's Y/X.** The maze forbids four-cell open blocks (the 3D renderer draws only hallways), so a straight corridor only produces on-axis offsets (`dx = 0` or `dy = 0`). To cover `min > 2`, write the creature's Y/X directly each frame rather than relying on wandering.
5. **Sweep — Chebyshev 0…8.** `distance > 8` is silent by the first check, so sweep `dy, dx ∈ −8…8` (and a few just outside, `±9`, to confirm the boundary).

## Success criteria

- The logged `(dy, dx)` → "gate passed" map matches `max ≤ 8 && min ≤ 2` — or reveals the true rule.
- "Sound plays" ≈ half of "gate passed" at any offset (the fair coin), separating the corridor gate from the 50% roll.
- The real rule lands in `docs/plans/sound/plan.md` (replacing the *Corridor gate* unknown); this folder is deleted after use.
