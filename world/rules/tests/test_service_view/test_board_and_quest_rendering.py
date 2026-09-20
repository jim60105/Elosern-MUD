"""Slice of ``test_service_view``: BoardFilteringTests, QuestRenderingTests.
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
    BOARD_QUEST,
    BOARD_QUEST_DISPLAY,
    BRANCH,
    E_QUEST,
    FakeHost,
    FakeRoom,
    ServiceRegistryIsolation,
    TICK_NOON,
    actor,
    guild_examiner,
    guild_staff,
    quest_record,
    registration,
)


class BoardFilteringTests(ServiceRegistryIsolation):
    def _register_e_quest(self):
        definition = QuestDefinition(
            key=E_QUEST,
            display_name="測試E級任務",
            quest_type=QuestType.DEFEAT,
            rank="E",
            stages=(
                QuestStage(
                    index=0,
                    objective=QuestObjective(
                        kind=ObjectiveKind.DEFEAT,
                        quantity=1,
                        monster_tier=a_live_monster_tier_key(),
                    ),
                ),
            ),
            deadline_hours=None,
        )
        register_quest_definition(definition)
        register_guild_offer(
            GuildQuestOffer(
                definition_key=E_QUEST,
                issuer_branch_key=BRANCH,
                reward=QuestReward(
                    copper=rank_reward_band("E")[0], items=(), merit=50
                ),
            )
        )

    @covers_requirement("webclient-service-menus::the-guild-surface-covers-registration-board-quest-log-and-rank-examination")
    def test_f_member_sees_only_rank_eligible_board_offers(self):
        self._register_e_quest()
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, registration=registration(), guild_rank="F")
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        keys = [row.definition_key for row in view.guild.board]
        self.assertEqual(keys, [BOARD_QUEST])

    def test_e_member_sees_both_offers_in_rank_key_order(self):
        self._register_e_quest()
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, registration=registration(), guild_rank="E")
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        keys = [row.definition_key for row in view.guild.board]
        self.assertEqual(keys, [BOARD_QUEST, E_QUEST])
        accept = view.guild.board[0].accept
        self.assertEqual(accept.action_id, ACTION_ACCEPT)
        self.assertTrue(accept.enabled)

    def test_active_record_disables_its_board_accept(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(
            location=room,
            registration=registration(),
            guild_rank="F",
            quest_log=[quest_record()],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        accept = view.guild.board[0].accept
        self.assertFalse(accept.enabled)
        self.assertEqual(accept.reason_code, "quest_already_active")


class QuestRenderingTests(ServiceRegistryIsolation):
    @covers_requirement("webclient-service-menus::the-guild-surface-covers-registration-board-quest-log-and-rank-examination")
    def test_quest_row_carries_full_server_rendered_detail(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(
            location=room,
            registration=registration(),
            guild_rank="F",
            quest_log=[quest_record()],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        row = view.guild.quests[0]
        self.assertEqual(row.quest_id, f"{BOARD_QUEST}:1")
        self.assertEqual(row.state, "in_progress")
        self.assertEqual(row.stage_index, 0)
        self.assertEqual(row.stage_progress, 0)
        self.assertTrue(row.objective_summary)
        self.assertIsNone(row.deadline_line)
        self.assertTrue(row.detail.startswith(f"{BOARD_QUEST_DISPLAY}\n狀態："))
        self.assertIn("目標：討伐 2 隻", row.detail)
        self.assertIn(
            "獎勵：銅 "
            f"{self.board_reward.copper}、功績 {self.board_reward.merit}、"
            f"{SYNTH_ITEMS['t_ember_spray'].display_name_zh} × 2",
            row.detail,
        )
        self.assertTrue(row.abandon.enabled)
        self.assertFalse(row.turnin.enabled)

    def test_completed_quest_enables_turnin_until_claimed(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        completed = quest_record(state=QuestState.COMPLETED, progress=1)
        player = actor(
            location=room,
            registration=registration(),
            guild_rank="F",
            quest_log=[completed],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        row = view.guild.quests[0]
        self.assertFalse(row.abandon.enabled)
        self.assertTrue(row.turnin.enabled)

        claimed = actor(
            location=room,
            registration=registration(),
            guild_rank="F",
            quest_log=[completed],
            claims=[f"{BOARD_QUEST}:1"],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(claimed)
        row = view.guild.quests[0]
        self.assertFalse(row.turnin.enabled)
        self.assertEqual(row.turnin.reason_code, "already_claimed")

    def test_deadline_line_renders_when_set(self):
        record = QuestRecord(
            quest_id="deadline:1",
            definition_key=BOARD_QUEST,
            issuer_key=TEST_ISSUER_KEY,
            state=QuestState.IN_PROGRESS,
            stage_index=0,
            stage_progress=0,
            deadline_tick=TICK_NOON + 3 * 3600,
            accepted_tick=0,
            stage_room_id=None,
            objective_target_ids=(),
            protected_entity_ids=(),
            failure_reason=None,
        )
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(
            location=room,
            registration=registration(),
            guild_rank="F",
            quest_log=[to_storage(record)],
        )
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertEqual(view.guild.quests[0].deadline_line, "期限：剩餘 3 小時")

    def test_exam_eligibility_shows_exact_next_rank_only(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), guild_examiner(), location=None))
        player = actor(location=room, registration=registration(), guild_rank="F", merit=50)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        rank = view.guild.rank
        self.assertIsNotNone(rank)
        self.assertEqual(rank.rank, "F")
        self.assertEqual(rank.next_rank, "E")
        self.assertEqual(rank.next_threshold, 50)
        self.assertTrue(rank.eligible)
        self.assertTrue(rank.exam_start.enabled)

    def test_exam_start_disabled_below_threshold(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), guild_examiner(), location=None))
        player = actor(location=room, registration=registration(), guild_rank="F", merit=49)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        rank = view.guild.rank
        self.assertFalse(rank.eligible)
        self.assertFalse(rank.exam_start.enabled)
        self.assertEqual(rank.exam_start.reason_code, "below_threshold")

    def test_rank_surface_absent_without_examiner(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, registration=registration(), guild_rank="F")
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.guild.rank)
