"""Data-contract test: guild/shop config validation contract
Tests for immutable economy identities and the guild-economy catalog loader (tasks 2.1-2.5)."""

from tools.spec_traceability import covers_requirement

import unittest
from contextlib import contextmanager
from dataclasses import fields, replace
from pathlib import Path
from unittest import mock

import yaml

from world.lore.economy import PRICE_TABLE, PriceEntry
from world.lore.guild import GUILD_BRANCH_REGISTRY
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.items import (
    ITEM_REGISTRY,
    EquipmentModifierKey,
    ItemDefinition,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    ItemUseMechanics,
    SUMMARY_MAX,
)
from world.lore.settlements.assortments import ASSORTMENT_REGISTRY, AssortmentDefinition
from world.lore.settlements.places import PLACE_REGISTRY, PlaceDefinition, PlaceKind
from world.lore.settlements.shops import (
    SHOP_REGISTRY,
    ShopDefinition,
    validate_registry_identity_uniqueness,
)
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
    validate_assortment_configs,
    validate_exam_profiles,
    validate_merit_thresholds,
    validate_price_scales,
    validate_quest_rewards,
    validate_service_hosts,
    validate_shop_configs,
)
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildOfferError,
    GuildQuestOffer,
    register_guild_offer,
)
from world.skills.equipment import EquipmentSlot
from world.skills.registry import SKILL_REGISTRY

RULEBOOK = Path(__file__).resolve().parents[2] / "rules" / "rulebook" / "guild_economy.yaml"
COMMERCE = Path(__file__).resolve().parents[2] / "rules" / "rulebook" / "commerce.yaml"


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


def raw_commerce() -> dict:
    return yaml.safe_load(COMMERCE.read_text(encoding="utf-8"))


def _shipped_scales() -> dict:
    """The shipped price_scales section, validated like catalog load does."""
    return validate_price_scales(raw_commerce()["price_scales"])


def _assortment_row(
    assortment_key: str,
    mutate_offers=None,
) -> list[dict]:
    """Deep-copied shipped assortment rows with one row's offers mutated."""
    rows = raw_commerce()["assortments"]
    out: list[dict] = []
    for row in rows:
        copy = dict(row)
        if copy["key"] == assortment_key:
            offers = [dict(offer) for offer in copy["offers"]]
            if mutate_offers is not None:
                offers = mutate_offers(offers)
            copy["offers"] = offers
        out.append(copy)
    return out


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


class AssortmentRuleTests(unittest.TestCase):
    """Assortment-level item/offer alignment (commerce-assortments delta).

    The item/offer alignment, money, band and stock rejections the old
    per-shop join enforced are now evaluated once per assortment.
    """

    @covers_requirement(
        "commerce-assortments::an-assortment-is-a-named-reusable-bundle-of-goods"
    )
    def test_shipped_assortments_validate_and_resolve(self):
        offers = validate_assortment_configs(raw_commerce()["assortments"])
        self.assertEqual(set(offers), set(ASSORTMENT_REGISTRY))
        for assortment_key, item_rules in offers.items():
            definition = ASSORTMENT_REGISTRY[assortment_key]
            self.assertEqual(set(item_rules), set(definition.item_keys))
            for rule in item_rules.values():
                self.assertIsInstance(rule, ItemOfferRule)
                self.assertIsInstance(rule.buy_copper, int)
                self.assertNotIsInstance(rule.buy_copper, bool)
                self.assertLessEqual(rule.sell_copper, rule.buy_copper)
                band = PRICE_TABLE[ITEM_REGISTRY[rule.item_key].price_table_key]
                self.assertGreaterEqual(rule.buy_copper, band.min_copper)
                if band.max_copper is not None:
                    self.assertLessEqual(rule.buy_copper, band.max_copper)
                self.assertLessEqual(rule.initial_stock, rule.max_stock)

    @covers_requirement(
        "commerce-assortments::an-assortment-is-a-named-reusable-bundle-of-goods"
    )
    def test_assortment_missing_offer_is_rejected(self):
        rows = _assortment_row(
            "staple_meals",
            lambda offers: offers[:],
        )
        rows = [
            {**row, "offers": [o for o in row["offers"] if o["item_key"] != "meal"]}
            if row["key"] == "staple_meals" else row
            for row in rows
        ]
        with self.assertRaises(GuildConfigError) as caught:
            validate_assortment_configs(rows)
        message = str(caught.exception)
        self.assertIn("staple_meals", message)
        self.assertIn("meal", message)

    @covers_requirement(
        "commerce-assortments::an-assortment-is-a-named-reusable-bundle-of-goods"
    )
    def test_offer_for_item_outside_assortment_is_rejected(self):
        rows = _assortment_row(
            "common_arms",
            lambda offers: [{**offers[0], "item_key": "meal"}, *offers[1:]],
        )
        with self.assertRaises(GuildConfigError) as caught:
            validate_assortment_configs(rows)
        message = str(caught.exception)
        self.assertIn("common_arms", message)
        self.assertIn("meal", message)

    def test_unknown_offer_item_is_rejected(self):
        rows = _assortment_row(
            "common_arms",
            lambda offers: [*offers, {"item_key": "synthetic_retired_item", "buy_copper": 100, "sell_copper": 50, "max_stock": 5, "initial_stock": 1, "restock_quantity": 1}],
        )
        with self.assertRaises(GuildConfigError) as caught:
            validate_assortment_configs(rows)
        self.assertIn("synthetic_retired_item", str(caught.exception))

    def test_unknown_item_in_assortment_identity_is_rejected(self):
        definition = AssortmentDefinition("t_bad_items", "合成壞貨", ("synthetic_unknown_key",))
        with mock.patch.dict(ASSORTMENT_REGISTRY, {"t_bad_items": definition}, clear=False):
            rows = [{"key": "t_bad_items", "offers": []}]
            with self.assertRaises(GuildConfigError) as caught:
                validate_assortment_configs(rows)
            self.assertIn("synthetic_unknown_key", str(caught.exception))

    def test_unknown_assortment_key_is_rejected(self):
        with self.assertRaises(GuildConfigError):
            validate_assortment_configs([{"key": "not_an_assortment", "offers": []}])

    def test_duplicate_assortment_key_is_rejected(self):
        rows = raw_commerce()["assortments"]
        with self.assertRaises(GuildConfigError):
            validate_assortment_configs(rows + [rows[0]])

    def test_assortments_root_must_be_a_list(self):
        with self.assertRaises(GuildConfigError) as caught:
            validate_assortment_configs({"common_arms": {}})
        self.assertTrue(
            str(caught.exception).startswith("commerce.yaml: "),
            "assortment rejections must name their rulebook source",
        )

    def test_non_mapping_assortment_entry_is_rejected(self):
        with self.assertRaises(GuildConfigError):
            validate_assortment_configs(["nope"])

    @covers_requirement(
        "commerce-assortments::an-assortment-is-a-named-reusable-bundle-of-goods"
    )
    def test_assortment_declaring_hours_is_rejected(self):
        row = raw_commerce()["assortments"][0]
        with self.assertRaises(GuildConfigError) as caught:
            validate_assortment_configs([{**row, "open_hour": 8}])
        self.assertIn("open_hour", str(caught.exception))

    def test_float_price_is_rejected(self):
        rows = _assortment_row(
            "staple_meals",
            lambda offers: [
                {**offer, "buy_copper": 50.0} if offer["item_key"] == "meal" else offer
                for offer in offers
            ],
        )
        with self.assertRaises(GuildConfigError):
            validate_assortment_configs(rows)

    def test_initial_exceeding_max_is_rejected(self):
        rows = _assortment_row(
            "staple_meals",
            lambda offers: [
                {**offer, "initial_stock": 99} if offer["item_key"] == "meal" else offer
                for offer in offers
            ],
        )
        with self.assertRaises(GuildConfigError):
            validate_assortment_configs(rows)

    def test_registry_assortment_without_rules_is_rejected(self):
        definition = AssortmentDefinition("t_orphan", "合成孤兒", ())
        with mock.patch.dict(ASSORTMENT_REGISTRY, {"t_orphan": definition}, clear=False):
            with self.assertRaises(GuildConfigError) as caught:
                validate_assortment_configs(raw_commerce()["assortments"])
            self.assertIn("t_orphan", str(caught.exception))

    @covers_requirement(
        "masterwork-price-band::a-keepsake-band-item-can-never-be-offered-for-sale"
    )
    @covers_requirement(
        "commerce-assortments::an-assortment-may-not-contain-a-keepsake-band-item"
    )
    def test_keepsake_band_item_is_rejected_at_any_price(self):
        # A file-local keepsake-band fixture item, never a shipped keepsake:
        # the assortment validator must reject it before any price check.
        keepsake = ItemDefinition(
            key="t_keepsake_probe",
            display_name_zh="合成信物",
            price_table_key="relic",
            sellable=False,
            presentation=ItemPresentation(
                kind=ItemKind.MISC,
                icon_key=ItemIconKey.MISC,
                rarity=ItemRarity.LEGENDARY,
                summary_zh="用於測試信物帶拒絕的合成物品。",
            ),
        )
        definition = AssortmentDefinition("t_keepsake_rack", "合成信物架", ("t_keepsake_probe",))
        row = {
            "key": "t_keepsake_rack",
            "offers": [
                {
                    "item_key": "t_keepsake_probe",
                    # Exactly the relic band floor: the rejection fires on
                    # the band, not on the price, so even a band-legal price
                    # is refused.
                    "buy_copper": 999_999,
                    "sell_copper": 0,
                    "max_stock": 1,
                    "initial_stock": 1,
                    "restock_quantity": 1,
                }
            ],
        }
        with mock.patch.dict(ITEM_REGISTRY, {"t_keepsake_probe": keepsake}, clear=False), \
             mock.patch.dict(ASSORTMENT_REGISTRY, {"t_keepsake_rack": definition}, clear=False):
            with self.assertRaises(GuildConfigError) as caught:
                validate_assortment_configs([row])
            message = str(caught.exception)
            self.assertIn("t_keepsake_rack", message)
            self.assertIn("t_keepsake_probe", message)
            self.assertIn("keepsake", message)


class ShopRuleTests(unittest.TestCase):
    """Shop resolution against validated assortment offers (design §3.1)."""

    @staticmethod
    def _shipped_offers() -> dict:
        return validate_assortment_configs(raw_commerce()["assortments"])

    def test_loaded_shops_are_integer_and_band_consistent(self):
        offers = self._shipped_offers()
        configs = validate_shop_configs(raw_commerce()["shops"], offers, _shipped_scales())
        self.assertEqual(set(configs), set(SHOP_REGISTRY))
        for config in configs.values():
            self.assertIsInstance(config, ShopConfig)
            self.assertEqual(
                {offer.item_key for offer in config.offers},
                set(SHOP_REGISTRY[config.shop_key].offered_item_keys),
            )
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
        # The scenario pin for the legacy guild-economy spec: a floating
        # offer price fails the join end-to-end, not just the assortment
        # validator in isolation.
        rows = _assortment_row(
            "staple_meals",
            lambda offers: [
                {**offer, "buy_copper": 50.0} if offer["item_key"] == "meal" else offer
                for offer in offers
            ],
        )
        with self.assertRaises(GuildConfigError):
            validate_shop_configs(
                raw_commerce()["shops"],
                validate_assortment_configs(rows),
                _shipped_scales(),
            )

    def test_unknown_shop_key_is_rejected(self):
        row = raw_commerce()["shops"][0]
        with self.assertRaises(GuildConfigError):
            validate_shop_configs(
                [{**row, "shop_key": "not_a_shop"}],
                self._shipped_offers(),
                _shipped_scales(),
            )

    def test_shops_root_must_be_a_list(self):
        with self.assertRaises(GuildConfigError):
            validate_shop_configs(
                {"altoria_general_store": {}},
                self._shipped_offers(),
                _shipped_scales(),
            )

    def test_non_mapping_shop_entry_is_rejected(self):
        with self.assertRaises(GuildConfigError):
            validate_shop_configs(["nope"], self._shipped_offers(), _shipped_scales())

    def test_duplicate_shop_key_is_rejected(self):
        rows = raw_commerce()["shops"]
        with self.assertRaises(GuildConfigError):
            validate_shop_configs(rows + [rows[0]], self._shipped_offers(), _shipped_scales())

    def test_hour_at_or_above_day_length_is_rejected(self):
        row = raw_commerce()["shops"][0]
        with self.assertRaises(GuildConfigError):
            validate_shop_configs([{**row, "open_hour": 25}], self._shipped_offers(), _shipped_scales())

    def test_equal_open_and_close_hours_are_rejected(self):
        row = raw_commerce()["shops"][0]
        with self.assertRaises(GuildConfigError):
            validate_shop_configs(
                [{**row, "close_hour": row["open_hour"]}],
                self._shipped_offers(),
                _shipped_scales(),
            )

    def test_shop_row_carrying_offers_is_rejected(self):
        # Commerce data moved under assortments: a leftover per-shop offers
        # block must fail closed instead of being silently ignored.
        row = raw_commerce()["shops"][0]
        with self.assertRaises(GuildConfigError) as caught:
            validate_shop_configs([{**row, "offers": []}], self._shipped_offers(), _shipped_scales())
        self.assertIn("offers", str(caught.exception))

    def test_shop_referencing_unknown_assortment_is_rejected(self):
        row = raw_commerce()["shops"][0]
        shop = replace(SHOP_REGISTRY["altoria_general_store"], assortment_keys=("no_such_assortment",))
        with mock.patch.dict(SHOP_REGISTRY, {"altoria_general_store": shop}, clear=True):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([row], self._shipped_offers(), _shipped_scales())
            message = str(caught.exception)
            self.assertIn("altoria_general_store", message)
            self.assertIn("no_such_assortment", message)

    def test_shop_without_assortments_is_rejected(self):
        row = raw_commerce()["shops"][0]
        shop = replace(SHOP_REGISTRY["altoria_general_store"], assortment_keys=())
        with mock.patch.dict(SHOP_REGISTRY, {"altoria_general_store": shop}, clear=True):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([row], self._shipped_offers(), _shipped_scales())
            self.assertIn("altoria_general_store", str(caught.exception))

    def test_duplicate_assortment_reference_is_rejected(self):
        row = raw_commerce()["shops"][0]
        shop = replace(
            SHOP_REGISTRY["altoria_general_store"],
            assortment_keys=("common_arms", "common_arms"),
        )
        with mock.patch.dict(SHOP_REGISTRY, {"altoria_general_store": shop}, clear=True):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([row], self._shipped_offers(), _shipped_scales())
            self.assertIn("common_arms", str(caught.exception))

    @covers_requirement(
        "commerce-assortments::a-shop-s-offered-goods-are-derived-from-the-assortments-it-references"
    )
    def test_overlapping_assortments_within_one_shop_are_rejected(self):
        # ``meal`` ships inside staple_meals; a local assortment sharing it
        # creates the per-shop collision the resolver must refuse.
        shared = AssortmentDefinition("t_shared_goods", "合成共用貨", ("meal",))
        offers = self._shipped_offers()
        offers = {**offers, "t_shared_goods": offers["staple_meals"]}
        shop = replace(
            SHOP_REGISTRY["altoria_general_store"],
            assortment_keys=("staple_meals", "t_shared_goods"),
        )
        with mock.patch.dict(ASSORTMENT_REGISTRY, {"t_shared_goods": shared}, clear=False), \
             mock.patch.dict(SHOP_REGISTRY, {"altoria_general_store": shop}, clear=True):
            row = raw_commerce()["shops"][0]
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([row], offers, _shipped_scales())
            message = str(caught.exception)
            self.assertIn("altoria_general_store", message)
            self.assertIn("meal", message)
            self.assertIn("staple_meals", message)
            self.assertIn("t_shared_goods", message)

    def test_two_shops_may_share_one_item_key_at_their_own_prices(self):
        # One good sold in two places at two prices is the model working,
        # not a collision: the rejection is scoped to a single shop.
        shared = AssortmentDefinition("t_shared_goods", "合成共用貨", ("meal",))
        offers = self._shipped_offers()
        offers = {
            **offers,
            "t_shared_goods": {
                "meal": replace(offers["staple_meals"]["meal"], buy_copper=7),
            },
        }
        first = SHOP_REGISTRY["altoria_general_store"]
        second = ShopDefinition(
            key="t_second_shop",
            host_name="合成二號",
            host_title="合成二號店老闆",
            assortment_keys=("t_shared_goods",),
        )
        rows = [
            {**raw_commerce()["shops"][0]},
            {"shop_key": "t_second_shop", "open_hour": 9, "close_hour": 19, "restock_hour": 7},
        ]
        second_place = replace(
            PLACE_REGISTRY["altoria_general_store"],
            key="t_second_shop_place",
            settlement_key="capital_altoria",
            assortment_keys=("t_shared_goods",),
            authored_kwargs=(("shop_key", "t_second_shop"),),
        )
        with mock.patch.dict(ASSORTMENT_REGISTRY, {"t_shared_goods": shared}, clear=False), \
             mock.patch.dict(
                 SHOP_REGISTRY,
                 {"altoria_general_store": first, "t_second_shop": second},
                 clear=True,
             ), \
             mock.patch.dict(PLACE_REGISTRY, {"t_second_shop_place": second_place}, clear=False):
            configs = validate_shop_configs(rows, offers, _shipped_scales())
            self.assertEqual(
                {offer.item_key for offer in configs["t_second_shop"].offers},
                {"meal"},
            )
            self.assertEqual(
                configs["t_second_shop"].offers[0].buy_copper,
                7,
            )
            self.assertEqual(
                {offer.item_key for offer in configs["altoria_general_store"].offers},
                set(first.offered_item_keys),
            )


def _price_shop_env(
    *,
    shop_key="t_price_stall",
    place_key="t_price_store",
    assortment_key="t_price_goods",
    item_key="t_price_probe",
    band_key="t_price_band",
    band_min=20,
    band_max=None,
    base_buy=25,
    base_sell=10,
    price_scale=None,
    overrides=(),
    extra_item_keys=(),
    excluded_item_keys=(),
    settlement_key="t_scale_city",
    scales=None,
) -> dict:
    """One synthetic price-scaling shop environment (design §8).

    A single place authoring one shop over one assortment of one item with
    its own price band — everything the scale/override pipeline touches.
    Returns the raw parse inputs (``row``, ``offers``, ``scales``) plus the
    registry rows for ``_price_shop_scope``.
    """
    item = ItemDefinition(
        key=item_key,
        display_name_zh="合成價格探針",
        price_table_key=band_key,
        sellable=True,
        presentation=ItemPresentation(
            kind=ItemKind.TOOL,
            icon_key=ItemIconKey.TOOL,
            rarity=ItemRarity.COMMON,
            summary_zh="合成價格縮放測試物。",
        ),
    )
    band = PriceEntry(band_key, "合成價格頻帶", band_min, band_max, "synthetic probe band")
    assortment = AssortmentDefinition(assortment_key, "合成價格貨架", (item_key,))
    shop = ShopDefinition(
        key=shop_key,
        host_name="合成價格攤主",
        host_title="合成價格攤主",
        assortment_keys=(assortment_key,),
    )
    place = PlaceDefinition(
        key=place_key,
        settlement_key=settlement_key,
        kind=PlaceKind.GENERAL_STORE,
        room_name_zh="合成價格雜貨店",
        room_desc_zh="A synthetic price-scaling store.",
        exterior_xy=(0, 0),
        doorway_key_zh="合成價格入口",
        doorway_aliases=("probe store",),
        host_name="合成價格店主",
        host_title="合成價格雜貨店主",
        host_race="human",
        host_subrace=None,
        host_sex="other",
        profession="t_price_merchant",
        service_id="t_price_merchant",
        assortment_keys=(assortment_key,),
        authored_kwargs=(("shop_key", shop_key),),
        extra_item_keys=extra_item_keys,
        excluded_item_keys=excluded_item_keys,
    )
    row = {"shop_key": shop_key, "open_hour": 8, "close_hour": 20, "restock_hour": 6}
    if price_scale is not None:
        row["price_scale"] = price_scale
    if overrides:
        row["overrides"] = list(overrides)
    offers = {
        assortment_key: {
            item_key: ItemOfferRule(
                item_key=item_key,
                buy_copper=base_buy,
                sell_copper=base_sell,
                max_stock=5,
                initial_stock=2,
                restock_quantity=1,
            )
        }
    }
    return {
        "row": row,
        "offers": offers,
        "scales": {settlement_key: 100} if scales is None else scales,
        "items": {item.key: item},
        "bands": {band.key: band},
        "assortments": {assortment.key: assortment},
        "shops": {shop.key: shop},
        "places": {place.key: place},
    }


@contextmanager
def _price_shop_scope(*envs):
    """Patch the registries for one or more synthetic price-shop environments."""
    items: dict = {}
    bands: dict = {}
    assortments: dict = {}
    shops: dict = {}
    places: dict = {}
    for env in envs:
        items.update(env["items"])
        bands.update(env["bands"])
        assortments.update(env["assortments"])
        shops.update(env["shops"])
        places.update(env["places"])
    with mock.patch.dict(ITEM_REGISTRY, items, clear=False), \
         mock.patch.dict(PRICE_TABLE, bands, clear=False), \
         mock.patch.dict(ASSORTMENT_REGISTRY, assortments, clear=False), \
         mock.patch.dict(SHOP_REGISTRY, shops, clear=True), \
         mock.patch.dict(PLACE_REGISTRY, places, clear=True):
        yield


class PriceScaleSectionTests(unittest.TestCase):
    """``price_scales`` section and per-shop scale validation (design §4)."""

    def test_shipped_section_is_par(self):
        self.assertEqual(_shipped_scales(), {"capital_altoria": 100})

    def test_price_scales_must_be_a_mapping(self):
        with self.assertRaises(GuildConfigError):
            validate_price_scales([("capital_altoria", 100)])

    def test_unknown_settlement_key_is_rejected(self):
        with self.assertRaises(GuildConfigError) as caught:
            validate_price_scales({"t_no_such_city": 100})
        self.assertIn("t_no_such_city", str(caught.exception))

    def test_scale_must_be_an_integer(self):
        with self.assertRaises(GuildConfigError) as caught:
            validate_price_scales({"capital_altoria": 1.5})
        self.assertIn("capital_altoria", str(caught.exception))

    def test_scale_bounds_reject_zero_and_negative(self):
        for bad in (0, -1):
            with self.assertRaises(GuildConfigError) as caught:
                validate_price_scales({"capital_altoria": bad})
            self.assertIn("capital_altoria", str(caught.exception))

    def test_scale_bounds_accept_one_and_thousand(self):
        for keep in (1, 1000):
            self.assertEqual(
                validate_price_scales({"capital_altoria": keep}),
                {"capital_altoria": keep},
            )

    def test_scale_bounds_reject_above_thousand(self):
        with self.assertRaises(GuildConfigError) as caught:
            validate_price_scales({"capital_altoria": 1001})
        self.assertIn("capital_altoria", str(caught.exception))

    def test_shop_scale_must_be_an_integer(self):
        env = _price_shop_env(price_scale=1.5)
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        self.assertIn("t_price_stall", str(caught.exception))

    def test_shop_scale_bounds_reject_bad_values(self):
        for bad in (0, -1, 1001):
            env = _price_shop_env(price_scale=bad)
            with _price_shop_scope(env):
                with self.assertRaises(GuildConfigError):
                    validate_shop_configs([env["row"]], env["offers"], env["scales"])

    @covers_requirement(
        "place-price-scaling::a-place-s-final-offer-is-a-shared-base-adjusted-by-one-local-rule"
    )
    def test_shop_scale_overrides_settlement_entry(self):
        env = _price_shop_env(price_scale=150)
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(config.offers[0].buy_copper, (25 * 150 + 50) // 100)

    @covers_requirement(
        "place-price-scaling::a-place-s-final-offer-is-a-shared-base-adjusted-by-one-local-rule"
    )
    def test_shop_inherits_settlement_scale(self):
        env = _price_shop_env(scales={"t_scale_city": 150})
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(config.offers[0].buy_copper, (25 * 150 + 50) // 100)

    def test_shop_settlement_without_scale_entry_fails_load(self):
        env = _price_shop_env(scales={"t_other_city": 100})
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        message = str(caught.exception)
        self.assertIn("t_scale_city", message)
        self.assertIn("t_price_store", message)


class PlacePriceScalingTests(unittest.TestCase):
    """Resolved price model over synthetic places (place-price-scaling §4/§8)."""

    @covers_requirement(
        "place-price-scaling::a-place-s-final-offer-is-a-shared-base-adjusted-by-one-local-rule"
    )
    def test_rounding_boundaries_are_half_up(self):
        # (base * scale + 50) // 100: 25@150 -> 37.5 rounds up to 38;
        # 10@150 -> 15 exact; 33@150 -> 49.5 rounds up to 50.
        env = _price_shop_env(base_buy=25, base_sell=10, price_scale=150)
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(
            (config.offers[0].buy_copper, config.offers[0].sell_copper),
            (38, 15),
        )

        env = _price_shop_env(base_buy=33, base_sell=33, price_scale=150)
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(config.offers[0].buy_copper, 50)

    @covers_requirement(
        "place-price-scaling::a-place-s-final-offer-is-a-shared-base-adjusted-by-one-local-rule"
    )
    def test_par_scale_leaves_prices_unchanged(self):
        env = _price_shop_env(base_buy=25, base_sell=10, price_scale=100)
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(
            (config.offers[0].buy_copper, config.offers[0].sell_copper),
            (25, 10),
        )

    @covers_requirement(
        "place-price-scaling::resolved-prices-are-validated-not-the-bases"
    )
    def test_scaled_price_outside_band_fails_load(self):
        # Base 25 is legal inside band 20..30 at par; at scale 150 it
        # resolves to 38, above the ceiling, and load fails naming the
        # place, the item and the resolved value.
        env = _price_shop_env(band_min=20, band_max=30, base_buy=25, price_scale=150)
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        message = str(caught.exception)
        self.assertIn("t_price_store", message)
        self.assertIn("t_price_probe", message)
        self.assertIn("38", message)

    @covers_requirement(
        "place-price-scaling::resolved-prices-are-validated-not-the-bases"
    )
    def test_scaled_sell_above_buy_fails_load(self):
        # The inverted base (sell 30 > buy 25) is legal at assortment level
        # now; the moved rejection fires on the resolved values here.
        env = _price_shop_env(base_buy=25, base_sell=30)
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        message = str(caught.exception)
        self.assertIn("t_price_store", message)
        self.assertIn("t_price_probe", message)
        self.assertIn("30", message)

    @covers_requirement(
        "place-price-scaling::an-override-is-complete-or-rejected"
    )
    def test_override_is_absolute_and_not_scaled(self):
        override = {
            "item_key": "t_price_probe",
            "buy_copper": 42,
            "sell_copper": 21,
            "max_stock": 3,
            "initial_stock": 1,
            "restock_quantity": 1,
        }
        env = _price_shop_env(price_scale=200, overrides=(override,))
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(
            (config.offers[0].buy_copper, config.offers[0].sell_copper),
            (42, 21),
        )

    @covers_requirement(
        "place-price-scaling::an-override-is-complete-or-rejected"
    )
    def test_partial_override_fails_naming_missing_fields(self):
        partial = {
            "item_key": "t_price_probe",
            "buy_copper": 42,
            "sell_copper": 21,
            "max_stock": 3,
            "initial_stock": 1,
        }
        env = _price_shop_env(overrides=(partial,))
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        message = str(caught.exception)
        self.assertIn("t_price_store", message)
        self.assertIn("t_price_probe", message)
        self.assertIn("restock_quantity", message)

    @covers_requirement(
        "place-price-scaling::an-override-is-complete-or-rejected"
    )
    def test_override_for_unoffered_item_fails_load(self):
        # A known item that is in none of the place's assortments and is not
        # one of its additions: the override names an unoffered good.
        curio = ItemDefinition(
            key="t_price_curio",
            display_name_zh="合成珍奇",
            price_table_key="t_price_band",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MISC,
                icon_key=ItemIconKey.MISC,
                rarity=ItemRarity.COMMON,
                summary_zh="合成價格縮放的珍奇物。",
            ),
        )
        override = {
            "item_key": "t_price_curio",
            "buy_copper": 42,
            "sell_copper": 21,
            "max_stock": 3,
            "initial_stock": 1,
            "restock_quantity": 1,
        }
        env = _price_shop_env(overrides=(override,))
        env["items"]["t_price_curio"] = curio
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        message = str(caught.exception)
        self.assertIn("t_price_store", message)
        self.assertIn("t_price_curio", message)

    @covers_requirement(
        "place-price-scaling::a-place-may-add-and-remove-individual-items"
    )
    def test_extra_without_override_fails_load(self):
        env = _price_shop_env(extra_item_keys=("t_price_curio",))
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        self.assertIn("t_price_curio", str(caught.exception))

    @covers_requirement(
        "place-price-scaling::a-place-may-add-and-remove-individual-items"
    )
    def test_extra_with_complete_override_is_offered(self):
        curio = ItemDefinition(
            key="t_price_curio",
            display_name_zh="合成珍奇",
            price_table_key="t_price_band",
            sellable=True,
            presentation=ItemPresentation(
                kind=ItemKind.MISC,
                icon_key=ItemIconKey.MISC,
                rarity=ItemRarity.COMMON,
                summary_zh="合成價格縮放的珍奇物。",
            ),
        )
        override = {
            "item_key": "t_price_curio",
            "buy_copper": 42,
            "sell_copper": 21,
            "max_stock": 3,
            "initial_stock": 1,
            "restock_quantity": 1,
        }
        env = _price_shop_env(extra_item_keys=("t_price_curio",), overrides=(override,))
        env["items"]["t_price_curio"] = curio
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(
            {offer.item_key for offer in config.offers},
            {"t_price_probe", "t_price_curio"},
        )

    @covers_requirement(
        "place-price-scaling::a-place-may-add-and-remove-individual-items"
    )
    def test_removal_matching_no_assortment_item_fails_load(self):
        env = _price_shop_env(excluded_item_keys=("t_no_such_item",))
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        self.assertIn("t_no_such_item", str(caught.exception))

    @covers_requirement(
        "place-price-scaling::a-place-may-add-and-remove-individual-items"
    )
    def test_removal_drops_the_item_from_offers(self):
        env = _price_shop_env(excluded_item_keys=("t_price_probe",))
        with _price_shop_scope(env):
            config = validate_shop_configs(
                [env["row"]], env["offers"], env["scales"]
            )["t_price_stall"]
        self.assertEqual(config.offers, ())

    @covers_requirement(
        "place-price-scaling::a-place-may-add-and-remove-individual-items"
    )
    def test_override_for_removed_item_fails_load(self):
        override = {
            "item_key": "t_price_probe",
            "buy_copper": 42,
            "sell_copper": 21,
            "max_stock": 3,
            "initial_stock": 1,
            "restock_quantity": 1,
        }
        env = _price_shop_env(
            excluded_item_keys=("t_price_probe",), overrides=(override,)
        )
        with _price_shop_scope(env):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([env["row"]], env["offers"], env["scales"])
        self.assertIn("t_price_probe", str(caught.exception))

    @covers_requirement(
        "place-price-scaling::a-place-s-final-offer-is-a-shared-base-adjusted-by-one-local-rule"
    )
    def test_same_item_two_places_stays_one_definition(self):
        # Design §8: one item at two resolved prices is one item definition.
        scaled = _price_shop_env()
        override = {
            "item_key": "t_price_probe",
            "buy_copper": 42,
            "sell_copper": 21,
            "max_stock": 3,
            "initial_stock": 1,
            "restock_quantity": 1,
        }
        overridden = _price_shop_env(
            shop_key="t_price_stall_b",
            place_key="t_price_store_b",
            overrides=(override,),
        )
        with _price_shop_scope(scaled, overridden):
            configs = validate_shop_configs(
                [scaled["row"], overridden["row"]],
                scaled["offers"],
                scaled["scales"],
            )
            first = configs["t_price_stall"].offers[0]
            second = configs["t_price_stall_b"].offers[0]
            self.assertEqual(first.item_key, second.item_key)
            self.assertIs(ITEM_REGISTRY[first.item_key], ITEM_REGISTRY[second.item_key])
            self.assertNotEqual(first.buy_copper, second.buy_copper)


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


class ServiceHostRosterTests(CatalogRegistryIsolation):
    """Derived service-host roster: places yield rows; rejections are unchanged (design §3.2)."""

    # The rows the hand-authored service_hosts roster shipped before this
    # change removed it. The derived roster must reproduce them field for
    # field — that is the change's behaviour-neutrality gate.
    FORMER_YAML_ROWS = (
        {
            "name": "葛里安·衛登",
            "title": "阿爾托利亞分會會長",
            "profession": "guild_staff",
            "anchor_room": "altoria_guild_hall",
            "service_id": "altoria_guild_master",
            "branch_key": "guild_branch_altoria",
            "dialogue_key": "guild_staff",
        },
        {
            "name": "瑪爾特·金秤",
            "title": "阿爾托利亞雜貨商店老闆",
            "profession": "merchant",
            "anchor_room": "altoria_general_store",
            "service_id": "altoria_merchant",
            "shop_key": "altoria_general_store",
        },
    )

    def _assert_reproduces_former_rows(self, rows):
        self.assertEqual(
            [row.service_id for row in rows],
            [
                "altoria_guild_master", "altoria_merchant", "altoria_blacksmith",
                "altoria_eatery_owner", "altoria_tailor",
            ],
        )
        for row, former in zip(rows, self.FORMER_YAML_ROWS):
            self.assertEqual(row.name, former["name"])
            self.assertEqual(row.title, former["title"])
            self.assertEqual(row.profession.key, former["profession"])
            self.assertEqual(row.anchor_room, former["anchor_room"])
            self.assertEqual(row.service_id, former["service_id"])
            expected_kwargs = {
                key: value
                for key, value in former.items()
                if key not in ("name", "title", "profession", "anchor_room", "service_id")
            }
            self.assertEqual(row.authored_kwargs, expected_kwargs)

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_shipped_roster_reproduces_the_removed_yaml_rows_exactly(self):
        rows = validate_service_hosts()
        self._assert_reproduces_former_rows(rows)
        guild, merchant = rows[0], rows[1]
        branch = GUILD_BRANCH_REGISTRY["guild_branch_altoria"]
        store = SHOP_REGISTRY["altoria_general_store"]
        # The identity join that used to be hand-synchronized across four
        # files still holds: the guild host's authored identity is the guild
        # branch's, and the merchant host's is the derived shop's.
        self.assertEqual((guild.name, guild.title), (branch.host_name, branch.host_title))
        self.assertEqual((merchant.name, merchant.title), (store.host_name, store.host_title))

    def test_catalog_exposes_the_roster(self):
        catalog = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
        self.assertEqual(
            [row.service_id for row in catalog.service_hosts],
            [
                "altoria_guild_master", "altoria_merchant", "altoria_blacksmith",
                "altoria_eatery_owner", "altoria_tailor",
            ],
        )
        self.assertEqual(
            set(catalog.host_by_service_id),
            {
                "altoria_guild_master", "altoria_merchant", "altoria_blacksmith",
                "altoria_eatery_owner", "altoria_tailor",
            },
        )

    def test_rulebook_no_longer_hand_authors_a_service_hosts_roster(self):
        # The roster is derived from the place registry; a hand-authored
        # section would declare each host a second time. Derivation makes
        # disagreement unrepresentable, so the YAML section is gone and the
        # catalog still loads the full derived roster.
        self.assertNotIn("service_hosts", raw_rulebook())
        catalog = load_guild_catalog(QUEST_DEFINITION_REGISTRY)
        self.assertEqual(
            [row.service_id for row in catalog.service_hosts],
            [
                "altoria_guild_master", "altoria_merchant", "altoria_blacksmith",
                "altoria_eatery_owner", "altoria_tailor",
            ],
        )

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_named_offenses_raise_the_catalog_error_family_without_db_access(self):
        store = PLACE_REGISTRY["altoria_general_store"]
        mutations = [
            # Empty (whitespace-only) required field.
            replace(store, key="t_offense", service_id="t_offense", host_title="   "),
            # Missing (empty) required field.
            replace(store, key="t_offense", service_id="t_offense", host_name=""),
            # Non-string anchor tag (the place key doubles as the room tag).
            replace(store, key=7, service_id="t_offense"),
            # Profession naming no registry row.
            replace(store, key="t_offense", service_id="t_offense", profession="blacksmith"),
            # Blueprint component identity kwargs the place fails to supply.
            replace(store, key="t_offense", service_id="t_offense", authored_kwargs=()),
            # Authored kwargs no blueprint component consumes.
            replace(
                store,
                key="t_offense",
                service_id="t_offense",
                authored_kwargs=(
                    ("shop_key", "t_offense_shop"),
                    ("branch_key", "guild_branch_altoria"),
                ),
            ),
        ]
        for position, place in enumerate(mutations):
            with self.subTest(mutation=position):
                with mock.patch.dict(
                    PLACE_REGISTRY, {"t_offense_place": place}, clear=True
                ):
                    with self.assertRaises(GuildConfigError):
                        validate_service_hosts()

    def test_duplicate_service_anchor_in_the_place_registry_is_rejected(self):
        guild = PLACE_REGISTRY["altoria_guild_hall"]
        store = PLACE_REGISTRY["altoria_general_store"]
        colliding = replace(guild, key="t_colliding", service_id=store.service_id)
        with mock.patch.dict(
            PLACE_REGISTRY, {"t_colliding": colliding}, clear=False
        ):
            with self.assertRaises(GuildConfigError):
                validate_service_hosts()

    def test_person_bound_profession_place_is_rejected_as_an_anchor(self):
        # The roster row IS the anchor registration: anchoring a blueprint
        # whose components co-presence by design (service-anchoring) is the
        # invalid combination, rejected before any host is ever created.
        from world.rules import profession_config
        from world.rules.profession_config import Profession, ProfessionComponent

        courier = Profession(
            key="courier",
            components=(ProfessionComponent("scripted_dialogue", "person"),),
            schedule_template=None,
            default_tier=None,
        )
        place = replace(
            PLACE_REGISTRY["altoria_general_store"],
            key="t_courier_place",
            service_id="t_courier",
            profession="courier",
        )
        with mock.patch.object(profession_config, "TABLE", {"courier": courier}):
            with mock.patch.dict(
                PLACE_REGISTRY, {"t_courier_place": place}, clear=True
            ):
                with self.assertRaises(GuildConfigError):
                    validate_service_hosts()

    def test_malformed_profession_rulebook_surfaces_as_catalog_error(self):
        from world.rules import profession_config

        with mock.patch.object(
            profession_config,
            "get_profession",
            side_effect=profession_config.ProfessionConfigError("broken rulebook"),
        ):
            with self.assertRaises(GuildConfigError):
                validate_service_hosts()

    @covers_requirement(
        "guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster"
    )
    def test_derived_shop_row_collision_with_guild_registry_row_is_rejected(self):
        # The authored-name uniqueness rule (shops x guild branches x guild
        # ranks) runs unchanged over the DERIVED shop rows: a planted
        # collision between the derived merchant row and a guild branch row
        # names both holders.
        merchant = SHOP_REGISTRY["altoria_general_store"]
        collision = replace(
            GUILD_BRANCH_REGISTRY["guild_branch_altoria"],
            host_name=merchant.host_name,
        )
        with self.assertRaises(ValueError) as caught:
            validate_registry_identity_uniqueness(
                branch_rows={
                    **GUILD_BRANCH_REGISTRY,
                    "guild_branch_altoria": collision,
                },
                rank_rows=GUILD_RANK_REGISTRY,
            )
        message = str(caught.exception)
        self.assertIn("shop:altoria_general_store", message)
        self.assertIn("guild_branch:guild_branch_altoria", message)


if __name__ == "__main__":
    unittest.main()