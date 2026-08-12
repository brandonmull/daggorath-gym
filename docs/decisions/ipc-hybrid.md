# Hybrid IPC Architecture

_12 Aug 2026_

## Decision

State channel uses a named pipe (FIFO) via Lua `io.open("w")`; command channel uses TCP via `emu.file("r")`. This replaces the previous two-TCP-socket architecture.

## Why

MAME's `emu.file` socket layer has documented fragility under sustained write load:
- `emu.file("rw")` corrupts the emulator (black screen, looping audio)
- `emu.file("w")` with no connected client crashes MAME
- Two separate unidirectional sockets are a workaround, not a fix — the write path remains fragile

The state channel carries the bulk of the traffic (~154 bytes per frame at 60 Hz = ~9 KB/s) and needs a reliable write path. Standard Lua `io.open("w")` on a FIFO bypasses `emu.file` entirely — `file:write()` is a standard Lua library call that MAME's plugin-lifecycle sandbox proved stable for sustained logging.

The command channel carries ~1 byte per step at most and needs **non-blocking reads** — the frame notifier must return immediately when no command is available. Standard Lua `io` has no non-blocking read capability; `io.open("r"):read("*l")` blocks the frame notifier, freezing the emulator. `emu.file("r"):read(1)` returns an empty string when no data is available, allowing the frame notifier to continue.

## What Was Evaluated

| Method | Write (Lua → Python) | Read (Python → Lua) | Sandbox |
|--------|---------------------|--------------------|---------|
| TCP via `emu.file` | Fragile under load | Stable, non-blocking | `sandbox/tcp-sockets/` |
| UDS via `emu.file` | Not supported | Not supported | `sandbox/uds/` |
| FIFO via `io.open` | Stable at 60 Hz, 208+ frames | Blocks frame notifier, freezes MAME | `sandbox/fifo/` |

See `docs/findings/ipc.md` for the full evaluation.

## What Changed

### Lua side

- `state.lua`: `_socket` → `_stateFile`; writes via `_stateFile:write()` instead of `_socket:write()`
- `init.lua`: opens state FIFO with `io.open(path, "w")` instead of `emu.file("w")`
- `commands.lua`: unchanged (still uses `emu.file("r")`)

### Python side

- `emulator.py`: state channel changed from `socket.recv()` to `os.read()` on a FIFO; FIFO created with `os.mkfifo()` and opened `O_RDWR` before MAME launch
- `SocketConfig` → `IpcConfig`; `state_port` → `state_fifo_path`