"""Grid map data for 暗影谷村 (village_ciaran), map-anchor-grid.

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

MAPSTR = r"""
+ 0 1 2 3

3   #-#
    |
2   #-#
    |
1 #-#-#-#
    |
0   #-#

+ 0 1 2 3
"""

# Prototypes keyed by (X, Y) coordinate; sync_grid() spawns these through the
# xyzgrid contrib's prototype machinery. Every coordinate except the village
# plaza (1,1) is a plain GridRoom; the plaza is the AnchorRoom that
# ANCHOR_PLACEMENT_REGISTRY["village_ciaran"] points at. 隱密小徑 is the way
# in from 虛境 and the return point from the wilderness: elven villages have
# no walls and no gates, so it reads as a concealed path through the forest,
# not as a city gate (even though it occupies the CITY_GATE_REGISTRY slot).
# The four nodes added by ciaran-village-crafts — (1,3), (2,3), (3,1), (2,0) —
# keep the six original coordinates exactly where they were, so none of the
# four landed homes' exteriors moved. 長老古樹下 and 溪畔下游 are walkable
# scenery: the commons change fills the elder's grove; the stream bend stays
# scenery.
PROTOTYPES = {
    (0, 1): {
        "prototype_parent": "grid_room",
        "key": "隱密小徑",
        "desc": "藤蔓與落葉幾乎掩住了這條小徑；不認得這片林子的人，縱使走進去也看不出來。",
    },
    (1, 1): {
        "prototype_parent": "anchor_room",
        "anchor_key": "village_ciaran",
        "key": "村中廣場",
        "desc": "村裡的空地，老樹繞著一塊被腳步踩實的泥地。族人聚集在這裡交談，"
        "交換一天的見聞。",
    },
    (2, 1): {
        "prototype_parent": "grid_room",
        "key": "練刀場",
        "desc": "無數腳步踩硬的空地，四周樹幹佈滿練習留下的刀痕——"
        "村中的少年刀舞者從清晨練到日暮，練的就是這裡。",
    },
    (1, 0): {
        "prototype_parent": "grid_room",
        "key": "溪畔小徑",
        "desc": "沿著潺潺溪流蜿蜒的土路，水邊幾塊平坦的石盤，正好讓人坐下歇腳。",
    },
    (1, 2): {
        "prototype_parent": "grid_room",
        "key": "村北古樹下",
        "desc": "村北古樹之下，樹冠如屋簷般撐開；盤根間嵌著磨平的石座，"
        "孩子們聚在這裡聽長者說故事。",
    },
    (2, 2): {
        "prototype_parent": "grid_room",
        "key": "織房坡",
        "desc": "通往林中住屋的緩坡，新染的布掛在繩上晾乾，風裡帶著植物染料的氣味。",
    },
    (1, 3): {
        "prototype_parent": "grid_room",
        "key": "長老古樹下",
        "desc": "再往北，林子更老。最老的那株巨樹寬得數人合抱，盤根之間有磨平的坐石；"
        "族裡老一輩的決定，多在這棵樹下說出口。平日這裡安靜，只餘風穿過樹冠的聲音。",
    },
    (2, 3): {
        "prototype_parent": "grid_room",
        "key": "銀葉坡",
        "desc": "織房坡再往上，坡頂長著一叢銀葉樹，葉背在午後的光裡泛著細碎銀光。"
        "樹下曬著幾件完成的花邊與綴飾，綴著貝殼和磨圓的晶砂。",
    },
    (3, 1): {
        "prototype_parent": "grid_room",
        "key": "藥草園",
        "desc": "練刀場東邊，樹冠開處漏下整片陽光。矮石壘成的畦邊圈著一株株藥草與香草，"
        "空氣裡是苦味與清甜交錯的氣息。",
    },
    (2, 0): {
        "prototype_parent": "grid_room",
        "key": "溪畔下游",
        "desc": "溪流出了村子便寬了、緩了，水色轉深。下游有一片族人清洗染具的淺灘，"
        "石上還留著乾涸的藍色水痕；走到這裡的人多半只為坐一坐，聽水聲。",
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
