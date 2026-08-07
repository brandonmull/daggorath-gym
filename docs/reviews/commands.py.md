# commands.py — Design Review

_8 Aug 2026 — Brandon & Cline_

This records observations, concerns, alternatives, and decisions from a line-by-line review of `daggorath_gym/commands.py`. The file enumerates the 154 valid command phrases for Dungeons of Daggorath and provides the `DaggorathCommand` value type.

---

## 1. Cross-layer docstring

**Observation:** Module docstring: `"Mirrors the Lua commands.lua grammar."` — references Lua internals. The project convention says each layer documents itself.

**Decision:** Changed to `"Enumerates the 154 valid command phrases for Dungeons of Daggorath."` Applied.

---

## 2. `NUM_COMMANDS` — ugly name, questionable design

**Observation:** `NUM_COMMANDS` is a module-level `UPPER_SNAKE_CASE` constant — reads like a C macro. `env.py` imports it solely to construct the action space. The count is derivable from `len(_COMMAND_PHRASES)`.

**Decision:** Deferred — part of the broader gym space architecture design session (see `docs/reviews/environment.py.md` #1).

---

## 3. `DaggorathCommand` — frozen dataclass

**Observation:** Clean pattern — `frozen=True` ensures immutability, `__post_init__` validates index range, `phrase` property provides human-readable string. No issues.

---

## 4. Grammar constants and builder functions

**Observation:** Four alphabetically-ordered constants (`_COMMAND_WORDS`, `_COMMAND_DIRECTIONS`, `_OBJECT_CLASSES`, `_OBJECT_PROPER_NAMES`) feed two builder functions (`_build_object_specifiers`, `_build_command_phrases`). The resulting `_COMMAND_PHRASES` list (154 entries) mirrors `commands.lua` exactly. The structure is clean and the order is the shared contract.

**Decision:** No changes needed.

---

## Deferred

| Topic | When |
|-------|------|
| `NUM_COMMANDS` naming and location | Gym space architecture design session |