## Deployment

### "Environment-only; training is external"

**From the conversation:**

> *The user wanted to reach SB3 training while keeping the environment free of training libraries:*
>
> **You:** "i want to get to actually using this environment in sb3. this project, however, is for the environment only. it should not import training libs. therefore, i probably need to create an external folder for training with sb3, and expand the workspace."

> ### The Crux
>
> **Cline:** "Yes — that's the correct split, and it's already largely true: `daggorath_gym` depends only on `gymnasium` + `numpy`, so nothing there imports SB3/torch today. The training side is genuinely separate."

**Resolution:** the environment repo never imports a training library; SB3 training lives in a sibling project.

### "Two repos under one folder, and the name"

**From the conversation:**

> *The user settled the folder shape, then named the training project:*
>
> **You:** "I think i'm going to reconstruct my folders so that the 'daggorath' folder is top level for both the gym and sb3, then create subfolders named after the repos for both gym and sb3 projects."
>
> **You:** "i'm actually thinking of calling the sb3 project 'daggorath-agent'. got any other recommendations?"

> ### The Crux
>
> **Cline:** "It completes the pairing. The project already speaks in the 'three-role split' language from `reward/conversation.md`: *environment = objective reporter, reward = valuation, agent = learner*. So `daggorath-gym` (the environment) + `daggorath-agent` (the learner) is a clean, self-documenting pair — one is where the game *runs*, the other is *who plays it*."

**Resolution:** a top-level `daggorath/` folder holds `daggorath-gym` and `daggorath-agent` — two independent repos, the environment and its trainer.

### "Register it, but the reward is a choice"

**From the conversation:**

> *The user took the external trainer's perspective and asked whether to register:*
>
> **You:** "now let's take the perspective of someone trying to use my environment to train their own agent. how would they use the repo in this case? should my environment be registered with gymnasium?"

> ### The Crux
>
> **Cline:** "Registration is the *standard, discoverable* interface: it's how SB3, RLlib, CleanRL, `gymnasium.vector.make`, and eval harnesses all expect to find a custom env."
>
> **Cline:** "Register the raw env only (`Daggorath-v0` = the objective world, `reward == 0.0` placeholder). This honors the 'fact vs valuation' split — the environment is a reporter, and the reward is a *choice* the user makes."

**Resolution:** register `Daggorath-v0` (the raw environment) at import time; the reward wrapper is an opt-in, agent-side choice — the world and its worth stay separate.

### "daggorath-agent is the reference implementation"

**From the conversation:**

> *Registration alone leaves the hard parts of consumption unaddressed:*
>
> **Cline:** "The non-trivial parts of using this env — the `Dict` observation (CNN over `map`, MLP over entities/scalars), the factored `MultiDiscrete` action, and the INCANT joint-masking — are *not* 'solved' by `gym.make`."

> ### The Crux
>
> **Cline:** "That's exactly what **`daggorath-agent`** becomes: a working reference implementation (env → wrapper → `VecEnv` → PPO → feature extractor → policy) that an external user reads and adapts. Registration answers 'how do I get the env'; `daggorath-agent` answers 'how do I actually train with it.'"

**Resolution:** `daggorath-agent` is the reference trainer — the wiring an external user copies, beyond what `gym.make` provides.
