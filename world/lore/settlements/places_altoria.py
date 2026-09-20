"""聖潔王都 (capital_altoria) place rows (settlement-shops design §6.1).

Transcribed from the constants in ``world/maps/bootstrap.py`` and the roster
rows removed from ``world/rules/rulebook/guild_economy.yaml``, so the derived
shops and service-host roster reproduce today's shipped identities exactly.

The tuple order is load-bearing: ``PLACE_REGISTRY`` preserves it, and the
derived roster must keep the [altoria_guild_master, altoria_merchant] order
the pre-change YAML shipped (sync iterates the roster in this order).
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
        exterior_xy=(3, 1),  # GUILD_HALL_EXTERIOR_XYZ
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
        exterior_xy=(1, 2),  # GENERAL_STORE_EXTERIOR_XYZ
        doorway_key_zh="雜貨店",
        doorway_aliases=("general store", "store", "shop"),
        host_name="瑪爾特·金秤",
        host_title="阿爾托利亞雜貨商店老闆",
        host_race="human",
        host_subrace=None,
        host_sex="other",
        profession="merchant",
        service_id="altoria_merchant",
        assortment_keys=(
            "common_arms", "common_outfits", "staple_meals",
            "general_sundries",
        ),
        authored_kwargs=(
            ("shop_key", "altoria_general_store"),
        ),
    ),
)