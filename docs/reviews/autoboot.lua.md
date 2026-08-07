# autoboot.lua — Design Review

_8 Aug 2026 — Brandon & Cline_

This records observations, concerns, alternatives, and decisions from a line-by-line review of `emulation/autoboot.lua`. The file is the MAME autoboot entry point; it opens two TCP sockets and hands them off to the state and commands modules.

---

## 1. Missing `local` on module `require()`s

**Observation:** `state = require("state")` and `commands = require("commands")` create global Lua variables in MAME's embedded Lua environment. Any other script could collide with these names.

**Decision:** Add `local` to both: `local state = require("state")`, `local commands = require("commands")`. Applied.

---

## 2. Socket error signaling

**Observation:** If a socket fails to open, autoboot calls `return` — MAME keeps running, the bridge on the Python side waits 30 seconds for a TimeoutError, and the only clue is a print statement in MAME's stdout.

**Decision:** Send errors to stderr + call MAME's exit function. Both `io.stderr:write()` for diagnostics and MAME's Lua exit API need sandboxing. Deferred to sandbox experiment.

---

## 3. Hardcoded host/ports — two-sided contract

**Observation:** `HOST`, `STATE_PORT`, `COMMAND_PORT` must match `SocketConfig` on the Python side. Any configuration change requires editing both files. Unlike frame_sampling_rate (Lua-only), this is a shared contract.

**Decision:** Deferred. The values are well-known conventions (localhost, 15000/15001) and unlikely to change except during parallel training, which requires per-instance autoboot scripts anyway. A comment documenting the contract between both sides would help.

---

## 4. `frame_sampling_rate` hardcoded

**Observation:** `{ frame_sampling_rate = 1 }` is inlined in the `state.beginWatching()` call. If we want a different rate, we must edit this file.

**Decision:** Deferred. This is a Lua-only concern — no Python-side contract. Could be extracted to a local constant later.

---

## 5. Module hand-off pattern

**Observation:** The two-line hand-off (`state.beginWatching(...)` / `commands.beginProcessing(...)`) is clean. Autoboot doesn't know about RAM addresses, frame notifiers, or command dispatch. Well-designed.

**Decision:** No changes needed.

---

## 6. Method naming: `state.watch` → `state.beginWatching`, `commands.start` → `commands.beginProcessing`

**Discussion:** The original single-word verbs (`watch`, `start`) appeared to act on the socket parameter rather than the game concept. The `beginX` prefix signals starting a continuous activity; the gerund tells you what the activity is (watching the game, processing commands). The socket parameter says *how* (via this socket).

**Decision:** Renamed in both module files and at the call site in `autoboot.lua`. Applied.

---

## Deferred

| Topic | When |
|-------|------|
| Socket error → stderr + MAME exit | Sandbox experiment |
| Hardcoded host/ports contract | Review when parallel training needs it |
| frame_sampling_rate configuration | Review when different rates are needed |