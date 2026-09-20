"""Slice of ``test_service_view``: ShopTests, InventoryTests, InventoryRowActionTests.
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
        self.assertEqual(rows[T_APPLE].sell_copper, _sell_copper(T_APPLE))
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
        self.assertEqual(sellable[T_APPLE].sell_copper, _sell_copper(T_APPLE))
        self.assertTrue(sellable[T_APPLE].sell.enabled)
        self.assertEqual(sellable[T_FANG].sell.enabled, True)


class InventoryTests(ServiceRegistryIsolation):
    @covers_requirement("webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory")
    def test_repeated_key_inventory_aggregates_and_marks_equipped(self):
        room = FakeRoom()
        equipment = {
            "weapon_main": T_KNIFE,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        player = actor(
            location=room,
            wallet=42,
            inventory=[T_SPRAY, T_APPLE, T_KNIFE, T_SPRAY],
            equipment=equipment,
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        rows = {row.item_key: row for row in view.inventory.rows}
        self.assertEqual(rows[T_SPRAY].held, 2)
        self.assertEqual(rows[T_SPRAY].equipped, False)
        self.assertEqual(rows[T_APPLE].held, 1)
        self.assertEqual(rows[T_KNIFE].equipped, True)
        self.assertEqual(view.inventory.wallet, 42)
        self.assertEqual(view.player.wallet, 42)

    @covers_requirement("webclient-service-menus::the-shop-surface-covers-stock-quantity-buy-sell-and-sellable-inventory")
    def test_registered_inventory_key_projects_registry_presentation(self):
        room = FakeRoom()
        player = actor(
            location=room,
            wallet=42,
            inventory=[T_SPRAY, T_SPRAY, "mystery_relic"],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        rows = {row.item_key: row for row in view.inventory.rows}
        self.assertEqual(
            rows[T_SPRAY].presentation,
            live_item_registry()[T_SPRAY].presentation,
        )
        self.assertEqual(rows[T_SPRAY].held, 2)
        self.assertIsNone(rows["mystery_relic"].presentation)
        self.assertEqual(rows["mystery_relic"].display_name, "mystery_relic")


class InventoryRowActionTests(ServiceRegistryIsolation):
    """Personal-item descriptors derived by the shared preflight APIs."""

    def _build(self, player):
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            return build_services_view(player)

    def _rows(self, view):
        return {row.item_key: row for row in view.inventory.rows}

    def test_injured_usable_row_carries_enabled_use_descriptor(self):
        player = actor(
            location=FakeRoom(),
            inventory=[T_SPRAY],
            hp_current=50,
        )
        row = self._rows(self._build(player))[T_SPRAY]
        self.assertIsNotNone(row.action)
        self.assertEqual(row.action.action_id, "inventory.use")
        self.assertEqual(row.action.label, "使用")
        self.assertTrue(row.action.enabled)
        self.assertIsNone(row.action.reason_code)

    def test_full_hp_use_disabled_with_stable_reason(self):
        player = actor(
            location=FakeRoom(),
            inventory=[T_SPRAY],
            hp_current=100,
        )
        row = self._rows(self._build(player))[T_SPRAY]
        self.assertFalse(row.action.enabled)
        self.assertEqual(row.action.reason_code, "hp_full")
        self.assertEqual(
            row.action.reason_message,
            "你的體力已經全滿。",
        )

    def test_single_scope_row_disabled_with_no_target_reason(self):
        # add-item-effect-targeting 6.3: the descriptor preflight builds the
        # RoomActionContext explicitly, so a single-scope item's row carries
        # the stable no-target reason instead of appearing enabled with a
        # target the webclient never supplied.
        from world.rules.item_effects import (
            GaugeAdjustEffect,
            ItemEffectProfile,
            ItemStat,
            ItemTargetScope,
        )

        live_item_effect_profiles()[T_SPRAY] = ItemEffectProfile(
            effects=(
                GaugeAdjustEffect(
                    stat=ItemStat.HP, amount=40, scope=ItemTargetScope.SINGLE
                ),
            )
        )
        player = actor(
            location=FakeRoom(),
            inventory=[T_SPRAY],
            hp_current=50,
        )
        row = self._rows(self._build(player))[T_SPRAY]
        self.assertIsNotNone(row.action)
        self.assertFalse(row.action.enabled)
        self.assertEqual(row.action.reason_code, "no_target")

    def test_unknown_and_inspect_only_rows_have_null_actions(self):
        player = actor(
            location=FakeRoom(),
            inventory=["mystery_relic", T_APPLE],
            hp_current=50,
        )
        rows = self._rows(self._build(player))
        self.assertIsNone(rows["mystery_relic"].action)
        self.assertIsNone(rows["mystery_relic"].presentation)
        self.assertIsNone(rows[T_APPLE].action)
        self.assertIsNotNone(rows[T_APPLE].presentation)

    def test_equipment_toggle_descriptor_tracks_equipped_state(self):
        equipment = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        player = actor(
            location=FakeRoom(),
            inventory=[T_KNIFE],
            equipment=dict(equipment),
            hp_current=100,
        )
        row = self._rows(self._build(player))[T_KNIFE]
        self.assertEqual(row.action.action_id, "inventory.toggle_equip")
        self.assertEqual(row.action.label, "裝備")
        self.assertTrue(row.action.enabled)

        player.db.equipment = {**equipment, "weapon_main": T_KNIFE}
        row = self._rows(self._build(player))[T_KNIFE]
        self.assertTrue(row.equipped)
        self.assertEqual(row.action.label, "卸下")
        self.assertTrue(row.action.enabled)

    def test_sixth_accessory_disabled_and_equipped_rows_stay_enabled(self):
        from world.skills.equipment import EquipmentSlot

        registry = live_item_registry()
        for index in range(6):
            registry[f"ring_{index}"] = ItemDefinition(
                key=f"ring_{index}",
                display_name_zh="測試戒指",
                price_table_key="ring_0",
                sellable=False,
                presentation=ItemPresentation(
                    kind=ItemKind.ACCESSORY,
                    icon_key=ItemIconKey.ACCESSORY,
                    rarity=ItemRarity.COMMON,
                    summary_zh="測試用的飾品。",
                ),
                equipment_slot=EquipmentSlot.ACCESSORY,
                modifier_key=EquipmentModifierKey.PROTECTIVE_RING,
            )
        player = actor(
            location=FakeRoom(),
            inventory=[f"ring_{index}" for index in range(6)],
            equipment={
                "weapon_main": None,
                "weapon_off": None,
                "armor": None,
                "accessories": [f"ring_{index}" for index in range(5)],
            },
            hp_current=100,
        )
        rows = self._rows(self._build(player))
        for index in range(5):
            row = rows[f"ring_{index}"]
            self.assertTrue(row.equipped)
            self.assertTrue(row.action.enabled)
            self.assertEqual(row.action.label, "卸下")
        overflow = rows["ring_5"]
        self.assertFalse(overflow.action.enabled)
        self.assertEqual(overflow.action.reason_code, "accessory_slots_full")
        self.assertIn("飾品欄", overflow.action.reason_message)

    def test_combat_view_keeps_personal_use_descriptor_available(self):
        player = actor(
            location=FakeRoom(),
            inventory=[T_SPRAY],
            hp_current=50,
        )
        player.db.active_combat = {
            "session_id": "hostile:1:0",
            "mode": "hostile",
            "room_id": 1,
            "player_ids": [1],
            "enemy_ids": [2],
            "fled_ids": [],
            "knocked_out_ids": [],
            "rounds_elapsed": 0,
            "exam_id": None,
        }
        view = self._build(player)
        self.assertIsNone(view.guild)
        row = self._rows(view)[T_SPRAY]
        self.assertTrue(row.action.enabled)

    def test_descriptor_derivation_mutates_nothing(self):
        from copy import deepcopy

        player = actor(
            location=FakeRoom(),
            inventory=[T_SPRAY, T_KNIFE, "mystery_relic"],
            equipment={
                "weapon_main": T_KNIFE,
                "weapon_off": None,
                "armor": None,
                "accessories": [],
            },
            hp_current=50,
        )
        before_db = deepcopy(vars(player.db))
        before_traits = deepcopy(player.attributes._store)
        self._build(player)
        self.assertEqual(vars(player.db), before_db)
        self.assertEqual(player.attributes._store, before_traits)
