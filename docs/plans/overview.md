# Project Overview

_A newcomer-friendly explanation of what we're building and why._

---

## What Is This Project?

We're training an AI to play **Dungeons of Daggorath**, a 1982 text-adventure / dungeon-crawler game for the TRS-80 Color Computer. The game runs inside **MAME**, an emulator that simulates the original hardware — including a Motorola 6809 CPU running at ~0.89 MHz (yes, megahertz, singular).

MAME lets us attach **Lua scripts** that run alongside the emulated machine. These scripts can read the emulated RAM (to see what's happening in the game) and inject keystrokes (to control the game). On the other side, a **Python** program talks to MAME over TCP sockets and presents everything as a standard **Gymnasium** environment (the same interface used by OpenAI Gym for reinforcement learning).

```
┌─────────────────────────────────────────────────────────────┐
│                      Python (our code)                      │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────┐  │
│  │ bridge.py │    │ state.py    │    │     env.py        │  │
│  │ TCP comms │    │ deserialize  │    │ Gymnasium Env     │  │
│  │           │    │ game state   │    │ step() / reset()  │  │
│  └─────┬─────┘    └──────▲───────┘    └───────────────────┘  │
│        │                 │                                    │
│        │ raw bytes       │ typed attributes                  │
│        │                 │ (obs.heart_rate, obs.player_x...) │
├────────┼─────────────────┼────────────────────────────────────┤
│        │    TCP sockets  │                                    │
│        │    (localhost)  │                                    │
├────────┼─────────────────┼────────────────────────────────────┤
│        ▼                 │                                    │
│  ┌──────────────────────────────┐                             │
│  │         MAME (emulator)      │                             │
│  │  ┌────────────────────────┐  │                             │
│  │  │   Lua scripts           │  │                             │
│  │  │   - autoboot.lua        │  │                             │
│  │  │   - state.lua           │  │                             │
│  │  │   - commands.lua        │  │                             │
│  │  └────────────────────────┘  │                             │
│  │  ┌────────────────────────┐  │                             │
│  │  │   Emulated CoCo 3       │  │                             │
│  │  │   - 6809 CPU            │  │                             │
│  │  │   - 16-64K RAM          │  │                             │
│  │  │   - Daggorath cartridge │  │                             │
│  │  └────────────────────────┘  │                             │
│  └──────────────────────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Choices

- **Two unidirectional TCP sockets** — port 15000 (MAME → Python, game state) and port 15001 (Python → MAME, game commands). Using MAME's built-in `emu.file` socket API. Proven in the `sandbox/` validation.
- **No external Lua dependencies** — MAME ships its own embedded Lua interpreter. LuaRocks packages cannot be loaded. All Lua scripts use only MAME's built-in APIs.
- **Raw byte wire format** — no JSON on either socket. Compact, fast, and avoids serialization overhead on the emulated CPU.
- **Flyweight pattern** — shared schema objects on both sides, per-frame/per-command value objects. Schema defines the contract once; instances are light.

## Naming Conventions

### All names come from the plan docs — never improvise.

The plan documents name every constant, function, class, and variable. Use those exact names. If you think a name could be shorter or different, ask first.

### Prefer fully-worded terminology.

Domain terms have specific multi-word names defined in the plans ("command phrase", "command word", "command index", "command socket"). Never drop the qualifying word — a "phrase" on its own is ambiguous, "command phrase" is precise. This applies everywhere: constant names, function names, local variables, docstrings, comments. If the plan calls it `_build_command_phrases`, don't shorten it to `_build_phrases`. If a comment describes "62 phrases", write "62 command phrases". The qualifier is not redundant — it distinguishes our domain concept from generic programming terms.

### Constants use UPPER_SNAKE_CASE on both sides.

Lua uses `local` for privacy, Python uses a `_` prefix. The root names are identical: `COMMAND_WORDS` on both sides, `_COMMAND_WORDS` in Python. Every constant that exists on one side must exist on the other with the same name (modulo the `_` prefix for Python privacy).

### `socket`, never `sock`.

### Multi-word names follow adjective-then-noun order.

`stateSocket`, not `socketState`. `commandPort`, not `portCommand`.

## Documentation Structure

The project uses a three-phase documentation pipeline:

| Phase | Directory | Description |
|-------|-----------|-------------|
| **Plans** | `docs/plans/` | Pre-build design specifications — what we intended to build |
| **Reviews** | `docs/reviews/` | Post-build critique — observations, alternatives, and deferred items |
| **Decisions** | `docs/decisions/` | Implemented changes — concrete code-level outcomes from each review |
| **References** | `docs/references/` | External source material from the game manual, disassembly, and hardware docs |

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/plans/state-module.md` | Game state reporting module plan |
| `docs/plans/commands-module.md` | Command dispatch module plan |
| `docs/reviews/environment.py.md` | environment.py design review (observations, deferred items) |
| `docs/reviews/emulator.py.md` | emulator.py design review (observations, deferred items) |
| `docs/reviews/state.py.md` | state.py design review (observations, deferred items) |
| `docs/reviews/commands.py.md` | commands.py design review (observations, deferred items) |
| `docs/reviews/autoboot.lua.md` | autoboot.lua design review (observations, deferred items) |
| `docs/reviews/state.lua.md` | state.lua design review (observations, deferred items) |
| `docs/reviews/commands.lua.md` | commands.lua design review (observations, deferred items) |
| `docs/decisions/environment.py.md` | environment.py implemented decisions |
| `docs/decisions/emulator.py.md` | emulator.py implemented decisions |
| `docs/decisions/autoboot.lua.md` | autoboot.lua implemented decisions |
| `docs/decisions/state.lua.md` | state.lua implemented decisions |
| `docs/decisions/commands.lua.md` | commands.lua implemented decisions |
| `docs/references/game/commands.md` | Original game manual + ROM-derived command grammar, object tables, incantation words |
| `docs/references/game/ram.md` | Memory map — every known RAM address and what it stores |
| `docs/references/game/code.md` | Full 6809 disassembly of the game |
| `docs/references/mame/hardware.md` | CoCo hardware reference |
| `docs/references/mame/setup.md` | Emulator architecture notes, lite MAME build plans |
| `sandbox/README.md` | Sandbox validation: TCP sockets, natkeyboard delivery, command buffering |
| `README.md` | Project overview, milestones, setup instructions |
