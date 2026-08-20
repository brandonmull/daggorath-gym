# Events

_See [overview.md](../overview.md) for project context and architecture._

This document records the event-based architecture — deferred, not built for the prototype — and the catalog of candidate events it would carry.

## Status

**Deferred.** The prototype relies on state observation plus potential-based reward; a dedicated event channel (discrete "something happened" signals) is a future architectural surface. The deferral is argued in `../creatures/conversation.md` ("combat — loud signals") and `../objects/conversation.md` ("pick-up and drop").

## What an event is

A one-shot, loud, temporally-local signal that a discrete happening occurred — distinct from state (the current situation) and from potential-based reward (the situation's value). Events say "a hit landed," "the torch died," "the wizard is dead"; they don't say "how good things are right now."

## Candidate events

| Event | RAM signal |
|-------|-----------|
| Player lands a hit | screen `!!!`; creature damage (0x0A) rises |
| Player takes a hit | `m0221` rises; hit sound (12/13) |
| Kill (typed) | alive flag (0x0C) FF→0; type (0x0D) = what died |
| Pick-up / drop | location field (slot + 5) moves 0 → 1/hand or back |
| Reveal | strength-to-reveal (slot + 11) → 0 |
| Incant | ring word (slot + 7) clears, proper name changes |
| Torch lit | `torchPtr` set |
| Torch died | torch becomes dead (below 5 minutes) |
| Descent / climb | `at_floor` changes |
| Demon killed | advances to level 4 |
| Wizard killed | `wizard_dead` → FF, creatures stop |
| Win | PlayerWins — "BEHOLD! DESTINY AWAITS…" |
| Wall bump | wall-hit sound (14) |
| Faint / recover | `player_fainting` transitions |
| Death | `game_mode` → FF, "YET ANOTHER DOES NOT RETURN" |
| Command rejected | "???" in the command area; `perfectMatch` (0x027B) never fires |

The sound module's auditory cues (creature approach sound, heartbeat, combat sounds) are a related but separate channel — derived from RAM rather than events.

## Why events beat flags (recorded, not yet acted on)

From the factored-action-space discussion (`../commands/conversation.md`):

- **A flag is a level; an event is a pulse.** `command_rejected` as a boolean means "rejected right now," which needs edge-detection to count once; an event says "a rejection happened once, here," and is self-counting and self-ordering. Most reward signals — spikes, the two-stage win, novelty — are transitions over time, which events model directly.
- **Environment reports, wrapper prices.** Detection is a fact (the environment's job, from `command_text`/`perfectMatch`); sequencing and valuation are the reward wrapper's job. `command_rejected` would be a true-state fact, not a `PERCEIVED_SPACE` channel — the policy never sees it, only feels the penalty.
- **SB3 compatibility.** SB3's algorithm consumes only a scalar reward per step and has no event-stream concept — nor needs one. The event stream is an env → wrapper fact channel; the wrapper (agent-side, arbitrary memory) translates events + sequencing into that scalar.
- **Detection fork (unresolved).** Persistent transitions (kill `FF→0`, reveal `→0`, descent, death) can be edge-detected in Python from raw state deltas — consistent with "wire carries raw, Python derives." Transient signals (`perfectMatch` `0→FF→0`, `!!!`, one-frame sounds) only Lua sees frame-accurately, and would need a new `E` record. `command_rejected` is persistent ("???" lingers), so Python can derive it.
- **Sequencing.** command → reject is one step apart, so the wrapper's own transition gives the ordering; sequence numbers on events cover multi-step attribution (kill-after-attack) if needed.

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `../creatures/conversation.md` | The "combat — loud signals" thread that deferred the channel |
| `../objects/conversation.md` | The "pick-up and drop" thread that flagged the architecture |
