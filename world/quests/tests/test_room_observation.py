"""Tests for room-driven quest progress (tasks 7.1-7.6)."""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import (
    AnchorRoom,
    GridRoom,
    InstanceRoom,
    Room,
    TerrainRoom,
)
from world.quests.binding import bind_stage_runtime
from world.quests.definitions import QuestStage, QuestType
from world.quests.room_observation import QuestObservableRoomMixin
from world.quests.runtime import QuestState, accept_quest, read_records, to_storage
from world.maps.bootstrap import NORTH_GATE_XYZ, sync_grid, sync_wilderness

from ._fixtures import (
    QuestRegistryIsolation,
    anchor_locator,
    bound_instance_locator,
    escort,
    grid_locator,
    quest,
    reach,
    register,
)


class QuestRoomMroTests(unittest.TestCase):
    def test_mixin_adoption_and_wilderness_exclusion(self):
        self.assertIn(QuestObservableRoomMixin, GridRoom.__mro__)
        self.assertIn(QuestObservableRoomMixin, AnchorRoom.__mro__)
        self.assertIn(QuestObservableRoomMixin, InstanceRoom.__mro__)
        self.assertNotIn(QuestObservableRoomMixin, TerrainRoom.__mro__)
        self.assertNotIn(QuestObservableRoomMixin, Room.__mro__)


def reach_stage(destination, index: int = 0):
    return QuestStage(index, reach(destination))


def escort_stage(destination, index: int = 0):
    return QuestStage(index, escort(destination))


class RoomArrivalProgressTests(QuestRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        create_object(Room, key="Limbo", location=None)
        sync_grid()
        self.player = create_object(PlayerCharacter, key="room-player")
        self.player.race = "human"
        self.player.apply_race_baseline()

    def _anchor(self) -> AnchorRoom:
        room = AnchorRoom.objects.filter(db_key="中央廣場").first()
        self.assertIsInstance(room, AnchorRoom)
        return room

    def _grid_room(self, x: int = 1, y: int = 1) -> GridRoom:
        room = GridRoom.objects.filter_xyz(xyz=(x, y, "capital_altoria")).first()
        self.assertIsNotNone(room)
        return room

    def _npc(self, key: str) -> NPC:
        npc = create_object(NPC, key=key)
        npc.race = "human"
        npc.apply_race_baseline()
        return npc

    def _enter(self, room):
        self.player.move_to(room, quiet=True)
        self.assertIs(self.player.location, room)

    def _records(self):
        return [to_storage(record) for record in read_records(self.player)]

    def test_anchor_arrival_completes_matching_reach_stage(self):
        definition = register(
            quest(
                "reach_anchor_arrival",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(anchor_locator()),),
            )
        )
        record = accept_quest(self.player, definition.key)
        self.assertIs(record.state, QuestState.IN_PROGRESS)
        self._enter(self._anchor())
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["quest_id"], record.quest_id)

    @covers_requirement("quest-progress-tracking::room-arrival-drives-reach-and-escort-through-supported-persistent-room-hooks")
    def test_grid_arrival_uses_exact_xyz_identity(self):
        definition = register(
            quest(
                "reach_grid_xyz",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(grid_locator(1, 1)),),
            )
        )
        record = accept_quest(self.player, definition.key)
        self._enter(self._grid_room(1, 1))
        stored = self._records()[0]
        self.assertEqual(stored["state"], "completed")
        self.assertEqual(stored["quest_id"], record.quest_id)

    def test_bound_instance_arrival_uses_accepted_record(self):
        definition = register(
            quest(
                "reach_bound_instance",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(bound_instance_locator()),),
            )
        )
        record = accept_quest(self.player, definition.key)
        room = create_object(InstanceRoom, key="instance-arrival")
        bind_stage_runtime(self.player, record.quest_id, room=room)
        self._enter(room)
        self.assertEqual(self._records()[0]["state"], "completed")

    def test_escort_requires_all_protected_entities_alive_and_present(self):
        definition = register(
            quest(
                "escort_presence",
                quest_type=QuestType.ESCORT,
                stages=(escort_stage(anchor_locator()),),
            )
        )
        record = accept_quest(self.player, definition.key)
        first = self._npc("first")
        second = self._npc("second")
        bind_stage_runtime(
            self.player,
            record.quest_id,
            protected_entities=(first, second),
        )
        anchor = self._anchor()
        first.move_to(anchor, quiet=True)
        self._enter(anchor)
        self.assertEqual(self._records()[0]["state"], "in_progress")
        second.move_to(anchor, quiet=True)
        self.player.move_to(self.room1, quiet=True)
        self._enter(anchor)
        self.assertEqual(self._records()[0]["state"], "completed")

    def test_escort_with_dead_protected_entity_does_not_complete(self):
        definition = register(
            quest(
                "escort_dead",
                quest_type=QuestType.ESCORT,
                stages=(escort_stage(anchor_locator()),),
            )
        )
        record = accept_quest(self.player, definition.key)
        guard = self._npc("dead-guard")
        bind_stage_runtime(self.player, record.quest_id, protected_entities=(guard,))
        anchor = self._anchor()
        guard.traits.hp._data["current"] = 0
        guard.move_to(anchor, quiet=True)
        self._enter(anchor)
        self.assertEqual(self._records()[0]["state"], "in_progress")

    def test_instance_interaction_behavior_remains_intact(self):
        definition = register(
            quest(
                "reach_instance_behavior",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(bound_instance_locator()),),
            )
        )
        record = accept_quest(self.player, definition.key)
        room = create_object(InstanceRoom, key="interaction-room")
        bind_stage_runtime(self.player, record.quest_id, room=room)
        self._enter(room)
        self.assertTrue(room.db.interacted)
        self.assertEqual(self._records()[0]["state"], "completed")

    def test_multiple_matching_quests_each_transition_once_per_hook(self):
        first = register(
            quest(
                "reach_multi_one",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(anchor_locator()),),
            )
        )
        second = register(
            quest(
                "reach_multi_two",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(anchor_locator()),),
            )
        )
        accept_quest(self.player, first.key)
        accept_quest(self.player, second.key)
        self._enter(self._anchor())
        states = {entry["definition_key"]: entry["state"] for entry in self._records()}
        self.assertEqual(states[first.key], "completed")
        self.assertEqual(states[second.key], "completed")

    def test_terminal_records_are_ignored_by_arrival(self):
        definition = register(
            quest(
                "reach_terminal",
                quest_type=QuestType.EXPLORE,
                stages=(reach_stage(anchor_locator()),),
            )
        )
        record = accept_quest(self.player, definition.key)
        self._enter(self._anchor())
        self.assertEqual(self._records()[0]["state"], "completed")
        self.player.move_to(self.room1, quiet=True)
        self._enter(self._anchor())
        self.assertEqual(self._records()[0]["state"], "completed")


class WildernessObservationExclusionTests(QuestRegistryIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        create_object(Room, key="Limbo", location=None)
        sync_grid()
        sync_wilderness()
        self.north_gate = GridRoom.objects.filter_xyz(xyz=NORTH_GATE_XYZ).first()
        self.gate = [e for e in self.north_gate.exits if e.key == "荒野"][0]

    def _step(self, direction: str):
        exit_obj = [e for e in self.char1.location.exits if e.key == direction][0]
        exit_obj.at_traverse(self.char1, self.char1.location)

    @covers_requirement("quest-progress-tracking::wilderness-rooms-do-not-advertise-an-arrival-hook-that-normal-traversal-bypasses")
    def test_wilderness_entry_and_step_do_not_invoke_observation(self):
        with patch(
            "world.quests.room_observation.observe_room_entry",
        ) as observer:
            self.gate.at_traverse(self.char1, self.north_gate)
            self.assertIsInstance(self.char1.location, TerrainRoom)
            self._step("east")
        observer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
