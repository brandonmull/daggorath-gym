# Sandbox

Short, focused experiments to validate design assumptions before they reach the main codebase. Each sub-folder targets one open question.

| Folder | Goal | Status |
|--------|------|--------|
| `tcp-sockets/` | Validate MAME `emu.file` socket communication | ✅ Proven |
| `typing-timing/` | Can we send typed commands to the in-game console? | ✅ Proven |
| `command-buffering/` | How fast can we send commands? Do we need rate management? | ✅ Proven |
| `lua-module-loading/` | Verify `require()` works in MAME's Lua (vs `dofile()` fallback) | ✅ Proven |
| `read-atomicity/` | Is the 32-slot creature scan torn? (frame-notifier timing) | ⏳ Deferred |

## Running a sandbox

Each sub-folder follows the same pattern as `tcp-sockets`:
- A Lua script that runs under MAME's `-autoboot_script`
- A Python server that orchestrates: binds ports, launches MAME, validates results
- A README with goal, approach, and success criteria

```bash
env/bin/python3 sandbox/<name>/server.py