"""Data-contract test: assortment registry content contract
Self-consistency checks for the capital assortment registry (settlement-shops
design §3.1): the four bundles split the former 58-item general-store monolith
along the weapons/armour/food/sundries axis, non-overlapping, with every item
known to the item registry. Borderline assignments are deliberate and stable:
`iron_shield` (armor band, off-hand) lives in outfits not arms; the potion
consumables `miners_bracing_broth`, `beastfolk_herbal_salve`, `passion_draught`
and `spirit_dew` stay in sundries rather than staple_meals; the jewellery and
magic accessories wait in sundries for the unbuilt specialist shops."""

import unittest

from world.lore.items import ITEM_REGISTRY
from world.lore.settlements.assortments import ASSORTMENT_REGISTRY, AssortmentDefinition


# The exact pre-change offered set of `altoria_general_store` (the 58-key
# monolith this registry redistributes). Keeping the literal here is what
# turns "appears to cover the store" into "covers the store exactly".
PRE_SPLIT_OFFERED_KEYS = (
    "meal", "healing_potion", "plain_sword",
    "iron_dagger", "hunting_throwing_axe", "hunters_longbow",
    "apprentice_focus_staff", "knight_blade", "magic_sword",
    "leather_armor", "mage_robe", "chainmail", "iron_shield",
    "silver_hairpin", "wolf_fang_necklace", "pilgrim_medallion",
    "protective_ring", "storage_pouch", "gliding_cloak", "magic_lamp",
    "healing_herb", "rough_iron_ore", "beast_crystal", "evernight_shard",
    "mana_core", "dragon_scale_fragment", "elven_spider_silk",
    "baptismal_holy_water", "greater_healing_potion", "mana_potion",
    "purified_pendant", "fearless_brooch", "knight_platemail",
    "apothecary_beads", "archmage_mending_robe", "enticing_lace_set",
    "passion_silk_choker", "sister_vestments", "radiant_holy_emblem",
    "saintess_vestments", "kingdom_rye_hardtack", "adventurer_field_ration",
    "imperial_candied_fruit", "beastfolk_smoked_jerky",
    "harbor_lobster_bisque", "elven_candied_blossom", "miners_bracing_broth",
    "beastfolk_herbal_salve", "passion_draught", "spirit_dew",
    "enchanted_compass", "dungeon_flare_talisman", "beastfolk_signal_conch",
    "camp_ward_kit", "goblin_ear", "slime_residue", "earth_drake_scale",
    "troll_fang",
)


class AssortmentRegistryTests(unittest.TestCase):
    """Assortment identity is immutable, keyed, and covers the store exactly."""

    def test_registry_is_keyed_by_definition_key(self):
        self.assertEqual(
            list(ASSORTMENT_REGISTRY), [definition.key for definition in ASSORTMENT_REGISTRY.values()]
        )

    def test_registry_carries_the_four_capital_assortments(self):
        self.assertEqual(
            list(ASSORTMENT_REGISTRY),
            ["common_arms", "common_outfits", "staple_meals", "general_sundries"],
        )

    def test_definitions_are_frozen(self):
        import dataclasses

        for definition in ASSORTMENT_REGISTRY.values():
            self.assertTrue(dataclasses.is_dataclass(definition))
            self.assertTrue(dataclasses.is_dataclass(definition) and definition.__dataclass_params__.frozen)

    def test_union_of_items_is_exactly_the_pre_split_offered_set(self):
        union = [
            item_key
            for definition in ASSORTMENT_REGISTRY.values()
            for item_key in definition.item_keys
        ]
        self.assertEqual(set(union), set(PRE_SPLIT_OFFERED_KEYS))
        self.assertEqual(len(union), len(PRE_SPLIT_OFFERED_KEYS))

    def test_no_item_lives_in_two_assortments(self):
        owner: dict[str, str] = {}
        for definition in ASSORTMENT_REGISTRY.values():
            for item_key in definition.item_keys:
                self.assertNotIn(item_key, owner, f"{item_key!r} split across assortments")
                owner[item_key] = definition.key

    def test_every_assortment_item_resolves_in_the_item_registry(self):
        for definition in ASSORTMENT_REGISTRY.values():
            for item_key in definition.item_keys:
                with self.subTest(assortment=definition.key, item=item_key):
                    self.assertIn(item_key, ITEM_REGISTRY)

    def test_display_names_are_traditional_chinese(self):
        for definition in ASSORTMENT_REGISTRY.values():
            with self.subTest(assortment=definition.key):
                self.assertTrue(definition.display_name_zh)


if __name__ == "__main__":
    unittest.main()