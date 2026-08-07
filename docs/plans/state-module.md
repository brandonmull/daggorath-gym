# Game State Module

_See [overview.md](overview.md) for project context and architecture._

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
│  state.lua      samples game state each frame     │
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
│  state.py       deserializes into DaggorathState  │
│  env.py         converts to array for RL agent    │
└───────────────────────────────────────────────────┘

  Legend:
    ┌───┐  = file or module    ──→ = data flow    port = TCP socket
```

## Data Flow

```
autoboot.lua                  state.lua                        port 15000          bridge.py / env.py
─────────────                 ─────────                        ──────────          ─────────────────
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
                                └─ writes bytes to socket ────────→  raw bytes  →  deserializes to DaggorathState
                                                                                   │
                                                                                   ├─ attribute access
                                                                                   ├─ converts to array
                                                                                   └─ feeds to RL agent
```

---

## 1. What State Do We Track?

### Field List

All addresses were verified against the authoritative memory map ([`ram.md`](../references/game/ram.md)) and the 6809 disassembly ([`code.md`](../references/game/code.md)). The current `autoboot.lua` has several mislabeled addresses — 6 of its 10 fields pointed to wrong or unknown RAM locations.

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

### Module Names

| Side | File | Module/Class | Notes |
|------|------|-------------|-------|
| Lua | `state.lua` | `state` (module table) | Short, unambiguous within the emulation directory — it's the only state-related file there |
| Python | `state.py` | `DaggorathState`, `DaggorathStateSchema` | `Daggorath` prefix avoids naming collisions with MAME's internal state objects or a generic Python `GameState` |

`emulation/observer.lua` is legacy. `state.lua` replaces it. `observer.lua` must not exist.

The Lua module uses `state` rather than a longer name like `gamestate` because the emulation directory provides sufficient context — there's nothing else called "state" in that scope. The Python module uses `DaggorathState` rather than `GameState` because `GameState` is a generic term that could collide with other game state classes in the Python ecosystem. The `Daggorath` prefix makes the class name unique and self-documenting.

The module's public API is a single function: `state.watch(socket, config)`. This mirrors `commands.start(socket)` — both modules follow the same pattern: autoboot opens the socket and hands it off with a one-line call, and the module owns its own frame loop.

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
| Actual values | No — different every frame | `DaggorathState` (one per frame) |

The schema is created once at module import and shared by every `DaggorathState` instance. Each `DaggorathState` is extremely light — an immutable container with `__slots__` (no dictionary overhead) and only 12 integer attributes. Thousands can be created and discarded during training without memory pressure.

### Performance

| Metric | JSON | Raw Bytes |
|--------|------|-----------|
| Bytes per observation | ~250 | 16 |
| Lua CPU cost | `string.format` + JSON assembly | `string.char(read_u8(...))` |
| Python CPU cost | `json.loads()` | `DaggorathState(line)` — tuple unpack |
| Max reporting rate | Every 60 frames (1/sec) | Every frame (60/sec) |

---

## 3. How Is State Captured and Reported?

### Encapsulation: The Lua Module Owns the Frame Loop

Two approaches were considered for integrating the reporting logic with `autoboot.lua`:

- **Option A (chosen):** The module owns the frame loop. `autoboot.lua` opens the socket and calls `state.watch(socket, config)` — one line. The module registers the frame notifier, acquires the CPU memory space, reads RAM addresses, serializes bytes, and writes to the socket. `autoboot.lua` doesn't know about any of this.

- **Option B:** Autoboot drives. The module exposes a pure `sample(memspace)` function. Autoboot registers the frame callback, calls `sample()`, and writes to the socket.

We chose **A** because `autoboot.lua` stays minimal — just a socket open and a single module call — while the module encapsulates concerns autoboot doesn't need to know about. Testing must be end-to-end regardless; there's no `manager.machine` or `memspace:read_u8()` outside a running MAME instance. This also parallels the commands module design (same pattern, opposite direction).

After the change, `autoboot.lua` opens a write socket and hands it off with a single call — `state.watch(socket, { frame_sampling_rate = 1 })`. Everything else — memory space, RAM addresses, serialization, frame counting, error handling — is inside the module.

### Internal Mechanics

The public API is `state.watch(socket, config)` where `config` is `{ frame_sampling_rate = N }` (default: 1, meaning every frame). Internally the module tracks four state variables:

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
    → reads each address from _memspace as u8 or u16 (little-endian)
    → concatenates all values into a raw byte string using string.char()

_on_frame()
    → increments _frames_elapsed
    → lazy-initializes _memspace on first sampled frame
    → skips if _frames_elapsed is not a multiple of _frame_sampling_rate
    → reads all 12 RAM addresses and builds a 15-byte raw frame
    → writes the bytes plus a trailing newline to _socket (via pcall)
```

The `pcall()` wrapper is required — if Python hasn't connected yet, writing to the socket would crash MAME. `pcall` catches the error silently.

---

## 4. How Is State Received and Used?

### DaggorathState: Immutable Value Object

`DaggorathState` is a lightweight Python class that holds one frame of game state. It has three requirements:

1. **Fast attribute access** — fields are read thousands of times per second during RL training
2. **Immutability** — the game state reported by MAME shouldn't be changeable from Python
3. **IDE-friendly** — developers should get autocomplete on field names

Direct instance attributes satisfy requirement 1 — normal attribute access in Python is a single C-level operation, faster than dictionary lookups or property getters. `__slots__` eliminates per-instance dictionary overhead.

For requirement 2, we override `__setattr__` to raise `AttributeError` on any attempt to write. The `__init__` method uses `object.__setattr__` to bypass this block during construction. Reads have zero overhead; writes are blocked with negligible cost (since they never happen in normal operation).

Requirement 3 is satisfied because `__init__` sets each attribute explicitly by name from the schema dict (`vals["at_cell_x"]`), which IDEs recognize as typed attributes.

### Bridge Changes

`bridge.py`'s `recv()` method currently parses JSON. With raw bytes, it buffers incoming data, splits on newline delimiters, and constructs a `DaggorathState` directly from the raw byte frame for each complete line received. The `send()` method writes a single byte (the command index) to the command socket.

`to_array()` uses `uint16` — three fields are u16 values that can exceed 255. Clamping to `uint8` loses information. The environment layer can normalize or scale downstream if needed.

The reward function is out of scope for the state and commands modules. It's a derived calculation, not an intrinsic game value. The environment should provide a minimal placeholder until reward shaping is designed separately.

---

## Testing Strategy

Testing happens at two levels:

**Integration test** — launches actual MAME. Lives in `tests/test_bridge.py`. Receives raw bytes, constructs `DaggorathState`, asserts field values match known game-startup values.

**Unit tests** — lives in `tests/test_state.py` (standalone file, no MAME needed, no unified test file). Tests:
- Schema has 12 fields, `FRAME_LEN` = 15
- `unpack()` with known test bytes → correct typed dict
- `DaggorathState(raw)` construction → attribute access via `__slots__`
- `DaggorathState` immutability (`__setattr__` raises `AttributeError`)
- `to_array()` → correct numpy shape (12,) and uint16 dtype
- Newline handling (trailing `\n` from Lua is stripped before unpack)

---

## Implementation Details

### `state.lua`

`state.watch(socket, config)` is the entry point.

The schema is a constant named `SCHEMA` — an ordered array of `{ name, addr, width }` tables (12 entries, listed in §1). The byte order is the shared contract with `DaggorathStateSchema.FIELDS` in Python.

```
state.watch(socket, config)
    → stores the write socket
    → resets the frame counter
    → sets the sampling rate from config (default: every frame)
    → registers a per-frame notifier

per-frame notifier:
    → increments the frame counter
    → lazy-acquires the CPU memory space on first sampled frame
    → skips if the frame isn't a multiple of the sampling rate
    → reads all 12 RAM addresses as u8 or two-byte u16 little-endian
    → concatenates values into a 15-byte raw frame with string.char()
    → writes the bytes plus a trailing newline to the socket (via pcall)
```

### `state.py`

Two classes: `DaggorathStateSchema` (flyweight) and `DaggorathState` (immutable value object).

The field definitions are a class attribute named `FIELDS` — a tuple of `(name, offset, width)` 3-tuples in the same order as Lua's `SCHEMA`. No dataclass wrapper. `FRAME_LEN` is 15 (9 u8 + 3 u16 fields).

```
_schema.unpack(data)
    → validates data length against FRAME_LEN
    → iterates FIELDS
    → reads u8 via direct byte index, u16 via struct.unpack_from("<H")
    → returns dict of {field_name: value}

DaggorathState(data)
    → strips trailing newline from raw bytes
    → delegates to _schema.unpack()
    → sets each field as an attribute via object.__setattr__
    → after construction, __setattr__ raises AttributeError (immutable)

to_array()
    → returns a uint16 numpy array of length 12
```

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/references/game/commands.md` | Original game manual + ROM-derived command grammar, object tables, incantation words |
| `docs/references/game/ram.md` | Memory map — every known RAM address and what it stores |
| `docs/references/game/code.md` | Full 6809 disassembly of the game |
| `sandbox/README.md` | How the TCP socket communication works (emu.file, port architecture) |
| `README.md` | Project overview, milestones, setup instructions |
| `docs/plans/overview.md` | Project context and architecture |
| `docs/plans/commands-module.md` | Companion plan for the commands module |
