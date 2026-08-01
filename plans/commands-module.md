# Commands Module

_See [plans/overview.md](overview.md) for project context and architecture._

> **Status:** In progress — converted from the working notes in `plans/commands-module.md`. Several open questions remain; they are called out inline.

This document addresses four design questions:

1. **What actions can we take?** — the command grammar, action space enumeration
2. **How are actions represented?** — the wire format shared between Python and Lua
3. **How are actions dispatched and typed?** — the Lua-side module that types command phrases into the game
4. **How are actions chosen and sent?** — the Python-side Action class and bridge changes

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
┌─ Lua (<module>.lua) ──────────────────────────────┐
│  receives command index from socket                │
│  looks up corresponding command phrase             │
│  posts command phrase via natkeyboard:post()       │
└────────────────────────────────────────────────────┘

  Legend:
    ┌───┐  = file or module    ──→ = data flow    port = TCP socket
```

## Data Flow

```
env.py / bridge.py                port 15001          <module>.lua             ──── (external) ────
──────────────────                ──────────          ───────────                              ────
selects command by index
sends 1 byte ──────────────→  1 byte ──→  frame callback fires
                                            │
                                            ├─ reads byte from socket
                                            ├─ looks up phrase by index
                                            └─ natkeyboard:post(phrase .. "\r")
                                                 │
                                                 └──→  game's text parser receives full command
```

---

## 1. What Actions Can We Take?

### The Game's Command Grammar

Dungeons of Daggorath is a text parser — every command is typed as words followed by ENTER. There are no directional or joystick inputs. The full grammar is documented in Appendix C of `emulation/docs/commands.md` and produces ~152 valid command phrases across five categories:

| Category | Commands | Count |
|----------|----------|-------|
| Movement | MOVE (4), TURN (3), CLIMB (2) | 9 |
| View | EXAMINE, LOOK | 2 |
| Inventory | DROP (2), STOW (2), GET/PULL with objects | 128 |
| Combat | ATTACK (2), USE (2) | 4 |
| Magic | REVEAL (2), INCANT (9) | 11 |

The GET and PULL commands account for the bulk (124 phrases) because they accept object specifiers — 31 possible object references (6 class names + 25 proper names) × 2 hands (LEFT/RIGHT) × 2 commands = 124. This brings the total to roughly 152 discrete actions.

### The Current Approach (And Why It's Wrong)

`autoboot.lua` currently uses a simplified 11-action model that conflates letter keys with directional inputs:

```lua
local KEYS = {
    ATTACK  = "KEYCODE_A",  MOVE    = "KEYCODE_M",
    UP      = "P1_UP",      DOWN    = "P1_DOWN",
    -- etc.
}
```

This is wrong for two reasons. First, the game has no directional inputs — it only understands typed text. Second, sending single keystrokes without ENTER means the game never processes the command. The module needs to type complete phrases terminated by ENTER, matching how a human player interacts with the game.

### Flat Enumeration (Chosen)

For RL training with stable-baselines3, a flat list of all valid command phrases maps directly to `gymnasium.spaces.Discrete(152)`. The ordered list is the shared contract between Python and Lua — index 0 means "MOVE", index 1 means "MOVE BACK", and so on.

> **Future consideration:** A grammar-based approach (command byte + parameter bytes for object/hand selection) would be more elegant and extensible, but the flat enumeration is simpler to start with.

### Open: Action Space Scope

Start with the full 152 or a curated subset? Early training may benefit from fewer actions. Which commands are essential for initial training?

---

## 2. How Are Actions Represented?

### 1-Byte Action Index

Python sends a single byte (0–151) representing the action index. Lua looks up the index in its ordered phrase list and types the corresponding command. No JSON, no key names on the wire. The index is the shared contract — both sides maintain an identical ordered list.

### Flyweight Pattern

Mirrors the gamestate module's design: an ordered list of action phrases is the flyweight — shared, stateless, one instance at module level. Each per-step action is a lightweight value object wrapping an index.

| What | Shared? | Where |
|------|---------|-------|
| Action phrases ("MOVE", "ATTACK LEFT", ...) | Yes — same every run | `ACTIONS` list (one instance) |
| Action index | No — different per step | `Action` (one per step) |

### Why Full Words Instead of Abbreviations

The bot sends full-word command phrases (e.g., `"ATTACK LEFT"`) rather than abbreviated single letters. This makes gameplay human-readable if someone watches the game being played. The game's text parser accepts full words and abbreviations equally, so there's no downside to using the complete forms.

---

## 3. How Are Actions Dispatched and Typed?

### The Lua Module's Job

The module receives a 1-byte action index from the action socket (port 15001), looks up the corresponding command phrase, and posts it to the game via MAME's `natkeyboard:post()`. This mirrors `gamestate.lua` — the module owns its own frame loop, and `autoboot.lua` only opens the socket and hands it off.

### Internal Mechanics

The public API is `start(socket)` — the module registers a per-frame callback. On each frame, it reads one byte from the socket and posts the corresponding `\r`-terminated phrase directly:

```
_on_frame()
    read 1 byte from socket
      → if byte available:
          index = string.byte(raw)
          phrase = ACTIONS[index + 1]
          nk:post(phrase .. "\r")
      → if no byte: do nothing
```

**No state machine is needed.** `natkeyboard:post()` delivers the entire `\r`-terminated string in one call. The CoCo's input FIFO buffers commands and the parser consumes them in order. The typing-timing and command-buffering sandboxes confirmed:

- Commands are delivered intact — no per-character timing or hold/release cycles
- No Lua-side buffering is needed — `natkeyboard` operates below the game's ring buffer
- `-autoboot_delay 1` and two blank `\r` priming posts are required before the first real command (handled in `autoboot.lua`)

### Open: Module Name

Candidates: `commands`, `actions`, `input`. The module posts command phrases into the game — "command" or "input" are both reasonable.

---

## 4. How Are Actions Chosen and Sent?

### Python: Action Class

An `Action` is a lightweight value object wrapping an index:

```python
class Action:
    __slots__ = ('_index',)
    
    def __init__(self, index: int):
        self._index = index
    
    def to_bytes(self) -> bytes:
        return struct.pack("B", self._index)
    
    @property
    def phrase(self) -> str:
        return ACTION_SCHEMA[self._index]
```

The `ACTION_SCHEMA` is the shared ordered list — same phrases, same order as the Lua side. `to_bytes()` serializes to a single byte. The `phrase` property returns the human-readable command for debugging/logging.

### Bridge Changes

`bridge.py`'s `send()` currently sends JSON. It will instead send a single byte:

```python
def send(self, action: Action) -> None:
    self._action_conn.sendall(action.to_bytes())
```

### Env Integration

```python
self.action_space = spaces.Discrete(len(ACTION_SCHEMA))

def step(self, action_idx):
    action = Action(action_idx)
    self._bridge.send(action)
    obs = self._bridge.recv()  # returns GameState
    ...
```

---

## Open Questions

The following have been identified but not yet resolved:

- ~~**Module name** — `commands` (resolved — file: `commands.lua`, `commands.py`)~~
- ~~**Typing timing** — `natkeyboard:post()` delivers whole strings; no per-character timing needed (resolved — see sandbox/typing-timing)~~
- ~~**State machine behavior** — no state machine needed; `natkeyboard` handles delivery (resolved — see sandbox/command-buffering)~~
- **Action space scope** — full 152 or curated subset for initial training?
- ~~**Module loading strategy** — `require()` with `os.getenv("AUTOBOOT_DIR")` prepended to `package.path` (resolved — see sandbox/lua-module-loading)~~
- ~~**Character-level input API** — use `natkeyboard:post()` instead of per-character `input.set_value()` (resolved — see sandbox/typing-timing)~~
- **Error handling** — invalid index received

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `emulation/docs/commands.md` | Original game manual + ROM-derived command grammar, object tables, incantation words |
| `plans/state-module.md` | Companion plan for the game state module |
| `plans/overview.md` | Project context and architecture |
| `plans/commands-module.md` | Original working notes (preserved) |