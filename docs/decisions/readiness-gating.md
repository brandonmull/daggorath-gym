# Readiness Gating

_13 Aug 2026_

## Decision

State sampling in `state.lua` is gated on game readiness. The plugin reads
`displayFunction` (0x02B2–0x02B3) before sampling anything and returns early
unless it equals `0xCE66` (live play). It also returns early while
`manager.machine.paused` is true.

## Why

Reading RAM on frame 1 segfaults MAME: the 6809 has not yet initialized the
GIME MMU, so `read_u8` through the power-on mapping raises a native SIGSEGV
(see `docs/findings/memory-reads.md`). Gating on `displayFunction` also skips
the demo loop, where the command area does not exist.

The previous gate used `gameMode` (0x0277), which is a state field, not a
readiness signal — it cannot distinguish the demo loop from live play.
