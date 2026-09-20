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
"""

from world.lore.settlements.places import PlaceDefinition, PlaceKind

ROWS: tuple[PlaceDefinition, ...] = (
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
        ),
    ),
    PlaceDefinition(
        key="ciaran_valwyn_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room_name_zh="瓦爾溫的家",
        room_desc_zh=(
            "Roots cradle this house beneath the old tree at the village's "
            "north edge. Shelves along every wall hold the collected oddments "
            "of a long life — stones, feathers, lengths of silk, seeds — each "
            "tenderly kept, each with a story. It is a home filled with "
            "kept things, not a business."
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
        ),
    ),
)