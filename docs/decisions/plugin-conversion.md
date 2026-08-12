# Plugin Conversion

_12 Aug 2026_

## Decision

Replaced `autoboot.lua` + `-autoboot_script` with a MAME plugin loaded via `-plugin`.

## Why

The plugin lifecycle provides several advantages over autoboot scripts:

- **`startplugin()` survives machine resets.** The demo→live transition triggers a CoCo soft-reset. An autoboot script runs once at boot; a plugin's entry point fires on every machine initialization and survives all resets.
- **Reset/stop notifiers** are available for cleanup. The plugin can register `emu.add_machine_reset_notifier` and `emu.add_machine_stop_notifier` callbacks that fire on machine teardown — autoboot has no equivalent.
- **Proven in sandbox.** `sandbox/plugin-lifecycle/` validated the full plugin lifecycle: `startplugin()` fires on init, notifier subscriptions survive resets when saved to variables (GC fix), and the plugin persists through the demo→live transition.

## What Changed

### New: `emulation/plugins/daggorath/`

| File | Role |
|------|------|
| `plugin.json` | MAME plugin descriptor — `"start": "true"`, `"type": "plugin"` |
| `init.lua` | Entry point — `startplugin()` opens state FIFO + command socket, hands off to domain modules, registers reset/stop notifiers |
| `state.lua` | State reporting module (moved from `emulation/`) |
| `commands.lua` | Command dispatch module (moved from `emulation/`) |

### Deleted

`emulation/autoboot.lua`, `emulation/state.lua`, `emulation/commands.lua`

### Python changes

- `emulator.py`: `-autoboot_script <path>` → `-plugin <path>`, `-autoboot_delay` removed
- `MameConfig.autoboot_script_path` → `MameConfig.plugin_path`
- Tests use `IpcConfig` instead of `SocketConfig`

### GC fix applied

All three notifier subscriptions are saved to module-local variables:
- `init.lua`: `resetSubscription`, `stopSubscription`
- `state.lua`: `_frameSubscription`
- `commands.lua`: `_frameSubscription`

This prevents Lua's garbage collector from auto-unsubscribing after machine resets (see `docs/decisions/gc-autounsubscribe.md`).