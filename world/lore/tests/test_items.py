"""Registry contract tests for the immutable item presentation metadata."""

from tools.spec_traceability import covers_requirement

import unittest
from dataclasses import fields

from world.lore.items import (
    ITEM_REGISTRY,
    ItemDefinition,
    ItemEffectKey,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    ItemUseMechanics,
    SUMMARY_MAX,
)
from world.skills.equipment import EquipmentSlot


class ItemPresentationTests(unittest.TestCase):
    @covers_requirement(
        "item-presentation-metadata::registered-items-have-immutable-visual-identities"
    )
    def test_every_registered_item_resolves_complete_metadata(self):
        self.assertEqual(
            set(ITEM_REGISTRY),
            {
                "meal", "healing_potion", "plain_sword",
                "iron_dagger", "hunting_throwing_axe", "hunters_longbow",
                "apprentice_focus_staff", "knight_blade", "wooden_club",
                "gilded_saber", "great_axe", "ashen_scimitar",
                "steel_fang_dagger", "magic_sword",
                "leather_armor", "mage_robe", "chainmail", "iron_shield",
                "silver_hairpin", "wolf_fang_necklace", "pilgrim_medallion",
                "prism_charm", "protective_ring", "storage_pouch",
                "gliding_cloak",
                "magic_lamp", "healing_herb", "rough_iron_ore", "beast_crystal",
                "evernight_shard", "mana_core", "dragon_scale_fragment",
                "elven_spider_silk", "baptismal_holy_water",
                "greater_healing_potion", "mana_potion",
                "elven_traditional_robe", "royal_signet_ring",
                "royal_heirloom_pendant", "rose_crest_rapier", "black_maid_dress",
                "silver_feather_earring", "crescent_earring", "dark_elf_kimono",
                "shadow_blade", "shadow_blade_echo", "dark_elf_ninja_garb",
                "guild_recruit_badge",
            }
        )
        for key, definition in ITEM_REGISTRY.items():
            presentation = definition.presentation
            with self.subTest(item=key):
                self.assertIsInstance(presentation, ItemPresentation)
                self.assertIsInstance(presentation.kind, ItemKind)
                self.assertIsInstance(presentation.icon_key, ItemIconKey)
                self.assertIsInstance(presentation.rarity, ItemRarity)
                self.assertTrue(presentation.summary_zh.strip())
                self.assertLessEqual(
                    sum(1 for _ in presentation.summary_zh), SUMMARY_MAX
                )
                self.assertNotIn("\n", presentation.summary_zh)
                han_chars = [ch for ch in presentation.summary_zh if "\u4e00" <= ch <= "\u9fff"]
                self.assertTrue(
                    han_chars,
                    f"item {key!r} summary_zh must be Traditional Chinese",
                )

    @covers_requirement(
        "item-presentation-metadata::registered-items-have-immutable-visual-identities"
    )
    def test_repeated_lookups_resolve_the_same_immutable_metadata(self):
        for key in ITEM_REGISTRY:
            with self.subTest(item=key):
                first = ITEM_REGISTRY[key].presentation
                again = ITEM_REGISTRY[key].presentation
                self.assertIs(first, again)
                with self.assertRaises(AttributeError):
                    first.kind = ItemKind.MISC  # type: ignore[misc]
                self.assertIs(ITEM_REGISTRY[key].presentation, first)

    @covers_requirement(
        "item-presentation-metadata::item-presentation-keys-are-safe-closed-renderer-contracts"
    )
    def test_presentation_vocabularies_are_closed(self):
        self.assertEqual(
            set(ItemKind),
            {
                ItemKind.FOOD,
                ItemKind.POTION,
                ItemKind.WEAPON,
                ItemKind.ARMOR,
                ItemKind.ACCESSORY,
                ItemKind.AMMUNITION,
                ItemKind.TOOL,
                ItemKind.MATERIAL,
                ItemKind.MISC,
            },
        )
        self.assertEqual(
            set(ItemIconKey),
            {
                ItemIconKey.FOOD,
                ItemIconKey.POTION,
                ItemIconKey.WEAPON,
                ItemIconKey.ARMOR,
                ItemIconKey.ACCESSORY,
                ItemIconKey.AMMUNITION,
                ItemIconKey.TOOL,
                ItemIconKey.MATERIAL,
                ItemIconKey.MISC,
            },
        )
        self.assertEqual(
            set(ItemRarity),
            {
                ItemRarity.COMMON,
                ItemRarity.UNCOMMON,
                ItemRarity.RARE,
                ItemRarity.EPIC,
                ItemRarity.LEGENDARY,
            },
        )

    @covers_requirement(
        "item-presentation-metadata::item-presentation-keys-are-safe-closed-renderer-contracts"
    )
    def test_malformed_presentation_data_is_rejected(self):
        base = dict(
            kind=ItemKind.FOOD,
            icon_key=ItemIconKey.FOOD,
            rarity=ItemRarity.COMMON,
            summary_zh="供旅人充飢的普通餐食。",
        )
        cases = [
            ("bare-string-kind", {"kind": "food"}),
            ("bare-string-icon", {"icon_key": "potion"}),
            ("bare-string-rarity", {"rarity": "rare"}),
            ("empty-summary", {"summary_zh": "   "}),
            ("oversized-summary", {"summary_zh": "饌" * (SUMMARY_MAX + 1)}),
            ("newline-summary", {"summary_zh": "第一行\n第二行"}),
            ("carriage-return-summary", {"summary_zh": "第一行\r第二行"}),
            ("unicode-line-separator", {"summary_zh": "第一行\u2028第二行"}),
            ("markup-summary", {"summary_zh": "<b>粗體</b>餐食"}),
            ("url-summary", {"summary_zh": "圖 http://img.example/a.svg"}),
            ("url-slash-summary", {"summary_zh": "圖 //img.example/a.svg"}),
            ("emoji-summary", {"summary_zh": "美食🍗"}),
            ("dingbat-emoji", {"summary_zh": "美食✨"}),
            ("variation-selector-emoji", {"summary_zh": "美食🍗\ufe0f"}),
            ("keycap-sequence", {"summary_zh": "一號\U0001F7EB\u20e3"}),
        ]
        for name, overrides in cases:
            with self.subTest(case=name):
                with self.assertRaises(ValueError):
                    ItemPresentation(**{**base, **overrides})

        # ItemDefinition requires an ItemPresentation object, not a bare value.
        with self.assertRaises(ValueError):
            ItemDefinition(
                key="meal",
                display_name_zh="普通餐食",
                price_table_key="meal",
                sellable=True,
                presentation="food",
            )

    @covers_requirement(
        "item-presentation-metadata::presentation-metadata-does-not-claim-unimplemented-mechanics"
    )
    def test_presentation_schema_has_no_numeric_mechanics_fields(self):
        self.assertEqual(
            [field.name for field in fields(ItemDefinition)],
            [
                "key",
                "display_name_zh",
                "price_table_key",
                "sellable",
                "presentation",
                "use_mechanics",
                "equipment_slot",
            ],
        )
        self.assertEqual(
            [field.name for field in fields(ItemPresentation)],
            ["kind", "icon_key", "rarity", "summary_zh"],
        )
        for definition in ITEM_REGISTRY.values():
            self.assertNotRegex(definition.presentation.summary_zh, r"[0-9]", definition.key)
        # Mechanics bindings are references resolved by the deterministic
        # rules capability; presentation carries no mechanics.
        for definition in ITEM_REGISTRY.values():
            for mechanics_field in ("use_mechanics", "equipment_slot"):
                value = getattr(definition, mechanics_field)
                if value is None:
                    continue
                self.assertIsInstance(
                    value, (ItemUseMechanics, EquipmentSlot), definition.key
                )


class ItemMechanicsTests(unittest.TestCase):
    """The closed, mutually exclusive mechanics seam of the lore registry."""

    def _presentation(self) -> ItemPresentation:
        return ItemPresentation(
            kind=ItemKind.POTION,
            icon_key=ItemIconKey.POTION,
            rarity=ItemRarity.COMMON,
            summary_zh="可重複使用的測試藥水。",
        )

    def _definition(self, **overrides) -> ItemDefinition:
        base = dict(
            key="test_item",
            display_name_zh="測試物品",
            price_table_key="potion",
            sellable=False,
            presentation=self._presentation(),
        )
        return ItemDefinition(**{**base, **overrides})

    def test_canonical_bindings_resolve(self):
        potion = ITEM_REGISTRY["healing_potion"]
        self.assertEqual(
            potion.use_mechanics.effect_key, ItemEffectKey.SELF_HEAL
        )
        self.assertTrue(potion.use_mechanics.consumable)
        self.assertTrue(potion.use_mechanics.combat_allowed)
        self.assertIsNone(potion.equipment_slot)
        self.assertIs(ITEM_REGISTRY["plain_sword"].equipment_slot, EquipmentSlot.WEAPON_MAIN)
        self.assertIsNone(ITEM_REGISTRY["plain_sword"].use_mechanics)
        # Inspect-only items declare neither form.
        self.assertIsNone(ITEM_REGISTRY["meal"].use_mechanics)
        self.assertIsNone(ITEM_REGISTRY["meal"].equipment_slot)

    def test_mutable_use_definition_rejects_malformed_members(self):
        with self.assertRaises(ValueError):
            ItemUseMechanics(effect_key="self_heal", consumable=True, combat_allowed=True)
        with self.assertRaises(ValueError):
            ItemUseMechanics(
                effect_key=ItemEffectKey.SELF_HEAL, consumable="yes", combat_allowed=True
            )
        with self.assertRaises(ValueError):
            ItemUseMechanics(
                effect_key=ItemEffectKey.SELF_HEAL, consumable=True, combat_allowed=1
            )

    @covers_requirement(
        "item-use-resolution::item-mechanics-are-immutable-and-independent-from-presentation"
    )
    def test_ambiguous_and_malformed_mechanics_fail_construction(self):
        cases = {
            "both-forms": dict(
                use_mechanics=ItemUseMechanics(
                    effect_key=ItemEffectKey.SELF_HEAL,
                    consumable=True,
                    combat_allowed=True,
                ),
                equipment_slot=EquipmentSlot.WEAPON_MAIN,
            ),
            "bare-string-slot": dict(equipment_slot="weapon_main"),
            "unknown-slot-string": dict(equipment_slot="saddle"),
            "bare-mechanics-object": dict(use_mechanics="self_heal"),
        }
        for name, overrides in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(ValueError):
                    self._definition(**overrides)

    def test_reusable_definition_is_valid(self):
        definition = self._definition(
            use_mechanics=ItemUseMechanics(
                effect_key=ItemEffectKey.SELF_HEAL,
                consumable=False,
                combat_allowed=False,
            )
        )
        self.assertFalse(definition.use_mechanics.consumable)
        self.assertFalse(definition.use_mechanics.combat_allowed)

    def test_each_equipment_slot_is_acceptable(self):
        for slot in EquipmentSlot:
            with self.subTest(slot=slot.value):
                definition = self._definition(equipment_slot=slot)
                self.assertIs(definition.equipment_slot, slot)


if __name__ == "__main__":
    unittest.main()
