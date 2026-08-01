"""Tests for runtime instance and entity binding (tasks 4.1-4.5)."""

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import InstanceRoom
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import QuestStage
from world.quests.runtime import (
    QuestDataError,
    QuestTransitionError,
    abandon_quest,
    accept_quest,
    from_storage,
    read_records,
    to_storage,
)
from world.quests.transitions import (
    apply_quest_log_replacement,
    stage_pin_reason,
)

from ._fixtures import (
    QuestRegistryIsolation,
    anchor_locator,
    defeat,
    escort,
    quest,
    register,
)


class BindingTests(QuestRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="bind-player")
        self.bound_defeat = register(
            quest("bind_defeat", stages=(QuestStage(0, defeat(bound=True)),))
        )
        self.escort_def = register(
            quest(
                "bind_escort",
                stages=(QuestStage(0, escort(anchor_locator())),),
            )
        )

    def _monster(self, key: str, tier: str = "low") -> Monster:
        monster = create_object(Monster, key=key)
        monster.threat_tier = tier
        monster.apply_monster_tier("floor")
        return monster

    def _npc(self, key: str) -> NPC:
        npc = create_object(NPC, key=key)
        npc.race = "human"
        npc.apply_race_baseline()
        return npc

    def _room(self, key: str = "bind-room") -> InstanceRoom:
        return create_object(InstanceRoom, key=key)

    def test_runtime_binding_stores_identities_and_pins_instance(self):
        room = self._room()
        first = self._monster("first")
        second = self._monster("second")
        guard = self._npc("guard")
        record = accept_quest(self.player, self.bound_defeat.key)
        bound = bind_stage_runtime(
            self.player,
            record.quest_id,
            room=room,
            objective_targets=(first, second),
            protected_entities=(guard,),
        )
        self.assertEqual(bound.objective_target_ids, (first.pk, second.pk))
        self.assertEqual(bound.protected_entity_ids, (guard.pk,))
        self.assertEqual(bound.stage_room_id, room.pk)
        expected_reason = stage_pin_reason(self.player.pk, record.quest_id, 0)
        self.assertEqual(room.db.pin_reasons, [expected_reason])
        stored = self.player.db.quest_log[0]
        self.assertEqual(stored["objective_target_ids"], [first.pk, second.pk])

    def test_identical_binding_is_idempotent(self):
        room = self._room()
        first = self._monster("monster")
        record = accept_quest(self.player, self.bound_defeat.key)
        bind_stage_runtime(
            self.player,
            record.quest_id,
            room=room,
            objective_targets=(first,),
        )
        before = list(self.player.db.quest_log)
        re_bound = bind_stage_runtime(
            self.player,
            record.quest_id,
            room=room,
            objective_targets=(first,),
        )
        self.assertEqual(re_bound.objective_target_ids, (first.pk,))
        self.assertEqual(self.player.db.quest_log, before)
        self.assertEqual(room.db.pin_reasons, [stage_pin_reason(self.player.pk, record.quest_id, 0)])

    def test_conflicting_rebind_is_rejected_before_mutation(self):
        room = self._room()
        first = self._monster("monster")
        another_room = self._room("other-room")
        record = accept_quest(self.player, self.bound_defeat.key)
        bind_stage_runtime(self.player, record.quest_id, room=room, objective_targets=(first,))
        before_log = list(self.player.db.quest_log)
        before_pins = list(room.db.pin_reasons)
        with self.assertRaises(QuestTransitionError):
            bind_stage_runtime(self.player, record.quest_id, room=another_room, objective_targets=(first,))
        with self.assertRaises(QuestTransitionError):
            bind_stage_runtime(self.player, record.quest_id, objective_targets=(first,))
        self.assertEqual(self.player.db.quest_log, before_log)
        self.assertEqual(room.db.pin_reasons, before_pins)

    def test_overlapping_objective_and_protected_binding_is_rejected(self):
        room = self._room()
        monster = self._monster("shared")
        record = accept_quest(self.player, self.bound_defeat.key)
        before_log = list(self.player.db.quest_log)
        with self.assertRaises(QuestTransitionError):
            bind_stage_runtime(
                self.player,
                record.quest_id,
                room=room,
                objective_targets=(monster,),
                protected_entities=(monster,),
            )
        self.assertEqual(self.player.db.quest_log, before_log)
        self.assertEqual(room.db.pin_reasons, [])

    def test_persisted_overlap_fails_before_any_lifecycle_operation(self):
        room = self._room()
        record = accept_quest(self.player, self.bound_defeat.key)
        conflicting = {
            **to_storage(record),
            "objective_target_ids": [11],
            "protected_entity_ids": [11],
        }
        self.player.db.quest_log = [conflicting]
        with self.assertRaises(QuestDataError):
            bind_stage_runtime(self.player, record.quest_id, room=room)
        with self.assertRaises(QuestDataError):
            read_records(self.player)

    def test_non_instance_room_is_rejected(self):
        record = accept_quest(self.player, self.bound_defeat.key)
        with self.assertRaises(QuestTransitionError):
            bind_stage_runtime(self.player, record.quest_id, room=self.room1)

    def test_dead_or_non_living_targets_are_rejected(self):
        room = self._room()
        record = accept_quest(self.player, self.bound_defeat.key)
        dead = self._monster("dead")
        dead.traits.hp._data["current"] = 0
        with self.assertRaises(QuestTransitionError):
            bind_stage_runtime(self.player, record.quest_id, room=room, objective_targets=(dead,))
        from evennia.objects.objects import DefaultObject

        plain_object = create_object(DefaultObject, key="not-living")
        with self.assertRaises(QuestTransitionError):
            bind_stage_runtime(self.player, record.quest_id, room=room, protected_entities=(plain_object,))

    def test_pin_failure_rolls_back_binding_with_cache_restore(self):
        room = self._room()
        monster = self._monster("rollback")
        record = accept_quest(self.player, self.bound_defeat.key)
        before_log = list(self.player.db.quest_log)
        with patch(
            "world.quests.transitions._apply_pin_operations",
            side_effect=RuntimeError("injected pin failure"),
        ):
            with self.assertRaises(RuntimeError):
                bind_stage_runtime(
                    self.player,
                    record.quest_id,
                    room=room,
                    objective_targets=(monster,),
                )
        self.assertEqual(self.player.db.quest_log, before_log)
        self.assertEqual(room.db.pin_reasons, [])
        # The in-process cache has been restored; a fresh DB read agrees.
        fresh = read_records(self.player)
        self.assertEqual([to_storage(entry) for entry in fresh][0]["objective_target_ids"], [])
        room_fresh = InstanceRoom.objects.get(id=room.id)
        self.assertEqual(room_fresh.db.pin_reasons, [])

    def test_quest_log_failure_restores_an_already_written_pin(self):
        room = self._room()
        monster = self._monster("log-rollback")
        record = accept_quest(self.player, self.bound_defeat.key)
        before_log = list(self.player.db.quest_log)
        original_add = room.attributes.add

        def injected_add(key, value, **kwargs):
            if key == "pin_reasons":
                raise RuntimeError("injected quest-log persistence failure")

        with patch.object(room.attributes, "add", side_effect=injected_add):
            with self.assertRaises(RuntimeError):
                bind_stage_runtime(
                    self.player,
                    record.quest_id,
                    room=room,
                    objective_targets=(monster,),
                )
        self.assertEqual(self.player.db.quest_log, before_log)
        self.assertEqual(room.db.pin_reasons, [])
        self.assertEqual(InstanceRoom.objects.get(id=room.id).db.pin_reasons, [])

    def test_restore_itself_failing_still_degrades_to_cache_reset(self):
        room = self._room()
        monster = self._monster("restore-rollback")
        record = accept_quest(self.player, self.bound_defeat.key)
        before_log = list(self.player.db.quest_log)

        def injected_write(key, value, **kwargs):
            if key == "pin_reasons":
                raise RuntimeError("injected commit failure")

        real_add = self.player.attributes.add

        def injected_restore(key, value, **kwargs):
            if key == "quest_log":
                raise RuntimeError("injected restore failure")
            return real_add(key, value, **kwargs)

        with (
            patch.object(room.attributes, "add", side_effect=injected_write),
            patch.object(self.player.attributes, "add", side_effect=injected_restore),
        ):
            with self.assertRaises(RuntimeError):
                bind_stage_runtime(
                    self.player,
                    record.quest_id,
                    room=room,
                    objective_targets=(monster,),
                )
        # The best-effort restore fell back to a cache reset, so reads agree
        # with the rolled-back database.
        self.assertEqual(self.player.db.quest_log, before_log)
        self.assertEqual(room.db.pin_reasons, [])

    def test_abandonment_releases_exact_pin(self):
        room = self._room()
        monster = self._monster("release")
        record = accept_quest(self.player, self.bound_defeat.key)
        bind_stage_runtime(self.player, record.quest_id, room=room, objective_targets=(monster,))
        failed = abandon_quest(self.player, record.quest_id)
        self.assertEqual(failed.failure_reason, "abandoned")
        self.assertEqual(room.db.pin_reasons, [])

    def test_release_tolerates_already_deleted_bound_room(self):
        temp = self._room("to-delete")
        temp_id = temp.pk
        temp.delete()
        self.assertFalse(InstanceRoom.objects.filter(id=temp_id).exists())
        record = accept_quest(self.player, self.bound_defeat.key)
        bound = {
            **to_storage(record),
            "stage_room_id": temp_id,
            "objective_target_ids": [],
            "protected_entity_ids": [],
        }
        apply_quest_log_replacement(self.player, [from_storage(bound)])
        failed = abandon_quest(self.player, record.quest_id)
        self.assertEqual(failed.failure_reason, "abandoned")
        self.assertEqual(failed.stage_room_id, None)

    def test_escort_binding_stores_only_protected_identities(self):
        room = self._room("escort-room")
        npc = self._npc("escort-npc")
        record = accept_quest(self.player, self.escort_def.key)
        bound = bind_stage_runtime(
            self.player,
            record.quest_id,
            room=room,
            protected_entities=(npc,),
        )
        self.assertEqual(bound.protected_entity_ids, (npc.pk,))
        self.assertEqual(bound.objective_target_ids, ())


if __name__ == "__main__":
    unittest.main()