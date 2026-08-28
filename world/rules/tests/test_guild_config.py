"""Tests for immutable economy identities and the guild-economy catalog loader (tasks 2.1-2.5)."""

from tools.spec_traceability import covers_requirement

import unittest
from dataclasses import fields
from pathlib import Path

import yaml

from world.lore.economy import PRICE_TABLE
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.items import (
    ITEM_REGISTRY,
    ItemDefinition,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    SUMMARY_MAX,
)
from world.lore.shops import SHOP_REGISTRY
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.catalog import register_catalog
from world.rules.guild_config import (
    CATALOG,
    EXAM_RANKS,
    GuildCatalog,
    GuildConfigError,
    ItemOfferRule,
    ShopConfig,
    load_guild_catalog,
    validate_exam_profiles,
    validate_merit_thresholds,
    validate_quest_rewards,
    validate_shop_configs,
)
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildOfferError,
    GuildQuestOffer,
    register_guild_offer,
)
from world.skills.registry import SKILL_REGISTRY

RULEBOOK = Path(__file__).resolve().parents[2] / "rules" / "rulebook" / "guild_economy.yaml"


class CatalogRegistryIsolation(unittest.TestCase):
    def setUp(self):
        super().setUp()
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY

        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())
        self._offer_items = list(GUILD_OFFER_REGISTRY.items())
        self._catalog = CATALOG
        register_catalog()

    def tearDown(self):
        global CATALOG
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY

        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._registry_items)
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._offer_items)
        CATALOG = self._catalog
        super().tearDown()


def raw_rulebook() -> dict:
    return yaml.safe_load(RULEBOOK.read_text(encoding="utf-8"))


class ItemDefinitionTests(unittest.TestCase):
    @covers_requirement(
        "shop-economy::item-and-shop-identities-are-immutable-while-numeric-trade-rules-are-yaml-and-lore-constrained"
    )
    def test_initial_items_have_lore_price_identity_without_numbers(self):
        self.assertEqual(len(ITEM_REGISTRY), 42)
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
        self.assertEqual(set(SHOP_REGISTRY), {"altoria_general_store"})
        shop = SHOP_REGISTRY["altoria_general_store"]
        self.assertTrue(all(key in ITEM_REGISTRY for key in shop.offered_item_keys))

    @covers_requirement(
        "item-presentation-metadata::presentation-metadata-does-not-claim-unimplemented-mechanics"
    )
    def test_presentation_swap_leaves_economy_outputs_unchanged(self):
        raw = raw_rulebook()["shops"]
        baseline = validate_shop_configs(raw)
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
            changed = validate_shop_configs(raw)
            self.assertEqual(changed, baseline)
        finally:
            ITEM_REGISTRY["meal"] = original


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


class MeritThresholdTests(unittest.TestCase):
    def test_loaded_thresholds_are_strictly_increasing(self):
        raw = raw_rulebook()["merit_thresholds"]
        values = validate_merit_thresholds(raw)
        self.assertEqual(list(values), ["E", "D", "C", "B", "A", "S"])
        for lower, upper in zip(EXAM_RANKS, EXAM_RANKS[1:]):
            self.assertLess(values[lower], values[upper])

    def test_non_strict_sequence_is_rejected(self):
        bad = {"E": 5, "D": 5, "C": 40, "B": 90, "A": 200, "S": 500}
        with self.assertRaises(GuildConfigError):
            validate_merit_thresholds(bad)

    def test_negative_threshold_is_rejected(self):
        bad = {"E": -1, "D": 5, "C": 40, "B": 90, "A": 200, "S": 500}
        with self.assertRaises(GuildConfigError):
            validate_merit_thresholds(bad)

    def test_missing_threshold_rank_is_rejected(self):
        raw = raw_rulebook()["merit_thresholds"]
        bad = {k: v for k, v in raw.items() if k != "E"}
        with self.assertRaises(GuildConfigError):
            validate_merit_thresholds(bad)

    def test_unknown_threshold_rank_is_rejected(self):
        bad = {**raw_rulebook()["merit_thresholds"], "X": 1}
        with self.assertRaises(GuildConfigError):
            validate_merit_thresholds(bad)

    def test_non_integer_threshold_is_rejected(self):
        bad = {**raw_rulebook()["merit_thresholds"], "E": True}
        with self.assertRaises(GuildConfigError):
            validate_merit_thresholds(bad)


class ExamProfileTests(unittest.TestCase):
    def test_every_profile_stays_inside_its_lore_band(self):
        from world.lore.races import STATIC_TIER_REGISTRY

        raw = raw_rulebook()["exam_profiles"]
        profiles = validate_exam_profiles(raw)
        self.assertEqual(list(profiles), ["E", "D", "C", "B", "A", "S"])
        for rank, profile in profiles.items():
            band = STATIC_TIER_REGISTRY[profile.static_tier_key].band
            self.assertTrue(band[0] <= profile.atk_phys <= band[1])
            self.assertTrue(band[0] <= profile.agility <= band[1])
            self.assertTrue(band[0] <= profile.defense <= band[1])

    def test_every_exam_skill_key_exists(self):
        raw = raw_rulebook()["exam_profiles"]
        profiles = validate_exam_profiles(raw)
        for profile in profiles.values():
            for skill_key in profile.skills:
                self.assertIn(skill_key, SKILL_REGISTRY)

    def test_out_of_band_stat_is_rejected(self):
        raw = raw_rulebook()["exam_profiles"]
        mutated = {"E": {**raw["E"], "atk_phys": 100}, **{k: v for k, v in raw.items() if k != "E"}}
        with self.assertRaises(GuildConfigError):
            validate_exam_profiles(mutated)

    def test_wrong_tier_mapping_is_rejected(self):
        raw = raw_rulebook()["exam_profiles"]
        mutated = {"E": {**raw["E"], "static_tier": "human_elite"}, **{k: v for k, v in raw.items() if k != "E"}}
        with self.assertRaises(GuildConfigError):
            validate_exam_profiles(mutated)

    def test_unknown_skill_is_rejected(self):
        raw = raw_rulebook()["exam_profiles"]
        mutated = {
            "E": {**raw["E"], "skills": ["basic_attack", "no_such_skill"]},
            **{k: v for k, v in raw.items() if k != "E"},
        }
        with self.assertRaises(GuildConfigError):
            validate_exam_profiles(mutated)

    def test_missing_profile_rank_is_rejected(self):
        raw = raw_rulebook()["exam_profiles"]
        bad = {k: v for k, v in raw.items() if k != "E"}
        with self.assertRaises(GuildConfigError):
            validate_exam_profiles(bad)

    def test_unknown_profile_rank_is_rejected(self):
        raw = raw_rulebook()["exam_profiles"]
        bad = {**raw, "X": raw["E"]}
        with self.assertRaises(GuildConfigError):
            validate_exam_profiles(bad)

    def test_non_mapping_profile_entry_is_rejected(self):
        raw = raw_rulebook()["exam_profiles"]
        bad = {**raw, "E": "nope"}
        with self.assertRaises(GuildConfigError):
            validate_exam_profiles(bad)

    def test_empty_profile_skills_are_rejected(self):
        raw = raw_rulebook()["exam_profiles"]
        bad = {"E": {**raw["E"], "skills": []}, **{k: v for k, v in raw.items() if k != "E"}}
        with self.assertRaises(GuildConfigError):
            validate_exam_profiles(bad)


class ShopRuleTests(unittest.TestCase):
    def test_loaded_shops_are_integer_and_band_consistent(self):
        raw = raw_rulebook()["shops"]
        configs = validate_shop_configs(raw)
        self.assertEqual(set(configs), {"altoria_general_store"})
        config = configs["altoria_general_store"]
        self.assertIsInstance(config, ShopConfig)
        for offer in config.offers:
            self.assertIsInstance(offer, ItemOfferRule)
            self.assertIsInstance(offer.buy_copper, int)
            self.assertNotIsInstance(offer.buy_copper, bool)
            self.assertLessEqual(offer.sell_copper, offer.buy_copper)
            band = PRICE_TABLE[ITEM_REGISTRY[offer.item_key].price_table_key]
            self.assertGreaterEqual(offer.buy_copper, band.min_copper)
            if band.max_copper is not None:
                self.assertLessEqual(offer.buy_copper, band.max_copper)
            self.assertLessEqual(offer.initial_stock, offer.max_stock)

    def test_float_price_is_rejected(self):
        raw = raw_rulebook()["shops"]
        mutated = {
            **raw[0],
            "offers": [
                {**offer, **({"buy_copper": 50.0} if offer["item_key"] == "meal" else {})}
                for offer in raw[0]["offers"]
            ],
        }
        with self.assertRaises(GuildConfigError):
            validate_shop_configs([mutated])

    def test_sell_above_buy_is_rejected(self):
        raw = raw_rulebook()["shops"]
        mutated = {
            **raw[0],
            "offers": [
                {**offer, **({"sell_copper": 500} if offer["item_key"] == "meal" else {})}
                for offer in raw[0]["offers"]
            ],
        }
        with self.assertRaises(GuildConfigError):
            validate_shop_configs([mutated])

    def test_initial_exceeding_max_is_rejected(self):
        raw = raw_rulebook()["shops"]
        mutated = {
            **raw[0],
            "offers": [
                {**offer, **({"initial_stock": 99} if offer["item_key"] == "meal" else {})}
                for offer in raw[0]["offers"]
            ],
        }
        with self.assertRaises(GuildConfigError):
            validate_shop_configs([mutated])

    def test_unknown_shop_key_is_rejected(self):
        raw = raw_rulebook()["shops"]
        with self.assertRaises(GuildConfigError):
            validate_shop_configs([{**raw[0], "shop_key": "not_a_shop"}])

    def test_shops_root_must_be_a_list(self):
        with self.assertRaises(GuildConfigError):
            validate_shop_configs({"altoria_general_store": {}})

    def test_non_mapping_shop_entry_is_rejected(self):
        with self.assertRaises(GuildConfigError):
            validate_shop_configs(["nope"])

    def test_duplicate_shop_key_is_rejected(self):
        raw = raw_rulebook()["shops"]
        with self.assertRaises(GuildConfigError):
            validate_shop_configs(raw + [raw[0]])

    def test_hour_at_or_above_day_length_is_rejected(self):
        raw = raw_rulebook()["shops"]
        with self.assertRaises(GuildConfigError):
            validate_shop_configs([{**raw[0], "open_hour": 25}])

    def test_offer_not_in_shop_identity_is_rejected(self):
        raw = raw_rulebook()["shops"]
        mutated = {
            **raw[0],
            "offers": [
                *raw[0]["offers"],
                {**raw[0]["offers"][0], "item_key": "plain_sword", "buy_copper": 250, "sell_copper": 100, "max_stock": 3, "initial_stock": 1, "restock_quantity": 1},
            ],
        }
        with self.assertRaises(GuildConfigError):
            validate_shop_configs([mutated])

    def test_missing_offer_is_rejected(self):
        raw = raw_rulebook()["shops"]
        mutated = {
            **raw[0],
            "offers": [offer for offer in raw[0]["offers"] if offer["item_key"] != "meal"],
        }
        with self.assertRaises(GuildConfigError):
            validate_shop_configs([mutated])


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


if __name__ == "__main__":
    unittest.main()