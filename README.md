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
- **Headless training**: `-video none -sound none` (pass `MameConfig(window=False, sound="none")` to MameOperator)
- **With sound**: `-sound sdl` (best quality on WSLg); upgrade SDL2 with `sudo apt install --only-upgrade libsdl2-2.0-0`

## Known Issues

| # | Severity | Issue |
|---|---|---|
| 1 | P1 | Readiness detection not yet implemented — reset() returns first frame (see `docs/reviews/env.md`) |
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
    ↕ TCP sockets (127.0.0.1:15000 state, 15001 commands)
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
- **state.lua** reads RAM state every frame → raw bytes over port 15000
- **Frame notifier** reads command indices from port 15001 → dispatches to commands.lua
- **Python** receives game state, sends command indices back

### Layout

| File | Role |
|------|------|
| `daggorath_gym/environment.py` | DaggorathEnv (Gymnasium) |
| `daggorath_gym/emulator.py` | MameOperator — TCP servers + MAME lifecycle |
| `daggorath_gym/state.py` | Game state deserialization |
| `daggorath_gym/commands.py` | Command phrase enumeration |
| `daggorath_gym/paths.py` | Project path resolution |
| `emulation/autoboot.lua` | Entry point — emu.file sockets, frame notifier |
| `emulation/state.lua` | RAM reader → raw bytes over TCP |
| `emulation/commands.lua` | Command phrase dispatch via natkeyboard |
| `emulation/paths.lua` | Socket config (host, ports) |
| `emulation/roms/` | coco3.zip, daggorath.zip |
| `docs/references/` | 6809 disassembly, RAM map, command grammar, hardware ref |
| `sandbox/` | Validated TCP sandbox (see its README) |
| `setup.sh` | One-shot MAME + ROM + Lua installer |
| `pyproject.toml` | Pip package config |

## Coding Conventions

**The game manual is the authority.** Module-level constant names come from the game manual or ROM disassembly when available. When neither supplies a term, use the plan docs.

**Constants use a two-word body with a domain prefix.** The first word scopes to a domain (objects, commands); the second word matches the source material. This keeps related constants visually grouped and prevents ambiguous bare-name collisions.

**Don't extract a subset into a separate constant when the superset already exists.** A value derivable from an existing constant lives in the function that uses it. Duplicating data in two constants means two places to keep in sync.

**Prefer tuples for simple data, but use a named type when position alone isn't clear.** A tuple works when each element's role is obvious from context. When the reader would need to remember which position means what, a dataclass or named tuple reduces cognitive load.

**`action` is Gymnasium's word, `command` is ours.** `action` is the integer an agent chooses at each step — it appears only in `action_space` and `step(action)`. Our code never uses `action` as a name for our own components. The channel on port 15001 is the **command** channel; what travels across it are **command indices**. Variables and constants use `command`, never `action`.

**`socket`, never `sock`.** TCP socket variable names use the full word.

**Multi-word variable names follow adjective-then-noun order.** `state_socket`, not `socket_state`. `command_socket`, not `socket_command`.

**Naming conventions span both sides of the wire.** Lua and Python constants that represent the same concept must use the same name, differing only in Python's `_` prefix (Lua uses `local` for privacy).

**`emulation/observer.lua` is legacy.** `state.lua` is its replacement. `observer.lua` must not exist.

## Reference Documentation

- **Code Disassembly**: [docs/references/game/code.md](docs/references/game/code.md)
- **RAM Memory Map**: [docs/references/game/ram.md](docs/references/game/ram.md)
- **Command Grammar**: [docs/references/game/commands.md](docs/references/game/commands.md)
- **CoCo Hardware**: [docs/references/mame/hardware.md](docs/references/mame/hardware.md)
- **Emulator Setup Notes**: [docs/references/mame/setup.md](docs/references/mame/setup.md)
- **Original Source**: https://www.computerarcheology.com/CoCo/Daggorath/
- **MAME Lua Scripting**: https://docs.mamedev.org/luascript/index.html