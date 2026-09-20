"""Slice of ``test_titles``: TitleGuildPairingTests."""
from tools.spec_traceability import covers_requirement
import ast
import contextlib
import functools
import inspect
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.titles import (
    FixedTitleDef,
    StarterEpithet,
    TitleCategory,
    TitlePredicate,
    TitlePredicateFamily,
)
from world.rules import titles as titles_module
from world.rules.titles import removal as titles_removal_module
from world.rules.action import (
    CommitFailed,
    PendingEffect,
    _EVENT_EFFECT_PLANNERS,
    _commit,
    ActionRequest,
)
from world.rules.cast_settlement import settle_out_of_combat_cast
from world.rules.clock import CLOCK_YAML, WorldClock, _EVENT_SOURCES
from world.rules.event_log import EventEntry, EventLog, render_plain_text
from world.rules.guild import register_adventurer
from world.rules.titles import (
    DECLINED_LOG_KEY,
    MAX_DECLINE_RECORDS,
    MAX_REMOVAL_RECORDS,
    MAX_TITLE_ENTRIES,
    PENDING_BALLOT_KEY,
    REMOVALS_LOG_KEY,
    TITLE_COLLECTION_KEY,
    TITLE_EQUIPPED_KEY,
    TitleBallotError,
    TitleBallotReason,
    TitleDataError,
    TitleEquipError,
    TitleRemovalError,
    TitleRemovalReason,
    accept_epithet,
    bank_epithet,
    bank_fixed,
    banked_epithets,
    banked_fixed_keys,
    compose_full_title,
    compose_title,
    decline_epithet_ballot,
    decline_records,
    declined_digest,
    equip_epithet,
    equip_fixed,
    epithet_removal_gate,
    fixed_display_name,
    grant_rank_title,
    grant_first_quest_epithet,
    nomination_cooldown_active,
    nomination_suppressed,
    owned_epithet_displays,
    persist_nomination_ballot,
    predicate_satisfied,
    read_pending_ballot,
    read_title_state,
    register_title_planner,
    remove_epithet,
    removal_digest,
    removal_records,
    safe_full_title,
    safe_pending_ballot,
    title_context_entries,
    title_event_effect_planner,
)
from world.rules.tests.test_cast_settlement import (
    _CastSettlementTestCase,
    _raising_stage,
)
from world.lore.guild import GuildRank
from world.tests.synthetic_data import make_title
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._knowledge_probes import basic_attack_key, live_fixed_title_registry, live_guild_rank_registry, live_registry

from ._support import (
    T_E_DISPLAY,
    T_E_KEY,
    T_F_DISPLAY,
    T_F_KEY,
    _open_title_scope,
    _starter,
)


class TitleGuildPairingTests(EvenniaTest):
    """Registration banks the rank title only; the epithet rides first claim."""

    def setUp(self):
        _open_title_scope(self)
        super().setUp()
        from world.quests.catalog import register_catalog

        register_catalog()
        self.room = create_object(Room, key="title guild lobby")
        self.player = create_object(PlayerCharacter, key="title guild player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.staff = create_object(NPC, key="title guild staff", location=self.room)
        self.staff.components.add(
            GuildStaff.create(
                self.staff, service_id="staff", branch_key="t_mossgate_branch"
            )
        )

    @covers_requirement("title-system::guild-registration-and-rank-promotion-grant-paired-titles-atomically")
    def test_first_quest_epithet_grant_banks_and_auto_equips_the_epithet_slot(self):
        with patch("world.rules.titles.planner.get_world_clock", return_value=WorldClock(42)):
            lines = grant_first_quest_epithet(self.player)
        self.assertEqual(lines, (f"獲得異名：{_starter().display}",))
        self.assertEqual(compose_full_title(self.player), _starter().display)
        collection, equipped = read_title_state(self.player)
        self.assertEqual(equipped, {"fixed": None, "epithet": _starter().display})
        self.assertEqual([entry["granted_tick"] for entry in collection], [42])
        self.assertEqual(collection[0]["origin_quote"], _starter().origin_basis)

    def test_a_second_first_quest_epithet_grant_is_silent_and_inert(self):
        first = grant_first_quest_epithet(self.player)
        before = deepcopy(read_title_state(self.player))
        self.assertEqual(grant_first_quest_epithet(self.player), ())
        self.assertEqual(read_title_state(self.player), before)
        self.assertEqual(first, (f"獲得異名：{_starter().display}",))

    @covers_requirement("title-system::guild-registration-and-rank-promotion-grant-paired-titles-atomically")
    def test_rank_titles_pair_one_to_one_with_the_guild_ranks(self):
        for rank, definition in live_guild_rank_registry().items():
            with self.subTest(rank=rank):
                title_row = live_fixed_title_registry()[definition.title_key]
                holder = create_object(PlayerCharacter, key=f"title-rank-{rank}")
                self.assertEqual(
                    grant_rank_title(holder, rank),
                    (f"獲得稱號：{title_row.display_name_zh}",),
                )
                self.assertEqual(compose_full_title(holder), title_row.display_name_zh)
                self.assertEqual(grant_rank_title(holder, rank), ())
        # An unknown rank grants nothing at all.
        self.assertEqual(grant_rank_title(self.player, "Z"), ())
        self.assertEqual(
            read_title_state(self.player), ([], {"fixed": None, "epithet": None})
        )

    @covers_requirement("guild-registration::guild-registration-grants-the-paired-starter-titles-atomically", "title-system::guild-registration-and-rank-promotion-grant-paired-titles-atomically")
    def test_registration_banks_the_rank_title_only(self):
        record = register_adventurer(self.player, staff=self.staff)
        self.assertEqual(
            record["title_notifications"],
            [f"獲得稱號：{T_F_DISPLAY}"],
        )
        self.assertEqual(compose_full_title(self.player), T_F_DISPLAY)
        self.assertEqual(banked_fixed_keys(self.player), (T_F_KEY,))
        self.assertEqual(banked_epithets(self.player), ())

    @covers_requirement("guild-registration::guild-registration-grants-the-paired-starter-titles-atomically", "title-system::guild-registration-and-rank-promotion-grant-paired-titles-atomically")
    def test_registration_rollback_leaves_no_titles_and_cannot_double_grant(self):
        class FakeAtomic:
            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                raise RuntimeError("db failure")

        with patch("django.db.transaction.atomic", return_value=FakeAtomic()):
            with self.assertRaises(RuntimeError):
                register_adventurer(self.player, staff=self.staff)
        self.assertEqual(
            read_title_state(self.player), ([], {"fixed": None, "epithet": None})
        )
        self.assertFalse(self.player.attributes.has(TITLE_COLLECTION_KEY))
        # The retry grants each entry exactly once.
        record = register_adventurer(self.player, staff=self.staff)
        self.assertEqual(record["title_notifications"], [f"獲得稱號：{T_F_DISPLAY}"])
        self.assertEqual(len(banked_fixed_keys(self.player)), 1)
        self.assertEqual(banked_epithets(self.player), ())

    def _arm_exam(self, target_rank: str) -> str:
        """Attach one ACTIVE exam record without running the exam pipeline.

        ``settle_exam_outcome`` only reads the session's mode/exam ID and the
        stored record; spawning the examiner and battlefield is
        ``test_guild_exams.py``'s contract, not the title surface's.
        """
        from world.rules.guild_exams import ExamState, GuildExamRecord, to_storage

        exam_id = f"{self.player.pk}:{target_rank}:1"
        record = GuildExamRecord(
            exam_id=exam_id,
            character_id=int(self.player.pk),
            target_rank=target_rank,
            requested_by="command",
            opponent_id=1,
            session_id=f"guild_exam:{self.player.pk}:1:{target_rank}:1",
            state=ExamState.ACTIVE,
            terminal_reason=None,
        )
        self.player.db.guild_exams = [to_storage(record)]
        return exam_id

    def _settle(self, exam_id: str, outcome: str):
        from world.rules.guild_exams import settle_exam_outcome

        return settle_exam_outcome(
            self.player,
            SimpleNamespace(mode="guild_exam", exam_id=exam_id),
            None,
            outcome,
        )

    @covers_requirement("title-system::guild-registration-and-rank-promotion-grant-paired-titles-atomically", "title-system::narrative-consumers-compose-predicates-read-the-collection")
    def test_promotion_banks_the_rank_title_inside_the_transaction(self):
        register_adventurer(self.player, staff=self.staff)
        exam_id = self._arm_exam("E")
        result = self._settle(exam_id, "exam_passed")
        self.assertEqual(result["passed"], True)
        self.assertEqual(result["title_notifications"], [f"獲得稱號：{T_E_DISPLAY}"])
        self.assertEqual(self.player.guild_rank, "E")
        self.assertEqual(
            banked_fixed_keys(self.player), (T_F_KEY, T_E_KEY)
        )
        # D8: the fixed slot was occupied, so promotion never re-equips.
        _, equipped = read_title_state(self.player)
        self.assertEqual(equipped["fixed"], T_F_KEY)

    def test_a_failed_exam_grants_nothing(self):
        register_adventurer(self.player, staff=self.staff)
        before = deepcopy(read_title_state(self.player))
        result = self._settle(self._arm_exam("E"), "exam_failed")
        self.assertNotIn("title_notifications", result)
        self.assertEqual(self.player.guild_rank, "F")
        self.assertEqual(read_title_state(self.player), before)

    @covers_requirement("title-system::guild-registration-and-rank-promotion-grant-paired-titles-atomically")
    def test_promotion_rollback_revokes_the_grant_and_the_notice(self):
        register_adventurer(self.player, staff=self.staff)
        exam_id = self._arm_exam("E")
        before_collection, before_equipped = read_title_state(self.player)
        from world.rules.guild_exams import _read_exams

        with patch(
            "world.rules.titles.grant_rank_title",
            side_effect=RuntimeError("db failure"),
        ):
            with self.assertRaises(RuntimeError):
                self._settle(exam_id, "exam_passed")
        # The rank write, the exam write, and the title write are one unit:
        # the promotion leaves nothing behind.
        self.assertEqual(self.player.guild_rank, "F")
        self.assertEqual([r.state.value for r in _read_exams(self.player)], ["active"])
        self.assertEqual(read_title_state(self.player), (before_collection, before_equipped))
        # Exactly one retry settles and grants once.
        result = self._settle(exam_id, "exam_passed")
        self.assertEqual(result["title_notifications"], [f"獲得稱號：{T_E_DISPLAY}"])
        self.assertEqual(len(banked_fixed_keys(self.player)), 2)

    def test_exam_pass_fires_observers_once_and_fail_does_not(self):
        from world.rules import guild_exams

        calls: list = []
        observer = lambda actor, rank: calls.append((actor, rank))  # noqa: E731
        guild_exams._EXAM_PASS_OBSERVERS.append(observer)
        self.addCleanup(
            lambda: guild_exams._EXAM_PASS_OBSERVERS.remove(observer)
        )
        register_adventurer(self.player, staff=self.staff)
        failed_id = self._arm_exam("E")
        result = self._settle(failed_id, "exam_failed")
        self.assertIs(result["passed"], False)
        self.assertEqual(calls, [])
        passed_id = self._arm_exam("E")
        self._settle(passed_id, "exam_passed")
        self.assertEqual(calls, [(self.player, "E")])
        # Replay of the settled exam returns early: no second notice.
        replay = self._settle(passed_id, "exam_passed")
        self.assertNotIn("passed", replay)
        self.assertEqual(replay["state"], "passed")
        self.assertEqual(len(calls), 1)

    def test_raising_exam_observer_cannot_break_settlement(self):
        from world.rules import guild_exams

        def explode(*args):
            raise RuntimeError("observer boom")

        guild_exams._EXAM_PASS_OBSERVERS.append(explode)
        self.addCleanup(
            lambda: guild_exams._EXAM_PASS_OBSERVERS.remove(explode)
        )
        register_adventurer(self.player, staff=self.staff)
        result = self._settle(self._arm_exam("E"), "exam_passed")
        self.assertIs(result["passed"], True)
        self.assertEqual(self.player.guild_rank, "E")
