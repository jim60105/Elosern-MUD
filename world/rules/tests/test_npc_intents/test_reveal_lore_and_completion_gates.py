"""Slice of ``test_npc_intents``: RevealLoreIntentTests, CompletionGateTests.
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
    T_ITEM,
)


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
