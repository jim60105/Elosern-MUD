"""Slice of ``test_titles``: EpithetRemovalRulesTests."""
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
    _open_title_scope,
    _starter,
)


class EpithetRemovalRulesTests(EvenniaTest):
    """The sole delete path: gate precedence, the transactional writer, and
    the bounded durable removal log (title-codex-removal task 4.2)."""

    def setUp(self):
        _open_title_scope(self)
        super().setUp()
        self.entity = create_object(PlayerCharacter, key="removal-holder")

    def _bank_pair(self):
        """The titled pair (F fixed + starter epithet) plus a removable one."""
        grant_rank_title(self.entity, "F")
        grant_first_quest_epithet(self.entity)
        bank_epithet(self.entity, "破城先鋒", "率先破門。", 500)

    @covers_requirement(
        "title-system::epithet-removal-is-the-only-delete-path-and-gates-precede-confirmation"
    )
    def test_gate_precedence_unknown_then_last_then_equipped(self):
        # Unknown before anything: no epithets at all, fixed keys, blanks,
        # and non-strings all read TARGET_UNKNOWN.
        grant_first_quest_epithet(self.entity)
        for target in (" nonexistent", T_F_KEY, "", None, 7, True, ["破城先鋒"]):
            with self.subTest(target=target):
                self.assertIs(
                    epithet_removal_gate(self.entity, target),
                    TitleRemovalReason.TARGET_UNKNOWN,
                )
        self.assertIs(
            epithet_removal_gate(self.entity, "破城先鋒"),
            TitleRemovalReason.TARGET_UNKNOWN,
        )
        # Sole epithet (necessarily equipped by D8) reads LAST, not EQUIPPED.
        self.assertIs(
            epithet_removal_gate(self.entity, _starter().display),
            TitleRemovalReason.LAST_EPITHET,
        )
        # With two epithets the equipped one reads EQUIPPED, the other passes.
        bank_epithet(self.entity, "破城先鋒", "率先破門。", 500)
        self.assertIs(
            epithet_removal_gate(self.entity, _starter().display),
            TitleRemovalReason.EQUIPPED_UNREMOVABLE,
        )
        self.assertIsNone(epithet_removal_gate(self.entity, "破城先鋒"))
        # Swapping moves the verdict, never the precedence.
        equip_epithet(self.entity, "破城先鋒")
        self.assertIsNone(epithet_removal_gate(self.entity, _starter().display))
        self.assertIs(
            epithet_removal_gate(self.entity, "破城先鋒"),
            TitleRemovalReason.EQUIPPED_UNREMOVABLE,
        )
        # A malformed collection fails closed through the strict read.
        self.entity.attributes.add(TITLE_COLLECTION_KEY, "not-a-list")
        with self.assertRaises(TitleDataError):
            epithet_removal_gate(self.entity, "破城先鋒")

    def test_gated_calls_raise_stable_reasons_without_touching_state(self):
        self._bank_pair()
        before = read_title_state(self.entity)
        for target, reason in (
            ("不存在", TitleRemovalReason.TARGET_UNKNOWN),
            (T_F_KEY, TitleRemovalReason.TARGET_UNKNOWN),
            (_starter().display, TitleRemovalReason.EQUIPPED_UNREMOVABLE),
        ):
            with self.subTest(target=target):
                with self.assertRaises(TitleRemovalError) as caught:
                    remove_epithet(self.entity, target)
                self.assertIs(caught.exception.reason, reason)
                self.assertEqual(read_title_state(self.entity), before)
                self.assertEqual(removal_records(self.entity), ())

    def test_successful_removal_shrinks_by_one_and_writes_the_log(self):
        self._bank_pair()
        before_collection, before_equipped = read_title_state(self.entity)
        before_serialized = (
            deepcopy(self.entity.attributes.get(TITLE_COLLECTION_KEY)),
            deepcopy(self.entity.attributes.get(TITLE_EQUIPPED_KEY)),
        )
        with patch("world.rules.titles.removal.get_world_clock", return_value=WorldClock(900)):
            event_log = remove_epithet(self.entity, "破城先鋒")
        collection, equipped = read_title_state(self.entity)
        # Exactly one entry gone; the OTHER entry is byte-identical.
        self.assertEqual(len(collection), len(before_collection) - 1)
        self.assertEqual(collection, before_serialized[0][: len(collection)])
        # Slots are written back UNCHANGED (a removal can never orphan one).
        self.assertEqual(equipped, before_equipped)
        self.assertEqual(
            self.entity.attributes.get(TITLE_EQUIPPED_KEY), before_serialized[1]
        )
        # The durable log gained exactly the newest-first {tick, display}.
        records = removal_records(self.entity)
        self.assertEqual(records, ({"tick": 900, "display": "破城先鋒"},))
        # The EventLog is renderable and names the display.
        self.assertEqual(event_log.entries[0].kind, "title_epithet_removed")
        self.assertEqual(
            event_log.entries[0].data, {"display": "破城先鋒", "tick": 900}
        )
        self.assertIn("放下了異名：破城先鋒", render_plain_text(event_log))

    def test_swap_then_delete_keeps_both_slots_intact(self):
        self._bank_pair()
        equip_epithet(self.entity, "破城先鋒")
        remove_epithet(self.entity, _starter().display)
        _collection, equipped = read_title_state(self.entity)
        self.assertEqual(
            equipped, {"fixed": T_F_KEY, "epithet": "破城先鋒"}
        )
        self.assertEqual(
            [entry["display"] for entry in banked_epithets(self.entity)],
            ["破城先鋒"],
        )

    def test_writer_failure_restores_all_three_attributes(self):
        self._bank_pair()
        before = (
            deepcopy(self.entity.attributes.get(TITLE_COLLECTION_KEY)),
            deepcopy(self.entity.attributes.get(TITLE_EQUIPPED_KEY)),
            self.entity.attributes.has(REMOVALS_LOG_KEY),
        )

        def explode(key, value, **kwargs):
            if key == REMOVALS_LOG_KEY:
                raise RuntimeError("db failure")

        with patch.object(
            self.entity.attributes, "add", side_effect=explode
        ):
            with self.assertRaises(RuntimeError):
                remove_epithet(self.entity, "破城先鋒")
        self.assertEqual(
            self.entity.attributes.get(TITLE_COLLECTION_KEY), before[0]
        )
        self.assertEqual(
            self.entity.attributes.get(TITLE_EQUIPPED_KEY), before[1]
        )
        self.assertEqual(
            self.entity.attributes.has(REMOVALS_LOG_KEY), before[2]
        )
        # One retry after the fault completes exactly once.
        with patch("world.rules.titles.removal.get_world_clock", return_value=WorldClock(901)):
            remove_epithet(self.entity, "破城先鋒")
        self.assertEqual(
            [entry["display"] for entry in banked_epithets(self.entity)],
            [_starter().display],
        )
        self.assertEqual(
            removal_records(self.entity),
            ({"tick": 901, "display": "破城先鋒"},),
        )

    def test_removal_log_is_bounded_newest_first(self):
        grant_first_quest_epithet(self.entity)
        previous = _starter().display
        for index in range(1, 6):
            display = f"異名{index}"
            bank_epithet(self.entity, display, f"事蹟{index}。", 100 * index)
            equip_epithet(self.entity, display)
            # The previously equipped epithet is now unequipped (and the
            # collection holds at least two) → removable.
            with patch(
                "world.rules.titles.removal.get_world_clock",
                return_value=WorldClock(1000 + index),
            ):
                remove_epithet(self.entity, previous)
            previous = display
        records = removal_records(self.entity)
        self.assertEqual(len(records), MAX_REMOVAL_RECORDS)
        self.assertEqual(records[0], {"tick": 1005, "display": "異名4"})
        self.assertEqual(records[1], {"tick": 1004, "display": "異名3"})
        self.assertEqual(records[2], {"tick": 1003, "display": "異名2"})

    def test_removed_display_is_renomable_and_digests_softly(self):
        self._bank_pair()
        with patch("world.rules.titles.removal.get_world_clock", return_value=WorldClock(900)):
            remove_epithet(self.entity, "破城先鋒")
        # The live-collection collision filter no longer blocks the name.
        self.assertNotIn("破城先鋒", owned_epithet_displays(self.entity))
        self.assertTrue(
            bank_epithet(self.entity, "破城先鋒", "再次破門。", 950)
        )
        # The digest is prompt context ONLY, never a filter rule.
        self.assertEqual(removal_digest(self.entity), ("破城先鋒",))

    def test_digest_dedupes_and_degrades_on_malformed_history(self):
        grant_first_quest_epithet(self.entity)
        bank_epithet(self.entity, "甲名", "甲事蹟。", 100)
        bank_epithet(self.entity, "乙名", "乙事蹟。", 200)
        equip_epithet(self.entity, "乙名")
        remove_epithet(self.entity, "甲名")
        # Force a duplicate display record directly (same name, older tick).
        history = list(self.entity.attributes.get(REMOVALS_LOG_KEY))
        self.entity.attributes.add(
            REMOVALS_LOG_KEY,
            [*history, {"tick": 50, "display": "甲名"}],
        )
        digest = removal_digest(self.entity)
        self.assertEqual(len(digest), len(set(digest)))
        self.assertEqual(digest, ("甲名",))
        # Malformed history degrades the digest to empty (prompt context only).
        self.entity.attributes.add(REMOVALS_LOG_KEY, "not-a-list")
        self.assertEqual(removal_digest(self.entity), ())
        with self.assertRaises(TitleDataError):
            removal_records(self.entity)
        # The over-cap log is a strict failure too.
        self.entity.attributes.add(
            REMOVALS_LOG_KEY,
            [{"tick": i, "display": f"名{i}"} for i in range(1, MAX_REMOVAL_RECORDS + 2)],
        )
        with self.assertRaises(TitleDataError):
            removal_records(self.entity)
        self.assertEqual(removal_digest(self.entity), ())

    def test_digest_limit_validates(self):
        self._bank_pair()
        remove_epithet(self.entity, "破城先鋒")
        self.assertEqual(removal_digest(self.entity, 0), ())
        self.assertEqual(removal_digest(self.entity, 1), ("破城先鋒",))
        for bad_limit in (True, -1, "1", None):
            with self.subTest(limit=bad_limit), self.assertRaises(ValueError):
                removal_digest(self.entity, bad_limit)
