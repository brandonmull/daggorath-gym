# Line of Sight

## Goal

Determine how far the 3D view renders down a corridor at a given light level — the number that sets the sight-gate's reach in `docs/plans/navigation/plan.md`. Vary light and creature depth; log whether the creature's pixels appear in the play field.

## Status

Prepared, not built. The static trace below is the hypothesis; the experiment in TODO will confirm or correct it before the rule is recorded in `navigation/plan.md`.

## Static finding (the hypothesis to confirm)

The 3D renderer (`NormalDisplay`, `CE66`) walks at most **10 cells** down the facing corridor — depth `0` (the player's own cell) through depth `9` — and stops at the first facing wall that is not open (normal door, magic door, and solid wall all block: `CF24`).

Light is the second bound. Each refresh (`C660`) computes a 16-bit light level `m026E:m026F`:

- high byte = `ambientLight` high byte (`0x0226`) + lit torch **physical illumination** (torch object byte 7)
- low byte = `ambientLight` low byte (`0x0227`) + lit torch **magic illumination** (torch object byte 8)

`SWI_0` (`0x0C384`) maps that to a dot frequency (`0x022D`) for each cell: for depth `N`, `A = light − 7 − N`; `A ≥ 0` → solid, `−6…−1` → dotted, `≤ −7` → `0xFF` (no draw). So a creature at depth `N` is drawn — and therefore seen — only while `N < light`, capped by the 10-cell walk.

The renderer picks the light channel from the creature's **"See" byte** (offset 02, `MonsterData` at `DABB`): ordinary creatures (See = 0) use physical light; magical creatures (See ≠ 0 — scorpion, wraith, galdrog, demon, wizard) use magic light.

Constants: `ambientLight` is `0x0000` in normal play (RAM `0x0200–0x4000` cleared at boot; written again only at the wizard's death → `0x0713`). Torch physical/magic illumination: Pine `7/0`, Lunar `10/4`, Solar `13/11`, each clamped to remaining minutes as it burns (`D19B`).

Predicted reach = `min(light, 10)` cells.

## TODO

Write a Lua plugin (mirroring `command-readiness`) that boots the game to live play — auto-prime at frame 300, gate on `displayFunction == 0xCE66` — then hand-builds a straight corridor and runs a sweep. For each `(light, depth)` case it places one creature, lets the 3D screen redraw, and decides "drawn" by diffing the visible play-field buffer against a no-creature baseline captured at the same light level. It logs `config,light,depth,visible`.

Sweep two creature kinds — one See = 0 (physical channel), one See ≠ 0 (magic channel) — each over its own light channel `0…13` and depth `0…10`.

## Recommendations

Each is a default; all are changeable.

1. **Light control — write `ambientLight` directly, torch off.** Set `torchPtr = 0` and poke `0x0226:0x0227` = `(physical, magic)` — exactly the `m026E:m026F` the renderer reads, and it sidesteps the torch-minutes dimming. *(Alternative: light a real torch and vary its minutes — faithful but couples light to the burn-down code.)*
2. **Visibility detection — play-field buffer diff.** Capture the visible play field (via `activeScreen` `0x0209` → descriptor → `0x1000`/`0x2800`) with the creature present and absent, and diff. No pixel decoding — walls/objects are identical, so any difference is the creature. *(Alternative: read `dotFrequency` `0x022D` timed to the redraw — cheaper but racy.)*
3. **Creature freezing — `wizardDead` (`0x022B`) = FF.** `T_MoveCreature` (D041) gates on it and skips all actions, so placed creatures stay put.
4. **Corridor — hand-built maze bytes at `0x05F4`.** A straight open run up column 16 from the player's cell.
5. **Creature kinds — spider (See=0) and scorpion (See=FF).** One per light channel; the type sets the picture, the See byte sets the channel.
6. **Sweep `0…13` light and `0…10` depth.** Covers no-torch (0) through Solar (13), one past the 10-cell cap.
7. **Plugin, not autoboot script** — matches the current sandboxes and the production plugin layout.

## Success criteria

- The logged `visible` column matches `depth ≤ 9 && depth < light`, with `light` = physical for See = 0 and magic for See ≠ 0.
- Depth 10 is never visible (the 10-cell cap).

Outcome lands in `docs/plans/navigation/plan.md` (replacing the *Line-of-sight extent* unknown) and a thread in `docs/plans/navigation/conversation.md`; this folder is deleted after use.
