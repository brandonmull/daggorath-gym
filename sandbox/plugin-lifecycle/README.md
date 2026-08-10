# Plugin Lifecycle Sandbox

Tests MAME's Lua plugin lifecycle — which notifiers fire, when they fire, and whether they survive machine resets.

**Key finding:** `emu.add_machine_*_notifier()` return values MUST be saved in a Lua variable. Discarding them allows Lua's garbage collector to auto-unsubscribe, which was the root cause of "notifiers dying" bugs.

## Quick Start

```bash
python sandbox/plugin-lifecycle/server.py
```

## Architecture

```
sandbox/plugin-lifecycle/
├── plugin.json          # MAME plugin descriptor
├── init.lua             # Plugin entry point + notifier callbacks
├── server.py            # Python launcher — launches MAME, reads log.txt
├── log.txt              # Output log (never created or deleted by code)
└── README.md            # This file
```

## What We Tested

| Test | Result |
|------|--------|
| `emu.add_machine_reset_notifier` with saved subscription | ✅ Fires on init, hard_reset, and soft_reset |
| `emu.add_machine_stop_notifier` with saved subscription | ✅ Fires on exit AND hard_reset (teardown phase) |
| `emu.add_machine_frame_notifier` with saved subscription | ✅ Fires continuously through all resets |
| `emu.add_machine_pause_notifier` | ❌ UI-driven only — can't trigger from natkeyboard mode |
| `emu.add_machine_resume_notifier` | ❌ Same as pause |
| `emu.wait(seconds)` from coroutine | ❌ ACCESS VIOLATION during startup — machine not ready |
| `emu.wait_next_update()` from coroutine | ✅ Works for coroutine-based timing |
| `manager.machine.paused` | ✅ Read-only property — works as memory-readiness gate |
| Notifiers with DISCARED subscriptions | ❌ Fire once, then die (GC auto-unsubscribes) |

## Production Architecture

Three notifiers, all subscriptions saved to module-local Lua variables:

| Notifier | Fires when | Action |
|----------|-----------|--------|
| `reset_notifier` | Machine init, hard_reset, soft_reset | Re-acquire memory handle, reset frame counter |
| `stop_notifier` | Machine exit, hard_reset teardown | Flush remaining buffer |
| `frame_notifier` | Every frame (gated by `machine.paused`) | Read RAM signals, buffer, flush every 60 frames |

## Files

| File | Purpose |
|------|---------|
| `init.lua` | Plugin entry point. Opens log, registers all three notifiers with saved subscriptions. |
| `server.py` | Python launcher. Fully detached — no pipes, no file management. Just launches MAME, waits 30s, reads `log.txt`. |
| `log.txt` | Output log written by the Lua plugin (`"w"` mode in `startplugin()`). |
