# Perception

_See [overview.md](../overview.md) for project context and architecture._

This document specifies perception — the perceptible state: what the player can perceive at a single instant, gated by sight and by the display mode. Perception is the source of the observation (the policy's input array) and the reference for the project's "the agent perceives what the player perceives" principle. It is instantaneous and stateless: the environment reports only what is visible *now*; memory is the agent's job, built in a wrapper, never held by the environment.

## Purpose

Perception answers one question: what does the player perceive right now? The answer is the perceptible state, assembled from the channels below and passed through two gates. The observation is that state serialized into a fixed-shape `Dict` (grid + scalars).

## Channels

- **State.** Thirteen raw fields — `game_mode`, `at_floor`, `at_cell_x`, `at_cell_y`, `at_heading`, `ambient_light`, `player_weight`, `player_strength`, `m0221`, `effective_light`, `heart_beat_interval`, `player_fainting`, `evil_wizard_dead` — shipped as uint16. Always present: the player knows their own body and position even in the dark.
- **Hands.** The two held objects, always present on the status line. An unrevealed object shows its class; a revealed object shows its proper name.
- **Creatures.** The creature array — `alive`, `type`, `X`, `Y` per slot — gated by light.
- **Objects.** The pack (inventory) and the floor objects at the player's cell — the pack gated by mode, the floor gated by light.
- **Map.** The maze cells within the visible corridor — gated by light.

Sound is a deferred channel — see `sound/plan.md`.

## Gates

Two gates decide what reaches the agent.

### Light — line-of-sight

The dungeon is visible only while there is light. The reach is `min(light, 10)`, where `light` is the effective light level `effective_light` (`m026E:m026F`) and the reach is a corridor walk from the player's cell in the facing direction, stopping at the first non-open edge (see `navigation/plan.md`). `light == 0` blanks the dungeon channels entirely — pure blackout, where even the own-cell walls vanish.

### Mode — LOOK vs EXAMINE

The display is modal, driven by `displayFunction` (`0x02B2–0x02B3`): `0xCE66` (LOOK) draws the dungeon, `0xD495` (EXAMINE) draws the inventory. Only one view is active at a time, so the dungeon and the inventory are mutually exclusive:

- LOOK + `light > 0` → maze, creatures, floor objects.
- EXAMINE → the pack.
- Either → state fields and hands.

## No memory

Perception is instantaneous. The environment holds no "visited cell," no "seen creature," no explored-vs-unexplored flags — nothing persists across steps. Memory is the agent's job, built in a wrapper that accumulates whatever the policy wants. For the POC the bar is immediate responsiveness — the agent must see the monster ahead and the wall ahead — even if it repeats itself; memory and action-space masking are deferred training-quality work, not correctness.

## Encoding

The observation is a `Dict` with two keys, processed by Stable-Baselines3's `MultiInputPolicy` — a CNN over the grid and an MLP over the scalars, concatenated:

- **`grid`** — a `Box(C, 32, 32)` one-hot multi-channel image:
  - cell type: open, normal door, magic door, wall — one channel each
  - creatures: one channel per type, `1` where a visible creature of that type sits
  - objects: one channel per class, `1` where a visible floor object of that class sits
  - player: `1` at the player's cell
  - visible: `1` for cells in view — the light + line-of-sight mask
- **`scalars`** — a `Box(S,)` of the 13 self-fields plus the two hand specifiers and the lit torch's minutes.

The one-hot grid gives the CNN the spatial structure it needs — a CNN's local filters and translation invariance are the right inductive bias for a maze, where a flat MLP would treat adjacent cells as unrelated numbers and relearn each spatial pattern at every position. The scalars carry the body and status numbers that have no place on the grid. Scalar magnitudes are normalized by a wrapper (e.g. `VecNormalize`) at training time, not baked into the environment.

## Decisions

- **No novelty in perception.** "First time seen, explored, or revealed" is not a perception channel — it is the reward wrapper's bookkeeping for the information-gain layer. Perception reports only what is visible now; the reward reads true state directly (see `reward/plan.md`), and novelty never enters the step return.
- **Modal perception.** LOOK vs EXAMINE via `displayFunction` — the dungeon and the inventory are mutually exclusive.
- **No memory.** Perception is instantaneous; the environment holds no history.
- **Light-gated via line-of-sight.** The dungeon channels appear only while `effective_light > 0`, within the corridor walk.
- **`Dict` + `MultiInputPolicy`.** The observation is a `Dict` of grid + scalars — a CNN reads the grid's spatial structure, an MLP reads the scalars.

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/plans/state/plan.md` | The thirteen raw state fields |
| `docs/plans/creatures/plan.md` | The creature array — slots, types, and positions |
| `docs/plans/objects/plan.md` | Hands, pack, and the reveal distinction |
| `docs/plans/sound/plan.md` | The auditory cue list — distance, sound type, source |
| `docs/plans/navigation/plan.md` | The 32×32 maze and the line-of-sight walk |
| `docs/plans/reward/plan.md` | The reward and its novelty memory |
