"""Data-contract test: starting-kit data contract
Registry contract tests for the subrace starting-kit catalog."""

from tools.spec_traceability import covers_requirement

import unittest

from world.lore.items import ITEM_REGISTRY, ItemRarity
from world.lore.races import SUBRACE_REGISTRY
from world.skills.equipment import EquipmentSlot
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
        "lore-item-catalog::retiring-an-item-key-leaves-no-dangling-reference"
    )
    def test_starting_kit_naming_retired_item_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            _validate_starting_kit(
                "human_plains",
                SubraceStartingKit("human_plains", (("synthetic_retired_sword", 1),)),
            )
        self.assertIn("synthetic_retired_sword", str(caught.exception))

    @covers_requirement(
        "lore-item-catalog::retiring-an-item-key-leaves-no-dangling-reference"
    )
    def test_completed_kit_retirement_leaves_kit_valid(self):
        kit = SubraceStartingKit("human_plains", (("plain_sword", 1), ("leather_armor", 1)))
        _validate_starting_kit("human_plains", kit)

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
    def test_every_selection_satisfies_its_declared_lineage_ceiling(self):
        # Reference closure and eligibility are both computed from the live
        # registries: a valid selection edit is a data edit, and an
        # ineligible one is rejected by the kit's own declaration rather
        # than by a named prohibited-item blacklist.
        for subrace_key, kit in SUBRACE_STARTING_KIT_REGISTRY.items():
            with self.subTest(subrace=subrace_key):
                for item_key, _ in kit.items:
                    self.assertIn(item_key, ITEM_REGISTRY)
                    self.assertIsNotNone(ITEM_REGISTRY[item_key].equipment_slot)
                if kit.max_rarity is not None:
                    self.assertIsInstance(kit.max_rarity, ItemRarity)

    @covers_requirement("lore-registries::human-starting-kits-express-lineage-character-not-an-affluence-ladder")
    def test_the_commoner_lineages_share_one_common_rarity_profile(self):
        # "Commoner" is derived, not listed: the lineage kits whose declared
        # ceiling is COMMON. They must be equipotent -- identical rarity
        # profiles, every item COMMON -- so no commoner bloodline starts
        # richer than another. The individual selections stay data.
        commoner_kits = {
            key: kit
            for key, kit in SUBRACE_STARTING_KIT_REGISTRY.items()
            if kit.max_rarity is ItemRarity.COMMON
        }
        self.assertTrue(commoner_kits, "no commoner lineage kit declares the COMMON ceiling")
        profiles = {
            key: tuple(
                sorted(ITEM_REGISTRY[item_key].presentation.rarity for item_key, _ in kit.items)
            )
            for key, kit in commoner_kits.items()
        }
        first = next(iter(profiles.values()))
        for subrace_key, profile in profiles.items():
            with self.subTest(subrace=subrace_key):
                self.assertEqual(profile, first)
                self.assertTrue(all(rarity is ItemRarity.COMMON for rarity in profile))

    @covers_requirement("lore-registries::human-starting-kits-express-lineage-character-not-an-affluence-ladder")
    def test_the_noble_lineages_keep_their_uncommon_inherited_arms(self):
        # The two noble bloodlines the delta names: 王族 and 貴族 hand down an
        # UNCOMMON weapon -- the inherited arm -- while their armour and
        # accessory stay COMMON.
        for subrace_key in ("human_royal", "human_noble"):
            kit = SUBRACE_STARTING_KIT_REGISTRY[subrace_key]
            with self.subTest(subrace=subrace_key):
                self.assertIs(kit.max_rarity, ItemRarity.UNCOMMON)
                inherited_arms = [
                    ITEM_REGISTRY[item_key].presentation.rarity
                    for item_key, _ in kit.items
                    if ITEM_REGISTRY[item_key].equipment_slot
                    is EquipmentSlot.WEAPON_MAIN
                ]
                self.assertEqual(inherited_arms, [ItemRarity.UNCOMMON])

    @covers_requirement("lore-registries::human-starting-kits-express-lineage-character-not-an-affluence-ladder")
    def test_an_ineligible_selection_fails_at_registry_load(self):
        # A synthetic commoner kit reaching for an UNCOMMON arm violates its
        # own declared lineage ceiling; the rejection names the kit and the
        # item and consults no historical item-name list.
        above_ceiling = SubraceStartingKit(
            "t_synth_lineage",
            (("knight_blade", 1),),
            ItemRarity.COMMON,
        )
        with self.assertRaises(ValueError) as caught:
            _validate_starting_kit("t_synth_lineage", above_ceiling)
        message = str(caught.exception)
        self.assertIn("t_synth_lineage", message)
        self.assertIn("knight_blade", message)
        self.assertIn("lineage ceiling", message)
        # The same declaration accepts a selection inside its ceiling, and a
        # malformed ceiling is itself rejected.
        _validate_starting_kit(
            "t_synth_lineage",
            SubraceStartingKit(
                "t_synth_lineage",
                (("plain_sword", 1),),
                ItemRarity.COMMON,
            ),
        )
        with self.assertRaises(ValueError) as caught:
            _validate_starting_kit(
                "t_synth_lineage",
                SubraceStartingKit(
                    "t_synth_lineage", (("plain_sword", 1),), "common"
                ),
            )
        self.assertIn("max_rarity", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
