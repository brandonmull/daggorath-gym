# Torch Light

## Goal

Verify the torch ↔ light relationship end-to-end by *playing* the torch commands through the real command channel — `PULL LEFT TORCH` (take the Pine torch from the backpack), then `USE LEFT` (light it) — and checking that the torch and light RAM fields update as the game's own tables prescribe.

## Status

Built and passing.

## Approach

No RAM poking and no new Lua plugin: the driver uses the production `MameOperator` (command socket + state FIFO + screen decode) exactly as the agent will.

1. Boot to live play; record the initial state (torch fields all 0 — no lit torch).
2. Send `PULL LEFT TORCH`; read the command-area text until the echo appears (confirms the command was typed and accepted).
3. Send `USE LEFT`; read until `torch_minutes` goes non-zero (confirms the torch lit).
4. Read until `effective_light` reaches its recomputed value, then assert.

The player always starts with a Pine torch in the backpack (grammar: "a backpack containing a PINE TORCH and a WOODEN SWORD"), so the procedure is deterministic.

## Expected values (Pine torch, ROM `ObjectSpecial` @ `DA84: 0F 0F 07 00`)

| Field | Before | After USE |
|---|---|---|
| `torch_minutes` | 0 | 15 (14 if a minute ticked) |
| `torch_physical_light` | 0 | 7 |
| `torch_magic_light` | 0 | 0 |
| `effective_light` | 0x0000 | 0x0700 (ambient 0 + physical 7, magic 0) |
| `ambient_light` | 0 | 0 |

`torchPtr` is not a schema field; the three torch fields leaving 0 is the proof the sampler followed the now-non-zero `torchPtr` to the lit torch object.

## Success criteria

- The command area echoes `PULL LEFT TORCH` and `USE LEFT` (no `???`).
- After `USE LEFT`, `torch_minutes`, `torch_physical_light`, and `torch_magic_light` match the Pine torch values, and `effective_light` rises to `0x0700`.

## Running

```bash
python sandbox/torch-light/server.py
```
