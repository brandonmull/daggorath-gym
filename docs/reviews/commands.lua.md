# commands.lua — Design Review

_8 Aug 2026 — Brandon & Cline_

This records observations, concerns, alternatives, and decisions from a line-by-line review of `emulation/commands.lua`. The file receives 1-byte command indices from the command socket, looks up the corresponding command phrase, and dispatches it to the game's text parser.

---

## 1. `cmdIndex` → `commandIndex`

**Observation:** `cmdIndex` abbreviated "command index" — violates the fully-worded terminology convention.

**Decision:** Renamed to `commandIndex`. Applied.

---

## 2. `_natkeyboard` → `_keyboard`

**Observation:** `_natkeyboard` abbreviated MAME's port name — violates the convention.

**Decision:** Renamed to `_keyboard`. Applied. The MAME port name (`":natkeyboard"`) stays as-is because it's the API identifier.

---

## 3. `_primed` → `_inputPrimed`

**Observation:** `_primed` didn't say what was primed. The comment says "Prime the input buffer" but the variable name didn't carry that context.

**Decision:** Renamed to `_inputPrimed`. Applied.

---

## 4. Keyboard acquisition — eager instead of lazy

**Observation:** The original code had three nil-checks for `_keyboard` — acquired during priming on first frame, with a fallback acquire on first real command dispatch, plus a guard before `post()`. This defensive pattern signaled uncertainty about when the port becomes available.

**Alternatives considered:**

- **Acquire eagerly in `beginProcessing`.** If the port isn't ready, fail immediately with a clear error. No per-frame nil checks needed.
- **Retry during priming.** Try N frames; error if still unavailable.

**Decision:** Eager acquire in `beginProcessing`. If `manager.machine:ioport().ports[":natkeyboard"]` returns nil, the module prints an error and returns without registering the frame notifier — a hard failure. Applied.

---

## 5. Grammar and phrase building

**Observation:** Four alphabetically-ordered grammar constants (`COMMAND_WORDS`, `COMMAND_DIRECTIONS`, `OBJECT_CLASSES`, `OBJECT_PROPER_NAMES`) feed two builder functions (`_build_object_specifiers`, `_build_command_phrases`). The resulting `COMMAND_PHRASES` list (154 entries) mirrors `commands.py` exactly. The structure is clean and the order is the shared contract.

**Decision:** No changes needed.

---

## Deferred

None.