"""Tests for DELIVER quest objectives, transfer observer, and atomic progress."""

import unittest
from unittest.mock import patch

from django.db import transaction
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import (
    DestinationKind,
    ObjectiveKind,
    QuestDefinitionError,
    QuestObjective,
    QuestStage,
    RoomLocator,
    register_quest_definition,
)
from world.quests.deliver import compute_deliver_replacement
from world.quests.describe import QuestDescribeError, describe_objective
from world.quests.runtime import QuestState, read_records
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    anchor_locator,
    deliver,
    quest,
    register,
    register_catalog_once,
)
from world.rules.npc_intents import _transfer_items, apply_npc_intent


class DeliverDefinitionTests(QuestRegistryIsolation, EvenniaTest):
    """Validation contract for DELIVER quest objectives."""

    def setUp(self):
        super().setUp()
        register_catalog_once()

    @covers_requirement("quest-delivery::deliver-is-a-closed-transfer-backed-quest-objective")
    def test_valid_deliver_objective_registers_and_starts_at_zero(self):
        definition = register(
            quest(
                "deliver_valid",
                stages=(QuestStage(0, deliver("healing_potion", quantity=2)),),
            )
        )
        player = create_object(PlayerCharacter, key="deliver player")
        record = accept(player, definition.key)
        self.assertEqual(record.stage_progress, 0)
        self.assertEqual(record.state, QuestState.IN_PROGRESS)

    @covers_requirement("quest-delivery::deliver-is-a-closed-transfer-backed-quest-objective")
    def test_deliver_rejects_unregistered_item_key(self):
        bad_objective = QuestObjective(
            kind=ObjectiveKind.DELIVER,
            quantity=1,
            item_key="nonexistent_item_xyz",
            requires_bound_targets=True,
        )
        bad_definition = quest("deliver_bad_item", stages=(QuestStage(0, bad_objective),))
        with self.assertRaises(QuestDefinitionError) as ctx:
            register_quest_definition(bad_definition)
        self.assertIn("item_key", str(ctx.exception))

    @covers_requirement("quest-delivery::deliver-is-a-closed-transfer-backed-quest-objective")
    def test_deliver_rejects_non_positive_quantity(self):
        for qty in (0, -1, True, False):
            bad_objective = QuestObjective(
                kind=ObjectiveKind.DELIVER,
                quantity=qty,
                item_key="healing_potion",
                requires_bound_targets=True,
            )
            bad_definition = quest(f"deliver_bad_qty_{qty}", stages=(QuestStage(0, bad_objective),))
            with self.subTest(quantity=qty):
                with self.assertRaises(QuestDefinitionError) as ctx:
                    register_quest_definition(bad_definition)
                self.assertIn("quantity", str(ctx.exception))

    @covers_requirement("quest-delivery::deliver-is-a-closed-transfer-backed-quest-objective")
    def test_deliver_rejects_unbound_targets(self):
        for val in (False, None, 1, "yes"):
            bad_objective = QuestObjective(
                kind=ObjectiveKind.DELIVER,
                quantity=1,
                item_key="healing_potion",
                requires_bound_targets=val,
            )
            bad_definition = quest("deliver_unbound", stages=(QuestStage(0, bad_objective),))
            with self.subTest(requires_bound_targets=val):
                with self.assertRaises(QuestDefinitionError) as ctx:
                    register_quest_definition(bad_definition)
                self.assertIn("requires_bound_targets", str(ctx.exception))

    @covers_requirement("quest-delivery::deliver-is-a-closed-transfer-backed-quest-objective")
    def test_deliver_rejects_supplied_destination(self):
        bad_objective = QuestObjective(
            kind=ObjectiveKind.DELIVER,
            quantity=1,
            item_key="healing_potion",
            requires_bound_targets=True,
            destination=anchor_locator(),
        )
        bad_definition = quest("deliver_dest", stages=(QuestStage(0, bad_objective),))
        with self.assertRaises(QuestDefinitionError) as ctx:
            register_quest_definition(bad_definition)
        self.assertIn("destination", str(ctx.exception))

    @covers_requirement("quest-delivery::deliver-is-a-closed-transfer-backed-quest-objective")
    def test_deliver_rejects_supplied_monster_tier(self):
        bad_objective = QuestObjective(
            kind=ObjectiveKind.DELIVER,
            quantity=1,
            item_key="healing_potion",
            requires_bound_targets=True,
            monster_tier="low",
        )
        bad_definition = quest("deliver_tier", stages=(QuestStage(0, bad_objective),))
        with self.assertRaises(QuestDefinitionError) as ctx:
            register_quest_definition(bad_definition)
        self.assertIn("monster_tier", str(ctx.exception))


class DeliverBindingTests(QuestRegistryIsolation, EvenniaTest):
    """Binding contract for DELIVER quest objectives."""

    def setUp(self):
        super().setUp()
        register_catalog_once()
        self.room = create_object(Room, key="delivery room")
        self.player = create_object(PlayerCharacter, key="delivery player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.recipient = create_object(NPC, key="target npc", location=self.room)
        self.recipient.race = "human"
        self.recipient.apply_race_baseline()
        self.other_npc = create_object(NPC, key="target npc", location=self.room)
        self.other_npc.race = "human"
        self.other_npc.apply_race_baseline()

        self.definition = register(
            quest(
                "deliver_binding_quest",
                stages=(QuestStage(0, deliver("healing_potion", quantity=1)),),
            )
        )
        self.record = accept(self.player, self.definition.key)
        bind_stage_runtime(
            self.player,
            self.record.quest_id,
            objective_targets=(self.recipient,),
        )

    @covers_requirement("quest-delivery::the-recipient-is-a-runtime-bound-identity-never-a-name")
    def test_transfer_to_bound_recipient_advances_the_objective(self):
        self.player.db.inventory = ["healing_potion"]
        self.recipient.db.inventory = []
        outcome = _transfer_items(self.player, self.recipient, "healing_potion", 1)
        self.assertTrue(outcome.applied)
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.COMPLETED)
        self.assertEqual(record.stage_progress, 1)

    @covers_requirement("quest-delivery::the-recipient-is-a-runtime-bound-identity-never-a-name")
    def test_transfer_to_same_named_unbound_character_does_not_advance(self):
        self.player.db.inventory = ["healing_potion"]
        self.other_npc.db.inventory = []
        outcome = _transfer_items(self.player, self.other_npc, "healing_potion", 1)
        self.assertTrue(outcome.applied)
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(record.stage_progress, 0)


class DeliverProgressTests(QuestRegistryIsolation, EvenniaTest):
    """Progress rules for DELIVER quest objectives."""

    def setUp(self):
        super().setUp()
        register_catalog_once()
        self.room = create_object(Room, key="progress room")
        self.player = create_object(PlayerCharacter, key="progress player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.recipient = create_object(NPC, key="progress recipient", location=self.room)
        self.recipient.race = "human"
        self.recipient.apply_race_baseline()

        self.definition = register(
            quest(
                "deliver_progress_quest",
                stages=(QuestStage(0, deliver("healing_potion", quantity=2)),),
            )
        )
        self.record = accept(self.player, self.definition.key)
        bind_stage_runtime(
            self.player,
            self.record.quest_id,
            objective_targets=(self.recipient,),
        )

    @covers_requirement("quest-delivery::delivery-progress-comes-only-from-a-committed-transfer-to-the-bound-recipient")
    def test_giver_side_transfer_advances_matching_objective(self):
        self.player.db.inventory = ["healing_potion", "healing_potion"]
        self.recipient.db.inventory = []
        outcome = _transfer_items(self.player, self.recipient, "healing_potion", 1)
        self.assertTrue(outcome.applied)
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(record.stage_progress, 1)

    @covers_requirement("quest-delivery::delivery-progress-comes-only-from-a-committed-transfer-to-the-bound-recipient")
    def test_transferring_wrong_item_advances_nothing(self):
        self.player.db.inventory = ["iron_ore"]
        self.recipient.db.inventory = []
        outcome = _transfer_items(self.player, self.recipient, "iron_ore", 1)
        self.assertTrue(outcome.applied)
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(record.stage_progress, 0)

    @covers_requirement("quest-delivery::delivery-progress-comes-only-from-a-committed-transfer-to-the-bound-recipient")
    def test_receiving_rather_than_giving_advances_nothing(self):
        self.recipient.db.inventory = ["healing_potion"]
        self.player.db.inventory = []
        outcome = _transfer_items(self.recipient, self.player, "healing_potion", 1)
        self.assertTrue(outcome.applied)
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(record.stage_progress, 0)

    @covers_requirement("quest-progress-tracking::stage-completion-advances-exactly-once-and-releases-obsolete-runtime-bindings")
    def test_oversized_transfer_advances_once_with_progress_capped_and_no_surplus(self):
        self.player.db.inventory = ["healing_potion"] * 5
        self.recipient.db.inventory = []
        outcome = _transfer_items(self.player, self.recipient, "healing_potion", 5)
        self.assertTrue(outcome.applied)
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.COMPLETED)
        self.assertEqual(record.stage_progress, 2)
        self.assertEqual(record.objective_target_ids, ())

    @covers_requirement("quest-progress-tracking::stage-completion-advances-exactly-once-and-releases-obsolete-runtime-bindings")
    def test_terminal_record_ignores_later_matching_transfer(self):
        self.player.db.inventory = ["healing_potion"] * 3
        self.recipient.db.inventory = []
        # Complete the quest
        _transfer_items(self.player, self.recipient, "healing_potion", 2)
        completed_record = read_records(self.player)[0]
        self.assertEqual(completed_record.state, QuestState.COMPLETED)

        # Transfer one more item to the former recipient
        outcome = _transfer_items(self.player, self.recipient, "healing_potion", 1)
        self.assertTrue(outcome.applied)
        after_record = read_records(self.player)[0]
        self.assertEqual(after_record, completed_record)


class DeliverPurityAndAtomicityTests(QuestRegistryIsolation, EvenniaTest):
    """Purity of observer and atomicity of transfer with rollback."""

    def setUp(self):
        super().setUp()
        register_catalog_once()
        self.room = create_object(Room, key="atomicity room")
        self.player = create_object(PlayerCharacter, key="atomicity player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.recipient = create_object(NPC, key="atomicity recipient", location=self.room)
        self.recipient.race = "human"
        self.recipient.apply_race_baseline()

        self.definition = register(
            quest(
                "deliver_atomicity_quest",
                stages=(QuestStage(0, deliver("healing_potion", quantity=2)),),
            )
        )
        self.record = accept(self.player, self.definition.key)
        bind_stage_runtime(
            self.player,
            self.record.quest_id,
            objective_targets=(self.recipient,),
        )

    @covers_requirement("quest-delivery::the-delivery-observer-computes-a-replacement-and-writes-nothing")
    def test_observer_computes_replacement_without_writing(self):
        before_inventory = list(self.player.db.inventory or [])
        before_log = [dict(entry) for entry in (self.player.db.quest_log or [])]

        result = compute_deliver_replacement(self.player, self.recipient, "healing_potion", 1)
        self.assertIsNotNone(result)
        new_records, pin_ops = result
        self.assertEqual(new_records[0].stage_progress, 1)

        # The player's actual attributes remain unchanged
        self.assertEqual(list(self.player.db.inventory or []), before_inventory)
        self.assertEqual([dict(entry) for entry in (self.player.db.quest_log or [])], before_log)
        self.assertEqual(read_records(self.player)[0].stage_progress, 0)

    @covers_requirement("quest-delivery::the-delivery-observer-computes-a-replacement-and-writes-nothing")
    def test_fault_injected_transfer_restores_quest_log_and_inventories(self):
        self.player.db.inventory = ["healing_potion", "healing_potion"]
        self.recipient.db.inventory = []
        player_before = list(self.player.db.inventory)
        recipient_before = list(self.recipient.db.inventory)
        log_before = [dict(entry) for entry in (self.player.db.quest_log or [])]

        def failing_apply(plan):
            if plan.entity == self.recipient:
                raise RuntimeError("simulated recipient failure")
            from world.rules.npc_intents import _apply_plan
            return _apply_plan(plan)

        with patch("world.rules.npc_intents._apply_plan", side_effect=failing_apply):
            outcome = _transfer_items(self.player, self.recipient, "healing_potion", 1)

        self.assertFalse(outcome.applied)
        self.assertEqual(list(self.player.db.inventory), player_before)
        self.assertEqual(list(self.recipient.db.inventory), recipient_before)
        self.assertEqual([dict(entry) for entry in (self.player.db.quest_log or [])], log_before)
        self.assertEqual(read_records(self.player)[0].stage_progress, 0)

    @covers_requirement("quest-delivery::the-delivery-observer-computes-a-replacement-and-writes-nothing")
    def test_successful_transfer_schedules_delivery_progress_event(self):
        self.player.db.inventory = ["healing_potion"]
        self.recipient.db.inventory = []

        with (
            patch("world.quests.deliver.log_info") as mock_log,
            self.captureOnCommitCallbacks(execute=True),
        ):
            outcome = _transfer_items(self.player, self.recipient, "healing_potion", 1)

        self.assertTrue(outcome.applied)
        mock_log.assert_called_once_with(
            "delivery_progress",
            context={
                "char": str(self.player.pk),
                "quest": self.definition.key,
                "step": "0",
            },
        )

    @covers_requirement("quest-delivery::the-delivery-observer-computes-a-replacement-and-writes-nothing")
    def test_rolled_back_transfer_does_not_emit_delivery_progress_event(self):
        self.player.db.inventory = ["healing_potion"]
        self.recipient.db.inventory = []

        def failing_apply(plan):
            raise RuntimeError("injected failure")

        with (
            patch("world.quests.deliver.log_info") as mock_log,
            patch("world.rules.npc_intents._apply_plan", side_effect=failing_apply),
            self.captureOnCommitCallbacks(execute=True),
        ):
            outcome = _transfer_items(self.player, self.recipient, "healing_potion", 1)

        self.assertFalse(outcome.applied)
        mock_log.assert_not_called()


class DeliverProseTests(unittest.TestCase):
    """Prose rendering contract for DELIVER quest objectives."""

    @covers_requirement("quest-delivery::a-delivery-objective-renders-player-facing-prose-from-the-registries")
    def test_deliver_objective_renders_traditional_chinese_prose(self):
        objective = QuestObjective(
            kind=ObjectiveKind.DELIVER,
            quantity=3,
            item_key="healing_potion",
            requires_bound_targets=True,
        )
        prose = describe_objective(objective)
        self.assertEqual(prose, "交付 3 個治療藥水")

    @covers_requirement("quest-delivery::a-delivery-objective-renders-player-facing-prose-from-the-registries")
    def test_deliver_objective_with_unknown_item_raises(self):
        objective = QuestObjective(
            kind=ObjectiveKind.DELIVER,
            quantity=1,
            item_key="unknown_item_xyz",
            requires_bound_targets=True,
        )
        with self.assertRaises(QuestDescribeError):
            describe_objective(objective)


if __name__ == "__main__":
    unittest.main()
