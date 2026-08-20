## Commands

### Factoring the action space

**From the conversation:**

> *The factored action space was already a settled design decision; the user asked for the motivation before implementation:*
>
> **You:** "so exactly what is this item all about: 'factored' action space?"
>
> **Cline:** "'Factored' here means **splitting one flat 154-way choice into two orthogonal dimensions** — like factoring a number. Instead of the agent picking a single integer 0–153, it picks a *pair*: `(template, object)`."
>
> **Cline:** "The `object = 25` is literally the number it just read out of its `hands`/`pack`/`objects` observation. **Zero translation** — you act on an object by echoing the index you saw it at. That's the whole point: it collapses 124 GET/PULL buttons into 4 templates + one shared index."

> ### The Crux
>
> **Cline:** "Factor the action space into 'which command shape' × 'which object', and reuse the observation's object index so the agent never has to learn a separate action↔object mapping."

**Resolution:** `Discrete(154)` becomes `MultiDiscrete([26, 31])` = (template, object); the object index is shared end-to-end with the observation, and direction is deliberately not factored (LEFT/RIGHT overloaded).

### Masking a factored space — the joint constraint

**From the conversation:**

> *Having accepted the (template, object) split, the user proposed shrinking the space dynamically to steer the agent:*
>
> **You:** "couldn't we assist the agent in choosing the correct pair by dynamically reducing action space based on choice of command: e.g. INCANT only allows so many targets?"
>
> **Cline:** "Yes — that's a well-known RL technique called **invalid-action masking** (or just 'action masking')."

> ### The Crux
>
> **Cline:** "For a `MultiDiscrete([26, 31])`, SB3's mask is a *list* — one boolean vector per axis. The two axes are masked and sampled **independently**. That means a mask can only say 'this axis value is always invalid' — it **cannot** express 'object 25 is valid for PULL LEFT but invalid for INCANT.'"
>
> **Cline:** "So a standard per-axis mask can't cleanly encode INCANT's restriction. The only way to get conditional-on-template masking is an *autoregressive/hierarchical* policy: sample the template first, then mask the object axis *given* that template."

**Resolution:** the INCANT restriction is a joint (template × object) rule, not a per-axis one, so it needs a custom or autoregressive policy — not SB3's default per-axis mask.

### The "???" is the game's own verdict

**From the conversation:**

> *The masking discussion stalled on what to do with invalid pairs, and the user surfaced the player-experience angle:*
>
> **You:** "i think no matter what we do, there will always be the potential for agent to attempt an invalid command. even when their command is syntactically correct, it might be completely inappropriate to current state: e.g. PULL LEFT SWORD when agent doesn't have a sword. it seems like we should build in a signal to the agent about invalid command occurring. this is definitely what players experience during the game, and i'm going to tell you that when i've played the game and saw '???' it gave me pause like i just received a fairly loud negative signal."

> ### The Crux
>
> **Cline:** "There are actually **two different kinds of 'invalid,'** and they need different handling. Semantic invalidity — the phrase is syntactically fine but wrong *for the current state*: `PULL LEFT SWORD` when you hold no sword. **This is your '???.'**"
>
> **Cline:** "semantic validity can't be enumerated by us — it depends on the full hidden state (what you hold, what's adjacent, torch, level). Only the game knows. And the game *tells* you, loudly, with '???'."
>
> **Cline:** "The signal already exists — twice over. The '???' text itself is already decoded every frame into `state.command_text`. And `perfectMatch` at `0x027B` — a 1-byte parser flag: `0xFF` when the parser matched a complete valid command, `0x00` otherwise; 'an unrecognised command that produces `???` does not set this flag.'"

**Resolution:** syntax vs. semantics — the game's "???" (already decoded as `command_text`, or `perfectMatch` at 0x027B) is the universal semantic-invalid verdict; surface it (perception flag) and price it (reward) instead of reimplementing validity.

### Prevent what you can, punish what you can't

**From the conversation:**

> *The user responded to the 'a no-op gives no penalty' point with a two-tier penalty proposal:*
>
> **You:** "syntactically invalid commands should be learned quickly and definitely avoided. i think they should produce higher penalty. statefully invalid commands should provide a medium penalty, like you proposed."

> ### The Crux
>
> **Cline:** "Your two-tier instinct is reasonable, but I'd reframe it — because the RL-correct split here is **'prevent what you can, punish what you can't,'** not 'high penalty vs. medium penalty.'"
>
> **Cline:** "A syntactically-invalid pair (INCANT + non-ring) is invalid *always and forever* — it has nothing to do with the game, it's an artifact of how we factorized the space. There's nothing for the agent to *learn*. 'Definitely avoided' is achieved *more* definitely by masking than by any penalty."
>
> **Cline:** "Semantic-invalid is the one worth *punishing*: it's state-dependent, genuinely learnable structure. We can't mask it without reimplementing the game's validity rules, so we let the game judge, and we price its verdict at ~−0.1."

**Resolution:** syntactic-invalid is an encoding artifact — prevent it (no-op now, joint mask later), never penalize; semantic-invalid is learnable structure — punish at ~−0.1 from the game's "???" verdict, charged once per rejection.

### "Write the custom policy now" → no-op now, policy later

**From the conversation:**

> *The user rejected deferring masking, asking to write the policy immediately; the reply was grounded in the actual project stack:*
>
> **You:** "no. let's write the custom policy now, not later."
>
> **Cline:** "A 'policy' in the RL sense is a *neural-network policy class inside the training stack* (`torch.nn.Module` / an SB3 `ActorCriticPolicy` subclass). Writing one now would mean (a) adding torch + SB3 as dependencies, and (b) producing a class that nothing instantiates — which is exactly the 'speculative API surface' the project rules forbid."

> ### The Crux
>
> **Cline:** "The part of this that *isn't* a policy is the part we should write now: the **joint validity mask** — and that's an *environment* concern, not a policy concern. The 'custom policy' you're describing is just the *consumer* of this mask."
>
> **You:** "i see. so we go with no-op now, then add policy later."

**Resolution:** the mapping returns `None` and `step()` no-ops on syntactically-invalid pairs now; the joint `action_mask()` + custom policy is the milestone-4 consumer, once torch/SB3 and a training loop exist.