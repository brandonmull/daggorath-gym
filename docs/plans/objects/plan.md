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
- **The win is an incantation, not the kill.** Killing the Wizard drops the Supreme Ring and clears hands, pack, and torch (D35D–D371). Incanting FINAL on it triggers PlayerWins ("BEHOLD! DESTINY AWAITS..."). So `wizard_dead` is necessary but not sufficient — the true win is the INCANT FINAL, and its RAM signal is the ring's proper-type field (slot + 9) becoming 0x12 (FINAL) as the word (slot + 7) clears: `CmdINCANT` writes the matched word to slot + 9 (D5E0), clears slot + 7 (D5E9), then branches to `PlayerWins` (D5ED). That 0x12 is the only persistent trace — `PlayerWins` itself writes nothing durable (its `DEC initBeamIn` is cleared by the beam routine within the same call) and then freezes in an endless loop (D621).
- **Torches burn down.** The lit torch's minutes (slot + 6) decrement once a minute; its physical and magic light (slots + 7, + 8) track the remaining minutes, and below five minutes it becomes a dead torch.
- **Rings carry strikes and a hidden word.** Each ring has a strike count (slot + 6) and an incantation word (slot + 7) that, on a match, transforms the ring and clears the word.
- Object data lives in ROM tables: `ObjectData` (DA00 — class, reveal strength, magic/physical power) and `ObjectSpecial` (DA64 — strikes, defense, torch minutes); `ObjectDist` (DA91) assigns objects to creatures by level, strongest creatures first.
- **The object array is fixed at startup.** The creation loop (C088–C0AE) walks `ObjectDist` (DA91), whose 18 bytes each carry a count in the low nibble and a first-appearance level in the high nibble, and places 63 objects on creatures. `GameObjects` (D7D9) adds two more to the starting pack — a wooden sword and a pine torch — so boot allocates 65 objects and `nextObjSlot` settles at 0x0EA3 (0x0B15 + 65 × 14). Nothing creates objects after boot; the only later write is the Wizard's death, which truncates the array to 0x0B23 to keep just the Supreme Ring (D364–D367). The stack at 0x0FFF leaves ~348 bytes of headroom that no code touches.
- **Flask effects.** `CmdUSE` (D741) dispatches on proper type through `UseFunctions` (D76B). THEWS (05) adds 0x03E8 to `pStrength` (D77A); HALE (09) zeroes exertion `m0221` (D783); ABYE (08) adds `pStrength × 0x66` to exertion via the 16×8 multiply at D436 (D787) — a penalty that drives the heart toward death, not a boon. Every flask becomes an EMPTY flask (proper type 0x17) and is marked revealed on drinking (D792–D796); no reveal is needed first — the drink is the reveal.
- **Scroll effects.** VISION and SEER both hand the display to `ShowMap` (CDB2) after writing `scrollType` (0x0294): VISION stores 0, SEER stores FF (D7A0–D7A4). `ShowMap` always draws the current level's maze, the player, and the holes and ladders, but draws creatures and floor objects only when `scrollType` is non-zero (CDDD–CDDF). So VISION reveals the maze layout alone, and SEER adds creatures and objects. Both scrolls must be revealed first (D7A6–D7A8) and are transient — the map stays up until the next command.
- **Ring catalogue.** Each placed ring carries 3 strikes (slot + 6) and a hidden incantation word (slot + 7) from `ObjectSpecial` (DA64). `CmdINCANT` (D5BC) matches a typed word against slot + 7 and, on a hit, writes it to slot + 9 and reloads the descriptor (D5D8–D5E9): SUPREME (00) is incanted with FINAL (12) and wins the game; JOULE (01) → ENERGY (13), RIME (06) → ICE (14), VULCAN (0C) → FIRE (15), the three combat rings carrying magic/physical power FF FF from `ObjectData` (DA4C–DA54). Each attack with a powered ring (types 13–15) decrements the strike count, and at zero the ring degrades to GOLD (16) (D2E2–D2F4) — GOLD is never placed, only produced as the spent-ring residue.
- **Shield defense is a damage multiplier — and fixed in our ROM.** A shield's magic defense (slot + 6) and physical defense (slot + 7) are fractions of incoming damage where 0x80 = 1.0 and 0x40 = 0.5, taken from `ObjectSpecial` (DA6C/DA78/DA88); combat multiplies incoming hits by them at D40C, the held shield feeding `m021A`/`m021C` at D07A–D087 with an 0x80/0x80 default. The original ROM stores leather and bronze swapped — magic 0x6C/0x60, physical 0x80 — the bug `code.md` documents. The ROM we run is Aaron Oliver's Shield Fix (CRC `c985282a`), which exchanges those two bytes at DA78 (`0B 80 60 00`) and DA88 (`10 80 6C 00`) — ROM file offsets 0x1A78/0x1A88, the only divergence from the disassembly across `ObjectData`/`ObjectSpecial`/`ObjectDist` — so the live factors are bronze taking 75% and leather 84% of physical damage with no magic protection; mithril is 50% of both either way.

## Scan

The environment samples objects by walking the pointer chains: `leftHand` and `rightHand` give the two held objects, `firstPackObject` walks the pack, `torchPtr` gives the lit torch. Each object is reported as its class (slot + 10) plus, when revealed, its proper type (slot + 9) — reveal is the strength-to-reveal field (slot + 11) being 0. Floor objects — location (slot + 5) is 0 and the cell is the player's — are gated by light like the rest of the dungeon. Monster-held objects (location FF) stay hidden. The lit torch's minutes (slot + 6) are self-state, exposed at full precision.

## Decisions

Perception mirrors what the player perceives:

- Objects are needed, and all of them matter — torches, swords, shields, rings, scrolls, flasks.
- Hands are visible on the status line (always); the pack is visible via EXAMINE; floor objects are visible in LOOK while the torch is lit. The three follow the perception module's mode + light gates.
- **Class until revealed.** An object's proper name and true powers appear only after the reveal event (slot + 11 → 0) — before that the object genuinely acts as its base class. The strength-to-reveal threshold is exposed for now and removed in a later curriculum stage, the same pattern as strength.
- **Torch minutes are self-state.** The torch's remaining minutes (slot + 6 of the lit torch) are exposed at full precision — the player tracks torch life via dimming, and the reward's sight potential needs the minutes, not `ambient_light` (which jumps on the Wizard's death). Not curriculum-removable.
- **Monster-held objects stay hidden.** What a creature carries is not exposed — it's truly hidden until the creature dies and drops it, at which point the agent sees it on the floor.
- **The win is two stages; the terminal is the ring's transformation.** `wizard_dead` → `FF` is a large spike, not terminal — the episode continues to the ring. The terminal signal is `CmdINCANT`'s write of 0x12 (FINAL) into the held ring's proper-type field (slot + 9), which clears the word (slot + 7) and branches straight to `PlayerWins` (D5ED). There is no separate win-screen flag to trace: the Star Wizard beam and "BEHOLD! DESTINY AWAITS…" are transient renderings — `initBeamIn` (0x029E) is set and cleared inside the same beam call, and the game freezes in an endless loop (D621) — so the proper type 0x12 is the win's only persistent RAM signal.
- **Pick-up and drop are not events — for now.** The location field (`slot + 5`) and the hand/pack chains show the transition reliably, but the holdings and sight potentials already reward the value of gaining an object — a separate pick-up spike would double-count. The agent observes holdings each step; only the Supreme Ring is a discrete event, via the two-stage win. Pick-up/drop events are a natural candidate for the deferred event-based architecture.

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/references/game/ram.md` | Memory map — the object structure and pointers |
| `docs/references/game/code.md` | Disassembly — object commands, reveal, incant, torch, object tables |
| `docs/references/game/commands.md` | Command grammar — object classes and proper names |
| `docs/findings/combat-model.md` | How object magic/physical power feeds the combat damage formula |
