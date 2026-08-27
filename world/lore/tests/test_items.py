"""Registry contract tests for the immutable item presentation metadata."""

from tools.spec_traceability import covers_requirement

import unittest
from dataclasses import fields

from world.lore.items import (
    ITEM_REGISTRY,
    ItemDefinition,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    SUMMARY_MAX,
)


class ItemPresentationTests(unittest.TestCase):
    @covers_requirement(
        "item-presentation-metadata::registered-items-have-immutable-visual-identities"
    )
    def test_every_registered_item_resolves_complete_metadata(self):
        self.assertEqual(
            set(ITEM_REGISTRY), {"meal", "healing_potion", "plain_sword"}
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
            ["key", "display_name_zh", "price_table_key", "sellable", "presentation"],
        )
        self.assertEqual(
            [field.name for field in fields(ItemPresentation)],
            ["kind", "icon_key", "rarity", "summary_zh"],
        )
        for definition in ITEM_REGISTRY.values():
            self.assertNotRegex(definition.presentation.summary_zh, r"[0-9]", definition.key)


if __name__ == "__main__":
    unittest.main()
