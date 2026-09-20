"""Slice of ``test_npc_intents``: AcquireRollbackTests, ApplierBoundaryTests.
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
