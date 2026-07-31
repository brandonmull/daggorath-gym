# Keyboard Input

_Source: [MAME Documentation 0.289 — Lua Input System Classes](https://docs.mamedev.org/luascript/ref-input.html)_

MAME's **Natural Keyboard Manager** translates host keystrokes to emulated keyboard inputs automatically. This is the preferred API for typing commands into Dungeons of Daggorath.

## Usage

```lua
local natkbd = manager.machine.natkeyboard
natkbd.in_use = true
natkbd:post("EXAMINE{ENTER}")
```

## Natural Keyboard Manager

`manager.machine.natkeyboard`

### Methods

| Method | Description |
|--------|-------------|
| `natkeyboard:post(text)` | Post literal text to the emulated machine. Must have keyboard inputs with character bindings and the correct keyboard input device enabled. |
| `natkeyboard:post_coded(text)` | Post text with brace-enclosed control codes (see below). |
| `natkeyboard:paste()` | Post host clipboard contents. |
| `natkeyboard:dump()` | Human-readable description of keyboard devices, their state, and character bindings. |

### Recognized brace codes for `post_coded()`

`{BACKSPACE}`, `{BS}`, `{BKSP}`, `{DEL}`, `{DELETE}`, `{END}`, `{ENTER}`, `{ESC}`, `{HOME}`, `{INS}`, `{INSERT}`, `{PGDN}`, `{PGUP}`, `{SPACE}`, `{TAB}`, `{F1}`–`{F12}`, `{QUOTE}`

### Properties

| Property | R/W | Description |
|----------|-----|-------------|
| `natkeyboard.empty` | R | Input buffer is empty |
| `natkeyboard.full` | R | Input buffer is full |
| `natkeyboard.can_post` | R | Emulated system supports posting |
| `natkeyboard.is_posting` | R | Posted data is being delivered |
| `natkeyboard.in_use` | R/W | Enable/disable natural keyboard mode |

## Keyboard Input Device

`manager.machine.natkeyboard.keyboards[tag]`

| Property | R/W | Description |
|----------|-----|-------------|
| `keyboard.tag` | R | Absolute device tag |
| `keyboard.name` | R | Human-readable device type name |
| `keyboard.is_keypad` | R | True if keypad (no keyboard inputs) |
| `keyboard.enabled` | R/W | Whether keyboard/keypad inputs are enabled |

## I/O Port Field (low-level)

`field:set_value(value)` — Sets an I/O port field directly. For digital fields, non-zero activates the field. This is the lower-level API used by the old `autoboot.lua` via `input.set_value()`. Prefer `natkeyboard:post()` for typing.