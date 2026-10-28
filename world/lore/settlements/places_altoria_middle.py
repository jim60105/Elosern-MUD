"""聖潔王都 (capital_altoria) MIDDLE-terrace place rows (settlement-shops design §6.1).

The middle terrace is the city's civic and crafting ground between the old
lower town and the noble upper heights (docs/lore/settlement-locations.md):
the adventurer guild, the general store, and the craft alley where 鍛造鋪 and
裁縫坊 share one exterior under two doorway names (altoria-capital-replan).

The guild hall and general store are transcribed from the constants in
``world/maps/bootstrap.py`` and the roster rows removed from
``world/rules/rulebook/guild_economy.yaml``, so the derived shops and
service-host roster reproduce the pre-change shipped identities exactly. The
two specialist shops (聖潔王都鍛造鋪 / 聖潔王都裁縫坊) are authored content:
their interiors, hosts and assortments exist only here and in
``world/rules/rulebook/commerce/altoria.yaml``.

The assembled tuple order is load-bearing (see the assembly comment in
``places.py``): this slice follows the lower terrace and precedes the upper,
so its rows reach the derived roster between them.

Merchant rows carry a ``dialogue_key`` beside their ``shop_key``: the merchant
blueprint answers as well as trades (merchant-dialogue), and a merchant place
without the kwarg fails load naming the place. The tables live in
``world/lore/dialogue/altoria_middle.py`` under the same keys.

altoria-learning-and-exchange appends the capital's last two middle-terrace
rooms: 聖潔王都商會公所 off 東市 — the document's designated future source
of escort commissions, landed here as an attendant host who talks caravans
and trade routes and offers no work, because the escort quest type the
commissions need does not exist — and 聖潔王都市集棚 off 市場街, the
capital's second host-less place, host-less on the document's authority
rather than on an unwritten story: 「市場街本身不需要一位固定的街長型功能性
NPC，遊戲性功能都掛在各個攤販身上」 (docs/lore/settlement-locations.md
line 374). 市場街 now carries three doors (雜貨店、首飾坊、市集棚) and 東市
two (鍊金坊、商會公所); the registry's doorway-name rule keeps them honest.
"""

from world.lore.settlements.places import PlaceDefinition, PlaceKind
from world.lore.settlements.capability_declarations import (
    capability,
    place_bound,
)
from elosern_map_core.references import interior_room_ref

ROWS: tuple[PlaceDefinition, ...] = (
    PlaceDefinition(
        key="altoria_hok_home", settlement_key="capital_altoria",
        kind=PlaceKind.HOME,
        room=interior_room_ref("altoria_hok_home", "altoria_hok_home"),
    ),
    PlaceDefinition(
        key="altoria_cassandra_home", settlement_key="capital_altoria",
        kind=PlaceKind.HOME,
        room=interior_room_ref("altoria_cassandra_home", "altoria_cassandra_home"),
    ),
    PlaceDefinition(
        key="altoria_augustine_home", settlement_key="capital_altoria",
        kind=PlaceKind.HOME,
        room=interior_room_ref("altoria_augustine_home", "altoria_augustine_home"),
    ),
    PlaceDefinition(
        key="altoria_guild_hall",
        settlement_key="capital_altoria",
        kind=PlaceKind.GUILD_HALL,
        room=interior_room_ref("altoria_guild_hall", "altoria_guild_hall"),
        host_name="葛里安‧衛登",
        host_race="human",
        host_subrace=None,
        host_sex="other",
        host_profile_key="altoria_guild_master",
        assortment_keys=(),
        components=(
            capability(
                "guild_staff",
                binding=place_bound("altoria_guild_hall"),
                service_id="altoria_guild_master",
                branch_key="guild_branch_altoria",
            ),
            capability(
                "guild_exam_reception",
                binding=place_bound("altoria_guild_hall"),
                service_id="altoria_guild_master",
                branch_key="guild_branch_altoria",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_guild_hall"),
                dialogue_key="guild_staff",
            ),
        ),
    ),
    PlaceDefinition(
        key="altoria_general_store",
        settlement_key="capital_altoria",
        kind=PlaceKind.GENERAL_STORE,
        room=interior_room_ref("altoria_general_store", "altoria_general_store"),
        host_name="瑪爾特‧金秤",
        host_race="human",
        host_subrace=None,
        host_sex="other",
        host_profile_key="altoria_merchant",
        # The 58-item monolith split along the specialist axis
        # (commerce-assortment-registry): the general store keeps the
        # sundries shelf, the specialists take weapons, food and armour.
        assortment_keys=("general_sundries",),
        components=(
            capability(
                "merchant",
                binding=place_bound("altoria_general_store"),
                service_id="altoria_merchant",
                shop_key="altoria_general_store",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_general_store"),
                dialogue_key="altoria_general_store",
            ),
        ),
    ),
    PlaceDefinition(
        key="altoria_forge",
        settlement_key="capital_altoria",
        kind=PlaceKind.WEAPONSMITH,
        room=interior_room_ref("altoria_forge", "altoria_forge"),
        host_name="維爾登‧黑潭",
        host_race="human",
        host_subrace="human_plains",
        host_sex="male",
        host_profile_key="altoria_blacksmith",
        assortment_keys=("common_arms",),
        components=(
            capability(
                "merchant",
                binding=place_bound("altoria_forge"),
                service_id="altoria_blacksmith",
                shop_key="altoria_forge",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_forge"),
                dialogue_key="altoria_forge",
            ),
        ),
    ),
    PlaceDefinition(
        key="altoria_tailor",
        settlement_key="capital_altoria",
        kind=PlaceKind.OUTFITTER,
        room=interior_room_ref("altoria_tailor", "altoria_tailor"),
        host_name="妮絲塔‧狐溪",
        host_race="human",
        host_subrace="human_plains",
        host_sex="female",
        host_profile_key="altoria_tailor",
        assortment_keys=("common_outfits",),
        components=(
            capability(
                "merchant",
                binding=place_bound("altoria_tailor"),
                service_id="altoria_tailor",
                shop_key="altoria_tailor",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_tailor"),
                dialogue_key="altoria_tailor",
            ),
        ),
    ),
    # altoria-adornments-and-remedies: the last two specialists of the
    # forge/eatery/tailor family. The jeweller shares 市場街 with the general
    # store — one exterior, two doors, distinguished by their authored
    # doorway names (雜貨店 vs 首飾坊).
    PlaceDefinition(
        key="altoria_jeweller",
        settlement_key="capital_altoria",
        kind=PlaceKind.JEWELLER,
        room=interior_room_ref("altoria_jeweller", "altoria_jeweller"),
        host_name="艾蓮娜‧鴉丘",
        host_race="human",
        host_subrace="human_plains",
        host_sex="female",
        host_profile_key="altoria_jeweller",
        assortment_keys=("capital_adornments",),
        components=(
            capability(
                "merchant",
                binding=place_bound("altoria_jeweller"),
                service_id="altoria_jeweller",
                shop_key="altoria_jeweller",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_jeweller"),
                dialogue_key="altoria_jeweller",
            ),
        ),
    ),
    PlaceDefinition(
        key="altoria_alchemist",
        settlement_key="capital_altoria",
        kind=PlaceKind.ALCHEMIST,
        room=interior_room_ref("altoria_alchemist", "altoria_alchemist"),
        host_name="希碧拉‧灰沼",
        host_race="human",
        host_subrace="human_plains",
        host_sex="female",
        host_profile_key="altoria_alchemist",
        assortment_keys=("capital_remedies",),
        components=(
            capability(
                "merchant",
                binding=place_bound("altoria_alchemist"),
                service_id="altoria_alchemist",
                shop_key="altoria_alchemist",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_alchemist"),
                dialogue_key="altoria_alchemist",
            ),
        ),
    ),
    # 聖潔王都商會公所 — the merchants' guild hall, off 東市 (5,3), sharing
    # that exterior with the alchemist under a different doorway name
    # (鍊金坊 vs 商會公所). The document's 商會與貿易行 is 「未來的」護衛委託
    # 發放處 and 「guild request」 already reports escort work closed: the
    # guild master talks caravans, routes and tariffs as world-building and
    # offers nothing — a commission surface without the escort quest type
    # behind it would post work that cannot be completed, so this row ships
    # an attendant's dialogue table and no work board (design refusal two).
    PlaceDefinition(
        key="altoria_merchant_hall",
        settlement_key="capital_altoria",
        kind=PlaceKind.MERCHANT_HALL,
        room=interior_room_ref("altoria_merchant_hall", "altoria_merchant_hall"),
        host_name="尤斯汀‧柯德溫",
        host_race="human",
        host_subrace=None,
        host_sex="male",
        host_profile_key="altoria_merchant_master",
        assortment_keys=(),
        components=(
            capability(
                "scripted_dialogue",
                binding=place_bound("altoria_merchant_hall"),
                dialogue_key="altoria_merchant_hall",
            ),
        ),
    ),
    # 聖潔王都市集棚 — the covered market stalls, off 市場街 (2,3), sharing
    # that exterior with the general store and the jeweller under a third
    # doorway name (雜貨店 vs 首飾坊 vs 市集棚). Host-less on the document's
    # authority, not by omission: line 374 says a market street's function
    # hangs on individual stallholders, not on a fixed street-chief NPC, so
    # this emptiness is a design statement, not the palace's unwritten
    # story. When stallholders arrive they will be transient scene NPCs on
    # the quest path — the same rooms-only shape hostless-places reserves,
    # with no permanent roster row expected behind it.
    PlaceDefinition(
        key="altoria_market_stalls",
        settlement_key="capital_altoria",
        kind=PlaceKind.MARKET,
        room=interior_room_ref("altoria_market_stalls", "altoria_market_stalls"),
    ),
)
