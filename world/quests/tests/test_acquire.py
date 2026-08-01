"""Tests for quest ACQUIRE objectives and inventory planning (tasks 5.3-5.6)."""

from dataclasses import replace

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
from world.quests.runtime import QuestState, accept_quest, read_records
from world.quests.tests._fixtures import (
    QuestRegistryIsolation,
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


class AcquireDefinitionTests(QuestRegistryIsolation, EvenniaTest):
    def test_valid_acquire_objective_registers_and_starts_at_zero(self):
        definition = register(
            quest(
                "acquire_valid",
                stages=(
                    __import__(
                        "world.quests.definitions",
                        fromlist=["QuestStage"],
                    ).QuestStage(0, acquire("healing_potion", quantity=3)),
                ),
            )
        )
        self.player = create_object(PlayerCharacter, key="acquire player")
        record = accept_quest(self.player, definition.key)
        self.assertEqual(record.stage_progress, 0)
        self.assertEqual(record.state, QuestState.IN_PROGRESS)

    def test_acquire_rejects_unrelated_fields(self):
        from world.quests.definitions import QuestObjective, QuestStage

        bad_shapes = [
            QuestObjective(
                kind=ObjectiveKind.ACQUIRE,
                quantity=1,
                item_key="healing_potion",
                monster_tier="low",
            ),
            QuestObjective(
                kind=ObjectiveKind.ACQUIRE,
                quantity=1,
                item_key="healing_potion",
                destination=__import__(
                    "world.quests.definitions", fromlist=["RoomLocator"]
                ).RoomLocator("anchor", anchor_key="capital_altoria"),
            ),
            QuestObjective(
                kind=ObjectiveKind.ACQUIRE,
                quantity=1,
                item_key="healing_potion",
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
                item_key="no_such_item",
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
        register_catalog_once()
        self.player = create_object(PlayerCharacter, key="acquire progress")
        self.definition = register(
            quest("acquire_potions", stages=(
                __import__(
                    "world.quests.definitions", fromlist=["QuestStage"]
                ).QuestStage(0, acquire("healing_potion", quantity=2)),
            ))
        )

    def _accept(self):
        return accept_quest(self.player, self.definition.key)

    def test_planning_is_side_effect_free(self):
        accept = self._accept()
        before_inventory = list(self.player.db.inventory or [])
        before_log = [dict(entry) for entry in (self.player.db.quest_log or [])]
        plan = plan_inventory_delta(self.player, additions=("healing_potion",))
        self.assertEqual(list(self.player.db.inventory or []), before_inventory)
        self.assertEqual([dict(entry) for entry in (self.player.db.quest_log or [])], before_log)
        self.assertIsNotNone(plan.acquire)
        self.assertEqual(plan.after, ("healing_potion",))
        # Unapplied plan changed nothing.
        self.assertEqual(read_records(self.player)[0].stage_progress, 0)

    def test_repeated_item_quantities_are_preserved(self):
        plan = plan_inventory_delta(self.player, additions=("healing_potion", "healing_potion"))
        self.assertEqual(plan.additions, ("healing_potion", "healing_potion"))
        self.assertEqual(plan.after, ("healing_potion", "healing_potion"))

    def test_insufficient_removal_fails_before_mutation(self):
        add_item(self.player, "healing_potion")
        original_log = [dict(entry) for entry in (self.player.db.quest_log or [])]
        with self.assertRaises(InventoryError):
            plan_inventory_delta(self.player, removals=("healing_potion", "healing_potion"))
        self.assertEqual(list_items(self.player), ["healing_potion"])

    def test_unknown_item_key_is_rejected(self):
        with self.assertRaises(InventoryError):
            plan_inventory_delta(self.player, additions=(123,))
        with self.assertRaises(InventoryError):
            plan_inventory_delta(self.player, additions=("",))

    def test_committed_plan_advances_acquire_objective(self):
        self._accept()
        add_item(self.player, "healing_potion")
        self.assertEqual(read_records(self.player)[0].stage_progress, 1)
        add_item(self.player, "healing_potion")
        record = read_records(self.player)[0]
        self.assertEqual(record.state, QuestState.COMPLETED)
        self.assertEqual(record.stage_progress, 2)

    def test_removal_does_not_reverse_progress(self):
        self._accept()
        add_item(self.player, "healing_potion")
        remove_item(self.player, "healing_potion")
        self.assertEqual(read_records(self.player)[0].stage_progress, 1)

    def test_import_population_is_not_gameplay_acquisition(self):
        record = self._accept()
        self.assertEqual(record.state, QuestState.IN_PROGRESS)
        # Import writes raw inventory directly, never via the planner.
        self.player.db.inventory = ["healing_potion", "healing_potion"]
        # No planner call happened, so progress stays zero.
        self.assertEqual(read_records(self.player)[0].stage_progress, 0)
        # The inventory is still there as initial state.
        self.assertEqual(list_items(self.player), ["healing_potion", "healing_potion"])

    def test_one_addition_advances_multiple_quests_without_surplus_carry(self):
        second = register(
            quest("acquire2", stages=(
                __import__(
                    "world.quests.definitions", fromlist=["QuestStage"]
                ).QuestStage(0, acquire("healing_potion", quantity=1)),
            ))
        )
        self._accept()
        accept_quest(self.player, second.key)
        plan = plan_inventory_delta(self.player, additions=("healing_potion", "healing_potion"))
        self.assertIsNotNone(plan.acquire)
        # Both quests advance at most one stage; the remaining surplus is not
        # carried into the next stage of either quest.
        records = {r.quest_id: r for r in read_records(self.player)}
        for record in records.values():
            self.assertIn(record.state, (QuestState.IN_PROGRESS, QuestState.COMPLETED))
            self.assertNotEqual(record.stage_progress, 2)

    def test_add_item_tolerates_no_inventory(self):
        self.player.db.inventory = None
        add_item(self.player, "healing_potion")
        self.assertEqual(list_items(self.player), ["healing_potion"])

    def test_fault_rolls_back_inventory_and_quest_together(self):
        self._accept()
        before_inventory = list(self.player.db.inventory or [])
        before_log = [dict(entry) for entry in (self.player.db.quest_log or [])]
        plan = plan_inventory_delta(self.player, additions=("healing_potion",))

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


class ImportNonProgressionTests(QuestRegistryIsolation, EvenniaTest):
    def test_imported_items_do_not_auto_complete_a_later_quest(self):
        from world.imports.loader import instantiate_character
        from world.imports.tests.helpers import example_record

        record = example_record()
        record["inventory"] = ["healing_potion", "healing_potion", "healing_potion"]
        entity = instantiate_character(record, PlayerCharacter)
        definition = register(
            quest("acquire_after_import", stages=(
                __import__(
                    "world.quests.definitions", fromlist=["QuestStage"]
                ).QuestStage(0, acquire("healing_potion", quantity=3)),
            ))
        )
        accepted = accept_quest(entity, definition.key)
        self.assertEqual(accepted.stage_progress, 0)


if __name__ == "__main__":
    import unittest

    unittest.main()