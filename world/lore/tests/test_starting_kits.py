"""Data-contract test: starting-kit data contract
Registry contract tests for the subrace starting-kit catalog."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.items import ITEM_REGISTRY, ItemRarity
from world.lore.races import SUBRACE_REGISTRY
from world.lore.starting_kits import (
    SUBRACE_STARTING_KIT_REGISTRY,
    SubraceStartingKit,
    _validate_starting_kit,
    _validate_starting_kit_coverage,
)


class SubraceStartingKitTests(unittest.TestCase):
    @covers_requirement(
        "player-character-creation::every-subrace-has-a-validated-basic-starting-equipment-kit-in-the-item-catalog"
    )
    def test_kit_keys_exactly_cover_the_subrace_registry(self):
        self.assertEqual(
            set(SUBRACE_STARTING_KIT_REGISTRY), set(SUBRACE_REGISTRY)
        )

    @covers_requirement(
        "player-character-creation::every-subrace-has-a-validated-basic-starting-equipment-kit-in-the-item-catalog"
    )
    def test_every_kit_is_a_non_empty_set_of_registered_equipment(self):
        for subrace_key, kit in SUBRACE_STARTING_KIT_REGISTRY.items():
            with self.subTest(subrace=subrace_key):
                self.assertTrue(kit.items)
                for item_key, quantity in kit.items:
                    definition = ITEM_REGISTRY[item_key]
                    self.assertIsNotNone(
                        definition.equipment_slot,
                        f"kit {subrace_key!r} must be equipment-only",
                    )
                    self.assertGreaterEqual(quantity, 1)
                self.assertEqual(
                    kit.inventory_list(),
                    [
                        key
                        for key, qty in kit.items
                        for _ in range(qty)
                    ],
                )

    @covers_requirement(
        "player-character-creation::every-subrace-has-a-validated-basic-starting-equipment-kit-in-the-item-catalog"
    )
    def test_basic_items_are_shared_across_kits(self):
        shared = SubraceStartingKit(
            "wolfkin", (("leather_armor", 1), ("plain_sword", 1))
        )
        borrowed = {
            key: SUBRACE_STARTING_KIT_REGISTRY[key]
            for key in SUBRACE_REGISTRY
        }
        borrowed["wolfkin"] = shared
        _validate_starting_kit_coverage(borrowed)

    @covers_requirement(
        "player-character-creation::every-subrace-has-a-validated-basic-starting-equipment-kit-in-the-item-catalog"
    )
    def test_kit_validation_rejects_malformed_unknown_and_non_equipment_entries(self):
        cases = [
            (
                "mismatched-key",
                SubraceStartingKit("other_subrace", (("plain_sword", 1),)),
                "mismatched subrace",
            ),
            (
                "not-a-kit",
                ("human_plains", (("plain_sword", 1),)),
                "must be a SubraceStartingKit",
            ),
            (
                "empty-kit",
                SubraceStartingKit("human_plains", ()),
                "non-empty",
            ),
            (
                "items-not-tuple",
                SubraceStartingKit("human_plains", ["plain_sword"]),
                "non-empty tuple",
            ),
            (
                "malformed-entry",
                SubraceStartingKit("human_plains", (("plain_sword",),)),
                "malformed item entry",
            ),
            (
                "unknown-item",
                SubraceStartingKit("human_plains", (("not_an_item", 1),)),
                "unknown item",
            ),
            (
                "non-string-item",
                SubraceStartingKit("human_plains", ((["plain_sword"], 1),)),
                "unknown item",
            ),
            (
                "non-equipment-item",
                SubraceStartingKit("human_plains", (("meal", 1),)),
                "non-equipment item",
            ),
            (
                "duplicate-item",
                SubraceStartingKit(
                    "human_plains",
                    (("leather_armor", 1), ("leather_armor", 2)),
                ),
                "duplicate item",
            ),
            (
                "zero-quantity",
                SubraceStartingKit("human_plains", (("plain_sword", 0),)),
                "non-positive quantity",
            ),
            (
                "string-quantity",
                SubraceStartingKit("human_plains", (("plain_sword", "2"),)),
                "non-positive quantity",
            ),
            (
                "boolean-quantity",
                SubraceStartingKit("human_plains", (("plain_sword", True),)),
                "non-positive quantity",
            ),
        ]
        for name, kit, message in cases:
            with self.subTest(case=name):
                with self.assertRaisesRegex(ValueError, message):
                    _validate_starting_kit("human_plains", kit)
        _validate_starting_kit(
            "human_plains",
            SubraceStartingKit(
                "human_plains", (("leather_armor", 2), ("plain_sword", 1))
            ),
        )

    @covers_requirement(
        "player-character-creation::every-subrace-has-a-validated-basic-starting-equipment-kit-in-the-item-catalog"
    )
    def test_coverage_validation_rejects_missing_and_unknown_subraces(self):
        missing = {
            key: SUBRACE_STARTING_KIT_REGISTRY[key]
            for key in SUBRACE_REGISTRY
            if key != "human_plains"
        }
        with self.assertRaisesRegex(ValueError, "missing subrace"):
            _validate_starting_kit_coverage(missing)
        unknown = dict(SUBRACE_STARTING_KIT_REGISTRY)
        unknown["dragonkin"] = SubraceStartingKit(
            "dragonkin", (("plain_sword", 1),)
        )
        with self.assertRaisesRegex(ValueError, "unknown subrace"):
            _validate_starting_kit_coverage(unknown)

    @covers_requirement(
        "player-character-creation::custom-activation-grants-the-chosen-subrace-s-basic-starting-kit"
    )
    def test_colliding_or_accessory_overflowing_kit_fails_at_registry_load(self):
        # Scenario "A colliding or accessory-overflowing kit fails at registry
        # load" (custom-kit-worn-at-activation): once custom activation wears
        # every kit item, an unwearable kit is a failed player activation, so
        # the wearable-set rules run at load. Pinning the coverage validator is
        # pinning the import: _validate_starting_kit_coverage is the module-
        # level call that makes importing world.lore.starting_kits raise.
        colliding = SubraceStartingKit(
            # plain_sword and hunters_longbow are both weapon_main items.
            "human_plains",
            (("plain_sword", 1), ("hunters_longbow", 1)),
        )
        overflowing = SubraceStartingKit(
            # Six carried accessories exceed ACCESSORY_MAX_SLOTS (5).
            "human_plains",
            (
                ("wolf_fang_necklace", 1),
                ("pilgrim_medallion", 1),
                ("protective_ring", 1),
                ("prism_charm", 1),
                ("storage_pouch", 1),
                ("gliding_cloak", 1),
            ),
        )
        for name, kit in (("colliding", colliding), ("overflowing", overflowing)):
            with self.subTest(kit=name):
                with self.assertRaisesRegex(ValueError, "starting kit"):
                    _validate_starting_kit("human_plains", kit)
                registry = dict(SUBRACE_STARTING_KIT_REGISTRY)
                registry["human_plains"] = kit
                with self.assertRaisesRegex(ValueError, "starting kit"):
                    _validate_starting_kit_coverage(registry)

    def test_inventory_list_flattens_by_quantity_in_declared_order(self):
        kit = SubraceStartingKit(
            "human_plains",
            (("leather_armor", 2), ("plain_sword", 1)),
        )
        self.assertEqual(
            kit.inventory_list(),
            ["leather_armor", "leather_armor", "plain_sword"],
        )

    @covers_requirement("lore-registries::human-starting-kits-express-lineage-character-not-an-affluence-ladder")
    def test_human_kits_match_the_lineage_table(self):
        expected = {
            "human_royal": ("gilded_saber", "chainmail", "silver_hairpin"),
            "human_noble": ("knight_blade", "leather_armor", "silver_hairpin"),
            "human_coastal": ("plain_sword", "leather_armor", "iron_dagger"),
            "human_plains": ("plain_sword", "leather_armor", "silver_hairpin"),
            "human_highland": ("plain_sword", "leather_armor", "hunting_throwing_axe"),
        }
        for subrace_key, item_keys in expected.items():
            with self.subTest(subrace=subrace_key):
                kit = SUBRACE_STARTING_KIT_REGISTRY[subrace_key]
                self.assertEqual(tuple(key for key, _ in kit.items), item_keys)
        # The three commoner lineages are equipotent: three COMMON items each,
        # so no commoner lineage starts richer than another.
        for subrace_key in ("human_coastal", "human_plains", "human_highland"):
            kit = SUBRACE_STARTING_KIT_REGISTRY[subrace_key]
            with self.subTest(subrace=subrace_key):
                self.assertEqual(len(kit.items), 3)
                for item_key, _ in kit.items:
                    self.assertEqual(
                        ITEM_REGISTRY[item_key].presentation.rarity,
                        ItemRarity.COMMON,
                        f"{subrace_key} kit item {item_key!r} must be COMMON",
                    )
        # 木製棍棒 is retired from every kit.
        for subrace_key, kit in SUBRACE_STARTING_KIT_REGISTRY.items():
            with self.subTest(subrace=subrace_key):
                self.assertNotIn("wooden_club", tuple(key for key, _ in kit.items))


if __name__ == "__main__":
    unittest.main()
