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

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `emulation/docs/commands.md` | Original game manual + ROM-derived command grammar, object tables, incantation words |
| `emulation/docs/ram.md` | Memory map — every known RAM address and what it stores |
| `emulation/docs/code.md` | Full 6809 disassembly of the game |
| `sandbox/README.md` | Sandbox validation: TCP sockets, natkeyboard delivery, command buffering |
| `README.md` | Project overview, milestones, setup instructions |
| `plans/state-module.md` | Game state reporting module plan |
| `plans/commands-module.md` | Command dispatch module plan |