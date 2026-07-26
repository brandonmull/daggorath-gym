# TCP Socket Sandbox (emu.file edition)

Python ↔ MAME Lua bidirectional TCP communication using MAME's built-in `emu.file` socket API. Zero external Lua dependencies.

## Quick Start

```bash
env/bin/python3 sandbox/server.py
```

Game loads, socket connects, pings flow, actions flow back.

## Architecture

```
                    ┌─────────────────────────┐
                    │         MAME             │
                    │                          │
                    │  client.lua              │
                    │  ┌──────────────────┐    │
                    │  │ emu.file("w")    │─────── Port 15000 ───→ server.py (read state)
                    │  │ emu.file("r")    │←─── Port 15001 ──── server.py (send actions)
                    │  │ frame_notifier   │    │
                    │  └──────────────────┘    │
                    └─────────────────────────┘
```

- Python binds TCP servers on both ports **before** launching MAME
- Lua connects to both as a client via `emu.file`
- `emu.add_machine_frame_notifier` drives emulation while handling both sockets

## emu.file Socket Modes

MAME's built-in `emu.file` API provides TCP socket access. Mode string determines behavior:

| Mode | Result | Notes |
|------|--------|-------|
| `emu.file("w")` | ✅ Stable | Write-only. MAME → Python game state. |
| `emu.file("r")` | ✅ Stable | Read-only. Python → MAME action commands. |
| `emu.file("rw")` | ❌ Broken | Read/write. Corrupts emulator every time — black screen, looping audio. Not a timing issue. |
| `emu.file("rwc")` | ❌ Broken | `"c"` (create) flag is for files only. Hangs or fails silently on sockets. |

**Key insight:** `emu.file` sockets must be single-direction. Use separate sockets for read and write.

## Files

| File | Purpose |
|------|---------|
| `server.py` | Orchestrator: binds ports 15000+15001, launches MAME, reads state, sends actions |
| `client.lua` | MAME script: `emu.file("w")` on 15000 + `emu.file("r")` on 15001, frame notifier |
| `mame-lua-chat.md` | Original AI discussion about emu.file (some advice proven wrong for this MAME build) |

## Protocol

| Port | Direction | Format |
|------|-----------|--------|
| 15000 | MAME → Python | Newline-delimited JSON (`{"event":"ping","count":N}`) |
| 15001 | Python → MAME | Newline-delimited JSON (`{"action":"ATTACK"}`) |

## MAME CLI Flags

| Flag | Purpose |
|------|---------|
| `-autoboot_script <path>` | Lua script to run after boot; use absolute paths |
| `-autoboot_delay <n>` | Seconds to wait before running script (ignored in this MAME build) |
| `-skip_gameinfo` | Skips the "press any key" nag screen |
| `-nonvram_save` | Prevents corrupted state from persisting between runs (boolean flag, NOT `-nvram_save 0`) |
| `-window` | Run in a window (required for WSLg) |
| `-sound sdl` | SDL audio backend — best quality on WSLg |
| `-sound pulse` | PulseAudio backend — works with WSLg but more jitter than SDL |
| `-sound none` | No audio — use for headless RL training |

## Audio on WSLg

- WSLg provides PulseAudio at `/mnt/wslg/PulseServer` — no extra packages needed
- Upgrade SDL2 for best audio: `sudo apt install --only-upgrade libsdl2-2.0-0`
- Update WSL: `wsl --update` (from Windows PowerShell as Administrator)
- Some audio jitter on certain synthesized sounds is a WSLg limitation — confirmed present even without any Lua script
- ALSA is absent on WSL (`/dev/snd` doesn't exist) — don't use `-sound alsa`

## NVRAM / Persistent State

MAME saves emulated machine state to `~/.mame/nvram/` between sessions. Corrupted state persists across reboots.

- `-nonvram_save` prevents NVRAM writes (boolean flag, not `-nvram_save 0`)
- Manual clear: `rm -rf ~/.mame/nvram/coco3/*`

## Lua API Notes

- `emu.add_machine_frame_notifier(callback)` — fires every emulated frame. Use this instead of `emu.register_frame` (deprecated) or `emu.register_periodic` (blocks game)
- `emu.wait(seconds)` — unreliable in this MAME build; use frame counting for delays
- `emu.file:open()` returns `nil` on success, error string on failure (inverted from luasocket convention)
- `sock:write()` with no connected client crashes MAME — wrap in `pcall()`

## Python-Side Notes

- Python must be the TCP server (bind before MAME launches) — `emu.file` connects as a client
- `server_sock.settimeout(N)` prevents hanging forever if MAME fails to connect
- Use absolute paths for `-rompath`, `-hashpath`, `-autoboot_script`
- Use `env/bin/python3` (project virtual environment, even though sandbox uses only stdlib)

## Troubleshooting

**"Address already in use"**
```bash
ss -tlnp | grep 15000 && pkill -f "sandbox/server.py"
```

**Game stuck / black screen**
```bash
rm -rf ~/.mame/nvram/coco3/*
```

**MAME can't find Lua script**
```bash
# Verify absolute path in server.py autoboot_script resolves correctly
ls -la /mnt/c/Users/brand/Projects/Daggorath/sandbox/client.lua
```

**No audio / audio jitter**
```bash
sudo apt install --only-upgrade libsdl2-2.0-0
# Then from Windows PowerShell (admin): wsl --update
```

## Ports

| Port | Purpose |
|------|---------|
| 15000 | Game state (MAME → Python) |
| 15001 | Action commands (Python → MAME) |