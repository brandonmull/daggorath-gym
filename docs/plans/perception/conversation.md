## Perception

### "Act-first, fairness-later"

**From the conversation:**

> **Cline:** "Position + heading + body state, with no walls, no creatures, no goal, reduces to a random walk with a sparse death penalty."
>
> **You:** "it would be better to prioritize the state needed for the agent to successfully act, rather than worrying about how fair it's access to knowledge is in comparison to what a real player would have."

**The recap:**

> Position + heading + body state, with no walls, no creatures, no goal, reduces to a random walk with a sparse death penalty. The survival-margin potential gives the agent a number that drifts but nothing to act *on*; there's no gradient to follow. The twelve-field shell is a functioning interface, not a trainable task.
>
> The fix is a different scope, not more of the same: prioritize the state the agent needs to *act* — the maze, the creatures, the light — rather than worrying how fairly its access mirrors a real player's. This is the "expose now, remove later" scaffolding pattern the curriculum plan already sanctions (map memory is literally listed there as "provided now, removed later"); the decision extends the same pattern to creature positions and sight. **Act-first, fairness-later.**
>
> What it unblocks: sight-gating was the expensive part, not the maze or the creatures. The blockers are thinner than they look — the maze and the creature array are fully documented "knowns," not unknowns; the genuinely open questions (sight reach, read-atomicity) are refinements with bounded, low-stakes failure modes.

**Resolution:** the POC prioritizes the state the agent needs to act — self-fields plus the world (maze, creatures, light) — over faithfulness to what a real player perceives; fairness constraints are deferred to later curriculum stages.

### "The perception gate is RAM line-of-sight"

**From the conversation:**

> **You:** "i guess we need sight gating for this. we have to calculate what the player is able to see, without relying on screen visuals."
>
> **You:** "i definitely think effective light is what we should use."

**The recap:**

> The game itself computes visibility from RAM, so we mirror its own logic rather than reverse-engineer pixels — consistent with the project's "derive the cue, never read the output" principle (the sound plan already rejects reading the DAC for exactly this reason).
>
> The rule, from the line-of-sight sandbox's static trace: the renderer walks the **facing corridor** from the player's cell, depths `0…9`, stopping at the first facing edge that isn't open (normal door, magic door, and wall all occlude alike). A cell at depth `N` is drawn — and therefore seen — while `N < light`, where `light = m026E:m026F`, the effective level. So **reach = `min(light, 10)`**, and `light == 0` means nothing is visible — pure blackout, where even the own-cell walls vanish (authentic: in pitch black you navigate by feel). The `−7` offset in the renderer's dot-frequency math cancels out for the binary seen/not-seen boundary, so only `N < light` matters, not solid-vs-dotted.
>
> That's a ≤10-cell loop per step, reading edge bits from the decoded maze — cheap. The "sight gating is a lot of effort" concern was really about the sandbox's *screen-buffer-diff* approach; a RAM corridor-walk is a different, much smaller thing.
>
> The effective light is the *input*, not a separate binary gate: it sets the reach, and `light == 0` is the blackout. Darkness is just `reach == 0`.

**Resolution:** perception is RAM line-of-sight — a ≤10-cell corridor walk from the decoded maze, reach = `min(light, 10)` with `light = m026E:m026F`; no screen visuals, no distance math beyond the walk itself.

### "No memory in the observation"

**From the conversation:**

> **You:** "i don't think perceived state should actually include a memory of the map. it should only ever report the exact things the player can see at any given moment. the agent should be responsible for building its own memory, which can be done via wrappers."

**The recap:**

> The clean split: **perception = the environment's job** — instantaneous, stateless, a pure function of *current* true state + the torch gate; the env remembers nothing across steps. **Memory = the agent's job** — a wrapper accumulates whatever it needs, in whatever form the policy wants. That's exactly what wrappers are for.
>
> This simplifies the environment: no episode-long "visited cell" bookkeeping, no explored-vs-unexplored flags, no persistence anywhere in the environment. The observation is just "here's what's true right now, gated by light."
>
> Blackout semantics: when `light == 0`, the maze channel and the creature channel blank (and later, objects on the floor — the "and such"); the self-fields stay — position, heading, and body state are always known, because a player always feels where they stand and their own heartbeat even in the dark.

**Resolution:** the observation is instantaneous and stateless — the env reports only what's visible *now*, torch-gated; accumulated map and creature memory is the agent's job, built in a wrapper, never in the observation.

### "Look vs. Examine — modal perception"

**From the conversation:**

> **You:** "i would also like player inventory. i'm imagining a precondition to player perceiving inventory, which would be easy to do for first implementation (no memory). the player's perceived inventory is only given to them while they're in the EXAMINE mode."
>
> **You:** "being able to see dungeon or see inventory should be mutually exclusive. you have to be in LOOK mode and have a torch lit to see the dungeon. you have to be in EXAMINE mode to see inventory."

**The recap:**

> The signal is already known and already sampled — the mode is `displayFunction` (`0x02B2–0x02B3`), the same pointer the readiness gate reads. `0xCE66` is `NormalDisplay`, the dungeon view — `CmdLOOK` (C751) sets it: `LDX #$CE66; STX <displayFunction`, "the routine for drawing... the normal game screen." `0xD495` is `DrawInventory`, the inventory view — `CmdEXAMINE` (D481) sets it: `LDX #$D495; STX <displayFunction`, "to draw the inventory."
>
> Because it's a single pointer, the two are mutually exclusive by construction — the game runs one screen-drawing routine or the other, never both. The perception rule becomes modal and stays stateless: LOOK + `light > 0` reveals the dungeon (maze, creatures, floor objects); EXAMINE reveals the pack; self-fields and hands are always present (the HUD/status line is never gated). No memory — the mode is read fresh each frame, and what's visible is a pure function of `(mode, light, current state)`.
>
> One consequence: the readiness gate in `state.lua` currently returns early unless `displayFunction == 0xCE66`, so typing EXAMINE (`0xD495`) would close the gate and stop sampling. Supporting this means widening the gate to accept both `0xCE66` and `0xD495` as live play — which also corrects `ram-signals.md`'s note that "once 0xCE66, it stays there for the session."

**Resolution:** perception is modal — LOOK + torch reveals the dungeon, EXAMINE reveals the pack, mutually exclusive via `displayFunction` (`0xCE66` vs `0xD495`); self-fields and hands are always present. The `state.lua` readiness gate widens to accept both values.

### "Grid + CNN vs. flat + MLP"

**From the conversation:**

> **You:** "i'm not too familiar with available RL techniques related to this kind of thing. i really need a learning session on this topic to help me decide on a path forward."
>
> **You:** "regarding encoding, CNN with MultiInputPolicy."

**The recap:**

> The question is which network architecture gives the policy the right inductive bias for spatial data. An MLP treats all inputs as an unordered bag of numbers — two adjacent cells and two opposite-corner cells are equally "unrelated," so it must relearn "wall ahead" at every position (no translation invariance), and it wastes parameters (a flat 32×32 grid is 1024 inputs, ×256 hidden = 262k weights in layer one). A CNN slides a small filter over the grid, detecting a local pattern everywhere it appears — locality, translation equivariance, parameter sharing — which is exactly the right prior for a maze. This is the Atari playbook; Stable-Baselines3's `CnnPolicy` ships a NatureCNN for it.
>
> The encoding turns each grid cell into a vector of channels, one per fact (wall, door, creature, object, player, visible), like an image's RGB channels — the observation becomes a `(C, 32, 32)` picture. The 13 scalar self-fields have no place on the grid, so the observation is a `Dict`: `grid` (`C, 32, 32`) for the CNN, `scalars` (13 self-fields + hands + torch minutes) for an MLP, joined by `MultiInputPolicy`.
>
> The alternatives were a local 9×9 window + MLP (no CNN, but throws away global structure) and a naive flat ~1,200-dim vector (avoid). Given the need for spatial reasoning, the CNN grid is the natural fit — and less bespoke than hand-rolling a window.

**Resolution:** the observation is a `Dict` (grid + scalars) read by `MultiInputPolicy` — a CNN for the spatial grid, an MLP for the scalars.

### "Working agent means it can respond"

**From the conversation:**

> **You:** "for poc, i'm good with no memory. this is something i would like to focus on later... by 'working agent' i mean will it have the potential to respond to its environment. it's no good if the agent doesn't know there's a monster in front of it. it's no good if an agent doesn't know it's running into a wall. if it can respond to it's immediate circumstances appropriately but it ends up repeating itself periodically, that's okay for now."
>
> **You:** "reducing the action space is definitely important and needs to be done eventually. however, this, like memory, is an issue of training quality and should be saved for later."

**The recap:**

> "Working agent" is not "plays the whole game" — it is "responds correctly to its immediate circumstances." The agent must know there is a monster in front of it, and that it is running into a wall. If it reacts to the moment appropriately but wanders back into places it has already been, that is acceptable for the POC. Memory (remembering the map) and action-space reduction/masking are training-quality concerns, not correctness concerns — they are deferred, not omitted.

**Resolution:** the POC bar is immediate responsiveness; memory and action-masking are deferred.
