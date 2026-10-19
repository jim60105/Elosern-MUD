"""Slice of ``test_service_view``: ShopTests over fake hosts and members.

The viewed-member facts, the party boundary and the trade-rule parity run on
real objects in ``test_viewed_member_shop``; here the boundary verdict is
admitted so the merchant gates alone are exercised.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from tools.spec_traceability import covers_requirement
from typeclasses.components import GuildExaminer, GuildStaff, Merchant
from world.lore.items import (
    EquipmentModifierKey,
    ItemDefinition,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
)
from world.quests.catalog import register_catalog
from world.quests.definitions import (
    QUEST_DEFINITION_REGISTRY,
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    register_quest_definition,
)
from world.quests.runtime import QuestRecord, QuestState, to_storage
from world.quests.tests._fixtures import TEST_ISSUER_KEY, register_catalog_once
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    register_guild_offer,
)
from world.rules.tests._combat_session_helpers import (
    live_item_effect_profiles,
    open_synthetic_scope,
)
from world.rules.tests._guild_service_probes import (
    a_live_monster_tier_key,
    install_synthetic_catalog,
    live_item_registry,
    live_monster_tier_keys,
    price_band,
    rank_reward_band,
    synth_catalog,
    synth_offer_rule,
    synth_shop_config,
    synthetic_branch_key,
)
from world.tests.synthetic_data import (
    SYNTH_ITEMS,
    SYNTH_SHOPS,
)
from world.rules.service_view import (
    ACTION_ACCEPT,
    ACTION_BUY,
    ACTION_REGISTER,
    ACTION_SELL,
    ServicesViewError,
    build_services_view,
)


from ._support import (
    FakeHost,
    FakeRoom,
    ServiceRegistryIsolation,
    TICK_NIGHT,
    TICK_NOON,
    T_APPLE,
    T_FANG,
    T_KNIFE,
    T_SPRAY,
    _buy_copper,
    _sell_copper,
    actor,
    merchant,
)


class ShopTests(ServiceRegistryIsolation):
    def _shop_room(self):
        store = FakeHost("合成行商", 1, merchant(), location=None)
        room = FakeRoom(store)
        store.location = room
        return room

    @covers_requirement("webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory")
    def test_open_shop_reports_exact_integer_copper_and_stock(self):
        room = self._shop_room()
        player = actor(location=room, wallet=1000)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        shop = view.shop
        self.assertTrue(shop.open)
        rows = {row.item_key: row for row in shop.stock}
        self.assertEqual(rows[T_APPLE].buy_copper, _buy_copper(T_APPLE))
        self.assertFalse(hasattr(rows[T_APPLE], "sell_copper"))
        self.assertEqual(view.shop.member_id, player.pk)
        self.assertEqual(rows[T_APPLE].stock, 20)
        self.assertEqual(rows[T_APPLE].max_stock, 20)
        self.assertEqual(rows[T_SPRAY].stock, 3)
        self.assertTrue(rows[T_APPLE].buy.enabled)

    def test_closed_shop_disables_purchases_but_renders_stock(self):
        room = self._shop_room()
        player = actor(location=room, wallet=1000)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NIGHT),
        ):
            view = build_services_view(player)
        shop = view.shop
        self.assertFalse(shop.open)
        self.assertEqual(len(shop.stock), 3)
        for row in shop.stock:
            self.assertFalse(row.buy.enabled)
            self.assertEqual(row.buy.reason_code, "closed")

    def test_quantity_descriptor_advertises_bounded_maximum(self):
        room = self._shop_room()
        player = actor(location=room, wallet=1000)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        rows = {row.item_key: row for row in view.shop.stock}
        quantity_min = rows[T_SPRAY].buy.quantity_min
        quantity_max = rows[T_SPRAY].buy.quantity_max
        self.assertEqual(quantity_min, 1)
        self.assertLessEqual(quantity_max, 3)
        self.assertLessEqual(quantity_max, 1000)

    def test_insufficient_funds_disables_buy(self):
        room = self._shop_room()
        player = actor(location=room, wallet=5)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        rows = {row.item_key: row for row in view.shop.stock}
        self.assertFalse(rows[T_SPRAY].buy.enabled)
        self.assertEqual(rows[T_SPRAY].buy.reason_code, "insufficient_funds")

    def test_sellable_rows_aggregate_held_items(self):
        room = FakeRoom(
            FakeHost(
                "合成行商",
                1,
                merchant(merchant_stock={T_APPLE: 10, T_SPRAY: 3, T_FANG: 1}),
                location=None,
            )
        )
        player = actor(location=room, wallet=1000, inventory=[T_APPLE, T_APPLE, T_FANG])
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        sellable = {row.item_key: row for row in view.shop.sellable}
        self.assertEqual(sellable[T_APPLE].held, 2)
        self.assertEqual(
            sellable[T_APPLE].presentation,
            live_item_registry()[T_APPLE].presentation,
        )
        self.assertEqual(sellable[T_APPLE].sell_copper, _sell_copper(T_APPLE))
        self.assertTrue(sellable[T_APPLE].sell.enabled)
        self.assertEqual(sellable[T_FANG].sell.enabled, True)


    def test_stock_rows_report_held_and_no_delta_for_non_equipment(self):
        room = self._shop_room()
        player = actor(location=room, wallet=1000, inventory=[T_SPRAY, T_SPRAY])
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        rows = {row.item_key: row for row in view.shop.stock}
        self.assertEqual(rows[T_SPRAY].viewed.held, 2)
        self.assertEqual(rows[T_APPLE].viewed.held, 0)
        self.assertEqual(
            rows[T_SPRAY].presentation, live_item_registry()[T_SPRAY].presentation
        )
        for row in view.shop.stock:
            if live_item_registry()[row.item_key].equipment_slot is None:
                self.assertIsNone(row.viewed.delta)

    def test_malformed_member_inventory_degrades_only_the_shop(self):
        room = self._shop_room()
        player = actor(location=room, wallet=1000)
        player.db.inventory = "not a list"
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.shop)
        self.assertEqual(view.shop_unavailable_reason, "malformed_inventory")
        self.assertEqual(view.pagination.stock_total, 0)
