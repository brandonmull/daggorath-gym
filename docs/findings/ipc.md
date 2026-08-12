# IPC Transport

Evaluation of inter-process communication methods between Python and MAME's embedded Lua engine. The goal is a reliable frame-by-frame channel for RL training — state flowing from MAME to Python, commands flowing back.

## Summary

| Channel | Transport | Lua API | Why |
|---------|-----------|---------|-----|
| State (MAME → Python, ~154 bytes/frame at 60 Hz) | Named pipe (FIFO) | `io.open("w")` | Bypasses `emu.file` socket layer; stable at 60 Hz |
| Command (Python → MAME, ~1 byte/frame) | TCP socket | `emu.file("r")` | Non-blocking reads; documented as stable |

## What We Tested

### Unix domain sockets via `emu.file`

`emu.file` only parses the `socket.host:port` TCP format. All UDS syntax variants fail: `socket./path`, `unix:/path`, `local:/path` — all return "No such file or directory" even when the socket file exists. MAME's socket implementation is TCP-only.

**Sandbox:** `sandbox/uds/` — negative result.

### Named pipes (FIFOs) via `io.open`

Standard Lua `io.open()` on a FIFO works but with one caveat:

| Direction | API | Result |
|-----------|-----|--------|
| Write (Lua → Python) | `io.open(fifo, "w"):write()` | ✅ Stable at 60 Hz; 208+ frames received with no corruption |
| Read (Python → Lua) | `io.open(fifo, "r"):read("*l")` | ❌ Blocks the frame notifier when no data is available, freezing the emulator |

The write path succeeds because a write returns immediately when a reader exists on the other end. The read path fails because Lua's `io` library has no non-blocking read — `read("*l")` blocks the calling thread (the frame notifier) which blocks the entire emulation loop.

**Sandbox:** `sandbox/fifo/` — write path validated, read path blocked by design.

### TCP via `emu.file`

The existing transport. Prior sandboxes documented fragility:
- `emu.file("rw")` corrupts the emulator (black screen, looping audio) — a bidirectional socket breaks the emulation loop
- `emu.file("w")` with no connected client crashes MAME
- Two separate unidirectional sockets (`"w"` + `"r"`) are the required workaround

## Why the Hybrid

The state channel carries the bulk of the traffic (raw bytes every frame during training) and `emu.file("w")` has known reliability problems under load. Moving it to `io.open("w")` on a FIFO eliminates the `emu.file` socket layer from the high-throughput path.

The command channel carries ~1 byte at most per step and needs non-blocking reads to avoid freezing the emulator when no command is pending. `emu.file("r")` provides this naturally — `read(n)` returns an empty string when nothing is available, allowing the frame notifier to continue immediately.

Python opens both the FIFO and the TCP socket before launching MAME, so Lua's write and read sides never block during normal operation.