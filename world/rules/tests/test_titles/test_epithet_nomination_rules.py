"""Slice of ``test_titles``: EpithetNominationRulesTests."""
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
    T_F_KEY,
    _DAY,
    _ballot,
    _open_title_scope,
    _starter,
    get_world_clock_tick,
)


class EpithetNominationRulesTests(EvenniaTest):
    """Ballot face, suppression/cooldown, and the three rules-layer writers."""

    def setUp(self):
        _open_title_scope(self)
        super().setUp()
        self.entity = create_object(PlayerCharacter, key="ballot-holder")

    def _persist(self, *pairs):
        return persist_nomination_ballot(self.entity, _ballot(*pairs))

    def test_absent_faces_read_empty(self):
        self.assertEqual(read_pending_ballot(self.entity), ())
        self.assertEqual(safe_pending_ballot(self.entity), ())
        self.assertEqual(decline_records(self.entity), ())
        self.assertFalse(nomination_suppressed(self.entity))

    @covers_requirement("title-system::the-ballot-persists-unchanged-until-consent")
    def test_persist_round_trips_the_ballot(self):
        self.assertTrue(self._persist(("火焰之心", "燒毀匪寨"), ("新月", "月下救人")))
        self.assertEqual(
            read_pending_ballot(self.entity),
            (
                {"display": "火焰之心", "basis": "燒毀匪寨"},
                {"display": "新月", "basis": "月下救人"},
            ),
        )
        self.assertEqual(safe_pending_ballot(self.entity), read_pending_ballot(self.entity))

    def test_persist_rejects_invalid_shapes_without_writing(self):
        cases = [
            [],
            _ballot(("甲名", "事"), ("乙名", "事"), ("丙名", "事"), ("丁名", "事")),
            [{"display": "只有顯示"}],
            [{"display": "", "basis": "空"}],
            [{"display": "甲名", "basis": "事" * 81}],
            [{"display": "甲" * 65, "basis": "短"}],
            "not-a-sequence-of-mappings",
        ]
        for candidates in cases:
            with self.subTest(candidates=str(candidates)[:24]):
                self.assertFalse(persist_nomination_ballot(self.entity, candidates))
        self.assertFalse(self.entity.attributes.has(PENDING_BALLOT_KEY))

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_single_pending_ballot_blocks_replacement(self):
        self._persist(("甲名", "一"))
        self.assertFalse(self._persist(("乙名", "二")))
        self.assertEqual(read_pending_ballot(self.entity)[0]["display"], "甲名")

    def test_malformed_ballot_fails_closed(self):
        self.entity.attributes.add(PENDING_BALLOT_KEY, [{"display": "缺 basis"}])
        with self.assertRaises(TitleDataError):
            read_pending_ballot(self.entity)
        self.assertEqual(safe_pending_ballot(self.entity), ())
        self.assertTrue(nomination_suppressed(self.entity))
        self.assertFalse(self._persist(("甲名", "一")))

    def test_accept_without_ballot_is_a_stable_reason(self):
        with self.assertRaises(TitleBallotError) as caught:
            accept_epithet(self.entity, 1)
        self.assertIs(caught.exception.reason, TitleBallotReason.NO_PENDING_BALLOT)

    def test_accept_index_validation(self):
        self._persist(("甲名", "一"), ("乙名", "二"))
        for bad in (0, 3, -1, "1", True, None):
            with self.subTest(index=bad), self.assertRaises(TitleBallotError) as caught:
                accept_epithet(self.entity, bad)
            self.assertIs(
                caught.exception.reason, TitleBallotReason.BALLOT_INDEX_OUT_OF_RANGE
            )
        self.assertEqual(len(read_pending_ballot(self.entity)), 2)

    @covers_requirement("title-system::ballot-persistence-acceptance-and-decline-are-rules-layer-writers-only")
    def test_accept_banks_auto_equips_and_clears(self):
        bank_fixed(self.entity, T_F_KEY, 1)
        self._persist(("火焰之心", "焚盡匪寨"))
        display, banked = accept_epithet(self.entity, 1)
        self.assertEqual((display, banked), ("火焰之心", True))
        collection, equipped = read_title_state(self.entity)
        epithet = [entry for entry in collection if entry["kind"] == "epithet"]
        self.assertEqual(len(epithet), 1)
        self.assertEqual(epithet[0]["origin_quote"], "焚盡匪寨")
        self.assertEqual(epithet[0]["granted_tick"], get_world_clock_tick())
        self.assertEqual(equipped["epithet"], "火焰之心")
        self.assertFalse(self.entity.attributes.has(PENDING_BALLOT_KEY))
        # Accepting never starts a cooldown.
        self.assertFalse(nomination_suppressed(self.entity))

    @covers_requirement("title-system::ballot-persistence-acceptance-and-decline-are-rules-layer-writers-only")
    def test_accept_with_occupied_slot_banks_without_touching_it(self):
        grant_first_quest_epithet(self.entity)
        self._persist(("新月", "月下救人"))
        _, equipped_before = read_title_state(self.entity)
        self.assertEqual(equipped_before["epithet"], _starter().display)
        accept_epithet(self.entity, 1)
        _, equipped_after = read_title_state(self.entity)
        self.assertEqual(equipped_after["epithet"], _starter().display)

    def test_duplicate_display_accept_consumes_ballot_without_new_entry(self):
        grant_first_quest_epithet(self.entity)
        self._persist((_starter().display, "再次入票的事蹟"))
        display, banked = accept_epithet(self.entity, 1)
        self.assertEqual((display, banked), (_starter().display, False))
        self.assertFalse(self.entity.attributes.has(PENDING_BALLOT_KEY))
        self.assertEqual(len(banked_epithets(self.entity)), 1)

    def test_replay_accept_reports_no_pending_ballot(self):
        self._persist(("甲名", "一"))
        accept_epithet(self.entity, 1)
        with self.assertRaises(TitleBallotError) as caught:
            accept_epithet(self.entity, 1)
        self.assertIs(caught.exception.reason, TitleBallotReason.NO_PENDING_BALLOT)

    @covers_requirement("title-system::ballot-persistence-acceptance-and-decline-are-rules-layer-writers-only")
    def test_accept_failure_restores_every_attribute(self):
        bank_fixed(self.entity, T_F_KEY, 1)
        self._persist(("甲名", "一"))
        before = read_title_state(self.entity)
        with patch.object(
            self.entity.attributes, "remove", side_effect=RuntimeError("db failure")
        ):
            with self.assertRaises(RuntimeError):
                accept_epithet(self.entity, 1)
        self.assertEqual(read_title_state(self.entity), before)
        self.assertEqual(len(read_pending_ballot(self.entity)), 1)
        # One retry after the fault clears everything exactly once.
        accept_epithet(self.entity, 1)
        self.assertFalse(self.entity.attributes.has(PENDING_BALLOT_KEY))
        self.assertEqual(len(banked_epithets(self.entity)), 1)

    @covers_requirement("title-system::ballot-persistence-acceptance-and-decline-are-rules-layer-writers-only")
    def test_decline_records_emits_and_suppresses(self):
        self._persist(("甲名", "一"), ("乙名", "二"))
        event_log = decline_epithet_ballot(self.entity)
        text = render_plain_text(event_log)
        self.assertIn("甲名", text)
        self.assertIn("乙名", text)
        self.assertEqual(event_log.entries[0].kind, "title_epithet_declined")
        self.assertEqual(
            event_log.entries[0].data["displays"], ["甲名", "乙名"]
        )
        self.assertFalse(self.entity.attributes.has(PENDING_BALLOT_KEY))
        records = decline_records(self.entity)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["displays"], ("甲名", "乙名"))
        self.assertTrue(nomination_suppressed(self.entity))

    def test_decline_without_ballot_is_a_stable_reason(self):
        with self.assertRaises(TitleBallotError) as caught:
            decline_epithet_ballot(self.entity)
        self.assertIs(
            caught.exception.reason, TitleBallotReason.NO_PENDING_BALLOT
        )
        self.assertEqual(decline_records(self.entity), ())
        self.assertFalse(nomination_suppressed(self.entity))

    def _force_decline_cycle(self, display: str, tick: int) -> None:
        """Write a ballot directly (cooldown bypass) and decline at ``tick``.

        ``get_world_clock`` builds a fresh instance per call, so the decline
        clock is pinned through the titles-module binding instead of mutating
        one instance.
        """
        from unittest.mock import patch

        from world.rules.clock import WorldClock

        self.entity.attributes.add(PENDING_BALLOT_KEY, _ballot((display, "事蹟")))
        with patch(
            "world.rules.titles.ballot.get_world_clock",
            return_value=WorldClock(tick),
        ):
            decline_epithet_ballot(self.entity)

    def test_decline_log_is_bounded_newest_first(self):
        for index in range(1, 6):
            self._force_decline_cycle(f"異名{index}", index * _DAY)
        records = decline_records(self.entity)
        self.assertEqual(len(records), MAX_DECLINE_RECORDS)
        self.assertEqual(records[0]["tick"], 5 * _DAY)
        self.assertEqual(records[0]["displays"], ("異名5",))
        digest = declined_digest(self.entity)
        self.assertEqual(digest, ("異名5", "異名4", "異名3"))

    def test_cooldown_arithmetic_across_boundaries(self):
        self.entity.attributes.add(
            DECLINED_LOG_KEY, [{"tick": 5 * _DAY + 100, "displays": ["甲名"]}]
        )
        # Same day and after the FIRST boundary: suppressed.
        self.assertTrue(nomination_cooldown_active(self.entity, 5 * _DAY + 500))
        self.assertTrue(nomination_cooldown_active(self.entity, 6 * _DAY))
        # The SECOND boundary resumes; multi-day jumps behave by subtraction.
        self.assertFalse(nomination_cooldown_active(self.entity, 7 * _DAY))
        self.assertFalse(nomination_cooldown_active(self.entity, 40 * _DAY))
        # With no ballot stored, suppression is exactly the cooldown.
        self.assertTrue(nomination_suppressed(self.entity, 6 * _DAY))
        self.assertFalse(nomination_suppressed(self.entity, 7 * _DAY))

    def test_bad_now_tick_is_rejected(self):
        self.entity.attributes.add(
            DECLINED_LOG_KEY, [{"tick": 1, "displays": ["甲名"]}]
        )
        for bad in (-1, True, "5"):
            with self.subTest(now=bad), self.assertRaises(TitleDataError):
                nomination_cooldown_active(self.entity, bad)

    @covers_requirement("title-system::the-ballot-persists-unchanged-until-consent")
    def test_ballot_survives_cache_reset(self):
        self._persist(("甲名", "一"))
        self.entity.attributes.reset_cache()
        self.assertEqual(read_pending_ballot(self.entity)[0]["display"], "甲名")

    def test_owned_displays_and_digest_reads(self):
        grant_first_quest_epithet(self.entity)
        self.assertEqual(
                owned_epithet_displays(self.entity),
                frozenset({_starter().display}),
        )
        self.assertEqual(declined_digest(self.entity), ())
        for bad_limit in (True, -1, "5", None):
            with self.subTest(limit=bad_limit), self.assertRaises(ValueError):
                declined_digest(self.entity, bad_limit)

    @covers_requirement("title-system::ballot-persistence-acceptance-and-decline-are-rules-layer-writers-only")
    def test_persist_rechecks_suppression_after_proposal(self):
        # Race: a ballot appears between the service pre-check and the
        # writer's re-check. The writer must refuse without touching it.
        first = self._persist(("先來", "一"))
        self.assertTrue(first)
        self.assertFalse(self._persist(("後來", "二")))
        self.assertEqual(
            read_pending_ballot(self.entity),
            ({"display": "先來", "basis": "一"},),
        )
