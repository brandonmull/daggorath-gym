# Creature Detection

_See [overview.md](../overview.md) for project context and architecture._

This document records what we know and don't know about the game's creature array, and the open questions that must be answered before any design work begins. It is deliberately not a design spec — architecture and wire format are deferred until the questions below are settled.

## Purpose

Reward and termination may need to know about creatures — how many are alive, of what type, and whether one shares the player's cell. Before deciding how to sample and ship that data, this document establishes what is actually known and surfaces the questions that would change the answer.

## Knowns

The creature array is 32 slots at 0x03D4, 17 bytes per slot. The disassembly walks it with a 17-byte stride.

| Address | Meaning |
|----------|---------|
| slot + 0 | Strength — max hitpoints, 2 bytes big-endian; also the kill reward (player gains strength / 8) |
| slot + 2 | Magic attack — multiplies attacker strength in the damage formula |
| slot + 3 | Magic shield — incoming magic damage multiplier (0x80 = full damage) |
| slot + 4 | Physical attack — multiplies attacker strength in the damage formula |
| slot + 5 | Physical shield — incoming physical damage multiplier (0x80 = full damage) |
| slot + 10 | Damage taken — hitpoints left = strength - damage |
| slot + 12 | Alive — `FF` = alive, `0` = dead or empty slot (`DEC` marks living, `CLR` marks dead) |
| slot + 13 | Type — one of the 12 types catalogued below |
| slot + 14 | Direction |
| slot + 15 | Y coordinate — same grid as the player |
| slot + 16 | X coordinate |

Verified from the disassembly:

- Kills grant strength equal to the creature's strength divided by eight, so the player-strength delta is already a kill signal.
- Killing type 0x0A (Demon) advances the player to level 4; killing 0x0B (Wizard) flips `evil_wizard_dead`.
- A kill decrements the creature's type entry in `creatureCounts`, a 12-byte per-type count table pointed to by 0x0282; the table lives at `0x0398 + currentLevel × 12` ("12 bytes each (one byte to count each type of creature)", C75B).
- The array holds the monsters of the current level (comment at C790) and is rebuilt on level change; at most 32 creatures exist per level, and every five minutes `T4_MakeCreature` (D027) adds one random creature of type 0x02–0x09 — "not spider, snake, demon, or wizard" (D039).
- `GetCreatureAt` is called with the player's Y/X, so creature and player coordinates share a grid.
- Combat is a strength pool versus a damage pool. Each landed hit adds to the defender's pool (creature offset `0x0A`; the player's `m0221` at 0x0221), and death is the damage pool overtaking the strength pool — so hitpoints left = strength - damage. See `docs/findings/combat-model.md`.
- An unseen creature announces itself by sound: Chebyshev distance ≤ 8, volume 255 - 31×distance, and the sound is the creature's type. The disassembly reads a 2-cell corridor gate, but this is disputed (see `sound/plan.md`). The Seer scroll (`scrollType`, 0x0294) reveals all creatures on the map.

The 12-type catalogue is resolved. Every type token (the byte at `slot + 13`) indexes three parallel ROM tables laid out in the same order — sound routine (C7DC), creature picture (DAA3), and an 8-byte creature-class entry (DABB). The class entry's first two bytes are the creature's strength, copied to `slot + 0`.

| Token | Name          | Strength      |
|-------|---------------|---------------|
| 0x00  | Spider        | 32 (0x0020)   |
| 0x01  | Snake         | 56 (0x0038)   |
| 0x02  | Giant         | 200 (0x00C8)  |
| 0x03  | Blob          | 304 (0x0130)  |
| 0x04  | Knight        | 504 (0x01F8)  |
| 0x05  | Hatchet-giant | 704 (0x02C0)  |
| 0x06  | Scorpion      | 400 (0x0190)  |
| 0x07  | Shield-knight | 800 (0x0320)  |
| 0x08  | Wraith        | 800 (0x0320)  |
| 0x09  | Galdrog       | 1000 (0x03E8) |
| 0x0A  | Demon         | 1000 (0x03E8) |
| 0x0B  | Wizard        | 8000 (0x1F40) |

Traced in the disassembly (`docs/references/game/code.md`):

- `CreateCreature` (CFA5) stores the type at `slot + 13` ("Set the type"), indexes the class table at `type × 8 + DABB` ("Add to creature-class data table"), and copies its eight bytes into the slot ("8 bytes of init data" / "Copy the 8 bytes of initial data").
- `MonsterData` (DABB) is that class table — one 8-byte entry per type in token order. Its header names the fields (`To-kill  See  MShield  Damage  PShield  task-speed`); "To-kill" is the leading two-byte strength, and the middle four are the combat multipliers — `See` = magic attack, `MShield` = magic shield, `Damage` = physical attack, `PShield` = physical shield (slots + 2 through + 5). See `docs/findings/combat-model.md`.
- The kill site reads the strength back as 16 bits: `D347: LDD ,U` ("Monster strength"), `DRight3` at D37F ("divide by 8"), added to `pStrength`.
- `CreaturePictures` (DAA3) and `SoundEffectsRoutines` (C7DC) name all 12 types in token order; C7DC's comments run `00 Spider` through `0B Wizard`, so a creature's sound effect number is its type token.
- The level-spawn loop walks the count table from type 0x0B down to 0x00 ("Start with most powerful", C781), matching the strength column (Wizard strongest).
- The three ROM tables agree on the short names above; the level listings use longer display names (`CLUB GIANT` for Giant, `PLAIN KNIGHT` for Knight).

## Unknowns

- **`creatureCounts` semantics.** Kills decrement it. It is not traced whether spawning also decrements it, so it is unclear whether the table means "alive right now" or "still to be placed."
- **Read atomicity.** Each byte read is atomic, but a 32-slot scan spans many instructions. A creature moving or dying mid-scan could produce a torn snapshot. **Important investigation point** — a torn snapshot corrupts the exact observation this module exists to deliver. Deferred to `sandbox/read-atomicity/`.
- **Player death.** On death the game returns to demo mode and hangs; it is not traced what happens to the array or the count table in that state.

## Decisions

- **Creatures are needed.** The Safety potential and player-perception both require them; strength-delta alone gives kills, not proximity or type.
- **Sample the array, not just `creatureCounts`.** Counts have no positions, so no proximity. Sample alive + type + X/Y per slot; the count table is at best a supplement.
- **Positions, sight-gated.** Positions are the "sight" channel; the sound channel covers what sight can't.
- **Kill detection is typed and frame-rate.** A kill is a slot going alive→dead, and the slot's type is what died. Lua samples every frame, so there's no race; strength-delta is only the aggregate.
- **No level-switch window.** The level-setup routine zeroes the whole array (`SWI_11` over 0x03D4–0x05F4) and re-spawns — the array is never garbage.
- **Type and starting strength; withhold current hitpoints.** The player gets no health bar; starting strength (slot + 0) is the power tier, which type already roughly encodes.
- **Sight-gated positions via line-of-sight.** A creature is "seen" when the navigation module's line-of-sight reaches it; everything else is heard.
- **No memory of the unseen.** Stale coordinates lie; the sound channel is the game's own "behind me" cue.
- **Sound as proximity.** The sound channel (type + distance, no direction, multi-slot) is the proximity observation for unseen creatures.
- **Combat is a reward-level interpretation, not a module.** Strikes come from existing signals (`!!!`, alive flags, `m0221`); the event channel (see `events/plan.md`) is deferred.

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/references/game/ram.md` | Memory map — the creature array layout and `creatureCounts` |
| `docs/references/game/code.md` | Disassembly — spawn/death paths, `GetCreatureAt`, creature type tokens |
| `docs/findings/combat-model.md` | The strength-vs-damage combat model and the sound proximity channel |
| `docs/plans/sound/plan.md` | The auditory proximity channel — answers the sound-as-proximity question |
