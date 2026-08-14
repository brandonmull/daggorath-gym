# Creature Detection

_See [overview.md](../overview.md) for project context and architecture._

This document records what we know and don't know about the game's creature array, and the open questions that must be answered before any design work begins. It is deliberately not a design spec — architecture and wire format are deferred until the questions below are settled.

## Purpose

Reward and termination may need to know about creatures — how many are alive, of what type, and whether one shares the player's cell. Before deciding how to sample and ship that data, this document establishes what is actually known and surfaces the questions that would change the answer.

## Knowns

The creature array is 32 slots at 0x03D4, 17 bytes per slot. The disassembly walks it with a 17-byte stride.

| Address | Meaning |
|----------|---------|
| slot + 0 | Strength — max hitpoints; also the kill reward (player gains strength / 8) |
| slot + 10 | Damage taken — hitpoints left = strength - damage |
| slot + 12 | Alive — `FF` = alive, `0` = dead or empty slot (`DEC` marks living, `CLR` marks dead) |
| slot + 13 | Type — 12 creature types; `0x0A` = Demon, `0x0B` = Wizard |
| slot + 14 | Direction |
| slot + 15 | Y coordinate — same grid as the player |
| slot + 16 | X coordinate |

Verified from the disassembly:

- Kills grant strength equal to the creature's strength divided by eight, so the player-strength delta is already a kill signal.
- Killing type 0x0A (Demon) advances the player to level 4; killing 0x0B (Wizard) flips `evil_wizard_dead`.
- A kill decrements the creature's type entry in `creatureCounts`, a 12-byte per-type count table pointed to by 0x0282.
- The array holds the monsters of the current level (comment at C790) and is rebuilt on level change; at most 32 creatures exist per level, and one random creature spawns every five minutes.
- `GetCreatureAt` is called with the player's Y/X, so creature and player coordinates share a grid.
- Combat is a strength pool versus a damage pool. Each landed hit adds to the defender's pool (creature offset `0x0A`; the player's `m0221` at 0x0221), and death is the damage pool overtaking the strength pool — so hitpoints left = strength - damage. See `docs/findings/combat-model.md`.
- An unseen creature announces itself by sound: Chebyshev distance ≤ 8, volume 255 - 31×distance, and the sound is the creature's type. The disassembly reads a 2-cell corridor gate, but this is disputed (see `sound/plan.md`). The Seer scroll (`scrollType`, 0x0294) reveals all creatures on the map.

## Unknowns

- **Type catalogue.** Only Demon and Wizard are confirmed. The other ten types and their strengths live in ROM data tables not yet catalogued. **Blocks the observation** — the creature array's type field and the sound channel's "sound = type" cue can't be populated until this is catalogued.
- **Combat multipliers.** Creature offsets 0x02–0x05 feed the damage formula but are not individually decoded.
- **`creatureCounts` semantics.** Kills decrement it. It is not traced whether spawning also decrements it, so it is unclear whether the table means "alive right now" or "still to be placed."
- **Read atomicity.** Each byte read is atomic, but a 32-slot scan spans many instructions. A creature moving or dying mid-scan could produce a torn snapshot. **Important investigation point** — needs dedicated discussion; a torn snapshot corrupts the exact observation this module exists to deliver.
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
