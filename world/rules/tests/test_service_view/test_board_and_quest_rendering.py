"""Slice of ``test_service_view``: BoardFilteringTests, QuestRenderingTests.
"""
import unittest
from dataclasses import replace
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
    SYNTH_MONSTER_SPECIES,
    SYNTH_MONSTER_VARIANTS,
    SYNTH_REGIONS,
    SYNTH_SHOPS,
    synthetic_registries,
)
from world.quests.describe import describe_objective
from world.lore.guild import GUILD_BRANCH_REGISTRY, GUILD_RANK_REGISTRY
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
    def test_board_discloses_nullable_prose_and_item_reward(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, registration=registration(), guild_rank="F")
        with patch("world.rules.service_view.read_world_clock", return_value=SimpleNamespace(tick=TICK_NOON)):
            guild = build_services_view(player).guild
        row = guild.board[0]
        self.assertEqual(row.category, QuestType.DEFEAT)
        self.assertIsNone(row.objective_note)
        self.assertIsNone(row.deadline_line)
        self.assertIsNone(row.rationale)
        self.assertIsNone(row.flavor)
        self.assertEqual(row.reward, {
            "copper": self.board_reward.copper,
            "merit": 25,
            "items": [{
                "item_key": SYNTH_ITEMS["t_ember_spray"].key,
                "display_name": SYNTH_ITEMS["t_ember_spray"].display_name_zh,
                "quantity": 2,
            }],
        })
        self.assertEqual(guild.branch_label, GUILD_BRANCH_REGISTRY[BRANCH].display_name_zh)
        self.assertEqual(guild.rank_ladder, tuple(
            rank.key for rank in sorted(GUILD_RANK_REGISTRY.values(), key=lambda rank: rank.order)
        ))

    def test_species_hunt_splits_note_and_discloses_authored_deadline_and_prose(self):
        with synthetic_registries("regions", "monster_species", "monster_variants"):
            species = next(iter(SYNTH_MONSTER_SPECIES))
            variants = tuple(key for key, variant in SYNTH_MONSTER_VARIANTS.items() if variant.species_key == species)
            objective = QuestObjective(
                kind=ObjectiveKind.DEFEAT, quantity=2,
                region_key=next(iter(SYNTH_REGIONS)), species_key=species,
                countable_variant_keys=variants,
            )
            definition = replace(
                QUEST_DEFINITION_REGISTRY[BOARD_QUEST],
                stages=(QuestStage(index=0, objective=objective),),
                deadline_hours=72,
                rating_rationale_zh="合成評價理由。",
                background_flavor_zh="合成委託背景。",
            )
            with patch.dict(QUEST_DEFINITION_REGISTRY, {BOARD_QUEST: definition}):
                room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
                player = actor(location=room, registration=registration(), guild_rank="F")
                with patch("world.rules.service_view.read_world_clock", return_value=SimpleNamespace(tick=TICK_NOON)):
                    row = build_services_view(player).guild.board[0]
            self.assertTrue(row.objective_note)
            self.assertEqual(f"{row.objective_summary}（{row.objective_note}）", describe_objective(objective))
            self.assertEqual(row.deadline_line, "接取後 3 日")
            self.assertEqual(row.rationale, definition.rating_rationale_zh)
            self.assertEqual(row.flavor, definition.background_flavor_zh)

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

    def _rank(self, *hosts, **actor_fields):
        room = FakeRoom(*hosts)
        player = actor(location=room, **actor_fields)
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            return build_services_view(player).guild.rank

    @covers_requirement("webclient-service-menus::the-guild-surface-covers-registration-board-quest-log-and-rank-examination")
    def test_exam_eligibility_shows_exact_next_rank_only(self):
        rank = self._rank(
            FakeHost("a", 1, guild_staff(), guild_examiner()),
            registration=registration(), guild_rank="F", merit=50,
        )
        self.assertIsNotNone(rank)
        self.assertEqual(rank.rank, "F")
        self.assertEqual(rank.next_rank, "E")
        self.assertEqual(rank.next_threshold, 50)
        self.assertTrue(rank.merit_qualified)
        self.assertTrue(rank.exam_request.enabled)
        self.assertEqual(rank.exam_request.action_id, "guild.exam_request")
        self.assertEqual(rank.exam_request.label, "預約升等考核")

    @covers_requirement("webclient-service-menus::the-guild-surface-covers-registration-board-quest-log-and-rank-examination")
    def test_below_merit_request_stays_enabled(self):
        # Merit qualification and request availability are distinct facts:
        # below threshold the request still reaches the counter.
        rank = self._rank(
            FakeHost("a", 1, guild_staff(), guild_examiner()),
            registration=registration(), guild_rank="F", merit=49,
        )
        self.assertFalse(rank.merit_qualified)
        self.assertTrue(rank.exam_request.enabled)
        self.assertIsNone(rank.exam_request.reason_code)

    @covers_requirement("webclient-service-menus::the-guild-surface-covers-registration-board-quest-log-and-rank-examination")
    def test_exam_request_disables_only_for_target_and_counter_gates(self):
        unregistered = self._rank(
            FakeHost("a", 1, guild_staff(), guild_examiner()), guild_rank=None, merit=999,
        )
        self.assertEqual(
            (unregistered.merit_qualified, unregistered.exam_request.enabled,
             unregistered.exam_request.reason_code),
            (False, False, "unregistered"),
        )
        wrong_branch = self._rank(
            FakeHost("a", 1, guild_staff(), guild_examiner(branch_key="t_other_branch")),
            registration=registration(), guild_rank="F", merit=999,
        )
        self.assertEqual(
            (wrong_branch.merit_qualified, wrong_branch.exam_request.reason_code),
            (True, "wrong_branch"),
        )
        busy = FakeHost("a", 1, guild_staff(), guild_examiner())
        busy.db = SimpleNamespace(schedule_state="busy")
        blocked = self._rank(busy, registration=registration(), guild_rank="F", merit=999)
        self.assertEqual(
            (blocked.merit_qualified, blocked.exam_request.enabled, blocked.exam_request.reason_code),
            (True, False, "schedule_blocked"),
        )
        malformed = FakeHost("a", 1, guild_staff(), guild_examiner(service_binding="portable"))
        malformed.ndb = SimpleNamespace()
        with patch("world.rules.service_gate.log_warn"):
            off_anchor = self._rank(
                malformed, registration=registration(), guild_rank="F", merit=0,
            )
        self.assertEqual(off_anchor.exam_request.reason_code, "service_unavailable")

    def test_rank_surface_absent_without_examiner(self):
        room = FakeRoom(FakeHost("a", 1, guild_staff(), location=None))
        player = actor(location=room, registration=registration(), guild_rank="F")
        with patch(
            "world.rules.service_view.read_world_clock",
            return_value=SimpleNamespace(tick=TICK_NOON),
        ):
            view = build_services_view(player)
        self.assertIsNone(view.guild.rank)
