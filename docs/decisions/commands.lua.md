# commands.lua — Implemented Decisions

_8 Aug 2026_

This records the concrete code changes applied to `emulation/commands.lua` during the post-build review. For the full analysis, see `docs/reviews/commands.lua.md`.

## Applied Changes

### `cmdIndex` → `commandIndex`

The local variable `cmdIndex` abbreviated "command index." Renamed to `commandIndex`.

### `_natkeyboard` → `_keyboard`

The internal variable `_natkeyboard` abbreviated MAME's port name. Renamed to `_keyboard`. The MAME port identifier (`":natkeyboard"`) stays as-is because it's the API name.

### `_primed` → `_inputPrimed`

The boolean flag `_primed` didn't say what was primed. Renamed to `_inputPrimed`.

### Keyboard acquisition — eager instead of lazy

The original code had three nil-checks for `_keyboard`: acquired during priming on first frame, with a fallback on first real command dispatch, plus a guard before `post()`. This defensive pattern signaled uncertainty about when the port becomes available.

The keyboard is now acquired once in `beginProcessing()`. If the port isn't available, the module prints an error and returns without registering the frame notifier — a hard failure. No per-frame nil checks remain in `_onFrame()`.

---

_12 Aug 2026_

### Frame notifier subscription saved

The return value from `emu.add_machine_frame_notifier(_onFrame)` is now saved to `_frameSubscription`. Previously discarded, which allowed Lua's garbage collector to auto-unsubscribe the notifier after machine resets (see `docs/decisions/gc-autounsubscribe.md`).

### File moved

`emulation/commands.lua` → `emulation/plugins/daggorath/commands.lua`. Part of the plugin conversion — all Lua files now live under the plugin directory.
