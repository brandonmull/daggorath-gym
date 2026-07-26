# Daggorath Gym

A Gymnasium environment for training an RL agent to play **Dungeons of Daggorath** (1982, Tandy TRS-80 Color Computer). The game runs inside MAME emulator, and the agent receives game state by reading RAM via Lua scripts and sends keystroke commands back.

## Milestones

1. ✅ **Functional gym environment** — MAME boots the game, Lua reports state
2. 🔜 **Working socket communication** — Python ↔ Lua TCP bridge operational
3. **Future** — Train an RL agent

## Architecture

```
Python Gym Env (gym/main.py)
    ↕ TCP socket (intended: 127.0.0.1:15000)
MAME emulator (coco3 driver)
    ↕
Lua scripts (emu/*.lua) running inside MAME's embedded Lua engine
    ↕
Daggorath ROM (daggorath.zip — Shield Fix by Aaron Oliver)
    ↕
CoCo 3 system ROM (coco3.zip)
```

### Communication Flow (intended)

- **Python** starts a TCP server
- **MAME** boots with `-autoboot_script emu/autoboot.lua`
- **autoboot.lua** connects TCP client to Python, registers periodic observer
- **observer.lua** reads RAM state (heart rate, player XY/HP/stamina, game state) every 1s → JSON
- **commands.lua** simulates keystrokes (arrows + ATTACK/MOVE/LOOK/CLIMB/USE/INCANT)
- **Python** receives game state, sends actions back

## Directory Structure

```
daggorath-gym/
├── gym/                    # Python Gymnasium environment
│   ├── main.py             # DaggorathEnv(gym.Env)
│   ├── config.py           # MAME CLI invocation builder
│   ├── funcs.py            # TCP socket helpers
│   ├── paths.py            # Path resolution
│   └── requirements.txt    # gymnasium, numpy
├── emu/                    # Lua scripts (run inside MAME)
│   ├── autoboot.lua        # Entry point, TCP client, observer registration
│   ├── observer.lua        # RAM state reader → JSON over TCP
│   ├── commands.lua        # Input simulation via MAME Lua API
│   ├── paths.lua           # Centralized config (socket host/port, MAME paths)
│   ├── setup_hash.py       # Copies MAME hash files to local dir
│   ├── hash/coco_cart.xml  # MAME software list (includes Shield Fix)
│   ├── roms/coco3.zip      # CoCo 3 system ROM
│   ├── roms/daggorath.zip  # Daggorath ROM (Shield Fix)
│   └── docs/               # Reference documentation
│       ├── code.md         # Full 6809 disassembly with commentary
│       ├── ram.md          # RAM memory map (100+ addresses, structures)
│       ├── hardware.md     # CoCo hardware reference (PIA, SAM, vectors)
│       └── setup.md        # Emulator architecture notes, Lua deps, build plans
├── test_gym.py             # Integration test
├── test_socket.py          # Standalone socket server/client test
├── verify_rom.py           # ROM CRC32/SHA1 validation
├── setup.sh                # WSL/Linux host MAME+ROM+Lua installer
├── pyproject.toml          # Python package config
└── requirements.txt        # Delegates to gym/requirements.txt
```

## Installation

1. Install MAME with the Dungeons of Daggorath ROM (see `setup.sh` for WSL/Linux)
2. Install the Python package:
   ```
   pip install -e .
   ```
3. Set up the local hash files:
   ```
   python emu/setup_hash.py
   ```

## Known Issues (PoC Blockers)

| # | Severity | Issue |
|---|---|---|
| 1 | **P0** | Port mismatch: Lua connects to `127.0.0.1:15000`, Python listens on `127.0.0.1:8080` |
| 2 | **P0** | DaggorathEnv is mostly stubs: `get_observation()` returns `[0]`, `send_action()` is `pass` |
| 3 | **P0** | funcs.py is send-only — no `recv_message()` to read JSON from Lua |
| 4 | **P0** | No gym environment registration: `gym.make('Daggorath-v0')` won't resolve |
| 5 | P1 | Several observer.lua RAM addresses may not match actual memory map (see `emu/docs/ram.md`) |
| 6 | P1 | observer.lua redundantly reconnects on an already-connected socket |

## Reference Documentation

- **Code Disassembly**: [emu/docs/code.md](emu/docs/code.md)
- **RAM Memory Map**: [emu/docs/ram.md](emu/docs/ram.md)
- **CoCo Hardware**: [emu/docs/hardware.md](emu/docs/hardware.md)
- **Emulator Setup Notes**: [emu/docs/setup.md](emu/docs/setup.md)
- **Original Source**: https://www.computerarcheology.com/CoCo/Daggorath/
- **MAME Lua Scripting**: https://docs.mamedev.org/luascript/index.html

## Environment Notes

- **Requires MAME** — runs on any platform that supports MAME (Linux, macOS, Windows via WSL)
- **Headless training**: Use `-video none -sound none` (already in config.py) — no display needed
- **Setup**: Run `setup.sh` for automated MAME + ROM + Lua installation (Linux/WSL)
