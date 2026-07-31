# Lua Module Loading

## Goal

Verify that `require("modulename")` works in MAME's embedded Lua environment when the autoboot script and sibling modules share a directory. If `require()` fails, we need a fallback to `dofile()`.

## Background

The current `autoboot.lua` uses:
```lua
local state = require("state")
local commands = require("commands")
```

This assumes MAME adds the `-autoboot_script` directory to `package.path` automatically. The old `autoboot.lua` was monolithic (no external requires), so this is untested.

## Approach

### Test 1: `require()` a sibling module

Create a minimal module `sandbox/lua-module-loading/hello.lua`:
```lua
return { loaded = true }
```

Create an autoboot script that tries `require("hello")` and reports the result over the state socket (port 15000). The Python server checks whether the module loaded successfully.

### Test 2: Verify `package.path`

The autoboot script prints `package.path` to see what directories MAME configured. This tells us whether the script's directory was added automatically, or if we need to modify `package.path` manually.

### Test 3: `dofile()` fallback

If `require()` fails, test `dofile()` with an absolute path derived from the autoboot script's location. MAME might pass the script path via an environment variable or argument — investigate.

## Success Criteria

- [x] `require("hello")` succeeds or fails (documented) — fails by default
- [x] `package.path` contents logged and understood
- [x] Fallback mechanism identified if `require()` fails — `dofile()` works, `os.getenv()` + prepend also works
- [x] Decision: use `require()` with `os.getenv()` to prepend the module directory to `package.path`

## Results

| Approach | Result |
|----------|--------|
| `arg[0]` | ❌ `arg` global doesn't exist in MAME's Lua |
| Varargs (`...`) | ❌ MAME passes zero arguments to autoboot scripts |
| `-pluginspath` | ❌ Doesn't affect Lua's `package.path` |
| `os.getenv("AUTOBOOT_DIR")` | ✅ Environment variables pass through from Python |
| `require()` after prepending path | ✅ Works once the directory is in `package.path` |
| `dofile("/abs/path")` | ✅ Always works |

### Production Fix

In `emulation/autoboot.lua`, add before any `require()` calls:

```lua
local emu_dir = os.getenv("DAGGORATH_EMU_DIR")
if emu_dir then
    package.path = emu_dir .. "/?.lua;" .. package.path
end
```

`bridge.py` sets `DAGGORATH_EMU_DIR` in the MAME subprocess environment.

## Notes

- MAME uses Lua 5.3 (embedded, not system Lua)
- `-autoboot_script` takes an absolute path — we may need to derive the directory from it
- If `package.path` doesn't include the script directory, we can prepend it in autoboot before calling `require()`
- The sandbox server can use the existing `tcp-sockets` pattern (bind → launch MAME → accept → validate)