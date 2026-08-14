## Sound

### The game's own proximity channel

**From the conversation:**

> *Antecedent — in the creature observation discussion I had proposed sight-gating and rejected memory:*
>
> **Cline:** "Memory of the unseen → No. Stale coordinates lie; the sound channel is the game's own 'behind me' cue."
>
> **You** (earlier): "what about creature sounds because they're really important for determining proximity in the absence of sight."

> ### The Crux
>
> **Cline:** "The game already computes a distance-scaled, corridor-gated, type-encoded sound — Chebyshev distance ≤ 8, within a 2-cell corridor, louder when closer, and the sound *is* the creature type. We can derive that cue from RAM instead of reading the DAC."

**Resolution:** the sound module is a Python derivation over creature and player state — no new RAM sampling, no DAC reading.

### Derive the cues, not the DAC

**From the conversation:**

> **Cline:** "The DAC is a mixed, transient waveform — the player never 'hears the DAC'; they distinguish sources: a spider chittering two cells ahead, their own racing heart. Reading the DAC would throw away the very signal that matters. And the question collapses with 'module or derivation': derive, in Python, over existing signals — no DAC, no new Lua sampling."

> ### The Crux
>
> **Cline:** "Derive the cues from RAM — creature type + distance, heartbeat, combat sounds — and never read the DAC."

**Resolution:** derive the cues; sound is a Python derivation over existing signals, not a new Lua module.

### Noise fidelity

**From the conversation:**

> **Cline:** "The coin flip is rolled per sound event, so a creature in range is heard with probability 1 − 0.5ⁿ — essentially certainly within a second. Drop it; the corridor gate is the part that carries meaning."
>
> **You:** "agreed, but i'm not sure i agree with the corridor gating rule. plenty of times when playing the game, i've heard creatures that were not in same corridor as me but were off to the side some distance. i think clarity about this rule and its real application needs to be investigated. it might be worth deferring, with a recommendation to sandbox."

> ### The Crux
>
> **Cline:** "Deterministic 'audible now' — drop the coin flip. The corridor gate is not settled: the disassembly reading contradicts lived experience, so it's deferred to a sandbox."

**Resolution:** drop the 50% coin flip (deterministic "audible now"); the corridor gate is deferred pending a sandbox — the `min(|dx|,|dy|) ≤ 2` reading needs empirical verification.

### Granularity

**From the conversation:**

> **Cline:** "Per-creature (type + distance). The type is non-negotiable — the sound number is the creature type. And creatures come in groups, so a single nearest-threat cue discards real information. Direction is a refinement, not a replacement."
>
> **You:** "per creature, definitely."
>
> **You:** "sound perception isn't necessarily location based though. it's a more reductive form of knowledge: distance only. no left, right, forward, back; just vague distance and type. however, there needs to be room for multiple sounds at once."

> ### The Crux
>
> **Cline:** "Sound is distance + type only — the game is mono, so nothing conveys bearing — and it's a multi-slot channel."

**Resolution:** per-creature (type + distance), no direction; multiple audible creatures representable at once.

### Sound as proximity

**From the conversation:**

> **Cline:** "The sound channel answers creature #10 and settles #8 (sight-gated positions) and #9 (no memory) in the same stroke — the three were really one question: how does the player perceive creatures, and in what form do we reproduce it?"

> ### The Crux
>
> **Cline:** "Seen creatures get positions (sight-gated); unseen creatures get sound (type + distance, no direction). No raw positions, no memory."

**Resolution:** the sound channel is the proximity observation; it closes the creature module's observation questions.

### Sound type ≠ creature type

**From the conversation:**

> **You:** "sound type should not be represented as creature alone. any one given creature could produce more than one type of sound. there's an indirect correlation that's occurring. i don't want the agent to be responsible for learning how to associate sound type with creature type right away though. this is another thing that belongs to a curriculum. perhaps every sound should have three properties: distance, sound type, creature type. are creatures the only things that make sounds?"
>
> **Cline:** "No — creatures aren't the only source: objects (use sounds), the player (hit, heartbeat), the environment (wall hit), and the wizard (beam, strike) all sound too; and a creature alone makes more than one sound (approach, dying). So the third property is 'source,' not 'creature type.'"

> ### The Crux
>
> **Cline:** "Every sound carries distance, sound type, and source — and the sound→source association is a curriculum item: exposed now, removed later."

**Resolution:** per-sound (distance, sound type, source); the sound→source association is a curriculum item.

