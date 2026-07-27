# Daggorath Gym

A Gymnasium environment for training an RL agent to play **Dungeons of Daggorath** (1982, Tandy TRS-80 Color Computer) inside the MAME emulator. Requires MAME — runs on Linux, macOS, or Windows via WSL.

## Installation

1. Run the setup script to install MAME, ROMs, and configure hash files:
   ```
   bash setup.sh
   ```
2. Install the Python package:
   ```
   source .venv/bin/activate
   pip install -e .
   ```

Usage tips:
- **Headless training**: `-video none -sound none` (controlled via `config.py` or MameBridge)
- **With sound**: `-sound sdl` (best quality on WSLg); upgrade SDL2 with `sudo apt install --only-upgrade libsdl2-2.0-0`

## Known Issues

| # | Severity | Issue |
|---|---|---|
| 1 | P1 | Several observer.lua RAM addresses may not match actual memory map (see `emulation/docs/ram.md`) |
| 2 | P1 | No gym environment registration: `gymnasium.make('Daggorath-v0')` won't resolve |
| 3 | P2 | commands.lua action dispatch from Python not yet wired |
| 4 | P2 | WSLg audio has intermittent jitter on synthesized sounds (use `-sound sdl` + update SDL2) |

## Milestones

1. ✅ **Functional gym environment** — MAME boots the game, Lua reports state
2. 🔜 **Working socket communication** — Python ↔ Lua TCP bridge operational
3. **Future** — Train an RL agent

## Architecture

```
Python Gym Env (daggorath_gym/env.py)
    ↕ TCP sockets (127.0.0.1:15000 state, 15001 actions)
MAME emulator (coco3 driver)
    ↕
Lua scripts (emulation/*.lua) running inside MAME's embedded Lua engine
    ↕
Daggorath ROM (daggorath.zip — Shield Fix by Aaron Oliver)
    ↕
CoCo 3 system ROM (coco3.zip)
```

### Communication Flow

- **Python** starts TCP servers on ports 15000 + 15001, then launches MAME
- **MAME** boots with `-autoboot_script emulation/autoboot.lua`
- **autoboot.lua** opens two unidirectional emu.file sockets, registers frame notifier
- **observer.lua** reads RAM state every 60 frames → JSON over port 15000
- **Frame notifier** reads actions from port 15001 → dispatches to commands.lua
- **Python** receives game state, sends actions back

### Layout

| File | Role |
|------|------|
| `daggorath_gym/env.py` | DaggorathEnv (Gymnasium) |
| `daggorath_gym/bridge.py` | MameBridge — TCP servers + MAME lifecycle |
| `daggorath_gym/config.py` | MAME CLI flags |
| `daggorath_gym/paths.py` | Project path resolution |
| `emulation/autoboot.lua` | Entry point — emu.file sockets, frame notifier |
| `emulation/observer.lua` | RAM reader → JSON over TCP |
| `emulation/commands.lua` | Keystroke simulation |
| `emulation/paths.lua` | Socket config (host, ports) |
| `emulation/roms/` | coco3.zip, daggorath.zip |
| `emulation/docs/` | 6809 disassembly, RAM map, hardware ref |
| `sandbox/` | Validated TCP sandbox (see its README) |
| `setup.sh` | One-shot MAME + ROM + Lua installer |
| `pyproject.toml` | Pip package config |

## Reference Documentation

- **Code Disassembly**: [emulation/docs/code.md](emulation/docs/code.md)
- **RAM Memory Map**: [emulation/docs/ram.md](emulation/docs/ram.md)
- **CoCo Hardware**: [emulation/docs/hardware.md](emulation/docs/hardware.md)
- **Emulator Setup Notes**: [emulation/docs/setup.md](emulation/docs/setup.md)
- **Original Source**: https://www.computerarcheology.com/CoCo/Daggorath/
- **MAME Lua Scripting**: https://docs.mamedev.org/luascript/index.html
