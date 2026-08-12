# FIFO Sandbox — Result: Hybrid Viable

Standard Lua `io.open()` on named pipes works for **writing** (state channel) but
not for **reading** (command channel) — `io.read()` blocks, freezing the emulator.

## Test Results

| Channel | API | Result |
|---------|-----|--------|
| State (Lua → Python) | `io.open(fifo, "w")` | ✅ Stable at 60 Hz, 208+ frames received |
| Command (Python → Lua) | `io.open(fifo, "r")` | ❌ `read("*l")` blocks the frame notifier, freezing MAME |

## Recommended Architecture: Hybrid FIFO + emu.file

The write path works — `io.open("w")` on a FIFO returns immediately from
`file:write()` and never blocks the frame notifier. The read path needs
a non-blocking API, which `io` doesn't provide but `emu.file("r")` does.

| Channel | Transport | Why |
|---------|-----------|-----|
| State (high throughput, ~154 bytes/frame at 60 Hz) | FIFO via `io.open("w")` | Bypasses `emu.file` socket layer completely; no emulator corruption risk |
| Command (low throughput, ~1 byte/frame) | `emu.file("r")` socket | Documented as stable, naturally non-blocking |

## The Freeze Problem (Read Side)

When Lua calls `io.open(fifo, "r"):read("*l")` inside the frame notifier and
no data is available, the kernel blocks the Lua thread — which blocks the
frame notifier — which blocks the entire emulation loop. The emulator freezes
until Python writes something.

`emu.file("r"):read(n)` doesn't have this problem — it returns an empty string
when no data is available, allowing the frame notifier to continue immediately.

## Quick Start

```bash
# Must run from WSL:
wsl bash -c "cd /mnt/c/Users/brand/Projects/Daggorath && python3 sandbox/fifo/server.py"
```

## Files

| File | Purpose |
|------|---------|
| `server.py` | Python orchestrator — creates FIFOs, launches MAME, reads state, sends commands |
| `client.lua` | Lua test — opens state FIFO via `io.open("w")`, sends every frame |
| `README.md` | This file |