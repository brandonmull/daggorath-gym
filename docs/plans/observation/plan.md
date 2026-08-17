# Observation

_See [overview.md](../overview.md) for project context and architecture._

This document records what the agent observes — the single array that combines the five perception channels — and the open questions that must be answered before the observation space is fixed. It is deliberately not a design spec: the encoding decisions are recorded here as options, deferred to later sessions.

## Purpose

The observation is the one array the RL agent sees each step. Five channels feed it, each with its own plan: the raw state fields, sight-gated creature positions, the sound cue list, hands and pack, and the explored map. This document is where they combine into one space, and where the encoding decisions that span them are recorded.

## Knowns

Five channels feed the observation:

- **State.** Twelve raw fields — `game_mode`, `at_floor`, `at_cell_x`, `at_cell_y`, `at_heading`, `ambient_light`, `player_weight`, `player_strength`, `m0221`, `heart_beat_interval`, `player_fainting`, `evil_wizard_dead` — shipped as uint16. This is the only channel implemented today: `observation_space` is `Box(12,) uint16`.
- **Creatures.** Sight-gated positions: a creature appears with its type and position only while the player sees it; there is no memory of the unseen. The count is variable.
- **Objects.** Two hands, always visible, plus the pack, variable in size. An unrevealed object shows its class; a revealed object shows its proper name.
- **Sound.** A fixed-size "nearest N" list of audible cues — distance, sound type, and source — with no direction, several sources at once.
- **Map.** Explored-with-memory: a persistent 32×32 cell map, each cell one of unknown, wall, open, normal door, or magic door.

## Open Questions

The encoding decisions, recorded as options and deferred to later sessions:

- **Flat `Box` or `Dict`?** A flat `Box` concatenates every channel into one array and works with Stable-Baselines3's `MlpPolicy` directly. A `Dict` keeps heterogeneous shapes separate — a 2D map plane beside flat lists — but needs `MultiInputPolicy` and a custom feature extractor. A `Dict` only earns its complexity once a convolutional map extractor is wanted.
- **Map encoding.** How to encode the explored 32×32 map: a flat (1024,) uint8 of five cell states, a (32, 32) 2D plane, or five one-hot (5, 32, 32) planes. The flat form matches a flat `Box`; the 2D and one-hot forms matter once a CNN arrives.
- **Seen-creature slots.** How many slots, and what fills them: cap at the nearest N seen, padded with a sentinel, or pad all 32 array slots. And whether position is absolute (x, y) or relative (dx, dy) to the player.
- **Sound slots.** The size N of the nearest-N list, and whether a seen creature appears in both channels — seen and heard, like a real player — or sound reports only unseen creatures. The sound plan says both "proximity for unseen creatures" and "the full auditory scene," which conflict until this is settled.
- **Object slots.** The bound on the pack (the two hands are fixed), and how reveal appears in the encoding. One option: each slot is a specifier index 0–30 — the commands module's 31 specifiers enumerate bare class and proper name, so an unrevealed object is simply its bare-class specifier.
- **Normalization.** Ship the raw uint16 values and normalize in a wrapper later, or ship scaled values. The shape is the design question now; scaling is a knob for the first training run.

## Decisions

- **No novelty in the observation.** "First time seen, explored, or revealed" is not an observation channel — it is the reward wrapper's bookkeeping for the information-gain layer. The observation reports perception only; the reward reads true state directly (see `reward/plan.md`), and novelty never enters the step return.

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/plans/state/plan.md` | The twelve raw state fields |
| `docs/plans/creatures/plan.md` | Sight-gated positions and the no-memory rule |
| `docs/plans/objects/plan.md` | Hands, pack, and the reveal distinction |
| `docs/plans/sound/plan.md` | The auditory cue list — distance, sound type, source |
| `docs/plans/navigation/plan.md` | The 32×32 maze and the explored-with-memory map |
| `docs/plans/reward/plan.md` | The reward and its novelty memory |
