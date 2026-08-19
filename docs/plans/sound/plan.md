# Sound

_See [overview.md](../overview.md) for project context and architecture._

This document records what we know and don't know about the game's sound system, and the open questions that must be answered before any design work begins. It applies the perception principle — the agent perceives what the player perceives — to the ears rather than the eyes.

## Purpose

Sound is how the player locates creatures they cannot see and reads their own body. A creature announces itself by type and loudness before it enters view; the heartbeat announces strain. The state and creature modules report numbers; this document considers whether, and how, to give the agent the *auditory* channel.

## Knowns

The game synthesizes sound through a 6-bit DAC and plays one of 23 named effects:

| Sound | Meaning |
|-------|---------|
| 0x00–0x0B | Creature types — the sound number *is* the creature type (spider, snake, … demon, wizard) |
| 0x0C–0x11 | Object use — flask, ring, scroll, shield, sword, torch |
| 0x12 | Player hit |
| 0x13 / 0x16 | Wizard beam / wizard strike |
| 0x14 | Wall hit |
| 0x15 | Creature dying |

- Effects play through SWI_1B (full volume) or SWI_1C (volume in B, stored to `m0261` at 0x0261, then output to PIA1_DA at 0xFF20). Playback is transient — the DAC is cleared after each effect.
- **The approach sound is distance-scaled** (already recorded in `docs/findings/combat-model.md`): a creature announces itself as "type T, N cells away on my line" — Chebyshev distance ≤ 8, within a 2-cell corridor, 50% of the time, volume 255 − 31×distance.
- **The heartbeat is always audible** (`hearHeart`, 0x02B1) and its rate is the heart rate already sampled as `heart_beat_interval`.
- The wizard's beam toggles a square wave (`beamSound` 0x029C, `beamSoundVal` 0x029D) during cut scenes.

The key property: the DAC carries a *mixed, transient* waveform. What a player actually distinguishes — a spider three cells ahead, a heartbeat racing — is reconstructed from the sound *sources*, not read off the waveform. The game computes each source separately; the DAC is only the sum.

## Unknowns

- **Heartbeat audibility.** When does `hearHeart` clear — fainting, death, or never? Not traced.
- **Effect internals.** Each of the 23 sound routines is a small waveform program; their shapes are irrelevant if cues are derived, but they are not catalogued.
- **`m0261` semantics.** Identified as the volume register (was `??` in the RAM map), but its exact interaction with the DAC writes is not traced.
- **Corridor gate.** The disassembly appears to gate the approach sound to a 2-cell corridor (`min(|dx|,|dy|) ≤ 2`), but this contradicts lived experience of hearing creatures off-axis. Needs a sandbox to determine when approach sounds actually fire — a *separate experiment* from the navigation module's line-of-sight, in its own sandbox subfolder.

## Decisions

- **Derive the cues; never read the DAC.** The DAC carries a mixed, transient amplitude with no source attribution — the player distinguishes *sources*, not the waveform, and the game discards source structure when it sums them. The cues (creature type + distance, heartbeat, combat sounds) are derived from RAM instead.
- **Sound is a Python derivation, not a module.** No new Lua sampling — the cues are a transform over creature positions, player position, heart rate, and combat signals.
- **Deterministic "audible now."** The 50% coin flip is dropped — it's rolled per sound event and washes out at the agent's timescale. The corridor gate is *not* settled (see Unknowns).
- **Per-sound granularity; three properties.** Each sound carries distance (loudness), sound type (the effect), and source (creature type / object class / player / environment / wizard). Sound conveys *no direction*: the game is mono, so loudness carries distance and nothing carries bearing. Multiple sounds at once must be representable (a fixed-size "nearest N" list).
- **Sound is the full auditory scene, not just creature proximity.** Creatures aren't the only source — objects (use sounds), the player (hit, heartbeat), the environment (wall hit), and the wizard (beam, strike) all sound too; a creature alone makes more than one sound (approach, dying).
- **The sound→source association is a curriculum item.** The source is exposed alongside each sound for now; in a later stage it's removed, so the agent learns to associate sound with source itself.
- **Sound answers the creature module's "sound as proximity."** For unseen creatures, the auditory channel (distance + sound type + source) is the proximity perception, alongside light-gated positions for seen creatures.

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/references/game/code.md` | Disassembly — sound dispatch, effect table, approach-sound math |
| `docs/findings/combat-model.md` | The distance-scaled approach sound model |
| `docs/plans/creatures/plan.md` | The "sound as proximity" question this module answers |
