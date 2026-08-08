"""Tests for the deterministic NPC intent verifier-and-applier (npc-dialogue).

Covers ``apply_npc_intent``: the ``request_guild_exam`` routing through
``start_guild_exam`` with ``requested_by="npc_intent"``, every failed exam gate
discarding only the intent, the atomic give/take item transfer primitive, the
``adjust_relation`` routing through the sole-writer affinity API with the
applied-amount report, the remaining forward-declared kind rejections, and the
boundary rule that this module never imports the generative package.
"""

import inspect
from unittest.mock import patch
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildExaminer, GuildStaff
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.quests.definitions import QuestStage
from world.quests.runtime import QuestState, accept_quest, read_records
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    acquire as _acquire,
    quest as _quest,
    register as _register_quest,
)
from world.rules.combat_session import read_session
from world.rules.guild import GuildDataError, register_adventurer
from world.rules.guild_config import CATALOG
from world.rules.guild_exams import ExamState, _read_exams
from world.rules.npc_intents import (
    IntentOutcome,
    _apply_plan,
    apply_npc_intent,
)
from world.rules.surfaces import write_counter_trait

from tools.spec_traceability import covers_requirement


class ExamRegistryIsolation(QuestRegistryIsolation):
    def setUp(self):
        super().setUp()
        register_catalog()
        self._previous_catalog = CATALOG
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        self._previous_offers = list(GUILD_OFFER_REGISTRY.items())

    def tearDown(self):
        import world.rules.guild_config as guild_config
        from world.rules.guild_offers import GUILD_OFFER_REGISTRY

        guild_config.CATALOG = self._previous_catalog
        GUILD_OFFER_REGISTRY.clear()
        GUILD_OFFER_REGISTRY.update(self._previous_offers)
        super().tearDown()


def _exam_intent(target_rank="E"):
    return {"kind": "request_guild_exam", "target_rank": target_rank}


class ExamIntentTests(ExamRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.hall = create_object(Room, key="exam hall")
        self.player = create_object(PlayerCharacter, key="exam player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.hall
        self.staff = create_object(NPC, key="guild staff", location=self.hall)
        self.staff.components.add(
            GuildStaff.create(
                self.staff, service_id="staff", branch_key="guild_branch_altoria"
            )
        )
        self.examiner = create_object(NPC, key="examiner", location=self.hall)
        self.examiner.components.add(
            GuildExaminer.create(
                self.examiner,
                service_id="examiner",
                branch_key="guild_branch_altoria",
            )
        )
        register_adventurer(self.player, self.staff)

    def _give_merit(self, amount):
        write_counter_trait(self.player, "guild_merit", amount)

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_valid_exam_intent_starts_the_exam_with_requested_by_npc_intent(self):
        self._give_merit(50)
        outcome = apply_npc_intent(self.examiner, self.player, _exam_intent("E"))
        self.assertIsInstance(outcome, IntentOutcome)
        self.assertTrue(outcome.applied)
        records = _read_exams(self.player)
        self.assertEqual(records[-1].requested_by, "npc_intent")
        self.assertEqual(records[-1].state, ExamState.ACTIVE)
        self.assertIsNotNone(read_session(self.player))

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_remote_examiner_discards_only_the_intent(self):
        other = create_object(Room, key="elsewhere")
        far = create_object(NPC, key="far examiner", location=other)
        far.components.add(
            GuildExaminer.create(far, service_id="far", branch_key="guild_branch_altoria")
        )
        self._give_merit(50)
        outcome = apply_npc_intent(far, self.player, _exam_intent("E"))
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "remote_examiner")
        self.assertEqual(_read_exams(self.player), [])
        self.assertIsNone(read_session(self.player))
        self.assertEqual(self.player.guild_rank, "F")

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_wrong_branch_examiner_discards_only_the_intent(self):
        examiner = create_object(NPC, key="other branch examiner", location=self.hall)
        examiner.components.add(
            GuildExaminer.create(
                examiner, service_id="other", branch_key="guild_branch_elsewhere"
            )
        )
        self._give_merit(50)
        outcome = apply_npc_intent(examiner, self.player, _exam_intent("E"))
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "wrong_branch")
        self.assertEqual(_read_exams(self.player), [])
        self.assertIsNone(read_session(self.player))

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_wrong_next_rank_discards_only_the_intent(self):
        self._give_merit(150)
        outcome = apply_npc_intent(self.examiner, self.player, _exam_intent("D"))
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "not_next_rank")
        self.assertEqual(_read_exams(self.player), [])
        self.assertIsNone(read_session(self.player))

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_below_merit_threshold_discards_only_the_intent(self):
        outcome = apply_npc_intent(self.examiner, self.player, _exam_intent("E"))
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "below_threshold")
        self.assertEqual(_read_exams(self.player), [])
        self.assertIsNone(read_session(self.player))

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_active_exam_discards_only_the_intent(self):
        self._give_merit(50)
        first = apply_npc_intent(self.examiner, self.player, _exam_intent("E"))
        self.assertTrue(first.applied)
        second = apply_npc_intent(self.examiner, self.player, _exam_intent("E"))
        self.assertFalse(second.applied)
        self.assertEqual(second.reason, "active_combat")
        records = _read_exams(self.player)
        self.assertEqual(len(records), 1)

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_malformed_exam_payload_is_rejected_without_state_change(self):
        for intent in (
            {"kind": "request_guild_exam"},
            {"kind": "request_guild_exam", "target_rank": "E", "extra": 1},
            {"kind": "request_guild_exam", "target_rank": ""},
        ):
            with self.subTest(intent=intent):
                outcome = apply_npc_intent(self.examiner, self.player, intent)
                self.assertFalse(outcome.applied)
                self.assertIsNotNone(outcome.reason)
                self.assertEqual(_read_exams(self.player), [])

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_unknown_kind_is_rejected_defensively(self):
        outcome = apply_npc_intent(self.examiner, self.player, {"kind": "bogus"})
        self.assertFalse(outcome.applied)
        self.assertIn("unknown intent kind", outcome.reason)

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_malformed_registration_failure_propagates_loudly(self):
        self._give_merit(50)
        self.player.db.guild_registration = {"branch_key": 123}
        with self.assertRaises(GuildDataError):
            apply_npc_intent(self.examiner, self.player, _exam_intent("E"))
        self.assertEqual(_read_exams(self.player), [])
        self.assertIsNone(read_session(self.player))

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_none_intent_is_an_applied_noop(self):
        outcome = apply_npc_intent(self.examiner, self.player, {"kind": "none"})
        self.assertTrue(outcome.applied)
        self.assertEqual(_read_exams(self.player), [])
        self.assertIsNone(read_session(self.player))


class ItemIntentTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="transfer room")
        self.player = create_object(PlayerCharacter, key="transfer player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.npc = create_object(NPC, key="giver npc", location=self.room)

    def _give_intent(self, item_key="healing_potion", qty=1):
        return {"kind": "give_item", "item_key": item_key, "qty": qty}

    def _take_intent(self, item_key="healing_potion", qty=1):
        return {"kind": "take_item", "item_key": item_key, "qty": qty}

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_give_item_transfers_verified_holdings_to_the_player(self):
        self.npc.db.inventory = ["healing_potion", "healing_potion"]
        self.player.db.inventory = []
        outcome = apply_npc_intent(self.npc, self.player, self._give_intent(qty=2))
        self.assertTrue(outcome.applied)
        self.assertEqual(list(self.npc.db.inventory), [])
        self.assertEqual(list(self.player.db.inventory), ["healing_potion", "healing_potion"])

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_take_item_transfers_verified_holdings_to_the_npc(self):
        self.player.db.inventory = ["iron_ore", "iron_ore", "iron_ore"]
        self.npc.db.inventory = []
        outcome = apply_npc_intent(self.npc, self.player, self._take_intent("iron_ore", 2))
        self.assertTrue(outcome.applied)
        self.assertEqual(list(self.player.db.inventory), ["iron_ore"])
        self.assertEqual(list(self.npc.db.inventory), ["iron_ore", "iron_ore"])

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_unverifiable_item_intent_changes_no_inventory(self):
        self.npc.db.inventory = ["healing_potion"]
        self.player.db.inventory = []
        outcome = apply_npc_intent(self.npc, self.player, self._give_intent(qty=2))
        self.assertFalse(outcome.applied)
        self.assertEqual(list(self.npc.db.inventory), ["healing_potion"])
        self.assertEqual(list(self.player.db.inventory), [])

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_pathological_qty_is_rejected_before_any_transfer_work(self):
        self.npc.db.inventory = ["healing_potion"]
        self.player.db.inventory = []
        outcome = apply_npc_intent(self.npc, self.player, self._give_intent(qty=10**9))
        self.assertFalse(outcome.applied)
        self.assertIn("does not hold", outcome.reason)
        self.assertEqual(list(self.npc.db.inventory), ["healing_potion"])
        self.assertEqual(list(self.player.db.inventory), [])

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_invalid_item_payload_is_rejected_without_state_change(self):
        self.npc.db.inventory = ["healing_potion"]
        self.player.db.inventory = []
        for intent in (
            {"kind": "give_item", "item_key": "healing_potion"},
            {"kind": "give_item", "item_key": "", "qty": 1},
            {"kind": "give_item", "item_key": "healing_potion", "qty": 0},
            {"kind": "give_item", "item_key": "healing_potion", "qty": "1"},
        ):
            with self.subTest(intent=intent):
                outcome = apply_npc_intent(self.npc, self.player, intent)
                self.assertFalse(outcome.applied)
                self.assertEqual(list(self.npc.db.inventory), ["healing_potion"])
                self.assertEqual(list(self.player.db.inventory), [])

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_second_side_transfer_failure_rolls_back_both_entities(self):
        self.npc.db.inventory = ["healing_potion"]
        self.player.db.inventory = []
        npc_before = list(self.npc.db.inventory)
        player_before = list(self.player.db.inventory)
        calls = {"n": 0}

        def flaky_apply(plan):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("second-side apply failure")
            return _apply_plan(plan)

        with patch("world.rules.npc_intents._apply_plan", side_effect=flaky_apply):
            outcome = apply_npc_intent(self.npc, self.player, self._give_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(calls["n"], 2)
        self.assertEqual(list(self.npc.db.inventory), npc_before)
        self.assertEqual(list(self.player.db.inventory), player_before)
        self.assertEqual(self._db_inventory(self.npc), npc_before)
        self.assertEqual(self._db_inventory(self.player), player_before)

    @staticmethod
    def _db_inventory(entity):
        entity.attributes.reset_cache()
        return list(entity.db.inventory or [])

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_forward_declared_kinds_are_rejected_with_no_state_change(self):
        for kind in ("offer_quest", "reveal_lore"):
            with self.subTest(kind=kind):
                outcome = apply_npc_intent(self.npc, self.player, {"kind": kind})
                self.assertFalse(outcome.applied)
                self.assertIn("no deterministic capability surface yet", outcome.reason)

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_non_mapping_intent_is_rejected(self):
        outcome = apply_npc_intent(self.npc, self.player, "not-a-dict")
        self.assertFalse(outcome.applied)


class AdjustRelationIntentTests(EvenniaTest):
    """The adjust_relation intent routes through the sole affinity writer."""

    def setUp(self):
        super().setUp()
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


class PartyInviteIntentTests(EvenniaTest):
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
        outcome = apply_npc_intent(far, self.player, self._invite_intent(True))
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


class AcquireRollbackTests(QuestRegistryIsolation, EvenniaTest):
    """A second-side ACQUIRE failure restores both entities' quest surfaces too."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="acquire rollback room")
        self.player = create_object(PlayerCharacter, key="acquire player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.npc = create_object(NPC, key="acquire giver", location=self.room)
        definition = _register_quest(
            _quest(
                "potions_please",
                stages=(QuestStage(0, _acquire("healing_potion", quantity=2)),),
            )
        )
        accept_quest(self.player, definition.key)
        self.quest_id = f"{definition.key}:1"

    def _snapshot(self):
        return {
            "npc_inventory": list(self.npc.db.inventory or []),
            "player_inventory": list(self.player.db.inventory or []),
            "player_quest_log": list(self.player.db.quest_log or []),
        }

    @staticmethod
    def _db_inventory(entity):
        entity.attributes.reset_cache()
        return list(entity.db.inventory or [])

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_second_side_acquire_failure_rolls_back_quest_log_and_inventories(self):
        self.npc.db.inventory = ["healing_potion", "healing_potion"]
        self.player.db.inventory = []
        before = self._snapshot()
        records_before = read_records(self.player)
        self.assertEqual(records_before[0].state, QuestState.IN_PROGRESS)
        self.assertEqual(records_before[0].stage_progress, 0)

        with patch(
            "world.quests.transitions.apply_quest_log_delta",
            side_effect=RuntimeError("acquire apply failure"),
        ):
            outcome = apply_npc_intent(
                self.npc, self.player, self._give_intent(qty=2)
            )
        self.assertFalse(outcome.applied)
        self.assertEqual(self._snapshot(), before)
        self.assertEqual(self._db_inventory(self.npc), before["npc_inventory"])
        self.assertEqual(self._db_inventory(self.player), before["player_inventory"])
        records_after = read_records(self.player)
        self.assertEqual(records_after[0].state, QuestState.IN_PROGRESS)
        self.assertEqual(records_after[0].stage_progress, 0)
        self.assertEqual(list(self.player.db.quest_log or []), before["player_quest_log"])

    def _give_intent(self, item_key="healing_potion", qty=1):
        return {"kind": "give_item", "item_key": item_key, "qty": qty}


class ApplierBoundaryTests(unittest.TestCase):
    @covers_requirement("npc-dialogue::the-generative-dialogue-layer-preserves-the-transport-and-single-writer-boundaries")
    def test_applier_source_has_no_generative_import(self):
        from world.rules import npc_intents

        source = inspect.getsource(npc_intents)
        self.assertNotIn("world.ai", source)
        self.assertNotIn("import ollama", source.lower())
        self.assertNotIn("llm_client", source.lower())

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_adjust_relation_delegates_only_through_the_affinity_writer(self):
        from world.rules import npc_intents

        source = inspect.getsource(npc_intents)
        self.assertIn(
            "from world.rules.affinity import apply_affinity_change", source
        )


if __name__ == "__main__":
    unittest.main()
