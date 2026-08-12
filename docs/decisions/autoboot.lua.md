# autoboot.lua — Implemented Decisions

_8 Aug 2026_

This records the concrete code changes applied to `emulation/autoboot.lua` during the post-build review.

## Applied Changes

### `local` on module `require()`s

`state = require("state")` → `local state = require("state")`. Same for `commands`. Lua module references were global variables; they're now local to prevent collisions in MAME's Lua environment.

### Method naming: `state.watch` → `state.beginWatching`, `commands.start` → `commands.beginProcessing`

The original single-word verbs (`watch`, `start`) were misleading — they appeared to act on the socket parameter rather than the game concept. The `beginX` prefix signals that these start a continuous activity (registering a frame notifier that runs indefinitely). The gerund tells you *what* the activity is — watching the game, processing commands. The socket parameter says *how* (via this socket).

Both methods renamed in their respective module files (`state.lua`, `commands.lua`) and at the call site in `autoboot.lua`.

---

_12 Aug 2026_

## Historical: File Deleted

`autoboot.lua` was deleted during the plugin conversion. Its role — opening IPC channels and handing off to `state.lua` and `commands.lua` — is now performed by `emulation/plugins/daggorath/init.lua` via the `startplugin()` entry point. See `docs/decisions/plugin-conversion.md`.