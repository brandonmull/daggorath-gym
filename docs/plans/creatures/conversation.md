## Creatures

### Kill detection — direct and typed

**From the conversation:**

> *Antecedent — in the walkthrough I had framed kill detection as a read-rate question:*
>
> **Cline:** "At what rate must we read to trust kill detection? If slot transitions are only reliable at frame rate, reward may need to fall back on aggregate signals like strength-delta."
>
> **You:** "kill detection is important, not its 'read rate' (whatever that means). if the only ram signal is strength gain, that sucks; i'd rather it were more direct. also, *what* did the player kill? they can be battling more than one creature at a time. what if screen reading is the only way to tell?"

> ### The Crux
>
> **Cline:** "A kill is a slot going alive→dead, and the slot's type is exactly what was killed. Lua samples every frame, so there's no race — and the array is strictly better than screen reading, which only says 'a hit landed,' not 'what died.'"

**Resolution:** kill detection = alive flag (0x0C) FF→0 + type (0x0D), caught at frame rate in Lua. Strength gain remains only the aggregate.

### Level-switch — the array is zeroed

**From the conversation:**

> *Antecedent — in the walkthrough I had raised the level-switch window as an open question:*
>
> **Cline:** "Is there a level-switch window we must avoid sampling? If so, the readiness gate may need to extend beyond `displayFunction`."
>
> **You:** "i never thought of the possibility that level switching could cause reset or lapse in state. good catch. needs a sandbox, which is going to be tricky since that's a lengthy process to get to end of level. i think saving game progress will be required for this one."

> ### The Crux
>
> **Cline:** "The level-setup routine zeroes the entire creature array (0x03D4–0x05F4), then rebuilds the maze and re-spawns creatures. The array is never garbage — it's validly empty, briefly, then repopulated."

**Resolution:** resolved statically (`SWI_1A`, "Fill X to U with 0s"); no sandbox required, though save-states remain useful for confirmation.

### Sight and navigation

**From the conversation:**

> *Antecedent — in the walkthrough I had asked whether positions should be sight-gated:*
>
> **Cline:** "Sight-gated positions. Should positions be exposed only when the player sees the creature (facing + light), or always?"
>
> **You:** "creatures can be seen well ahead of immediate cells. it's somewhat dependent on light level but typically it's all the way down corridors. which now makes me think of the need for a navigation module, since we need to detect walls and doors and ladders/stairs, etc."

> ### The Crux
>
> **Cline:** "Sight-gating needs line-of-sight, which needs the maze. Navigation is the prerequisite module for 'what does the player see down the corridor.'"

**Resolution:** a navigation module (walls, doors, holes/ladders, line-of-sight) precedes creature sight-gating.

### Combat — loud signals

**From the conversation:**

> *Antecedent — in the walkthrough I had recommended against a separate combat module:*
>
> **Cline:** "Is combat detection a separate module, or a reward-level interpretation of signals already owned by the creature, state, and screen modules?"
>
> **You:** "i don't know that i agree with the absence of combat detection. it's a serious event that demands immediate attention. just simply inferring it doesn't seem to do justice. agents should get loud signals for things like this, just like a real human would."

> ### The Crux
>
> **Cline:** "Combat deserves loud, explicit signals — a dedicated event channel — but that's a new architectural surface, so it's deferred until after a working prototype."

**Resolution:** for the prototype, combat signals come from existing sources (screen `!!!`, sound, alive flags, `m0221`); the event channel is a deferred idea, not forgotten.

### Type catalogue — the 12 types and their strengths

**From the conversation:**

> *Antecedent — `plan.md` "Unknowns" flagged the type catalogue as reward-blocking, with only Demon (0x0A) and Wizard (0x0B) confirmed:*
>
> **Cline:** "The other ten types and their strengths live in ROM data tables not yet catalogued."
>
> **You:** "Trace the tables around `T4_MakeCreature` (D027) and `GetCreatureAt` in `code.md`. Deliverable: the full 12-type table (token, name, strength) in the plan's 'Knowns,' with disassembly addresses as evidence."

> ### The Crux
>
> **Cline:** "Every type token indexes three parallel ROM tables laid out in the same order — sound routine (C7DC), creature picture (DAA3), and an 8-byte creature-class entry (DABB). `CreateCreature` copies `type × 8 + DABB` into the slot, so the class entry's first two bytes are the strength."

**Resolution:** the 12-type table is catalogued in `plan.md` ("Knowns") and the "Type catalogue" unknown is closed. Evidentiary comments: `CreateCreature` (CFA5) — "Set the type", "8 bytes of init data", "Add to creature-class data table"; `MonsterData` (DABB) — "To-kill" names the first two bytes, the strength; the kill site (D347) — "Monster strength ... divided by 8" reads it back as 16 bits; `SoundEffectsRoutines` (C7DC) — "00 Spider" through "0B Wizard" confirms the sound effect number equals the type token; level setup (C75B) — "12 bytes each (one byte to count each type of creature)". Also found: the random spawner (`T4_MakeCreature`, D039) adds only types 2–9 — "not spider, snake, demon, or wizard" — and the level listings use longer display names (`CLUB GIANT`, `PLAIN KNIGHT`).

### Combat multipliers — the six-field layout

**From the conversation:**

> *Antecedent — `plan.md` "Unknowns" listed combat multipliers: "Creature offsets 0x02–0x05 feed the damage formula but are not individually decoded."*
>
> **Cline:** "The shield-defense trace walked `D40C`, the single combat-resolution routine — and it decodes those four offsets for free."

> ### The Crux
>
> **Cline:** "`D40C` pairs the attacker's 0x02/0x04 against the defender's 0x03/0x05, so player and creature share one layout: 0x02 = magic attack, 0x03 = magic shield, 0x04 = physical attack, 0x05 = physical shield."

**Resolution:** the four offsets are catalogued in `plan.md` (the slot table and the `MonsterData` bullet) and the "Combat multipliers" unknown is closed. Evidence: `D40C` multiplies attacker 0x02 × defender 0x03 and attacker 0x04 × defender 0x05; `CmdATTACK` (D2C4–D2CA) sets the player's 0x02/0x04 from the weapon's power; the creature-attack path (D07A–D087) sets the player's 0x03/0x05 from the held shield. The `MonsterData` header names the creature bytes `See`/`MShield`/`Damage`/`PShield` — `See` is the magic attack, `Damage` the physical attack.

