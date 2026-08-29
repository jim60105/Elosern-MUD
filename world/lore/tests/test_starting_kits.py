"""Registry contract tests for the subrace starting-kit catalog."""

import unittest

from world.lore.items import ITEM_REGISTRY
from world.lore.races import SUBRACE_REGISTRY
from world.lore.starting_kits import (
    SUBRACE_STARTING_KIT_REGISTRY,
    SubraceStartingKit,
    _validate_starting_kit,
    _validate_starting_kit_coverage,
)


class SubraceStartingKitTests(unittest.TestCase):
    def test_kit_keys_exactly_cover_the_subrace_registry(self):
        self.assertEqual(
            set(SUBRACE_STARTING_KIT_REGISTRY), set(SUBRACE_REGISTRY)
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

    def test_kit_validation_rejects_malformed_unknown_and_non_equipment_entries(self):
        cases = [
            (
                "mismatched-key",
                SubraceStartingKit("other_subrace", (("plain_sword", 1),)),
                "mismatched subrace",
            ),
            (
                "not-a-kit",
                ("human_commoner", (("plain_sword", 1),)),
                "must be a SubraceStartingKit",
            ),
            (
                "empty-kit",
                SubraceStartingKit("human_commoner", ()),
                "non-empty",
            ),
            (
                "items-not-tuple",
                SubraceStartingKit("human_commoner", ["plain_sword"]),
                "non-empty tuple",
            ),
            (
                "malformed-entry",
                SubraceStartingKit("human_commoner", (("plain_sword",),)),
                "malformed item entry",
            ),
            (
                "unknown-item",
                SubraceStartingKit("human_commoner", (("not_an_item", 1),)),
                "unknown item",
            ),
            (
                "non-string-item",
                SubraceStartingKit("human_commoner", ((["plain_sword"], 1),)),
                "unknown item",
            ),
            (
                "non-equipment-item",
                SubraceStartingKit("human_commoner", (("meal", 1),)),
                "non-equipment item",
            ),
            (
                "duplicate-item",
                SubraceStartingKit(
                    "human_commoner",
                    (("leather_armor", 1), ("leather_armor", 2)),
                ),
                "duplicate item",
            ),
            (
                "zero-quantity",
                SubraceStartingKit("human_commoner", (("plain_sword", 0),)),
                "non-positive quantity",
            ),
            (
                "string-quantity",
                SubraceStartingKit("human_commoner", (("plain_sword", "2"),)),
                "non-positive quantity",
            ),
            (
                "boolean-quantity",
                SubraceStartingKit("human_commoner", (("plain_sword", True),)),
                "non-positive quantity",
            ),
        ]
        for name, kit, message in cases:
            with self.subTest(case=name):
                with self.assertRaisesRegex(ValueError, message):
                    _validate_starting_kit("human_commoner", kit)
        _validate_starting_kit(
            "human_commoner",
            SubraceStartingKit(
                "human_commoner", (("leather_armor", 2), ("plain_sword", 1))
            ),
        )

    def test_coverage_validation_rejects_missing_and_unknown_subraces(self):
        missing = {
            key: SUBRACE_STARTING_KIT_REGISTRY[key]
            for key in SUBRACE_REGISTRY
            if key != "human_commoner"
        }
        with self.assertRaisesRegex(ValueError, "missing subrace"):
            _validate_starting_kit_coverage(missing)
        unknown = dict(SUBRACE_STARTING_KIT_REGISTRY)
        unknown["dragonkin"] = SubraceStartingKit(
            "dragonkin", (("plain_sword", 1),)
        )
        with self.assertRaisesRegex(ValueError, "unknown subrace"):
            _validate_starting_kit_coverage(unknown)

    def test_inventory_list_flattens_by_quantity_in_declared_order(self):
        kit = SubraceStartingKit(
            "human_commoner",
            (("leather_armor", 2), ("plain_sword", 1)),
        )
        self.assertEqual(
            kit.inventory_list(),
            ["leather_armor", "leather_armor", "plain_sword"],
        )


if __name__ == "__main__":
    unittest.main()
