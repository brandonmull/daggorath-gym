# Reward

_See [overview.md](../overview.md) for project context and architecture._

This document describes the reward — an agent-side component, separate from the environment, that turns game state into a training signal. It follows the perception principle from the object and creature modules — the agent perceives what the player perceives — and shapes reward from that same state.

## Purpose

Reward answers one question: did the agent's situation just get better or worse? The game's own signals — strength, light, holdings, survival, the win — each answer that question in part. This document assembles them into a single signal.

## Architecture

Reward is not computed by the environment. The environment is the objective world: it holds the true state internally and reports only what the player perceives. The reward is a separate, agent-side wrapper that reads that true state and assigns it value.

- The environment (`DaggorathEnv`) holds the true state — creatures, objects, maze, player fields — as internal attributes. Its `step()` returns the perception-only observation, a placeholder reward, the objective game-over fact, and metadata. Nothing hidden rides in `info`.
- The reward wrapper is agent-side code, plugged in around the environment. It reads the environment's true state through the environment object, computes one scalar reward, and returns the observation unchanged.
- The scalar is a constraint: Stable-Baselines3 stores reward as a one-dimensional array per step and computes returns and advantages with scalar arithmetic, so the wrapper collapses spikes, potentials, and information gain into a single number.

The environment reports facts and events — including the game's own accomplishments — and the wrapper decides what they are worth. "Hidden from the agent" means hidden from the policy's input, the observation, not hidden from the reward, which is supposed to value true state.

Termination splits the same way: the environment reports the objective game-over fact and its cause (death → `game_mode` FF; the win → ring type 0x12), and the wrapper assigns the terminal value (-1 for death, +1 for the win). The two-stage win's boundary is the open "Termination coupling" question below.

## Framework

Reward has three layers, each doing a distinct job:

- **Spikes** — the objective itself: what was achieved. One-shot, large, temporally-local rewards for kills, pick-ups, and the win, so the agent learns early that combat pays off.
- **Potentials** — potential-based shaping: how good the situation is now. The term γ·Φ(next) − Φ(current) scores the situation and densifies the gradient between spikes; it never changes the optimal policy, only the speed of learning.
- **Information gain** — intrinsic motivation: what was learned. A novelty-bounded reward for the unknown→known transition, tracked by the novelty memory below. It generalizes across cells, objects, and creatures — and the VISION/SEER scrolls are the same mechanism.

Because the observation mirrors player perception, all three layers draw from the same state.

## Potentials

Conditions the agent should seek or avoid, each drawn from a state signal:

| Potential | Signal | Sampled today? |
|-----------|--------|----------------|
| Strength | `player_strength` — grows with every kill | Yes |
| Sight | torch minutes remaining (lit torch, slot + 6) | No — object detection |
| Survival | `player_strength − m0221` — the margin to death | Yes |
| Holdings | powerful objects in hand or pack | No — object detection |
| Safety | absence of creatures in or near the cell | No — creature detection |
| Strain | `player_weight` | Yes |
| Incapacity | `player_fainting` | Yes |

Use the survival margin, not raw heart rate: exertion rises in combat as much as from being hit, so the margin — which kills raise — rewards fighting without punishing the effort. Strength rises only through kills and scales with the creature's power, so the strength potential is a smooth echo of the kill spike, not a substitute for it.

## Events

One-shot rewards for discrete happenings:

| Event | Signal |
|-------|--------|
| Kill | a fight ends in victory — the spike that rewards engaging combat |
| Pick up / drop | object location field moves floor → hand/pack |
| Reveal | strength-to-reveal field (slot + 11) → 0 |
| Incant | ring word (slot + 7) clears, proper name changes |
| Descend | a deeper `at_floor` than any reached this episode |
| Wizard dead | `evil_wizard_dead` → FF |
| Win | the incanted ring's proper type (slot + 9) → 0x12 (FINAL) |

The win is two events — the Wizard dies, then the Supreme Ring is incanted — and both merit reward. The terminal is detected by the ring's own field: incanting FINAL writes 0x12 (FINAL) into the held ring's proper-type field (slot + 9) and clears its word (slot + 7) in the same burst that renders the win screen. That field is the win's only persistent RAM trace — `PlayerWins` writes no durable flag (its `initBeamIn` write is cleared within the same beam call), and the game then freezes in an endless loop, so there is no separate win-screen flag to sample.

## Novelty Memory

Information gain is novelty-bounded: the unknown→known transition pays once. The memory that enforces this lives in the reward wrapper — it is valuation bookkeeping, not perception, so it never appears in the observation and never leaves the wrapper. It resets each episode.

The memory holds two kinds of entries: **flags**, for facts learned in a single exposure, and a **counter**, for a skill learned only through repetition.

### Flags

One-shot, monotonic milestones — each fires once, then is silent. Every key is read from true state.

| Milestone | Key | Marked known when |
|-----------|-----|-------------------|
| Cell explored | `(floor, x, y)` | the cell is in line-of-sight, or a VISION scroll reveals it — the dense *advance* term |
| Object encountered | object address | the object's location (`slot + 5`) leaves `FF` (monster-held) |
| Object revealed | object address | the object's strength-to-reveal (`slot + 11`) → 0 |
| Type heard | creature type token | the type first becomes audible (approach sound) |
| Type seen | creature type token | the type first becomes visible (line-of-sight) |
| Instance seen | `(floor, slot)` | a specific creature first becomes visible |

Exploration reward is two-tier. The per-cell milestone is the **advance** term — dense and small, its job is credit assignment over long corridors. The **discovery** term is structural: line-of-sight delivers a corridor's worth of geometry at once, and the salient features — a junction, a door, a dead end (the walk terminating) — are the low-probability, high-surprise observations; a straight corridor cell is predictable, a junction is not, so discovery rewards the first reveal of *features*, not the *count* of cells. *Discovery dominates; advance is small* — discovery alone is too sparse to guide the agent through a corridor, advance alone is cell-counting with no notion of why the map matters. Without either, the minimal reward (survival margin + death) makes standing still optimal: `m0221` doesn't rise if you don't exert, so there is no gradient pulling the agent into the dungeon. The revealed-object milestone scales with the object's power, which only the reveal discloses.

### Counter

Combat is the third stage of the encounter arc after heard and seen, and the one novelty that does not wear off in a single exposure — learning what a creature type is like takes many fights. The wrapper keeps a per-type kill counter and pays a decaying bonus on each kill, 1/√N where N is the type's kill count: the first fight is maximally novel, the tenth pays a third as much, the hundredth is familiar. Keyed by the twelve type tokens, reset per episode.

The kill spike and the combat novelty share a trigger but not a purpose — the spike pays every kill ("combat pays"), the decaying bonus pays the learning ("this type is still new").

### Scrolls

VISION and SEER are bulk triggers over the same memory, not a fourth reward. VISION marks every cell of the current floor explored; SEER marks every cell, every creature instance, and every type. The scroll's cost is already felt as the consumed object.

## Rules

- **Light is a proxy.** Reward torch minutes, not `ambient_light`. The latter jumps to 0x0713 on the Wizard's death, which would read as sight-gain for the wrong reason.
- **Events dominate; potentials are small.** Terminal events (±1) outrank shaping terms (hundredths), so shaping accelerates without distorting the goal.
- **Descent is monotonic.** Reward the deepest floor reached this episode, not a per-step delta — climbing back down must not re-reward.
- **Competing signals resolve at the spike.** Combat is low safety (potential) yet leads to strength (potential) and a kill (spike). The two potentials need not out-shout each other — shaping never changes the objective. What matters is that the kill spike outweighs the safety penalty accumulated over the fight, and that it is one-shot, so it teaches "combat pays" without a standing incentive to stay in it.
- **Information gain is novelty-bounded.** Reward the *first* time a thing becomes known, not every re-look — otherwise the agent stands still and stares at what it already knows.

## Coefficients

The prototype ships with light, reasonable numbers — tunable, not final:

| Signal | Value |
|---|---|
| Win | +1.0 |
| Death | −1.0 |
| Discovery (new salient feature) | +0.1 |
| Advance (new cell) | +0.01 |
| Survival shaping | γ·Φ(s′) − Φ(s), Φ = `player_strength − m0221`, γ = 0.99 |

The scale rule is *terminal ≫ discovery ≫ advance*: terminal events dominate, discovery is a meaningful tenth, advance is a dense hundredth.

## Open Questions

- **Termination coupling.** Loss (death → `game_mode` FF, or `player_strength < m0221`) and the two-stage win straddle reward and termination — where is the boundary?

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/plans/state/plan.md` | The player fields the potentials draw from |
| `docs/plans/objects/plan.md` | Object attainment, the reveal field, and the win's second stage |
| `docs/plans/creatures/plan.md` | The creature array — type tokens, slots, and kill detection |
| `docs/plans/navigation/plan.md` | Line-of-sight and the visible corridor the cell milestone draws from |
| `docs/plans/sound/plan.md` | The approach sound that marks the type-heard milestone |
| `docs/plans/perception/plan.md` | The perception, which carries no novelty flags |
| `docs/findings/combat-model.md` | The survival margin `player_strength − m0221` |
