"""Sample city sample grid data for 聖潔王都 (capital_altoria), map-anchor-grid."""

MAPSTR = r"""
+ 0 1 2 3 4

4     #
      |
3   #-#-#
      |
2 #-#-#-#-#
      |
1   #-#-#
      |
0     #

+ 0 1 2 3 4
"""

# Prototypes keyed by (X, Y) coordinate; sync_grid() spawns these through the
# xyzgrid contrib's prototype machinery. Every coordinate except the central
# plaza (2,2) is a plain GridRoom; the plaza is the AnchorRoom that
# ANCHOR_PLACEMENT_REGISTRY["capital_altoria"] points at.
PROTOTYPES = {
    (2, 0): {
        "prototype_parent": "grid_room",
        "key": "南門",
        "desc": "The southern gate of 聖潔王都, a wide arch under the city wall.",
    },
    (2, 1): {
        "prototype_parent": "grid_room",
        "key": "南大道",
        "desc": "The south main street of 聖潔王都, lined with shops and stalls.",
    },
    (1, 1): {
        "prototype_parent": "grid_room",
        "key": "旅店外",
        "desc": "The exterior of a bustling inn on 南大道.",
    },
    (3, 1): {
        "prototype_parent": "grid_room",
        "key": "冒險者公會外",
        "desc": "The exterior of the adventurers' guild hall, its banner snapping in the wind.",
    },
    (2, 2): {
        "prototype_parent": "anchor_room",
        "anchor_key": "capital_altoria",
        "key": "中央廣場",
        "desc": "The central plaza of 聖潔王都, open to the sky at the heart of the city.",
    },
    (0, 2): {
        "prototype_parent": "grid_room",
        "key": "鐵匠鋪外",
        "desc": "The exterior of a blacksmith's forge, with a heavy anvil visible within.",
    },
    (1, 2): {
        "prototype_parent": "grid_room",
        "key": "市場街",
        "desc": "Market Street, crowded with vendors between 中央廣場 and the west wall.",
    },
    (3, 2): {
        "prototype_parent": "grid_room",
        "key": "神殿街",
        "desc": "Temple Street, quieter than the market, leading east toward the temple.",
    },
    (4, 2): {
        "prototype_parent": "grid_room",
        "key": "光明神殿外",
        "desc": "The exterior of the Temple of Light, its marble steps rising to the doors.",
    },
    (2, 3): {
        "prototype_parent": "grid_room",
        "key": "北大道",
        "desc": "The north main street of 聖潔王都, broad and stately.",
    },
    (1, 3): {
        "prototype_parent": "grid_room",
        "key": "貴族區門口",
        "desc": "The gate of the noble quarter, guarded and closed to common traffic.",
    },
    (3, 3): {
        "prototype_parent": "grid_room",
        "key": "城牆哨塔",
        "desc": "A watchtower on the city wall, overlooking the rooftops.",
    },
    (2, 4): {
        "prototype_parent": "grid_room",
        "key": "北門",
        "desc": "The northern gate of 聖潔王都, currently shut tight against the wilds.",
    },
}

XYMAP_DATA = {
    "zcoord": "capital_altoria",
    "map": MAPSTR,
    "options": {
        # map-knowledge-minimap: the closed visual-range options the xyzgrid
        # contrib's own get_visual_range accepts, consumed by the grid layer
        # adapter. Adding these SHALL NOT change topology or connectivity.
        "map_visual_range": 2,
        "map_mode": "nodes",
    },
    "prototypes": {
        **PROTOTYPES,
        # map-movement-clock: every intra-city link spawns as CostedXYZExit so
        # grid steps charge the ordinary move cost (movement-cost-charging).
        ("*", "*", "*"): {
            "prototype_parent": "xyz_exit",
            "typeclass": "typeclasses.exits.CostedXYZExit",
        },
    },
}

XYMAP_DATA_LIST = [XYMAP_DATA]