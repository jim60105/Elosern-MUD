"""Tests for quest ACQUIRE objectives and inventory planning (tasks 5.3-5.6)."""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from contextlib import ExitStack

from world.tests.synthetic_data import SYNTH_ITEMS, synthetic_registries

#: Every objective runs on the kit's synthetic potion row; the class scope
#: keeps the item registry synthetic for setup, planner calls, and runtime
#: observation alike.
_T_ITEM = SYNTH_ITEMS["t_ember_spray"].key

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from unittest.mock import patch

from typeclasses.characters import PlayerCharacter
from world.quests.catalog import register_catalog
from world.quests.definitions import (
    ObjectiveKind,
    QuestDefinitionError,
    register_quest_definition,
)
from world.quests.runtime import QuestState, read_records
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
    accept,
    acquire,
    quest,
    register,
)
from world.quests.tests._fixtures import register_catalog_once
from world.rules.equipment import (
    InventoryError,
    add_item,
    plan_inventory_delta,
    remove_item,
)
from world.skills.equipment import list_items


@synthetic_registries("items")
class AcquireDefinitionTests(QuestRegistryIsolation, EvenniaTest):
    def test_valid_acquire_objective_registers_and_starts_at_zero(self):
        definition = register(
            quest(
                "acquire_valid",
                stages=(
                    __import__(
                        "world.quests.definitions",
                        fromlist=["QuestStage"],
                    ).QuestStage(0, acquire(_T_ITEM, quantity=3)),
                ),
            )
        )
        self.player = create_object(PlayerCharacter, key="acquire player")
        record = accept(self.player, definition.key)
        self.assertEqual(record.stage_progress, 0)
        self.assertEqual(record.state, QuestState.IN_PROGRESS)

    def test_acquire_rejects_unrelated_fields(self):
        from world.quests.definitions import QuestObjective, QuestStage

        bad_shapes = [
            QuestObjective(
                kind=ObjectiveKind.ACQUIRE,
                quantity=1,
                item_key=_T_ITEM,
                monster_tier="low",
            ),
            QuestObjective(
                kind=ObjectiveKind.ACQUIRE,
                quantity=1,
                item_key=_T_ITEM,
                destination=__import__(
                    "world.quests.definitions", fromlist=["RoomLocator"]
                ).RoomLocator("anchor", anchor_key="t_reject_anchor"),
            ),
            QuestObjective(
                kind=ObjectiveKind.ACQUIRE,
                quantity=1,
                item_key=_T_ITEM,
                requires_bound_targets=True,
            ),
            QuestObjective(
                kind=ObjectiveKind.ACQUIRE,
                quantity=1,
                item_key=None,
            ),
            QuestObjective(
                kind=ObjectiveKind.ACQUIRE,
                quantity=1,
                item_key="t_no_such_item",
            ),
        ]
        for bad in bad_shapes:
            bad_definition = quest("acquire_bad", stages=(QuestStage(0, bad),))
            with self.subTest(objective=bad):
                with self.assertRaises(QuestDefinitionError):
                    register_quest_definition(bad_definition)


class AcquireProgressTests(QuestRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        # The class decorator wraps test methods only, so the item scope is
        # entered here as well: the definition registered below validates its
        # item key against the synthetic registry.
        stack = ExitStack()
        stack.enter_context(synthetic_registries("items"))
        self.addCleanup(stack.close)
        register_catalog_once()
        self.player = create_object(PlayerCharacter, key="acquire progress")
        self.definition = register(
            quest("acquire_potions", stages=(
                __import__(
                    "world.quests.definitions", fromlist=["QuestStage"]
                ).QuestStage(0, acquire(_T_ITEM, quantity=2)),
            ))
        )

    def _accept(self):
        return accept(self.player, self.definition.key)

    def test_planning_is_side_effect_free(self):
        accept = self._accept()
        before_inventory = list(self.player.db.inventory or [])
        before_log = [dict(entry) for entry in (self.player.db.quest_log or [])]
        plan = plan_inventory_delta(self.player, additions=(_T_ITEM,))
        self.assertEqual(list(self.player.db.inventory or []), before_inventory)
        self.assertEqual([dict(entry) for entry in (self.player.db.quest_log or [])], before_log)
        self.assertIsNotNone(plan.acquire)
        self.assertEqual(plan.after, (_T_ITEM,))
        # Unapplied plan changed nothing.
        self.assertEqual(read_records(self.player)[0].stage_progress, 0)

    def test_repeated_item_quantities_are_preserved(self):
        plan = plan_inventory_delta(self.player, additions=(_T_ITEM, _T_ITEM))
        self.assertEqual(plan.additions, (_T_ITEM, _T_ITEM))
        self.assertEqual(plan.after, (_T_ITEM, _T_ITEM))

    def test_insufficient_removal_fails_before_mutation(self):
        add_item(self.player, _T_ITEM)
        original_log = [dict(entry) for entry in (self.player.db.quest_log or [])]
        with self.assertRaises(InventoryError):
            plan_inventory_delta(self.player, removals=(_T_ITEM, _T_ITEM))
        self.assertEqual(list_items(self.player), [_T_ITEM])

    def test_unknown_item_key_is_rejected(self):
        with self.assertRaises(InventoryError):
            plan_inventory_delta(self.player, additions=(123,))
        with self.assertRaises(InventoryError):
            plan_inventory_delta(self.player, additions=("",))

    def test_committed_plan_advances_acquire_objective(self):
        self._accept()
        add_item(self.player, _T_ITEM)
        self.assertEqual(read_records(self.player)[0].stage_progress, 1)
        add_item(self.player, _T_ITEM)
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.COMPLETED)
        self.assertEqual(record.stage_progress, 2)

    def test_removal_does_not_reverse_progress(self):
        self._accept()
        add_item(self.player, _T_ITEM)
        remove_item(self.player, _T_ITEM)
        self.assertEqual(read_records(self.player)[0].stage_progress, 1)

    def test_import_population_is_not_gameplay_acquisition(self):
        record = self._accept()
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        # Import writes raw inventory directly, never via the planner.
        self.player.db.inventory = [_T_ITEM, _T_ITEM]
        # No planner call happened, so progress stays zero.
        self.assertEqual(read_records(self.player)[0].stage_progress, 0)
        # The inventory is still there as initial state.
        self.assertEqual(list_items(self.player), [_T_ITEM, _T_ITEM])

    @covers_requirement("quest-reward-settlement::acquire-is-a-closed-inventory-backed-quest-objective")
    def test_one_addition_advances_multiple_quests_without_surplus_carry(self):
        second = register(
            quest("acquire2", stages=(
                __import__(
                    "world.quests.definitions", fromlist=["QuestStage"]
                ).QuestStage(0, acquire(_T_ITEM, quantity=1)),
            ))
        )
        self._accept()
        accept(self.player, second.key)
        plan = plan_inventory_delta(self.player, additions=(_T_ITEM, _T_ITEM))
        self.assertIsNotNone(plan.acquire)
        # Both quests advance at most one stage; the remaining surplus is not
        # carried into the next stage of either quest.
        records = {r.quest_id: r for r in read_records(self.player)}
        for record in records.values():
            self.assertIn(record.state, (QuestState.IN_PROGRESS, QuestState.COMPLETED))
            self.assertNotEqual(record.stage_progress, 2)

    def test_add_item_tolerates_no_inventory(self):
        self.player.db.inventory = None
        add_item(self.player, _T_ITEM)
        self.assertEqual(list_items(self.player), [_T_ITEM])

    @covers_requirement("equipment-inventory::inventory-plans-compose-with-larger-atomic-operations")
    def test_fault_rolls_back_inventory_and_quest_together(self):
        self._accept()
        before_inventory = list(self.player.db.inventory or [])
        before_log = [dict(entry) for entry in (self.player.db.quest_log or [])]
        plan = plan_inventory_delta(self.player, additions=(_T_ITEM,))

        class FakeAtomic:
            def __enter__(self):
                return self

            def __exit__(self, *exc_info):
                raise RuntimeError("db failure")

        with patch("django.db.transaction.atomic", return_value=FakeAtomic()):
            from world.rules.equipment import apply_inventory_plan

            with self.assertRaises(RuntimeError):
                apply_inventory_plan(plan)
        self.assertEqual(list(self.player.db.inventory or []), before_inventory)
        self.assertEqual([dict(entry) for entry in (self.player.db.quest_log or [])], before_log)


@synthetic_registries("items")
class ImportNonProgressionTests(QuestRegistryIsolation, EvenniaTest):
    @covers_requirement("quest-reward-settlement::import-population-is-not-gameplay-acquisition")
    def test_imported_items_do_not_auto_complete_a_later_quest(self):
        from world.imports.loader import instantiate_character
        from world.imports.tests.helpers import example_record

        record = example_record()
        record["inventory"] = [_T_ITEM, _T_ITEM, _T_ITEM]
        entity = instantiate_character(record, PlayerCharacter)
        definition = register(
            quest("acquire_after_import", stages=(
                __import__(
                    "world.quests.definitions", fromlist=["QuestStage"]
                ).QuestStage(0, acquire(_T_ITEM, quantity=3)),
            ))
        )
        accepted = accept(entity, definition.key)
        self.assertEqual(accepted.stage_progress, 0)


if __name__ == "__main__":
    import unittest

    unittest.main()
