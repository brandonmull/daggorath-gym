## Objects

### All of them, as the player sees them

**From the conversation:**

> *Antecedent — in the walkthrough I had asked whether objects were needed at all, which ones, and hands vs. pack:*
>
> **Cline:** "Do we need objects at all? Which objects matter? Hands vs. pack?"
>
> **You:** "yes, we need objects. all objects matter; why is that even a question? the player can see both hands. the player sees inventory by using LOOK command."

> ### The Crux
>
> **Cline:** "Observation mirrors what the player perceives: both hands (always on the status line) and the inventory (the EXAMINE screen lists the room's floor objects and the pack)."

**Resolution:** objects are needed, all of them; the agent gets hands and inventory.

### Revealed vs. unrevealed

**From the conversation:**

> **Cline:** "Reveal isn't 'seeing' — it changes the object. The proper name describes something that doesn't exist yet: before reveal, the sword genuinely is wooden. So exposing the proper name early would be not just unfaithful but wrong. And it's hidden-but-obtainable, unlike creature HP — the player can unlock it in-game via REVEAL."
>
> **You:** "stick with the 'training curriculum' idea we already agreed upon. for now, expose strength-to-reveal to agent. in later stages of the curriculum, remove that information."

> ### The Crux
>
> **Cline:** "Class only until revealed — the proper name and true powers appear in the observation only after the reveal event."

**Resolution:** class only until revealed; strength-to-reveal follows the strength curriculum (exposed now, removed later).

### Torch state

**From the conversation:**

> **Cline:** "The player sees light, not a minutes counter — but they track torch life through dimming, and the lit torch is their own equipment. The sight potential must use torch minutes, because `ambient_light` is the wrong signal: it jumps to `0x0713` on the Wizard's death. Since Φ is a function of the observation, the minutes have to be in the observation."

> ### The Crux
>
> **Cline:** "Torch minutes exposed as self-state — the player tracks torch life via dimming, and the reward can't do without it."

**Resolution:** torch minutes exposed permanently, as self-state; not curriculum-removable.

### Monster-held objects

**From the conversation:**

> **Cline:** "What a creature carries is truly hidden — not imprecise (strength), not obtainable (reveal). The player has no way to know until the creature dies and drops it. The drop is the revelation: the object moves to the floor, and the agent already observes floor objects."
>
> **You:** "because monster-held objects are not supposed to be visible to a player until they're dropped, it should not be exposed to agent."

> ### The Crux
>
> **Cline:** "Monster-held objects stay hidden — the drop reveals them naturally."

**Resolution:** monster-held objects not exposed; the drop (location FF → 0) reveals them.

### The two-stage win

**From the conversation:**

> **Cline:** "Wizard-dead is a large spike, not a terminal — the episode continues to the ring. INCANT FINAL is the terminal. The detection question is how to observe INCANT FINAL in RAM: the FINAL ring in hand (proper type 0x12), the final screen text, or the win-screen state."
>
> **You:** "i'm not against detecting all three but i think the final state signal should be the one baked into the game, which a player would actually see. everything else leads up to that, even if they're the only signals that do."

> ### The Crux
>
> **Cline:** "The terminal is the player-visible win — the game's own win screen — not the internal FINAL-ring state. The ring is a precursor; the screen is the win."

**Resolution:** `wizard_dead` = spike; the terminal signal is the game's win screen (Star Wizard + "BEHOLD! DESTINY AWAITS…"); the FINAL ring (proper 0x12) is a precursor. The exact RAM signal for the win screen still needs a trace.

### Pick-up and drop

**From the conversation:**

> **Cline:** "The detection is easy — the location field moves 0 → 1 on GET and back on DROP, single-byte writes at command time. The real question is whether pick-up deserves an event or is already covered by the holdings potential. Grabbing a sword → holdings rises; grabbing a torch in the dark → sight rises. A separate pick-up spike would double-count."
>
> **You:** "agreed"
>
> **You:** "before moving on, pick-up/drop events are something that would work into an event-based architecture, which we've already preserved as future consideration."

> ### The Crux
>
> **Cline:** "No separate pick-up/drop event — the agent observes holdings each step, and the holdings and sight potentials carry the value."

**Resolution:** no pick-up/drop event for now (holdings + sight potentials reward the value; only the Supreme Ring is discrete, via the two-stage win); pick-up/drop is a natural candidate for the deferred event-based architecture.

