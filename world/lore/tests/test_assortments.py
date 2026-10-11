"""Data-contract test: assortment registry content contract
Self-consistency checks for the assortment registry (settlement-shops design
§3.1): every bundle is a named, frozen, keyed tuple of registered item keys,
every shelf declares the closed kind/slot policy it exists to stock, every
member satisfies that policy, and a shop's offered goods are exactly the
derived union of the assortments it references. No pre-split, sanctum-added or
approved-union snapshot survives here: a valid membership edit (move, add,
retire) changes this file nowhere, which is the point of the cutover.

The six E-S military sword/armor pairs stay NAMED on purpose (WP6 task 6.5):
``world/rules/rulebook/guild_exam_restrictions.yaml`` names the B/A/S pairs as
rank gear and the E-S examination kits depend on the whole family, so their
narrow membership test stays separate from the generic registry coverage.
"""

import dataclasses
import unittest

from tools.spec_traceability import covers_requirement

from world.lore.items import (
    ITEM_REGISTRY,
    EquipmentModifierKey,
    ItemDefinition,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
)
from world.lore.settlements.assortments import (
    ASSORTMENT_REGISTRY,
    AssortmentDefinition,
    assortment_membership_violation,
)
from world.lore.settlements.shops import SHOP_REGISTRY, ShopDefinition
from world.skills.equipment import EquipmentSlot

#: The deliberately named military family: six grade pairs, twelve keys.
MILITARY_PAIR_GRADES = ("e", "d", "c", "b", "a", "s")
MILITARY_SWORDS = tuple(f"military_{grade}_sword" for grade in MILITARY_PAIR_GRADES)
MILITARY_ARMORS = tuple(f"military_{grade}_armor" for grade in MILITARY_PAIR_GRADES)
MILITARY_PAIR_KEYS = MILITARY_SWORDS + MILITARY_ARMORS


def _synthetic_item(
    key: str,
    kind: ItemKind,
    slot: EquipmentSlot | None = None,
) -> ItemDefinition:
    """One file-local synthetic item; never a shipped key."""
    return ItemDefinition(
        key=key,
        display_name_zh="合成測試物品",
        price_table_key="meal",
        sellable=True,
        presentation=ItemPresentation(
            kind=kind,
            icon_key=ItemIconKey.MISC,
            rarity=ItemRarity.COMMON,
            summary_zh="供貨架資格測試使用的合成物品。",
        ),
        equipment_slot=slot,
        modifier_key=(
            EquipmentModifierKey.PLAIN_SWORD if slot is not None else None
        ),
    )


class AssortmentRegistryTests(unittest.TestCase):
    """Assortment identity is immutable, keyed, and shelf-policy validated."""

    def test_registry_is_keyed_by_definition_key(self):
        self.assertTrue(ASSORTMENT_REGISTRY)
        self.assertEqual(
            list(ASSORTMENT_REGISTRY),
            [definition.key for definition in ASSORTMENT_REGISTRY.values()],
        )

    def test_definitions_are_frozen(self):
        for definition in ASSORTMENT_REGISTRY.values():
            self.assertTrue(dataclasses.is_dataclass(definition))
            self.assertTrue(definition.__dataclass_params__.frozen)

    def test_every_assortment_item_resolves_in_the_item_registry(self):
        for definition in ASSORTMENT_REGISTRY.values():
            self.assertTrue(definition.item_keys)
            for item_key in definition.item_keys:
                with self.subTest(assortment=definition.key, item=item_key):
                    self.assertIn(item_key, ITEM_REGISTRY)

    def test_display_names_are_traditional_chinese(self):
        for definition in ASSORTMENT_REGISTRY.values():
            with self.subTest(assortment=definition.key):
                self.assertTrue(definition.display_name_zh)

    def test_every_shipped_shelf_declares_its_stocked_kinds(self):
        # A shelf without a declared kind policy would silently accept any
        # good; the policy is what replaces the frozen key rosters.
        for definition in ASSORTMENT_REGISTRY.values():
            with self.subTest(assortment=definition.key):
                self.assertTrue(definition.allowed_item_kinds)

    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-xyzgrid-remains-thirteen-exterior-nodes-while-permanent-service-interiors-are-attached"
    )
    def test_every_assortment_member_satisfies_its_declared_shelf_eligibility(self):
        # The partition RULE, computed from both sides: both the offered set
        # and the policy come from the registries, so the next good added to
        # a shelf either satisfies its purpose or fails load -- no approved
        # item list decides this.
        # This is where the sample-city-altoria requirement's merchandise
        # scenarios now live: "Specialist shops do not narrow what the capital
        # sells", "The accessory-slot partition ... follows explicit
        # registry-owned shop-purpose and eligible-slot declarations", "An
        # omitted accessory good is a gap; a non-accessory good is a leak" and
        # "The partition is stated as a set equality, not a hand-listed
        # inventory" (the grid/interior half of that requirement keeps its
        # assertions in world/maps/tests/test_service_interiors.py).
        for definition in ASSORTMENT_REGISTRY.values():
            for item_key in definition.item_keys:
                with self.subTest(assortment=definition.key, item=item_key):
                    self.assertIsNone(
                        assortment_membership_violation(
                            definition, ITEM_REGISTRY[item_key]
                        )
                    )

    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-xyzgrid-remains-thirteen-exterior-nodes-while-permanent-service-interiors-are-attached"
    )
    def test_a_shelf_rejects_a_mismatched_kind_or_slot(self):
        # File-local synthetic shelf and items: a non-accessory good is a
        # leak onto the jeweller's glass case, and an accessory that equips
        # to another slot is a mismatch, while a conforming good is accepted.
        shelf = AssortmentDefinition(
            key="t_synth_shelf",
            display_name_zh="合成貨架",
            item_keys=(),
            allowed_item_kinds=frozenset({ItemKind.ACCESSORY}),
            allowed_equipment_slots=frozenset({EquipmentSlot.ACCESSORY}),
        )
        conforming = _synthetic_item("t_synth_ring", ItemKind.ACCESSORY, EquipmentSlot.ACCESSORY)
        self.assertIsNone(assortment_membership_violation(shelf, conforming))

        wrong_kind = _synthetic_item("t_synth_potion", ItemKind.POTION)
        reason = assortment_membership_violation(shelf, wrong_kind)
        self.assertIsNotNone(reason)
        self.assertIn("potion", reason)
        self.assertIn("t_synth_shelf", reason)

        # Accessory kind so the KIND axis passes and the failure names the
        # slot axis alone.
        wrong_slot = _synthetic_item(
            "t_synth_blade", ItemKind.ACCESSORY, EquipmentSlot.WEAPON_MAIN
        )
        reason = assortment_membership_violation(shelf, wrong_slot)
        self.assertIsNotNone(reason)
        self.assertIn("weapon_main", reason)
        self.assertIn("t_synth_shelf", reason)

        # An unrestricted shelf accepts both axes; only a declared policy
        # constrains a member.
        open_shelf = AssortmentDefinition(
            key="t_open_shelf", display_name_zh="合成開放貨架", item_keys=()
        )
        for item in (conforming, wrong_kind, wrong_slot):
            self.assertIsNone(assortment_membership_violation(open_shelf, item))

    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-xyzgrid-remains-thirteen-exterior-nodes-while-permanent-service-interiors-are-attached"
    )
    def test_shop_offered_membership_is_derived_not_hand_listed(self):
        for field in dataclasses.fields(ShopDefinition):
            self.assertNotIn(field.name, {"items", "item_keys", "offers"})

    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-xyzgrid-remains-thirteen-exterior-nodes-while-permanent-service-interiors-are-attached"
    )
    def test_capital_shop_membership_is_the_current_authored_union(self):
        # "Specialist shops do not narrow what the capital sells": the capital
        # union is exactly the union of the bundles its own shops reference,
        # with no historical roster and no per-shop hand list. Capital shops
        # may share a key; only one shop referencing two overlapping bundles
        # is rejected (test_guild_config).
        capital_shops = [
            shop for shop in SHOP_REGISTRY.values() if shop.key.startswith("altoria_")
        ]
        self.assertTrue(capital_shops)
        union: set[str] = set()
        for shop in capital_shops:
            self.assertTrue(shop.assortment_keys)
            authored: list[str] = []
            for assortment_key in shop.assortment_keys:
                for item_key in ASSORTMENT_REGISTRY[assortment_key].item_keys:
                    if item_key not in authored:
                        authored.append(item_key)
            with self.subTest(shop=shop.key):
                self.assertEqual(list(shop.offered_item_keys), authored)
            union.update(authored)
        self.assertEqual(
            union,
            {
                item_key
                for assortment_key, definition in ASSORTMENT_REGISTRY.items()
                if any(assortment_key in shop.assortment_keys for shop in capital_shops)
                for item_key in definition.item_keys
            },
        )


class MilitaryPairMembershipTests(unittest.TestCase):
    """The six named E-S military pairs the guild examiner depends on.

    Kept deliberately NAMED (WP6 task 6.5): ``world/rules/rulebook/
    guild_exam_restrictions.yaml`` names the B/A/S pairs as the rank gear a
    restricted examination must wear and the E-S examination kits depend on
    the whole family, so this one membership contract stays a narrow tagged
    test. Everything else in the item/shop/assortment families above is
    registry-derived; the reason for the exception is the examiner dependency,
    not that military items resist being registry data.
    """

    @covers_requirement(
        "military-equipment::six-military-pairs-use-shared-registered-effects-and-approved-integer-prices"
    )
    def test_the_twelve_named_pairs_are_registered_and_stocked(self):
        military_keys = {key for key in ITEM_REGISTRY if key.startswith("military_")}
        self.assertEqual(military_keys, set(MILITARY_PAIR_KEYS))
        for key in MILITARY_PAIR_KEYS:
            with self.subTest(item=key):
                definition = ITEM_REGISTRY[key]
                self.assertIsNotNone(definition.equipment_slot)
                self.assertEqual(definition.modifier_key.value, key)
                self.assertTrue(definition.sellable)
                self.assertTrue(
                    any(
                        key in shop.offered_item_keys
                        for shop in SHOP_REGISTRY.values()
                    ),
                    f"{key} is registered but no shop stocks it",
                )

    @covers_requirement(
        "military-equipment::military-pairs-participate-in-ordinary-finite-commerce"
    )
    def test_each_pair_rides_its_named_capital_shelf(self):
        arms = set(ASSORTMENT_REGISTRY["common_arms"].item_keys)
        outfits = set(ASSORTMENT_REGISTRY["common_outfits"].item_keys)
        for key in MILITARY_SWORDS:
            self.assertIn(key, arms)
        for key in MILITARY_ARMORS:
            self.assertIn(key, outfits)


if __name__ == "__main__":
    unittest.main()
