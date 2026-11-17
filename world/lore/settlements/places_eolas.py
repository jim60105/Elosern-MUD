"""幽月谷村 (elven_village_eolas) place rows.

Every trading place in the village is a private dwelling, not a storefront: a
villager who happens to make things trades from her own home, and the room
names use the given name alone, the way a village refers to a neighbour's
house. Rows stay alphabetical by key.

The tuple order is load-bearing: ``PLACE_REGISTRY`` appends this slice after
the capital's and 暗影谷村's, so the derived roster and shop registry keep
those rows ahead of the 幽月谷村 homes (sync iterates in this order).

Every row carries a ``dialogue_key`` beside its ``shop_key``: the merchant
blueprint answers as well as trades, and the tables in
``world/lore/dialogue/content/eolas_*.yaml`` speak as villagers sharing what
they make, never as shopkeepers.
"""

from world.lore.settlements.places import PlaceDefinition, PlaceKind
from world.lore.settlements.capability_declarations import (
    capability,
    place_bound,
)
from elosern_map_core.references import interior_room_ref

ROWS: tuple[PlaceDefinition, ...] = (
    PlaceDefinition(
        key="eolas_naelara_home",
        settlement_key="elven_village_eolas",
        kind=PlaceKind.HOME,
        room=interior_room_ref("eolas_naelara_home", "eolas_naelara_home"),
        host_name="奈拉拉‧弗羅斯特威洛",
        host_race="elf",
        host_subrace="eolas",
        host_sex="female",
        host_profile_key="eolas_naelara",
        assortment_keys=("eolas_silkwork",),
        components=(
            capability(
                "merchant",
                binding=place_bound("eolas_naelara_home"),
                service_id="eolas_naelara",
                shop_key="eolas_naelara_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("eolas_naelara_home"),
                dialogue_key="eolas_naelara_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="eolas_sirelwen_home",
        settlement_key="elven_village_eolas",
        kind=PlaceKind.HOME,
        room=interior_room_ref("eolas_sirelwen_home", "eolas_sirelwen_home"),
        host_name="希瑞爾溫‧布瑞特瓦特爾",
        host_race="elf",
        host_subrace="eolas",
        host_sex="female",
        host_profile_key="eolas_sirelwen",
        assortment_keys=("eolas_wandcraft",),
        components=(
            capability(
                "merchant",
                binding=place_bound("eolas_sirelwen_home"),
                service_id="eolas_sirelwen",
                shop_key="eolas_sirelwen_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("eolas_sirelwen_home"),
                dialogue_key="eolas_sirelwen_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="eolas_taelith_home",
        settlement_key="elven_village_eolas",
        kind=PlaceKind.HOME,
        room=interior_room_ref("eolas_taelith_home", "eolas_taelith_home"),
        host_name="泰莉斯‧恩貝爾莉夫",
        host_race="elf",
        host_subrace="eolas",
        host_sex="female",
        host_profile_key="eolas_taelith",
        assortment_keys=("eolas_kilnware",),
        components=(
            capability(
                "merchant",
                binding=place_bound("eolas_taelith_home"),
                service_id="eolas_taelith",
                shop_key="eolas_taelith_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("eolas_taelith_home"),
                dialogue_key="eolas_taelith_home",
            ),
        ),
    ),
)
