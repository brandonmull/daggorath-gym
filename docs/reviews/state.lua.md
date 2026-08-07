# state.lua — Design Review

_8 Aug 2026 — Brandon & Cline_

This records observations, concerns, alternatives, and decisions from a line-by-line review of `emulation/state.lua`. The file reads 12 game state fields from emulated RAM each frame and writes them as raw bytes to the state socket.

---

## 1. `_memspace` → `_memory`

**Observation:** The internal variable `_memspace` abbreviated "memory space" — violates the fully-worded terminology convention. The assignment from `cpu.spaces["program"]` provides the "space" context.

**Decision:** Renamed to `_memory`. Applied.

---

## 2. `_sample` → `_sampleState`

**Observation:** `_sample()` didn't name what it samples. The verb+object convention says to name the object.

**Decision:** Renamed to `_sampleState()`. Applied.

---

## 3. Variable naming: `_framesElapsed` vs `_frameSamplingRate`

**Observation:** One uses plural (`_framesElapsed`), the other singular (`_frameSamplingRate`). Same domain (frame counting), inconsistent.

**Decision:** Left as-is. The difference is defensible: `_framesElapsed` counts "frames that have elapsed," `_frameSamplingRate` is a "sampling rate" with "frame" as modifier. Minor.

---

## 4. `local raw` in `_sampleState`

**Observation:** Adjective used as noun. Standard Lua idiom for building byte strings efficiently via `table.concat()`.

**Decision:** No change. Idiomatic Lua.

---

## 5. Module structure

**Observation:** `beginWatching` stores config and registers the frame notifier; `_onFrame` handles lazy memory init and rate limiting; `_sampleState` does RAM reading and serialization. Each function has a clear single responsibility. The module is well-designed.

**Decision:** No changes needed.

---

## Deferred

| Topic | When |
|-------|------|
| Flyweight pattern implementation | Professional research needed — currently `SCHEMA` is a module-level constant, which is a valid simple flyweight |