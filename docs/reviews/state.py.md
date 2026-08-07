# state.py — Design Review

_8 Aug 2026 — Brandon & Cline_

This records observations, concerns, alternatives, and decisions from a line-by-line review of `daggorath_gym/state.py`. The file deserializes raw byte frames from the Lua state module into immutable `DaggorathState` value objects.

---

## 1. `FIELDS` visibility

**Observation:** `FIELDS` is a module-level public constant (no `_` prefix). The project convention says Python uses `_` for privacy. `env.py` imports `NUM_FIELDS` (derived from `FIELDS`), never `FIELDS` directly. Tests import `FIELDS`, `FRAME_LEN`, and `NUM_FIELDS` directly — standard test practice for accessing private names.

**Concern:** Making `FIELDS` public exposes internal schema structure that consumers (`env.py`) don't need. The derived `NUM_FIELDS` is the public API surface.

**Decision:** Deferred. Requires further discussion about whether the schema is a public contract (shared with Lua) or an implementation detail.

---

## 2. Flyweight pattern — `DaggorathStateSchema` class with one method

**Observation:** The schema exists as a class (`DaggorathStateSchema`) instantiated once as `_schema`. Its single method `unpack()` has no internal state. Could be a module-level `_unpack_frame(data)` function — same behavior, fewer lines.

**Concern:** The current implementation isn't wrong, but it may not be implementing the Flyweight pattern as thoroughly as intended. A class wrapper around a single stateless method adds abstraction without value.

**Decision:** Deferred. Requires professional research on proper Flyweight implementation. The current code works correctly; the question is whether a class or function better expresses the intent.

---

## 3. Cross-layer comment

**Observation:** Line 87: `"Strip the trailing newline that Lua appends (raw + \"\\n\")"` — references Lua internals. The project convention says each layer documents itself.

**Decision:** Changed to `"Frames are newline-delimited on the wire"`. Applied.

---

## 4. Typing imports

**Observation:** `from typing import Dict, List, Tuple` — Python 3.12 supports lowercase `dict`, `list`, `tuple` as built-in type hints.

**Decision:** Dropped `typing` imports. `FIELDS: List[Tuple[str, int, int]]` → `FIELDS: list[tuple[str, int, int]]`, `Dict[str, int]` → `dict[str, int]`. Applied.

---

## Deferred

| Topic | When |
|-------|------|
| FIELDS privacy (`_FIELDS` vs public) | Design session |
| Flyweight pattern implementation | Professional research |