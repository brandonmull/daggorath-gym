## Reward

### "Almost everything counts" → potential-based shaping

**From the conversation:**

> *Antecedent — the reward discussion had stalled on a two-loop tension, then detoured through creatures, objects, and sound before returning here:*
>
> **Cline:** "Daggorath's objective is two loops that a single signal can't capture: the combat loop — survive and build strength — and the navigation loop — descend to the wizard."
>
> **You:** "i was about to say sorry that i went off on a tangent, away from talking about rewards and more about state. however, now that i think about it, object attainment is rewarding, especially if they're powerful objects. heck, obtaining a torch if you're running out of light is important too. even the ability to see is part of reward. we want to give signals to the agent when conditions are bad or when they're good. almost everything in the state counts toward this."
>
> **Cline:** "You didn't go off on a tangent — you found the spine of the whole thing. 'Object attainment is rewarding, seeing is rewarding, good/bad conditions deserve signals' is the answer to 'how do we calculate reward.' And all the state work we just did turns out to be the inventory of signals to draw from."

> ### The Crux
>
> **Cline:** "The clean way to say 'almost everything counts' — and stay safe while doing it — is **potential-based shaping**. Define a potential Φ(state) = 'how good is my situation right now,' and make the shaping term **γ·Φ(s′) − Φ(s)**. The agent earns positive reward when Φ *rises* and negative when it *falls*. This is **provably harmless** — it doesn't change the optimal policy, it just densifies the signal. That's the crucial difference from sprinkling arbitrary bonuses, which *can* be reward-hacked."

> **Cline:** "Light is a proxy, not the thing. 'Seeing' is really 'the torch still has minutes.' Reward torch-minutes, not instantaneous ambient_light — because ambient_light also jumps to 0x0713 when you kill the Wizard... Combat and heart are the same signal. Exertion (m0221) rises both from attacking and from being hit. Penalize high heart rate directly and you punish the very attacking that wins fights. The margin pStrength − m0221 sidesteps it."
>
> **Cline:** "The satisfying part: since the observation already mirrors what the player perceives, Φ is just a function of that same state — reward design and observation design collapse into one question: what makes this situation good?"
>
> **You:** "i like the potential shaping idea. good recommendation!"

**Resolution:** reward is potential-based shaping — γ·Φ(s′) − Φ(s) — with two care points: light is a proxy (torch minutes, not `ambient_light`), and combat and heart are one signal (the margin `pStrength − m0221`).

### The strength potential

**From the conversation:**

> *Just prior, I had split reward into potentials and events — and strength appeared only inside the survival margin and as the kill's reward, never as a potential of its own:*
>
> **Cline:** "Potentials: light / torch minutes, survival margin (`pStrength − m0221`), holdings, safety, (inverse) fainting and carried weight. Events: kill (strength delta), pick up, reveal, incant, descent; the win is two events."
>
> **You:** "potentials are missing strength."

> ### The Crux
>
> **Cline:** "Strength rises only through kills, so the strength potential already rewards combat, and it scales with the creature's power the same way the game's own kill reward does. The kill event is later scoped to what the strength potential doesn't capture."

**Resolution:** strength is its own potential — it rises only through kills and scales with creature power; the kill event is scoped to what the potential doesn't capture.

### Competing signals → the spike/potential split

**From the conversation:**

> *Just prior — my answer to the missing strength, which this responds to:*
>
> **Cline:** "Strength rises only through kills, so the strength potential already rewards combat... The kill event is later scoped to what the strength potential doesn't capture."
>
> **You:** "we have to be careful about competing signals. being in combat is low safety but it leads to greater strength. does this mean the reward for gaining strength should be that much greater? what if we used some kind of spiking reward system in addition to potential, so that the agent can learn early on that engaging in combat leads to big rewards, but that kind of large reward is only temporary?"

> ### The Crux
>
> **Cline:** "You've independently arrived at the standard two-layer reward design, and it's exactly right. The spike is the objective; the potential is the shaping. They do different jobs, and you want both: spikes define what the task is — sparse, large, temporally local. Potentials define how good the situation is, densifying the gradient between spikes so every step has signal."
>
> **Cline:** "On 'does strength need to be that much greater?' — no. The safety and strength potentials don't need to out-shout each other, because shaping provably never changes the optimal policy — it only changes learning speed. The thing that must outweigh is the spike vs. the accumulated safety penalty. That's a scale question, not a correctness question."
>
> **Cline:** "On 'temporary' — that's the whole point of a spike. A one-shot reward fires once at the kill and then vanishes. A potential that's permanently elevated would create a standing 'be strong, stay in combat' bias. The strength potential then just echoes the spike smoothly."

**Resolution:** spikes (the objective — large, one-shot, temporary) sit above potentials (the shaping); what must outweigh is the spike against the accumulated safety penalty, not the strength potential.

### "Confidence" — you're describing intrinsic motivation

**From the conversation:**

> *Just prior, in the creature walkthrough:*
>
> **Cline:** "Memory of the unseen → No. Stale coordinates lie; the sound channel is the game's own 'behind me' cue."
>
> **You:** "even if you stop reporting creature location, you can still retain safety level calculation as long as it's true to state not perception. the agent can always turn around to see again, and hopefully this design encourages that behavior. which makes me think of adjusting the reward system on a third layer: confidence. even if a player's safety is compromised, having confidence about where the danger is coming from still lends a slight bit of relief. i wonder if there can be confidence in other things besides creature whereabouts which adds to reward? what do you think? am i conflating the idea of confidence with something else?"
>
> **Cline:** "Your instinct is sound and has a name: information gain / curiosity. The slight relief of knowing where the danger is = the value of information. 'Confidence' is the belief-state; 'information gain' is the reward for improving it. You're not conflating — you're circling a real third layer."
>
> **Cline:** "Reward the unknown→known transition: creature unseen→seen, object unrevealed→revealed, cell unexplored→explored, scroll used. It generalizes well beyond creatures — object reveal, map exploration, and the VISION/SEER scrolls are all the same mechanism. One caveat: it must be novelty-bounded, or the agent will just stand there looking around forever."
>
> **You:** "i love the information gain model!"

> ### The Crux
>
> **Cline:** "Your instinct is sound and has a name: **information gain / curiosity**. The slight relief of knowing where the danger is = the *value of information*. 'Confidence' is the belief-state; 'information gain' is the reward for improving it. You're not conflating — you're circling a real third layer:"
>
> - Reward the **unknown→known transition**: creature unseen→seen, object unrevealed→revealed, cell unexplored→explored, scroll used.
> - It generalizes well beyond creatures — object reveal, map exploration, and the VISION/SEER scrolls are all the same mechanism.
> - One caveat: it must be **novelty-bounded** (reward the *first* time you learn a thing, not every re-look), or the agent will just stand there looking around forever.
>
> So: spikes (what was achieved) + potentials (how good now) + information-gain (what did I learn). Three layers, each doing a distinct job.

**Resolution:** a third layer joins the two — information gain, novelty-bounded rewards for the unknown→known transition.

