"""Tests for DELIVER quest objectives, transfer observer, and atomic progress."""

import unittest
from contextlib import ExitStack
from unittest.mock import patch

from world.tests.synthetic_data import SYNTH_ITEMS, synthetic_registries

#: Deliveries run on the kit's synthetic rows: the delivery item and the
#: wrong-item decoy are both catalog-synthetic.
_T_ITEM = SYNTH_ITEMS["t_ember_spray"].key
_T_OTHER = SYNTH_ITEMS["t_iron_fang"].key

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
from world.rules.npc_intents import (
    _transfer_items,
    advance_deliveries_for_transfer,
    apply_npc_intent,
)


@synthetic_registries("items")
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
                stages=(QuestStage(0, deliver(_T_ITEM, quantity=2)),),
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
                item_key=_T_ITEM,
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
                item_key=_T_ITEM,
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
            item_key=_T_ITEM,
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
            item_key=_T_ITEM,
            requires_bound_targets=True,
            monster_tier="low",
        )
        bad_definition = quest("deliver_tier", stages=(QuestStage(0, bad_objective),))
        with self.assertRaises(QuestDefinitionError) as ctx:
            register_quest_definition(bad_definition)
        self.assertIn("monster_tier", str(ctx.exception))


@synthetic_registries("items")
class DeliverBindingTests(QuestRegistryIsolation, EvenniaTest):
    """Binding contract for DELIVER quest objectives."""

    def setUp(self):
        super().setUp()
        # The class decorator wraps test methods only, so the item scope
        # is entered here too: the definition registered below validates
        # its item key against the synthetic registry.
        stack = ExitStack()
        stack.enter_context(synthetic_registries("items"))
        self.addCleanup(stack.close)
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
                stages=(QuestStage(0, deliver(_T_ITEM, quantity=1)),),
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
        self.player.db.inventory = [_T_ITEM]
        self.recipient.db.inventory = []
        outcome = _transfer_items(self.player, self.recipient, _T_ITEM, 1)
        self.assertTrue(outcome.applied)
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.COMPLETED)
        self.assertEqual(record.stage_progress, 1)

    @covers_requirement("quest-delivery::the-recipient-is-a-runtime-bound-identity-never-a-name")
    def test_transfer_to_same_named_unbound_character_does_not_advance(self):
        self.player.db.inventory = [_T_ITEM]
        self.other_npc.db.inventory = []
        outcome = _transfer_items(self.player, self.other_npc, _T_ITEM, 1)
        self.assertTrue(outcome.applied)
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(record.stage_progress, 0)


@synthetic_registries("items")
class DeliverProgressTests(QuestRegistryIsolation, EvenniaTest):
    """Progress rules for DELIVER quest objectives."""

    def setUp(self):
        super().setUp()
        # The class decorator wraps test methods only, so the item scope
        # is entered here too: the definition registered below validates
        # its item key against the synthetic registry.
        stack = ExitStack()
        stack.enter_context(synthetic_registries("items"))
        self.addCleanup(stack.close)
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
                stages=(QuestStage(0, deliver(_T_ITEM, quantity=2)),),
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
        self.player.db.inventory = [_T_ITEM, _T_ITEM]
        self.recipient.db.inventory = []
        outcome = _transfer_items(self.player, self.recipient, _T_ITEM, 1)
        self.assertTrue(outcome.applied)
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(record.stage_progress, 1)

    @covers_requirement("quest-delivery::delivery-progress-comes-only-from-a-committed-transfer-to-the-bound-recipient")
    def test_transferring_wrong_item_advances_nothing(self):
        self.player.db.inventory = [_T_OTHER]
        self.recipient.db.inventory = []
        outcome = _transfer_items(self.player, self.recipient, _T_OTHER, 1)
        self.assertTrue(outcome.applied)
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(record.stage_progress, 0)

    @covers_requirement("quest-delivery::delivery-progress-comes-only-from-a-committed-transfer-to-the-bound-recipient")
    def test_receiving_rather_than_giving_advances_nothing(self):
        self.recipient.db.inventory = [_T_ITEM]
        self.player.db.inventory = []
        outcome = _transfer_items(self.recipient, self.player, _T_ITEM, 1)
        self.assertTrue(outcome.applied)
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        self.assertEqual(record.stage_progress, 0)

    @covers_requirement("quest-progress-tracking::stage-completion-advances-exactly-once-and-releases-obsolete-runtime-bindings")
    def test_oversized_transfer_advances_once_with_progress_capped_and_no_surplus(self):
        self.player.db.inventory = [_T_ITEM] * 5
        self.recipient.db.inventory = []
        outcome = _transfer_items(self.player, self.recipient, _T_ITEM, 5)
        self.assertTrue(outcome.applied)
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.COMPLETED)
        self.assertEqual(record.stage_progress, 2)
        self.assertEqual(record.objective_target_ids, ())

    @covers_requirement("quest-progress-tracking::stage-completion-advances-exactly-once-and-releases-obsolete-runtime-bindings")
    def test_terminal_record_ignores_later_matching_transfer(self):
        self.player.db.inventory = [_T_ITEM] * 3
        self.recipient.db.inventory = []
        # Complete the quest
        _transfer_items(self.player, self.recipient, _T_ITEM, 2)
        completed_record = read_records(self.player)[0]
        self.assertEqual(completed_record.state, QuestState.COMPLETED)

        # Transfer one more item to the former recipient
        outcome = _transfer_items(self.player, self.recipient, _T_ITEM, 1)
        self.assertTrue(outcome.applied)
        after_record = read_records(self.player)[0]
        self.assertEqual(after_record, completed_record)


@synthetic_registries("items")
class DeliverPurityAndAtomicityTests(QuestRegistryIsolation, EvenniaTest):
    """Purity of observer and atomicity of transfer with rollback."""

    def setUp(self):
        super().setUp()
        # The class decorator wraps test methods only, so the item scope
        # is entered here too: the definition registered below validates
        # its item key against the synthetic registry.
        stack = ExitStack()
        stack.enter_context(synthetic_registries("items"))
        self.addCleanup(stack.close)
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
                stages=(QuestStage(0, deliver(_T_ITEM, quantity=2)),),
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

        result = compute_deliver_replacement(self.player, self.recipient, _T_ITEM, 1)
        self.assertIsNotNone(result)
        new_records, pin_ops = result
        self.assertEqual(new_records[0].stage_progress, 1)

        # The player's actual attributes remain unchanged
        self.assertEqual(list(self.player.db.inventory or []), before_inventory)
        self.assertEqual([dict(entry) for entry in (self.player.db.quest_log or [])], before_log)
        self.assertEqual(read_records(self.player)[0].stage_progress, 0)

    @covers_requirement("quest-delivery::the-delivery-observer-computes-a-replacement-and-writes-nothing")
    def test_fault_injected_transfer_restores_quest_log_and_inventories(self):
        self.player.db.inventory = [_T_ITEM, _T_ITEM]
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
            outcome = _transfer_items(self.player, self.recipient, _T_ITEM, 1)

        self.assertFalse(outcome.applied)
        self.assertEqual(list(self.player.db.inventory), player_before)
        self.assertEqual(list(self.recipient.db.inventory), recipient_before)
        self.assertEqual([dict(entry) for entry in (self.player.db.quest_log or [])], log_before)
        self.assertEqual(read_records(self.player)[0].stage_progress, 0)

    @covers_requirement("quest-delivery::the-delivery-observer-computes-a-replacement-and-writes-nothing")
    def test_successful_transfer_schedules_delivery_progress_event(self):
        self.player.db.inventory = [_T_ITEM]
        self.recipient.db.inventory = []

        with (
            patch("world.quests.deliver.log_info") as mock_log,
            self.captureOnCommitCallbacks(execute=True),
        ):
            outcome = _transfer_items(self.player, self.recipient, _T_ITEM, 1)

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
        self.player.db.inventory = [_T_ITEM]
        self.recipient.db.inventory = []

        def failing_apply(plan):
            raise RuntimeError("injected failure")

        with (
            patch("world.quests.deliver.log_info") as mock_log,
            patch("world.rules.npc_intents._apply_plan", side_effect=failing_apply),
            self.captureOnCommitCallbacks(execute=True),
        ):
            outcome = _transfer_items(self.player, self.recipient, _T_ITEM, 1)

        self.assertFalse(outcome.applied)
        mock_log.assert_not_called()


@synthetic_registries("items")
class DeliverSeamTests(QuestRegistryIsolation, EvenniaTest):
    """Contract of the shared advance seam both transfer callers route through."""

    def setUp(self):
        super().setUp()
        # The class decorator wraps test methods only, so the item scope
        # is entered here too: the definition registered below validates
        # its item key against the synthetic registry.
        stack = ExitStack()
        stack.enter_context(synthetic_registries("items"))
        self.addCleanup(stack.close)
        self.room = create_object(Room, key="seam room")
        self.player = create_object(PlayerCharacter, key="seam player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.recipient = create_object(NPC, key="seam recipient", location=self.room)
        self.recipient.race = "human"
        self.recipient.apply_race_baseline()
        self.bystander = create_object(NPC, key="seam bystander", location=self.room)
        self.bystander.race = "human"
        self.bystander.apply_race_baseline()

        self.definition = register(
            quest(
                "deliver_seam_quest",
                stages=(QuestStage(0, deliver(_T_ITEM, quantity=2)),),
            )
        )
        self.record = accept(self.player, self.definition.key)
        bind_stage_runtime(
            self.player,
            self.record.quest_id,
            objective_targets=(self.recipient,),
        )

    def test_seam_advances_a_matching_delivery(self):
        with (
            patch("world.quests.deliver.log_info") as mock_log,
            self.captureOnCommitCallbacks(execute=True),
        ):
            advance_deliveries_for_transfer(
                self.player, self.recipient, _T_ITEM, 1, pin_snapshots={}
            )

        self.assertEqual(read_records(self.player)[0].stage_progress, 1)
        mock_log.assert_called_once_with(
            "delivery_progress",
            context={
                "char": str(self.player.pk),
                "quest": self.definition.key,
                "step": "0",
            },
        )

    def test_seam_advances_nothing_for_an_unbound_receiver(self):
        advance_deliveries_for_transfer(
            self.player, self.bystander, _T_ITEM, 1, pin_snapshots={}
        )

        self.assertEqual(read_records(self.player)[0].stage_progress, 0)

    def test_seam_multi_record_advance_applies_min_quantity_per_record(self):
        second_definition = register(
            quest(
                "deliver_seam_quest_two",
                stages=(QuestStage(0, deliver(_T_ITEM, quantity=2)),),
            )
        )
        second_record = accept(self.player, second_definition.key)
        bind_stage_runtime(
            self.player,
            second_record.quest_id,
            objective_targets=(self.recipient,),
        )

        advance_deliveries_for_transfer(
            self.player, self.recipient, _T_ITEM, 3, pin_snapshots={}
        )

        progress = {
            record.quest_id: (record.stage_progress, record.state)
            for record in read_records(self.player)
        }
        self.assertEqual(
            progress,
            {
                self.record.quest_id: (2, QuestState.COMPLETED),
                second_record.quest_id: (2, QuestState.COMPLETED),
            },
        )

    @covers_requirement("quest-delivery::the-delivery-observer-computes-a-replacement-and-writes-nothing")
    def test_seam_fault_inside_caller_transaction_rolls_back(self):
        before_log = [dict(entry) for entry in (self.player.db.quest_log or [])]

        def failing_delta(*args, **kwargs):
            raise RuntimeError("injected advance failure")

        with (
            patch(
                "world.quests.transitions.apply_quest_log_delta",
                side_effect=failing_delta,
            ),
            transaction.atomic(),
            self.assertRaises(RuntimeError),
        ):
            advance_deliveries_for_transfer(
                self.player, self.recipient, _T_ITEM, 1, pin_snapshots={}
            )

        self.assertEqual(read_records(self.player)[0].stage_progress, 0)
        self.assertEqual(
            [dict(entry) for entry in (self.player.db.quest_log or [])], before_log
        )


@synthetic_registries("items")
class DeliverProseTests(unittest.TestCase):
    """Prose rendering contract for DELIVER quest objectives."""

    @covers_requirement("quest-delivery::a-delivery-objective-renders-player-facing-prose-from-the-registries")
    def test_deliver_objective_renders_traditional_chinese_prose(self):
        objective = QuestObjective(
            kind=ObjectiveKind.DELIVER,
            quantity=3,
            item_key=_T_ITEM,
            requires_bound_targets=True,
        )
        prose = describe_objective(objective)
        self.assertEqual(
            prose, f"交付 3 個{SYNTH_ITEMS[_T_ITEM].display_name_zh}"
        )

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
