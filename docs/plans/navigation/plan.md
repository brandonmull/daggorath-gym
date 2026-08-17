# Navigation

_See [overview.md](../overview.md) for project context and architecture._

This document records what we know and don't know about the dungeon's layout — walls, doors, holes, ladders — and the open questions that must be answered before any design work begins. Navigation is the prerequisite for sight-gating: knowing what the player sees down a corridor requires knowing the maze.

## Knowns

The maze is a 32×32 grid of cells at 0x05F4–0x09F3, one byte per cell. Each cell is either null (rock — byte `FF`, unenterable) or floor (non-`FF`, enterable). A floor cell's byte packs its four edges as four 2-bit fields. The field's position selects the edge; its value is the edge type:

| Bits | Edge |
|------|------|
| 7–6 | West |
| 5–4 | South |
| 3–2 | East |
| 1–0 | North |

| Value | Edge type |
|-------|-----------|
| 00 | Open |
| 01 | Normal door |
| 10 | Magic door |
| 11 | Wall |

Verified from the disassembly:

- `MakeMazeLevel` (CC9C) generates each level by carving runs of open cells until exactly 500 are open, then adds 70 normal doors and 45 magic doors between adjacent cells (both cells get the door, in opposite directions).
- The generator forbids blocks of four adjacent open cells — the 3D renderer can only draw hallways, so the dungeon has no rooms.
- Holes and ladders are hand-placed per level in a separate table (`currentHoles` 0x0286 → table at CFFD), not encoded in the maze bytes. Each entry is a type plus a cell coordinate — a hole goes down only, a ladder goes up and down — and a cell holds at most one.
- The level-setup routine (`SWI_1A`) zeroes the creature array and rebuilds the maze on every level change.
- The four edge fields consume the whole byte — there are no bits beyond the four edges. A null cell is just a cell whose four edges are all wall (`FF`).
- Doors never open. The maze bytes are written only by `MakeMazeLevel`; movement (`MoveCheckWall` D720 → D136) rejects only a step into a null (`FF`) cell, so a normal door and a magic door are both always passable.
- Both door kinds block sight — the corridor walk (`CF24`) stops at any non-open facing edge, so normal door, magic door, and wall occlude alike.
- Normal and magic doors differ only in rendering. A normal door draws a rectangle on the physical-light channel, visible in any light. A magic door draws a triangle on the magic-light channel (`m0275` → `SWI_0` reads `m026F`) plus the wall behind it, so under a physical-only torch (Pine, magic light 0) it looks like a wall yet is passable, and under magic light (Lunar 4 / Solar 11) it shows as a triangle.

## Unknowns

- **Line-of-sight extent.** How far the 3D view renders down a corridor under a given light level is not traced — it sets the sight-gate's reach. Deferred to a sandbox/trace. This is a *separate experiment* from the sound module's corridor gate — its own sandbox subfolder.

## Decisions

- **Explored-with-memory.** The observation exposes cells the player has seen (a persistent map), not the full maze. The environment tracks the full maze internally (for line-of-sight and reward). Map memory is reliable — walls don't move — unlike creature memory.
- **Map memory is scaffolding.** Building a map is conceptually the player's (hence the agent's) job; the environment providing it is a training convenience, removed in a later curriculum stage so a recurrent agent maintains its own map.
- **True state vs. perceived state.** Navigation decodes the true maze — the bytes are ground truth, held internally for line-of-sight and reward. The explored map is perception, and the two diverge only for magic doors: the byte says "magic door" regardless of light, but the player perceives a triangle only under magic light and a wall under a physical-only torch. So the map exposes the perceived type (light-gated); the true value stays internal.

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/references/game/code.md` | `MakeMazeLevel`, `GetCellPointer`, `IsValidCell`, holes/ladders table |
| `docs/references/game/ram.md` | Memory map — the maze at 0x05F4, `currentHoles` |
| `docs/references/game/levels.md` | The published per-level maps — the decoder's validation fixture |
| `conversation.md` | The "maze in a byte" and "cell, not room" threads |
