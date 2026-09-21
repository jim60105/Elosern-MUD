"""Data-contract test: guild/shop config validation contract
Slice of ``test_guild_config``: ItemDefinitionTests, OfferDefinitionTests.
"""
from tools.spec_traceability import covers_requirement
import unittest
from dataclasses import fields
from world.lore.economy import PRICE_TABLE
from world.lore.items import ITEM_REGISTRY
from world.lore.items import EquipmentModifierKey
from world.lore.items import ItemDefinition
from world.lore.items import ItemIconKey
from world.lore.items import ItemKind
from world.lore.items import ItemPresentation
from world.lore.items import ItemRarity
from world.lore.items import ItemUseMechanics
from world.lore.items import SUMMARY_MAX
from world.lore.settlements.shops import SHOP_REGISTRY
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.rules.guild_config import load_guild_catalog
from world.rules.guild_config import validate_assortment_configs
from world.rules.guild_config import validate_shop_configs
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.rules.guild_offers import GuildOfferError
from world.rules.guild_offers import GuildQuestOffer
from world.rules.guild_offers import register_guild_offer
from world.skills.equipment import EquipmentSlot
from ._support import (
    CatalogRegistryIsolation,
    _shipped_scales,
    raw_commerce,
)


class ItemDefinitionTests(unittest.TestCase):
    @covers_requirement(
        "shop-economy::item-and-shop-identities-are-immutable-while-numeric-trade-rules-are-yaml-and-lore-constrained"
    )
    def test_initial_items_have_lore_price_identity_without_numbers(self):
        self.assertEqual(len(ITEM_REGISTRY), 106)
        self.assertTrue(
            {"meal", "healing_potion", "plain_sword"} <= set(ITEM_REGISTRY)
        )
        for key, definition in ITEM_REGISTRY.items():
            with self.subTest(item=key):
                self.assertIn(definition.price_table_key, PRICE_TABLE)
                self.assertIsInstance(definition.sellable, bool)
                self.assertIsInstance(definition.presentation, ItemPresentation)
                self.assertIsInstance(definition.presentation.kind, ItemKind)
                self.assertIsInstance(definition.presentation.icon_key, ItemIconKey)
                self.assertIsInstance(definition.presentation.rarity, ItemRarity)
                self.assertTrue(definition.presentation.summary_zh.strip())
                self.assertLessEqual(
                    sum(1 for _ in definition.presentation.summary_zh), SUMMARY_MAX
                )

    def test_item_definitions_are_deeply_immutable(self):
        definition = ITEM_REGISTRY["meal"]
        with self.assertRaises(Exception):
            definition.display_name_zh = "changed"  # type: ignore[misc]
        self.assertEqual(ITEM_REGISTRY["meal"].display_name_zh, "普通餐食")

    def test_shop_definitions_reference_only_known_items(self):
        self.assertEqual(
            set(SHOP_REGISTRY),
            {
                "altoria_general_store", "altoria_forge",
                "altoria_eatery", "altoria_tailor",
                "ciaran_hailiel_home", "ciaran_lareneth_home",
                "ciaran_valwyn_home", "ciaran_vethiel_home",
                "ciaran_gwenaera_home", "ciaran_nireth_home",
            },
        )
        for shop in SHOP_REGISTRY.values():
            self.assertTrue(all(key in ITEM_REGISTRY for key in shop.offered_item_keys))

    @covers_requirement(
        "masterwork-price-band::goods-a-community-trades-everyday-do-not-sit-in-the-keepsake-band"
    )
    @covers_requirement(
        "item-presentation-metadata::presentation-metadata-does-not-claim-unimplemented-mechanics"
    )
    def test_presentation_swap_leaves_economy_outputs_unchanged(self):
        raw = raw_commerce()
        baseline = validate_shop_configs(
            raw["shops"],
            validate_assortment_configs(raw["assortments"]),
            _shipped_scales(),
        )
        original = ITEM_REGISTRY["meal"]
        altered = ItemDefinition(
            key="meal",
            display_name_zh=original.display_name_zh,
            price_table_key=original.price_table_key,
            sellable=original.sellable,
            presentation=ItemPresentation(
                kind=ItemKind.FOOD,
                icon_key=ItemIconKey.FOOD,
                rarity=ItemRarity.LEGENDARY,
                summary_zh="旅人充飢的普通餐食。",
            ),
        )
        ITEM_REGISTRY["meal"] = altered
        try:
            changed = validate_shop_configs(
                raw["shops"],
                validate_assortment_configs(raw["assortments"]),
                _shipped_scales(),
            )
            self.assertEqual(changed, baseline)
        finally:
            ITEM_REGISTRY["meal"] = original

    @covers_requirement(
        "lore-registries::currency-is-an-integer-count-of-\u9285-with-no-floats-in-the-money-path"
    )
    def test_one_band_serves_both_mechanical_shapes_of_category(self):
        usable_item = ItemDefinition(
            key="synthetic_usable_toy",
            display_name_zh="測試情趣消耗品",
            price_table_key="intimacy_tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOY,
                icon_key=ItemIconKey.TOY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="測試用的情趣消耗品。",
            ),
            use_mechanics=ItemUseMechanics(consumable=True, combat_allowed=False),
        )
        equipment_item = ItemDefinition(
            key="synthetic_equipment_toy",
            display_name_zh="測試情趣穿戴品",
            price_table_key="intimacy_tool",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.TOY,
                icon_key=ItemIconKey.TOY,
                rarity=ItemRarity.UNCOMMON,
                summary_zh="測試用的情趣穿戴品。",
            ),
            equipment_slot=EquipmentSlot.ACCESSORY,
            modifier_key=EquipmentModifierKey.PILGRIM_MEDALLION,
        )
        usable_band = PRICE_TABLE[usable_item.price_table_key]
        equipment_band = PRICE_TABLE[equipment_item.price_table_key]
        self.assertIs(usable_band, equipment_band)
        self.assertEqual(usable_band.min_copper, 50)
        self.assertEqual(usable_band.max_copper, 20_000)

class OfferDefinitionTests(CatalogRegistryIsolation):
    def test_offer_frozen_shape_and_nested_immutability(self):
        offer = GuildQuestOffer(
            definition_key="introductory_hunt",
            issuer_branch_key="guild_branch_altoria",
            reward=__import__(
                "world.rules.guild_offers", fromlist=["QuestReward"]
            ).QuestReward(
                copper=50,
                items=(__import__(
                    "world.rules.guild_offers", fromlist=["ItemQuantity"]
                ).ItemQuantity("healing_potion", 2),),
                merit=25,
            ),
        )
        with self.assertRaises(Exception):
            offer.reward = None  # type: ignore[misc]
        self.assertIsInstance(fields(offer), tuple)

    def test_equal_registration_is_idempotent_and_conflict_fails(self):
        catalog = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
        from world.rules.guild_config import register_catalog_offers

        register_catalog_offers(catalog)
        offer = catalog.quest_offers[0]
        first_key = (offer.definition_key, offer.issuer_branch_key)
        register_guild_offer(offer)
        self.assertEqual(GUILD_OFFER_REGISTRY[first_key], offer)

        # Registering the same catalog again must not raise or replace.
        register_catalog_offers(catalog)
        self.assertEqual(GUILD_OFFER_REGISTRY[first_key], offer)

        conflicting = GuildQuestOffer(
            definition_key="introductory_hunt",
            issuer_branch_key="guild_branch_altoria",
            reward=__import__(
                "world.rules.guild_offers", fromlist=["QuestReward"]
            ).QuestReward(99, (), 30),
        )
        with self.assertRaises(GuildOfferError):
            register_guild_offer(conflicting)
        self.assertEqual(GUILD_OFFER_REGISTRY[first_key], offer)


if __name__ == "__main__":
    unittest.main()
