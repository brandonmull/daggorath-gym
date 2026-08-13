# environment.py — Design Review

_8 Aug 2026 — Brandon & Cline_

This records observations, concerns, alternatives, and decisions from a line-by-line review of `daggorath_gym/environment.py`. The file is the Gymnasium environment wrapper; it bridges the MAME bridge layer to stable-baselines3.

---

## 1. `NUM_COMMANDS` and `NUM_FIELDS` imports

**Observation:** `environment.py` reaches into `commands.py` and `state.py` to import bare integer constants — `NUM_COMMANDS` (154) and `NUM_FIELDS` (11). These are used only to construct the gym action/observation spaces.

**Concern:** The names read like C macros, not Python identifiers. More importantly, the pattern of importing a derived count from a sibling module feels inverted — `environment.py` is the consumer and shouldn't need to know about internal module bookkeeping. The count is derivable from the data the module already exposes (`len(_COMMAND_PHRASES)`, `len(FIELDS)`), so the import is redundant at best and a sync hazard at worst (if someone adds a field and forgets to update the count constant).

**Alternatives considered:**

- **Keep counts but rename.** Changes the symptom, not the structure.
- **`len(_COMMAND_PHRASES)` / `len(FIELDS)` inline.** Simplest fix — removes the constant import entirely. But still leaves `environment.py` constructing gym spaces from what are essentially implementation details of sibling modules.
- **Delegate space construction to the modules.** `commands.action_space()` returns `spaces.Discrete(154)`, `state.observation_space()` returns a `Box` or `Dict`. The modules own the data, so they own the shape. But this pulls gymnasium into modules that currently describe only game concepts — a coupling that may not be desirable.
- **Let `environment.py` construct spaces from the module's public data.** The pragmatic middle: `environment.py` reads the module's data structures and builds spaces from them. No new abstractions, no cross-contamination.

**Decision:** Deferred to a focused gym space architecture design session. That session will pull gymnasium documentation for `Box`, `Discrete`, `Dict`, and `Tuple` spaces and choose the right shape for each. Until then, the current imports remain.

**Assumption:** The modules (`state.py`, `commands.py`) should not import gymnasium. They describe the game, not the RL framework.

---

## 2. `observation_space` static bounds

**Observation:** `spaces.Box(low=0, high=65535, shape=(11,), dtype=np.uint16)` assumes every field is a full-range unsigned 16-bit integer. The 11 fields include eight u8 values (natural range 0–255) and three u16 values (`ambient_light`, `player_weight`, `player_strength`), none of which meaningfully approach 65535. `ambient_light` in practice is a small value (the base dungeon illumination level).

**Concern:** Over-reporting the range degrades RL learning — the agent wastes exploration budget on values that can never occur. A field whose true range is 0–255 but whose space advertises 0–65535 means the agent considers 65,280 impossible values as part of its exploration space.

**Alternatives considered:**

- **Per-field bounds.** The schema (`FIELDS`) already tracks width. Adding `low`/`high` per field gives `environment.py` precise bounds to construct a `Dict` space or a `Box` with per-dimension `low`/`high` arrays.
- **`Dict` space.** More expressive — each field gets its own `Box` with correct bounds. More complex for the agent to process (SB3 typically flattens dict observations anyway). Worth exploring gymnasium docs before committing.

**Decision:** Deferred to the same gym space architecture design session as #1. The two are tightly coupled — where spaces live and what shape they take are the same question.

---

## 3. `reset()` — command readiness detection

**Observation:** `reset()` calls `self._bridge.recv()` and returns the first frame. During MAME startup, the game runs a demo loop (`game_mode=0xFF`) before transitioning to live play (`game_mode=0x00`). The first frame `recv()` returns may be from the demo — the agent would observe a game it can't control.

**Concern:** `game_mode` alone is not sufficient. Even after the transition to `0x00`, there may be a window where the input ring buffer isn't ready or the display is mid-redraw. We currently have no way to detect "ready to receive commands" from RAM alone.

**Alternatives considered:**

- **`while` loop in `reset()`** that discards frames until `game_mode == 0x00`. Simple but incomplete — doesn't guarantee input readiness.
- **Additional RAM signals.** `inputHead` (`0x02BC`) and `inputTail` (`0x02BD`) indicate ring buffer state; `displayFunction` (`0x02B2`) indicates the active screen. Combining `game_mode == 0x00` with `inputHead == inputTail` (empty buffer, ready for input) and a frame-count threshold after the transition may be sufficient.
- **Visual processing.** If RAM signals prove insufficient, we'd need to watch the CoCo's display output for known patterns (title screen, prompt cursor). Last resort — adds significant complexity.

**Decision:** Sandbox experiment needed. Investigate RAM signals first (game_mode + input buffer state + display function). Only resort to visual processing if RAM alone cannot disambiguate.

---

## 4. `step()` — command execution detection

**Observation:** `step()` sends a command byte, then immediately blocks on `recv()`. The next state frame reflects the game state *before* the command had time to take effect (or mid-effect). The game needs at least one frame to parse the command through its text parser, and potentially many more for animation, combat resolution, or creature movement.

**Concern:** The agent learns from stale observations — it issues a command and sees state that doesn't yet reflect the command's outcome. This is a fundamental RL problem (action lag), but we're not even giving the command one frame to propagate.

**Alternatives considered:**

- **Frame skip after send.** After sending, drop N frames before collecting the observation. Simple but blind — we skip frames whether or not the command has been processed.
- **Input ring buffer watch.** The input ring buffer at `0x02D1–0x02F0` (head at `0x02BC`, tail at `0x02BD`) tracks what the game's parser has consumed. After `natkeyboard:post()`, wait until `inputHead` advances — the parser consumed the command. Then sample state. This avoids visual processing entirely.
- **Console output watch.** Watch the CoCo's display for the command echo (the player's typed command appearing in the command area). More complex, requires visual processing or text output RAM monitoring.

**Decision:** Sandbox experiment needed — same scope as command readiness detection. The input ring buffer is the most promising signal. Validate that `natkeyboard:post()` delivery is observable via head/tail movement, and that the parser consumes in a predictable timeframe.

---

## 5. `_compute_reward` — placeholder calculation

**Observation:** `_compute_reward` returns `heart_beat_interval / 255.0`. Higher interval = slower heartbeat = less exertion. The comment says "reward shaping is out of scope."

**Concern:** The current placeholder is actively misleading. It suggests "stay calm" is always good, which is wrong for this game — you must fight creatures to gain strength, and combat raises heart rate. A placeholder that looks plausible will train an agent that maximizes the wrong objective, and its very existence removes the signal that reward needs design work.

**Alternatives considered:**

- **Return 0.** Neutral but silent — the training loop runs with zero reward, nothing signals that this is incomplete.
- **Return a comment-only placeholder.** Same problem — the code looks done.
- **Raise `NotImplementedError`.** Loud, Pythonic, can't be ignored. Crashes `step()` immediately, which is fine because `step()` won't be called in a training loop until reward is designed. The module tests don't exercise `step()`, so they remain green.

**Decision:** Replace with `raise NotImplementedError("Reward function not designed. See plans/reward.md (TBD).")`

**Assumption:** Module tests (`test_state.py`, `test_commands.py`) are the success criterion for the current phase. Integration tests that call `step()` wait until reward/termination are designed.

---

## 6. `_check_terminated` — partial wizard-dead check

**Observation:** `_check_terminated` returns `True` when `evil_wizard_dead == 0xFF`. The comment mentions "player fainted too long" as a TODO. Otherwise returns `False`.

**Concern:** Two issues. First, completeness: we haven't examined whether the wizard-dead byte persists or clears on respawn, whether there's a distinct "game over" screen with separate RAM state, whether the game has soft-lock states, or whether the agent should receive a terminal signal at all (vs. reward alone driving behavior). Second, the partial implementation looks complete enough to use — it removes the signal that more design work is needed. The same logic that applied to reward (a plausible-seeming placeholder that masks incompleteness) applies here.

**Counterpoint considered:** `return False` is the honest "not terminated" — it's not a placeholder, it's the accurate statement that no terminal condition was detected. But the wizard-dead check *is* a detection — it's a hypothesis we haven't validated.

**Decision:** Replace with `raise NotImplementedError("Termination conditions not designed.")` — same policy as reward.

**Assumption:** When a player dies, the game restarts the player in the dungeon rather than ending. Termination is complex enough to warrant its own design session.

---

## 7. `_check_truncated` — no truncation logic yet

**Observation:** `truncated = False` is set unconditionally in `step()`. There is no `_check_truncated` method.

**Concern:** While truncation is typically handled externally by gymnasium's `TimeLimit` wrapper, we may eventually want environment-level truncation (e.g., the game reaches a soft-lock state that isn't a terminal condition). More importantly, failing to provide a method for it removes the signal that this decision point exists — the same argument we applied to reward and termination: a plausible default that looks complete masks design work still needed.

**Alternatives considered:**

- **`return False` inline.** Correct for now (no step limit), but silent. The reader doesn't know whether truncation was considered or simply forgotten.
- **Extract to a method that returns False.** Makes the decision point visible without changing behavior. Still doesn't signal that more work may be needed.
- **Raise `NotImplementedError`.** Follows the same policy as reward and termination. Loud, honest about the gap, forces a design discussion before training can proceed.

**Decision:** Extract `_check_truncated(self, state) -> bool` as a method that raises `NotImplementedError("Truncation conditions not designed.")`. Same policy as reward and termination. When truncation is properly designed (or explicitly decided to be purely external via TimeLimit), the method gets a real body.

---

## 8. Module tests as success criterion

**Discussion:** Brandon proposed that the module tests (`test_state.py`, `test_commands.py`) should be the definition of "done" for the current implementation phase. If the modules pass their tests, the modules are correct. The env layer is a consumer — it's not testable end-to-end until reward and termination are designed, and that's a separate planning effort.

**Decision:** Agreed. Module tests passing = modules done. Env integration tests are blocked on reward/termination design. This clean separation prevents premature integration testing while keeping module quality high.

---

## 9. `reset()` — MAME configuration and randomness flow

**Observation:** `reset()` constructs a `MameBridge()` with no arguments — windowed, SDL sound, default ports. There is no path from the caller (training script, test suite) to MAME's command line. Additionally, `reset()` uses `**kwargs` which silently swallows gymnasium's `seed` and `options` parameters.

**Concern:** Headless training requires `window=False` and `sound="none"`. Testing may want a different timeout or ROM path. The env currently hardcodes bridge configuration, meaning every consumer that needs different MAME flags must edit source. On the seed/options front, stable-baselines3 calls `reset(seed=...)` on every episode — silently dropping it violates gymnasium's contract and will cause warnings.

**Alternatives considered:**

- **`__init__` stores bridge kwargs.** `DaggorathEnv(bridge_kwargs={"window": False})` — configuration lives at construction time. Matches how SB3 works (one `make()` call, many `reset()` calls). The env knows a bit about MAME configuration, which is a minor coupling but acceptable for the first design.
- **`reset(options=...)` passes bridge kwargs.** Configuration per episode. More flexible but unusual for RL — most envs don't reconfigure MAME between resets.
- **Bridge configuration lives in `config.py`.** The env reads defaults from a config module. `config.py` already exists but is dead code — this would revive it as the single source of truth.

**Decision:** Deferred. Open question: how should MAME configuration and randomness flow from the caller to the bridge? Needs more familiarity with gymnasium's conventions before committing. For now, `reset()` declares the full gymnasium signature (`seed`, `options`) so the contract is visible, but configuration flow is unresolved.

---

## Code-only changes (not requiring review doc)

The following were discussed and decided — they are implementation details, not architectural questions:

- **Docstring duplication:** Module docstring stays; class docstring gets specific (spaces, lifecycle, status).
- **`@staticmethod` → instance methods:** `_compute_reward` and `_check_terminated` become regular methods taking `self`. Reward and termination logic may eventually need instance state (history, episode context).
- **`step()` typing:** Signature updated to gymnasium's `step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]`.
- **`reset()` signature:** Declares full gymnasium signature `reset(self, *, seed=None, options=None)` rather than `**kwargs`. Returns `{"seed": seed}` in info dict per gymnasium convention. Seed isn't wired to an RNG yet.
- **`NotImplementedError`:** `_compute_reward`, `_check_terminated`, and `_check_truncated` all raise `NotImplementedError` rather than returning placeholder values. Consistent policy across all three step-outcome methods.

---

## Deferred to later design sessions

| Topic | Status |
|-------|--------|
| Gym space architecture (how env constructs action/observation spaces) | Open |
| Command readiness detection | Resolved — `displayFunction == 0xCE66` gate in state.lua (see `docs/decisions/readiness-gating.md`) |
| Command execution detection | Resolved — `perfectMatch` fingerprint (see `docs/findings/ram-signals.md`) |
| MAME configuration flow (how bridge kwargs reach `reset()`) | Resolved — `__init__(mame_config, ipc_config)`; seed still unwired |
| Reward function design | Open — needs a new plan doc |
| Termination condition design | Open — needs a new plan doc |
