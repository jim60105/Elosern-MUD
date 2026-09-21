"""Data-contract test: assortment registry content contract
Self-consistency checks for the assortment registry (settlement-shops design
§3.1): the four capital bundles split the former 58-item general-store
monolith along the weapons/armour/food/sundries axis, non-overlapping, with
every item known to the item registry; the six elven bundles serve 暗影谷村's
homes (design §6.2) and deliberately share four keys with the capital —
`elven_spider_silk`, `elven_candied_blossom`, `greater_healing_potion` and
`mana_potion` — because two shops offering
one key through two different assortments is the model working, not a
duplicate (design §4.1). Borderline assignments are deliberate and stable:
`iron_shield` (armor band, off-hand) lives in outfits not arms; the potion
consumables `miners_bracing_broth`, `beastfolk_herbal_salve`, `passion_draught`
stay in sundries rather than staple_meals — the first three moved to
capital_remedies with altoria-adornments-and-remedies, while `spirit_dew`
remains a sundries material; the elven jewellery (`crescent_earring`) rides
the adornment maker's shelf (elven_adornments, moved there by
ciaran-village-crafts)."""

import unittest

from tools.spec_traceability import covers_requirement

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

    def test_registry_carries_the_four_capital_and_six_elven_assortments(self):
        self.assertEqual(
            list(ASSORTMENT_REGISTRY),
            [
                "common_arms", "common_outfits", "staple_meals",
                "general_sundries", "capital_adornments", "capital_remedies",
                "elven_crafted_arms", "elven_attire",
                "elven_fare", "elven_sundries",
                "elven_adornments", "elven_remedies",
            ],
        )

    def test_definitions_are_frozen(self):
        import dataclasses

        for definition in ASSORTMENT_REGISTRY.values():
            self.assertTrue(dataclasses.is_dataclass(definition))
            self.assertTrue(dataclasses.is_dataclass(definition) and definition.__dataclass_params__.frozen)

    def test_capital_union_of_items_is_exactly_the_pre_split_offered_set(self):
        union = [
            item_key
            for definition in (
                ASSORTMENT_REGISTRY["common_arms"],
                ASSORTMENT_REGISTRY["common_outfits"],
                ASSORTMENT_REGISTRY["staple_meals"],
                ASSORTMENT_REGISTRY["general_sundries"],
                ASSORTMENT_REGISTRY["capital_adornments"],
                ASSORTMENT_REGISTRY["capital_remedies"],
            )
            for item_key in definition.item_keys
        ]
        self.assertEqual(set(union), set(PRE_SPLIT_OFFERED_KEYS))
        self.assertEqual(len(union), len(PRE_SPLIT_OFFERED_KEYS))

    def test_no_item_lives_in_two_capital_assortments(self):
        owner: dict[str, str] = {}
        for definition in (
            ASSORTMENT_REGISTRY["common_arms"],
            ASSORTMENT_REGISTRY["common_outfits"],
            ASSORTMENT_REGISTRY["staple_meals"],
            ASSORTMENT_REGISTRY["general_sundries"],
            ASSORTMENT_REGISTRY["capital_adornments"],
            ASSORTMENT_REGISTRY["capital_remedies"],
        ):
            for item_key in definition.item_keys:
                self.assertNotIn(item_key, owner, f"{item_key!r} split across assortments")
                owner[item_key] = definition.key

    def test_elven_assortments_share_exactly_the_four_inherited_keys(self):
        # The village shelves are independent of the capital's except for the
        # goods the world document carries across: the silk (the design's
        # worked example), the candied blossom (蜜漬花蕊), and the two remedy
        # potions the hedge-healer keeps (ciaran-village-crafts). Two shops,
        # two assortments, one key, two prices — the case this model exists
        # for.
        elven_keys = {
            item_key
            for definition in ASSORTMENT_REGISTRY.values()
            if definition.key.startswith("elven_")
            for item_key in definition.item_keys
        }
        capital_keys = {
            item_key
            for definition in ASSORTMENT_REGISTRY.values()
            if not definition.key.startswith("elven_")
            for item_key in definition.item_keys
        }
        self.assertEqual(
            elven_keys & capital_keys,
            {
                "elven_spider_silk", "elven_candied_blossom",
                "greater_healing_potion", "mana_potion",
            },
        )

    def test_every_assortment_item_resolves_in_the_item_registry(self):
        for definition in ASSORTMENT_REGISTRY.values():
            for item_key in definition.item_keys:
                with self.subTest(assortment=definition.key, item=item_key):
                    self.assertIn(item_key, ITEM_REGISTRY)

    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-xyzgrid-remains-thirteen-exterior-nodes-while-permanent-service-interiors-are-attached"
    )
    def test_capital_shops_redistribute_the_pre_split_set_without_overlap(self):
        # The specialist split (altoria-trading-places §6.1, widened by
        # altoria-adornments-and-remedies until the general store sells only
        # what a general store sells) narrows each shop's shelf; the union
        # across every CAPITAL trading place must still equal the 58-key
        # pre-split offered set, with no key offered by two capital shops.
        # The village shops are out of scope here: they deliberately share
        # keys with the capital through their own assortments (design §4.1).
        from world.lore.settlements.shops import SHOP_REGISTRY

        union: list[str] = []
        owner: dict[str, str] = {}
        for shop_key, shop in SHOP_REGISTRY.items():
            if not shop_key.startswith("altoria_"):
                continue
            for item_key in shop.offered_item_keys:
                self.assertNotIn(
                    item_key,
                    owner,
                    f"{item_key!r} offered by both {owner.get(item_key)!r} and "
                    f"{shop.key!r}",
                )
                owner[item_key] = shop.key
                union.append(item_key)
        self.assertEqual(set(union), set(PRE_SPLIT_OFFERED_KEYS))
        self.assertEqual(len(union), len(PRE_SPLIT_OFFERED_KEYS))

    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-xyzgrid-remains-thirteen-exterior-nodes-while-permanent-service-interiors-are-attached"
    )
    def test_adornments_bundle_is_exactly_the_capital_accessory_slot_goods(self):
        # The partition RULE, computed from both sides: the adornments
        # bundle is defined as the capital's accessory-slot goods, so an
        # accessory the capital sells and the bundle omits is a gap, and a
        # non-accessory inside it is a leak. Neither side is a literal list:
        # the offered set comes from the derived shop registry, the slot
        # from the item registry's own equipment_slot — the data nobody can
        # drift by accident when the next accessory lands.
        from world.lore.settlements.shops import SHOP_REGISTRY
        from world.skills.equipment import EquipmentSlot

        capital_accessories = {
            item_key
            for shop in SHOP_REGISTRY.values()
            if shop.key.startswith("altoria_")
            for item_key in shop.offered_item_keys
            if ITEM_REGISTRY[item_key].equipment_slot is EquipmentSlot.ACCESSORY
        }
        adornments = set(ASSORTMENT_REGISTRY["capital_adornments"].item_keys)
        self.assertEqual(capital_accessories, adornments)
        # The mirror half of the equality, stated separately so a bundle
        # widened with a non-accessory names itself in the failure: no
        # accessory-slot key may sit in ANOTHER capital bundle either.
        for definition in ASSORTMENT_REGISTRY.values():
            if definition.key.startswith("elven_") or definition.key == "capital_adornments":
                continue
            for item_key in definition.item_keys:
                self.assertIsNot(
                    ITEM_REGISTRY[item_key].equipment_slot,
                    EquipmentSlot.ACCESSORY,
                    f"{item_key!r} equips to the accessory slot but sits in "
                    f"{definition.key!r}, not the adornments bundle",
                )

    def test_display_names_are_traditional_chinese(self):
        for definition in ASSORTMENT_REGISTRY.values():
            with self.subTest(assortment=definition.key):
                self.assertTrue(definition.display_name_zh)


if __name__ == "__main__":
    unittest.main()