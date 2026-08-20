# Game State Module

_See [overview.md](../overview.md) for project context and architecture._

This document addresses four design questions:

1. **What state do we track?** — which game variables, from where, in what order
2. **How is state represented?** — the wire format shared between Lua and Python
3. **How is state captured and reported?** — the Lua-side module that reads RAM and streams bytes
4. **How is state received and used?** — the Python-side class that deserializes bytes and feeds the RL agent

---

## Architecture

**Startup:**

```
  environment starts emulator
    │
    ├─ emulator creates state FIFO (/tmp/daggorath-state)
    │
    └─ emulator launches MAME as subprocess
        │
        └─ MAME runs the plugin
            │
            └─ init.lua hands off to state.lua
                │
                └─ state.lua opens state FIFO for writing (io.open("w"))
```

**Runtime** (state flow — Lua writes, Python reads):

```
┌─ Lua ────────────────────────────────────────────┐
│  state.lua      opens the state FIFO for writing  │
│                 samples game state each frame     │
│                 reads known RAM addresses         │
│                 reads command-area pixels         │
│                 dedups both, writes tagged bytes  │
└──────────────────────┬────────────────────────────┘
                       │ tagged records
                       ▼
                ┌── state FIFO ──┐
                │ named pipe     │
                │ io.open("w")   │
                └────────┬───────┘
                         │ tagged records
                         ▼
┌─ Python ─────────────────────────────────────────┐
│  emulator.py   reads records from FIFO            │
│  state.py      deserializes into DaggorathState   │
│  screen.py     decodes text from pixel bytes      │
│  environment.py converts to array for RL agent    │
└───────────────────────────────────────────────────┘

  Legend:
    ┌───┐  = file or module    ──→ = data flow    FIFO = named pipe
```

## Data Flow

```
init.lua                      state.lua                        state FIFO          emulator.py / environment.py
───────                       ─────────                        ──────────          ────────────────────
hands off to state.lua ──→   begins watching
                              │
                              ├─ acquires CPU memory space (lazy)
                              ├─ registers per-frame callback
                              │
                              ▼  (every sampled frame)
                              frame callback fires
                                ├─ reads each field from RAM
                                │    ├─ looks up address by name
                                │    ├─ reads u8 or u16 value    ←──  6809 RAM
                                │    └─ builds byte string
                                ├─ reads command-area pixels
                                │    └─ copies 1024 bytes + comColor
                                ├─ compares both against snapshots
                                └─ writes a tagged record ────────→  record bytes  →  deserializes to DaggorathState
                                                                                     │
                                                                                     ├─ attribute access
                                                                                     ├─ decodes screen text
                                                                                     ├─ converts to array
                                                                                     └─ feeds to RL agent
```

---

## 1. What State Do We Track?

### Field List

All addresses were verified against the authoritative memory map ([`ram.md`](../references/game/ram.md)) and the 6809 disassembly ([`code.md`](../references/game/code.md)).

| Field | Bytes | Group | Description |
|-------|-------|-------|-------------|
| `game_mode` | 1 | World | FF = demo, 00 = live game |
| `at_floor` | 1 | Spatial | Current dungeon floor (0–4) |
| `at_cell_x` | 1 | Spatial | Grid column |
| `at_cell_y` | 1 | Spatial | Grid row |
| `at_heading` | 1 | Spatial | Facing direction |
| `ambient_light_physical` | 1 | World | Base physical dungeon illumination (spikes when wizard dies) |
| `ambient_light_magical` | 1 | World | Base magical dungeon illumination (spikes when wizard dies) |
| `effective_light_physical` | 1 | World | The renderer's computed physical light — `ambient_light_physical` + `torch_physical_light`; drives the sight reach |
| `effective_light_magical` | 1 | World | The renderer's computed magic light — `ambient_light_magical` + `torch_magic_light`; gates magic doors and magical creatures |
| `torch_minutes` | 1 | Light | Lit torch's remaining minutes — via `torchPtr` (`0x0224:0225`); 0 when none lit |
| `torch_physical_light` | 1 | Light | Lit torch's physical illumination — a factor of `effective_light` (via `torchPtr`) |
| `torch_magic_light` | 1 | Light | Lit torch's magic illumination — a factor of `effective_light` (via `torchPtr`) |
| `player_weight` | 2 | Body | Strain from carried items (u16) |
| `player_strength` | 2 | Body | Grows with combat victories (u16) |
| `m0221` | 2 | Body | Damage pool in combat — each landed hit adds to it; death when it exceeds `player_strength` (u16) |
| `heart_beat_interval` | 1 | Heart | Raw `heartCounterRel` — ticks between beats; lower = faster |
| `player_fainting` | 1 | Body | Faint steps remaining — 0 means conscious |
| `evil_wizard_dead` | 1 | Enemy | FF = wizard defeated |

The light fields compose the sight equation (`C660`): `effective_light_physical` is `ambient_light_physical` plus `torch_physical_light`, and `effective_light_magical` is `ambient_light_magical` plus `torch_magic_light`. Both the ambient base and the sums ship as two explicit fields rather than one packed u16 with the levels hidden in its bytes. Exposing the sums and their torch factors together lets the agent relate its torch to its ability to see. In normal play the ambient fields are `0` (only written at the Wizard's death), so the torch is effectively the whole of sight.

The previous `heart_beat_countdown` field is dropped. It was the raw `heartCounter` (0x02AE) — a countdown that decrements on the CoCo's 60 Hz interrupt and reloads from `heartCounterRel` every time it reaches zero. It changes every frame, which makes change detection (see §2) impossible. It is the timer *mechanism*, not game state.

### Derived Fields

`heart_beat_interval` is the raw reload value. The agent-facing heart signal is the **rate**, which is derived on the Python side rather than shipped over the wire:

```
heart_rate = 60 / heart_beat_interval       (beats per second)
heart_rate = 0 when heart_beat_interval == 0  (heart inactive)
```

The derivation follows from the disassembly: the heart update runs on the CoCo's 60 Hz vertical-blank interrupt (`DEC <heartCounter` at C2AD, reload from `heartCounterRel` at C2B3). The divisor 60 is the interrupt cadence, not MAME's frame rate — cross-checked by the `81 / 60 = 1.35 seconds` sync loop at C67F.

### Naming Conventions

Fields use semantic prefixes to group related concepts:

| Prefix | Fields | Group |
|--------|--------|-------|
| `at_` | `at_cell_x`, `at_cell_y`, `at_floor`, `at_heading` | Spatial location |
| `player_` | `player_weight`, `player_strength`, `player_fainting` | Physical attributes |
| `heart_` | `heart_beat_interval` | Heartbeat mechanics |
| `torch_` | `torch_minutes`, `torch_physical_light`, `torch_magic_light` | Lit torch state |
| `evil_` | `evil_wizard_dead` | Enemy state |
| _(bare)_ | `game_mode`, `ambient_light`, `effective_light`, `m0221` | No semantic prefix |

Lua uses camelCase (`heartBeatInterval`), Python uses snake_case (`heart_beat_interval`). The names don't appear on the wire — only the byte order matters — so each side uses the convention appropriate for its language.

`heart_rate` is Python-only (a derived value, not a wire field), which is why it has no Lua counterpart. The wire field stays `heartBeatInterval` / `heart_beat_interval` and mirrors the disassembly name.

### Field Ordering

Three competing principles were considered before settling on **hierarchical**:

1. **Player experience** — spatial first, body, heart, world, enemy. Answers "where am I → how am I doing → what's around me → is it over?" in the order a player thinks.

2. **Game mechanic coupling** — the causal chain: weight/strength → heart interval → fainting → death. Adjacent fields in the wire format tell the story of the core survival loop.

3. **Hierarchical (chosen)** — broad context to immediate survival. Like zooming in on a map: first the world (game mode, dungeon floor), then the region (cell, heading, light), then the character sheet (weight, strength, heart), then the life-or-death moment (fainting, wizard dead). This is the most intuitive reading order for a state dump.

### Module Names

| Side | File | Module/Class | Notes |
|------|------|-------------|-------|
| Lua | `state.lua` | `state` (module table) | Short, unambiguous within the plugin directory — it's the only state-related file there |
| Python | `state.py` | `DaggorathState`, `DaggorathStateSchema` | `Daggorath` prefix avoids naming collisions with MAME's internal state objects or a generic Python `GameState` |

`emulation/observer.lua` is legacy. `state.lua` replaces it. `observer.lua` must not exist.

The module's public API is a single function: `state.beginWatching(stateFile, config)`. This mirrors `commands.beginProcessing(commandSocket)` — both modules follow the same pattern: the entry point receives an open I/O handle and owns its own frame loop.

---

## 2. How Is State Represented?

### The Schema: A Shared Contract

State is represented as an ordered list of fields — a **schema** that both sides share. The Lua module defines which RAM addresses to read and in what order. The Python module defines the same field list, in the same order, with a converter function for each field.

The order is the contract. If the two sides fall out of sync, all values shift and everything breaks. But when they match, the representation is compact and unambiguous.

### Why Raw Bytes Instead of JSON

The previous system built a JSON string for each observation — about **250 bytes** of text, of which only ~10 were actual game data. On the emulated 6809 CPU running at ~0.89 MHz, string formatting eats into the frame budget.

**Raw bytes** invert this: we send just the values in schema order. Twenty-one bytes carry all eighteen fields. The Lua side writes with simple `string.char()` calls — near-zero CPU cost. The Python side reads a byte string and hands it to the schema for deserialization.

```
[00] [00] [16] [0C] [00] [00] [00] [00] [07] [64] [07] [00] [23] [00] [A0] [17] [00] [07] [28] [00] [00]
  ↑    ↑    ↑    ↑    ↑    ↑    ↑    ↑    ↑    ↑    ↑    ↑    ↑    ↑    ↑    ↑    ↑    ↑    ↑    ↑    ↑
game at   at    at   at   ambi ambi eff  eff  torch torch torch plyr plyr plyr plyr m0221 m0221 heart plyr evil
mode floor cellX cellY head LgtLo LgtHi LgtLo LgtHi  Min  Phys  Mag  WgtLo WgtHi StrLo StrHi  Lo   Hi  Inter faint WizDed
```

Five fields are u16 (two bytes each: `ambient_light`, `effective_light`, `player_weight`, `player_strength`, `m0221`); the remaining eleven are u8.

### The Tracked Wire Record

The state channel now carries **tagged records** instead of a bare frame. A record is one ASCII kind byte followed by its payload, newline-terminated:

| Kind | Payload | Meaning |
|------|---------|---------|
| `S` | 21-byte frame | Numeric state changed, screen text unchanged |
| `T` | 1 byte `comColor` + 1024 pixel bytes | Screen text changed, numeric state unchanged |
| `B` | 21-byte frame + 1 byte `comColor` + 1024 pixel bytes | Both changed |
| `M` | 1024-byte maze | The current level's maze edge bytes changed |
| `C` | 128-byte creature array | A creature slot changed |
| `O` | 70-byte object record | Hands, pack, or a floor object changed |
| `H` | 24-byte holes/ladders record | A ceiling or floor connection changed |

This is change detection, not batching. A record in the FIFO means "something meaningful changed." Identical frames are not written at all — replaced by a snapshot comparison in Lua (see §3).

Python maintains the last-known frame and last-known text, so either can be omitted from a record and reconstructed on the other side. The `B` record is the unambiguous case where both changed in the same sampled frame. The four world records follow the same rule — each is written only when its own snapshot differs — and Python keeps the last-known maze, creature array, object record, and holes/ladders record so the world state reconstructs across records. The world records' layouts live in their modules' plans: the maze and holes/ladders in `navigation/plan.md`, the creature array in `creatures/plan.md`, and the object record in `objects/plan.md`.

### Flyweight Pattern

The schema embodies the **Flyweight pattern**: what's shared across every frame is separated from what's unique per instance.

| What | Shared? | Where |
|------|---------|-------|
| Field names | Yes — same every frame | Schema (one instance) |
| Byte offsets | Yes — same every frame | Schema (one instance) |
| Type converters (u8, u16) | Yes — same every frame | Schema (one instance) |
| Actual values | No — different every frame | `DaggorathState` (one per change) |

The schema is created once at module import and shared by every `DaggorathState` instance. Each `DaggorathState` is extremely light — an immutable container with `__slots__` (no dictionary overhead). Change detection means these are now created only when a meaningful change occurs, not every frame.

### Performance

| Metric | Previous | This design |
|--------|----------|-------------|
| Bytes per wired state frame | 16 | 16 |
| Wired records | every frame | only on change |
| Lua CPU cost | `string.char(read_u8(...))` | same, plus a byte comparison |
| Python CPU cost | `DaggorathState(line)` | tag dispatch + `DaggorathState` |

---

## 3. How Is State Captured and Reported?

### Encapsulation: The Lua Module Owns the Frame Loop

The module owns the frame loop. `init.lua` hands the state FIFO file handle to the module via `state.beginWatching(stateFile, config)` — one line. The module registers the frame notifier, acquires the CPU memory space, reads RAM addresses, captures pixels, detects change, and writes records. `init.lua` doesn't know about any of this.

### Internal Mechanics

The public API is `state.beginWatching(stateFile, config)` where `config` is `{ frame_sampling_rate = N }` (default: 1, meaning every frame). Internally the module tracks:

| Variable | Purpose |
|----------|---------|
| `_stateFile` | The FIFO file handle opened with `io.open("w")` |
| `_memory` | CPU program space, lazy-initialized on first frame |
| `_framesElapsed` | Counter since `beginWatching()` was called |
| `_frameSamplingRate` | From config |
| `_stateSnapshot` | Last-emitted 21-byte numeric frame, for change detection |
| `_pixelSnapshot` | Last-emitted 1024 pixel bytes + `comColor`, for change detection |

Two internal functions do the work:

```
_sampleState()
    → iterates SCHEMA
    → reads each address from _memory as u8 or u16 (little-endian)
    → concatenates all values into a 21-byte string using string.char()

_readCommandAreaPixels()
    → reads comStart from 0x0390–0x0391 (big-endian)
    → copies 1024 bytes from the command area (32 scanlines × 32 bytes)
    → reads comColor from 0x0396
    → returns the pixel block plus comColor
```

On each sampled frame these produce two candidates. Each is compared byte-for-byte against its snapshot; a record is written only for the side(s) that differ, and the snapshot advances. The first sampled frame emits a `B` record unconditionally — there is no prior snapshot to compare against.

```
_on_frame()
    → increments _framesElapsed
    → lazy-initializes _memory on first sampled frame
    → skips if _framesElapsed is not a multiple of _frameSamplingRate
    → gates on displayFunction == 0xCE66 (no text to read during demo)
    → samples the numeric frame and the pixel block
    → compares each to its snapshot
    → writes S / T / B record to _stateFile (via pcall)
    → advances the snapshot(s) for whichever changed
```

The `pcall()` wrapper is required — if Python hasn't opened the FIFO yet, writing to it would crash MAME. `pcall` catches the error silently.

---

## 4. How Is State Received and Used?

### DaggorathState: Immutable Value Object

`DaggorathState` is a lightweight Python class that holds one meaningful change of game state. It has three requirements:

1. **Fast attribute access** — fields are read thousands of times per second during RL training
2. **Immutability** — the game state reported by MAME shouldn't be changeable from Python
3. **IDE-friendly** — developers should get autocomplete on field names

Direct instance attributes satisfy requirement 1 — normal attribute access in Python is a single C-level operation, faster than dictionary lookups or property getters. `__slots__` eliminates per-instance dictionary overhead.

For requirement 2, we override `__setattr__` to raise `AttributeError` on any attempt to write. The `__init__` method uses `object.__setattr__` to bypass this block during construction.

Requirement 3 is satisfied because `__init__` sets each attribute explicitly by name from the schema dict, which IDEs recognize as typed attributes.

In addition to the wire fields, `DaggorathState` exposes the derived `heart_rate` attribute computed from `heart_beat_interval`. The derivation is `60 / interval` (0 when the interval is zero). Because this value is fractional, it is *not* part of the current uint16 array — its representation in the observation space is a decision for the gym-space design (see below).

### Emulator Changes

`emulator.py`'s `recv()` reads a newline-terminated record from the state FIFO. It dispatches on the kind byte:

- `S` → unpack the 21-byte frame, reuse the last-decoded text
- `T` → decode the pixel block via `screen.py`, reuse the last-known state
- `B` → unpack both

It maintains the last-known frame and text so omitted halves of a record can be reconstructed. Decoded text and the numeric frame are returned together (see the deferred note below on how this surfaces to the agent).

### A Note Carried Into the Gym-Space Design

MAME runs continuously — while Python computes, frames keep flowing into the FIFO. Change detection means each meaningful change is *captured*, but they may accumulate into a series between two agent steps. Whether the agent observes the **latest snapshot** or the **full series since the last step** is the first decision of the gym-space design. This module's job is only to ensure no change is lost: every meaningful change is written once, and nothing is re-transmitted merely because a frame ticked.

---

## Testing Strategy

Testing happens at two levels:

**Integration test** — launches actual MAME. Lives in `tests/test_emulator.py`. Receives records, constructs `DaggorathState`, asserts field values match known game-startup values, and verifies the first record is a `B`.

**Unit tests** — lives in `tests/test_state.py` (standalone file, no MAME needed, no unified test file). Tests:
- Schema has 18 fields, `FRAME_LEN` = 21
- `unpack()` with known test bytes → correct typed dict
- `DaggorathState(raw)` construction → attribute access via `__slots__`
- `DaggorathState` immutability (`__setattr__` raises `AttributeError`)
- `as_perceived()` → perceived-state Dict; `scalars` has shape (16,) and uint16 dtype
- `heart_rate` derivation → `60 / interval`, and 0 when the interval is zero
- Record dispatch → `S`, `T`, and `B` kinds each route correctly

**Screen decode tests** live with the screen module (see `docs/plans/screen/plan.md`): known pixel blocks decode to `PULL LEFT TORCH` and `???`.

---

## Implementation Details

### `state.lua`

`state.beginWatching(stateFile, config)` is the entry point.

The schema is a constant named `SCHEMA` — an ordered array of `{ name, addr, width }` tables (18 entries, listed in §1). The three torch fields carry `torchOffset` instead of `addr` and are read through `torchPtr`, the pointer to the lit torch (0 when none lit). The byte order is the shared contract with `DaggorathStateSchema.FIELDS` in Python.

```
state.beginWatching(stateFile, config)
    → stores the state FIFO file handle
    → resets the frame counter and both snapshots
    → sets the sampling rate from config (default: every frame)
    → registers a per-frame notifier

per-frame notifier:
    → increments the frame counter
    → lazy-acquires the CPU memory space on first sampled frame
    → skips if the frame isn't a multiple of the sampling rate
    → reads 13 direct RAM addresses and the lit torch's three bytes (via torchPtr) as u8 or two-byte u16 little-endian
    → concatenates values into a 21-byte raw frame with string.char()
    → reads the command-area pixel block and comColor
    → compares frame and pixels to their snapshots
    → writes an S / T / B tagged record (via pcall)
    → advances whichever snapshots changed
```

### `state.py`

Two classes: `DaggorathStateSchema` (flyweight) and `DaggorathState` (immutable value object).

The field definitions are a class attribute named `FIELDS` — a tuple of `(name, offset, width)` 3-tuples in the same order as Lua's `SCHEMA`. No dataclass wrapper. `FRAME_LEN` is 21 (15 u8 + 3 u16 fields).

```
_schema.unpack(data)
    → validates data length against FRAME_LEN
    → iterates FIELDS
    → reads u8 via direct byte index, u16 via struct.unpack_from("<H")
    → returns dict of {field_name: value}

DaggorathState(data)
    → strips trailing newline from the frame bytes
    → delegates to _schema.unpack()
    → sets each field as an attribute via object.__setattr__
    → derives heart_rate from heart_beat_interval
    → after construction, __setattr__ raises AttributeError (immutable)

as_perceived()
    → returns the perceived-state Dict
    → fills scalars with the eighteen self-fields
    → zero-fills the world channels (hands, pack, creatures, objects, map) —
      not sampled yet, so their zeros are stubs, not an empty world
    → applies the perception gates (line-of-sight, mode, light) once the
      world channels land
```

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/references/game/commands.md` | Original game manual + ROM-derived command grammar, object tables, incantation words |
| `docs/references/game/ram.md` | Memory map — every known RAM address and what it stores |
| `docs/references/game/code.md` | Full 6809 disassembly of the game |
| `docs/plans/screen/plan.md` | Screen-reading plan — capture and decode of command-area text |
| `docs/plans/creatures/plan.md` | Creature detection — knowns, unknowns, and open questions |
| `docs/plans/objects/plan.md` | Object detection — knowns, unknowns, and open questions |
| `docs/plans/reward/plan.md` | Reward — potential-based shaping over player-perceived state |
| `docs/findings/ipc.md` | IPC transport evaluation — FIFO for state, TCP for commands |
| `docs/findings/combat-model.md` | The strength-vs-damage combat model and the sound proximity channel |
| `docs/plans/overview.md` | Project context and architecture |
| `docs/plans/commands/plan.md` | Companion plan for the commands module |