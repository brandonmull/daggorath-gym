# Curriculum

_See [overview.md](../overview.md) for project context and architecture._

This document records the training curriculum — the staged removal of information the environment currently hands the agent, so that the agent learns to maintain that knowledge itself. It is deliberately not a design spec: the stage order and graduation criteria are recorded here as open questions, deferred to later sessions.

## Purpose

Four modules defer information to a "curriculum stage": the environment exposes a signal now to accelerate early training, and removes it later so the agent internalizes the skill. Those items are scattered across the module plans. This document gathers them into one place and records the questions a curriculum design must answer.

## Knowns

Four curriculum items exist, each "exposed now, removed later":

- **Strength.** The player's exact strength number is exposed now as a training accelerant; a later stage removes it so the agent learns its own body. See the strength controversy in `state/conversation.md`.
- **Reveal threshold.** An object's strength-to-reveal is exposed now; a later stage removes it, following the same pattern as strength. See `objects/plan.md`.
- **Sound→source association.** Each sound carries its source now; a later stage removes the source so the agent learns to associate sound with source itself. See `sound/plan.md`.
- **Map memory.** The explored map is provided now as environment scaffolding; a later stage removes it so a recurrent agent maintains its own map. See `navigation/plan.md`.

## Open Questions

The curriculum's structure, recorded as options and deferred to later sessions:

- **Stages and order.** Which item is removed first, and is there a single ordered path or independent stages per item?
- **Graduation criteria.** How is "the agent has internalized it" measured — a performance threshold, a fixed number of timesteps, or manual judgment — before an item is removed?
- **One curriculum or per-item ablations.** A single sequence versus independent experiments, one per item.

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/plans/state/conversation.md` | The strength controversy — expose now, remove later |
| `docs/plans/objects/plan.md` | The reveal threshold, following the strength pattern |
| `docs/plans/sound/plan.md` | The sound→source association as a curriculum item |
| `docs/plans/navigation/plan.md` | Map memory as environment scaffolding |
