"""Grid map data for 暗影谷村 (village_ciaran), map-anchor-grid.

A six-node tree rather than a grid: one concealed entrance, one gathering
plaza, and four dwelling approaches. The capital is a thirteen-node cross;
a village of a hundred people copying that shape would read as a small town,
so this settlement deliberately carries no crossroads (settlement-shops
design §6.2, ciaran-village-map D2).
"""

MAPSTR = r"""
+ 0 1 2

2   #-#
    |
1 #-#-#
    |
0   #

+ 0 1 2
"""

# Prototypes keyed by (X, Y) coordinate; sync_grid() spawns these through the
# xyzgrid contrib's prototype machinery. Every coordinate except the village
# plaza (1,1) is a plain GridRoom; the plaza is the AnchorRoom that
# ANCHOR_PLACEMENT_REGISTRY["village_ciaran"] points at. 隱密小徑 is the way
# in from 虛境 and the return point from the wilderness: elven villages have
# no walls and no gates, so it reads as a concealed path through the forest,
# not as a city gate (even though it occupies the CITY_GATE_REGISTRY slot).
PROTOTYPES = {
    (0, 1): {
        "prototype_parent": "grid_room",
        "key": "隱密小徑",
        "desc": "A path almost hidden under vines and fallen leaves, showing "
        "only to those who know this stretch of forest.",
    },
    (1, 1): {
        "prototype_parent": "anchor_room",
        "anchor_key": "village_ciaran",
        "key": "村中廣場",
        "desc": "The village clearing, ringed by old trees around a patch of "
        "trodden earth where the villagers gather to talk and share the day's news.",
    },
    (2, 1): {
        "prototype_parent": "grid_room",
        "key": "練刀場",
        "desc": "A clearing of earth worn smooth by countless feet, the "
        "surrounding trunks scarred by practice cuts — the young blade-dancers "
        "of the village train here from dawn to dusk.",
    },
    (1, 0): {
        "prototype_parent": "grid_room",
        "key": "溪畔小徑",
        "desc": "A dirt path winding along a murmuring stream; flat stones by "
        "the water offer a place to sit and rest.",
    },
    (1, 2): {
        "prototype_parent": "grid_room",
        "key": "村北古樹下",
        "desc": "Beneath the great old tree north of the village, its canopy "
        "spreading like a roof; roots cradle stone seats where children gather "
        "to hear stories.",
    },
    (2, 2): {
        "prototype_parent": "grid_room",
        "key": "織房坡",
        "desc": "A gentle slope toward dwellings half-hidden among the trees, "
        "freshly dyed cloth hanging on lines, the wind carrying the scent of "
        "herb dyes.",
    },
}

XYMAP_DATA = {
    "zcoord": "village_ciaran",
    "map": MAPSTR,
    "options": {
        # map-knowledge-minimap: same closed visual-range options the capital
        # uses, consumed by the grid layer adapter. Adding these SHALL NOT
        # change topology or connectivity.
        "map_visual_range": 2,
        "map_mode": "nodes",
    },
    "prototypes": {
        **PROTOTYPES,
        # map-movement-clock: every intra-village link spawns as
        # CostedXYZExit so grid steps charge the ordinary move cost,
        # exactly as movement inside the capital does.
        ("*", "*", "*"): {
            "prototype_parent": "xyz_exit",
            "typeclass": "typeclasses.exits.CostedXYZExit",
        },
    },
}