# MAME Lua API Reference

_Source: [MAME Documentation 0.289 — Lua Common Types and Globals](https://docs.mamedev.org/luascript/ref-common.html)_

## Emulator Interface (`emu`)

The emulator interface `emu` provides access to core functionality. Many classes are also available as properties of the emulator interface.

### Methods

| Method | Description |
|--------|-------------|
| `emu.wait(duration, ...)` | Yields for the specified duration in emulated time. Returns `false` immediately if a saved state is loaded or the emulation session ends. **Unreliable in this MAME build** — use frame counting for delays. |
| `emu.wait_next_update(...)` | Yields until the next video/UI update. |
| `emu.wait_next_frame(...)` | Yields until the next emulated frame completes. |
| `emu.add_machine_reset_notifier(callback)` | Add a callback to receive notifications when the emulated system is **reset**. Returns a notifier subscription. |
| `emu.add_machine_stop_notifier(callback)` | Add a callback to receive notifications when the emulated system is **stopped**. Returns a notifier subscription. |
| `emu.add_machine_pause_notifier(callback)` | Add a callback to receive notifications when the emulated system is **paused**. Returns a notifier subscription. |
| `emu.add_machine_resume_notifier(callback)` | Add a callback to receive notifications when the emulated system is **resumed** after being paused. Returns a notifier subscription. |
| `emu.add_machine_frame_notifier(callback)` | Add a callback to receive notifications when an emulated **frame completes**. Returns a notifier subscription. **This is the preferred API** — `emu.register_frame` is deprecated. |
| `emu.add_machine_pre_save_notifier(callback)` | Add a callback to receive notification **before** the emulated system state is saved. Returns a notifier subscription. |
| `emu.add_machine_post_load_notifier(callback)` | Add a callback to receive notification **after** the emulated system is restored to a previously saved state. Returns a notifier subscription. |
| `emu.print_error(message)` | Print an error message. |
| `emu.print_warning(message)` | Print a warning message. |
| `emu.print_info(message)` | Print an informational message. |
| `emu.print_verbose(message)` | Print a verbose diagnostic message (disabled by default). |
| `emu.print_debug(message)` | Print a debug message (only enabled for debug builds by default). |
| `emu.lang_translate([context], message)` | Look up a message with optional context in the current localised message catalog. |
| `emu.subst_env(string)` | Substitute environment variables in a string. The syntax is dependent on the host operating system. |

### Key Lifecycle Notifiers for This Project

Three notifiers are critical for surviving the CoCo's demo→live transition:

| Notifier | When it fires | What to do |
|----------|--------------|------------|
| `emu.add_machine_reset_notifier` | CoCo soft-resets (including demo→live transition) | Re-acquire `memory` handle, re-register frame notifier |
| `emu.add_machine_stop_notifier` | Emulation stops | Flush buffers, close file handles |
| `emu.add_machine_frame_notifier` | Every emulated frame | Read RAM signals, accumulate in buffer |

**Why this matters:** The demo→live transition triggers a CoCo soft-reset, which invalidates the `memory` handle obtained via `cpu.spaces["program"]`. Using only `add_machine_frame_notifier` without re-acquiring on reset causes an ACCESS VIOLATION crash. The fix is to use `add_machine_reset_notifier` to detect the reset and re-acquire the memory space.

## Notifier Subscriptions

All `add_machine_*_notifier` functions return a notifier subscription object (`luascript-ref-notifiersub`). To unsubscribe, keep the return value and call the appropriate release method (documented in [Lua Core Classes](https://docs.mamedev.org/luascript/ref-core.html)).

## Containers

Many properties yield container wrappers. Container wrappers are cheap to create and provide an interface similar to a read-only table.

| Operation | Description |
|-----------|-------------|
| `#c` | Get the number of items in the container. |
| `c[k]` | Returns the item corresponding to key `k`, or `nil`. |
| `pairs(c)` | Iterate over container by key and value. |
| `ipairs(c)` | Iterate over container by index and value. |
| `c:empty()` | Returns `true` if no items in container. |
| `c:get(k)` | Returns item for key `k`, or `nil`. |
| `c:at(i)` | Returns value at 1-based index `i`, or `nil`. |
| `c:find(v)` | Returns key for item `v`, or `nil`. |
| `c:index_of(v)` | Returns 1-based index for item `v`, or `nil`. |