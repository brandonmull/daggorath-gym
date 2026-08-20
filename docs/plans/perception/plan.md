# Perception

_See [overview.md](../overview.md) for project context and architecture._

This document specifies perception — the perceptible state: what the player can perceive at a single instant, gated by sight and by the display mode. Perception is the source of the observation (the policy's input array) and the reference for the project's "the agent perceives what the player perceives" principle. It is instantaneous and stateless: the environment reports only what is visible *now*; memory is the agent's job, built in a wrapper, never held by the environment.

## Purpose

Perception answers one question: what does the player perceive right now? The answer is the perceptible state, assembled from the channels below and passed through two gates. The observation is that state serialized into a fixed-shape `Dict` of six channels.

## Channels

- **Scalars.** Eighteen raw self-fields — `game_mode`, `at_floor`, `at_cell_x`, `at_cell_y`, `at_heading`, `ambient_light_physical`, `ambient_light_magical`, `effective_light_physical`, `effective_light_magical`, `torch_minutes`, `torch_physical_light`, `torch_magic_light`, `player_weight`, `player_strength`, `m0221`, `heart_beat_interval`, `player_fainting`, `evil_wizard_dead` — shipped as uint16. Always present: the player knows their own body and position even in the dark.
- **Hands.** The two held objects as specifier indices (the class until revealed, the proper name after). Always present.
- **Pack.** The backpack as specifier slots — gated by mode (EXAMINE).
- **Creatures.** The creature array — `alive`, `type`, `X`, `Y` per slot, absolute — gated by light.
- **Objects.** Floor objects — `specifier`, `X`, `Y`, absolute — gated by light.
- **Map.** The maze edge bytes plus the per-cell hole/ladder feature — gated by light, stacked as two planes of one image.

Sound is a deferred channel — see `sound/plan.md`.

## Gates

Two gates decide what reaches the agent.

### Light — line-of-sight

The dungeon is visible only while there is light. The reach is a corridor walk from the player's cell in the facing direction, stopping at the first non-open edge (see `navigation/plan.md`). The light is two channels — `effective_light_physical` (`m026E`) drives the corridor walk (`reach = min(effective_light_physical, 10)`), and `effective_light_magical` (`m026F`) drives magic doors and magical creatures (`reach = min(effective_light_magical, 10)`). `effective_light_physical == 0` blanks the dungeon channels entirely — pure blackout, where even the own-cell walls vanish.

### Mode — LOOK vs EXAMINE

The display is modal, driven by `displayFunction` (`0x02B2–0x02B3`): `0xCE66` (LOOK) draws the dungeon, `0xD495` (EXAMINE) draws the inventory. Only one view is active at a time, so the dungeon and the inventory are mutually exclusive:

- LOOK + `light > 0` → maze, creatures, floor objects.
- EXAMINE → the pack.
- Either → state fields and hands.

The mode gate needs `displayFunction` on the wire: it is read by the readiness gate today but not shipped in the state frame, so the frame must add a `display_function` field (or a LOOK/EXAMINE flag) before `as_perceived()` can apply this gate.

## No memory

Perception is instantaneous. The environment holds no "visited cell," no "seen creature," no explored-vs-unexplored flags — nothing persists across steps. Memory is the agent's job, built in a wrapper that accumulates whatever the policy wants. For the POC the bar is immediate responsiveness — the agent must see the monster ahead and the wall ahead — even if it repeats itself; memory and action-space masking are deferred training-quality work, not correctness.

## Encoding

The observation is a fixed-shape `Dict` of six channels, defined in code as `PERCEIVED_SPACE` in `state.py`. Every channel is absolute and gated; agent-side wrappers translate to relative.

- **`scalars`** — `Box(18,)` uint16: the eighteen self-fields.
- **`hands`** — `Box(2,)` uint8: the two held objects as specifier indices (255 = empty).
- **`pack`** — `Box(8,)` uint8: the backpack as specifier indices, zero-padded.
- **`creatures`** — `Box(32, 4)` uint8: per slot, `alive`/`type`/`X`/`Y`; dead slots zeroed.
- **`objects`** — `Box(8, 3)` uint8: visible floor objects as `specifier`/`X`/`Y`, zero-padded.
- **`map`** — `Box(2, 32, 32)` uint8: two planes — plane 0 the maze edge bytes, plane 1 the per-cell feature byte (0 none, 1 hole in ceiling, 2 ladder in ceiling, 3 hole in floor, 4 ladder in floor), both `0xFF` unseen.

Only `scalars` is sampled today; the five world channels are zeroed stubs until creatures, objects, and maze land on the wire and the perception gates fill them. The map's representation is settled: the wire carries the raw edge bytes, and the perceived map keeps visible cells' edge bytes while marking unseen cells `0xFF` (see `navigation/plan.md`).

The map is static geometry; the entity tables and the scalars are explicit values. Scalar magnitudes are normalized by a wrapper (e.g. `VecNormalize`) at training time, not baked into the environment.

## Decisions

- **No novelty in perception.** "First time seen, explored, or revealed" is not a perception channel — it is the reward wrapper's bookkeeping for the information-gain layer. Perception reports only what is visible now; the reward reads true state directly (see `reward/plan.md`), and novelty never enters the step return.
- **Modal perception.** LOOK vs EXAMINE via `displayFunction` — the dungeon and the inventory are mutually exclusive.
- **No memory.** Perception is instantaneous; the environment holds no history.
- **Light-gated via line-of-sight.** The dungeon channels appear only while `effective_light_physical > 0`, within the corridor walk.
- **`Dict` + `MultiInputPolicy`.** The observation is a six-channel `Dict` — a CNN reads the map's spatial structure, an MLP reads the entity tables and the scalars.
- **Shared object index.** Objects in the observation are reported as their specifier index (0–30), the same index the action's `object` slot uses — the agent commands an object by reusing the index it observed, with no learned translation between the two.
- **Absolute-and-gated env, wrappers translate.** The environment reports absolute, perception-gated state — positions in the world's own coordinates, filtered only by line-of-sight, display mode, and light. Relative translation (egocentric positions, survival margins), normalization, and memory are agent-side wrapper concerns, not the environment's. The observation keeps the player's absolute frame (`at_cell_x`, `at_cell_y`, `at_heading`) so a wrapper can translate absolute → relative.
- **True state for the reward; `as_perceived` for the policy.** The environment holds the true state — absolute and ungated — as a well-structured value object the reward wrapper interrogates directly. The state model's `as_perceived()` method applies the perception gates and returns the observation. Two consumers, one source: the reward reads the ungated true state; the policy reads the gated perceived state.

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/plans/state/plan.md` | The eighteen raw state fields |
| `docs/plans/creatures/plan.md` | The creature array — slots, types, and positions |
| `docs/plans/objects/plan.md` | Hands, pack, and the reveal distinction |
| `docs/plans/sound/plan.md` | The auditory cue list — distance, sound type, source |
| `docs/plans/navigation/plan.md` | The 32×32 maze and the line-of-sight walk |
| `docs/plans/reward/plan.md` | The reward and its novelty memory |
