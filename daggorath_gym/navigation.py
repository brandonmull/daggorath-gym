"""Maze navigation — edge decode and the line-of-sight corridor walk.

Pure Python, no MAME dependency. Consumes the decoded maze (a (32, 32)
uint8 grid of edge bytes) and the player's frame, and returns the cells the
player currently sees. The walk mirrors the 3D renderer: it follows the
facing corridor, stopping at the first non-open edge, and includes the open
lateral neighbor at each cell — one step laterally, not a flood-fill.
"""

import numpy as np

# Edge type values — two bits per direction packed into one maze byte.
EDGE_OPEN = 0
EDGE_NORMAL_DOOR = 1
EDGE_MAGIC_DOOR = 2
EDGE_WALL = 3

# Direction numbers, the maze's own convention: 0 = North (up), 1 = East
# (right), 2 = South (down), 3 = West (left), per the CDA6 bit-position table.
DIRECTION_NORTH = 0
DIRECTION_EAST = 1
DIRECTION_SOUTH = 2
DIRECTION_WEST = 3

# The renderer walks at most ten cells (depths 0 through 9).
REACH_CAP = 10

# Per-direction step deltas, indexed by the direction number.
_DIRECTION_DX = (0, 1, 0, -1)
_DIRECTION_DY = (-1, 0, 1, 0)


def decode_edge(maze: np.ndarray, x: int, y: int, direction: int) -> int:
    """Return the edge type from cell (x, y) toward the given direction."""
    return (int(maze[y, x]) >> (direction * 2)) & 0x03


def walk_corridor(
    maze: np.ndarray, x: int, y: int, heading: int, physical_light: int
) -> dict[tuple[int, int], int]:
    """Return the cells visible now, as a dict mapping (x, y) to depth.

    Walks the facing corridor from the player's cell out to
    ``min(physical_light, 10)`` cells, stopping at the first facing edge that
    is not open. At each cell on the walk, the cell itself and its open
    lateral neighbors (perpendicular to the facing direction) are included at
    that cell's depth. A ``physical_light`` of 0 returns an empty dict — pure
    blackout, where even the player's own cell vanishes.
    """
    visible = {}
    reach = min(physical_light, REACH_CAP)
    if reach <= 0:
        return visible

    left = (heading - 1) % 4
    right = (heading + 1) % 4

    for depth in range(reach):
        visible[(x, y)] = depth
        for lateral in (left, right):
            if decode_edge(maze, x, y, lateral) == EDGE_OPEN:
                lateral_x = x + _DIRECTION_DX[lateral]
                lateral_y = y + _DIRECTION_DY[lateral]
                visible[(lateral_x, lateral_y)] = depth
        if decode_edge(maze, x, y, heading) != EDGE_OPEN:
            break
        x += _DIRECTION_DX[heading]
        y += _DIRECTION_DY[heading]

    return visible


def rewrite_magic_doors(byte: int) -> int:
    """Rewrite every magic-door 2-bit edge field in a maze byte to wall.

    Magic doors draw as walls under a physical-only torch; the perception
    applies this rewrite to a cell's edge byte once its depth reaches the
    magic-light reach. Normal doors and open edges are left untouched.
    """
    rewritten = byte
    for direction in range(4):
        shift = direction * 2
        if ((byte >> shift) & 0x03) == EDGE_MAGIC_DOOR:
            rewritten = (rewritten & ~(0x03 << shift)) | (EDGE_WALL << shift)
    return rewritten
