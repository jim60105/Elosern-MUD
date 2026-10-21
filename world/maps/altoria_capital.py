"""Sample city data for 聖潔王都 (capital_altoria), map-anchor-grid.

This module is the settlement's sparse declaration: stable node identities,
their authored integer-metre local coordinates (world-map-scale design §8),
explicit roads and the room prototypes the synchronizer applies. There is no
ASCII map: the meter coordinates are the single authored geometry. The
``SETTLEMENT_GRAPHS`` assembly for all settlements lives in
``world/maps/map_data.py``.

The layout is a river town that climbed a rock (altoria-capital-replan): the
riverbank lower city hugs the north bank where the southern road meets the
crossing, the market belt runs along the line of the wall the city outgrew,
and the upper city sits on the terrace above, reached by the 聖階 steps. The
pilgrim road runs 南門 → 南大道 → 大道北段 → 中央廣場 → 聖階 → 大神殿前.
Twenty-one nodes, twenty-six links, six cycles — deliberately not a tree: a
capital where every route is the only route is a corridor. The two diagonals
are worn shortcuts: apprentices' path from 工匠巷 up to 校場外, and the
pilgrims' slope from 東市 up to 大神殿前.
"""

# Prototypes keyed by the node's (X, Y) integer-metre local coordinate;
# sync_grid() applies these through the prototype machinery. Every coordinate
# except the central plaza (3500, 2850) is a plain GridRoom; the plaza is the
# AnchorRoom that
# ANCHOR_PLACEMENT_REGISTRY["capital_altoria"] points at. Seven nodes are
# walkable scenery with no interior to enter — quayside, ruin, plaza, steps,
# gates, and the road — which the design doc treats as the parts of a capital
# that exist to be moved through and looked at.
PROTOTYPES = {
    (3050, 150): {
        "prototype_parent": "grid_room",
        "key": "南門",
        "desc": (
            "聖潔王都的南門，一道寬拱，朝聖之路在這裡離開郊野走進下城。這座王都後來長成的一切，都是從這裡開始，一處渡口、然後一座鎮子、然後一座沿"
            "著身後岩壁向上攀爬的王城。"
        ),
    },
    (1250, 760): {
        "prototype_parent": "grid_room",
        "key": "碼頭埠",
        "desc": (
            "聖潔王都的碼頭，上游來的駁船繫繩在被幾百年纜繩磨黑的石緣上。下城是王城最老的部分，而這裡是下城裡最老的一段，一座仍在營運的河港，叫賣"
            "、水鳥與貨件吵成一片。"
        ),
    },
    (2150, 920): {
        "prototype_parent": "grid_room",
        "key": "河岸道",
        "desc": (
            "聖潔王都的河岸道，從碼頭沿著北岸向東而去。屋舍在這裡肩並著肩擠成一排，離水最近的土地最先被認領，而且從不肯讓出一寸。"
        ),
    },
    (3140, 1050): {
        "prototype_parent": "grid_room",
        "key": "南大道",
        "desc": (
            "聖潔王都的南大道，朝聖之路的第一段。從南門沿著它直直向上，整座城市就在前方攤開來，市集、廣場、階梯、大教堂。"
        ),
    },
    (3970, 1120): {
        "prototype_parent": "grid_room",
        "key": "客棧巷",
        "desc": (
            "聖潔王都的客棧巷。趕在上方台地關閉之後才到王都的旅人，向來都在下面一帶過夜；巷子裡的旅店"
            "、馬廄與打烊遲的酒館，就在同一片擁擠的地面上招呼他們。"
        ),
    },
    (4830, 970): {
        "prototype_parent": "grid_room",
        "key": "浴場前",
        "desc": (
            "王都公共浴場門前，蒸氣與河水的氣味在路緣攪在一起。河鎮總是先有了浴池，才談得上別的排場；"
            "而這一間浴場，比這座城市興築又捨棄的每一道牆都活得久。"
        ),
    },
    (2350, 1900): {
        "prototype_parent": "grid_room",
        "key": "舊城牆遺跡",
        "desc": (
            "聖潔王都的舊城牆遺跡。這截剩下的基腳，是曾經圈住下城的那道牆僅存的東西。王都長過了它的範圍之後，牆被拆了下來，沿牆線清出的帶狀空地成"
            "了這座城市最寬敞的空地，市集街正是因此在這裡。對著這處遺跡讀地圖吧，它上方那條市集帶，就是那道牆變成的墳。"
        ),
    },
    (3350, 1980): {
        "prototype_parent": "grid_room",
        "key": "大道北段",
        "desc": (
            "朝聖之路的北段，南大道持續朝廣場攀升的地方。它把下城的擁擠拋在身後，沿著一段刻意留寬的路走，獻禮的車隊與朝聖者的腳，早把鋪石磨得平滑"
            "。"
        ),
    },
    (1300, 2600): {
        "prototype_parent": "grid_room",
        "key": "工匠巷",
        "desc": (
            "聖潔王都的工匠巷，在舊牆線的最西端。當市集取得了那條帶狀地，吵鬧的手藝就被擠到這裡來，鍛造鋪的錘聲如歌、裁縫坊的粉筆灰與布疋，還有一"
            "條斜斜切往校場的磨舊小徑，學徒們帶著貨物跑的就是這條。"
        ),
    },
    (2420, 2700): {
        "prototype_parent": "grid_room",
        "key": "市場街",
        "desc": (
            "聖潔王都的市場街，全王都最長的一條連續街道。它之所以長，是因為它正是那道倒下的牆清出來的牆線，街西頭的遺跡解釋了這條街的由來；而街上"
            "的攤位，就是王都的貿易為什麼向東流的原因。"
        ),
    },
    (3500, 2850): {
        "prototype_parent": "anchor_room",
        "anchor_key": "capital_altoria",
        "key": "中央廣場",
        "desc": (
            "聖潔王都的中央廣場，這座城市敞開的樞紐。朝聖之路從它中間穿過，舊城牆的市集帶在它下方橫切而過，聖階則從它遠端拔起，通往上方的台地。王"
            "都的地圖從這個廣場畫出去，多數日子，吵架也是。"
        ),
    },
    (4380, 3000): {
        "prototype_parent": "grid_room",
        "key": "公會前",
        "desc": (
            "聖潔王都冒險者公會門前的廣場，在市集帶上、廣場以東一格。契約在它告示板的蔭下就交接了，筆"
            "還沒進門檻，條件早已拍定；公會的搬運工也在這裡裝貨，雇來的刀客與木箱一齊上車。"
        ),
    },
    (5380, 2850): {
        "prototype_parent": "grid_room",
        "key": "東市",
        "desc": (
            "聖潔王都的東市，舊牆線上的貿易與出東門的道路交會的地方。穀物、玻璃與外國硬幣都經過它；道"
            "旁一條磨舊的斜坡抄近直通向大教堂，專走給不肯繞廣場和聖階的朝聖者。"
        ),
    },
    (6500, 3010): {
        "prototype_parent": "grid_room",
        "key": "東門",
        "desc": (
            "聖潔王都的東門，在市集帶的最遠端，正是東方來的道路會與河鎮主街合理相接的位置。它來得晚，它所立身的那道牆，比廣場西邊那處遺跡還新，王"
            "都以東的買賣、以及多半的麻煩，都從這扇門進來。"
        ),
    },
    (2300, 3820): {
        "prototype_parent": "grid_room",
        "key": "校場外",
        "desc": (
            "王都上方台地之下的校場外，徵兵與公會護衛在這裡學著站進陣形。地面被踩得堅硬，軍官的嗓子一"
            "路傳得進工匠巷，從工匠巷斜斜上來的學徒小徑在坡上磨出一道草綠的縫。"
        ),
    },
    (3480, 3700): {
        "prototype_parent": "grid_room",
        "key": "聖階",
        "desc": (
            "聖潔王都的聖階，朝聖之路的最後一段，也是上城始終是上城的原因。每一位在此加冕的王都把它們拓寬過，每一位跪著爬上來的懺悔者，都用石階量"
            "過這座王都的野心。階頂之上是那片想要高度的地，教會、學院、王宮。"
        ),
    },
    (4560, 3920): {
        "prototype_parent": "grid_room",
        "key": "大神殿前",
        "desc": (
            "聖潔王都大神殿前的前庭，正面對著聖階的頂端。光明教會先取走了這層台地，王冠才取了它上面那一層；兩者的次序是這整座城市被蓋出來反覆宣示"
            "的一句話，神在前，王冠在更高的地方俯視。"
        ),
    },
    (3500, 4850): {
        "prototype_parent": "grid_room",
        "key": "貴族區前",
        "desc": (
            "聖潔王都貴族區前的通道，在校場的後上方。當年握著下城渡口的那些家族，是一層台地一層台地買"
            "上岩壁的；他們的門、點燈人與拴著的狗，都寫著這一段攀爬走了多久。"
        ),
    },
    (4690, 5010): {
        "prototype_parent": "grid_room",
        "key": "上城門",
        "desc": (
            "聖潔王都的上城門，嵌在圍起機構台地的那道牆裡。它還有門樓與守門誓約，不過如今它存在，主要是為了讓上城能在節日裡把自己關起來，以及在它"
            "不想被市集帶看見的那些日子。"
        ),
    },
    (5650, 5200): {
        "prototype_parent": "grid_room",
        "key": "學院前",
        "desc": (
            "王立魔法學院門前的廣場，在攀爬東側的肩頭。學生在它的階上爭辯，賣墨水與二手論文的販子圍著"
            "他們打轉，而下到東市的那條斜坡，是理論到晚餐之間最短的距離。"
        ),
    },
    (4500, 6350): {
        "prototype_parent": "grid_room",
        "key": "王宮前庭",
        "desc": (
            "聖潔王都的王宮前庭，攀登上的最後一格，也是王都裡最高的地面。從這裡看下去，整座城市像一滴淚攤在腳下，河、碼頭、倒下的牆、市集帶、階與"
            "教堂，一塊河鎮的岩石，握在一個刻意把宮殿蓋在教堂之上的王冠手裡。"
        ),
    },
}

# The sparse map declaration. ``map_data.py`` builds the authoritative graph
# from these tables; the xyzgrid contrib's ASCII ``map`` key is intentionally
# absent because a metre lattice is never allocated (world-map-scale §11).
XYMAP_DATA = {
    "zcoord": "capital_altoria",
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

# Stable authored identity per coordinate (implement-sparse-settlement-graphs).
# Identity, not the coordinate, is the synchronizer's matching authority: a
# coordinate move rewrites the coordinate here while the same rooms, occupants
# and references persist. ``NODE_IDS`` must describe exactly the
# ``PROTOTYPES`` coordinates; ``build_sparse_graph()`` rejects drift.
NODE_IDS = {
    (3050, 150): "south_gate",
    (1250, 760): "quay",
    (2150, 920): "riverbank_road",
    (3140, 1050): "south_avenue",
    (3970, 1120): "inn_lane",
    (4830, 970): "bath_forecourt",
    (2350, 1900): "old_wall_ruins",
    (3350, 1980): "north_avenue",
    (1300, 2600): "craft_alley",
    (2420, 2700): "market_street",
    (3500, 2850): "central_plaza",
    (4380, 3000): "guild_forecourt",
    (5380, 2850): "east_market",
    (6500, 3010): "east_gate",
    (2300, 3820): "training_ground",
    (3480, 3700): "holy_steps",
    (4560, 3920): "great_temple",
    (3500, 4850): "noble_quarter",
    (4690, 5010): "upper_gate",
    (5650, 5200): "academy",
    (4500, 6350): "palace_forecourt",
}

# Explicit roads: (source identity, destination identity, compass octant), one
# directed road per travel direction. The octant is authored because the
# irregular metre layout is almost never axis-aligned: it is the exit a
# traveller takes, exactly the octant the compact layout used to spell. The
# sparse route adapter measures each edge's physical length between the two
# authored metre positions.
ROADS = (
    ("south_gate", "south_avenue", "n"),
    ("south_avenue", "south_gate", "s"),
    ("south_avenue", "north_avenue", "n"),
    ("north_avenue", "south_avenue", "s"),
    ("north_avenue", "central_plaza", "n"),
    ("central_plaza", "north_avenue", "s"),
    ("south_avenue", "riverbank_road", "w"),
    ("riverbank_road", "south_avenue", "e"),
    ("south_avenue", "inn_lane", "e"),
    ("inn_lane", "south_avenue", "w"),
    ("riverbank_road", "quay", "w"),
    ("quay", "riverbank_road", "e"),
    ("riverbank_road", "old_wall_ruins", "n"),
    ("old_wall_ruins", "riverbank_road", "s"),
    ("old_wall_ruins", "market_street", "n"),
    ("market_street", "old_wall_ruins", "s"),
    ("old_wall_ruins", "north_avenue", "e"),
    ("north_avenue", "old_wall_ruins", "w"),
    ("inn_lane", "bath_forecourt", "e"),
    ("bath_forecourt", "inn_lane", "w"),
    ("market_street", "craft_alley", "w"),
    ("craft_alley", "market_street", "e"),
    ("craft_alley", "training_ground", "ne"),
    ("training_ground", "craft_alley", "sw"),
    ("market_street", "central_plaza", "e"),
    ("central_plaza", "market_street", "w"),
    ("central_plaza", "holy_steps", "n"),
    ("holy_steps", "central_plaza", "s"),
    ("central_plaza", "guild_forecourt", "e"),
    ("guild_forecourt", "central_plaza", "w"),
    ("holy_steps", "training_ground", "w"),
    ("training_ground", "holy_steps", "e"),
    ("holy_steps", "noble_quarter", "n"),
    ("noble_quarter", "holy_steps", "s"),
    ("holy_steps", "great_temple", "e"),
    ("great_temple", "holy_steps", "w"),
    ("guild_forecourt", "great_temple", "n"),
    ("great_temple", "guild_forecourt", "s"),
    ("guild_forecourt", "east_market", "e"),
    ("east_market", "guild_forecourt", "w"),
    ("great_temple", "upper_gate", "n"),
    ("upper_gate", "great_temple", "s"),
    ("great_temple", "east_market", "se"),
    ("east_market", "great_temple", "nw"),
    ("noble_quarter", "upper_gate", "e"),
    ("upper_gate", "noble_quarter", "w"),
    ("upper_gate", "palace_forecourt", "n"),
    ("palace_forecourt", "upper_gate", "s"),
    ("upper_gate", "academy", "e"),
    ("academy", "upper_gate", "w"),
    ("east_market", "east_gate", "e"),
    ("east_gate", "east_market", "w"),
)
