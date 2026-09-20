"""Slice of ``test_npc_intents``: ExamIntentTests, ItemIntentTests.
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


from ._support import (
    BRANCH,
    ExamRegistryIsolation,
    T_ITEM,
    _exam_intent,
)


class ExamIntentTests(ExamRegistryIsolation, EvenniaTestCase):
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
                self.staff, service_id="staff", branch_key=BRANCH
            )
        )
        self.examiner = create_object(NPC, key="examiner", location=self.hall)
        self.examiner.components.add(
            GuildExaminer.create(
                self.examiner,
                service_id="examiner",
                branch_key=BRANCH,
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
            GuildExaminer.create(far, service_id="far", branch_key=BRANCH)
        )
        self._give_merit(50)
        # The completion gate is bypassed so this test exercises the exam
        # gate's own remote-examiner check: the gate is the first line of
        # defense and per-kind domain checks stay in force below it (F22).
        outcome = apply_npc_intent(
            far, self.player, _exam_intent("E"), context_ok=lambda npc, player: True
        )
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
                examiner, service_id="other", branch_key="t_other_branch"
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


class ItemIntentTests(EvenniaTestCase):
    def setUp(self):
        # Transferred item identities validate against the kit potion row.
        open_synthetic_scope(self, "items")
        super().setUp()
        self.room = create_object(Room, key="transfer room")
        self.player = create_object(PlayerCharacter, key="transfer player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.npc = create_object(NPC, key="giver npc", location=self.room)

    def _give_intent(self, item_key=T_ITEM, qty=1):
        return {"kind": "give_item", "item_key": item_key, "qty": qty}

    def _take_intent(self, item_key=T_ITEM, qty=1):
        return {"kind": "take_item", "item_key": item_key, "qty": qty}

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_give_item_transfers_verified_holdings_to_the_player(self):
        self.npc.db.inventory = [T_ITEM, T_ITEM]
        self.player.db.inventory = []
        outcome = apply_npc_intent(self.npc, self.player, self._give_intent(qty=2))
        self.assertTrue(outcome.applied)
        self.assertEqual(list(self.npc.db.inventory), [])
        self.assertEqual(list(self.player.db.inventory), [T_ITEM, T_ITEM])

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
        self.npc.db.inventory = [T_ITEM]
        self.player.db.inventory = []
        outcome = apply_npc_intent(self.npc, self.player, self._give_intent(qty=2))
        self.assertFalse(outcome.applied)
        self.assertEqual(list(self.npc.db.inventory), [T_ITEM])
        self.assertEqual(list(self.player.db.inventory), [])

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_pathological_qty_is_rejected_before_any_transfer_work(self):
        self.npc.db.inventory = [T_ITEM]
        self.player.db.inventory = []
        outcome = apply_npc_intent(self.npc, self.player, self._give_intent(qty=10**9))
        self.assertFalse(outcome.applied)
        self.assertIn("does not hold", outcome.reason)
        self.assertEqual(list(self.npc.db.inventory), [T_ITEM])
        self.assertEqual(list(self.player.db.inventory), [])

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_invalid_item_payload_is_rejected_without_state_change(self):
        self.npc.db.inventory = [T_ITEM]
        self.player.db.inventory = []
        for intent in (
            {"kind": "give_item", "item_key": T_ITEM},
            {"kind": "give_item", "item_key": "", "qty": 1},
            {"kind": "give_item", "item_key": T_ITEM, "qty": 0},
            {"kind": "give_item", "item_key": T_ITEM, "qty": "1"},
        ):
            with self.subTest(intent=intent):
                outcome = apply_npc_intent(self.npc, self.player, intent)
                self.assertFalse(outcome.applied)
                self.assertEqual(list(self.npc.db.inventory), [T_ITEM])
                self.assertEqual(list(self.player.db.inventory), [])

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_second_side_transfer_failure_rolls_back_both_entities(self):
        self.npc.db.inventory = [T_ITEM]
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
    def test_no_forward_declared_kinds_remain(self):
        from world.rules import npc_intents

        self.assertEqual(npc_intents._FORWARD_DECLARED_KINDS, ())
        outcome = apply_npc_intent(self.npc, self.player, {"kind": "reveal_lore"})
        self.assertFalse(outcome.applied)
        self.assertIn("must carry exactly category and key", outcome.reason)
        self.assertIsNone(self.player.db.lore_discovered)

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_non_mapping_intent_is_rejected(self):
        outcome = apply_npc_intent(self.npc, self.player, "not-a-dict")
        self.assertFalse(outcome.applied)
