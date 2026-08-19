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

### "Only the agent cares about novelty" → the environment/agent boundary

**From the conversation:**

> *Antecedent — the novelty-tracking prompt asked how "first time seen/explored/revealed" is represented, and I had proposed a novelty memory owned by the reward layer:*
>
> **You:** "when it comes to visitation of locations within a world, the environment can report the visitation but it shouldn't care whether that has been done before, only the agent cares."

> ### The Crux
>
> **Cline:** "Novelty is not a thing the environment computes. It's a thing the environment's reports let the agent compute."

**Resolution:** the environment reports perception — including visitation — and never judges whether something has been seen before. Novelty is subjective, so it belongs on the agent side.

### "Reward calculation shouldn't be in the environment" → three-role split

**From the conversation:**

> **You:** "this is one of the reasons i disagree with environment being responsible for reward calculation at all."

> ### The Crux
>
> **Cline:** "The reward is part of the task, not part of the world. The environment answers 'what is true and what does the player perceive'; the reward answers 'is this situation good.' Environment = objective reporter, reward = valuation, agent = learner."

**Resolution:** reward is a separate component from the environment — the environment reports facts and perception; the reward assigns value; the agent learns.

### "Even reward facts are facts" → fact vs valuation

**From the conversation:**

> **You:** "in super mario brothers, obtaining coins is a fact and is defined by the game as a measure of reward; also, completing levels is a fact... however, there is always an element of subjective interpretation to those rewarding facts/events which should be up to the training algorithm (player) to determine for themselves. ... the distinguishment is even more complex due to the interplay of game elements and game mechanics."

> ### The Crux
>
> **Cline:** "The boundary isn't 'rewarding facts' vs 'non-rewarding facts.' It's fact vs valuation, all the way down. The environment's side is 'what is true / what happened / what the player perceives'; the other side is 'what any of it is worth.'"

**Resolution:** even a game's own reward signals (score, victory, kill-grants-strength) are facts, not value. The environment reports facts and events; the reward assigns all value. Daggorath is harder because potentials and entangled mechanics (strength ↔ kills ↔ combat ↔ exertion ↔ safety ↔ light) are pure interpretation.

### "SB3: wrapper, scalar reward" → the customization surface

**From the conversation:**

> **You:** "what options does stablebaselines3 provide for customization. is it possible to override the reward environment returns? does reward have to be one dimensional? can we control how reward is used in training?"

> ### The Crux
>
> **Cline:** "Yes, no, and yes. SB3 consumes whatever scalar `env.step()` returns; a `RewardWrapper` (or `VecEnvWrapper`) overrides the reward before it reaches the algorithm. Rewards are stored as a `float32` array of shape `(buffer_size, n_envs)` and GAE/n-step returns do scalar arithmetic, so reward must be one scalar per step."

**Resolution:** SB3 supports the wrapper architecture natively. Reward must be a single scalar per step, so the wrapper's job is to collapse spikes, potentials, and information gain into one number. Potential-based shaping (γ·Φ(s′) − Φ(s)) lives in the wrapper, which holds the transition across steps.

### "The wrapper is agent-side; info leaks hidden state"

**From the conversation:**

> **You:** "info needed for calculating reward must necessarily carry state that should be hidden from agent." and "i thought the wrapper would be written on the agent side and plugged in."

> ### The Crux
>
> **Cline:** "`info` is the wrong channel... the reward wrapper reads true state through the environment object itself, not through the step return. 'Hidden from the agent' means hidden from the policy's input — the observation — not hidden from the reward function."

**Resolution:** true state flows from the environment to the wrapper through the environment object, never through `info` or the observation. `step()` returns perception only. The wrapper is agent-side code, plugged in around the environment.

### "Termination is environment-side"

**From the conversation:**

> **You:** "termination is definitely environment side, and yes i agree with the objective fact loss vs win."

> ### The Crux
>
> **Cline:** "`_check_terminated` stays in the environment — it detects the objective game-over (death → `game_mode` FF; win → ring type 0x12) and reports the cause. Only reward leaves. The wrapper assigns the terminal value (-1 / +1)."

**Resolution:** termination detection (the objective game-over fact and its cause) is the environment's job; only its value is the wrapper's. Reward and termination are separate threads.

### "Novelty is layered milestones" → designing the memory

**From the conversation:**

> **You:** "how about the novelty of basic objects? ... how about the novelty of a new door or portal or whatever? ... when it comes to creatures, i guess there's a creature's location, but then there's also creature types you might not have seen before. ... there's also new sounds. i guess that would primarily be creatures."

> ### The Crux
>
> **Cline:** "Novelty isn't one flag per domain; it's layered milestones, each with its own identity and worth. The memory is a set of monotonic knowledge milestones, and the reward is new milestones this step, weighted by kind."

**Resolution:** the memory holds milestones across domains — explored cells (weighted by content: door > open > wall), encountered and revealed objects, creature types heard and seen, and creature instances seen. The approach sound is the usual first trigger for the type-heard milestone, because sound reaches farther than sight.

### "Combat novelty decays" → flags vs counters

**From the conversation:**

> **You:** "there's also the novelty of combat... how hard do they hit? how much damage can they take?" and "heard and seen wear off quick, but fought is a kind of novelty that lasts longer because it really takes many fights to learn what this new creature is like."

> ### The Crux
>
> **Cline:** "Facts are learned in one exposure (flags, one-shot); skills are learned by repetition (counters, decaying). Combat is a count-based exploration bonus: each kill pays 1/√N per type, where N is the type's kill count."

**Resolution:** the memory has two kinds of entries — one-shot flags (heard, seen, explored, encountered, revealed, instance seen) and a decaying counter (combat, per-type kill count, 1/√N). The kill spike pays every kill; the combat novelty pays the learning and fades as the type becomes familiar.

### "Advance vs. discovery"

**From the conversation:**

> **You:** "i think the 'cell' centric view of the novelty flag for exploration is the wrong one. line-of-sight provides a host of information about the map altogether. moving into a new cell is logically good as reward because it means moving and can help push the agent along one step at a time, but the larger information gain of the map structure is much more significant."

**The recap:**

> Two different rewards, two different jobs. **Per-cell "advance"** — moving into a new cell pays a little. This is a *locomotion* signal: dense, small, its job is credit assignment over long corridors. "You're making progress, keep going." It's not really about information at all. **Structural discovery** — line-of-sight delivers a corridor's worth of geometry *at once*: the walk's extent, its termination, the branches off it. That's the information gain, and it's fundamentally *holistic*, not cell-wise.
>
> The point is clean: a straight corridor cell is predictable — once you've seen one, you've seen them all, so each new one conveys almost no surprise. A **junction** (three exits instead of two), a **door**, a **dead end** (the walk terminating) — those are the low-probability, high-surprise observations. That's where the information actually lives. So the info-gain term should credit *salient features discovered*, not *cells counted*.
>
> What line-of-sight can actually extract: (1) **termination type** — did this view end in a wall (dead end), a door, or run out of light (continues beyond sight); (2) **lateral exits / junctions** — a cell along the walk with an open edge perpendicular to the path is a branch; (3) **door and wall placements** — the map's decision points and its boundaries.
>
> The shape: **advance (dense, small)** — each newly-entered cell pays a trickle, keeping the agent moving; **discovery (sparse, large)** — each newly-revealed salient feature pays. *Discovery dominates; advance is small.* If discovery is the only term, the reward is too sparse to guide the agent through a ten-cell corridor. If advance is the only term, you're back to cell-counting with no notion of *why* the map matters.
>
> Why it's a big one: with the minimal reward (survival margin + death penalty), the *optimal* policy is to stand still. `m0221` doesn't rise if you don't exert, so the margin stays high — no risk, no death, steady reward. There's no gradient pulling the agent into the dungeon at all.

**Resolution:** exploration reward is two-tier — a dense per-cell *advance* term for locomotion, and a sparse structural *discovery* term for salient features (junctions, doors, dead ends, corridor terminations); both novelty-bounded in the reward wrapper, discovery dominating.

### "Light coefficients"

**From the conversation:**

> **You:** "for reward coefficients, we should apply some light, reasonable thinking and get this thing out the door."

**The recap:**

> The scale rule is *terminal ≫ discovery ≫ advance*. Terminal events (±1) are the goal and must dominate. Discovery — a newly revealed salient feature (junction, door, dead end) — is a meaningful tenth (+0.1): sparse and structural, worth real value. Advance — each newly entered cell — is a dense hundredth (+0.01): a trickle of locomotion credit, not real information. Survival shaping is potential-based (γ·Φ(s′) − Φ(s), Φ = `player_strength − m0221`, γ = 0.99), so it densifies the signal without changing the objective. The numbers are light, reasonable, and tunable — not final.

**Resolution:** win +1.0, death −1.0, discovery +0.1, advance +0.01, survival γ·Φ(s′) − Φ(s) with γ = 0.99.

