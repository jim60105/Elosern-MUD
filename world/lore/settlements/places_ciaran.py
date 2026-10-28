"""暗影谷村 (village_ciaran) place rows (settlement-shops design §6.2, §10 change 7).

Every trading place in the village is a private home, not a storefront: a
villager who happens to make or collect things trades from their own
dwelling. The room names use the given name alone — a village refers to a
neighbour's house by the neighbour, not by the full 名‧姓 form.

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
from world.lore.settlements.capability_declarations import (
    capability,
    place_bound,
)
from elosern_map_core.references import interior_room_ref

ROWS: tuple[PlaceDefinition, ...] = (
    PlaceDefinition(
        key="ciaran_elenis_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room=interior_room_ref("ciaran_elenis_home", "ciaran_elenis_home"),
        host_name="艾莉妮斯‧達恩斯特瑞德爾",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        host_profile_key="ciaran_elenis",
        components=(
            capability(
                "scripted_dialogue",
                binding=place_bound("ciaran_elenis_home"),
                dialogue_key="ciaran_elenis_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="ciaran_gwenaera_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room=interior_room_ref("ciaran_gwenaera_home", "ciaran_gwenaera_home"),
        host_name="格威娜拉‧希爾維爾莉夫",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        host_profile_key="ciaran_gwenaera",
        assortment_keys=("elven_adornments",),
        components=(
            capability(
                "merchant",
                binding=place_bound("ciaran_gwenaera_home"),
                service_id="ciaran_gwenaera",
                shop_key="ciaran_gwenaera_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("ciaran_gwenaera_home"),
                dialogue_key="ciaran_gwenaera_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="ciaran_hailiel_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room=interior_room_ref("ciaran_hailiel_home", "ciaran_hailiel_home"),
        host_name="海莉爾‧斯塔爾法爾",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        host_profile_key="ciaran_hailiel",
        assortment_keys=("elven_crafted_arms",),
        components=(
            capability(
                "merchant",
                binding=place_bound("ciaran_hailiel_home"),
                service_id="ciaran_hailiel",
                shop_key="ciaran_hailiel_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("ciaran_hailiel_home"),
                dialogue_key="ciaran_hailiel_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="ciaran_lareneth_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room=interior_room_ref("ciaran_lareneth_home", "ciaran_lareneth_home"),
        host_name="拉瑞內斯‧妮特布倫",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        host_profile_key="ciaran_lareneth",
        assortment_keys=("elven_fare",),
        components=(
            capability(
                "merchant",
                binding=place_bound("ciaran_lareneth_home"),
                service_id="ciaran_lareneth",
                shop_key="ciaran_lareneth_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("ciaran_lareneth_home"),
                dialogue_key="ciaran_lareneth_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="ciaran_nireth_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room=interior_room_ref("ciaran_nireth_home", "ciaran_nireth_home"),
        host_name="妮瑞斯‧米斯特瓦勒",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        host_profile_key="ciaran_nireth",
        assortment_keys=("elven_remedies",),
        components=(
            capability(
                "merchant",
                binding=place_bound("ciaran_nireth_home"),
                service_id="ciaran_nireth",
                shop_key="ciaran_nireth_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("ciaran_nireth_home"),
                dialogue_key="ciaran_nireth_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="ciaran_shelter",
        settlement_key="village_ciaran",
        kind=PlaceKind.COMMONS,
        room=interior_room_ref("ciaran_shelter", "ciaran_shelter"),
    ),
    PlaceDefinition(
        key="ciaran_teliel_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room=interior_room_ref("ciaran_teliel_home", "ciaran_teliel_home"),
        host_name="泰莉爾‧菲溫德",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        host_profile_key="ciaran_teliel",
        components=(
            capability(
                "scripted_dialogue",
                binding=place_bound("ciaran_teliel_home"),
                dialogue_key="ciaran_teliel_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="ciaran_valwyn_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room=interior_room_ref("ciaran_valwyn_home", "ciaran_valwyn_home"),
        host_name="瓦爾溫‧斯蒂爾瓦特爾",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        host_profile_key="ciaran_valwyn",
        assortment_keys=("elven_sundries",),
        components=(
            capability(
                "merchant",
                binding=place_bound("ciaran_valwyn_home"),
                service_id="ciaran_valwyn",
                shop_key="ciaran_valwyn_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("ciaran_valwyn_home"),
                dialogue_key="ciaran_valwyn_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="ciaran_vethiel_home",
        settlement_key="village_ciaran",
        kind=PlaceKind.HOME,
        room=interior_room_ref("ciaran_vethiel_home", "ciaran_vethiel_home"),
        host_name="維特希爾‧威爾德布瑞亞爾",
        host_race="elf",
        host_subrace="ciaran",
        host_sex="female",
        host_profile_key="ciaran_vethiel",
        assortment_keys=("elven_attire",),
        components=(
            capability(
                "merchant",
                binding=place_bound("ciaran_vethiel_home"),
                service_id="ciaran_vethiel",
                shop_key="ciaran_vethiel_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("ciaran_vethiel_home"),
                dialogue_key="ciaran_vethiel_home",
            ),
        ),
    ),
)