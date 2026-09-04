"""Evennia integration tests for map-knowledge arrival recording.

Covers the writer seams (design D3): ``record_arrival`` deriving canonical node
IDs from real locations, the ``MovementCostMixin.at_post_traverse`` hook, the
wilderness gate/return success branches, activation relocation, corrupt-record
isolation, and reclamation pruning (design D4).
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.exits import Exit, WildernessGateExit, WildernessReturnExit
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom, InstanceRoom, Room, TerrainRoom
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.maps.bootstrap import SOUTH_GATE_XYZ, sync_grid, sync_wilderness
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.clock import get_world_clock
from world.rules.map_knowledge import (
    KnowledgeError,
    parse_knowledge,
    prune_reclaimed_room,
    record_arrival,
)

NORTH_GATE_XYZ = (2, 4, "capital_altoria")
_CAPITAL = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
ENTRY_XY = _CAPITAL.approach_cell(_CAPITAL.gate_for("s"))  # (60, 103)


def _knowledge(character):
    try:
        return parse_knowledge(character)
    except KnowledgeError:
        return []


def _node_ids(character):
    return {visit.node_id for visit in _knowledge(character)}


class MapKnowledgeSeamTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        create_object(Room, key="虛境", location=None)
        sync_grid()
        sync_wilderness()
        self.north_gate = GridRoom.objects.filter_xyz(xyz=NORTH_GATE_XYZ).first()
        self.south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.gate = [e for e in self.north_gate.exits if isinstance(e, WildernessGateExit)][0]

    def _exit(self, direction):
        return [e for e in self.char1.location.exits if e.key == direction][0]

    @covers_requirement("map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams")
    def test_grid_traversal_records_destination_grid_node(self):
        self.char1.location = self.south_gate
        city_exit = [e for e in self.south_gate.exits if e.destination.key == "南大道"][0]
        city_exit.at_traverse(self.char1, city_exit.destination)
        self.assertEqual(self.char1.location.key, "南大道")
        self.assertIn("grid:capital_altoria:2:1", _node_ids(self.char1))

    def test_plain_exit_records_room_node(self):
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        self.char1.location = self.room1
        exit_obj.at_traverse(self.char1, self.room2)
        self.assertIn(f"room:{self.room2.id}", _node_ids(self.char1))

    @covers_requirement("map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams")
    def test_limbo_bridge_records_grid_node(self):
        from world.maps.bootstrap import EXIT_TO_CITY

        limbo = create_object(Room, key="LimboBridge", location=None)
        south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        bridge = create_object(
            Exit,
            key=EXIT_TO_CITY["key"],
            aliases=EXIT_TO_CITY["aliases"],
            location=limbo,
            destination=south_gate,
        )
        self.char1.location = limbo
        bridge.at_traverse(self.char1, south_gate)
        self.assertIn("grid:capital_altoria:2:0", _node_ids(self.char1))

    def test_instance_doorway_records_room_node(self):
        from world.maps.instance import spawn_instance_room

        room = spawn_instance_room(
            self.room1,
            {"prototype_parent": "instance_room", "key": "cave"},
            exit_key="in",
            return_key="out",
            ttl_seconds=10,
        )
        door = [e for e in self.room1.exits if e.key == "in"][0]
        self.char1.location = self.room1
        door.at_traverse(self.char1, room)
        self.assertIs(self.char1.location, room)
        self.assertIn(f"room:{room.id}", _node_ids(self.char1))

    @covers_requirement("map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams")
    def test_gate_entry_records_wilderness_node(self):
        before = get_world_clock().tick
        self.gate.at_traverse(self.char1, self.north_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        self.assertEqual(self.char1.location.coordinates, ENTRY_XY)
        expected = f"wild:{WILDERNESS_NAME}:{ENTRY_XY[0]}:{ENTRY_XY[1]}"
        self.assertIn(expected, _node_ids(self.char1))
        self.assertGreater(get_world_clock().tick, before)

    @covers_requirement("map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams")
    def test_ordinary_wilderness_step_records_wilderness_node(self):
        self.gate.at_traverse(self.char1, self.north_gate)
        start = self.char1.location.coordinates
        self._exit("east").at_traverse(self.char1, self.char1.location)
        expected = f"wild:{WILDERNESS_NAME}:{start[0] + 1}:{start[1]}"
        self.assertIn(expected, _node_ids(self.char1))

    @covers_requirement("map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams")
    def test_south_return_records_grid_node(self):
        self.gate.at_traverse(self.char1, self.north_gate)
        self._exit("south").at_traverse(self.char1, self.char1.location)
        self.assertIs(self.char1.location, self.north_gate)
        self.assertIn("grid:capital_altoria:2:4", _node_ids(self.char1))

    @covers_requirement("map-knowledge::arrival-recording-happens-only-at-existing-successful-arrival-seams")
    def test_failed_gate_entry_records_nothing(self):
        original_location = self.char1.location
        before = get_world_clock().tick
        with patch("typeclasses.exits.enter_wilderness", return_value=False):
            result = self.gate.at_traverse(self.char1, self.north_gate)
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


class MapKnowledgePruneTests(EvenniaTest):
    """Reclaimed-room pruning (design D4) through the instance reclaim seam."""

    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room1.save()

    def _knowledge_of(self, character):
        try:
            return parse_knowledge(character)
        except KnowledgeError:
            return []

    @covers_requirement("map-knowledge::reclaimed-room-knowledge-is-pruned-transactionally-with-the-room-deletion")
    def test_prune_removes_target_node_only_from_affected_players(self):
        room = create_object(InstanceRoom, key="ephemeral")
        affected = self.char1
        unaffected = self.char2
        affected.attributes.add(
            "map_knowledge",
            {
                "schema_version": 1,
                "visited": {
                    f"room:{room.id}": {"first_seen_tick": 10, "last_seen_tick": 20},
                    f"room:{self.room1.id}": {"first_seen_tick": 30, "last_seen_tick": 30},
                },
            },
        )
        unaffected.attributes.add(
            "map_knowledge",
            {
                "schema_version": 1,
                "visited": {
                    f"room:{self.room1.id}": {"first_seen_tick": 30, "last_seen_tick": 30}
                },
            },
        )
        prune_reclaimed_room(room.id)
        self.assertNotIn(f"room:{room.id}", _node_ids(affected))
        self.assertIn(f"room:{self.room1.id}", _node_ids(affected))
        self.assertIn(f"room:{self.room1.id}", _node_ids(unaffected))

    def test_player_without_attribute_gets_none_by_pruning(self):
        room = create_object(InstanceRoom, key="never_visited")
        self.assertFalse(self.char1.attributes.has("map_knowledge"))
        prune_reclaimed_room(room.id)
        self.assertFalse(self.char1.attributes.has("map_knowledge"))

    def test_prune_skips_a_corrupt_record_with_a_diagnostic(self):
        room = create_object(InstanceRoom, key="corrupt_owner")
        self.char1.attributes.add(
            "map_knowledge", {"schema_version": 99, "visited": {}}
        )
        from world.rules.map_knowledge import log_warn as _log_warn

        with patch("world.rules.map_knowledge.log_warn") as log_warn:
            prune_reclaimed_room(room.id)
            log_warn.assert_called()
        # The corrupt record is left untouched, not reset or rewritten.
        self.assertEqual(
            self.char1.attributes.get("map_knowledge"),
            {"schema_version": 99, "visited": {}},
        )

    @covers_requirement("map-knowledge::reclaimed-room-knowledge-is-pruned-transactionally-with-the-room-deletion")
    def test_prune_write_failure_restores_snapshots(self):
        room = create_object(InstanceRoom, key="failure_room")
        before = {
            "schema_version": 1,
            "visited": {
                f"room:{room.id}": {"first_seen_tick": 10, "last_seen_tick": 20},
                f"room:{self.room1.id}": {"first_seen_tick": 30, "last_seen_tick": 30},
            },
        }
        self.char1.attributes.add("map_knowledge", before)
        self.char2.attributes.add(
            "map_knowledge",
            {
                "schema_version": 1,
                "visited": {f"room:{room.id}": {"first_seen_tick": 5, "last_seen_tick": 5}},
            },
        )
        from world.rules.map_knowledge import KnowledgePruneError

        target = f"room:{room.id}"

        def failing_prune_write(character, record):
            visited = record.get("visited", {})
            if target in visited:
                # A snapshot restore write carries the target node back; let it
                # through so the module's own rollback can run.
                character.attributes.add("map_knowledge", record)
                return
            raise RuntimeError("disk full")

        with patch(
            "world.rules.map_knowledge._write_knowledge",
            side_effect=failing_prune_write,
        ):
            with self.assertRaises(KnowledgePruneError):
                prune_reclaimed_room(room.id)
        # The failing write never committed, so the stored values are restored
        # to their prior snapshots via the real restore path.
        self.assertEqual(self.char1.attributes.get("map_knowledge"), before)
        self.assertEqual(
            self.char2.attributes.get("map_knowledge"),
            {
                "schema_version": 1,
                "visited": {f"room:{room.id}": {"first_seen_tick": 5, "last_seen_tick": 5}},
            },
        )

    def test_prune_restore_failure_is_best_effort_and_still_raises(self):
        # A persistence failure on the prune write, with the restore write also
        # failing, must not raise out of the module except as the dedicated
        # error (the inner restore failure is swallowed as best-effort).
        room = create_object(InstanceRoom, key="restore_failure")
        self.char1.attributes.add(
            "map_knowledge",
            {
                "schema_version": 1,
                "visited": {f"room:{room.id}": {"first_seen_tick": 10, "last_seen_tick": 20}},
            },
        )
        from world.rules.map_knowledge import KnowledgePruneError

        target = f"room:{room.id}"

        def always_fail(character, record):
            raise RuntimeError("disk full")

        with patch(
            "world.rules.map_knowledge._write_knowledge",
            side_effect=always_fail,
        ):
            with self.assertRaises(KnowledgePruneError):
                prune_reclaimed_room(room.id)


if __name__ == "__main__":
    import unittest

    unittest.main()
