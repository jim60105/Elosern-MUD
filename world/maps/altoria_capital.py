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
            "聖潔王都的南門，一道寬拱，朝聖之路在這裡離開郊野走進下城。這座王都後來長成的一切都是從這裡開始的，一處渡口、然後一座鎮子、然後一座沿"
            "著身後岩壁向上攀爬的王城。"
        ),
    },
    (1, 1): {
        "prototype_parent": "grid_room",
        "key": "碼頭埠",
        "desc": (
            "聖潔王都的碼頭，上游來的駁船繫繩在被幾百年纜繩磨黑的石緣上。下城是王城最老的部分，而這裡是下城裡最老的一段，一座仍在營運的河港，叫賣"
            "、水鳥與貨件吵成一片。"
        ),
    },
    (2, 1): {
        "prototype_parent": "grid_room",
        "key": "河岸道",
        "desc": (
            "聖潔王都的河岸道，從碼頭沿著北岸向東而去。屋舍在這裡肩並著肩擠成一排，離水最近的土地最先被認領，而且從不肯讓出一寸。"
        ),
    },
    (3, 1): {
        "prototype_parent": "grid_room",
        "key": "南大道",
        "desc": (
            "聖潔王都的南大道，朝聖之路的第一段。從南門沿著它直直向上，整座城市就在前方攤開來，市集、廣場、階梯、大教堂。"
        ),
    },
    (4, 1): {
        "prototype_parent": "grid_room",
        "key": "客棧巷",
        "desc": (
            "聖潔王都的客棧巷。趕在上方台地關閉之後才到王都的旅人，向來都在下面一帶過夜；巷子裡的旅店"
            "、馬廄與打烊遲的酒館，就在同一片擁擠的地面上招呼他們。"
        ),
    },
    (5, 1): {
        "prototype_parent": "grid_room",
        "key": "浴場前",
        "desc": (
            "王都公共浴場門前，蒸氣與河水的氣味在路緣攪在一起。河鎮總是先有了浴池，才談得上別的排場；"
            "而這一間浴場，比這座城市興築又捨棄的每一道牆都活得久。"
        ),
    },
    (2, 2): {
        "prototype_parent": "grid_room",
        "key": "舊城牆遺跡",
        "desc": (
            "聖潔王都的舊城牆遺跡。這截剩下的基腳，是曾經圈住下城的那道牆僅存的東西。王都長過了它的範圍之後，牆被拆了下來，沿牆線清出的帶狀空地成"
            "了這座城市最寬敞的空地，市集街正是因此在這裡。對著這處遺跡讀地圖吧，它上方那條市集帶，就是那道牆變成的墳。"
        ),
    },
    (3, 2): {
        "prototype_parent": "grid_room",
        "key": "大道北段",
        "desc": (
            "朝聖之路的北段，南大道持續朝廣場攀升的地方。它把下城的擁擠拋在身後，沿著一段刻意留寬的路走，獻禮的車隊與朝聖者的腳，早把鋪石磨得平滑"
            "。"
        ),
    },
    (1, 3): {
        "prototype_parent": "grid_room",
        "key": "工匠巷",
        "desc": (
            "聖潔王都的工匠巷，在舊牆線的最西端。當市集取得了那條帶狀地，吵鬧的手藝就被擠到這裡來，鍛造鋪的錘聲如歌、裁縫坊的粉筆灰與布疋，還有一"
            "條斜斜切往校場的磨舊小徑，學徒們帶著貨物跑的就是這條。"
        ),
    },
    (2, 3): {
        "prototype_parent": "grid_room",
        "key": "市場街",
        "desc": (
            "聖潔王都的市場街，全王都最長的一條連續街道。它之所以長，是因為它正是那道倒下的牆清出來的牆線，街西頭的遺跡解釋了這條街的由來；而街上"
            "的攤位，就是王都的貿易為什麼向東流的原因。"
        ),
    },
    (3, 3): {
        "prototype_parent": "anchor_room",
        "anchor_key": "capital_altoria",
        "key": "中央廣場",
        "desc": (
            "聖潔王都的中央廣場，這座城市敞開的樞紐。朝聖之路從它中間穿過，舊城牆的市集帶在它下方橫切而過，聖階則從它遠端拔起，通往上方的台地。王"
            "都的地圖是從這個廣場畫出去的，多數日子，吵架也是。"
        ),
    },
    (4, 3): {
        "prototype_parent": "grid_room",
        "key": "公會前",
        "desc": (
            "聖潔王都冒險者公會門前的廣場，在市集帶上、廣場以東一格。契約在它告示板的蔭下就交接了，筆"
            "還沒進門檻，條件早已拍定；公會的搬運工也在這裡裝貨，雇來的刀客與木箱一齊上車。"
        ),
    },
    (5, 3): {
        "prototype_parent": "grid_room",
        "key": "東市",
        "desc": (
            "聖潔王都的東市，舊牆線上的貿易與出東門的道路交會的地方。穀物、玻璃與外國硬幣都經過它；道"
            "旁一條磨舊的斜坡抄近直通向大教堂，專走給不肯繞廣場和聖階的朝聖者。"
        ),
    },
    (6, 3): {
        "prototype_parent": "grid_room",
        "key": "東門",
        "desc": (
            "聖潔王都的東門，在市集帶的最遠端，正是東方來的道路會與河鎮主街合理相接的位置。它來得晚，它所立身的那道牆，比廣場西邊那處遺跡還新，王"
            "都以東的買賣、以及多半的麻煩，都是從這扇門進來的。"
        ),
    },
    (2, 4): {
        "prototype_parent": "grid_room",
        "key": "校場外",
        "desc": (
            "王都上方台地之下的校場外，徵兵與公會護衛在這裡學著站進陣形。地面被踩得堅硬，軍官的嗓子一"
            "路傳得進工匠巷，從工匠巷斜斜上來的學徒小徑在坡上磨出一道草綠的縫。"
        ),
    },
    (3, 4): {
        "prototype_parent": "grid_room",
        "key": "聖階",
        "desc": (
            "聖潔王都的聖階，朝聖之路的最後一段，也是上城始終是上城的原因。每一位在此加冕的王都把它們拓寬過，每一位跪著爬上來的懺悔者，都用石階量"
            "過這座王都的野心。階頂之上是那片想要高度的地，教會、學院、王宮。"
        ),
    },
    (4, 4): {
        "prototype_parent": "grid_room",
        "key": "大神殿前",
        "desc": (
            "聖潔王都大神殿前的前庭，正面對著聖階的頂端。光明教會先取走了這層台地，王冠才取了它上面那一層；兩者的次序是這整座城市被蓋出來反覆宣示"
            "的一句話，神在前，王冠在更高的地方俯視。"
        ),
    },
    (3, 5): {
        "prototype_parent": "grid_room",
        "key": "貴族區前",
        "desc": (
            "聖潔王都貴族區前的通道，在校場的後上方。當年握著下城渡口的那些家族，是一層台地一層台地買"
            "上岩壁的；他們的門、點燈人與拴著的狗，都寫著這一段攀爬走了多久。"
        ),
    },
    (4, 5): {
        "prototype_parent": "grid_room",
        "key": "上城門",
        "desc": (
            "聖潔王都的上城門，嵌在圍起機構台地的那道牆裡。它還有門樓與守門誓約，不過如今它存在，主要是為了讓上城能在節日裡把自己關起來，以及在它"
            "不想被市集帶看見的那些日子。"
        ),
    },
    (5, 5): {
        "prototype_parent": "grid_room",
        "key": "學院前",
        "desc": (
            "王立魔法學院門前的廣場，在攀爬東側的肩頭。學生在它的階上爭辯，賣墨水與二手論文的販子圍著"
            "他們打轉，而下到東市的那條斜坡，是理論到晚餐之間最短的距離。"
        ),
    },
    (4, 6): {
        "prototype_parent": "grid_room",
        "key": "王宮前庭",
        "desc": (
            "聖潔王都的王宮前庭，攀登上的最後一格，也是王都裡最高的地面。從這裡看下去，整座城市像一滴淚攤在腳下，河、碼頭、倒下的牆、市集帶、階與"
            "教堂，一塊河鎮的岩石，握在一個刻意把宮殿蓋在教堂之上的王冠手裡。"
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
