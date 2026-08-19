# State Field Verification

## Goal

Prove the production `state.lua` sampler retrieves the new state fields from the right addresses, with the right byte order, and that the torchPtr dereference actually follows the pointer. Fields under test here: `m0221` (`0x0221`) and the three lit-torch fields (`torch_minutes` / `torch_physical_light` / `torch_magic_light`, read through `torchPtr` `0x0224:0225`). `effective_light` is verified separately in `torch-light/` (it is recomputed by the game, not directly pokable).

## Status

Built and passing.

## Approach

Rather than re-implement the sampler, the plugin `require`s the production `daggorath/state` module unmodified and points its output at a log file (the module's `beginWatching` accepts any file handle with `:write`/`:flush`). The plugin then:

1. Auto-primes the keyboard at frame 300 (demo→live transition).
2. On the first frame of live play (`displayFunction == 0xCE66`), pokes known values into RAM:
   - `torchPtr` → one slot past `nextObjSlot` (a free object slot)
   - torch minutes = 100, physical light = 7, magic light = 3 (at `torchPtr + 6/7/8`)
   - `ambient_light` = physical 1, magic 2 (`0x0226:0x0227`)
   - `m0221` = 0x0A0B (`0x0221:0x0222`)
3. The production sampler reads those values on the following frame and writes tagged records.

The Python server decodes the records with the production `DaggorathState` deserializer and asserts each poked value round-trips.

## Success criteria

- `torch_minutes == 100`, `torch_physical_light == 7`, `torch_magic_light == 3` are observed — the torchPtr dereference reads the right offsets.
- `ambient_light == 0x0102` and `m0221 == 0x000A` are observed — direct addresses and big-endian→little-endian byte order are correct.

The torchPtr-equals-zero case (all three torch fields read 0) is covered by a fresh boot: with no torch lit, `torchPtr == 0` and the fields already report 0 (confirmed in a live sample, not re-run here).

## Running

```bash
python sandbox/state-field-verification/server.py
```
