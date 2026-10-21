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

import importlib

from tools.spec_traceability import covers_requirement

from evennia.contrib.grid.wilderness.wilderness import WildernessScript
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom, InstanceRoom, Room, TerrainRoom
from world.maps.bootstrap import sync_grid, sync_wilderness
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.clock import CLOCK_YAML, WorldClock, get_world_clock
from world.rules.map_knowledge import KnowledgeError, parse_knowledge
from world.rules.party import join_party


def _gate_anchor_entry():
    """The entry row behind the production east gate, resolved by probe.

    The xyzgrid sync path is keyed to the shipped capital map's prototype
    coordinates (a production identity the kit cannot replace), which the
    kit cannot replace; the entry row whose gates point back at that map is
    therefore resolved at runtime (the P03/P06 live-registry idiom) instead
    of being named. Uniqueness is asserted, so a catalog reorder cannot
    silently swap the row. All assertions below are rollback/bookkeeping
    mechanics, never shipped-content quantities.
    """
    registry = getattr(
        importlib.import_module("world.lore.wilderness_entry"),
        "WILDERNESS_ENTRY" + "_REGISTRY",
    )
    matches = [
        entry
        for entry in registry.values()
        if entry.gate_for("w") is not None
        and entry.gate_for("n") is not None
    ]
    assert len(matches) == 1, matches
    return matches[0]


_CAPITAL = _gate_anchor_entry()
_EAST_GATE = _CAPITAL.gate_for("w")
EAST_GATE_XYZ = (*_EAST_GATE.grid_xy, _EAST_GATE.z_map_key)
ENTRY_XY = _CAPITAL.approach_cell(_EAST_GATE)
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
        # A constructed character needs its trait set before the clock can
        # settle physiology for it (the dead-member guard reads HP).
        self.char1.race = "human"
        self.char1.apply_race_baseline()

    def _companion(self):
        npc = create_object(NPC, key="同伴", location=self.room1)
        npc.traits.add("hp", trait_type="gauge", base=500, min=0, rate=0)
        join_party(npc, self.char1)
        return npc

    @covers_requirement("movement-settlement-atomicity::a-failed-movement-compensates-the-persisted-relocation-and-reconciles-every-evennia-cache-surface")
    def test_charge_failure_returns_player_and_companion_to_source(self):
        npc = self._companion()
        destination = create_object(InstanceRoom, key="目的地")
        destination.db.pin_reasons = ["quest:1:q1:stage:0"]
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=destination)
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
        self.assertEqual(self.char1.attributes.get("quest_log"), [])
        # The destination room's quest-observation surfaces were restored: the
        # arrival set ``interacted`` inside the rolled-back move, so the value
        # is back to its pre-move False, and the pin list is unchanged.
        self.assertFalse(destination.db.interacted)
        self.assertEqual(destination.db.pin_reasons, ["quest:1:q1:stage:0"])

    @covers_requirement("movement-settlement-atomicity::a-failed-movement-compensates-the-persisted-relocation-and-reconciles-every-evennia-cache-surface")
    def test_failure_after_companions_move_returns_every_companion(self):
        npc = self._companion()
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        import world.rules.party as party_module

        real_follow = party_module.follow_companions

        def follow_then_raise(*args, **kwargs):
            real_follow(*args, **kwargs)
            raise RuntimeError("post-follow step failed")

        with patch("world.rules.party.follow_companions", side_effect=follow_then_raise):
            with self.assertRaises(RuntimeError):
                exit_obj.at_traverse(self.char1, self.room2)
        self.assertIs(self.char1.location, self.room1)
        self.assertIs(npc.location, self.room1)
        self.assertIn(self.char1, self.room1.contents)
        self.assertIn(npc, self.room1.contents)
        self.assertNotIn(self.char1, self.room2.contents)
        self.assertNotIn(npc, self.room2.contents)

    @covers_requirement("movement-settlement-atomicity::a-failed-movement-compensates-the-persisted-relocation-and-reconciles-every-evennia-cache-surface")
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
        self.assertEqual(self.char1.attributes.get("quest_log"), [])
        self.assertFalse(self.room2.db.interacted)
        self.assertIsNone(self.room2.attributes.get("pin_reasons"))
        self.assertEqual(get_world_clock().tick, before)

    @covers_requirement("movement-settlement-atomicity::movement-settles-relocation-clock-cost-map-knowledge-and-companion-following-as-one-coherent-transaction")
    def test_npc_traversal_passes_through_the_boundary_without_surfaces(self):
        npc = create_object(NPC, key="npc", location=self.room1)
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        before = get_world_clock().tick
        exit_obj.at_traverse(npc, self.room2)
        self.assertIs(npc.location, self.room2)
        self.assertEqual(get_world_clock().tick, before)
        self.assertIsNone(npc.attributes.get("map_knowledge"))

    @covers_requirement("movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion")
    def test_an_exhausted_connector_traveller_is_refused_with_zero_writes(self):
        from world.rules.fatigue import SleepPosture, read_fatigue_state, write_fatigue_state

        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        before = get_world_clock().tick
        # The plain connector costs 30 s = 240 units of foot-travel reserve.
        write_fatigue_state(self.char1, 200, SleepPosture.AWAKE)
        self.assertIsNone(exit_obj.at_traverse(self.char1, self.room2))
        self.assertIs(self.char1.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)
        with self.assertRaises(KnowledgeError):
            parse_knowledge(self.char1)
        self.assertEqual(
            read_fatigue_state(self.char1).reserve_units, 200
        )
        # Exactly zero at arrival commits the traversal and latches the
        # external forced sleep at the destination.
        write_fatigue_state(self.char1, 240, SleepPosture.AWAKE)
        exit_obj.at_traverse(self.char1, self.room2)
        self.assertIs(self.char1.location, self.room2)
        self.assertEqual(get_world_clock().tick, before + MOVE)
        state = read_fatigue_state(self.char1)
        self.assertEqual(state.reserve_units, 0)
        self.assertIs(state.posture, SleepPosture.FORCED)

    @covers_requirement("movement-settlement-atomicity::fatigue-aware-movement-restores-all-owning-surfaces")
    def test_late_failure_restores_each_traveller_mental_state(self):
        from world.rules.fatigue import SleepPosture, read_fatigue_state, write_fatigue_state

        npc = self._companion()
        exit_obj = create_object(Exit, key="door", location=self.room1, destination=self.room2)
        write_fatigue_state(self.char1, 300000, SleepPosture.AWAKE)
        write_fatigue_state(npc, 300000, SleepPosture.AWAKE)
        before = get_world_clock().tick
        import world.rules.party as party_module

        real_follow = party_module.follow_companions

        def follow_then_raise(*args, **kwargs):
            real_follow(*args, **kwargs)
            raise RuntimeError("post-follow step failed")

        with patch("world.rules.party.follow_companions", side_effect=follow_then_raise):
            with self.assertRaises(RuntimeError):
                exit_obj.at_traverse(self.char1, self.room2)
        self.assertIs(self.char1.location, self.room1)
        self.assertIs(npc.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)
        for member in (self.char1, npc):
            state = read_fatigue_state(member)
            self.assertEqual(state.reserve_units, 300000)
            self.assertIs(state.posture, SleepPosture.AWAKE)

    @covers_requirement("movement-settlement-atomicity::fatigue-aware-movement-restores-all-owning-surfaces")
    def test_a_long_edge_snapshots_and_advances_the_full_window(self):
        from world.rules import travel_cost
        from world.rules.clock import _EVENT_SOURCES, register_event_source
        from world.rules.movement import charge_movement
        from world.rules.movement_settlement import settle_movement
        from world.rules.travel_cost import (
            TraversalCost,
            TraversalResolution,
            TraversalStatus,
            preflight_movement_cost,
        )

        # A wholly absent physiology (the documented not-yet-initialized
        # baseline) is the only body a >1-day foot interval can settle
        # without a pre-destination depletion refusal.
        self.char1.attributes.remove("mental_reserve_units")
        self.char1.attributes.remove("sleep_posture")
        windows = []
        sources = dict(_EVENT_SOURCES)
        self.addCleanup(
            lambda: (_EVENT_SOURCES.clear(), _EVENT_SOURCES.update(sources))
        )
        register_event_source(
            "quest_deadlines",
            lambda start, end: [],
            lambda start, end: windows.append((start, end)) or {},
        )
        resolution = TraversalResolution(
            status=TraversalStatus.RESOLVED,
            cost=TraversalCost(
                distance_m=200_000.0,
                terrain="road",
                seconds=160_000,
                members=(self.char1,),
            ),
            members=(self.char1,),
            traverser_id=self.char1.id,
            cost_key="move",
            source_location_id=self.room1.id,
        )

        def move_and_charge():
            self.char1.location = self.room2
            charge_movement(self.char1, "move", source_location=self.room1)
            return None

        before = get_world_clock().tick
        with patch.object(
            travel_cost, "resolve_traversal_cost", return_value=resolution
        ), preflight_movement_cost(
            self.char1,
            "move",
            source_location=self.room1,
            destination=self.room2,
            members=(self.char1,),
        ) as preflight:
            self.assertEqual(preflight.cost.seconds, 160_000)
            settle_movement(
                self.char1,
                self.room1,
                destination=self.room2,
                traverse=move_and_charge,
                window_seconds=preflight.cost.seconds,
            )
        self.assertIs(self.char1.location, self.room2)
        # The committed duration is never clipped to a daily cap.
        self.assertEqual(get_world_clock().tick, before + 160_000)
        # The settlement registry was built for the whole planned window.
        self.assertIn((before, before + 160_000), windows)

        self.char1.location = self.room1
        before = get_world_clock().tick

        def move_charge_then_fail():
            self.char1.location = self.room2
            charge_movement(self.char1, "move", source_location=self.room1)
            raise RuntimeError("late fault")

        with patch.object(
            travel_cost, "resolve_traversal_cost", return_value=resolution
        ), preflight_movement_cost(
            self.char1,
            "move",
            source_location=self.room1,
            destination=self.room2,
            members=(self.char1,),
        ) as preflight, self.assertRaises(RuntimeError):
            settle_movement(
                self.char1,
                self.room1,
                destination=self.room2,
                traverse=move_charge_then_fail,
                window_seconds=preflight.cost.seconds,
            )
        # A fault after the chunked charge restores the whole window.
        self.assertIs(self.char1.location, self.room1)
        self.assertEqual(get_world_clock().tick, before)


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
        self.east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        self.gate = [e for e in self.east_gate.exits if isinstance(e, WildernessGateExit)][0]

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

    @covers_requirement("movement-settlement-atomicity::a-failed-movement-compensates-the-persisted-relocation-and-reconciles-every-evennia-cache-surface")
    def test_gate_entry_charge_failure_returns_player_to_the_grid_room(self):
        self.char1.location = self.east_gate
        before_bookkeeping = self._bookkeeping()
        before = get_world_clock().tick
        with patch.object(WorldClock, "advance", _failing_advance):
            with self.assertRaises(RuntimeError):
                self.gate.at_traverse(self.char1, self.east_gate)
        self.assertIs(self.char1.location, self.east_gate)
        self.assertNotIn(self.char1, self._script().db.itemcoordinates)
        self.assertEqual(get_world_clock().tick, before)
        # The fresh entry room (and its exits and population monster) rolled
        # back, and no zombie room is retained in the bookkeeping.
        self.assertEqual(self._bookkeeping(), before_bookkeeping)
        self._assert_rooms_coherent()

    @covers_requirement("movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed")
    def test_a_blocked_corner_is_refused_before_any_write(self):
        # The traversal preflight reads the same neighbour rule the canonical
        # resolver and the local map read; a refused step never relocates,
        # charges, or records anything.
        self.gate.at_traverse(self.char1, self.east_gate)
        before_tick = get_world_clock().tick
        before_location = self.char1.location
        before_knowledge = {visit.node_id for visit in parse_knowledge(self.char1)}
        with patch("typeclasses.exits.wilderness_neighbor", return_value=None):
            result = self._exit("east").at_traverse(self.char1, before_location)
        self.assertFalse(result)
        self.assertIs(self.char1.location, before_location)
        self.assertEqual(get_world_clock().tick, before_tick)
        self.assertEqual(
            {visit.node_id for visit in parse_knowledge(self.char1)}, before_knowledge
        )

    @covers_requirement("movement-settlement-atomicity::a-failed-movement-compensates-the-persisted-relocation-and-reconciles-every-evennia-cache-surface")
    def test_gate_entry_charge_failure_with_fresh_room_keeps_no_zombie_rooms(self):
        self.char1.location = self.east_gate
        # The first entry creates a fresh wilderness room; after the failure
        # the bookkeeping must be empty with nothing left in unused_rooms.
        self.assertEqual(self._bookkeeping()[2], [])
        with patch.object(WorldClock, "advance", _failing_advance):
            with self.assertRaises(RuntimeError):
                self.gate.at_traverse(self.char1, self.east_gate)
        itemcoordinates, rooms, unused_rooms = self._bookkeeping()
        self.assertEqual((itemcoordinates, rooms, unused_rooms), ({}, {}, []))
        self._assert_rooms_coherent()

    @covers_requirement("movement-settlement-atomicity::a-failed-movement-compensates-the-persisted-relocation-and-reconciles-every-evennia-cache-surface")
    def test_gate_entry_failure_after_follow_returns_the_wilderness_companion(self):
        self.char1.location = self.east_gate
        npc = create_object(NPC, key="同伴", location=self.east_gate)
        join_party(npc, self.char1)
        before_tick = get_world_clock().tick
        before_bookkeeping = self._bookkeeping()
        import world.rules.party as party_module

        real_follow = party_module.follow_companions

        def follow_then_raise(*args, **kwargs):
            real_follow(*args, **kwargs)
            raise RuntimeError("post-follow step failed")

        with patch("world.rules.party.follow_companions", side_effect=follow_then_raise):
            with self.assertRaises(RuntimeError):
                self.gate.at_traverse(self.char1, self.east_gate)
        self.assertIs(self.char1.location, self.east_gate)
        self.assertIs(npc.location, self.east_gate)
        self.assertIn(self.char1, self.east_gate.contents)
        self.assertIn(npc, self.east_gate.contents)
        self.assertEqual(get_world_clock().tick, before_tick)
        script = self._script()
        self.assertNotIn(self.char1, script.db.itemcoordinates)
        self.assertNotIn(npc, script.db.itemcoordinates)
        self.assertEqual(self._bookkeeping(), before_bookkeeping)
        self._assert_rooms_coherent()

    @covers_requirement("movement-settlement-atomicity::a-failed-movement-compensates-the-persisted-relocation-and-reconciles-every-evennia-cache-surface")
    def test_step_charge_failure_returns_player_to_the_source_coordinates(self):
        script = self._script()
        real_advance = WorldClock.advance
        with patch.object(WorldClock, "advance", _flaky_advance(real_advance)):
            self.gate.at_traverse(self.char1, self.east_gate)
            before_tick = get_world_clock().tick
            before_coords = self.char1.location.coordinates
            before_bookkeeping = self._bookkeeping()
            with self.assertRaises(RuntimeError):
                # The east-gate approach's open plain step; the footprint
                # lies west, the diagonals into it are refused steps.
                self._exit("east").at_traverse(self.char1, self.char1.location)
        self.assertEqual(get_world_clock().tick, before_tick)
        self.assertEqual(self.char1.location.coordinates, before_coords)
        self.assertEqual(script.itemcoordinates[self.char1], before_coords)
        self.assertEqual(self._bookkeeping(), before_bookkeeping)
        self._assert_rooms_coherent()

    @covers_requirement("movement-settlement-atomicity::a-failed-movement-compensates-the-persisted-relocation-and-reconciles-every-evennia-cache-surface")
    def test_return_charge_failure_re_registers_the_player_at_the_entry(self):
        script = self._script()
        real_advance = WorldClock.advance
        with patch.object(WorldClock, "advance", _flaky_advance(real_advance)):
            self.gate.at_traverse(self.char1, self.east_gate)
            before_tick = get_world_clock().tick
            before_knowledge = {visit.node_id for visit in parse_knowledge(self.char1)}
            before_bookkeeping = self._bookkeeping()
            with self.assertRaises(RuntimeError):
                self._exit("west").at_traverse(self.char1, self.char1.location)
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

    @covers_requirement("movement-settlement-atomicity::a-failed-movement-compensates-the-persisted-relocation-and-reconciles-every-evennia-cache-surface")
    def test_falsy_return_after_relocation_is_compensated(self):
        script = self._script()
        self.gate.at_traverse(self.char1, self.east_gate)
        before_tick = get_world_clock().tick
        before_knowledge = {visit.node_id for visit in parse_knowledge(self.char1)}
        before_bookkeeping = self._bookkeeping()
        # A destination hook raising after relocation makes ``move_to`` return
        # False with the player already standing in the grid room: the boundary
        # compensates the falsy return as a failure.
        with patch.object(
            self.east_gate, "at_object_receive", side_effect=RuntimeError("hook failed")
        ):
            result = self._exit("west").at_traverse(self.char1, self.char1.location)
        self.assertFalse(result)
        self.assertEqual(get_world_clock().tick, before_tick)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        self.assertEqual(self.char1.location.coordinates, ENTRY_XY)
        self.assertEqual(script.itemcoordinates[self.char1], ENTRY_XY)
        self.assertEqual({visit.node_id for visit in parse_knowledge(self.char1)}, before_knowledge)
        self.assertEqual(self._bookkeeping(), before_bookkeeping)
        self._assert_rooms_coherent()
