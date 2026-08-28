"""Atomic shop trade tests (tasks 9.1-9.5)."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase

from commands.localized import CmdDrop, CmdGet, CmdGive
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


class ShopTradeTests(ShopRegistryIsolation, EvenniaCommandTestMixin, EvenniaTest):
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

    @covers_requirement("shop-economy::buying-and-selling-commit-wallet-inventory-acquisition-progress-and-stock-atomically", "affinity-system::deterministic-gains-apply-at-talk-trade-and-guild-success-paths")
    def test_successful_purchase_uses_integer_copper(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = buy(self.player, self.merchant_npc, "meal", 2)
        self.assertEqual(result["total_copper"], 20)
        self.assertEqual(result["wallet"], 80)
        self.assertEqual(list_items(self.player), ["meal", "meal"])
        stock = parse_merchant_stock(self.merchant)
        self.assertEqual(stock["meal"], 18)
        self.assertEqual(self.merchant_npc.relations.affinity_for(self.player), 1)

    def test_insufficient_funds_changes_nothing(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as ctx:
                buy(self.player, self.merchant_npc, "plain_sword", 1)
        self.assertEqual(ctx.exception.args[0], TradeReason.INSUFFICIENT_FUNDS)
        self.assertEqual(self.player.db.wallet, 100)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(parse_merchant_stock(self.merchant)["plain_sword"], 1)
        self.assertFalse(self.merchant_npc.relations.has_record(self.player))

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
        self.assertFalse(self.merchant_npc.relations.has_record(self.player))

    def test_successful_sale_credits_exact_copper(self):
        self.player.db.wallet = 0
        self.player.db.inventory = ["healing_potion", "healing_potion"]
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = sell(self.player, self.merchant_npc, "healing_potion", 2)
        self.assertEqual(result["total_copper"], 100)
        self.assertEqual(self.player.db.wallet, 100)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(parse_merchant_stock(self.merchant)["healing_potion"], 5)
        self.assertEqual(self.merchant_npc.relations.affinity_for(self.player), 1)

    @covers_requirement("shop-economy::item-and-shop-identities-are-immutable-while-numeric-trade-rules-are-yaml-and-lore-constrained")
    def test_unknown_or_unsellable_item_rejected(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError):
                buy(self.player, self.merchant_npc, "no_such_item", 1)
        with self.assertRaises(TradeError) as ctx:
            sell(self.player, self.merchant_npc, "no_such_item", 1)
        self.assertEqual(ctx.exception.args[0], TradeReason.UNKNOWN_ITEM)
        # royal_signet_ring is a genuinely unsellable registry item; the
        # sellable gate precedes merchant and shop-open resolution.
        self.player.db.inventory = ["royal_signet_ring"]
        with self.assertRaises(TradeError) as ctx:
            sell(self.player, self.merchant_npc, "royal_signet_ring", 1)
        self.assertEqual(ctx.exception.args[0], TradeReason.UNSELLABLE)
        self.assertEqual(self.player.db.inventory, ["royal_signet_ring"])

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

    @covers_requirement("affinity-system::deterministic-gains-apply-at-talk-trade-and-guild-success-paths")
    def test_non_npc_merchant_host_is_rejected_before_any_write(self):
        from typeclasses.monsters import Monster

        fake = create_object(Monster, key="fake merchant", location=self.store)
        fake.components.add(
            Merchant.create(fake, service_id="m", shop_key="altoria_general_store")
        )
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as ctx:
                buy(self.player, fake, "meal", 1)
        self.assertEqual(ctx.exception.args[0], TradeReason.NO_MERCHANT)
        self.assertEqual(self.player.db.wallet, 100)
        self.assertEqual(list_items(self.player), [])
        self.assertFalse(fake.relations.has_record(self.player))

    def test_fault_injection_restores_every_trade_surface(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            snapshot = (
                self.player.db.wallet,
                list(self.player.db.inventory or []),
                parse_merchant_stock(self.merchant)["meal"],
                self.merchant_npc.db.relations_data,
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
                    self.merchant_npc.db.relations_data,
                ),
                snapshot,
            )

    def test_no_float_created_by_trade(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, "meal", 1)
        self.assertNotIsInstance(self.player.db.wallet, float)
        self.assertEqual(self.player.db.wallet, 90)

    def _contained(self, item_key):
        return [obj for obj in self.player.contents if obj.key == item_key]

    @covers_requirement("shop-economy::shop-economy-stays-consistent-with-the-canonical-inventory")
    @covers_requirement("equipment-inventory::the-key-list-is-the-single-canonical-inventory-record-for-registry-items")
    def test_buy_materializes_a_contained_object_per_item(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, "meal", 2)
        self.assertEqual(len(self._contained("meal")), 2)
        self.assertTrue(all(obj.db.registry_key == "meal" for obj in self._contained("meal")))
        self.assertEqual(list_items(self.player), ["meal", "meal"])

    @covers_requirement("shop-economy::shop-economy-stays-consistent-with-the-canonical-inventory")
    def test_sell_removes_the_contained_objects(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, "meal", 2)
            sell(self.player, self.merchant_npc, "meal", 1)
        self.assertEqual(len(self._contained("meal")), 1)
        self.assertEqual(list_items(self.player), ["meal"])
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            sell(self.player, self.merchant_npc, "meal", 1)
        self.assertEqual(self._contained("meal"), [])
        self.assertEqual(list_items(self.player), [])

    def test_sell_deletes_what_exists_when_containment_holds_fewer(self):
        self.player.db.inventory = ["meal", "meal"]
        self.merchant.merchant_stock = {"meal": 5}
        create_object(
            "typeclasses.objects.Object",
            key="meal",
            attributes=[("registry_key", "meal")],
            location=self.player,
        )
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = sell(self.player, self.merchant_npc, "meal", 2)
        self.assertEqual(result["quantity"], 2)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(self._contained("meal"), [])

    def test_bought_item_can_be_dropped(self):
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, "meal", 1)
        output = self.call(CmdDrop(), "meal", caller=self.player)
        self.assertIn("你丟下了meal。", output)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(self._contained("meal"), [])
        self.assertEqual(len([o for o in self.store.contents if o.key == "meal"]), 1)

    def test_bought_item_can_be_given(self):
        recipient = create_object(PlayerCharacter, key="recipient", location=self.store)
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            buy(self.player, self.merchant_npc, "meal", 1)
        output = self.call(CmdGive(), "meal = recipient", caller=self.player)
        self.assertIn("你把meal交給了", output)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(self._contained("meal"), [])
        self.assertEqual(len([o for o in recipient.contents if o.key == "meal"]), 1)

    @covers_requirement("shop-economy::shop-economy-stays-consistent-with-the-canonical-inventory")
    def test_picked_up_item_is_sellable(self):
        create_object(
            "typeclasses.objects.Object",
            key="healing_potion",
            attributes=[("registry_key", "healing_potion")],
            location=self.store,
        )
        self.call(CmdGet(), "healing_potion", caller=self.player)
        self.assertEqual(list_items(self.player), ["healing_potion"])
        self.assertEqual(len(self._contained("healing_potion")), 1)
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = sell(self.player, self.merchant_npc, "healing_potion", 1)
        self.assertEqual(result["quantity"], 1)
        self.assertEqual(list_items(self.player), [])
        self.assertEqual(self._contained("healing_potion"), [])

    @covers_requirement(
        "item-presentation-metadata::presentation-metadata-does-not-claim-unimplemented-mechanics"
    )
    def test_presentation_swap_leaves_buy_sell_outcomes_unchanged(self):
        """Swapping a registry item's presentation must not change trade results."""
        from world.lore.items import (
            ITEM_REGISTRY,
            ItemDefinition,
            ItemIconKey,
            ItemKind,
            ItemPresentation,
            ItemRarity,
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

        def trade_round():
            self.player.db.wallet = 100
            self.player.db.inventory = []
            self.merchant.merchant_stock = {"meal": 20, "healing_potion": 3, "plain_sword": 1}
            with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
                buy_result = buy(self.player, self.merchant_npc, "meal", 2)
                sell_result = sell(self.player, self.merchant_npc, "meal", 2)
            return (
                buy_result,
                sell_result,
                list_items(self.player),
                parse_merchant_stock(self.merchant),
                self.player.db.wallet,
            )

        baseline = trade_round()
        ITEM_REGISTRY["meal"] = altered
        try:
            swapped = trade_round()
        finally:
            ITEM_REGISTRY["meal"] = original

        self.assertEqual(swapped, baseline)


class EquippedRemovalGuardTests(ShopRegistryIsolation, EvenniaCommandTestMixin, EvenniaTest):
    """Rubber-duck run-2 blocker: removal writers never unhold an equipped key."""

    EMPTY_EQUIPMENT = {
        "weapon_main": None,
        "weapon_off": None,
        "armor": None,
        "accessories": [],
    }

    def setUp(self):
        super().setUp()
        load_catalog_into_cache()
        self.store = create_object(Room, key="guard store")
        self.merchant_npc = create_object(NPC, key="guard merchant", location=self.store)
        self.merchant = Merchant.create(
            self.merchant_npc,
            service_id="guard-merchant",
            shop_key="altoria_general_store",
        )
        self.merchant_npc.components.add(self.merchant)
        self.merchant.merchant_stock = {"meal": 20, "healing_potion": 3, "plain_sword": 1}
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.store
        self.player.db.wallet = 0
        self.player.db.inventory = []
        self.player.db.equipment = dict(self.EMPTY_EQUIPMENT)

    def _open_clock(self, hour=12):
        return WorldClock(hour * 3600)

    def _wear(self, *keys):
        self.player.db.inventory = list(keys)
        if keys:
            self.player.db.equipment = {
                **self.EMPTY_EQUIPMENT,
                "weapon_main": keys[0],
            }

    def test_sell_last_equipped_key_is_refused_without_mutation(self):
        self.player.db.inventory = ["plain_sword"]
        self.player.db.equipment = {**self.EMPTY_EQUIPMENT, "weapon_main": "plain_sword"}
        stock_before = parse_merchant_stock(self.merchant)["plain_sword"]
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            with self.assertRaises(TradeError) as ctx:
                sell(self.player, self.merchant_npc, "plain_sword", 1)
        self.assertEqual(ctx.exception.args[0], TradeReason.EQUIPPED_ITEM)
        self.assertEqual(self.player.db.wallet, 0)
        self.assertEqual(list_items(self.player), ["plain_sword"])
        self.assertEqual(
            self.player.db.equipment["weapon_main"], "plain_sword"
        )
        self.assertEqual(parse_merchant_stock(self.merchant)["plain_sword"], stock_before)

    def test_sell_leaving_one_equipped_copy_is_allowed(self):
        self.player.db.inventory = ["plain_sword", "plain_sword"]
        self.player.db.equipment = {**self.EMPTY_EQUIPMENT, "weapon_main": "plain_sword"}
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = sell(self.player, self.merchant_npc, "plain_sword", 1)
        self.assertEqual(result["quantity"], 1)
        self.assertEqual(list_items(self.player), ["plain_sword"])

    def test_unequipped_item_sells_normally(self):
        self.player.db.inventory = ["plain_sword"]
        with patch("world.rules.economy.get_world_clock", return_value=self._open_clock()):
            result = sell(self.player, self.merchant_npc, "plain_sword", 1)
        self.assertEqual(result["quantity"], 1)
        self.assertEqual(list_items(self.player), [])

    def test_planner_raises_equipped_removal_error(self):
        from world.rules.equipment import (
            EquippedRemovalError,
            equipped_removal_conflict,
            plan_inventory_delta,
        )

        self.player.db.inventory = ["plain_sword"]
        self.player.db.equipment = {**self.EMPTY_EQUIPMENT, "weapon_main": "plain_sword"}
        self.assertEqual(
            equipped_removal_conflict(self.player, ("plain_sword",)), "plain_sword"
        )
        self.assertIsNone(equipped_removal_conflict(self.player, ("meal",)))
        with self.assertRaises(EquippedRemovalError):
            plan_inventory_delta(self.player, removals=("plain_sword",))
        # Malformed storage protects every removal of a registry equipment key.
        self.player.db.equipment = "corrupt"
        self.assertEqual(
            equipped_removal_conflict(self.player, ("plain_sword",)), "plain_sword"
        )
        self.assertIsNone(equipped_removal_conflict(self.player, ("meal",)))

    def test_drop_and_give_refuse_the_last_equipped_key(self):
        self.char2.location = self.store
        self.player.db.inventory = ["plain_sword"]
        self.player.db.equipment = {**self.EMPTY_EQUIPMENT, "weapon_main": "plain_sword"}
        self.call(
            CmdDrop(),
            "plain_sword",
            "你無法丟下已裝備的物品。",
            caller=self.player,
        )
        self.assertEqual(list_items(self.player), ["plain_sword"])
        self.call(
            CmdGive(),
            f"plain_sword = {self.char2.key}",
            "你無法給予已裝備的物品。",
            caller=self.player,
        )
        self.assertEqual(list_items(self.player), ["plain_sword"])

class MerchantStockParsingTests(ShopRegistryIsolation, EvenniaTestCase):
    @covers_requirement("shop-economy::merchant-stock-is-finite-persistent-repeated-item-quantity-state")
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
