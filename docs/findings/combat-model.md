# Combat Model

Reverse-engineered from the 6809 disassembly ([`code.md`](../references/game/code.md)). Resolves several `??` fields in the creature struct and the player RAM map ([`ram.md`](../references/game/ram.md)).

## The shared subroutine

`D40C` is the single combat-resolution routine, called from two places:

- `CmdATTACK` (`D327`) — the player attacks a creature; X = player-strength pointer, U = creature pointer.
- `T_MoveCreature` (`D096`) — a creature attacks the player; X = creature pointer, U = player-strength pointer.

It adds damage to the defender's damage pool and leaves a strength-vs-damage comparison in the condition codes; the caller branches on it to decide death.

## Two symmetric strength-vs-damage pools

Both combatants are a strength pool minus a damage pool, and death is the damage pool overtaking the strength pool:

| Combatant | Strength pool (max HP) | Damage pool | Death |
|-----------|------------------------|-------------|-------|
| Creature | struct offset `0x00:0x01` | struct offset `0x0A:0x0B` | damage ≥ strength (`CMPX 10,U` at D432; `BHI` survives at D32A) |
| Player | `pStrength` (0x0217) | `m0221` exertion (0x0221) | exertion > strength ("Player is dead!" at C5AE–C5B5) |

Hitpoints remaining: creature `strength - damage`; player `pStrength - m0221`. A landed hit *adds* to the defender's damage pool — the amount scales with the attacker's strength and weapon factors, rather than a fixed decrement.

## Damage formula

Each landed hit adds to the defender's damage pool:

`attacker_strength × attacker_magic_attack × defender_magic_shield + attacker_strength × attacker_physical_attack × defender_physical_shield`

computed through the 16×8 multiply routine `D436`. `D40C` reads the attacker's offsets 0x02 and 0x04 against the defender's offsets 0x03 and 0x05, so both combatants share one six-field layout:

| Offset | Meaning |
|--------|---------|
| 0x02 | Magic attack |
| 0x03 | Magic shield |
| 0x04 | Physical attack |
| 0x05 | Physical shield |

- Player factors are `m0219`/`m021A`/`m021B`/`m021C` at 0x0217. `CmdATTACK` sets `m0219`/`m021B` from the held weapon's magic/physical power (`D2C4–D2CA`); the creature-attack path sets `m021A`/`m021C` from the held shield's defense (`D07A–D087`).
- Creature factors come from the `MonsterData` (DABB) class entry, whose header names the four bytes `See`/`MShield`/`Damage`/`PShield` — `See` is the magic attack, `Damage` the physical attack.

## Shield defense

Shield and monster-defense values are damage multipliers normalized to 0x80 = 1.0 (lower blocks more: 0x40 = 0.5). A held shield's magic defense (slot + 6) and physical defense (slot + 7) load into `m021A`/`m021C` (`D07A–D087`), defaulting to 0x80/0x80 with no shield; `D40C` multiplies the incoming magic and physical terms by those factors.

The original ROM stores leather and bronze shields swapped — magic 0x6C/0x60, physical 0x80 — so those physical-only shields block magic instead of physical. The ROM in use is the Shield Fix build (Aaron Oliver, CRC `c985282a`), which exchanges those two bytes at `DA78`/`DA88`; the live values are leather 0x6C (84%) and bronze 0x60 (75%) physical reduction with no magic protection, mithril 0x40 (50%) of both.

## Combat signals

| Event | Signal |
|-------|--------|
| Player lands a hit | screen prints `!!!` (D322–D324); creature damage (0x0A) rises |
| Player kills creature | alive flag (0x0C) → 0; player strength += creature_strength/8 (D347–D351); the type's `creatureCounts` entry decrements |
| Player takes a hit | `m0221` rises (D41C–D41E); no screen text; heart rate spikes on the next heart update |
| Wizard killed | `evil_wizard_dead` → FF (D35D); creatures stop moving |
| Demon killed | player advances to level 4 (D355–D357) |

## Sound: the game's proximity channel

`T_MoveCreature` (D168–D195) computes each creature's approach sound:

```
distance = max(|creatureY - playerY|, |creatureX - playerX|)   Chebyshev distance
silent if distance > 8, or if the smaller axis > 2             creature must be in a 2-cell corridor
silent 50% of the time                                         BITA #$01
volume = 255 - 31 × distance                                   louder when closer
sound number = creature type                                    each type sounds different
```

The same-cell case plays at full volume. An unseen creature is therefore conveyed as "type T, N cells away on my line" — the game's designed substitute for vision.

## Visibility channels

- **Sight** — the 3D first-person view, gated by facing and light (torch / `ambient_light`).
- **Sound** — the distance-scaled corridor channel above.
- **Seer scroll** — full map reveal of all creatures (`CDF7` "Show monsters (Seer Scroll)"); `scrollType` (0x0294, not-0 = seer).
