# Decision: Save Notifier Subscriptions (GC Auto-Unsubscription)

_8 Aug 2026_

## Problem

`emu.add_machine_*_notifier()` callbacks stopped firing after machine resets.
Frame notifiers, reset notifiers, and stop notifiers all died after the first
machine reset, including the demo→live transition in Daggorath.

This affected:
- Production `state.lua` and `commands.lua` (plugin modules)
- All sandbox experiments (command-readiness, plugin-lifecycle)
- Every attempt to use `emu.add_machine_frame_notifier`

## Root Cause

MAME's Lua notifier API returns a `notifier_subscription` object. If the return
value is discarded (not saved to a variable), Lua's garbage collector eventually
collects the subscription object, which triggers an automatic unsubscribe.

```lua
-- BROKEN: subscription return value discarded → GC auto-unsubscribes
emu.add_machine_frame_notifier(_onFrame)

-- FIXED: subscription saved to module-local variable → survives GC
local frameSubscription = emu.add_machine_frame_notifier(_onFrame)
```

This was confirmed experimentally:
- `emu.register_frame()` (deprecated) always worked because it may not use subscription objects
- `emu.add_machine_frame_notifier()` with saved subscription survives all resets
- `emu.add_machine_reset_notifier()` with saved subscription fires on init, hard_reset, AND soft_reset
- `emu.add_machine_stop_notifier()` with saved subscription fires on exit AND hard_reset teardown

## Resolution

All notifier registrations in Daggorath Gym must save the return value in a
module-local Lua variable. Three notifiers are used in the production architecture:

| Notifier | Variable | When it fires |
|----------|----------|--------------|
| `add_machine_reset_notifier` | `resetSubscription` | Machine init, hard_reset, soft_reset |
| `add_machine_stop_notifier` | `stopSubscription` | Machine exit, hard_reset teardown |
| `add_machine_frame_notifier` | `frameSubscription` | Every frame (gated by `machine.paused`) |

## Notifiers That Cannot Be Used

- `add_machine_pause_notifier` — UI-driven only (P key in MAME), inaccessible in natkeyboard mode
- `add_machine_resume_notifier` — same as pause
- `add_machine_start_notifier` — does not exist; `startplugin()` is the equivalent

## Command-Readiness Result

The game becomes command-ready at **frame 725** (~12s after cold boot, ~7s after keyboard priming):
- Frame 300: auto-prime (two `\r` posted via natkeyboard)
- Frame 313: gameMode flips from 0xFF (demo) to 0x00 (live)
- Frame 725: displayFunction reaches 0xCE66 (normal game screen)