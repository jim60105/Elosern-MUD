"""Slice of ``test_npc_intents``: AdjustRelationIntentTests, PartyInviteIntentTests.
"""
import inspect
from unittest.mock import patch
import unittest
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExaminer, GuildStaff, QuestIssuer
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.quests.definitions import QuestStage
from world.quests.runtime import QuestState, read_records
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    acquire as _acquire,
    quest as _quest,
    register as _register_quest,
)
from world.rules.combat_session import read_session
from world.rules.guild import GuildDataError, register_adventurer
from world.rules.guild_config import CATALOG
from world.rules.guild_exams import ExamState, _read_exams
from world.rules.guild_offers import (
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    register_guild_offer,
)
from world.rules.npc_intents import (
    STALE_CONTEXT_REASON,
    IntentOutcome,
    _apply_plan,
    apply_npc_intent,
    intent_context_ok,
    is_stale_context,
)
from world.rules.quest_issuance import (
    QuestIssuance,
    Settlement,
    guild_issuer_key,
    npc_issuer_key,
    register_quest_issuance,
    resolve_issuance,
)
from world.rules.surfaces import write_counter_trait
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.tests._guild_service_probes import (
    install_synthetic_catalog,
    synth_catalog,
)
from world.tests.synthetic_data import SYNTH_GUILD_BRANCH_KEY, SYNTH_ITEMS
from tools.spec_traceability import covers_requirement


class AdjustRelationIntentTests(EvenniaTestCase):
    """The adjust_relation intent routes through the sole affinity writer."""

    def setUp(self):
        super().setUp()
        # Register the quest catalog in this class's own setup: the affinity
        # writer reaches the rulebook load, which resolves
        # ``introductory_hunt`` from the definition registry.
        register_catalog()
        self.room = create_object(Room, key="affinity room")
        self.player = create_object(PlayerCharacter, key="affinity player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.npc = create_object(NPC, key="affinity npc", location=self.room)

    def _relation_intent(self, delta):
        return {"kind": "adjust_relation", "delta": delta}

    def _record(self):
        return self.npc.relations._load(self.player)

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_full_delta_applies_through_the_writer_and_reports_the_amount(self):
        outcome = apply_npc_intent(self.npc, self.player, self._relation_intent(5))
        self.assertTrue(outcome.applied)
        self.assertEqual(outcome.delta_used, 5)
        record = self._record()
        self.assertEqual(record.value, 5)
        self.assertEqual(record.daily_gain, 5)

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_partial_budget_delta_applies_what_remains_and_reports_it(self):
        first = apply_npc_intent(self.npc, self.player, self._relation_intent(3))
        self.assertTrue(first.applied)
        self.assertEqual(first.delta_used, 3)
        outcome = apply_npc_intent(self.npc, self.player, self._relation_intent(4))
        self.assertTrue(outcome.applied)
        self.assertEqual(outcome.delta_used, 2)
        record = self._record()
        self.assertEqual(record.value, 5)
        self.assertEqual(record.daily_gain, 5)

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_zero_budget_delta_is_discarded_with_no_state_change(self):
        first = apply_npc_intent(self.npc, self.player, self._relation_intent(5))
        self.assertTrue(first.applied)
        outcome = apply_npc_intent(self.npc, self.player, self._relation_intent(3))
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.delta_used, 0)
        self.assertIn("budget", outcome.reason)
        record = self._record()
        self.assertEqual(record.value, 5)
        self.assertEqual(record.daily_gain, 5)

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_malformed_delta_payloads_are_rejected_without_state_change(self):
        for intent in (
            {"kind": "adjust_relation"},
            {"kind": "adjust_relation", "delta": -1},
            {"kind": "adjust_relation", "delta": 11},
            {"kind": "adjust_relation", "delta": 1.5},
            {"kind": "adjust_relation", "delta": True},
            {"kind": "adjust_relation", "delta": "3"},
            {"kind": "adjust_relation", "delta": 3, "extra": 1},
        ):
            with self.subTest(intent=intent):
                outcome = apply_npc_intent(self.npc, self.player, intent)
                self.assertFalse(outcome.applied)
                self.assertEqual(outcome.delta_used, 0)
                self.assertIsNone(self._record())

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_non_npc_target_is_rejected_without_state_change(self):
        outcome = apply_npc_intent(self.player, self.player, self._relation_intent(1))
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.delta_used, 0)
        self.assertIn("NPC", outcome.reason)
        self.assertIsNone(self.player.relations._load(self.player))

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_zero_delta_intent_is_discarded_with_no_state_change(self):
        outcome = apply_npc_intent(self.npc, self.player, self._relation_intent(0))
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.delta_used, 0)
        self.assertIsNone(self._record())

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_zero_delta_on_a_later_world_day_creates_no_record(self):
        from world.rules.clock import CLOCK_YAML, get_world_clock

        day_seconds = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]
        clock = get_world_clock()
        self.addCleanup(clock._persist, 0)
        clock._persist(day_seconds)
        outcome = apply_npc_intent(self.npc, self.player, self._relation_intent(0))
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.delta_used, 0)
        self.assertIsNone(self._record())
        self.assertFalse(self.npc.relations.has_record(self.player))


class PartyInviteIntentTests(EvenniaTestCase):
    """The party_invite intent routes through the party membership module."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="party intent room")
        self.player = create_object(PlayerCharacter, key="party intent player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.npc = create_object(NPC, key="party intent npc", location=self.room)

    def _invite_intent(self, accept):
        return {"kind": "party_invite", "accept": accept}

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_accepted_invite_routes_through_join_party(self):
        outcome = apply_npc_intent(self.npc, self.player, self._invite_intent(True))
        self.assertTrue(outcome.applied)
        from world.rules.party import is_companion

        self.assertTrue(is_companion(self.npc, self.player))
        self.assertEqual(int(self.npc.db.party_member), int(self.player.pk))

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_declined_invite_is_an_applied_no_op(self):
        outcome = apply_npc_intent(self.npc, self.player, self._invite_intent(False))
        self.assertTrue(outcome.applied)
        from world.rules.party import is_companion

        self.assertFalse(is_companion(self.npc, self.player))
        self.assertIsNone(self.npc.db.party_member)

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_malformed_invite_payloads_are_rejected_without_state_change(self):
        for intent in (
            {"kind": "party_invite"},
            {"kind": "party_invite", "accept": "yes"},
            {"kind": "party_invite", "accept": 1},
            {"kind": "party_invite", "accept": True, "extra": 1},
        ):
            with self.subTest(intent=intent):
                outcome = apply_npc_intent(self.npc, self.player, intent)
                self.assertFalse(outcome.applied)
                from world.rules.party import is_companion

                self.assertFalse(is_companion(self.npc, self.player))

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_remote_join_gate_failure_discards_only_the_intent(self):
        other = create_object(Room, key="remote room")
        far = create_object(NPC, key="far npc", location=other)
        # Bypass the completion gate so ``join_party``'s own co-location
        # recheck stays in force and is exercised directly (task 3.2: the
        # party flow still rechecks below the shared gate).
        outcome = apply_npc_intent(
            far, self.player, self._invite_intent(True), context_ok=lambda npc, player: True
        )
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "not_co_located")
        self.assertIsNone(far.db.party_member)

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_full_party_gate_failure_surfaces_the_distinct_reason(self):
        from world.rules.party import PARTY_MAX_COMPANIONS, join_party

        for index in range(PARTY_MAX_COMPANIONS):
            join_party(
                create_object(NPC, key=f"companion {index}", location=self.room),
                self.player,
            )
        outcome = apply_npc_intent(self.npc, self.player, self._invite_intent(True))
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "party_full")
        self.assertIsNone(self.npc.db.party_member)

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_duplicate_join_gate_failure_surfaces_the_distinct_reason(self):
        from world.rules.party import join_party

        join_party(self.npc, self.player)
        outcome = apply_npc_intent(self.npc, self.player, self._invite_intent(True))
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "already_companion")
        self.assertEqual(int(self.npc.db.party_member), int(self.player.pk))

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_non_npc_target_is_rejected_without_state_change(self):
        outcome = apply_npc_intent(self.player, self.player, self._invite_intent(True))
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "not_npc")
