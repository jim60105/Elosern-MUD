"""Sample city sample grid data for 聖潔王都 (capital_altoria), map-anchor-grid.

The ``XYMAP_DATA_LIST`` assembly for all settlements lives in
``world/maps/map_data.py`` (settlement-shops design §6.2 / §10); this module
declares only its own ``XYMAP_DATA``.

The layout is a river town that climbed a rock (altoria-capital-replan): the
lower city (Y=0-2) hugs the north bank where the southern road meets the
crossing, the middle belt (Y=3) runs along the line of the wall the city
outgrew, and the upper city (Y=4-6) sits on the terrace above, reached by the
聖階 steps. The pilgrim road runs 南門 → 南大道 → 大道北段 → 中央廣場 → 聖階 →
大神殿前. Twenty-one nodes, twenty-six links, six cycles — deliberately not a
tree: a capital where every route is the only route is a corridor. The two
diagonals are worn shortcuts: apprentices' path from 工匠巷 up to 校場外, and
the pilgrims' slope from 東市 up to 大神殿前.
"""

MAPSTR = r"""
+ 0 1 2 3 4 5 6

6         #
          |
5       #-#-#
        | |
4     #-#-#
     /  | |\
3   #-#-#-#-#-#
      | |
2     #-#
      | |
1   #-#-#-#-#
        |
0       #

+ 0 1 2 3 4 5 6
"""

# Prototypes keyed by (X, Y) coordinate; sync_grid() spawns these through the
# xyzgrid contrib's prototype machinery. Every coordinate except the central
# plaza (3,3) is a plain GridRoom; the plaza is the AnchorRoom that
# ANCHOR_PLACEMENT_REGISTRY["capital_altoria"] points at. Seven nodes are
# walkable scenery with no interior to enter — quayside, ruin, plaza, steps,
# gates, and the road — which the design doc treats as the parts of a capital
# that exist to be moved through and looked at.
PROTOTYPES = {
    (3, 0): {
        "prototype_parent": "grid_room",
        "key": "南門",
        "desc": (
            "The southern gate of 聖潔王都, a wide arch where the pilgrim road "
            "leaves the wilderness and enters the lower city. Everything the "
            "capital grew into began here: a crossing on the river, then a "
            "town, then a capital that climbed the rock behind it."
        ),
    },
    (1, 1): {
        "prototype_parent": "grid_room",
        "key": "碼頭埠",
        "desc": (
            "The quayside of 聖潔王都, where barges from upriver tie off "
            "against stone blackened by centuries of rope. The lower city is "
            "the oldest part of the capital, and this is the oldest part of "
            "the lower city: a river town's working waterfront, loud with "
            "calls, gulls and cargo."
        ),
    },
    (2, 1): {
        "prototype_parent": "grid_room",
        "key": "河岸道",
        "desc": (
            "The riverside road of 聖潔王都, running east from the quayside "
            "along the north bank. Houses lean shoulder to shoulder here — "
            "the ground closest to the water was claimed first and never "
            "gave an inch."
        ),
    },
    (3, 1): {
        "prototype_parent": "grid_room",
        "key": "南大道",
        "desc": (
            "The south main street of 聖潔王都, the first stretch of the "
            "pilgrim road. From the 南門 a traveller walks straight up this "
            "street and finds the whole city unrolling ahead: market, plaza, "
            "steps, cathedral."
        ),
    },
    (4, 1): {
        "prototype_parent": "grid_room",
        "key": "客棧巷",
        "desc": (
            "The inn lane of 聖潔王都. Travellers who reach the capital after "
            "the upper terraces have closed have always slept down here, and "
            "the lane's inns, stables and late taverns serve them on the same "
            "crowded ground."
        ),
    },
    (5, 1): {
        "prototype_parent": "grid_room",
        "key": "浴場前",
        "desc": (
            "The front of the capital's bathhouse, steam and river-water "
            "smell mingling at the curb. A river town got its baths before it "
            "got anything grander, and this one has outlasted every wall the "
            "city has built and outgrown."
        ),
    },
    (2, 2): {
        "prototype_parent": "grid_room",
        "key": "舊城牆遺跡",
        "desc": (
            "The ruins of the old city wall of 聖潔王都. This stub of "
            "foundation is all that stands of the wall that once ringed the "
            "lower city. When the capital outgrew it, the wall came down and "
            "the cleared strip along its line became the widest open ground "
            "the capital has — which is why the market street runs exactly "
            "here. Read the map by this ruin: the belt above it is the grave "
            "the wall became."
        ),
    },
    (3, 2): {
        "prototype_parent": "grid_room",
        "key": "大道北段",
        "desc": (
            "The north section of the pilgrim road, where 南大道 keeps "
            "climbing toward the plaza. It leaves the lower city's crowding "
            "behind along a stretch deliberately kept wide — carts of "
            "offerings and feet of pilgrims have worn the paving smooth."
        ),
    },
    (1, 3): {
        "prototype_parent": "grid_room",
        "key": "工匠巷",
        "desc": (
            "The craft alley of 聖潔王都, at the west end of the old wall "
            "line. The noisy trades were pushed out here when the market took "
            "the belt: hammer-song from the forge, chalk-dust and cloth from "
            "the tailor, and a worn path cut diagonally up toward the drill "
            "yard where apprentices run their wares."
        ),
    },
    (2, 3): {
        "prototype_parent": "grid_room",
        "key": "市場街",
        "desc": (
            "The market street of 聖潔王都, the longest continuous street "
            "of the capital. It is long because it is the cleared line of "
            "the fallen wall — the ruin at its west end explains the street, "
            "and the stalls on it are why the capital's trade flows east."
        ),
    },
    (3, 3): {
        "prototype_parent": "anchor_room",
        "anchor_key": "capital_altoria",
        "key": "中央廣場",
        "desc": (
            "The central plaza of 聖潔王都, the open hinge of the city. The "
            "pilgrim road passes through it, the old wall's market belt "
            "crosses beneath it, and the 聖階 steps rise from its far side to "
            "the upper terraces. Maps of the capital are drawn from this "
            "square, and so, most days, are arguments."
        ),
    },
    (4, 3): {
        "prototype_parent": "grid_room",
        "key": "公會前",
        "desc": (
            "The square before the adventurers' guild of 聖潔王都, one block "
            "east of the plaza on the market belt. Contracts change hands in "
            "the shade of its board before a pen ever moves past the doorsill, "
            "and the guild's carters load hired swords and crates alike here."
        ),
    },
    (5, 3): {
        "prototype_parent": "grid_room",
        "key": "東市",
        "desc": (
            "The east market of 聖潔王都, where the old wall line's trade "
            "meets the road out of the city's east gate. Grain, glass and "
            "foreign coin pass through it, and a worn slope beside it cuts "
            "the corner up to the cathedral for pilgrims who will not walk "
            "the plaza and the steps."
        ),
    },
    (6, 3): {
        "prototype_parent": "grid_room",
        "key": "東門",
        "desc": (
            "The eastern gate of 聖潔王都, at the far end of the market belt "
            "where a road from the east would sensibly meet a river town's "
            "high street. It came late — the wall it stands in is newer than "
            "the ruin west of the plaza — and it is where the capital's "
            "eastern trade, and most of its trouble, arrives."
        ),
    },
    (2, 4): {
        "prototype_parent": "grid_room",
        "key": "校場外",
        "desc": (
            "The drill yard below the upper terraces of 聖潔王都, where the "
            "capital's levies and the guild's escorts learn to stand in "
            "formation. The ground is beaten hard, the officers' voices carry "
            "all the way to the craft alley, and the apprentices' diagonal "
            "up from 工匠巷 wears a green seam across the slope."
        ),
    },
    (3, 4): {
        "prototype_parent": "grid_room",
        "key": "聖階",
        "desc": (
            "The sacred steps of 聖潔王都 — the last stretch of the pilgrim "
            "road and the reason the upper city stays the upper city. Every "
            "king crowned here has widened them, and every penitent who "
            "climbs them on their knees measures the capital's ambition in "
            "stone. Above them the ground that wanted height: church, "
            "academy, palace."
        ),
    },
    (4, 4): {
        "prototype_parent": "grid_room",
        "key": "大神殿前",
        "desc": (
            "The forecourt before the great cathedral of 聖潔王都, facing the "
            "top of the 聖階 dead-on. The Church of Light took this terrace "
            "before the crown took the one above it, and the ordering of the "
            "two is a statement the whole city is built to repeat: God first, "
            "and the crown watching from higher still."
        ),
    },
    (3, 5): {
        "prototype_parent": "grid_room",
        "key": "貴族區前",
        "desc": (
            "The approach to the noble quarter of 聖潔王都, behind and above "
            "the drill yard. The families that held the old lower-city "
            "crossing bought their way up the rock one terrace at a time, and "
            "their gates, lamplighters and leashed dogs show how long the "
            "climb took."
        ),
    },
    (4, 5): {
        "prototype_parent": "grid_room",
        "key": "上城門",
        "desc": (
            "The upper gate of 聖潔王都, set in the wall that encloses the "
            "terrace of institutions. It still has a gatehouse and a "
            "watch oath, though these days it exists mainly so the upper "
            "city can close itself off on feast days — and on the days it "
            "does not wish to be seen by the market belt."
        ),
    },
    (5, 5): {
        "prototype_parent": "grid_room",
        "key": "學院前",
        "desc": (
            "The square before the capital's academy, on the eastern shoulder "
            "of the climb. Students argue on its steps, sellers of ink and "
            "second-hand theses circle them, and the slope down to the east "
            "market is the shortest distance between theory and supper."
        ),
    },
    (4, 6): {
        "prototype_parent": "grid_room",
        "key": "王宮前庭",
        "desc": (
            "The palace forecourt of 聖潔王都, the last node of the climb and "
            "the highest ground in the capital. From here the whole teardrop "
            "of the city lies below: river, quay, fallen wall, market belt, "
            "steps and church — the river town's rock, held by a crown that "
            "made a point of building above the church."
        ),
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
