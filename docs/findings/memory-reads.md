# Memory Reads

How to read Daggorath RAM from MAME's embedded Lua engine — the mechanics, the crash we hit, and how we debug it. For what each address *means*, see `ram-signals.md`.

<br>

<br>

## How do I read a byte of game RAM?

Acquire the main CPU's program address space, then call `read_u8`:

`manager.machine` → `.devices` → iterate with `pairs()` for `":maincpu"` → `.spaces` → iterate with `pairs()` for `"program"` → `read_u8(address)`.

Direct indexing `manager.machine.devices[":maincpu"]` segfaults in some MAME Lua contexts — always iterate with `pairs()`.

<br>

<br>

## When is reading safe?

Not on frame 1. A frame notifier fires as soon as the machine starts, but on that first frame the 6809 has executed almost no instructions and the GIME MMU (which maps the 64 KB CPU space onto the 512 KB of physical RAM) is still in its power-on state. `read_u8` through that mapping raises a native SIGSEGV — see the warning at the top of `ram-signals.md`.

Two guards make reads safe:

| Guard | Why |
|-------|-----|
| Return while `manager.machine.paused` | MAME can be paused during early frames |
| Gate on `displayFunction == 0xCE66` before sampling | Skips the demo loop; first true several hundred frames in |

<br>

<br>

## Does `manager.machine` always exist in a frame notifier?

Yes. The frame notifier is part of the machine's own emulation loop, so it cannot fire without a machine. A `not manager.machine` guard is dead code inside a frame notifier — it only matters at `startplugin` time, before the machine exists (which is why the command module acquires the keyboard lazily).

<br>

<br>

## How do I debug a segfault in MAME Lua?

- `pcall` catches only Lua errors. A C++ segfault kills the process outright, so wrapping reads in `pcall` does nothing.
- `print()` output is lost on SIGSEGV — stdio is not flushed. Write markers to a file and `flush()` after every one. The last line in the file is the crash site.
- Bracket the suspect: log before and after each `read_u8` to pinpoint the exact crashing call.
