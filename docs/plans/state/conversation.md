## State

### Strength: hidden, imprecise, or proprioceptive?

**From the conversation:**

> *This thread began as a creature-hitpoint question and turned into the question of the player's own strength:*
>
> **You:** "should we provide that much information to the agent because players don't normally get that, right? we definitely want to provide the type of creature. what about providing starting strength/hitpoints?"
>
> **You:** "strength level seems appropriate because we want the agent to have good proprioception, but that's not information the player is actually given. i'm torn between whether to give it or not."

> ### The Crux
>
> **Cline:** "Strength isn't *hidden* from the player — it's *imprecise*. The player genuinely knows their strength, because the game tells them through effect: kill a creature and you're stronger; stronger means fewer hits to kill. The manual teaches this explicitly, so a player tracks strength qualitatively from their own history — just without a number."

> **Cline:** "Withholding it just forces the agent to re-derive a value the game already tracks. That's like hiding a robot's battery level because its chassis doesn't print it. Strength is self-state and deterministic — a pure function of what you've killed — and the reward needs it."
>
> **You:** "i like your clarification about a player's knowledge of their own strength being imprecise. that's the perfect way to perceive this issue. therefore, i would lean toward not giving an exact strength number to the agent, even though i'm absolutely certain we should track it internally. the question is WHO is responsible for knowing player strength: the game environment, or the agent playing the game? for now, it makes the agent's job of training a whole lot easier if we expose it. i feel we should at least surface and preserve the controversy in docs, regardless of what direction we go, so it can be reconsidered later."
>
> **Cline:** "the environment is always responsible for tracking strength — the only question is whether it's also *reported* to the agent. The reward layer needs the true strength regardless... a curriculum path. Train with the number exposed, then as a later experiment, remove it and see whether the agent has internalized its own strength. That turns 'who should know' from a philosophical standoff into a testable ablation."

**Resolution:** Track strength always (reward and termination need it). Expose it in the observation for now — a training accelerant. The controversy is preserved, not resolved: the "agent learns its own body" variant is a deferred curriculum ablation.

