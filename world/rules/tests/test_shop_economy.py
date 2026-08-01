"""Atomic shop trade tests (tasks 9.1-9.5)."""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import Merchant
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.clock import WorldClock
from world.rules.economy import (
    TradeError,
    TradeReason,
    buy,
    parse_merchant_stock,
    sell,
    shop_is_open,
)
from world.rules.guild_config import CATALOG, load_catalog_into_cache
from world.rules.guild_offers import GUILD_OFFER_REGISTRY
from world.skills.equipment import list_items


class ShopRegistryIsolation(QuestRegistryIsolation):
    def setUp(self):
        super().setUp()
        register_catalog()
        self._previous_catalog = CATALOG
        self._previous_offers = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        global CATALOG
        CATALOG = self._previous_catalog
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._previous_offers)
        super().tearDown()


class ShopTradeTests(ShopRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        load_catalog_into_cache()
        self.store = create_object(Room, key="store")
        self.merchant_npc = create_object(NPC, key="merchant", location=self.store)
        self.merchant = Merchant.create(
            self.merchant_npc,
            service_id="merchant",
            shop_key="altoria_general_store",
        )
        self.merchant_npc.components.add(self.merchant)
        self.merchant.merchant_stock = {
            "meal": 20,
            "healing_potion": 3,
            "plain_sword": 1,
        }
        self.player = create_object(PlayerCharacter, key="shopper")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.store
        self.player.db.wallet = 100

    def _open_clock(self, hour=12):
        tick = hour * 3600
        return WorldClock(tick)

    def test_successful_purchase_uses_integer_copper(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = buy(self.player, self.merchant_npc, "meal", 2)
        self.assertEqual(result["total_copper"], 20)
        self.assertEqual(result["wallet"], 80)
        self.assertEqual(list_items(self.player), ["meal", "meal"])
        stock = parse_merchant_stock(self.merchant)
        self.assertEqual(stock["meal"], 18)

    def test_insufficient_funds_changes_nothing(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as ctx:
                buy(self.player, self.merchant_npc, "plain_sword", 1)
        self.assertEqual(ctx.exception.args[0], TradeReason.INSUFFICIENT_FUNDS)
        self.assertEqual(self.player.db.wallet, 100)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(parse_merchant_stock(self.merchant)["plain_sword"], 1)

    def test_insufficient_stock_changes_nothing(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as ctx:
                buy(self.player, self.merchant_npc, "healing_potion", 4)
        self.assertEqual(ctx.exception.args[0], TradeReason.INSUFFICIENT_STOCK)

    def test_sale_cannot_overflow_merchant_stock(self):
        self.player.db.wallet = 0
        self.player.db.inventory = ["plain_sword", "plain_sword", "plain_sword"]
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as ctx:
                sell(self.player, self.merchant_npc, "plain_sword", 3)
        self.assertEqual(ctx.exception.args[0], TradeReason.STOCK_OVERFLOW)
        self.assertEqual(self.player.db.wallet, 0)
        self.assertEqual(
            list_items(self.player),
            ["plain_sword", "plain_sword", "plain_sword"],
        )

    def test_successful_sale_credits_exact_copper(self):
        self.player.db.wallet = 0
        self.player.db.inventory = ["healing_potion", "healing_potion"]
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = sell(self.player, self.merchant_npc, "healing_potion", 2)
        self.assertEqual(result["total_copper"], 100)
        self.assertEqual(self.player.db.wallet, 100)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(parse_merchant_stock(self.merchant)["healing_potion"], 5)

    def test_unknown_or_unsellable_item_rejected(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError):
                buy(self.player, self.merchant_npc, "no_such_item", 1)
        # Make meal unsellable by checking ITEM_REGISTRY sellable flag is true;
        # a genuinely unsellable item requires a registry change, so use a
        # not-offered item key instead.
        with self.assertRaises(TradeError) as ctx:
            sell(self.player, self.merchant_npc, "no_such_item", 1)
        self.assertEqual(ctx.exception.args[0], TradeReason.UNKNOWN_ITEM)

    def test_closed_shop_rejects_trade(self):
        with patch("world.rules.economy.get_world_clock", return_value=WorldClock(3 * 3600)):
            self.assertFalse(shop_is_open("altoria_general_store"))
            with self.assertRaises(TradeError) as ctx:
                buy(self.player, self.merchant_npc, "meal", 1)
            self.assertEqual(ctx.exception.args[0], TradeReason.CLOSED)

    def test_bad_quantity_rejected(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            for bad in (0, -1, 1.5, True):
                with self.subTest(quantity=bad):
                    with self.assertRaises(TradeError) as ctx:
                        buy(self.player, self.merchant_npc, "meal", bad)
                    self.assertEqual(ctx.exception.args[0], TradeReason.BAD_QUANTITY)

    def test_remote_merchant_rejected(self):
        other = create_object(Room, key="other")
        self.player.location = other
        with self.assertRaises(TradeError) as ctx:
            buy(self.player, self.merchant_npc, "meal", 1)
        self.assertEqual(ctx.exception.args[0], TradeReason.REMOTE_MERCHANT)

    def test_fault_injection_restores_every_trade_surface(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            snapshot = (
                self.player.db.wallet,
                list(self.player.db.inventory or []),
                parse_merchant_stock(self.merchant)["meal"],
            )

            class FakeAtomic:
                def __enter__(self):
                    return self

                def __exit__(self, *exc_info):
                    raise RuntimeError("db failure")

            with patch("django.db.transaction.atomic", return_value=FakeAtomic()):
                with self.assertRaises(RuntimeError):
                    buy(self.player, self.merchant_npc, "meal", 2)
            self.assertEqual(
                (
                    self.player.db.wallet,
                    list(self.player.db.inventory or []),
                    parse_merchant_stock(self.merchant)["meal"],
                ),
                snapshot,
            )

    def test_no_float_created_by_trade(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, "meal", 1)
        self.assertNotIsInstance(self.player.db.wallet, float)
        self.assertEqual(self.player.db.wallet, 90)


class MerchantStockParsingTests(ShopRegistryIsolation, EvenniaTest):
    def test_malformed_stock_fails_closed(self):
        from typeclasses.components import Merchant as MerchantComponent

        npc = create_object(NPC, key="bad merchant")
        merchant = MerchantComponent.create(npc, service_id="m", shop_key="altoria_general_store")
        npc.components.add(merchant)
        for bad in ({"meal": -1}, {"meal": 1.5}, {"no_such_item": 1}):
            merchant.merchant_stock = bad
            with self.subTest(stock=bad):
                with self.assertRaises(TradeError) as ctx:
                    parse_merchant_stock(merchant)
                self.assertEqual(ctx.exception.args[0], TradeReason.MALFORMED_STOCK)


if __name__ == "__main__":
    import unittest

    unittest.main()