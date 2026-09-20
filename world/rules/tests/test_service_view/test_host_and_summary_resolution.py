"""Slice of ``test_service_view``: HostResolutionTests, PlayerSummaryTests.
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
    TICK_NOON,
    actor,
    guild_examiner,
    guild_staff,
    merchant,
    registration,
)


class HostResolutionTests(ServiceRegistryIsolation):
    def _staff_room(self):
        staff = FakeHost("公會長", 10, guild_staff(), guild_examiner(), location=None)
        room = FakeRoom(staff)
        staff.location = room
        return room, staff

    @covers_requirement("webclient-service-menus::service-presentation-resolves-hosts-per-service-class-and-a-stable-player-summary")
    def test_guild_hall_resolves_one_guild_host_and_names_it(self):
        room, staff = self._staff_room()
        self._staff_room()
        player = actor(location=room, registration=registration())
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNotNone(view.host)
        self.assertEqual(view.host.identity, "10")
        self.assertEqual(view.host.display_name, "公會長")
        self.assertIsNotNone(view.guild)
        self.assertIsNotNone(view.guild.rank)
        self.assertIsNone(view.shop)

    def test_general_store_resolves_one_merchant_and_names_it(self):
        store = FakeHost("合成行商", 11, merchant(), location=None)
        room = FakeRoom(store)
        store.location = room
        player = actor(location=room, wallet=1000)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNotNone(view.host)
        self.assertEqual(view.host.identity, "11")
        self.assertIsNone(view.guild)
        self.assertIsNotNone(view.shop)

    @covers_requirement('npc-identity-titles::compact-presentation-rows-keep-the-plain-npc-name')
    def test_titled_host_rows_stay_plain_key(self):
        # npc-title-identity-core compact-row pin: guild and shop host rows
        # render the plain key even when the host entity carries a title.
        staff = FakeHost("公會長", 10, guild_staff(), location=None)
        staff.npc_title = "白銀之手會長"
        staff_room = FakeRoom(staff)
        staff.location = staff_room
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            guild_view = build_services_view(
                actor(location=staff_room, registration=registration())
            )
        self.assertIsNotNone(guild_view.host)
        self.assertEqual(guild_view.host.display_name, "公會長")
        self.assertNotIn("\u3000", guild_view.host.display_name)

        store = FakeHost("合成行商", 11, merchant(), location=None)
        store.npc_title = "南門行商"
        store_room = FakeRoom(store)
        store.location = store_room
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            shop_view = build_services_view(
                actor(location=store_room, wallet=1000)
            )
        self.assertIsNotNone(shop_view.host)
        self.assertEqual(shop_view.host.display_name, "合成行商")
        self.assertNotIn("\u3000", shop_view.host.display_name)

    @covers_requirement("webclient-service-menus::service-presentation-resolves-hosts-per-service-class-and-a-stable-player-summary")
    def test_ambiguous_guild_hosts_close_only_the_guild_surface(self):
        room = FakeRoom(
            FakeHost("a", 1, guild_staff(), location=None),
            FakeHost("b", 2, guild_staff(), location=None),
            FakeHost("shop", 3, merchant(), location=None),
        )
        player = actor(location=room, wallet=1000)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.guild)
        self.assertEqual(view.guild_unavailable_reason, "ambiguous_service_host")
        self.assertIsNotNone(view.shop)

    def test_no_host_closes_only_the_affected_surface(self):
        room = FakeRoom()
        player = actor(location=room, wallet=1000)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.host)
        self.assertIsNone(view.guild)
        self.assertIsNone(view.shop)
        self.assertIsNotNone(view.inventory)
        self.assertEqual(view.guild_unavailable_reason, "no_local_service_host")

    def test_co_located_guild_and_merchant_stay_independent(self):
        guild_host = FakeHost("a", 1, guild_staff(), location=None)
        merchant_host = FakeHost("b", 2, merchant(), location=None)
        room = FakeRoom(guild_host, merchant_host)
        guild_host.location = room
        merchant_host.location = room
        player = actor(location=room, wallet=1000, registration=registration())
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNotNone(view.guild)
        self.assertIsNotNone(view.shop)
        self.assertEqual(view.host.identity, "1")


class PlayerSummaryTests(ServiceRegistryIsolation):
    def test_unregistered_summary_is_honest(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=500)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertFalse(view.player.guild_registered)
        self.assertIsNone(view.player.guild_rank)
        self.assertEqual(view.player.wallet, 500)
        self.assertEqual(view.player.guild_merit, 0)
        self.assertIsNone(view.player.next_rank)
        self.assertIsNone(view.player.next_threshold)
        register = view.guild.registration.register
        self.assertEqual(register.action_id, ACTION_REGISTER)
        self.assertTrue(register.enabled)
        self.assertEqual(view.guild.board, ())

    def test_registered_summary_reports_rank_and_merit(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=500, registration=registration(), merit=60, guild_rank="F")
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertTrue(view.player.guild_registered)
        self.assertEqual(view.player.guild_rank, "F")
        self.assertEqual(view.player.guild_merit, 60)
        self.assertEqual(view.player.next_rank, "E")
        self.assertEqual(view.player.next_threshold, 50)
        self.assertFalse(view.guild.registration.register.enabled)

    def test_top_rank_summary_reports_no_next_rank(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=500, registration=registration(), merit=999999, guild_rank="S")
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.player.next_rank)
        self.assertIsNone(view.player.next_threshold)

    def test_disguised_elf_does_not_distort_the_summary(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=500, registration=registration(), merit=0, guild_rank="F")
        player.db.disguised_stats = {"atk_phys": 60, "magic_power": 30}
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertEqual(view.player.guild_rank, "F")
        self.assertEqual(view.player.guild_merit, 0)
        self.assertEqual(view.player.next_rank, "E")
        self.assertEqual(view.player.next_threshold, 50)

    def test_negative_wallet_fails_the_whole_panel(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=-1)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            with self.assertRaises(ServicesViewError):
                build_services_view(player)

    def test_missing_world_clock_fails_the_whole_panel(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, wallet=500)
        with patch("world.rules.service_view.read_world_clock", return_value=None):
            with self.assertRaises(ServicesViewError):
                build_services_view(player)
