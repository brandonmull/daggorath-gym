# Commands Module

_See [plans/overview.md](overview.md) for project context and architecture._

> **Status:** In progress — sandbox validation complete, implementation exists.

This document addresses four design questions:

1. **What commands can we issue?** — the command grammar, command space enumeration
2. **How are commands represented?** — the wire format shared between Python and Lua
3. **How are commands dispatched?** — the Lua-side module that delivers command phrases to the game
4. **How are commands chosen and sent?** — the Python side

**Terminology:** This plan uses several related terms:

- **Command word** — a single instruction the parser recognizes (MOVE, ATTACK, INCANT, etc.). There are 14.
- **Command phrase** — the full typed string sent to the game, built from a command word plus parts ("ATTACK LEFT", "GET LEFT TORCH"). There are 154.
- **Command index** — the 0–153 byte that identifies a phrase on the wire.
- **Action space** — a concept from Gymnasium (the RL framework we use). It describes what choices the agent can make at each step. Ours is a set of 154 discrete choices (indices 0–153), one per command phrase. "Action" in this plan means a Gymnasium action — the integer the agent emits to select a command. "Action space" means the set of all 154 possible actions.

---

## Architecture

**Startup:**

```
  environment starts bridge
    │
    ├─ bridge opens command socket as server (15001)
    │
    └─ bridge launches MAME as subprocess
        │
        └─ MAME runs autoboot
            │
            └─ autoboot connects to command socket as read-only client
```

**Runtime** (command flow — Python sends, Lua receives):

```
┌─ Python ──────────────────────────────────────────┐
│  env.py        selects command by index            │
│  commands.py   defines ordered phrase list         │
│  bridge.py     sends 1 byte over TCP               │
└──────────────────────┬────────────────────────────┘
                       │ 1 byte
                       ▼
                ┌── port 15001 ──┐
                │ TCP (emu.file)  │
                └────────┬────────┘
                         │ 1 byte
                         ▼
┌─ Lua (commands.lua) ──────────────────────────────┐
│  receives command index from socket                │
│  looks up corresponding command phrase             │
│  dispatches command phrase to game                 │
└────────────────────────────────────────────────────┘
```

## Data Flow

```
env.py / bridge.py                port 15001          commands.lua            ──── (external) ────
──────────────────                ──────────          ────────────
selects command by index
sends 1 byte ──────────────→  1 byte ──→  frame callback fires
                                            │
                                            ├─ reads byte from socket
                                            ├─ looks up phrase by index
                                            └─ dispatches phrase to game's text parser
```

---

## 1. What Commands Can We Issue?

### The Game's Command Grammar

Dungeons of Daggorath is a text parser — every command is typed as words followed by ENTER. There are no directional or joystick inputs. The full grammar is documented in Appendix C of `emulation/docs/commands.md` and produces **154** valid command phrases across five categories:

### Command Words (14 words)

| Category | Words |
|----------|-------|
| Combat | ATTACK, USE |
| Inventory | DROP, EXAMINE, GET, LOOK, PULL, STOW |
| Magic | INCANT, REVEAL |
| Movement | CLIMB, MOVE, TURN |

### Parts

| Part | Values |
|------|--------|
| Hands | LEFT, RIGHT |
| Object types | FLASK, RING, SCROLL, SHIELD, SWORD, TORCH |
| Proper names | ABYE, BRONZE, DEAD, ELVISH, EMPTY, ENERGY, FINAL, FIRE, GOLD, HALE, ICE, IRON, JOULE, LEATHER, LUNAR, MITHRIL, PINE, RIME, SEER, SOLAR, SUPREME, THEWS, VISION, VULCAN, WOODEN |

### Object Specifiers

An **object specifier** is either a class name alone (e.g., `TORCH`) or a proper name followed by its class (e.g., `PINE TORCH`). Each proper name belongs to exactly one class. The full set of 31 object specifiers is:

| Class | Specifiers |
|-------|-----------|
| FLASK | FLASK, ABYE FLASK, EMPTY FLASK, HALE FLASK, THEWS FLASK |
| RING | RING, ENERGY RING, FINAL RING, FIRE RING, GOLD RING, ICE RING, JOULE RING, RIME RING, SUPREME RING, VULCAN RING |
| SCROLL | SCROLL, SEER SCROLL, VISION SCROLL |
| SHIELD | SHIELD, BRONZE SHIELD, LEATHER SHIELD, MITHRIL SHIELD |
| SWORD | SWORD, ELVISH SWORD, IRON SWORD, WOODEN SWORD |
| TORCH | TORCH, DEAD TORCH, LUNAR TORCH, PINE TORCH, SOLAR TORCH |

INCANT accepts only the proper name (without its class): `INCANT SUPREME`, not `INCANT SUPREME RING`.

### Combination Rules

| Category | Command | Required parts |
|----------|--------|---------------|
| Combat | ATTACK | one hand |
| Combat | USE | one hand |
| Inventory | DROP | one hand |
| Inventory | EXAMINE | (none) |
| Inventory | GET | one hand + one object specifier |
| Inventory | LOOK | (none) |
| Inventory | PULL | one hand + one object specifier |
| Inventory | STOW | one hand |
| Magic | INCANT | one ring proper name |
| Magic | REVEAL | one hand |
| Movement | CLIMB | UP / DOWN |
| Movement | MOVE | (none), or LEFT / RIGHT / BACK |
| Movement | TURN | LEFT / RIGHT / AROUND |

Total action space: 154 discrete command phrases.

### Flat Enumeration (Chosen)

For RL training with stable-baselines3, a flat list of all valid command phrases maps directly to `gymnasium.spaces.Discrete(154)`. The ordered list is the shared contract between Python and Lua — both sides maintain an identical ordered list where index 0 means "MOVE", index 1 means "MOVE BACK", and so on.

> **Future consideration:** A grammar-based approach (command byte + parameter bytes for object/hand selection) would be more elegant and extensible, but the flat enumeration is simpler to start with.

### Open: Action Space Scope

Start with the full 154 or a curated subset? Early training may benefit from fewer commands. Which commands are essential for initial training?

---

## 2. How Are Commands Represented?

### 1-Byte Command Index

Python sends a single byte (0–153) representing the command index. Lua looks up the index in its ordered phrase list and dispatches the corresponding command. No JSON, no key names on the wire. The index is the shared contract — both sides maintain an identical ordered list.

### Flyweight Pattern

Mirrors the state module's design: an ordered list of command phrases is the flyweight — shared, stateless, one instance at module level. Each per-step command is a lightweight value object wrapping an index.

### Why Full Words Instead of Abbreviations

The bot sends full-word command phrases (e.g., "ATTACK LEFT") rather than abbreviated single letters. This makes gameplay human-readable if someone watches the game being played. The game's text parser accepts full words and abbreviations equally, so there's no downside to using the complete forms.

---

## 3. How Are Commands Dispatched?

### The Lua Module's Job

The module receives a 1-byte command index from the command socket (port 15001), looks up the corresponding command phrase, and dispatches it to the game. The module owns its own frame loop; `autoboot.lua` only opens the socket and hands it off.

### Dispatch Mechanism

Commands are delivered via MAME's `natkeyboard:post()`, which accepts whole `\r`-terminated strings in one call. No per-character typing, hold/release cycles, or state machine is needed. The CoCo's input FIFO buffers commands and the game's parser consumes them in order.

The typing-timing and command-buffering sandboxes confirmed:

- `natkeyboard:post()` delivers commands intact — no per-character coordination
- No Lua-side buffering is needed — `natkeyboard` operates below the game's ring buffer
- `-autoboot_delay 1` and two blank `\r` priming posts are required before the first real command (handled in `autoboot.lua`)

A command is dispatched on the same frame it arrives — no frame-skipping, throttling, or batching. The sandboxes confirmed that commands can be posted at full frame rate without loss. The natural keyboard interface is acquired once on first use and reused across all subsequent frames.

On the Python side, `bridge.send()` accepts a typed command value object rather than a raw integer. The object validates the index at construction time, so an invalid index fails at the Python call site rather than being sent to the emulator as a corrupted byte.

### Module Names

| Side | File | Module | Notes |
|------|------|--------|-------|
| Lua | `commands.lua` | `commands` (module table) | Directly describes what the module dispatches |
| Python | `commands.py` | — (exposes `_COMMAND_PHRASES` as ordered list) | Same stem, no prefix needed |

Both sides share the same module name (`commands`). The Lua module exposes a single public function (`commands.start(socket)`) following the same pattern as `state.watch()`. The Python module exposes the ordered command phrase list as the shared contract.

`command` is the consistent term for the channel on port 15001. `action` is a Gymnasium term — it belongs to the framework (`action_space`, `step(action)`), not to our component names.

### Phrase Construction

The ordered list of 154 command phrases is built from a parts dictionary and combination rules rather than maintained as a static flat list. The parts encode the command grammar's vocabulary:

- **Objects types, proper names, and hands** — the building blocks described in the [Parts](#parts) table above. Proper names are stored in a dictionary keyed by object type (not a flat array) — each type has its own set of valid names, and derivations flow from the type groupings.
- **Combination rules** — which parts each command requires, described in the [Combination Rules](#combination-rules) table

The phrase builder reads the rules, references the parts dictionary, and generates all valid `\r`-terminated command phrases in order. Object specifiers are derived by combining proper names with their types. INCANT words are derived from ring proper names (all except EMPTY). The result is the same 154-phrase flyweight list, but the source of truth is the grammar, not the flat output.

This approach has two advantages over a static flat list:

1. **The grammar is visible in the code.** You can see structure (6 object types, 9 ring proper names, 5 commands taking a hand) that a flat list buries in 154 opaque strings.

2. **Changes are localized.** Adding a proper name means adding one entry to the parts dictionary. Specifiers, GET/PULL phrases, and INCANT words update automatically through the rules. In a flat list, you'd recompute offsets across multiple sections.

---

## 4. How Are Commands Chosen and Sent?

### Python Side

The bridge's `send()` writes a single byte to the command socket. The environment's `step()` selects the index from the action space, wraps it in a value object, sends it, and awaits the next state observation.

---

## Open Questions

- **Action space scope** — Full 154 or curated subset for initial training?
- ~~**Error handling** — Invalid index: drop and log. Python's `DaggorathCommand` prevents out-of-range indices at construction; a bad byte on the wire is either a bug or corruption. Lua prints a warning and ignores it for that frame — no crash, no response.~~

---

## Testing Strategy

**Unit tests** — lives in `tests/test_commands.py` (standalone file, no MAME needed, no unified test file). Tests:
- Phrase count is 154
- First phrases (MOVE, MOVE BACK, MOVE LEFT, MOVE RIGHT, TURN LEFT...)
- Last phrase (INCANT VULCAN at index 153)
- All 154 phrases are unique
- GET phrases use the LEFT/RIGHT × specifier pattern (62 phrases)
- PULL phrases use the same pattern (62 phrases)
- INCANT phrases (9 phrases, all ring proper names except EMPTY)
- `DaggorathCommand` validates in-range indices (0 and 153)
- `DaggorathCommand` rejects out-of-range indices (−1 and 154) with `ValueError`

---

## Implementation Details

### `commands.lua`

`commands.start(socket)` is the entry point.

```
commands.start(socket)
    → on the first frame, primes the CoCo input buffer with two blank carriage returns
    → registers a per-frame notifier

per-frame notifier:
    → non-blocking read of one byte from the socket
    → if a byte is available, looks up the phrase (Lua is 1-indexed)
    → lazy-acquires the natkeyboard interface on first dispatch
    → posts the phrase + carriage return to the CoCo's input buffer
    → invalid indices print a warning and are ignored
```

The command grammar's building blocks live in a table called `COMMAND_PARTS` — directions, object classes, and proper names keyed by class (values listed in §1). At module load, a private function builds the 31 object specifiers by combining each class name with its proper names, then another builds the full ordered list of 154 command phrases from those specifiers and the combination rules. The resulting list is stored in `COMMAND_PHRASES`; its order is the shared contract with `_COMMAND_PHRASES` in `commands.py`.

```
_build_object_specifiers()
    → iterates COMMAND_PARTS.classes
    → for each class, adds the class name alone
    → then adds each proper name + class combination
    → returns 31 specifiers

_build_phrases()
    → adds MOVE phrases: bare, BACK, LEFT, RIGHT
    → adds TURN phrases: LEFT, RIGHT, AROUND
    → adds CLIMB phrases: UP, DOWN
    → adds EXAMINE and LOOK (no parameters)
    → for each of ATTACK, USE, DROP, STOW, REVEAL: adds LEFT and RIGHT
    → for GET and PULL: adds every combination of LEFT/RIGHT × object specifier (2 × 31 = 62 each)
    → for INCANT: adds every ring proper name except EMPTY (9)
    → returns the full 154-phrase ordered list
```

### `commands.py`

The module defines the same grammar constants as the Lua side, in dependency order: object classes, proper names keyed by class, a direction table mapping each command word to its valid direction values, generated object specifiers, and the generated phrase list whose order is the shared contract. A reverse-lookup dict maps phrases back to indices for debugging. Two private functions mirror the Lua builder functions; INCANT phrases are derived from the ring proper names minus `"EMPTY"` — no separate incantation words constant.

```
_build_object_specifiers()
    → iterates object classes
    → for each class, adds the class name alone
    → then adds each proper name + class combination
    → returns 31 specifiers

_build_phrases()
    → follows the same phrase construction rules as Lua's _build_phrases()
    → returns the full 154-phrase ordered list
```

**`DaggorathCommand`** is a frozen dataclass wrapping a validated command index. Construction validates that the index is in range 0–153 and raises `ValueError` otherwise. A `phrase` property returns the human-readable command string.

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `emulation/docs/commands.md` | Original game manual + ROM-derived command grammar, object tables, incantation words |
| `plans/state-module.md` | Companion plan for the game state module |
| `plans/overview.md` | Project context and architecture |
| `sandbox/typing-timing/` | Validated natkeyboard:post() delivery |
| `sandbox/command-buffering/` | Validated no Lua-side buffering needed |