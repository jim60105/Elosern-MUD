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
``world/lore/dialogue/altoria.py`` under the same keys.
"""

from world.lore.settlements.places import PlaceDefinition, PlaceKind

ROWS: tuple[PlaceDefinition, ...] = (
    PlaceDefinition(
        key="altoria_guild_hall",
        settlement_key="capital_altoria",
        kind=PlaceKind.GUILD_HALL,
        room_name_zh="阿爾托利亞冒險者公會大廳",
        room_desc_zh=(
            "The guild hall of 阿爾托利亞, with a grand board and a training "
            "ring (guild-economy D-9)."
        ),
        exterior_xy=(4, 3),  # 公會前
        doorway_key_zh="冒險者公會大廳",
        doorway_aliases=("guild hall", "hall"),
        host_name="葛里安·衛登",
        host_title="阿爾托利亞分會會長",
        host_race="human",
        host_subrace=None,
        host_sex="other",
        profession="guild_staff",
        service_id="altoria_guild_master",
        assortment_keys=(),
        authored_kwargs=(
            ("branch_key", "guild_branch_altoria"),
            ("dialogue_key", "guild_staff"),
        ),
    ),
    PlaceDefinition(
        key="altoria_general_store",
        settlement_key="capital_altoria",
        kind=PlaceKind.GENERAL_STORE,
        room_name_zh="阿爾托利亞雜貨店",
        room_desc_zh=(
            "The general store of 阿爾托利亞, its shelves waiting for the "
            "next caravan (guild-economy D-9)."
        ),
        exterior_xy=(2, 3),  # 市場街
        doorway_key_zh="雜貨店",
        doorway_aliases=("general store", "store", "shop"),
        host_name="瑪爾特·金秤",
        host_title="阿爾托利亞雜貨商店老闆",
        host_race="human",
        host_subrace=None,
        host_sex="other",
        profession="merchant",
        service_id="altoria_merchant",
        # The 58-item monolith split along the specialist axis
        # (commerce-assortment-registry): the general store keeps the
        # sundries shelf, the specialists take weapons, food and armour.
        assortment_keys=("general_sundries",),
        authored_kwargs=(
            ("shop_key", "altoria_general_store"),
            ("dialogue_key", "altoria_general_store"),
        ),
    ),
    PlaceDefinition(
        key="altoria_forge",
        settlement_key="capital_altoria",
        kind=PlaceKind.WEAPONSMITH,
        room_name_zh="聖潔王都鍛造鋪",
        room_desc_zh=(
            "The forge of 聖潔王都, its anvil ringing under the capital's "
            "weapons trade (settlement-shops design §6.1)."
        ),
        exterior_xy=(1, 3),  # 工匠巷
        doorway_key_zh="鍛造鋪",
        doorway_aliases=("forge", "smithy"),
        host_name="維爾登·黑潭",
        host_title="聖潔王都鍛造鋪鐵匠",
        host_race="human",
        host_subrace="human_plains",
        host_sex="male",
        profession="merchant",
        service_id="altoria_blacksmith",
        assortment_keys=("common_arms",),
        authored_kwargs=(
            ("shop_key", "altoria_forge"),
            ("dialogue_key", "altoria_forge"),
        ),
    ),
    PlaceDefinition(
        key="altoria_tailor",
        settlement_key="capital_altoria",
        kind=PlaceKind.OUTFITTER,
        room_name_zh="聖潔王都裁縫坊",
        room_desc_zh=(
            "The tailor's workshop of 聖潔王都, bolts of cloth beside the "
            "noble commissions of 北大道 (settlement-shops design §6.1)."
        ),
        exterior_xy=(1, 3),  # 工匠巷
        doorway_key_zh="裁縫坊",
        doorway_aliases=("tailor", "tailor shop"),
        host_name="妮絲塔·狐溪",
        host_title="聖潔王都裁縫坊坊主",
        host_race="human",
        host_subrace="human_plains",
        host_sex="female",
        profession="merchant",
        service_id="altoria_tailor",
        assortment_keys=("common_outfits",),
        authored_kwargs=(
            ("shop_key", "altoria_tailor"),
            ("dialogue_key", "altoria_tailor"),
        ),
    ),
)
