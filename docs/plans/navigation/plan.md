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
- A cell at depth `N` is drawn — and therefore seen — while `N < light`. The light is two channels: the effective **physical** light (`effective_light_physical`, `m026E`) and the effective **magic** light (`effective_light_magical`, `m026F`). Walls and normal doors gate on the physical channel; magic doors and magical creatures gate on the magic channel.
- So reach is per channel: the corridor walk uses `reach_physical = min(effective_light_physical, 10)`, magic doors and magical creatures use `reach_magic = min(effective_light_magical, 10)`. `effective_light_physical == 0` is pure blackout.

The visible set is the corridor plus its **open lateral neighbors**: at each cell on the walk, the two cells perpendicular to the facing direction are included only when the connecting edge is open (value `00`). A 2-cell-wide hall is seen; a door — normal or magic, both of which block sight — hides what lies beyond it, and a wall (value `11`) does too. This is one step laterally, not a flood-fill.

The `−7` offset in the renderer's dot-frequency math cancels out for the binary seen/not-seen boundary, so only `N < light` matters, not solid-vs-dotted. This lateral rule is the POC approximation; `sandbox/line-of-sight/` remains to confirm the renderer's exact geometry.

## Wire

The maze ships raw in one `M` record: the 1024 bytes at 0x05F4 in address order — row-major, cell (Y, X) at `Y * 32 + X` (per `GetCellPointer` CC7B). No unseen marking on the wire; the record is the ground-truth edge bytes, and Python keeps it internally for line-of-sight and reward.

Holes and ladders ship in one `H` record: the current level's ceiling list then its floor list, each a run of 3-byte entries — type (`0` hole, `1` ladder), Y, X — capped at four per list and sentinel-filled (`0xFF` type marks empty). Lua walks `currentHoles` (`0x0286`), which points at the ceiling list, and treats the list after its `0x80` terminator as the floor list. The record is static per level, so it changes alongside the maze.

The perceived map — the observation's `map` channel — is two planes stacked in one `Box(2, 32, 32)` image: plane 0 the edge bytes, plane 1 the per-cell feature byte derived from the `H` record — `0` none, `1` hole in ceiling, `2` ladder in ceiling, `3` hole in floor, `4` ladder in floor. Cells outside the visible corridor are marked `0xFF` in both planes. Rock (`0xFF`) is never in the visible set — the corridor walk only ever includes floor cells, and a rock cell sits behind a wall edge — so `0xFF` unambiguously means "not currently seen," while `0x00` stays reserved for a genuinely all-open cell. A one-hot per-edge encoding was rejected: the wire is already edge bytes, so plane 0 is a masked copy of the wire.

## Decisions

- **Edge bytes on the wire, `0xFF` marks unseen in perception.** The wire carries the raw edge byte per cell; the perceived map keeps visible cells' edge bytes and marks everything else `0xFF`. Rock is never visible, so the marker cannot collide with a drawn cell, and the all-open byte `0x00` stays a legitimate visible value.
- **Instantaneous visibility, no memory.** The environment reports only the cells visible *now* — the corridor walk's reach — not a persistent explored map. It tracks the full maze internally for line-of-sight and reward, but never accumulates what the player has seen. Map memory is the agent's job, built in a wrapper; walls don't move, so a wrapper's map is reliable — unlike creature memory.
- **True state vs. perceived state.** Navigation decodes the true maze — the bytes are ground truth, held internally for line-of-sight and reward. The visible corridor is perception, and the two diverge only for magic doors: the byte says "magic door" regardless of light, but the player perceives a triangle only under magic light and a wall under a physical-only torch. So the perception exposes the perceived type (light-gated); the true value stays internal.
- **Two light channels, two reaches.** Sight is not one number. The corridor walk gates on the effective physical light (`effective_light_physical`, `m026E`) with reach `min(effective_light_physical, 10)`; magic doors and magical creatures gate on the effective magic light (`effective_light_magical`, `m026F`) with reach `min(effective_light_magical, 10)`. `effective_light_physical == 0` is the blackout.
- **Magic doors are a distinct edge value, rewritten in perception.** The edge byte already distinguishes normal (01) from magic (10) doors, so the wire and the true map need nothing. The perceived map rewrites a magic-door edge to wall (11) when the door is beyond the magic reach (under a physical-only torch a magic door reads as a wall), and reports it as a magic door (10) otherwise.
- **The static trace is the POC rule.** The corridor walk, `N < light`, and the one-step open lateral neighbor are accepted as the sight approximation; `sandbox/line-of-sight/` stays deferred. Cheating a little around corners is acceptable for the POC.
- **Direction convention follows the disassembly.** `at_heading` uses the maze's direction numbering — 0 = Up (North), 1 = Right (East), 2 = Down (South), 3 = Left (West) — matching the `CDA6` bit-position table.
- **Holes and ladders are a second plane of the map image, not a separate channel.** They are static per-level geometry (the `currentHoles` table, `0x0286` → `CFFD`), not edge-encoded, so they ride a per-cell feature byte — 0 none, 1 hole in ceiling, 2 ladder in ceiling, 3 hole in floor, 4 ladder in floor — stacked beside the edge bytes as plane 1 of one `Box(2, 32, 32)` image, gated by the same corridor walk, `0xFF` unseen. Co-locating them with the edges keeps a ladder spatially aligned with the walls the CNN already sees; a separate Dict key would force the MLP to learn that correspondence with no spatial bias. They ship as the `H` record (see Wire).

## Implementation

Navigation lives in a pure-Python module, `daggorath_gym/navigation.py`, alongside `screen.py` and `state.py` — no MAME dependency. It consumes the decoded maze (the `(32, 32)` uint8 grid) and the player's frame, and returns what the player sees.

The edge type values are `EDGE_OPEN` (0), `EDGE_NORMAL_DOOR` (1), `EDGE_MAGIC_DOOR` (2), and `EDGE_WALL` (3). The four directions are `DIRECTION_NORTH` (0), `DIRECTION_EAST` (1), `DIRECTION_SOUTH` (2), and `DIRECTION_WEST` (3) — the maze's own numbering. `REACH_CAP` (10) is the renderer's ten-cell walk bound.

Two functions:

decode_edge(maze, x, y, direction)
    → returns the edge type out of cell (x, y) in the given direction
    → shifts the cell's byte by twice the direction number and masks two bits

walk_corridor(maze, x, y, heading, physical_light)
    → walks the facing corridor from the player's cell, depth 0 outward
    → at each cell, records it and each open lateral neighbor at that depth
    → stops at the first facing edge that is not open
    → caps the walk at min(physical_light, 10) cells
    → returns a dict mapping each visible cell to its depth
    → returns an empty dict when physical_light is 0 (blackout)

## Reference Documents

| Document | What It Contains |
|----------|-----------------|
| `docs/references/game/code.md` | `MakeMazeLevel`, `GetCellPointer`, `IsValidCell`, holes/ladders table |
| `docs/references/game/ram.md` | Memory map — the maze at 0x05F4, `currentHoles` |
| `docs/references/game/levels.md` | The published per-level maps — the decoder's validation fixture |
| `conversation.md` | The "maze in a byte" and "cell, not room" threads |
