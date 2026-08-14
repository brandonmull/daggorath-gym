# Reward

_See [overview.md](../overview.md) for project context and architecture._

This document describes how the reward function turns game state into a training signal. It follows the observation principle from the object and creature modules — the agent perceives what the player perceives — and shapes reward from that same state.

## Purpose

Reward answers one question: did the agent's situation just get better or worse? The game's own signals — strength, light, holdings, survival, the win — each answer that question in part. This document assembles them into a single signal.

## Framework

Reward has three layers, each doing a distinct job:

- **Spikes** — the objective itself: what was achieved. One-shot, large, temporally-local rewards for kills, pick-ups, and the win, so the agent learns early that combat pays off.
- **Potentials** — potential-based shaping: how good the situation is now. The term γ·Φ(next) − Φ(current) scores the situation and densifies the gradient between spikes; it never changes the optimal policy, only the speed of learning.
- **Information gain** — intrinsic motivation: what was learned. A novelty-bounded reward for the unknown→known transition: creature unseen→seen, object unrevealed→revealed, cell unexplored→explored, scroll used. It generalizes beyond creatures — object reveal, map exploration, and the VISION/SEER scrolls are the same mechanism.

Because the observation mirrors player perception, all three layers draw from the same state.

## Potentials

Conditions the agent should seek or avoid, each drawn from a state signal:

| Potential | Signal | Sampled today? |
|-----------|--------|----------------|
| Strength | `player_strength` — grows with every kill | Yes |
| Sight | torch minutes remaining (lit torch, slot + 6) | No — object detection |
| Survival | `player_strength − m0221` — the margin to death | Partly — `m0221` not sampled |
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

## Rules

- **Light is a proxy.** Reward torch minutes, not `ambient_light`. The latter jumps to 0x0713 on the Wizard's death, which would read as sight-gain for the wrong reason.
- **Events dominate; potentials are small.** Terminal events (±1) outrank shaping terms (hundredths), so shaping accelerates without distorting the goal.
- **Descent is monotonic.** Reward the deepest floor reached this episode, not a per-step delta — climbing back down must not re-reward.
- **Competing signals resolve at the spike.** Combat is low safety (potential) yet leads to strength (potential) and a kill (spike). The two potentials need not out-shout each other — shaping never changes the objective. What matters is that the kill spike outweighs the safety penalty accumulated over the fight, and that it is one-shot, so it teaches "combat pays" without a standing incentive to stay in it.
- **Information gain is novelty-bounded.** Reward the *first* time a thing becomes known, not every re-look — otherwise the agent stands still and stares at what it already knows.

## Open Questions

- **Scaling.** What coefficient per potential, per spike, and per information-gain transition, and what γ?
- **Termination coupling.** Loss (death → `game_mode` FF, or `player_strength < m0221`) and the two-stage win straddle reward and termination — where is the boundary?
- **Novelty tracking.** How is "first time known" represented — per-creature seen flags, per-cell explored flags, per-object revealed flags? Information gain needs a novelty memory, which is an observation question (what the agent has seen, not what exists).

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/plans/state/plan.md` | The player fields the potentials draw from |
| `docs/plans/objects/plan.md` | Object attainment and the win's second stage |
| `docs/plans/creatures/plan.md` | Creature presence and kill detection |
| `docs/findings/combat-model.md` | The survival margin `player_strength − m0221` |
