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
            "The eldest house under the eldest tree, its doorway worn smooth "
            "by a century of the same footsteps. Within, the room is spare "
            "and unhurried: low seats, a ledge of kept seed-pods and folded "
            "cloths, and nothing sorted for anyone's buying. The elder's "
            "goods are remembered things — the village's own history, "
            "kept whole, and none of them set out for a stranger's coin."
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
            "Silver wire and half-finished ornaments lie on a cloth across "
            "the work table, sorted by a craftswoman's eye rather than a "
            "merchant's. Finished pieces hang from a line by the window "
            "beside drying blossom heads from the slope below; the hearth "
            "warms a kettle no customer was expected to need. It is the "
            "house of someone who loves ornamental work, and trades only "
            "because the village asks her to."
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
            "A low, warm room under heavy beams. The hearth is banked with "
            "embers, and a window seat overlooks the practice ground where "
            "the village's young blade-dancers run through their forms from "
            "dawn to dusk. The tools of the house are kept tidy along the "
            "walls; nothing here is arranged for trade."
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
            "The scent of candied blossoms hangs in the air of this home "
            "along the stream path. Woven baskets of dried petals stand "
            "beside a small hearth stone, and by the window a low table "
            "holds the day's offering of small treats, set out for whoever "
            "passes by."
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
            "Bundles of herb and small stoppered jars of remedy crowd this "
            "sunlit house, sorted in the order of when they were picked "
            "rather than of what they are worth. A mortar sits by the "
            "window overlooking the village's herb plot, and the air turns "
            "bitter-sweet at the door. The remedies are kept for whoever "
            "needs them; being asked to keep them for coin is an after-"
            "thought of the same village that grows the herbs."
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
            "A wide roof of woven branches over a floor worn level by "
            "everyone's feet. Long tables stand in the shade; baskets of "
            "the day's gathering sit open on them, and the kettle place is "
            "already laid for whoever arrives next. Nobody tends the food "
            "and nobody asks for it: what the forest gave the village is "
            "simply set under one shared roof, and every villager eats from "
            "the same table."
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
            "A home on the training ground's edge, its one clear space kept "
            "swept for bare-foot forms. Wooden practice blades hang in a "
            "row by the door, worn light at the handles by many hands; "
            "cushions and a kettle sit opposite, for the resting that every "
            "hour of practice costs. Nothing in the room is for sale — the "
            "house of the village's sword instructor teaches the way its "
            "yard always has, by the trainee's own repetition."
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
            "Roots cradle this house beneath the old tree at the village's "
            "north edge. Along every wall, the collected oddments of a long "
            "life sit in woven baskets and hollowed stones — feathers, seeds, "
            "lengths of bundled silk — each tenderly kept, each with a story. "
            "It is a home filled with kept things, not a business."
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
            "Herbs hang to dry from the rafters, and dyed thread is wound "
            "around pegs by the loom. The wear of many hands shows on the "
            "wooden frame, yet the room is a dwelling first: cushions on the "
            "floor, a kettle by the fire, garments laid out to be admired "
            "among the weaving."
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