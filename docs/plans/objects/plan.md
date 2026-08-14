# Object Detection

_See [overview.md](../overview.md) for project context and architecture._

This document records what we know and don't know about the game's object system, and the open questions that must be answered before any design work begins. It is deliberately not a design spec — architecture and wire format are deferred until the questions below are settled.

## Purpose

Objects are the quest's tools: torches for light, swords and shields for combat, rings for the final incantation, scrolls and flasks for aid. The agent needs to know what it holds, what lies at its feet, and what a kill drops. This document establishes what is actually known and surfaces the questions that would change the answer.

## Knowns

Objects are 14-byte structures allocated upward from 0x0B15; `nextObjSlot` (0x020F:0x0210) points one past the last. They chain through their first two bytes, and each chain — pack, floor, per-monster — is a linked list.

| Address | Meaning |
|----------|---------|
| 0x0B15 (base) | First object slot, allocated upward |
| slot + 0 | Next object in the chain (0 = end) |
| slot + 2, 3 | Y, X — set when on the floor |
| slot + 4 | Maze level — set when on the floor |
| slot + 5 | Location — 0 = floor, 1 = pack, FF = monster |
| slot + 6 | Special data 1 — ring strikes, shield magic defense, torch minutes |
| slot + 7 | Special data 2 — ring incantation word, shield physical defense, torch physical light |
| slot + 8 | Special data 3 — torch magic light |
| slot + 9 | Proper type |
| slot + 10 | Class — FLASK, RING, SCROLL, SHIELD, SWORD, TORCH |
| slot + 11 | Strength to reveal (0 once revealed) |
| slot + 12 | Magic power |
| slot + 13 | Physical power |

Pointers to the object chains:

| Address | Meaning |
|----------|---------|
| 0x021D:021E | `leftHand` — object in the left hand, or 0 |
| 0x021F:0220 | `rightHand` — object in the right hand, or 0 |
| 0x0224:0225 | `torchPtr` — the lit torch, or 0 |
| 0x0229:022A | `firstPackObject` — head of the backpack chain (a LIFO stack) |
| 0x020F:0210 | `nextObjSlot` — one past the last object |
| creature + 8 | each creature's chain of held objects |

Verified from the disassembly:

- **Reveal is strength-gated.** An object acts as its base class — wooden sword, leather shield, pine torch (table C719) — until `pStrength >= strength_to_reveal × 25` (CmdREVEAL multiplies by 25, `MUL #$19`). Revealing clears the field (slot + 11) and applies the proper name.
- **The win is an incantation, not the kill.** Killing the Wizard drops the Supreme Ring and clears hands, pack, and torch (D35D–D371). Incanting FINAL on it triggers PlayerWins ("BEHOLD! DESTINY AWAITS..."). So `wizard_dead` is necessary but not sufficient — the true win is the INCANT FINAL.
- **Torches burn down.** The lit torch's minutes (slot + 6) decrement once a minute; its physical and magic light (slots + 7, + 8) track the remaining minutes, and below five minutes it becomes a dead torch.
- **Rings carry strikes and a hidden word.** Each ring has a strike count (slot + 6) and an incantation word (slot + 7) that, on a match, transforms the ring and clears the word.
- Object data lives in ROM tables: `ObjectData` (DA00 — class, reveal strength, magic/physical power) and `ObjectSpecial` (DA64 — strikes, defense, torch minutes); `ObjectDist` (DA91) assigns objects to creatures by level, strongest creatures first.

## Decisions

Observation mirrors what the player perceives:

- Objects are needed, and all of them matter — torches, swords, shields, rings, scrolls, flasks.
- Both hands are visible on the status line, and the inventory is visible via EXAMINE, so the agent gets both.
- **Class until revealed.** An object's proper name and true powers appear only after the reveal event (slot + 11 → 0) — before that the object genuinely acts as its base class. The strength-to-reveal threshold is exposed for now and removed in a later curriculum stage, the same pattern as strength.
- **Torch minutes are self-state.** The torch's remaining minutes (slot + 6 of the lit torch) are exposed at full precision — the player tracks torch life via dimming, and the reward's sight potential needs the minutes, not `ambient_light` (which jumps on the Wizard's death). Not curriculum-removable.
- **Monster-held objects stay hidden.** What a creature carries is not exposed — it's truly hidden until the creature dies and drops it, at which point the agent sees it on the floor.
- **The win is two stages; the terminal is player-visible.** `wizard_dead` → `FF` is a large spike, not terminal — the episode continues to the ring. The terminal signal is the game's own win moment (Star Wizard beamed in, "BEHOLD! DESTINY AWAITS…"), not the internal FINAL-ring state; the FINAL ring (proper type 0x12) is a precursor. The exact RAM signal for the win screen still needs a trace.
- **Pick-up and drop are not events — for now.** The location field (`slot + 5`) and the hand/pack chains show the transition reliably, but the holdings and sight potentials already reward the value of gaining an object — a separate pick-up spike would double-count. The agent observes holdings each step; only the Supreme Ring is a discrete event, via the two-stage win. Pick-up/drop events are a natural candidate for the deferred event-based architecture.

## Unknowns

- **Object array bound.** `nextObjSlot` grows upward from 0x0B15 toward the stack at 0x0FFF; the practical ceiling and the total number of objects placed at startup are not confirmed.
- **Flask and scroll effects.** The USE routines for the THEWS, HALE, and ABYE flasks, and the VISION scroll's effect, are not decoded (SEER revealing creatures is confirmed).
- **Shield defense swap.** `ObjectSpecial` notes the shield magic/physical defense values are swapped — a known bug, so the live combat factors are the swapped ones.
- **Ring catalogue.** The full incantation chain — which word makes which ring, and what each final ring does — is only partially catalogued.

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/references/game/ram.md` | Memory map — the object structure and pointers |
| `docs/references/game/code.md` | Disassembly — object commands, reveal, incant, torch, object tables |
| `docs/references/game/commands.md` | Command grammar — object classes and proper names |
| `docs/findings/combat-model.md` | How object magic/physical power feeds the combat damage formula |
