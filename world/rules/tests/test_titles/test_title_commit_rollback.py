"""Slice of ``test_titles``: TitleCastGrantSettlementTests, TitleCommitRollbackTests."""
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
    T_E_KEY,
    T_F_KEY,
    _COUNTER_ROW_KEY,
    _open_title_scope,
    _starter,
    _with_counter_row,
)


class TitleCommitRollbackTests(EvenniaTest):
    """A failed commit restores title state exactly (no lost or double grant)."""

    def setUp(self):
        _open_title_scope(self)
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="title-commit-actor")

    def _bank_effect(self, key=T_F_KEY):
        return PendingEffect(
            self.actor,
            f"title_granted|{key}",
            frozenset({"titles"}),
            lambda: bank_fixed(self.actor, key, 5),
            notify=f"獲得稱號：{fixed_display_name(key)}",
        )

    def _raising_effect(self):
        return PendingEffect(
            self.actor,
            "injected failure",
            frozenset({"titles"}),
            lambda: (_ for _ in ()).throw(RuntimeError("injected")),
        )

    def test_failed_commit_restores_absent_title_state(self):
        with self.assertRaises(CommitFailed):
            _commit([self._bank_effect(), self._raising_effect()], char="tester", action="test_skill")
        self.assertEqual(
            read_title_state(self.actor), ([], {"fixed": None, "epithet": None})
        )
        self.assertFalse(self.actor.attributes.has(TITLE_COLLECTION_KEY))

    def test_failed_commit_restores_a_pre_existing_collection(self):
        bank_fixed(self.actor, T_F_KEY, 1)
        before = deepcopy(read_title_state(self.actor))
        with self.assertRaises(CommitFailed):
            _commit([self._bank_effect(T_E_KEY), self._raising_effect()], char="tester", action="test_skill")
        self.assertEqual(read_title_state(self.actor), before)

    def test_a_successful_commit_grants_once(self):
        _commit([self._bank_effect(T_F_KEY)], char="tester", action="test_skill")
        self.assertEqual(banked_fixed_keys(self.actor), (T_F_KEY,))

    def test_failed_commit_restores_the_removal_log_surface(self):
        # The durable removal log is registered in the commit-window entity
        # snapshot: a failed commit restores it byte-identically alongside
        # the title attributes (no orphaned removal record).
        bank_epithet(self.actor, _starter().display, "初入南門。", 1)
        bank_epithet(self.actor, "待放之名", "舊事蹟。", 2)
        remove_epithet(self.actor, "待放之名")
        before_log = deepcopy(self.actor.attributes.get(REMOVALS_LOG_KEY))
        self.assertTrue(self.actor.attributes.has(REMOVALS_LOG_KEY))

        def mutate_removals():
            self.actor.attributes.add(
                REMOVALS_LOG_KEY, [{"tick": 999, "display": "注入之名"}]
            )

        effects = [
            PendingEffect(
                self.actor,
                "removal-log-write",
                frozenset({"titles"}),
                mutate_removals,
            ),
            self._raising_effect(),
        ]
        with self.assertRaises(CommitFailed):
            _commit(effects, char="tester", action="test_skill")
        self.assertEqual(self.actor.attributes.get(REMOVALS_LOG_KEY), before_log)


class TitleCastGrantSettlementTests(_CastSettlementTestCase):
    """The planner grant rides the cast's outer settlement transaction."""

    def setUp(self):
        super().setUp()
        self.planners = dict(_EVENT_EFFECT_PLANNERS)
        register_title_planner()
        self.char1.db.disguised_stats = {"atk_phys": 1}
        # Raised through the sanctioned mutator: a hand-forced one-key
        # ``sexual_traits`` record is not durable on an actor whose sexual
        # handler is mounted (the proxy flushes its own record back).
        for _ in range(3):
            self.char1.sexual.record_watched()

    def tearDown(self):
        _EVENT_EFFECT_PLANNERS.clear()
        _EVENT_EFFECT_PLANNERS.update(self.planners)
        super().tearDown()

    def _settle(self, clock):
        return settle_out_of_combat_cast(self._request(), clock=clock)

    @_with_counter_row
    @covers_requirement("title-system::fixed-title-grants-ride-the-triggering-action-s-atomic-transaction")
    def test_grant_and_notification_commit_with_the_cast(self):
        settlement = self._settle(WorldClock())
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(settlement.notifications, ("獲得稱號：受矚者",))
        self.assertEqual(banked_fixed_keys(self.char1), (_COUNTER_ROW_KEY,))
        self.assertEqual(compose_full_title(self.char1), "受矚者")

    @_with_counter_row
    def test_a_second_cast_neither_regrants_nor_notifies(self):
        self._settle(WorldClock())
        settlement = self._settle(WorldClock())
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(settlement.notifications, ())
        self.assertEqual(banked_fixed_keys(self.char1), (_COUNTER_ROW_KEY,))

    @_with_counter_row
    @covers_requirement("title-system::fixed-title-grants-ride-the-triggering-action-s-atomic-transaction")
    def test_clock_boundary_failure_rolls_the_grant_back_and_drops_the_notice(self):
        _EVENT_SOURCES["shop_hours"] = _raising_stage()
        with self.assertRaises(RuntimeError):
            self._settle(WorldClock())
        self.assertEqual(
            read_title_state(self.char1), ([], {"fixed": None, "epithet": None})
        )
        self.assertFalse(self.char1.attributes.has(TITLE_COLLECTION_KEY))
        self.assertIsNone(self._raw_attribute(self.char1, TITLE_COLLECTION_KEY))
        # Restore the shipped boundary stages (the injected key may not have
        # existed before): clear-then-update mirrors the class's own teardown.
        _EVENT_SOURCES.clear()
        _EVENT_SOURCES.update(self._sources)
        settlement = self._settle(WorldClock())
        self.assertEqual(settlement.notifications, ("獲得稱號：受矚者",))
        self.assertEqual(banked_fixed_keys(self.char1), (_COUNTER_ROW_KEY,))

    @_with_counter_row
    def test_final_clock_persistence_failure_rolls_the_grant_back(self):
        clock = WorldClock()
        clock._persist = lambda tick: (_ for _ in ()).throw(
            RuntimeError("simulated persist failure")
        )
        with self.assertRaises(RuntimeError):
            self._settle(clock)
        self.assertEqual(
            read_title_state(self.char1), ([], {"fixed": None, "epithet": None})
        )
        self.assertIsNone(self._raw_attribute(self.char1, TITLE_EQUIPPED_KEY))
