"""Immutable assortment identity registry (settlement-shops design §3.1).

An assortment is a named, reusable bundle of goods: stable key,
Traditional Chinese display name, and an immutable tuple of item keys as
its identity. Exact integer buy/sell copper, stock and restock quantities
for each item live in ``world/rules/rulebook/commerce.yaml`` and are joined
to these identities by the catalog loader in ``world/rules/guild_config.py``.
"""

from dataclasses import dataclass

#: The ``PRICE_TABLE`` band whose rows are one-of-a-kind keepsakes, never
#: traded (masterwork-gear-price-band states the rule; this package owns the
#: validator that enforces it via :data:`KEEPSAKE_BAND_KEY`).
KEEPSAKE_BAND_KEY = "relic"


@dataclass(frozen=True)
class AssortmentDefinition:
    """Immutable identity of one named goods bundle."""

    key: str
    display_name_zh: str
    item_keys: tuple[str, ...]


# The four capital assortments split the former 58-item general-store
# monolith along the axis the specialist shops now use: weapons, armour,
# food, and the remaining sundries (design §3.1, §10 change 2). The split
# is deliberately non-overlapping; the general store references sundries
# alone, and each specialist references exactly one other assortment
# (altoria-trading-places §6.1).
#
# The four elven-craft assortments serve 暗影谷村 (design §6.2, §10 change 7):
# each villager's home carries one shelf of what its host happens to make or
# collect. They share keys with the capital where the world document
# requires it — ``elven_spider_silk`` and ``elven_candied_blossom`` are also
# capital goods, offered in the village at everyday prices. Two shops
# offering one key through two different assortments is the case this model
# exists to serve; only one shop referencing two overlapping assortments is
# rejected (design §4.1).
ASSORTMENT_REGISTRY: dict[str, AssortmentDefinition] = {
    definition.key: definition
    for definition in (
        AssortmentDefinition(
            key="common_arms",
            display_name_zh="王都兵器",
            item_keys=(
                "plain_sword", "iron_dagger", "hunting_throwing_axe",
                "hunters_longbow", "apprentice_focus_staff", "knight_blade",
                "magic_sword",
            ),
        ),
        AssortmentDefinition(
            key="common_outfits",
            display_name_zh="王都衣甲",
            item_keys=(
                "leather_armor", "mage_robe", "chainmail", "iron_shield",
                "knight_platemail", "archmage_mending_robe",
                "enticing_lace_set", "sister_vestments", "saintess_vestments",
            ),
        ),
        AssortmentDefinition(
            key="staple_meals",
            display_name_zh="王都飯食",
            item_keys=(
                "meal", "kingdom_rye_hardtack", "adventurer_field_ration",
                "imperial_candied_fruit", "beastfolk_smoked_jerky",
                "harbor_lobster_bisque", "elven_candied_blossom",
            ),
        ),
        AssortmentDefinition(
            key="general_sundries",
            display_name_zh="王都雜貨",
            item_keys=(
                "healing_potion", "silver_hairpin", "wolf_fang_necklace",
                "pilgrim_medallion", "protective_ring", "storage_pouch",
                "gliding_cloak", "magic_lamp", "healing_herb",
                "rough_iron_ore", "beast_crystal", "evernight_shard",
                "mana_core", "dragon_scale_fragment", "elven_spider_silk",
                "baptismal_holy_water", "greater_healing_potion",
                "mana_potion", "purified_pendant", "fearless_brooch",
                "apothecary_beads", "passion_silk_choker",
                "radiant_holy_emblem", "enchanted_compass",
                "dungeon_flare_talisman", "beastfolk_signal_conch",
                "camp_ward_kit", "goblin_ear", "slime_residue",
                "earth_drake_scale", "troll_fang", "miners_bracing_broth",
                "beastfolk_herbal_salve", "passion_draught", "spirit_dew",
            ),
        ),
        AssortmentDefinition(
            key="elven_crafted_arms",
            display_name_zh="精靈兵刃",
            item_keys=(
                "shadow_blade", "shadow_blade_echo",
            ),
        ),
        AssortmentDefinition(
            key="elven_attire",
            display_name_zh="精靈衣飾",
            item_keys=(
                "dark_elf_kimono", "dark_elf_ninja_garb",
                "elven_traditional_robe", "elven_forest_veil",
            ),
        ),
        AssortmentDefinition(
            key="elven_fare",
            display_name_zh="精靈飯食",
            item_keys=(
                "elven_candied_blossom",
            ),
        ),
        AssortmentDefinition(
            key="elven_sundries",
            display_name_zh="精靈雜貨",
            item_keys=(
                "elven_spider_silk", "crescent_earring",
            ),
        ),
    )
}