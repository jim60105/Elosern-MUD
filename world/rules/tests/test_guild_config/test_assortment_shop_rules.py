"""Data-contract test: guild/shop config validation contract
Slice of ``test_guild_config``: AssortmentRuleTests, ShopRuleTests.
"""
from tools.spec_traceability import covers_requirement
import unittest
from dataclasses import replace
from unittest import mock
from world.lore.economy import PRICE_TABLE
from world.lore.items import ITEM_REGISTRY
from world.lore.items import EquipmentModifierKey
from world.lore.items import ItemDefinition
from world.lore.items import ItemIconKey
from world.lore.items import ItemKind
from world.lore.items import ItemPresentation
from world.lore.items import ItemRarity
from world.lore.settlements.assortments import ASSORTMENT_REGISTRY
from world.lore.settlements.assortments import AssortmentDefinition
from world.lore.settlements.places import PLACE_REGISTRY
from world.lore.settlements.shops import SHOP_REGISTRY
from world.lore.settlements.shops import ShopDefinition
from world.rules.guild_config import GuildConfigError
from world.rules.guild_config import ItemOfferRule
from world.rules.guild_config import ShopConfig
from world.rules.guild_config import validate_assortment_configs
from world.rules.guild_config import validate_shop_configs
from world.skills.equipment import EquipmentSlot
from ._support import (
    _assortment_row,
    _shipped_scales,
    raw_commerce,
)


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
            str(caught.exception).startswith("commerce rulebook: "),
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
        # Per-shop display names resolve to the owning place's room name, so
        # the synthetic shop needs a place row that authors its shop_key too.
        second_place = replace(
            PLACE_REGISTRY["altoria_general_store"],
            key="t_second_shop",
            service_id="t_second_shop_service",
            room_name_zh="合成二號店",
            host_name="合成二號",
            host_title="合成二號店老闆",
            authored_kwargs=(("shop_key", "t_second_shop"),),
            assortment_keys=("t_shared_goods",),
        )
        rows = [
            {**raw_commerce()["shops"][0]},
            {"shop_key": "t_second_shop", "open_hour": 9, "close_hour": 19, "restock_hour": 7},
        ]
        with mock.patch.dict(ASSORTMENT_REGISTRY, {"t_shared_goods": shared}, clear=False), \
             mock.patch.dict(
                 SHOP_REGISTRY,
                 {"altoria_general_store": first, "t_second_shop": second},
                 clear=True,
             ), mock.patch.dict(
                 PLACE_REGISTRY,
                 {"t_second_shop": second_place},
                 clear=False,
             ):
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


def _synthetic_price_item(
    key: str,
    *,
    kind: ItemKind = ItemKind.POTION,
    slot: EquipmentSlot | None = None,
    band: str = "potion",
    sellable: bool = True,
) -> ItemDefinition:
    """One file-local synthetic item; never a shipped key."""
    return ItemDefinition(
        key=key,
        display_name_zh="合成測試物品",
        price_table_key=band,
        sellable=sellable,
        presentation=ItemPresentation(
            kind=kind,
            icon_key=ItemIconKey.MISC,
            rarity=ItemRarity.COMMON,
            summary_zh="供商店分類與貨架測試使用的合成物品。",
        ),
        equipment_slot=slot,
        modifier_key=(
            EquipmentModifierKey.PLAIN_SWORD if slot is not None else None
        ),
    )


def _complete_override(item_key: str, buy_copper: int) -> dict:
    return {
        "item_key": item_key,
        "buy_copper": buy_copper,
        "sell_copper": buy_copper // 2,
        "max_stock": 2,
        "initial_stock": 1,
        "restock_quantity": 1,
    }


def _place_by_shop() -> dict:
    return {
        dict(place.authored_kwargs)["shop_key"]: place
        for place in PLACE_REGISTRY.values()
        if dict(place.authored_kwargs).get("shop_key")
    }


class ShopMembershipRouteTests(unittest.TestCase):
    """Offers derive from authored membership; nothing smuggles a good in."""

    @staticmethod
    def _shipped_offers() -> dict:
        return validate_assortment_configs(raw_commerce()["assortments"])

    @covers_requirement(
        "commerce-assortments::a-shop-s-offered-goods-are-derived-from-the-assortments-it-references"
    )
    def test_every_shop_resolves_its_authored_union_minus_removals_plus_additions(self):
        # Set equality against live data, not a snapshot: the union of the
        # referenced assortments, minus the place's removals, plus its
        # additions -- no historical roster defines what a counter carries.
        configs = validate_shop_configs(
            raw_commerce()["shops"], self._shipped_offers(), _shipped_scales()
        )
        places = _place_by_shop()
        self.assertEqual(set(configs), set(SHOP_REGISTRY))
        for shop_key, shop in SHOP_REGISTRY.items():
            place = places[shop_key]
            expected = (
                set(shop.offered_item_keys) - set(place.excluded_item_keys)
            ) | set(place.extra_item_keys)
            with self.subTest(shop=shop_key):
                self.assertEqual(
                    {offer.item_key for offer in configs[shop_key].offers},
                    expected,
                )

    @covers_requirement(
        "commerce-assortments::a-shop-s-offered-goods-are-derived-from-the-assortments-it-references"
    )
    def test_a_shelf_rejects_an_item_outside_its_declared_eligibility(self):
        # A shelf that declares itself an accessory counter cannot hold a
        # potion: the mismatch is a load error naming the shelf and the item.
        potion = _synthetic_price_item("t_shelf_potion")
        shelf = AssortmentDefinition(
            "t_shelf_rack",
            "合成貨架",
            ("t_shelf_potion",),
            allowed_item_kinds=frozenset({ItemKind.ACCESSORY}),
            allowed_equipment_slots=frozenset({EquipmentSlot.ACCESSORY}),
        )
        row = {
            "key": "t_shelf_rack",
            "offers": [_complete_override("t_shelf_potion", 100)],
        }
        with mock.patch.dict(
            ITEM_REGISTRY, {"t_shelf_potion": potion}, clear=False
        ), mock.patch.dict(
            ASSORTMENT_REGISTRY, {"t_shelf_rack": shelf}, clear=False
        ):
            with self.assertRaises(GuildConfigError) as caught:
                validate_assortment_configs([row])
            message = str(caught.exception)
            self.assertIn("t_shelf_rack", message)
            self.assertIn("t_shelf_potion", message)
            self.assertIn("does not stock", message)

    @covers_requirement(
        "commerce-assortments::an-assortment-may-not-contain-a-keepsake-band-item"
    )
    def test_a_place_addition_cannot_smuggle_a_keepsake_onto_a_counter(self):
        keepsake = _synthetic_price_item(
            "t_addition_keepsake", band="relic", sellable=False
        )
        place = replace(
            PLACE_REGISTRY["altoria_general_store"],
            extra_item_keys=("t_addition_keepsake",),
        )
        row = {
            **raw_commerce()["shops"][0],
            "overrides": [_complete_override("t_addition_keepsake", 999_999)],
        }
        with mock.patch.dict(
            ITEM_REGISTRY, {"t_addition_keepsake": keepsake}, clear=False
        ), mock.patch.dict(
            PLACE_REGISTRY,
            {"altoria_general_store": place},
            clear=False,
        ):
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([row], self._shipped_offers(), _shipped_scales())
            message = str(caught.exception)
            self.assertIn("altoria_general_store", message)
            self.assertIn("t_addition_keepsake", message)
            self.assertIn("keepsake", message)

    @covers_requirement(
        "commerce-assortments::an-assortment-may-not-contain-a-keepsake-band-item"
    )
    def test_a_hand_listed_offer_route_cannot_carry_a_keepsake_either(self):
        # ``validate_shop_configs`` accepts a caller-supplied offer mapping,
        # so the resolution itself -- not only the assortment validator -- is
        # the gate: a keepsake reaching ``offered`` is refused here.
        keepsake = _synthetic_price_item(
            "t_keepsake_probe", band="relic", sellable=False
        )
        offers = {
            "common_arms": {
                **self._shipped_offers()["common_arms"],
                "t_keepsake_probe": ItemOfferRule(
                    item_key="t_keepsake_probe",
                    buy_copper=999_999,
                    sell_copper=0,
                    max_stock=1,
                    initial_stock=1,
                    restock_quantity=1,
                ),
            }
        }
        shop = replace(
            SHOP_REGISTRY["altoria_general_store"],
            assortment_keys=("common_arms",),
        )
        with mock.patch.dict(
            ITEM_REGISTRY, {"t_keepsake_probe": keepsake}, clear=False
        ), mock.patch.dict(
            ASSORTMENT_REGISTRY,
            {
                "common_arms": replace(
                    ASSORTMENT_REGISTRY["common_arms"],
                    item_keys=(
                        *ASSORTMENT_REGISTRY["common_arms"].item_keys,
                        "t_keepsake_probe",
                    ),
                )
            },
            clear=False,
        ), mock.patch.dict(
            SHOP_REGISTRY,
            {"altoria_general_store": shop},
            clear=True,
        ):
            row = {**raw_commerce()["shops"][0]}
            with self.assertRaises(GuildConfigError) as caught:
                validate_shop_configs([row], offers, _shipped_scales())
            message = str(caught.exception)
            self.assertIn("altoria_general_store", message)
            self.assertIn("t_keepsake_probe", message)
            self.assertIn("keepsake", message)

    @covers_requirement(
        "commerce-assortments::a-shop-s-offered-goods-are-derived-from-the-assortments-it-references"
    )
    def test_a_valid_new_equipment_item_can_be_stocked(self):
        # Registration plus a shelf membership plus a numeric offer is all a
        # new good needs: no shop-specific approval table is edited.
        blade = _synthetic_price_item(
            "t_stocked_blade",
            kind=ItemKind.WEAPON,
            slot=EquipmentSlot.WEAPON_MAIN,
            band="mundane_weapon",
        )
        arms = replace(
            ASSORTMENT_REGISTRY["common_arms"],
            item_keys=(
                *ASSORTMENT_REGISTRY["common_arms"].item_keys,
                "t_stocked_blade",
            ),
        )
        rows = _assortment_row(
            "common_arms",
            lambda offers: [
                *offers,
                _complete_override("t_stocked_blade", 200),
            ],
        )
        with mock.patch.dict(
            ITEM_REGISTRY, {"t_stocked_blade": blade}, clear=False
        ), mock.patch.dict(
            ASSORTMENT_REGISTRY, {"common_arms": arms}, clear=False
        ):
            configs = validate_shop_configs(
                raw_commerce()["shops"],
                validate_assortment_configs(rows),
                _shipped_scales(),
            )
        stocked = {
            shop_key
            for shop_key, config in configs.items()
            if any(offer.item_key == "t_stocked_blade" for offer in config.offers)
        }
        self.assertTrue(stocked, "the new good reached no counter")
        for shop_key, shop in SHOP_REGISTRY.items():
            if "common_arms" in shop.assortment_keys:
                self.assertIn(shop_key, stocked)


if __name__ == "__main__":
    unittest.main()
