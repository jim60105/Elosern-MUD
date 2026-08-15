"""Integration tests for the movement-settlement boundary (movement-settlement-atomicity).

Covers the plain-exit, wilderness gate, wilderness step, and wilderness return
lineages: a failing settlement step must leave the traverser at the source with
every Evennia in-process cache surface reconciled, a falsy wilderness return
after relocation is compensated as a failure, and the commit-time cache
reconciliation is verified by invoking the compensation directly against a
deliberately constructed divergent in-process state (Django test cases wrap
every transaction, so a commit failure cannot occur at the boundary level in
tests).
"""

from unittest.mock import patch

from evennia.contrib.grid.wilderness.wilderness import WildernessScript
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom, InstanceRoom, Room, TerrainRoom
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.clock import CLOCK_YAML, WorldClock, get_world_clock
from world.rules.map_knowledge import KnowledgeError, parse_knowledge
from world.rules.party import join_party

NORTH_GATE_XYZ = (2, 4, "capital_altoria")
ENTRY_XY = WILDERNESS_ENTRY_REGISTRY["capital_altoria"].wilderness_xy
MOVE = CLOCK_YAML["command_defaults"]["move"]


def _failing_advance(*args, **kwargs):
    """A clock advance that always fails (patched onto ``WorldClock``)."""
    raise RuntimeError("clock advance failed")


def _flaky_advance(real):
    """Return a clock advance wrapper that fails on the second call.

    The first call (the gate entry) behaves exactly like the real advance, so
    a wilderness step can fail after the entry committed.
    """
    count = {"n": 0}

    def advance(clock, *args, **kwargs):
        count["n"] += 1
        if count["n"] >= 2:
            raise RuntimeError("clock advance failed")
        return real(clock, *args, **kwargs)

    return advance


class MovementSettlementPlainExitTests(EvenniaTest):
    """The plain ``MovementCostMixin`` exit lineage (tasks 3.1, 3.2, 3.6, 3.9)."""

    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()

    def _companion(self):
        npc = create_object(NPC, key="同伴", location=self.room1)
        join_party(npc, self.char1)
        return npc

    def test_charge_failure_returns_player_and_companion_to_source(self):
        npc = self._companion()
        destination = create_object(InstanceRoom, key="目的地")
        destination.db.pin_reasons = ["quest:1:q1:stage:0"]
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=destination)
        self.char1.guide_progress = {"state": "active", "seen_keywords": []}
        before = get_world_clock().tick
        with patch.object(WorldClock, "advance", _failing_advance):
            with self.assertRaises(RuntimeError):
                exit_obj.at_traverse(self.char1, destination)
        self.assertIs(self.char1.location, self.room1)
        self.assertIs(npc.location, self.room1)
        self.assertIn(self.char1, self.room1.contents)
        self.assertIn(npc, self.room1.contents)
        self.assertNotIn(self.char1, destination.contents)
        self.assertNotIn(npc, destination.contents)
        self.assertEqual(get_world_clock().tick, before)
        with self.assertRaises(KnowledgeError):
            parse_knowledge(self.char1)
        self.assertEqual(self.char1.guide_progress, {"state": "active", "seen_keywords": []})
        self.assertEqual(self.char1.attributes.get("quest_log"), [])
        # The destination room's quest-observation surfaces were restored: the
        # arrival set ``interacted`` inside the rolled-back move, so the value
        # is back to its pre-move False, and the pin list is unchanged.
        self.assertFalse(destination.db.interacted)
        self.assertEqual(destination.db.pin_reasons, ["quest:1:q1:stage:0"])

    def test_failure_after_companions_move_returns_every_companion(self):
        npc = self._companion()
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        with patch(
            "world.rules.onboarding.observe_room_entry",
            side_effect=RuntimeError("room-entry observer failed"),
        ):
            with self.assertRaises(RuntimeError):
                exit_obj.at_traverse(self.char1, self.room2)
        self.assertIs(self.char1.location, self.room1)
        self.assertIs(npc.location, self.room1)
        self.assertIn(self.char1, self.room1.contents)
        self.assertIn(npc, self.room1.contents)
        self.assertNotIn(self.char1, self.room2.contents)
        self.assertNotIn(npc, self.room2.contents)

    def test_direct_compensation_reconciles_divergent_in_process_state(self):
        from world.rules.movement_settlement import _compensate, _snapshot_movement_state

        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        self.char1.location = self.room1
        self.char1.db.map_knowledge = {
            "schema_version": 1,
            "visited": {
                f"room:{int(self.room1.pk)}": {"first_seen_tick": 5, "last_seen_tick": 5}
            },
        }
        before = get_world_clock().tick
        snapshot = _snapshot_movement_state(
            self.char1,
            self.room1,
            destination=self.room2,
            wilderness_coordinates=None,
            wilderness_source_coordinates=None,
        )
        # Diverge the in-process state exactly as a rolled-back commit leaves
        # it: the idmapper, the contents caches, the attribute backend cache,
        # and the clock script all keep their post-move values.
        self.char1.location = self.room2
        self.char1.db.map_knowledge = {
            "schema_version": 1,
            "visited": {
                f"room:{int(self.room2.pk)}": {"first_seen_tick": 5, "last_seen_tick": 5}
            },
        }
        self.char1.db.guide_progress = {"state": "skipped", "seen_keywords": []}
        self.char1.db.quest_log = [{"quest_id": "divergent"}]
        self.room2.db.interacted = True
        self.room2.db.pin_reasons = ["divergent"]
        get_world_clock()._script.db.tick += MOVE
        _compensate(snapshot)
        self.assertIs(self.char1.location, self.room1)
        self.assertIn(self.char1, self.room1.contents)
        self.assertNotIn(self.char1, self.room2.contents)
        visits = {visit.node_id for visit in parse_knowledge(self.char1)}
        self.assertEqual(visits, {f"room:{int(self.room1.pk)}"})
        self.assertEqual(self.char1.attributes.get("guide_progress"), {})
        self.assertEqual(self.char1.attributes.get("quest_log"), [])
        self.assertFalse(self.room2.db.interacted)
        self.assertIsNone(self.room2.attributes.get("pin_reasons"))
        self.assertEqual(get_world_clock().tick, before)

    def test_npc_traversal_passes_through_the_boundary_without_surfaces(self):
        npc = create_object(NPC, key="npc", location=self.room1)
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        before = get_world_clock().tick
        exit_obj.at_traverse(npc, self.room2)
        self.assertIs(npc.location, self.room2)
        self.assertEqual(get_world_clock().tick, before)
        self.assertIsNone(npc.attributes.get("map_knowledge"))


class MovementSettlementWildernessTests(EvenniaTest):
    """The wilderness gate, step, and return lineages (tasks 3.3, 3.4, 3.5)."""

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
        self.gate = [e for e in self.north_gate.exits if isinstance(e, WildernessGateExit)][0]

    def _exit(self, direction):
        return [e for e in self.char1.location.exits if e.key == direction][0]

    def _script(self):
        return WildernessScript.objects.get(db_key=WILDERNESS_NAME)

    def _bookkeeping(self):
        script = self._script()
        return (
            dict(script.db.itemcoordinates),
            dict(script.db.rooms),
            list(script.db.unused_rooms),
        )

    def _assert_rooms_coherent(self):
        """Every bookkeeping room must be the room actively bound to its key."""
        for coordinates, room in self._script().db.rooms.items():
            self.assertEqual(room.ndb.active_coordinates, coordinates)

    def test_gate_entry_charge_failure_returns_player_to_the_grid_room(self):
        self.char1.location = self.north_gate
        before_bookkeeping = self._bookkeeping()
        before = get_world_clock().tick
        with patch.object(WorldClock, "advance", _failing_advance):
            with self.assertRaises(RuntimeError):
                self.gate.at_traverse(self.char1, self.north_gate)
        self.assertIs(self.char1.location, self.north_gate)
        self.assertNotIn(self.char1, self._script().db.itemcoordinates)
        self.assertEqual(get_world_clock().tick, before)
        # The fresh entry room (and its exits and population monster) rolled
        # back, and no zombie room is retained in the bookkeeping.
        self.assertEqual(self._bookkeeping(), before_bookkeeping)
        self._assert_rooms_coherent()

    def test_gate_entry_charge_failure_with_fresh_room_keeps_no_zombie_rooms(self):
        self.char1.location = self.north_gate
        # The first entry creates a fresh wilderness room; after the failure
        # the bookkeeping must be empty with nothing left in unused_rooms.
        self.assertEqual(self._bookkeeping()[2], [])
        with patch.object(WorldClock, "advance", _failing_advance):
            with self.assertRaises(RuntimeError):
                self.gate.at_traverse(self.char1, self.north_gate)
        itemcoordinates, rooms, unused_rooms = self._bookkeeping()
        self.assertEqual((itemcoordinates, rooms, unused_rooms), ({}, {}, []))
        self._assert_rooms_coherent()

    def test_gate_entry_failure_after_follow_returns_the_wilderness_companion(self):
        self.char1.location = self.north_gate
        npc = create_object(NPC, key="同伴", location=self.north_gate)
        join_party(npc, self.char1)
        before_tick = get_world_clock().tick
        before_bookkeeping = self._bookkeeping()
        with patch(
            "world.rules.onboarding.observe_room_entry",
            side_effect=RuntimeError("room-entry observer failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.gate.at_traverse(self.char1, self.north_gate)
        self.assertIs(self.char1.location, self.north_gate)
        self.assertIs(npc.location, self.north_gate)
        self.assertIn(self.char1, self.north_gate.contents)
        self.assertIn(npc, self.north_gate.contents)
        self.assertEqual(get_world_clock().tick, before_tick)
        script = self._script()
        self.assertNotIn(self.char1, script.db.itemcoordinates)
        self.assertNotIn(npc, script.db.itemcoordinates)
        self.assertEqual(self._bookkeeping(), before_bookkeeping)
        self._assert_rooms_coherent()

    def test_step_charge_failure_returns_player_to_the_source_coordinates(self):
        script = self._script()
        real_advance = WorldClock.advance
        with patch.object(WorldClock, "advance", _flaky_advance(real_advance)):
            self.gate.at_traverse(self.char1, self.north_gate)
            before_tick = get_world_clock().tick
            before_coords = self.char1.location.coordinates
            before_bookkeeping = self._bookkeeping()
            with self.assertRaises(RuntimeError):
                self._exit("east").at_traverse(self.char1, self.char1.location)
        self.assertEqual(get_world_clock().tick, before_tick)
        self.assertEqual(self.char1.location.coordinates, before_coords)
        self.assertEqual(script.itemcoordinates[self.char1], before_coords)
        self.assertEqual(self._bookkeeping(), before_bookkeeping)
        self._assert_rooms_coherent()

    def test_return_charge_failure_re_registers_the_player_at_the_entry(self):
        script = self._script()
        real_advance = WorldClock.advance
        with patch.object(WorldClock, "advance", _flaky_advance(real_advance)):
            self.gate.at_traverse(self.char1, self.north_gate)
            before_tick = get_world_clock().tick
            before_knowledge = {visit.node_id for visit in parse_knowledge(self.char1)}
            before_bookkeeping = self._bookkeeping()
            with self.assertRaises(RuntimeError):
                self._exit("south").at_traverse(self.char1, self.char1.location)
        # The grid return relocated the player and deregistered them; the
        # failed charge is compensated by re-registering at the source
        # coordinates, with the recycled source room recreated or reused.
        self.assertEqual(get_world_clock().tick, before_tick)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        self.assertEqual(self.char1.location.coordinates, ENTRY_XY)
        self.assertEqual(script.itemcoordinates[self.char1], ENTRY_XY)
        self.assertEqual(
            {visit.node_id for visit in parse_knowledge(self.char1)}, before_knowledge
        )
        self.assertEqual(self._bookkeeping(), before_bookkeeping)
        self._assert_rooms_coherent()

    def test_falsy_return_after_relocation_is_compensated(self):
        script = self._script()
        self.gate.at_traverse(self.char1, self.north_gate)
        before_tick = get_world_clock().tick
        before_knowledge = {visit.node_id for visit in parse_knowledge(self.char1)}
        before_bookkeeping = self._bookkeeping()
        # A destination hook raising after relocation makes ``move_to`` return
        # False with the player already standing in the grid room: the boundary
        # compensates the falsy return as a failure.
        with patch.object(
            self.north_gate, "at_object_receive", side_effect=RuntimeError("hook failed")
        ):
            result = self._exit("south").at_traverse(self.char1, self.char1.location)
        self.assertFalse(result)
        self.assertEqual(get_world_clock().tick, before_tick)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        self.assertEqual(self.char1.location.coordinates, ENTRY_XY)
        self.assertEqual(script.itemcoordinates[self.char1], ENTRY_XY)
        self.assertEqual({visit.node_id for visit in parse_knowledge(self.char1)}, before_knowledge)
        self.assertEqual(self._bookkeeping(), before_bookkeeping)
        self._assert_rooms_coherent()
