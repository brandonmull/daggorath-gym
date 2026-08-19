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

## Line-of-sight

The sight-gate's reach is a corridor walk mirroring the 3D renderer (`NormalDisplay`, `CE66`):

- The renderer walks the **facing corridor** from the player's cell, depths `0…9`, stopping at the first facing edge that isn't open (normal door, magic door, and wall all occlude alike).
- A cell at depth `N` is drawn — and therefore seen — while `N < light`, where `light` is the effective light level `effective_light` (`m026E:m026F`).
- So reach = `min(light, 10)`, and `light == 0` means nothing is visible — pure blackout.

The visible set is the corridor plus its **open lateral neighbors**: at each cell on the walk, the two cells perpendicular to the facing direction are included only when the connecting edge is open (value `00`). A 2-cell-wide hall is seen; a door — normal or magic, both of which block sight — hides what lies beyond it, and a wall (value `11`) does too. This is one step laterally, not a flood-fill.

The `−7` offset in the renderer's dot-frequency math cancels out for the binary seen/not-seen boundary, so only `N < light` matters, not solid-vs-dotted. This lateral rule is the POC approximation; `sandbox/line-of-sight/` remains to confirm the renderer's exact geometry.

## Decisions

- **Instantaneous visibility, no memory.** The environment reports only the cells visible *now* — the corridor walk's reach — not a persistent explored map. It tracks the full maze internally for line-of-sight and reward, but never accumulates what the player has seen. Map memory is the agent's job, built in a wrapper; walls don't move, so a wrapper's map is reliable — unlike creature memory.
- **True state vs. perceived state.** Navigation decodes the true maze — the bytes are ground truth, held internally for line-of-sight and reward. The visible corridor is perception, and the two diverge only for magic doors: the byte says "magic door" regardless of light, but the player perceives a triangle only under magic light and a wall under a physical-only torch. So the perception exposes the perceived type (light-gated); the true value stays internal.

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/references/game/code.md` | `MakeMazeLevel`, `GetCellPointer`, `IsValidCell`, holes/ladders table |
| `docs/references/game/ram.md` | Memory map — the maze at 0x05F4, `currentHoles` |
| `docs/references/game/levels.md` | The published per-level maps — the decoder's validation fixture |
| `conversation.md` | The "maze in a byte" and "cell, not room" threads |
