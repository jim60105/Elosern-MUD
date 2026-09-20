"""Data-contract test: guild/shop config validation contract
Slice of ``test_guild_config``: CatalogLoadingTests.
"""
from tools.spec_traceability import covers_requirement
from unittest import mock
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.items import ItemDefinition
from world.lore.items import ItemIconKey
from world.lore.items import ItemKind
from world.lore.items import ItemPresentation
from world.lore.items import ItemRarity
from world.lore.settlements.assortments import ASSORTMENT_REGISTRY
from world.lore.settlements.assortments import AssortmentDefinition
from world.lore.settlements.shops import SHOP_REGISTRY
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.rules.guild_config import GuildCatalog
from world.rules.guild_config import GuildConfigError
from world.rules.guild_config import load_guild_catalog
from world.rules.guild_config import validate_assortment_configs
from world.rules.guild_config import validate_quest_rewards
import unittest
from ._support import (
    CatalogRegistryIsolation,
    raw_commerce,
    raw_rulebook,
)


class CatalogLoadingTests(CatalogRegistryIsolation):
    def test_full_catalog_loads_and_joins_registries(self):
        catalog = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
        self.assertIsInstance(catalog, GuildCatalog)
        self.assertEqual(
            set(catalog.shop_configs), set(SHOP_REGISTRY)
        )
        self.assertEqual(
            {offer.definition_key for offer in catalog.quest_offers},
            {"introductory_hunt"},
        )

    def test_reward_copper_lies_inside_quest_rank_band(self):
        from world.lore.guild import GUILD_RANK_REGISTRY

        catalog = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
        definition = QUEST_DEFINITION_REGISTRY["introductory_hunt"]
        band = GUILD_RANK_REGISTRY[definition.rank]
        offer = catalog.offer_by_definition["introductory_hunt"]
        self.assertTrue(band.reward_min_copper <= offer.reward.copper <= band.reward_max_copper)

    def test_unknown_definition_reward_is_rejected(self):
        raw = raw_rulebook()["quest_rewards"]
        mutated = [{**raw[0], "definition_key": "not_a_quest"}]
        with self.assertRaises(GuildConfigError):
            validate_quest_rewards(mutated, QUEST_DEFINITION_REGISTRY)

    def test_float_money_is_rejected_by_int_validation(self):
        raw = raw_rulebook()["quest_rewards"]
        mutated = [{**raw[0], "reward": {**raw[0]["reward"], "copper": 50.0}}]
        with self.assertRaises(GuildConfigError):
            validate_quest_rewards(mutated, QUEST_DEFINITION_REGISTRY)

    def test_duplicate_reward_item_is_rejected(self):
        raw = raw_rulebook()["quest_rewards"]
        mutated_items = [
            *raw[0]["reward"]["items"],
            {**raw[0]["reward"]["items"][0]},
        ]
        mutated = [{**raw[0], "reward": {**raw[0]["reward"], "items": mutated_items}}]
        with self.assertRaises(GuildConfigError):
            validate_quest_rewards(mutated, QUEST_DEFINITION_REGISTRY)

    def test_negative_merit_is_rejected(self):
        raw = raw_rulebook()["quest_rewards"]
        mutated = [{**raw[0], "reward": {**raw[0]["reward"], "merit": -5}}]
        with self.assertRaises(GuildConfigError):
            validate_quest_rewards(mutated, QUEST_DEFINITION_REGISTRY)

    def test_out_of_band_reward_is_rejected(self):
        raw = raw_rulebook()["quest_rewards"]
        mutated = [{**raw[0], "reward": {**raw[0]["reward"], "copper": 10_000}}]
        with self.assertRaises(GuildConfigError):
            validate_quest_rewards(mutated, QUEST_DEFINITION_REGISTRY)

    @covers_requirement(
        "lore-item-catalog::retiring-an-item-key-leaves-no-dangling-reference"
    )
    def test_shop_offering_retired_item_fails_catalog_load(self):
        raw = raw_commerce()
        synthetic_rows = [
            {
                **row,
                "offers": [
                    *row["offers"],
                    {
                        "item_key": "synthetic_retired_item",
                        "buy_copper": 100,
                        "sell_copper": 50,
                        "max_stock": 5,
                        "initial_stock": 1,
                        "restock_quantity": 1,
                    },
                ],
            }
            if row["key"] == "common_arms" else row
            for row in raw["assortments"]
        ]
        with mock.patch(
            "world.rules.guild_config.load_commerce_config",
            return_value={**raw, "assortments": synthetic_rows},
        ):
            with self.assertRaises(GuildConfigError) as caught:
                load_guild_catalog(QUEST_DEFINITION_REGISTRY)
            self.assertIn("synthetic_retired_item", str(caught.exception))

    @covers_requirement(
        "lore-item-catalog::retiring-an-item-key-leaves-no-dangling-reference"
    )
    def test_assortment_item_set_naming_retired_item_fails_catalog_load(self):
        # The identity side of the alignment: an assortment whose item set
        # names a retired key fails load naming the assortment and the item.
        definition = AssortmentDefinition(
            "t_retired_rack", "合成退役貨架", ("synthetic_retired_key",)
        )
        with mock.patch.dict(ASSORTMENT_REGISTRY, {"t_retired_rack": definition}, clear=False):
            with self.assertRaises(GuildConfigError) as caught:
                validate_assortment_configs([{"key": "t_retired_rack", "offers": []}])
            self.assertIn("synthetic_retired_key", str(caught.exception))

    @covers_requirement(
        "lore-item-catalog::retiring-an-item-key-leaves-no-dangling-reference"
    )
    def test_quest_reward_naming_retired_item_is_rejected(self):
        raw = raw_rulebook()["quest_rewards"]
        mutated_items = [{"item_key": "synthetic_retired_item", "quantity": 1}]
        mutated = [{**raw[0], "reward": {**raw[0]["reward"], "items": mutated_items}}]
        with self.assertRaises(GuildConfigError) as caught:
            validate_quest_rewards(mutated, QUEST_DEFINITION_REGISTRY)
        self.assertIn("synthetic_retired_item", str(caught.exception))

    @covers_requirement(
        "lore-item-catalog::retiring-an-item-key-leaves-no-dangling-reference"
    )
    def test_completed_retirement_leaves_catalog_load_clean(self):
        catalog = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
        self.assertIsInstance(catalog, GuildCatalog)

    @covers_requirement(
        "lore-registries::currency-is-an-integer-count-of-銅-with-no-floats-in-the-money-path"
    )
    def test_item_naming_absent_price_band_fails_catalog_load(self):
        synthetic_item = ItemDefinition(
            key="synthetic_absent_band_item",
            display_name_zh="合成無頻帶物品",
            price_table_key="undefined_band",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.FOOD,
                icon_key=ItemIconKey.FOOD,
                rarity=ItemRarity.COMMON,
                summary_zh="用於測試不存在價格帶的合成物品。",
            ),
        )
        definition = AssortmentDefinition(
            "t_band_rack", "合成頻帶貨架", ("synthetic_absent_band_item",)
        )
        assortment_raw = {
            "key": "t_band_rack",
            "offers": [
                {
                    "item_key": "synthetic_absent_band_item",
                    "buy_copper": 100,
                    "sell_copper": 50,
                    "max_stock": 5,
                    "initial_stock": 1,
                    "restock_quantity": 1,
                }
            ],
        }
        with mock.patch.dict(ITEM_REGISTRY, {"synthetic_absent_band_item": synthetic_item}, clear=False), \
             mock.patch.dict(ASSORTMENT_REGISTRY, {"t_band_rack": definition}, clear=False):
            with self.assertRaises(GuildConfigError) as caught:
                validate_assortment_configs([assortment_raw])
            self.assertIn("synthetic_absent_band_item", str(caught.exception))
            self.assertIn("has no price-table entry", str(caught.exception))

    @covers_requirement(
        "lore-item-catalog::registration-does-not-entitle-an-item-to-a-market"
    )
    def test_catalog_load_accepts_registered_items_not_offered_by_any_shop(self):
        synthetic_unstocked = ItemDefinition(
            key="synthetic_unstocked_item",
            display_name_zh="合成未上架物件",
            price_table_key="meal",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.FOOD,
                icon_key=ItemIconKey.FOOD,
                rarity=ItemRarity.COMMON,
                summary_zh="用於測試未上架物件載入的合成物品。",
            ),
        )
        with mock.patch.dict(ITEM_REGISTRY, {"synthetic_unstocked_item": synthetic_unstocked}, clear=False):
            catalog = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
            self.assertIsInstance(catalog, GuildCatalog)
            offered_keys = {
                offer.item_key
                for shop in catalog.shop_configs.values()
                for offer in shop.offers
            }
            self.assertNotIn("synthetic_unstocked_item", offered_keys)


if __name__ == "__main__":
    unittest.main()
