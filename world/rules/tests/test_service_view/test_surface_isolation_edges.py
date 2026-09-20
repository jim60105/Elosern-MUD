"""Slice of ``test_service_view``: SurfaceIsolationTests, MeritAndRankEdgeTests, GuildCorruptionEdgeTests, ShopEdgeTests.
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
    FakeAttributes,
    FakeComponents,
    FakeHost,
    FakeRoom,
    ServiceRegistryIsolation,
    TICK_NIGHT,
    TICK_NOON,
    T_APPLE,
    T_FANG,
    T_KNIFE,
    T_PASS,
    T_SPRAY,
    actor,
    guild_examiner,
    guild_staff,
    merchant,
    quest_record,
    registration,
)


class SurfaceIsolationTests(ServiceRegistryIsolation):
    def test_corrupt_quest_log_degrades_only_the_guild_surface(self):
        room = FakeRoom(
            FakeHost("g", 1, guild_staff(), location=None),
            FakeHost("m", 2, merchant(), location=None),
        )
        player = actor(
            location=room,
            wallet=1000,
            registration=registration(),
            quest_log=[{"quest_id": "broken", "definition_key": "nope"}],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.guild)
        self.assertEqual(view.guild_unavailable_reason, "malformed_quest_log")
        self.assertIsNotNone(view.shop)
        self.assertIsNotNone(view.inventory)
        self.assertEqual(view.pagination.board_total, 0)
        self.assertEqual(view.pagination.stock_total, 3)

    def test_malformed_merchant_stock_degrades_only_the_shop_surface(self):
        room = FakeRoom(
            FakeHost("g", 1, guild_staff(), location=None),
            FakeHost("m", 2, merchant(merchant_stock={"nope": 5}), location=None),
        )
        player = actor(
            location=room,
            wallet=1000,
            registration=registration(),
            quest_log=[quest_record()],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.shop)
        self.assertEqual(view.shop_unavailable_reason, "malformed_stock")
        self.assertIsNotNone(view.guild)
        self.assertIsNotNone(view.inventory)

    def test_corrupt_registration_degrades_the_guild_surface(self):
        room = FakeRoom(FakeHost("g", 1, guild_staff(), location=None))
        player = actor(
            location=room,
            wallet=1000,
            registration=registration(displayed_stats={"hp": 0}),
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.guild)
        self.assertEqual(view.guild_unavailable_reason, "guild_data_error")
        self.assertFalse(view.player.guild_registered)

    def test_pagination_totals_match_shipped_rows_and_null_surfaces(self):
        room = FakeRoom(
            FakeHost("g", 1, guild_staff(), location=None),
            FakeHost("m", 2, merchant(), location=None),
        )
        player = actor(
            location=room,
            wallet=1000,
            registration=registration(),
            guild_rank="F",
            quest_log=[quest_record()],
            inventory=[T_APPLE, T_APPLE],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertEqual(view.pagination.board_total, 1)
        self.assertEqual(view.pagination.quest_total, 1)
        self.assertEqual(view.pagination.stock_total, 3)
        self.assertEqual(view.pagination.sellable_total, 1)
        self.assertEqual(view.pagination.inventory_total, 1)


class MeritAndRankEdgeTests(ServiceRegistryIsolation):
    def test_missing_trait_storage_fails_the_whole_panel(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=5)
        player.attributes = FakeAttributes(traits=None)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            with self.assertRaises(ServicesViewError):
                build_services_view(player)

    def test_malformed_guild_merit_fails_the_whole_panel(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=5)
        player.attributes = FakeAttributes(
            traits={"guild_merit": {"base": -3, "current": -3}}
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            with self.assertRaises(ServicesViewError):
                build_services_view(player)

    def test_non_mapping_guild_merit_fails_the_whole_panel(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=5)
        player.attributes = FakeAttributes(traits={"guild_merit": "broken"})
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            with self.assertRaises(ServicesViewError):
                build_services_view(player)

    def test_malformed_guild_rank_fails_the_whole_panel(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=5, registration=registration(), guild_rank="Z")
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            with self.assertRaises(ServicesViewError):
                build_services_view(player)

    def test_top_rank_exam_start_reports_settled(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), guild_examiner(), location=None))
        player = actor(location=room, wallet=5, registration=registration(), guild_rank="S", merit=999999)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        rank = view.guild.rank
        self.assertFalse(rank.eligible)
        self.assertIsNone(rank.next_rank)
        self.assertEqual(rank.exam_start.reason_code, "already_settled")

    def test_active_session_blanks_remote_surfaces(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), guild_examiner(), location=None))
        player = actor(location=room, wallet=5, registration=registration(), guild_rank="F", merit=50)
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
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.guild)
        self.assertIsNone(view.shop)
        self.assertIsNone(view.host)
        self.assertIsNotNone(view.player)
        self.assertIsNotNone(view.inventory)


class GuildCorruptionEdgeTests(ServiceRegistryIsolation):
    def test_corrupt_registration_makes_guild_surface_unavailable(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(
            location=room,
            wallet=5,
            registration=registration(displayed_stats={"hp": 0}),
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.guild)
        self.assertEqual(view.guild_unavailable_reason, "guild_data_error")

    def test_malformed_reward_claims_degrades_the_guild_surface(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(
            location=room,
            wallet=5,
            registration=registration(),
            guild_rank="F",
            quest_log=[quest_record()],
            claims="not-a-list",
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.guild)
        self.assertEqual(view.guild_unavailable_reason, "malformed_quest_log")

    def test_unregistered_quest_rows_render_without_reward_section(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(
            location=room,
            wallet=5,
            quest_log=[quest_record()],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        # An unregistered actor sees a guild surface with no board and the
        # quest row rendering without the reward line.
        self.assertEqual(view.guild.board, ())
        row = view.guild.quests[0]
        self.assertNotIn("獎勵：", row.detail)


class ShopEdgeTests(ServiceRegistryIsolation):
    def test_merchant_host_without_component_closes_shop(self):
        room = FakeRoom(FakeHost("m", 1, location=None))
        player = actor(location=room, wallet=5)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.shop)
        self.assertEqual(view.shop_unavailable_reason, "no_local_service_host")

    def test_merchant_component_missing_closes_shop(self):
        # A host whose component lookup returns None even though its name is
        # advertised is treated as no merchant.
        class BrokenComponents(FakeComponents):
            def has(self, name):
                return name == Merchant.name

            def get(self, slot):
                return None

        room = FakeRoom(FakeHost("m", 1, location=None))
        room.contents[0].components = BrokenComponents()
        player = actor(location=room, wallet=5)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.shop)
        self.assertEqual(view.shop_unavailable_reason, "no_merchant")

    def test_unknown_shop_key_closes_shop(self):
        room = FakeRoom(FakeHost("m", 1, merchant(shop_key="unknown_shop"), location=None))
        player = actor(location=room, wallet=5)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.shop)
        self.assertEqual(view.shop_unavailable_reason, "unknown_shop")

    def test_sellable_excludes_unsellable_and_unoffered_items(self):
        room = FakeRoom(
            FakeHost(
                "m",
                1,
                merchant(merchant_stock={T_APPLE: 10, T_SPRAY: 3, T_FANG: 1}),
                location=None,
            )
        )
        # T_APPLE/T_SPRAY are sellable and offered; T_PASS is a held registry
        # item that is unsellable; a made-up key is neither.
        player = actor(
            location=room,
            wallet=5,
            inventory=[
                T_APPLE,
                T_SPRAY,
                T_PASS,
                "made_up_item",
                "made_up_item",
            ],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        keys = {row.item_key for row in view.shop.sellable}
        self.assertEqual(keys, {T_APPLE, T_SPRAY})
        self.assertNotIn("made_up_item", keys)
        self.assertNotIn(T_PASS, keys)

    def test_closed_sell_and_insufficient_items_reasons(self):
        room = FakeRoom(
            FakeHost(
                "m",
                1,
                merchant(merchant_stock={T_APPLE: 10, T_SPRAY: 3, T_FANG: 1}),
                location=None,
            )
        )
        player = actor(location=room, wallet=5, inventory=[T_APPLE])
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NIGHT),
        ):
            view = build_services_view(player)
        sellable = {row.item_key: row for row in view.shop.sellable}
        self.assertEqual(sellable[T_APPLE].sell.reason_code, "closed")

        open_room = FakeRoom(
            FakeHost(
                "m",
                1,
                merchant(merchant_stock={T_APPLE: 10, T_SPRAY: 3, T_FANG: 1}),
                location=None,
            )
        )
        player2 = actor(location=open_room, wallet=5, inventory=[T_FANG, T_FANG, T_FANG])
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player2)
        # The fang rule caps stock at 3 with 1 left; held 3 sells are capped at
        # 2 before overflow, so the enabled sell advertises min(held, cap)=2.
        sellable = {row.item_key: row for row in view.shop.sellable}
        self.assertTrue(sellable[T_FANG].sell.enabled)
        self.assertEqual(sellable[T_FANG].sell.quantity_max, 2)

    def test_malformed_equipment_degrades_inventory(self):
        room = FakeRoom()
        player = actor(location=room, wallet=5, inventory=[T_APPLE], equipment="corrupt")
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.inventory)
        self.assertEqual(view.inventory_unavailable_reason, "malformed_equipment")

    def test_accessories_not_a_list_fails_closed_unavailable(self):
        # The services rows normalize through the shared fail-closed
        # equipment layer (add-inventory-item-actions rubber-duck fix): a
        # malformed accessories value is never partially trusted — the
        # inventory section is unavailable, not partially equipped.
        room = FakeRoom()
        player = actor(
            location=room,
            wallet=5,
            inventory=[T_KNIFE],
            equipment={
                "weapon_main": T_KNIFE,
                "weapon_off": None,
                "armor": None,
                "accessories": "corrupt",
            },
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.inventory)
        self.assertEqual(view.inventory_unavailable_reason, "malformed_equipment")

    def test_cross_slot_duplicate_fails_closed_unavailable(self):
        # One key stored in two slots is malformed for the shared equipment
        # layer, so the panel never publishes a partial equipped truth.
        room = FakeRoom()
        player = actor(
            location=room,
            wallet=5,
            inventory=[T_KNIFE],
            equipment={
                "weapon_main": T_KNIFE,
                "weapon_off": None,
                "armor": None,
                "accessories": [T_KNIFE],
            },
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.inventory)
        self.assertEqual(view.inventory_unavailable_reason, "malformed_equipment")
