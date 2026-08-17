# Read Atomicity

## Goal

Decide how to sample the 32-slot creature array without torn snapshots. A scan reads 32 slots (17 bytes each) one `read_u8` at a time; if the game moves or kills a creature between the first and last read, the observation is corrupted.

## Status

Deferred. No code yet — the experiment below is the TODO; these notes capture the thinking so far.

## TODO

Write a Lua `-autoboot_script` that, inside a `emu.add_machine_frame_notifier` callback, scans the 32-slot array **twice back-to-back** and logs any frame where the two scans differ. Run it during live play with creatures present and fighting, then inspect the log:

- **Zero differences** → the scan is atomic in practice; the 6809 does not advance while the callback runs, so a single pass is enough.
- **Any difference** → the CPU can advance mid-scan, and we need a guard (double-read-and-retry, or sample only at the frame boundary).

## Thoughts

The static evidence already points at "single pass is fine," but it isn't trusted enough yet to record as a decision:

- `emu.add_machine_frame_notifier` fires when an emulated **frame completes** (`docs/references/mame/lua-common.md`), so the callback runs at the frame boundary rather than mid-instruction.
- A blocking read inside the frame notifier freezes the whole emulator (`docs/decisions/ipc-hybrid.md`, `sandbox/fifo/`) — proof that Lua runs synchronously inside the emulation loop and the 6809 is not executing while the callback reads RAM.
- If that holds, a 32-slot scan is already one consistent snapshot, and a double-read check could never disagree.

The four options:

| Option | Read |
|--------|------|
| Accept the single-pass scan | Likely right — but confirm with the TODO first |
| Double-read consistency check | Redundant if the scan is already atomic; would always match |
| Frame-locked sampling | Already in place — the frame notifier is the lock |
| Defer | Chosen for now |

Whichever way the sandbox lands, the outcome goes into `docs/plans/creatures/plan.md` (the "Read atomicity" unknown) and a thread in `docs/plans/creatures/conversation.md`.
