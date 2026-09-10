"""Tests for the deterministic NPC intent verifier-and-applier (npc-dialogue).

Covers ``apply_npc_intent``: the ``request_guild_exam`` routing through
``start_guild_exam`` with ``requested_by="npc_intent"``, every failed exam gate
discarding only the intent, the atomic give/take item transfer primitive, the
``adjust_relation`` routing through the sole-writer affinity API with the
applied-amount report, the ``offer_quest`` routing through the issuer-aware
offer surface with its atomic acceptance and rejection paths, the ``reveal_lore``
routing through the lore codex sole writer, and the boundary rule that this
module never imports the generative package.
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

# Intent application runs on kit rows: the exam/offer branch is the kit guild
# branch and transferred items are the kit potion row (scoped registries
# validate them), so no shipped content key is named below.
BRANCH = SYNTH_GUILD_BRANCH_KEY
T_ITEM = SYNTH_ITEMS["t_ember_spray"].key


class ExamRegistryIsolation(QuestRegistryIsolation):
    def setUp(self):
        # Examiner/staff branches resolve against the kit branch row, and the
        # exam path reads the synthetic catalog (invented E-through-S
        # thresholds) instead of the shipped rulebook.
        open_synthetic_scope(self, "guild_branches")
        super().setUp()
        register_catalog()
        install_synthetic_catalog(self, synth_catalog())
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


class OfferQuestIntentTests(ExamRegistryIsolation, EvenniaTestCase):
    """The offer_quest intent routes through the issuer-aware offer surface."""

    ALTORIA_BRANCH = BRANCH

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="offer quest room")
        self.player = create_object(PlayerCharacter, key="offer quest player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.staff = create_object(NPC, key="offer staff", location=self.room)
        self.staff.components.add(
            GuildStaff.create(
                self.staff, service_id="staff", branch_key=self.ALTORIA_BRANCH
            )
        )
        register_adventurer(self.player, self.staff)
        definition = _register_quest(_quest("forest_clearing", rank="F"))
        register_guild_offer(
            GuildQuestOffer(
                definition_key=definition.key,
                issuer_branch_key=self.ALTORIA_BRANCH,
                reward=QuestReward(copper=50, items=(), merit=25),
            )
        )
        self.quest_key = definition.key

    def _offer_intent(self, quest_key="forest_clearing"):
        return {"kind": "offer_quest", "quest_key": quest_key}

    def _affinity(self, player=None):
        return self.staff.relations._load(player or self.player)

    def _records(self):
        return read_records(self.player)

    def _commissioner(self, issuer_key=None):
        name = f"commissioner {issuer_key or 'pk'}"
        commissioner = create_object(NPC, key=name, location=self.room)
        commissioner.components.add(
            QuestIssuer.create(
                commissioner,
                service_id=f"commission-{issuer_key or 'pk'}",
                issuer_key=issuer_key,
            )
        )
        return commissioner

    def _register_commission(self, definition_key, issuer_key):
        issuance = QuestIssuance(
            definition_key=definition_key,
            issuer_key=issuer_key,
            reward=QuestReward(copper=30, items=(), merit=0),
            settlement=Settlement.AUTO,
        )
        register_quest_issuance(issuance)
        return issuance

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-is-assigned-directly-and-atomically")
    def test_verified_offer_assigns_the_quest_and_applies_guild_affinity(self):
        outcome = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertTrue(outcome.applied)
        self.assertEqual(outcome.reason, "quest assigned")
        records = self._records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].definition_key, self.quest_key)
        self.assertEqual(records[0].issuer_key, guild_issuer_key(self.ALTORIA_BRANCH))
        self.assertEqual(records[0].state, QuestState.IN_PROGRESS)
        self.assertEqual(self._affinity().value, 2)

    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-is-assigned-directly-and-atomically")
    def test_capped_affinity_write_commits_the_quest_without_rollback(self):
        from world.rules.affinity import AffinityRecord

        self.staff.db.relations_data = {
            str(self.player.pk): AffinityRecord(
                value=99, cap=99, daily_gain=0, daily_tick=0
            ).to_storage()
        }
        outcome = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertTrue(outcome.applied)
        self.assertIn("capped", outcome.reason)
        records = self._records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].definition_key, self.quest_key)
        self.assertEqual(self._affinity().value, 99)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_non_npc_speaker_is_rejected_without_state_change(self):
        outcome = apply_npc_intent(self.player, self.player, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "offer_quest requires an NPC speaker")
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_speaker_without_guild_staff_is_rejected_without_state_change(self):
        plain = create_object(NPC, key="plain npc", location=self.room)
        outcome = apply_npc_intent(plain, self.player, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, "offer_quest requires a GuildStaff or QuestIssuer speaker"
        )
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_speaker_without_branch_key_is_rejected_without_state_change(self):
        branchless = create_object(NPC, key="branchless staff", location=self.room)
        branchless.components.add(
            GuildStaff.create(branchless, service_id="branchless")
        )
        outcome = apply_npc_intent(branchless, self.player, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, "offer_quest requires a GuildStaff branch_key"
        )
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_unregistered_offer_is_rejected_without_state_change(self):
        outcome = apply_npc_intent(
            self.staff, self.player, self._offer_intent("unregistered_quest")
        )
        self.assertFalse(outcome.applied)
        self.assertIn("no guild offer", outcome.reason)
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_unregistered_player_is_rejected_without_state_change(self):
        other = create_object(PlayerCharacter, key="unregistered player")
        other.race = "human"
        other.apply_race_baseline()
        other.location = self.room
        outcome = apply_npc_intent(self.staff, other, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "actor is not registered")
        self.assertEqual(read_records(other), [])
        self.assertIsNone(self._affinity(other))

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_rankless_player_is_rejected_without_state_change(self):
        self.player.guild_rank = None
        outcome = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, "actor has no guild rank")
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_unknown_player_rank_is_rejected_without_state_change(self):
        self.player.guild_rank = "Z"
        outcome = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertIn("unknown guild rank", outcome.reason)
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_malformed_registration_discards_only_the_intent(self):
        self.player.db.guild_registration = {"branch_key": 123}
        outcome = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertIn("guild_registration", outcome.reason)
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_rank_below_the_quest_band_is_rejected_without_state_change(self):
        definition = _register_quest(_quest("ranked_quest", rank="E"))
        register_guild_offer(
            GuildQuestOffer(
                definition_key=definition.key,
                issuer_branch_key=self.ALTORIA_BRANCH,
                reward=QuestReward(copper=200, items=(), merit=25),
            )
        )
        outcome = apply_npc_intent(
            self.staff, self.player, self._offer_intent(definition.key)
        )
        self.assertFalse(outcome.applied)
        self.assertIn("not rank-eligible", outcome.reason)
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-is-assigned-directly-and-atomically")
    def test_duplicate_quest_rejection_is_delegated_to_the_quest_runtime(self):
        first = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertTrue(first.applied)
        second = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertFalse(second.applied)
        records = self._records()
        self.assertEqual(len(records), 1)
        self.assertEqual(self._affinity().value, 2)

    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-is-assigned-directly-and-atomically")
    def test_injected_commit_failure_restores_quest_log_and_affinity_record(self):
        with patch(
            "world.rules.npc_intents.apply_affinity_change",
            side_effect=RuntimeError("affinity write failure"),
        ):
            outcome = apply_npc_intent(self.staff, self.player, self._offer_intent())
        self.assertFalse(outcome.applied)
        self.assertIn("rolled back", outcome.reason)
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)
        self.staff.attributes.reset_cache()
        self.player.attributes.reset_cache()
        self.assertEqual(list(self.player.db.quest_log or []), [])

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-carries-exactly-one-quest-key-field")
    def test_malformed_offer_payloads_are_rejected_without_state_change(self):
        for intent in (
            {"kind": "offer_quest"},
            {"kind": "offer_quest", "quest_key": ""},
            {"kind": "offer_quest", "quest_key": 3},
            {"kind": "offer_quest", "quest_key": "x", "extra": 1},
            {"kind": "offer_quest", "quest_key": "q" * 65},
        ):
            with self.subTest(intent=intent):
                outcome = apply_npc_intent(self.staff, self.player, intent)
                self.assertFalse(outcome.applied)
                self.assertIsNotNone(outcome.reason)
                self.assertEqual(self._records(), [])
                self.assertEqual(self._affinity().value, 1)

    # -- private commission path (quest-issuance-dialogue-gate) --

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-names-its-issuance-when-assigning")
    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_authorized_commissioner_assigns_its_private_commission(self):
        issuer_key = npc_issuer_key(content_key="grey_granny")
        issuance = self._register_commission(self.quest_key, issuer_key)
        commissioner = self._commissioner("grey_granny")
        unregistered = create_object(PlayerCharacter, key="unregistered seeker")
        unregistered.race = "human"
        unregistered.apply_race_baseline()
        unregistered.location = self.room
        outcome = apply_npc_intent(
            commissioner, unregistered, self._offer_intent(self.quest_key)
        )
        self.assertTrue(outcome.applied)
        self.assertEqual(outcome.reason, "quest assigned")
        records = read_records(unregistered)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].definition_key, self.quest_key)
        self.assertEqual(records[0].issuer_key, issuer_key)
        resolved = resolve_issuance(records[0].definition_key, records[0].issuer_key)
        self.assertEqual(resolved, issuance)
        self.assertEqual(resolved.settlement, Settlement.AUTO)
        self.assertEqual(commissioner.relations._load(unregistered).value, 1)

    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-names-its-issuance-when-assigning")
    def test_identity_form_commissioner_assigns_under_its_primary_key(self):
        commissioner = self._commissioner()
        issuer_key = npc_issuer_key(pk=commissioner.pk)
        issuance = self._register_commission(self.quest_key, issuer_key)
        outcome = apply_npc_intent(
            commissioner, self.player, self._offer_intent(self.quest_key)
        )
        self.assertTrue(outcome.applied)
        records = self._records()
        self.assertEqual(records[0].issuer_key, issuer_key)
        self.assertEqual(resolve_issuance(self.quest_key, issuer_key), issuance)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_commissioner_without_issuance_for_the_key_is_rejected(self):
        commissioner = self._commissioner("grey_granny")
        self._register_commission(
            self.quest_key, npc_issuer_key(content_key="other_commission")
        )
        outcome = apply_npc_intent(
            commissioner, self.player, self._offer_intent(self.quest_key)
        )
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, f"no commission {self.quest_key!r} at this issuer"
        )
        self.assertEqual(self._records(), [])
        self.assertIsNone(commissioner.relations._load(self.player))

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_unauthorized_npc_cannot_issue_even_when_a_commission_exists(self):
        self._register_commission(
            self.quest_key, npc_issuer_key(content_key="grey_granny")
        )
        plain = create_object(NPC, key="plain bystander", location=self.room)
        outcome = apply_npc_intent(plain, self.player, self._offer_intent(self.quest_key))
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, "offer_quest requires a GuildStaff or QuestIssuer speaker"
        )
        self.assertEqual(self._records(), [])
        self.assertIsNone(plain.relations._load(self.player))

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_payload_cannot_reach_another_issuers_commission(self):
        self._register_commission(
            self.quest_key, npc_issuer_key(content_key="grey_granny")
        )
        other = self._commissioner()
        outcome = apply_npc_intent(other, self.player, self._offer_intent(self.quest_key))
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, f"no commission {self.quest_key!r} at this issuer"
        )
        self.assertEqual(self._records(), [])

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_dual_authority_with_both_issuances_fails_verification(self):
        dual = self._commissioner("grey_granny")
        dual.components.add(
            GuildStaff.create(
                dual, service_id="dual-staff", branch_key=self.ALTORIA_BRANCH
            )
        )
        self._register_commission(
            self.quest_key, npc_issuer_key(content_key="grey_granny")
        )
        outcome = apply_npc_intent(dual, self.player, self._offer_intent(self.quest_key))
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason,
            f"quest {self.quest_key!r} is issued under both this branch and this issuer",
        )
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-names-its-issuance-when-assigning")
    def test_dual_authority_resolves_by_the_guild_namespace(self):
        dual = self._commissioner("grey_granny")
        dual.components.add(
            GuildStaff.create(
                dual, service_id="dual-staff", branch_key=self.ALTORIA_BRANCH
            )
        )
        outcome = apply_npc_intent(dual, self.player, self._offer_intent(self.quest_key))
        self.assertTrue(outcome.applied)
        records = self._records()
        self.assertEqual(records[0].issuer_key, guild_issuer_key(self.ALTORIA_BRANCH))
        self.assertEqual(dual.relations._load(self.player).value, 1)

    @covers_requirement("dialogue-offer-quest::a-verified-offer-quest-names-its-issuance-when-assigning")
    def test_dual_authority_resolves_by_the_private_namespace(self):
        dual = self._commissioner("grey_granny")
        dual.components.add(
            GuildStaff.create(
                dual, service_id="dual-staff", branch_key="guild_branch_other"
            )
        )
        issuance = self._register_commission(
            self.quest_key, npc_issuer_key(content_key="grey_granny")
        )
        outcome = apply_npc_intent(dual, self.player, self._offer_intent(self.quest_key))
        self.assertTrue(outcome.applied)
        records = self._records()
        self.assertEqual(
            records[0].issuer_key, npc_issuer_key(content_key="grey_granny")
        )
        self.assertEqual(resolve_issuance(self.quest_key, records[0].issuer_key), issuance)
        self.assertEqual(dual.relations._load(self.player).value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_malformed_authored_issuer_key_is_rejected(self):
        commissioner = self._commissioner("bad:key")
        outcome = apply_npc_intent(
            commissioner, self.player, self._offer_intent(self.quest_key)
        )
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, "offer_quest QuestIssuer carries a malformed issuer_key"
        )
        self.assertEqual(self._records(), [])
        self.assertIsNone(commissioner.relations._load(self.player))

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_malformed_branch_key_is_rejected_without_state_change(self):
        malformed = create_object(NPC, key="malformed staff", location=self.room)
        malformed.components.add(
            GuildStaff.create(
                malformed, service_id="malformed-staff", branch_key="bad:branch"
            )
        )
        outcome = apply_npc_intent(malformed, self.player, self._offer_intent(self.quest_key))
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, "offer_quest GuildStaff carries a malformed branch_key"
        )
        self.assertEqual(self._records(), [])
        self.assertEqual(self._affinity().value, 1)

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_malformed_issuer_key_fails_closed_over_a_valid_guild_offer(self):
        dual = self._commissioner("bad:key")
        dual.components.add(
            GuildStaff.create(
                dual, service_id="dual-staff", branch_key=self.ALTORIA_BRANCH
            )
        )
        outcome = apply_npc_intent(dual, self.player, self._offer_intent(self.quest_key))
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, "offer_quest QuestIssuer carries a malformed issuer_key"
        )
        self.assertEqual(self._records(), [])
        self.assertIsNone(dual.relations._load(self.player))

    @covers_requirement("dialogue-offer-quest::the-offer-quest-intent-is-verified-against-the-registered-guild-offer-surface")
    def test_malformed_branch_key_fails_closed_over_a_valid_commission(self):
        dual = self._commissioner("grey_granny")
        self._register_commission(
            self.quest_key, npc_issuer_key(content_key="grey_granny")
        )
        dual.components.add(
            GuildStaff.create(
                dual, service_id="dual-staff", branch_key="bad:branch"
            )
        )
        outcome = apply_npc_intent(dual, self.player, self._offer_intent(self.quest_key))
        self.assertFalse(outcome.applied)
        self.assertEqual(
            outcome.reason, "offer_quest GuildStaff carries a malformed branch_key"
        )
        self.assertEqual(self._records(), [])
        self.assertIsNone(dual.relations._load(self.player))


class RevealLoreIntentTests(EvenniaTestCase):
    """The reveal_lore intent records discoveries through the codex writer."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="lore intent room")
        self.player = create_object(PlayerCharacter, key="lore intent player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.npc = create_object(NPC, key="lore intent npc", location=self.room)

    def _reveal_intent(self, category="race", key="elf"):
        return {"kind": "reveal_lore", "category": category, "key": key}

    def _discovered(self):
        return set(self.player.db.lore_discovered or ())

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_verified_reveal_records_the_discovery(self):
        outcome = apply_npc_intent(self.npc, self.player, self._reveal_intent())
        self.assertTrue(outcome.applied)
        self.assertEqual(self._discovered(), {"race:elf"})

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_reveal_grants_no_affinity(self):
        apply_npc_intent(self.npc, self.player, self._reveal_intent())
        self.assertIsNone(self.npc.relations._load(self.player))

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_repeat_reveal_is_an_applied_no_op(self):
        first = apply_npc_intent(self.npc, self.player, self._reveal_intent())
        second = apply_npc_intent(self.npc, self.player, self._reveal_intent())
        self.assertTrue(first.applied)
        self.assertTrue(second.applied)
        self.assertEqual(self._discovered(), {"race:elf"})

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_unknown_category_discards_only_the_intent(self):
        outcome = apply_npc_intent(self.npc, self.player, self._reveal_intent("bogus"))
        self.assertFalse(outcome.applied)
        self.assertIn("unknown lore category", outcome.reason)
        self.assertEqual(self._discovered(), set())

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_unresolvable_key_discards_only_the_intent(self):
        outcome = apply_npc_intent(
            self.npc, self.player, self._reveal_intent("race", "bogus")
        )
        self.assertFalse(outcome.applied)
        self.assertIn("no lore entry", outcome.reason)
        self.assertEqual(self._discovered(), set())

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_malformed_reveal_payloads_are_rejected_without_state_change(self):
        for intent in (
            {"kind": "reveal_lore"},
            {"kind": "reveal_lore", "category": "race"},
            {"kind": "reveal_lore", "category": "", "key": "elf"},
            {"kind": "reveal_lore", "category": "race", "key": 3},
            {"kind": "reveal_lore", "category": "race", "key": "elf", "extra": 1},
            {"kind": "reveal_lore", "category": "c" * 65, "key": "elf"},
            {"kind": "reveal_lore", "category": "race", "key": "k" * 65},
        ):
            with self.subTest(intent=intent):
                outcome = apply_npc_intent(self.npc, self.player, intent)
                self.assertFalse(outcome.applied)
                self.assertIsNotNone(outcome.reason)
                self.assertEqual(self._discovered(), set())

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_64_code_point_boundary_passes_the_applier_shape_check(self):
        bound = "k" * 64
        outcome = apply_npc_intent(
            self.npc, self.player, self._reveal_intent("race", bound)
        )
        self.assertFalse(outcome.applied)
        self.assertIn("no lore entry", outcome.reason)
        self.assertEqual(self._discovered(), set())

    @covers_requirement("npc-dialogue::intent-application-is-deterministic-verified-and-non-escalating")
    def test_persistence_failure_discards_only_the_intent(self):
        def flaky_writer(*args, **kwargs):
            raise RuntimeError("attribute write failure")

        with patch("world.rules.lore_knowledge.record_lore_reveal", side_effect=flaky_writer):
            outcome = apply_npc_intent(self.npc, self.player, self._reveal_intent())
        self.assertFalse(outcome.applied)
        self.assertIn("failed and was discarded", outcome.reason)
        self.assertIsNone(self.player.db.lore_discovered)


class CompletionGateTests(EvenniaTestCase):
    """The completion gate drops intents after separation or busy transitions.

    The gate is the canonical ``intent_context_ok`` predicate -- co-location
    of the pair and a talk-interactable NPC -- evaluated inside
    ``apply_npc_intent`` at application time, so an async exchange that
    settled after the player or the NPC left the room, or after a
    schedule-driven state transition, reads canonical state and skips the
    intent (audit F22).
    """

    def setUp(self):
        # Gate checks transfer kit-row item identities.
        open_synthetic_scope(self, "items")
        super().setUp()
        self.room = create_object(Room, key="gate room")
        self.other = create_object(Room, key="gate other room")
        self.player = create_object(PlayerCharacter, key="gate player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.npc = create_object(NPC, key="gate npc", location=self.room)

    def _give_intent(self):
        return {"kind": "give_item", "item_key": T_ITEM, "qty": 1}

    def _take_intent(self):
        return {"kind": "take_item", "item_key": T_ITEM, "qty": 1}

    def _relation_intent(self, delta=3):
        return {"kind": "adjust_relation", "delta": delta}

    def _lore_intent(self):
        return {"kind": "reveal_lore", "category": "race", "key": "elf"}

    @covers_requirement("npc-dialogue::async-dialogue-intents-revalidate-context-at-completion")
    def test_give_intent_is_dropped_after_separation(self):
        self.npc.db.inventory = [T_ITEM]
        self.npc.location = self.other
        outcome = apply_npc_intent(self.npc, self.player, self._give_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, STALE_CONTEXT_REASON)
        self.assertTrue(is_stale_context(outcome))
        self.assertEqual(list(self.npc.db.inventory), [T_ITEM])
        self.assertEqual(list(self.player.db.inventory or []), [])

    @covers_requirement("npc-dialogue::async-dialogue-intents-revalidate-context-at-completion")
    def test_take_intent_is_dropped_when_the_player_left(self):
        self.player.db.inventory = [T_ITEM]
        self.player.location = self.other
        outcome = apply_npc_intent(self.npc, self.player, self._take_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, STALE_CONTEXT_REASON)
        self.assertEqual(list(self.player.db.inventory), [T_ITEM])
        self.assertEqual(list(self.npc.db.inventory or []), [])

    @covers_requirement("npc-dialogue::async-dialogue-intents-revalidate-context-at-completion")
    def test_relation_intent_is_dropped_after_a_busy_transition(self):
        self.npc.db.schedule_state = "busy"
        outcome = apply_npc_intent(self.npc, self.player, self._relation_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, STALE_CONTEXT_REASON)
        self.assertIsNone(self.npc.relations._load(self.player))

    @covers_requirement("npc-dialogue::async-dialogue-intents-revalidate-context-at-completion")
    def test_lore_intent_is_dropped_after_a_resting_transition(self):
        self.npc.db.schedule_state = "resting"
        outcome = apply_npc_intent(self.npc, self.player, self._lore_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, STALE_CONTEXT_REASON)
        self.assertIsNone(self.player.db.lore_discovered)

    @covers_requirement("npc-dialogue::async-dialogue-intents-revalidate-context-at-completion")
    def test_co_located_interactive_completion_applies_the_intent(self):
        self.npc.db.inventory = [T_ITEM]
        outcome = apply_npc_intent(self.npc, self.player, self._give_intent())
        self.assertTrue(outcome.applied)
        self.assertFalse(is_stale_context(outcome))
        self.assertEqual(list(self.npc.db.inventory), [])
        self.assertEqual(list(self.player.db.inventory), [T_ITEM])

    @covers_requirement("npc-dialogue::async-dialogue-intents-revalidate-context-at-completion")
    def test_the_gate_reads_canonical_state_at_application_time(self):
        # The predicate is evaluated inside ``apply_npc_intent``, so a
        # schedule-driven move landing mid-exchange (between the pre-call
        # fast path and the intent application) still fails the gate.
        self.npc.db.inventory = [T_ITEM]
        self.assertTrue(intent_context_ok(self.npc, self.player))
        self.npc.location = self.other
        outcome = apply_npc_intent(self.npc, self.player, self._give_intent())
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, STALE_CONTEXT_REASON)
        self.assertEqual(list(self.npc.db.inventory), [T_ITEM])

    @covers_requirement("npc-dialogue::async-dialogue-intents-revalidate-context-at-completion")
    def test_stale_context_party_invite_returns_the_marker_before_join_gates(self):
        # The shared gate applies to ``party_invite`` too: a separated pair
        # gets the stale marker without running ``join_party``'s domain
        # gates, which stay in force once the gate passes (task 3.2).
        self.npc.location = self.other
        outcome = apply_npc_intent(
            self.npc, self.player, {"kind": "party_invite", "accept": True}
        )
        self.assertFalse(outcome.applied)
        self.assertEqual(outcome.reason, STALE_CONTEXT_REASON)
        self.assertIsNone(self.npc.db.party_member)


class AcquireRollbackTests(QuestRegistryIsolation, EvenniaTestCase):
    """A second-side ACQUIRE failure restores both entities' quest surfaces too."""

    def setUp(self):
        # The acquire objective and transfers name the kit potion row.
        open_synthetic_scope(self, "items")
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
                stages=(QuestStage(0, _acquire(T_ITEM, quantity=2)),),
            )
        )
        accept(self.player, definition.key)
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
        self.npc.db.inventory = [T_ITEM, T_ITEM]
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

    def _give_intent(self, item_key=T_ITEM, qty=1):
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
