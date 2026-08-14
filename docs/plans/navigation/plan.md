# Navigation

_See [overview.md](../overview.md) for project context and architecture._

This document records what we know and don't know about the dungeon's layout — walls, doors, holes, ladders — and the open questions that must be answered before any design work begins. Navigation is the prerequisite for sight-gating: knowing what the player sees down a corridor requires knowing the maze.

## Knowns

The maze is a 32×32 grid of cells at 0x05F4–0x09F3, one byte per cell. Each byte packs four 2-bit direction fields — one per side (up / right / down / left, layout `LL_DD_RR_UU`):

| Value | Meaning |
|-------|---------|
| 00 | Open |
| 01 | Normal door |
| 10 | Magic door |
| 11 | Solid wall |

Verified from the disassembly:

- `MakeMazeLevel` (CC9C) generates each level by carving runs of open cells until exactly 500 are open, then adds 70 normal doors and 45 magic doors between adjacent cells (both cells get the door, in opposite directions).
- The generator forbids blocks of four adjacent open cells — the 3D renderer can only draw hallways, so the dungeon has no rooms.
- Holes and ladders are hand-placed per level in a separate table (`currentHoles` 0x0286 → table at CFFD), not encoded in the maze bytes.
- The level-setup routine (`SWI_1A`) zeroes the creature array and rebuilds the maze on every level change.

## Unknowns

- **Cell semantics.** The meaning of any bits beyond the four direction fields, and how a magic door differs from a normal door in play, are not decoded. How to expose magic doors is deferred on the same research, with player-parity as the guide.
- **Line-of-sight extent.** How far the 3D view renders down a corridor under a given light level is not traced — it sets the sight-gate's reach. Deferred to a sandbox/trace. This is a *separate experiment* from the sound module's corridor gate — its own sandbox subfolder.

## Decisions

- **Explored-with-memory.** The observation exposes cells the player has seen (a persistent map), not the full maze. The environment tracks the full maze internally (for line-of-sight and reward). Map memory is reliable — walls don't move — unlike creature memory.
- **Map memory is scaffolding.** Building a map is conceptually the player's (hence the agent's) job; the environment providing it is a training convenience, removed in a later curriculum stage so a recurrent agent maintains its own map.

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/references/game/code.md` | `MakeMazeLevel`, `GetCellPointer`, `IsValidCell`, holes/ladders table |
| `docs/references/game/ram.md` | Memory map — the maze at 0x05F4, `currentHoles` |
| `conversation.md` | The "maze in a byte" and "cell, not room" threads |
