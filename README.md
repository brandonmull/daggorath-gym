# Daggorath Gym

A Gymnasium environment for training an RL agent to play **Dungeons of Daggorath** (1982, Tandy TRS-80 Color Computer) inside the MAME emulator. Requires MAME — runs on Linux, macOS, or Windows via WSL.

## Installation

1. Install MAME 0.289 — built from source under WSL and installed to `/usr/local` (see `docs/references/mame/setup.md`).
2. Put the ROMs and hash files in place:
   - `emulation/roms/` — `coco3.zip`, `daggorath.zip`
   - `emulation/hash/` — `coco_cart.xml` (Shield Fix)
3. Install the Python package:
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
| 1 | P1 | `step()` is unusable — reward and termination/truncation raise `NotImplementedError` (no reward or termination plan yet) |
| 2 | P2 | No gym environment registration: `gymnasium.make('Daggorath-v0')` won't resolve |
| 3 | P2 | `setup.sh` is stale — installs MAME via apt paths; the project now builds from source into `/usr/local` |
| 4 | P2 | WSLg audio has intermittent jitter on synthesized sounds (use `-sound sdl` + update SDL2) |
| 5 | P3 | `reset(seed=...)` ignores the seed (no RNG wired yet) |

## Milestones

1. ✅ **Functional gym environment** — MAME boots the game, `reset()` returns a live observation (readiness-gated)
2. ✅ **Hybrid IPC** — state FIFO + command socket between Python and the Lua plugin
3. 🔜 **Trainable step loop** — reward + termination so `step()` returns meaningful values
4. **Future** — Train an RL agent

## Architecture

```
Python Gym Env (daggorath_gym/environment.py)
    ↕  state: named pipe FIFO (MAME → Python, tagged S/T/B records)
    ↕  command: TCP socket (Python → MAME, 1-byte command indices)
MAME emulator (coco3 driver) — "daggorath" Lua plugin
    emulation/plugins/daggorath/init.lua    entry point, opens both channels
    emulation/plugins/daggorath/state.lua   RAM sampling → FIFO
    emulation/plugins/daggorath/commands.lua command dispatch via natkeyboard
    ↕
Daggorath ROM (daggorath.zip — Shield Fix) + CoCo 3 ROM (coco3.zip)
```

### Communication Flow

- **Python** creates the state FIFO and listens on the command socket, then launches MAME with `-plugin daggorath`
- **init.lua** (plugin entry) opens the FIFO for writing and the command socket for reading, then hands both to the modules
- **state.lua** samples RAM every frame once the game is in live play, and writes tagged records to the FIFO
- **commands.lua** reads 1-byte command indices from the socket and posts the matching phrase via natkeyboard
- **Python** `recv()`s state records and `send()`s command indices

### Layout

| Path | Role |
|------|------|
| `daggorath_gym/environment.py` | DaggorathEnv (Gymnasium) |
| `daggorath_gym/emulator.py` | MameOperator — MAME lifecycle + hybrid IPC |
| `daggorath_gym/state.py` | State schema + deserialization |
| `daggorath_gym/commands.py` | Command phrase enumeration |
| `daggorath_gym/screen.py` | Command-area pixel decoding |
| `daggorath_gym/paths.py` | Project path resolution |
| `emulation/plugins/daggorath/init.lua` | Plugin entry — opens FIFO + command socket |
| `emulation/plugins/daggorath/state.lua` | RAM sampling → FIFO (readiness-gated) |
| `emulation/plugins/daggorath/commands.lua` | Command dispatch via natkeyboard |
| `emulation/plugins/daggorath/plugin.json` | Plugin manifest |
| `emulation/roms/` | coco3.zip, daggorath.zip |
| `emulation/hash/` | MAME hash files (Shield Fix) |
| `tests/` | Pytest suite (unit + integration) |
| `docs/plans/`, `docs/reviews/`, `docs/decisions/`, `docs/findings/` | Design, review, decision, and findings docs |
| `docs/references/` | 6809 disassembly, RAM map, command grammar, hardware ref |
| `sandbox/` | Validated experiments (see its README) |
| `setup.sh` | One-shot installer (stale — see Known Issues) |
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

## Reference Documentation

Project docs follow a four-phase pipeline:

| Phase | Directory | Description |
|-------|-----------|-------------|
| **Plans** | `docs/plans/` | Pre-build design specifications |
| **Reviews** | `docs/reviews/` | Post-build critique — observations, deferred items |
| **Decisions** | `docs/decisions/` | Implemented changes |
| **Findings** | `docs/findings/` | Hard-won discoveries (IPC transport, RAM signals) |

External source material:

- **Code Disassembly**: [docs/references/game/code.md](docs/references/game/code.md)
- **RAM Memory Map**: [docs/references/game/ram.md](docs/references/game/ram.md)
- **Command Grammar**: [docs/references/game/commands.md](docs/references/game/commands.md)
- **CoCo Hardware**: [docs/references/mame/hardware.md](docs/references/mame/hardware.md)
- **Emulator Setup Notes**: [docs/references/mame/setup.md](docs/references/mame/setup.md)
- **Original Source**: https://www.computerarcheology.com/CoCo/Daggorath/
- **MAME Lua Scripting**: https://docs.mamedev.org/luascript/index.html