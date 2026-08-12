# UDS Sandbox — RESULT: Not Supported

MAME's `emu.file` API does **not** support Unix domain sockets. All three
connection syntax variants fail with "No such file or directory".

## What Was Tested

| # | Syntax | Result |
|---|--------|--------|
| 1 | `socket./tmp/daggorath-uds-state` | FAILED: No such file or directory |
| 2 | `unix:/tmp/daggorath-uds-state` | FAILED: No such file or directory |
| 3 | `local:/tmp/daggorath-uds-state` | FAILED: No such file or directory |

Python successfully bound both UDS endpoints at `/tmp/daggorath-uds-state`
and `/tmp/daggorath-uds-action` before MAME launched. The socket files existed.
MAME simply doesn't recognize the UDS address format — it only parses
`socket.host:port` as a TCP address.

## Conclusion

**TCP sockets remain the best IPC choice.** The `emu.file("w")` and
`emu.file("r")` API with `socket.127.0.0.1:15000` syntax is the only
supported same-machine IPC path in MAME's embedded Lua engine.

Other IPC mechanisms considered and ruled out:
- **Pipes (stdin/stdout):** MAME owns its own stdin/stdout for the console
- **Shared memory:** No Lua API in MAME's embedded engine
- **File polling:** Too high-latency for frame-by-frame state reporting

TCP on localhost has negligible overhead at this scale (~154 bytes/frame
at 60 FPS = ~9 KB/s), even for RL training workloads.

## Quick Start

```bash
# Run from WSL (AF_UNIX requires Linux):
wsl bash -c "cd /mnt/c/Users/brand/Projects/Daggorath && python3 sandbox/uds/server.py"
```

## Files

| File | Purpose |
|------|---------|
| `server.py` | Python-side UDS server — binds two UDS endpoints, launches MAME |
| `client.lua` | Lua-side test — tries multiple connection syntaxes, runs functional test |
| `README.md` | This file |