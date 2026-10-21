"""Settlement data for 暗影谷村 (village_ciaran), map-anchor-grid.

This module is the village's sparse declaration: stable node identities, their
authored integer-metre local coordinates (world-map-scale design §9),
explicit roads and the room prototypes the synchronizer applies. There is no
ASCII map: the metre coordinates are the single authored geometry.

A ten-node tree rather than a grid: one concealed entrance, one gathering
plaza, and eight further exterior nodes. The capital is a three-terrace city;
a village of a hundred people copying that shape would read as a small town,
so this settlement deliberately carries no crossroads (settlement-shops
design §6.2, ciaran-village-map D2) — and, as it grows, growth adds leaves
and short branches, never a loop. Each newer node extends something already
there rather than opening new ground: 銀葉坡 is further up the weaving
slope, 藥草園 past the training ground where cleared sun reaches, 長老古樹下
deeper into the north grove, 溪畔下游 further along the stream.
"""

# Prototypes keyed by the node's (X, Y) integer-metre local coordinate;
# sync_grid() applies these through the prototype machinery. Every coordinate
# except the village plaza (220, 305) is a plain GridRoom; the plaza is the
# AnchorRoom that
# ANCHOR_PLACEMENT_REGISTRY["village_ciaran"] points at. 隱密小徑 is the way
# in from 虛境 and the return point from the wilderness: elven villages have
# no walls and no gates, so it reads as a concealed path through the forest,
# not as a city gate (even though it occupies the CITY_GATE_REGISTRY slot).
# The four nodes added by ciaran-village-crafts keep their own meter
# coordinates, so none of the four landed homes' exteriors moved. 長老古樹下
# and 溪畔下游 are walkable scenery: the commons change fills the elder's
# grove; the stream bend stays scenery.
PROTOTYPES = {
    (35, 270): {
        "prototype_parent": "grid_room",
        "key": "隱密小徑",
        "desc": "藤蔓與落葉幾乎掩住了這條小徑；不認得這片林子的人，縱使走進去也看不出來。",
    },
    (220, 305): {
        "prototype_parent": "anchor_room",
        "anchor_key": "village_ciaran",
        "key": "村中廣場",
        "desc": "村裡的空地，老樹繞著一塊被腳步踩實的泥地。族人聚集在這裡交談，"
        "交換一天的見聞。",
    },
    (405, 335): {
        "prototype_parent": "grid_room",
        "key": "練刀場",
        "desc": "無數腳步踩硬的空地，四周樹幹佈滿練習留下的刀痕——"
        "村中的少年刀舞者從清晨練到日暮，練的就是這裡。",
    },
    (245, 135): {
        "prototype_parent": "grid_room",
        "key": "溪畔小徑",
        "desc": "沿著潺潺溪流蜿蜒的土路，水邊幾塊平坦的石盤，正好讓人坐下歇腳。",
    },
    (200, 465): {
        "prototype_parent": "grid_room",
        "key": "村北古樹下",
        "desc": "村北古樹之下，樹冠如屋簷般撐開；盤根間嵌著磨平的石座，"
        "孩子們聚在這裡聽長者說故事。",
    },
    (390, 495): {
        "prototype_parent": "grid_room",
        "key": "織房坡",
        "desc": "通往林中住屋的緩坡，新染的布掛在繩上晾乾，風裡帶著植物染料的氣味。",
    },
    (165, 650): {
        "prototype_parent": "grid_room",
        "key": "長老古樹下",
        "desc": "再往北，林子更老。最老的那株巨樹寬得數人合抱，盤根之間有磨平的坐石；"
        "族裡老一輩的決定，多在這棵樹下說出口。平日這裡安靜，只餘風穿過樹冠的聲音。",
    },
    (440, 665): {
        "prototype_parent": "grid_room",
        "key": "銀葉坡",
        "desc": "織房坡再往上，坡頂長著一叢銀葉樹，葉背在午後的光裡泛著細碎銀光。"
        "樹下曬著幾件完成的花邊與綴飾，綴著貝殼和磨圓的晶砂。",
    },
    (590, 300): {
        "prototype_parent": "grid_room",
        "key": "藥草園",
        "desc": "練刀場東邊，樹冠開處漏下整片陽光。矮石壘成的畦邊圈著一株株藥草與香草，"
        "空氣裡是苦味與清甜交錯的氣息。",
    },
    (430, 85): {
        "prototype_parent": "grid_room",
        "key": "溪畔下游",
        "desc": "溪流出了村子便寬了、緩了，水色轉深。下游有一片族人清洗染具的淺灘，"
        "石上還留著乾涸的藍色水痕；走到這裡的人多半只為坐一坐，聽水聲。",
    },
}

# The sparse map declaration; ``map_data.py`` builds the authoritative graph
# from these tables. No ASCII ``map`` key exists: a metre lattice is never
# allocated (world-map-scale §11).
XYMAP_DATA = {
    "zcoord": "village_ciaran",
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

# Stable authored identity per coordinate (implement-sparse-settlement-graphs).
# Same contract as the capital's ``NODE_IDS``: the identity, not the
# coordinate, is the synchronizer's matching authority.
NODE_IDS = {
    (245, 135): "stream_path",
    (430, 85): "stream_bend",
    (35, 270): "hidden_path",
    (220, 305): "village_plaza",
    (405, 335): "training_clearing",
    (590, 300): "herb_garden",
    (200, 465): "old_tree_north",
    (390, 495): "weaving_slope",
    (165, 650): "elder_tree",
    (440, 665): "silver_leaf_slope",
}

# (source identity, destination identity, compass octant), one directed road
# per travel direction. The octant is authored because the irregular metre
# layout is almost never axis-aligned.
ROADS = (
    ("hidden_path", "village_plaza", "e"),
    ("village_plaza", "hidden_path", "w"),
    ("stream_path", "village_plaza", "n"),
    ("village_plaza", "stream_path", "s"),
    ("stream_path", "stream_bend", "e"),
    ("stream_bend", "stream_path", "w"),
    ("village_plaza", "old_tree_north", "n"),
    ("old_tree_north", "village_plaza", "s"),
    ("village_plaza", "training_clearing", "e"),
    ("training_clearing", "village_plaza", "w"),
    ("old_tree_north", "elder_tree", "n"),
    ("elder_tree", "old_tree_north", "s"),
    ("old_tree_north", "weaving_slope", "e"),
    ("weaving_slope", "old_tree_north", "w"),
    ("elder_tree", "silver_leaf_slope", "e"),
    ("silver_leaf_slope", "elder_tree", "w"),
    ("training_clearing", "herb_garden", "e"),
    ("herb_garden", "training_clearing", "w"),
)
