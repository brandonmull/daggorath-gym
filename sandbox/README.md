# Sandbox

Short, focused experiments to validate design assumptions before they reach the main codebase. Each sub-folder targets one open question.

| Folder | Goal | Status |
|--------|------|--------|
| `tcp-sockets/` | Validate MAME `emu.file` socket communication | ✅ Proven |
| `typing-timing/` | Find minimum viable KEY_HOLD, CHAR_GAP, POST_ENTER_DELAY | Planned |
| `command-buffering/` | Determine whether a command buffer is needed during TYPING | Planned |
| `lua-module-loading/` | Verify `require()` works in MAME's Lua (vs `dofile()` fallback) | Planned |
| `command-grammar/` | Verify the command space is fully discrete and correctly counted | Planned |

## Running a sandbox

Each sub-folder follows the same pattern as `tcp-sockets`:
- A Lua script that runs under MAME's `-autoboot_script`
- A Python server that orchestrates: binds ports, launches MAME, validates results
- A README with goal, approach, and success criteria

```bash
env/bin/python3 sandbox/<name>/server.py