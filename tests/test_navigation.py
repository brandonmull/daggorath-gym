"""Unit tests for daggorath_gym.navigation — no MAME needed.

The maze fixtures are hand-built 32×32 grids. A cell's byte packs four
2-bit edges (LL_DD_RR_UU), so the tests assemble bytes from the four edge
types and assert the walk follows the facing corridor.
"""

import numpy as np

from daggorath_gym.navigation import (
    DIRECTION_EAST,
    DIRECTION_NORTH,
    DIRECTION_SOUTH,
    DIRECTION_WEST,
    EDGE_MAGIC_DOOR,
    EDGE_NORMAL_DOOR,
    EDGE_OPEN,
    EDGE_WALL,
    decode_edge,
    rewrite_magic_doors,
    walk_corridor,
)


def _make_maze():
    """Build a 32×32 grid of rock (0xFF), ready for carving test corridors."""
    return np.full((32, 32), 0xFF, dtype=np.uint8)


def _cell(north, east, south, west):
    """Pack four edge types into a maze byte (LL_DD_RR_UU)."""
    return (west << 6) | (south << 4) | (east << 2) | north


def _carve_vertical_corridor(maze, x, top_y, bottom_y):
    """Carve a north-south corridor of open cells, walled at the ends."""
    for y in range(top_y, bottom_y + 1):
        north = EDGE_OPEN if y > top_y else EDGE_WALL
        south = EDGE_OPEN if y < bottom_y else EDGE_WALL
        maze[y, x] = _cell(north, EDGE_WALL, south, EDGE_WALL)


# ---- edge decode ------------------------------------------------------------

def test_decode_edge_extracts_four_fields():
    """decode_edge reads each of the four two-bit fields from a byte."""
    maze = _make_maze()
    maze[16, 16] = _cell(EDGE_OPEN, EDGE_MAGIC_DOOR, EDGE_NORMAL_DOOR, EDGE_WALL)
    assert decode_edge(maze, 16, 16, DIRECTION_NORTH) == EDGE_OPEN
    assert decode_edge(maze, 16, 16, DIRECTION_EAST) == EDGE_MAGIC_DOOR
    assert decode_edge(maze, 16, 16, DIRECTION_SOUTH) == EDGE_NORMAL_DOOR
    assert decode_edge(maze, 16, 16, DIRECTION_WEST) == EDGE_WALL


# ---- corridor walk ----------------------------------------------------------

def test_walk_corridor_straight():
    """A straight corridor yields the player's cell and the cells ahead."""
    maze = _make_maze()
    _carve_vertical_corridor(maze, 16, 7, 16)
    visible = walk_corridor(maze, 16, 16, DIRECTION_NORTH, 10)
    assert visible == {(16, y): 16 - y for y in range(7, 17)}


def test_walk_corridor_stops_at_wall():
    """A non-open facing edge stops the walk short of the reach cap."""
    maze = _make_maze()
    _carve_vertical_corridor(maze, 16, 7, 16)
    maze[14, 16] = _cell(EDGE_WALL, EDGE_WALL, EDGE_OPEN, EDGE_WALL)
    visible = walk_corridor(maze, 16, 16, DIRECTION_NORTH, 10)
    assert (16, 14) in visible
    assert (16, 13) not in visible


def test_walk_corridor_lateral_open():
    """An open lateral edge includes the perpendicular neighbor."""
    maze = _make_maze()
    _carve_vertical_corridor(maze, 16, 14, 16)
    maze[16, 16] = _cell(EDGE_OPEN, EDGE_OPEN, EDGE_WALL, EDGE_WALL)
    maze[16, 17] = _cell(EDGE_WALL, EDGE_WALL, EDGE_WALL, EDGE_OPEN)
    visible = walk_corridor(maze, 16, 16, DIRECTION_NORTH, 10)
    assert (17, 16) in visible
    assert visible[(17, 16)] == 0


def test_walk_corridor_lateral_door_blocks():
    """A lateral door or wall does not include the perpendicular neighbor."""
    maze = _make_maze()
    _carve_vertical_corridor(maze, 16, 15, 16)
    maze[16, 16] = _cell(EDGE_OPEN, EDGE_MAGIC_DOOR, EDGE_OPEN, EDGE_WALL)
    visible = walk_corridor(maze, 16, 16, DIRECTION_NORTH, 10)
    assert (17, 16) not in visible


def test_walk_corridor_blackout():
    """Zero physical light sees nothing, even the player's own cell."""
    maze = _make_maze()
    _carve_vertical_corridor(maze, 16, 7, 16)
    assert walk_corridor(maze, 16, 16, DIRECTION_NORTH, 0) == {}


def test_walk_corridor_reach_cap():
    """The walk never exceeds ten cells, whatever the light."""
    maze = _make_maze()
    _carve_vertical_corridor(maze, 16, 0, 16)
    visible = walk_corridor(maze, 16, 16, DIRECTION_NORTH, 255)
    assert len(visible) == 10
    assert max(visible.values()) == 9


# ---- magic-door rewrite -----------------------------------------------------

def test_rewrite_magic_doors():
    """Magic-door fields become walls; the other three fields are untouched."""
    byte = _cell(EDGE_OPEN, EDGE_MAGIC_DOOR, EDGE_NORMAL_DOOR, EDGE_WALL)
    assert rewrite_magic_doors(byte) == _cell(EDGE_OPEN, EDGE_WALL, EDGE_NORMAL_DOOR, EDGE_WALL)


def test_rewrite_magic_doors_no_magic_is_identity():
    """A byte with no magic doors is returned unchanged."""
    byte = _cell(EDGE_OPEN, EDGE_NORMAL_DOOR, EDGE_WALL, EDGE_OPEN)
    assert rewrite_magic_doors(byte) == byte
