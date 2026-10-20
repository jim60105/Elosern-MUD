"""One loaded synthetic xyzgrid map for the room-look behavior tests.

Every identifier and prose value is invented with the reserved ``t_`` prefix
(test-data gate), so no test using this map names shipped content. The map
declares only the closed visual-range options the grid layer adapter consumes
and deliberately carries no text-map display override: the room typeclass
default is the only gate under test.
"""

from evennia.contrib.grid.xyzgrid.xyzgrid import get_xyzgrid

# Map identity and coordinates read as data, never as shipped place names.
Z_MAP_KEY = "t_probe_grid"
START_XYZ = (0, 0, Z_MAP_KEY)
ANCHOR_XYZ = (1, 0, Z_MAP_KEY)
END_XYZ = (2, 0, Z_MAP_KEY)

START_KEY = "測試石板街"
ANCHOR_KEY = "測試小廣場"
END_KEY = "測試鐘樓前"

START_DESC = "一條鋪著石板的測試街道。"
ANCHOR_DESC = "一座測試廣場，中央有一盞路燈。"
END_DESC = "測試鐘樓前的空地。"

# Three connected nodes: a plain grid room, an anchor room, and a second grid
# room, so the east-east route is an independently known two-step walk.
MAPSTR = r"""
+ 0 1 2

0 #-#-#

+ 0 1 2
"""

_PROTOTYPES = {
    (0, 0): {
        "prototype_parent": "grid_room",
        "key": START_KEY,
        "desc": START_DESC,
    },
    (1, 0): {
        "prototype_parent": "anchor_room",
        "key": ANCHOR_KEY,
        "desc": ANCHOR_DESC,
    },
    (2, 0): {
        "prototype_parent": "grid_room",
        "key": END_KEY,
        "desc": END_DESC,
    },
    # Every intra-map link charges the ordinary move cost, mirroring the
    # shipped maps' own exit override.
    ("*", "*", "*"): {
        "prototype_parent": "xyz_exit",
        "typeclass": "typeclasses.exits.CostedXYZExit",
    },
}

MAP_DATA = {
    "zcoord": Z_MAP_KEY,
    "map": MAPSTR,
    "options": {
        "map_visual_range": 1,
        "map_mode": "nodes",
    },
    "prototypes": _PROTOTYPES,
}


def load_synthetic_grid():
    """Add, reload and spawn the synthetic map; return the live ``XYGrid``."""
    grid = get_xyzgrid()
    grid.add_maps(dict(MAP_DATA))
    grid.reload()
    grid.spawn(xyz=("*", "*", Z_MAP_KEY))
    return grid


def synthetic_rooms():
    """Return the ``(start, anchor, end)`` rooms of the loaded synthetic map."""
    from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom

    start = XYZRoom.objects.get_xyz(xyz=START_XYZ)
    anchor = XYZRoom.objects.get_xyz(xyz=ANCHOR_XYZ)
    end = XYZRoom.objects.get_xyz(xyz=END_XYZ)
    return start, anchor, end
