# Game State Module

_See [plans/overview.md](overview.md) for project context and architecture._

This document addresses four design questions:

1. **What state do we track?** — which game variables, from where, in what order
2. **How is state represented?** — the wire format shared between Lua and Python
3. **How is state captured and reported?** — the Lua-side module that reads RAM and streams bytes
4. **How is state received and used?** — the Python-side class that deserializes bytes and feeds the RL agent

---

## Architecture

**Startup:**

```
  environment starts bridge
    │
    ├─ bridge opens state socket as server (15000)
    │
    └─ bridge launches MAME as subprocess
        │
        └─ MAME runs autoboot
            │
            └─ autoboot connects to state socket as write-only client
```

**Runtime** (state flow — Lua sends, Python receives):

```
┌─ Lua ────────────────────────────────────────────┐
│  autoboot.lua   opens the write socket            │
│  gamestate.lua  samples game state each frame     │
│                 reads known RAM addresses         │
│                 writes raw bytes to socket        │
└──────────────────────┬────────────────────────────┘
                       │ raw bytes
                       ▼
                ┌── port 15000 ──┐
                │ TCP (emu.file)  │
                └────────┬────────┘
                         │ raw bytes
                         ▼
┌─ Python ─────────────────────────────────────────┐
│  bridge.py      receives bytes from socket        │
│  game_state.py  deserializes into GameState       │
│  env.py         converts to array for RL agent    │
└───────────────────────────────────────────────────┘

  Legend:
    ┌───┐  = file or module    ──→ = data flow    port = TCP socket
```

## Data Flow

```
autoboot.lua                  gamestate.lua                    port 15000          bridge.py / env.py
─────────────                 ─────────────                    ──────────          ─────────────────
opens write socket ──────→   begins watching
                              │
                              ├─ acquires CPU memory space (lazy)
                              ├─ registers per-frame callback
                              │
                              ▼  (every N frames)
                              frame callback fires
                                ├─ reads each field from RAM
                                │    ├─ looks up address by name
                                │    ├─ reads u8 or u16 value    ←──  6809 RAM
                                │    └─ builds byte string
                                │
                                └─ writes bytes to socket ────────→  raw bytes  →  deserializes to GameState
                                                                                   │
                                                                                   ├─ attribute access
                                                                                   ├─ converts to array
                                                                                   └─ feeds to RL agent
```

---

## 1. What State Do We Track?

### Field List

All addresses were verified against the authoritative memory map (`emulation/docs/ram.md`) and the 6809 disassembly (`emulation/docs/code.md`). The current `autoboot.lua` has several mislabeled addresses — 6 of its 10 fields pointed to wrong or unknown RAM locations.

| Field | Bytes | Group | Description |
|-------|-------|-------|-------------|
| `game_mode` | 1 | World | FF = demo, 00 = live game |
| `at_floor` | 1 | Spatial | Current dungeon floor (0–4) |
| `at_cell_x` | 1 | Spatial | Grid column |
| `at_cell_y` | 1 | Spatial | Grid row |
| `at_heading` | 1 | Spatial | Facing direction |
| `ambient_light` | 2 | World | Base dungeon illumination (u16, spikes when wizard dies) |
| `player_weight` | 2 | Body | Strain from carried items (u16) |
| `player_strength` | 2 | Body | Grows with combat victories (u16) |
| `heart_beat_interval` | 1 | Heart | Time between heartbeats — lower = more exertion |
| `heart_beat_countdown` | 1 | Heart | Ticks toward zero; triggers redraw/beat sound at zero |
| `player_fainting` | 1 | Body | Faint steps remaining — 0 means conscious |
| `evil_wizard_dead` | 1 | Enemy | FF = wizard defeated |

### Naming Conventions

Fields use semantic prefixes to group related concepts:

| Prefix | Fields | Group |
|--------|--------|-------|
| `at_` | `at_cell_x`, `at_cell_y`, `at_floor`, `at_heading` | Spatial location |
| `player_` | `player_weight`, `player_strength`, `player_fainting` | Physical attributes |
| `heart_` | `heart_beat_interval`, `heart_beat_countdown` | Heartbeat mechanics |
| `evil_` | `evil_wizard_dead` | Enemy state |
| _(bare)_ | `game_mode`, `ambient_light` | World state |

Lua uses camelCase (`heartBeatInterval`), Python uses snake_case (`heart_beat_interval`). The names don't appear on the wire — only the byte order matters — so each side uses the convention appropriate for its language.

`at_` was chosen over `player_` for spatial fields because "player cell x" reads as "player one's x coordinate" when there's only one player. The game's own manual uses "cell" for grid positions ("step one cell forward"). `at_` groups spatial fields while `player_` groups physical attributes — a clean separation between "where" and "how you are."

### Field Ordering

Three competing principles were considered before settling on **hierarchical**:

1. **Player experience** — spatial first, body, heart, world, enemy. Answers "where am I → how am I doing → what's around me → is it over?" in the order a player thinks.

2. **Game mechanic coupling** — the causal chain: weight/strength → heart interval → countdown → fainting → death. Adjacent fields in the wire format tell the story of the core survival loop.

3. **Hierarchical (chosen)** — broad context to immediate survival. Like zooming in on a map: first the world (game mode, dungeon floor), then the region (cell, heading, light), then the character sheet (weight, strength, heart), then the life-or-death moment (fainting, wizard dead). This is the most intuitive reading order for a state dump.

---

## 2. How Is State Represented?

### The Schema: A Shared Contract

State is represented as an ordered list of fields — a **schema** that both sides share. The Lua module defines which RAM addresses to read and in what order. The Python module defines the same field list, in the same order, with a converter function for each field.

The order is the contract. If the two sides fall out of sync, all values shift and everything breaks. But when they match, the representation is compact and unambiguous.

### Why Raw Bytes Instead of JSON

The current system builds a JSON string for each observation:

```lua
local msg = string.format(
    '{"event":"observerTriggered","timestamp":"%s","heartCounter":%d,...}',
    os.date("%Y-%m-%d %H:%M:%S"),
    memspace:read_u8(0x02AE),  -- heartCounter
    memspace:read_u8(0x02AF),  -- heartCounterRel
    -- ... 8 more fields
)
```

This produces about **250 bytes** of text — 240 of which are repeated key names and structural characters. Only ~10 bytes are actual game data. On the emulated 6809 CPU running at ~0.89 MHz, every `string.format` call and string concatenation eats into the frame budget. JSON serialization becomes prohibitive at every-frame reporting.

**Raw bytes** invert this: we send just the values in schema order. Sixteen bytes carry all twelve fields. The Lua side writes this with simple `string.char()` calls — near-zero CPU cost. The Python side reads a byte string and hands it to the schema for deserialization.

```
[00] [01] [16] [0C] [02] [03] [2A] [00] [23] [17] [A0] [50] [00] [00] [03] [00]
  ↑     ↑     ↑    ↑    ↑    ↑    ↑     ↑    ↑     ↑     ↑    ↑    ↑    ↑    ↑
game  at   at    at   at   ambi ambi plyr  plyr  plyr  heart heart plyr  evil
mode  floor cellX cellY head LgtHi LgtLo WgtHi WgtLo StrHi StrLo Inter Count faint WizDed
```

Three fields are u16 (two bytes each: `ambient_light`, `player_weight`, `player_strength`). The rest are u8.

### Flyweight Pattern

The schema embodies the **Flyweight pattern**: what's shared across every frame is separated from what's unique per instance.

| What | Shared? | Where |
|------|---------|-------|
| Field names | Yes — same every frame | Schema (one instance) |
| Byte offsets | Yes — same every frame | Schema (one instance) |
| Type converters (u8, u16) | Yes — same every frame | Schema (one instance) |
| Actual values | No — different every frame | `GameState` (one per frame) |

The schema is created once at module import and shared by every `GameState` instance. Each `GameState` is extremely light — an immutable container with `__slots__` (no dictionary overhead) and only 12 integer attributes. Thousands can be created and discarded during training without memory pressure.

### Performance

| Metric | JSON | Raw Bytes |
|--------|------|-----------|
| Bytes per observation | ~250 | 16 |
| Lua CPU cost | `string.format` + JSON assembly | `string.char(read_u8(...))` |
| Python CPU cost | `json.loads()` | `GameState(line)` — tuple unpack |
| Max reporting rate | Every 60 frames (1/sec) | Every frame (60/sec) |

---

## 3. How Is State Captured and Reported?

### Encapsulation: The Lua Module Owns the Frame Loop

Two approaches were considered for integrating the reporting logic with `autoboot.lua`:

- **Option A (chosen):** The module owns the frame loop. `autoboot.lua` opens the socket and calls `gamestate.watch(socket, config)` — one line. The module registers the frame notifier, acquires the CPU memory space, reads RAM addresses, serializes bytes, and writes to the socket. `autoboot.lua` doesn't know about any of this.

- **Option B:** Autoboot drives. The module exposes a pure `sample(memspace)` function. Autoboot registers the frame callback, calls `sample()`, and writes to the socket.

We chose **A** because `autoboot.lua` stays minimal (3 lines instead of ~60), the module encapsulates concerns autoboot doesn't need to know about, and testing must be end-to-end regardless — there's no `manager.machine` or `memspace:read_u8()` outside a running MAME instance. This also parallels the commands module design (same pattern, opposite direction).

What `autoboot.lua` looks like after the change:

```lua
local sock_w = emu.file("w")
sock_w:open("socket.127.0.0.1:15000")
gamestate.watch(sock_w, { frame_sampling_rate = 1 })
```

That's it. Three lines. Everything else — memory space, RAM addresses, serialization, frame counting, error handling — is inside the module.

### Internal Mechanics

The public API is `gamestate.watch(socket, config)` where `config` is `{ frame_sampling_rate = N }` (default: 1, meaning every frame). Internally the module tracks four state variables:

| Variable | Purpose |
|----------|---------|
| `_socket` | The `emu.file("w")` socket |
| `_memspace` | CPU program space, lazy-initialized on first frame |
| `_frames_elapsed` | Counter since `watch()` was called |
| `_frame_sampling_rate` | From config |

Two internal functions do the work:

```
_sample()
    → iterates SCHEMA
    → looks up each name in RAM for address
    → calls memspace:read_u8() or read_u16() based on width
    → returns string.char(...) concatenated bytes

_on_frame()
    → increments _frames_elapsed
    → if _frames_elapsed % _frame_sampling_rate == 0:
        bytes = _sample()
        pcall(function() _socket:write(bytes) end)
```

The `pcall()` wrapper is required — if Python hasn't connected yet, writing to the socket would crash MAME. `pcall` catches the error silently.

---

## 4. How Is State Received and Used?

### GameState: Immutable Value Object

`GameState` is a lightweight Python class that holds one frame of game state. It has three requirements:

1. **Fast attribute access** — fields are read thousands of times per second during RL training
2. **Immutability** — the game state reported by MAME shouldn't be changeable from Python
3. **IDE-friendly** — developers should get autocomplete on field names

Direct instance attributes satisfy requirement 1 — normal attribute access in Python is a single C-level operation, faster than dictionary lookups or property getters. `__slots__` eliminates per-instance dictionary overhead.

For requirement 2, we override `__setattr__` to raise `AttributeError` on any attempt to write. The `__init__` method uses `object.__setattr__` to bypass this block during construction. Reads have zero overhead; writes are blocked with negligible cost (since they never happen in normal operation).

Requirement 3 is satisfied because `__init__` sets each attribute explicitly by name from the schema dict (`vals["at_cell_x"]`), which IDEs recognize as typed attributes.

### Bridge Changes

`bridge.py`'s `recv()` method currently parses JSON. With raw bytes, it constructs `GameState` directly:

```python
def recv(self) -> GameState:
    while True:
        if b"\n" in self._recv_buf:
            line, self._recv_buf = self._recv_buf.split(b"\n", 1)
            if line.strip():
                return GameState(line)
            continue
        chunk = self._state_conn.recv(4096)
        ...
```

The `send()` method stays unchanged — commands are handled by the separate `commands.py` module.

`env.py` replaces dict access with typed attributes and uses the built-in `to_array()`:

```python
def step(self, action_idx):
    obs = self._bridge.recv()          # GameState, not dict
    reward = self._compute_reward(obs)
    return obs.to_array(), reward, terminated, truncated, {}
```

---

## Testing Strategy

Testing happens at two levels:

**Integration test** — launches actual MAME with `emulation/test_gamestate.lua` (a minimal autoboot script that only calls `gamestate.watch()` — no action socket, no key handling). `tests/test_gamestate.py` receives raw bytes, constructs `GameState`, and asserts field values match known game-startup values. Also verifies immutability.

**Unit tests** (Python only — no MAME needed):
- `GameStateSchema.unpack()` with known test bytes → correct typed tuple
- `GameState(raw).to_array()` → correct numpy array shape and dtype
- `GameState` immutability → `__setattr__` raises on mutation attempt

---

## Implementation

### GameStateSchema

The schema is the flyweight — a single shared instance created at module import. It accepts a list of `(name, width, converter)` tuples, computes byte offsets automatically from the widths, and provides an `unpack()` method that slices the raw byte string and applies converters:

```python
from typing import Callable

class GameStateSchema:
    def __init__(self, fields: list[tuple[str, int, Callable[[bytes], int]]]):
        self._names = tuple(f[0] for f in fields)
        self._converters = tuple(f[2] for f in fields)
        self._offsets = []
        self._widths = []
        offset = 0
        for _, width, _ in fields:
            self._offsets.append(offset)
            self._widths.append(width)
            offset += width
        self._total_bytes = offset

    def unpack(self, raw: bytes) -> dict[str, int]:
        return {
            name: converter(raw[off:off + width])
            for name, converter, off, width in zip(
                self._names, self._converters, self._offsets, self._widths
            )
        }

    @property
    def field_names(self) -> tuple[str, ...]:
        return self._names
```

`unpack()` returns a dict keyed by field name — the schema is the single source of truth. `GameState` sets attributes by name from this dict, so changing the schema automatically updates everything. No hardcoded indices anywhere outside the schema definition itself.

### Schema Definitions

Per the shared contract described in section 2, both sides maintain an identical ordered field list passed to `GameStateSchema`:

**Lua** (`emulation/gamestate.lua`):

```lua
local RAM = {
    gameMode         = 0x0277,
    atFloor          = 0x0281,
    atCellX          = 0x0214,
    atCellY          = 0x0213,
    atHeading        = 0x0223,
    ambientLight     = 0x0226,
    playerWeight     = 0x0215,
    playerStrength   = 0x0217,
    heartBeatInterval  = 0x02AF,
    heartBeatCountdown = 0x02AE,
    playerFainting   = 0x0228,
    evilWizardDead   = 0x022B,
}

local SCHEMA = {
    {"gameMode",           1},
    {"atFloor",            1},
    {"atCellX",            1},
    {"atCellY",            1},
    {"atHeading",          1},
    {"ambientLight",       2},
    {"playerWeight",       2},
    {"playerStrength",     2},
    {"heartBeatInterval",  1},
    {"heartBeatCountdown", 1},
    {"playerFainting",     1},
    {"evilWizardDead",     1},
}
```

**Python** (`daggorath_gym/game_state.py`):

```python
SCHEMA = GameStateSchema([
    ("game_mode",              1, lambda b: b[0]),
    ("at_floor",               1, lambda b: b[0]),
    ("at_cell_x",              1, lambda b: b[0]),
    ("at_cell_y",              1, lambda b: b[0]),
    ("at_heading",             1, lambda b: b[0]),
    ("ambient_light",          2, lambda b: b[0] << 8 | b[1]),
    ("player_weight",          2, lambda b: b[0] << 8 | b[1]),
    ("player_strength",        2, lambda b: b[0] << 8 | b[1]),
    ("heart_beat_interval",    1, lambda b: b[0]),
    ("heart_beat_countdown",   1, lambda b: b[0]),
    ("player_fainting",        1, lambda b: b[0]),
    ("evil_wizard_dead",       1, lambda b: b[0]),
])
```

u16 converters use `b[0] << 8 | b[1]` (big-endian, high byte first).

### GameState Class

As discussed in section 4, `GameState` uses `__slots__` for zero dict overhead, direct attribute assignment for fast access, and a blocked `__setattr__` for immutability:

```python
import numpy as np

class GameState:
    __slots__ = (
        'game_mode', 'at_floor', 'at_cell_x', 'at_cell_y', 'at_heading',
        'ambient_light', 'player_weight', 'player_strength',
        'heart_beat_interval', 'heart_beat_countdown',
        'player_fainting', 'evil_wizard_dead',
    )

    def __init__(self, raw: bytes):
        vals = SCHEMA.unpack(raw)            # dict[str, int]
        for name in SCHEMA.field_names:
            object.__setattr__(self, name, vals[name])

    def __setattr__(self, name, value):
        raise AttributeError("GameState is immutable")

    def to_array(self) -> np.ndarray:
        return np.array(
            [getattr(self, name) for name in SCHEMA.field_names],
            dtype=np.uint8,
        )
```

`__init__` iterates the schema's field names, setting attributes from the dict returned by `unpack()`. No hardcoded indices — the schema is the single source of truth. Adding or reordering a field only requires changing the schema definition.

`to_array()` uses the same field-name iteration, so it automatically stays in sync. Note that u16 values span multiple array elements (the schema's widths aren't tracked here — each field produces one slot regardless of byte width).

> **Alternative considered:** We may not need named attribute access on the Python side at all. The Gym environment might just pass raw state directly to the RL agent as a numpy array, with no selective field access in reward calculation or observation processing. In that case, a single function `unpack(raw: bytes) -> np.ndarray` — with no `GameStateSchema` class, no `GameState` class, no immutability, and no `__slots__` — would be more direct and efficient. The current class-based approach is retained for now because it makes the state representation self-documenting for developers, but this may be revisited once the Gym environment's actual usage patterns are clear.

### Implementation Order

1. Create `daggorath_gym/game_state.py` with `GameStateSchema` and `GameState`
2. Create `emulation/gamestate.lua` with `RAM`, `SCHEMA`, `watch()`, `_sample()`, `_on_frame()`
3. Wire `gamestate.watch()` into `autoboot.lua` (replace inline observer logic)
4. Update `bridge.py` `recv()` to return `GameState` instead of dict
5. Update `env.py` to use typed attributes and `to_array()`
6. Create `emulation/test_gamestate.lua` and `tests/test_gamestate.py`
7. Run sandbox to verify end-to-end
8. Delete `emulation/observer.lua`

---

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `emulation/docs/commands.md` | Original game manual + ROM-derived command grammar, object tables, incantation words |
| `emulation/docs/ram.md` | Memory map — every known RAM address and what it stores |
| `emulation/docs/code.md` | Full 6809 disassembly of the game |
| `sandbox/README.md` | How the TCP socket communication works (emu.file, port architecture) |
| `README.md` | Project overview, milestones, setup instructions |
| `plans/overview.md` | Project context and architecture |
| `plans/commands-module.md` | Companion plan for the commands module |
