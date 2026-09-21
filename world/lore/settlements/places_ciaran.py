"""暗影谷村 (village_ciaran) place rows (settlement-shops design §6.2, §10 change 7).

Every trading place in the village is a private home, not a storefront: a
villager who happens to make or collect things trades from their own
dwelling. The room names use the given name alone — a village refers to a
neighbour's house by the neighbour, not by the full 名·姓 form — and the
titles deliberately avoid 老闆 / 店主: those words denote commercial
establishments, which this settlement does not have.

The tuple order is load-bearing: ``PLACE_REGISTRY`` appends this slice after
the capital's, so the derived roster and shop registry keep the capital's
rows first and the village's four homes after (sync iterates in this order).

Every merchant row carries a ``dialogue_key`` beside its ``shop_key``: the
merchant blueprint answers as well as trades (merchant-dialogue). The
village tables in ``world/lore/dialogue/ciaran.py`` speak as villagers
sharing what they make — never as shopkeepers.

ciaran-village-crafts adds the two homes the document names: 格威娜拉的家 off
銀葉坡, whose host makes the village's ornaments, and 妮瑞斯的家 off 藥草園,
whose hedge-healer keeps the remedies out of the 調藥坊's absence. Rows stay
alphabetical by host given name.

ciaran-village-commons adds the three shared spaces the document names and the
village lacked: 共食棚 off 村中廣場 — a host-less commons, because eating
together is not a transaction in this culture — and the two homes whose people
converse instead of trading: 泰莉爾的家 off 練刀場, where the village's sword
instructor lives beside the blade-smith's doorstep, and 艾莉妮斯的家 off
長老古樹下, home of the village's elder. Rows stay alphabetical by key.
"""

from world.lore.settlements.places import PlaceDefinition, PlaceKind

ROWS: tuple[PlaceDefinition, ...] = (
    PlaceDefinition(
        key="ciaran_elenis_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room_name_zh="艾莉妮斯的家",
        room_desc_zh=(
            "最老的樹下是最老的一間屋子，門框被同一族腳步磨了一百年，磨得發亮。屋裡簡樸而從容：低矮的"
            "坐處、一格擱著留種的莢果與摺好的布的擱板，沒有什麼東西是為了讓誰買而分類的。長老的家當都"
            "是被記得的東西——村莊自己的歷史，完完整整留著，沒有一樣攤出來等陌生人的錢。"
        ),
        exterior_xy=(1, 3),  # 長老古樹下
        doorway_key_zh="艾莉妮斯的家",
        doorway_aliases=("elenis", "elenis's home"),
        host_name="艾莉妮斯·達恩斯特瑞德爾",
        host_title="暗影谷村長老",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        profession="attendant",
        service_id="ciaran_elenis",
        authored_kwargs=(("dialogue_key", "ciaran_elenis_home"),),
    ),
    PlaceDefinition(
        key="ciaran_gwenaera_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room_name_zh="格威娜拉的家",
        room_desc_zh=(
            "銀絲與做了一半的飾品攤在工作檯的布上，分的標準出自手藝人的眼光，不是商人的。完成的作品掛"
            "在窗邊的繩上，旁邊晾著從下面坡上採來的花頭；爐火溫著一壺水，沒人指望會有客人要用。這是一"
            "個喜歡綴飾工作的人的家，會做買賣只是因為村子請她做。"
        ),
        exterior_xy=(2, 3),  # 銀葉坡
        doorway_key_zh="格威娜拉的家",
        doorway_aliases=("gwenaera", "gwenaera's home"),
        host_name="格威娜拉·希爾維爾莉夫",
        host_title="暗影谷村綴飾者",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        profession="merchant",
        service_id="ciaran_gwenaera",
        assortment_keys=("elven_adornments",),
        authored_kwargs=(
            ("shop_key", "ciaran_gwenaera_home"),
            ("dialogue_key", "ciaran_gwenaera_home"),
        ),
    ),
    PlaceDefinition(
        key="ciaran_hailiel_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room_name_zh="海莉爾的家",
        room_desc_zh=(
            "一道厚樑下是一間低矮溫暖的屋子。爐膛用餘燼蓋著過夜，窗邊的坐位望出去正是村中的練刀場，年"
            "幼的刀舞者從清晨到日暮都在那裡走他們的路子。這屋家的器具沿牆收得整整齊齊；這裡沒有任何一"
            "樣是為了買賣擺的。"
        ),
        exterior_xy=(2, 1),  # 練刀場
        doorway_key_zh="海莉爾的家",
        doorway_aliases=("hailiel", "hailiel's home"),
        host_name="海莉爾·斯塔爾法爾",
        host_title="暗影谷村鑄刃者",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        profession="merchant",
        service_id="ciaran_hailiel",
        assortment_keys=("elven_crafted_arms",),
        authored_kwargs=(
            ("shop_key", "ciaran_hailiel_home"),
            ("dialogue_key", "ciaran_hailiel_home"),
        ),
    ),
    PlaceDefinition(
        key="ciaran_lareneth_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room_name_zh="拉瑞內斯的家",
        room_desc_zh=(
            "溪畔小徑旁這戶人家，空氣裡懸著糖漬花的香氣。曬乾的花瓣織在籃裡擱著，挨著一方小爐石；窗邊"
            "一張矮凳上擺著今日待客的小點，為每個經過的人留著。"
        ),
        exterior_xy=(1, 0),  # 溪畔小徑
        doorway_key_zh="拉瑞內斯的家",
        doorway_aliases=("lareneth", "lareneth's home"),
        host_name="拉瑞內斯·妮特布倫",
        host_title="暗影谷村花饌好手",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        profession="merchant",
        service_id="ciaran_lareneth",
        assortment_keys=("elven_fare",),
        authored_kwargs=(
            ("shop_key", "ciaran_lareneth_home"),
            ("dialogue_key", "ciaran_lareneth_home"),
        ),
    ),
    PlaceDefinition(
        key="ciaran_nireth_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room_name_zh="妮瑞斯的家",
        room_desc_zh=(
            "成把的藥草與塞著木塞的小藥罐擠滿這間曬得到太陽的屋子，按摘下的時辰排，不按值多少錢排。窗"
            "邊一方臼，窗外望得見村子的藥草園，門口一帶的空氣苦裡帶甜。藥是留給需要的人的；被村子請託"
            "把藥換成錢賣，是同一座種藥的村子順便想到的事。"
        ),
        exterior_xy=(3, 1),  # 藥草園
        doorway_key_zh="妮瑞斯的家",
        doorway_aliases=("nireth", "nireth's home"),
        host_name="妮瑞斯·米斯特瓦勒",
        host_title="暗影谷村調藥者",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        profession="merchant",
        service_id="ciaran_nireth",
        assortment_keys=("elven_remedies",),
        authored_kwargs=(
            ("shop_key", "ciaran_nireth_home"),
            ("dialogue_key", "ciaran_nireth_home"),
        ),
    ),
    PlaceDefinition(
        key="ciaran_shelter",
        settlement_key="village_ciaran",
        kind=PlaceKind.COMMONS,
        room_name_zh="共食棚",
        room_desc_zh=(
            "寬寬一片編枝的屋頂，罩著被所有人的腳踩平的地板。長桌擱在蔭裡；當日採集的東西開著簍放在桌"
            "上，燒水的位置早已鋪好，等下一個來的人。沒有人看管食物，也沒有人索取：森林給村子的就攤在"
            "這一頂共用的屋簷下，每個村民都從同一張桌上吃。"
        ),
        exterior_xy=(1, 1),  # 村中廣場
        doorway_key_zh="共食棚",
        doorway_aliases=("shelter", "communal shelter"),
    ),
    PlaceDefinition(
        key="ciaran_teliel_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room_name_zh="泰莉爾的家",
        room_desc_zh=(
            "練刀場邊的一戶人家，屋裡那片騰空的空間掃得乾淨，為赤腳的路子留的。木刀在門邊排成一排，刀"
            "柄被許多手握得發白；對面擱著坐墊與水壺，為每一時辰練習都得還的休息留的。屋裡沒有一樣東西"
            "在賣——村子刀術導師的家教人的方式，和她的場子一直以來一樣，靠練習者自己的重複。"
        ),
        exterior_xy=(2, 1),  # 練刀場
        doorway_key_zh="泰莉爾的家",
        doorway_aliases=("teliel", "teliel's home"),
        host_name="泰莉爾·菲溫德",
        host_title="暗影谷村刀術導師",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        profession="attendant",
        service_id="ciaran_teliel",
        authored_kwargs=(("dialogue_key", "ciaran_teliel_home"),),
    ),
    PlaceDefinition(
        key="ciaran_valwyn_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room_name_zh="瓦爾溫的家",
        room_desc_zh=(
            "村北那株老樹下，樹根環抱間是這戶人家。沿著每一面牆，一輩子蒐羅來的零物擱在織籃與挖空的石"
            "裡——羽毛、種子、一綑綑紮起的絲——樣樣被細心留著，樣樣有一個故事。這是一個被留下來的事"
            "物裝滿的家，不是一間鋪子。"
        ),
        exterior_xy=(1, 2),  # 村北古樹下
        doorway_key_zh="瓦爾溫的家",
        doorway_aliases=("valwyn", "valwyn's home"),
        host_name="瓦爾溫·斯蒂爾瓦特爾",
        host_title="暗影谷村蒐羅者",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        profession="merchant",
        service_id="ciaran_valwyn",
        assortment_keys=("elven_sundries",),
        authored_kwargs=(
            ("shop_key", "ciaran_valwyn_home"),
            ("dialogue_key", "ciaran_valwyn_home"),
        ),
    ),
    PlaceDefinition(
        key="ciaran_vethiel_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room_name_zh="維特希爾的家",
        room_desc_zh=(
            "藥草倒掛在椽上晾乾，染好的線繞在織機邊的木釘上。木架上看得見許多手的磨損，可這間屋子首先"
            "是個住家：地上一個坐墊，火邊一壺水，織品之間攤著幾件衣服等人欣賞。"
        ),
        exterior_xy=(2, 2),  # 織房坡
        doorway_key_zh="維特希爾的家",
        doorway_aliases=("vethiel", "vethiel's home"),
        host_name="維特希爾·威爾德布瑞亞爾",
        host_title="暗影谷村織衣者",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        profession="merchant",
        service_id="ciaran_vethiel",
        assortment_keys=("elven_attire",),
        authored_kwargs=(
            ("shop_key", "ciaran_vethiel_home"),
            ("dialogue_key", "ciaran_vethiel_home"),
        ),
    ),
)