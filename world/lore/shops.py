"""Immutable shop identity registry for the deterministic economy (guild-economy D-8).

Shop definitions carry stable identity and offered item keys only; exact
prices, hours, and stock quantities live in
``world/rules/rulebook/guild_economy.yaml``.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ShopDefinition:
    """Immutable identity of one deterministic shop."""

    key: str
    merchant_component_key: str
    offered_item_keys: tuple[str, ...]


SHOP_REGISTRY: dict[str, ShopDefinition] = {
    definition.key: definition
    for definition in (
        ShopDefinition(
            key="altoria_general_store",
            merchant_component_key="merchant",
            offered_item_keys=(
                "meal", "healing_potion", "plain_sword",
                "iron_dagger", "hunting_throwing_axe", "hunters_longbow", "apprentice_focus_staff", "knight_blade", "magic_sword", "leather_armor", "mage_robe", "chainmail", "iron_shield", "silver_hairpin", "wolf_fang_necklace", "pilgrim_medallion", "protective_ring", "storage_pouch", "gliding_cloak", "magic_lamp", "healing_herb", "rough_iron_ore", "beast_crystal", "evernight_shard", "mana_core", "dragon_scale_fragment", "elven_spider_silk", "baptismal_holy_water", "greater_healing_potion", "mana_potion",
                "purified_pendant", "fearless_brooch", "knight_platemail", "apothecary_beads", "archmage_mending_robe", "enticing_lace_set", "passion_silk_choker", "sister_vestments", "radiant_holy_emblem", "saintess_vestments",
            ),
        ),
    )
}