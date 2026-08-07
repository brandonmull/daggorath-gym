# Emulator Setup Notes

Reference docs: [code.md](code.md) · [ram.md](ram.md) · [hardware.md](hardware.md)

# Lua Dependencies & the Rockspec Problem

## What We Need

These are the Lua modules required by the MAME autoboot/observer scripts:

- **luasocket** >= 3.0 — TCP socket communication (observer -> Python gym)
- **luafilesystem** >= 1.8.0 — Filesystem utilities

## Why LuaRocks / a Rockspec Approach Doesn't Work with MAME

MAME ships its own embedded Lua interpreter. When you run:

```
mame coco3 daggorath -autoboot_script emu/autoboot.lua
```

MAME does **not** consult the system Lua installation, `LUA_PATH`, or any locally installed LuaRocks packages. It runs scripts through its own bundled Lua engine, which only resolves modules from:

- MAME's plugin directory: `/usr/share/games/mame/plugins/`

This means:

1. Even if `setup.sh` successfully installs `luasocket` and `luafilesystem` via `luarocks` into `$WORKSPACE/env/`, MAME's embedded Lua will never find or load those `.so` files.

2. The rockspec (`emu/daggorath.rockspec`) only declares dependencies; its `modules` table is empty (`modules = {}`), so it doesn't package the project's own `.lua` files either.

3. `setup.sh` works around this by copying the `.lua` scripts directly into MAME's plugin directory, but this approach still cannot load compiled C Lua modules (like `luasocket.so`) inside MAME.

## Workarounds & Alternatives

- Use MAME's built-in Lua socket library (if available in the embedded build)
- Use a different IPC mechanism (pipes, stdout parsing, shared memory) that doesn't require external Lua C modules
- Place compiled `.so` files directly in MAME's plugin directory
- Run the socket client outside MAME (Python -> Lua bridge via MAME's console/network interface)

# Future Idea: Lite MAME Build for Daggorath-Only

Once the proof-of-concept is working with a full MAME installation, consider building a stripped-down MAME binary compiled only for the CoCo 3 driver and daggorath cartridge.

## Benefits

- Smaller binary size (MAME ships ~1000+ drivers; we only need `coco3`)
- Faster startup / compile time
- Fewer dependencies (no need for audio/video backends beyond what's needed for headless RL training)
- Easier to containerize (smaller image, fewer packages)
- Can potentially bundle the binary directly in the repo instead of requiring system MAME installation

## MAME Build Flags to Explore

```
SUBTARGET=coco3  -- build only the coco3 driver
SOURCES=src/mame/trs/coco3.cpp,src/mame/trs/coco12.cpp ...
make TARGET=mame SUBTARGET=coco3
```

## Headless RL Training Considerations

- Video: `-video none` or `-video soft`
- Audio: `-sound none` (already set in `config.py`)
- No need for input mapping plugins (keyboard handled via Lua input API)

*This is a future optimization — not needed for the initial PoC.*