# state.lua — Implemented Decisions

_8 Aug 2026_

This records the concrete code changes applied to `emulation/state.lua` during the post-build review. For the full analysis, see `docs/reviews/state.lua.md`.

## Applied Changes

### `_memspace` → `_memory`

The internal variable `_memspace` abbreviated "memory space." The assignment from `cpu.spaces["program"]` provides the "space" context. Renamed to `_memory`.

### `_sample` → `_sampleState`

The internal function `_sample()` didn't name what it samples. The verb+object convention says to name the object. Renamed to `_sampleState()`.

---

_12 Aug 2026_

### `_socket` → `_stateFile`

The state channel is now a named pipe (FIFO) instead of an `emu.file("w")` TCP socket. The internal variable `_socket` renamed to `_stateFile` — it holds a standard Lua file handle from `io.open("w")`. Writes use `_stateFile:write()` instead of `_socket:write()`.

### Frame notifier subscription saved

The return value from `emu.add_machine_frame_notifier(_onFrame)` is now saved to `_frameSubscription`. Previously discarded, which allowed Lua's garbage collector to auto-unsubscribe the notifier after machine resets (see `docs/decisions/gc-autounsubscribe.md`).

### File moved

`emulation/state.lua` → `emulation/plugins/daggorath/state.lua`. Part of the plugin conversion — all Lua files now live under the plugin directory.
