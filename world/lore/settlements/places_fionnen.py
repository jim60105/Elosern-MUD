"""翠綠森林村 (elven_village_fionnen) craft-home place rows.

Every row is a private dwelling whose host shares what she loves making: the
toy-carver's bench between the buttress roots of 樹根屋, the bow maker's room
beside 木作空地, the weaver's platform on 樹冠吊橋. No row is a storefront;
a visitor who finds the village is given a piece for coin because the village
looks after its guests, never because a shop keeps stock.

Rows stay alphabetical by key. The tuple order is load-bearing:
``PLACE_REGISTRY`` appends this slice after 幽月谷村's, so the derived roster
and shop registry keep the capital's rows first and the villages' homes after.
"""

from world.lore.settlements.places import PlaceDefinition, PlaceKind
from world.lore.settlements.capability_declarations import (
    capability,
    place_bound,
)
from elosern_map_core.references import interior_room_ref

ROWS: tuple[PlaceDefinition, ...] = (
    PlaceDefinition(
        key="fionnen_corith_home",
        settlement_key="elven_village_fionnen",
        kind=PlaceKind.HOME,
        room=interior_room_ref("fionnen_corith_home", "fionnen_corith_home"),
        host_name="科瑞斯‧蒙希斯佩爾",
        host_race="elf",
        host_subrace="fionnen",
        host_sex="female",
        host_profile_key="fionnen_corith",
        assortment_keys=("fionnen_trinkets",),
        components=(
            capability(
                "merchant",
                binding=place_bound("fionnen_corith_home"),
                service_id="fionnen_corith",
                shop_key="fionnen_corith_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("fionnen_corith_home"),
                dialogue_key="fionnen_corith_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="fionnen_gwynnel_home",
        settlement_key="elven_village_fionnen",
        kind=PlaceKind.HOME,
        room=interior_room_ref("fionnen_gwynnel_home", "fionnen_gwynnel_home"),
        host_name="格威內爾‧斯威夫塔羅",
        host_race="elf",
        host_subrace="fionnen",
        host_sex="female",
        host_profile_key="fionnen_gwynnel",
        assortment_keys=("fionnen_bowcraft",),
        components=(
            capability(
                "merchant",
                binding=place_bound("fionnen_gwynnel_home"),
                service_id="fionnen_gwynnel",
                shop_key="fionnen_gwynnel_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("fionnen_gwynnel_home"),
                dialogue_key="fionnen_gwynnel_home",
            ),
        ),
    ),
    PlaceDefinition(
        key="fionnen_ithrlin_home",
        settlement_key="elven_village_fionnen",
        kind=PlaceKind.HOME,
        room=interior_room_ref("fionnen_ithrlin_home", "fionnen_ithrlin_home"),
        host_name="伊斯爾林‧斯塔爾威維爾",
        host_race="elf",
        host_subrace="fionnen",
        host_sex="female",
        host_profile_key="fionnen_ithrlin",
        assortment_keys=("fionnen_attire",),
        components=(
            capability(
                "merchant",
                binding=place_bound("fionnen_ithrlin_home"),
                service_id="fionnen_ithrlin",
                shop_key="fionnen_ithrlin_home",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("fionnen_ithrlin_home"),
                dialogue_key="fionnen_ithrlin_home",
            ),
        ),
    ),
)
