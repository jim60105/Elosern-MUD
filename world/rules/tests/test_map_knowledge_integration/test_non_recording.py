"""Map-knowledge journeys (non recording)."""

from ._support import _MapKnowledgeFixture, _node_ids
from tools.spec_traceability import covers_requirement
from unittest.mock import patch
from evennia.utils.create import create_object
from typeclasses.exits import Exit
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom
from world.rules.clock import get_world_clock
from world.rules.map_knowledge import record_arrival


class MapKnowledgeNonRecordingTests(_MapKnowledgeFixture):
    """One map-knowledge recording rule per journey."""


    @covers_requirement("map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams")
    def test_failed_gate_entry_records_nothing(self):
        original_location = self.char1.location
        before = get_world_clock().tick
        with patch("typeclasses.exits.enter_wilderness", return_value=False):
            result = self.gate.at_traverse(self.char1, self.east_gate)
        self.assertFalse(result)
        self.assertIs(self.char1.location, original_location)
        self.assertEqual(get_world_clock().tick, before)
        self.assertEqual(_node_ids(self.char1), set())


    def test_locked_exit_records_nothing(self):
        exit_obj = create_object(Exit, key="locked", location=self.room1, destination=self.room2)
        exit_obj.locks.add("traverse:false()")
        from evennia.objects.objects import ExitCommand

        self.char1.location = self.room1
        command = ExitCommand()
        command.obj = exit_obj
        command.caller = self.char1
        command.func()
        self.assertIs(self.char1.location, self.room1)
        self.assertEqual(_node_ids(self.char1), set())


    def test_vetoed_traversal_records_nothing(self):
        exit_obj = create_object(Exit, key="veto", location=self.room1, destination=self.room2)
        self.char1.location = self.room1
        self.char1.at_pre_move = lambda *a, **k: False
        exit_obj.at_traverse(self.char1, self.room2)
        self.assertIs(self.char1.location, self.room1)
        self.assertEqual(_node_ids(self.char1), set())


    @covers_requirement("movement-cost-charging::movementcostmixin-charges-via-at-post-traverse-not-at-traverse-s-return-value")
    def test_teleport_move_to_records_no_observation(self):
        self.char1.location = self.room1
        self.char1.move_to(self.room2, move_type="teleport")
        self.assertIs(self.char1.location, self.room2)
        self.assertEqual(_node_ids(self.char1), set())


    @covers_requirement("movement-cost-charging::movementcostmixin-charges-via-at-post-traverse-not-at-traverse-s-return-value")
    def test_quiet_relocation_records_no_observation(self):
        self.char1.location = self.room1
        self.char1.move_to(self.room2, quiet=True)
        self.assertIs(self.char1.location, self.room2)
        self.assertEqual(_node_ids(self.char1), set())


    def test_npc_traversal_records_nothing(self):
        exit_obj = create_object(Exit, key="npc_door", location=self.room1, destination=self.room2)
        npc = create_object(NPC, key="wanderer", location=self.room1)
        exit_obj.at_traverse(npc, self.room2)
        self.assertIs(npc.location, self.room2)
        self.assertEqual(_node_ids(npc), set())


    @covers_requirement("map-knowledge::map-knowledge-py-is-the-sole-writer-of-a-versioned-visited-node-record")
    def test_corrupt_record_noops_without_resetting(self):
        self.char1.attributes.add("map_knowledge", {"schema_version": 99, "visited": {}})
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        self.char1.location = self.room1
        with patch("world.rules.map_knowledge.log_warn") as log_warn:
            exit_obj.at_traverse(self.char1, self.room2)
            log_warn.assert_called()
        self.assertIs(self.char1.location, self.room2)
        stored = self.char1.attributes.get("map_knowledge")
        self.assertEqual(stored, {"schema_version": 99, "visited": {}})


    def test_record_arrival_never_raises_on_a_broken_location(self):
        # A malformed location (or any persistence failure) must never bubble
        # out of the movement hook; record_arrival logs and no-ops instead.
        from typeclasses.rooms import GridRoom

        broken = create_object(GridRoom, key="broken")
        self.char1.location = broken
        with patch(
            "world.rules.map_knowledge._derive_node_id", side_effect=RuntimeError("boom")
        ) as derive:
            from world.rules.map_knowledge import record_arrival

            with patch("world.rules.map_knowledge.log_warn") as log_warn:
                record_arrival(self.char1)
                log_warn.assert_called()
            derive.assert_called()
        self.assertIsNone(self.char1.attributes.get("map_knowledge"))

