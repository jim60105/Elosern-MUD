"""Stable physical-edge history, legality discovery, and passage visibility.

Pins the ``movement-edge-history`` delta: a completed player edge is retained
by stable locator (never by a pooled room object), retreat pricing delegates to
the same canonical execution arithmetic, and the committed passage interval is
not idle-cell presence at either endpoint.
"""

import importlib
from unittest.mock import patch
import unittest

from evennia.contrib.grid.wilderness.wilderness import WildernessScript
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.npcs import NPC
from typeclasses.rooms import GridRoom, Room
from world.maps.static_references import settlement_node_xyz
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.clock import get_world_clock
from world.rules.fatigue import (
    POSTURE_ATTRIBUTE,
    RESERVE_ATTRIBUTE,
    FatigueActivity,
    FatigueStateError,
    SleepPosture,
    get_policy,
    initialize_fatigue_state,
    write_fatigue_state,
)
from world.rules.movement_edges import (
    KIND_ROOM,
    KIND_WILDERNESS,
    LocationRef,
    LocationRefError,
    MovementEdgeError,
    MovementHistoryError,
    PhysicalEdge,
    decode_location_ref,
    decode_physical_edge,
    encode_location_ref,
    encode_physical_edge,
    legal_edges,
    location_ref,
    quote_edge,
    read_previous_edge,
    record_completed_edge,
    resolve_direction_edge,
    resolve_exit_edge,
)
from world.rules.movement_settlement import (
    TraversalScope,
    field_presence,
    settle_relocation,
    traversal_scope,
)
from world.rules.party import join_party
from world.rules.possession import enter_possession
from world.rules.travel_cost import MovementPreflightRefused, TraversalStatus
from world.tests.geography_fixture import publish_shipped_geography

publish_shipped_geography()


def _gate_anchor_entry():
    """The live registry row the production east gate belongs to."""
    registry = getattr(
        importlib.import_module("world.lore.wilderness_entry"),
        "WILDERNESS_ENTRY" + "_REGISTRY",
    )
    matches = sorted(
        (
            entry
            for entry in registry.values()
            if entry.gate_for("w") is not None and entry.gate_for("n") is not None
        ),
        key=lambda entry: entry.anchor_key,
    )
    assert matches, "no wilderness entry authors both gateway faces"
    return matches[0]


_CAPITAL = _gate_anchor_entry()
_EAST_GATE = _CAPITAL.gate_for("w")
EAST_GATE_XYZ = settlement_node_xyz(_EAST_GATE.destination)
ENTRY_XY = _CAPITAL.approach_cell(_EAST_GATE)

_DIRECTIONS = ("n", "ne", "e", "se", "s", "sw", "w", "nw")
_LONG_KEYS = {
    "n": "north",
    "ne": "northeast",
    "e": "east",
    "se": "southeast",
    "s": "south",
    "sw": "southwest",
    "w": "west",
    "nw": "northwest",
}


class _DummyBody:
    """A stable ``id`` surface for pure passage-visibility assertions."""

    def __init__(self, identifier):
        self.id = identifier


class EdgeCodecTests(unittest.TestCase):
    def test_locators_round_trip_and_reject_inexact_shapes(self):
        wilderness = LocationRef.wilderness(WILDERNESS_NAME, 3, 4)
        room = LocationRef.room(17)
        self.assertEqual(decode_location_ref(encode_location_ref(wilderness)), wilderness)
        self.assertEqual(decode_location_ref(encode_location_ref(room)), room)
        self.assertEqual(
            encode_location_ref(wilderness),
            {"kind": "wilderness", "map": WILDERNESS_NAME, "x": 3, "y": 4},
        )
        self.assertEqual(encode_location_ref(room), {"kind": "room", "id": 17})
        for malformed in (
            {"kind": "wilderness", "map": WILDERNESS_NAME, "x": True, "y": 4},
            {"kind": "wilderness", "map": WILDERNESS_NAME, "x": -1, "y": 4},
            {"kind": "wilderness", "map": WILDERNESS_NAME, "x": 1, "y": 2, "id": 3},
            {"kind": "room", "id": 0},
            {"kind": "room", "id": True},
            {"kind": "room", "id": 3, "x": 1},
            {"kind": "other", "id": 3},
        ):
            with self.subTest(malformed=malformed):
                with self.assertRaises(MovementEdgeError):
                    decode_location_ref(malformed)

    def test_edges_round_trip_and_route_depends_on_source_kind(self):
        edge = PhysicalEdge(
            LocationRef.wilderness(WILDERNESS_NAME, 1, 2),
            LocationRef.wilderness(WILDERNESS_NAME, 2, 2),
            "direction:e",
        )
        self.assertEqual(decode_physical_edge(encode_physical_edge(edge)), edge)
        with self.assertRaises(MovementEdgeError):
            PhysicalEdge(LocationRef.room(1), LocationRef.room(2), "direction:e")
        with self.assertRaises(MovementEdgeError):
            PhysicalEdge(
                LocationRef.wilderness(WILDERNESS_NAME, 1, 2),
                LocationRef.room(2),
                "exit:2",
            )
        with self.assertRaises(MovementEdgeError):
            decode_physical_edge({"source": encode_location_ref(LocationRef.room(1))})


class MovementEdgeTestCase(EvenniaTest):
    """The shipped east gate and its wilderness approach cell."""

    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        create_object(Room, key="虛境", location=None)
        from world.tests.geography_fixture import (
            sync_test_settlements,
            sync_test_wilderness,
        )

        sync_test_settlements((_EAST_GATE.destination.map_id,))
        sync_test_wilderness((_EAST_GATE.destination.map_id,))
        self.east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        self.gate = [
            exit_obj
            for exit_obj in self.east_gate.exits
            if isinstance(exit_obj, WildernessGateExit)
        ][0]

    def _script(self):
        return WildernessScript.objects.get(db_key=WILDERNESS_NAME)

    def _enter_wilderness(self, entity=None):
        entity = entity or self.char1
        entity.location = self.east_gate
        self.gate.at_traverse(entity, self.east_gate)
        return entity

    def _direction_exit(self, entity, direction):
        return [
            exit_obj
            for exit_obj in entity.location.exits
            if getattr(exit_obj, "key", None) == _LONG_KEYS[direction]
        ][0]

    def _ordinary_step(self, entity=None):
        entity = entity or self.char1
        source = location_ref(entity)
        for direction in _DIRECTIONS:
            edge = resolve_direction_edge(
                source, (source.x, source.y), direction
            )
            if edge is not None and edge.destination.kind == KIND_WILDERNESS:
                return direction, edge
        self.fail("the arrival cell has no ordinary wilderness step")

    def _previous_edge(self, body):
        return read_previous_edge(body)


class LocationRefTests(MovementEdgeTestCase):
    def test_pooled_terrain_room_locator_is_coordinates_not_room_id(self):
        self._enter_wilderness()
        location = self.char1.location
        ref = location_ref(self.char1)
        self.assertEqual(ref.kind, KIND_WILDERNESS)
        self.assertEqual((ref.x, ref.y), tuple(location.coordinates))
        self.assertEqual(ref, location_ref(location))
        self.assertEqual(self._script().db.itemcoordinates.get(self.char1), (ref.x, ref.y))

    def test_authored_room_locator_is_the_durable_dbref(self):
        self.char1.location = self.room1
        self.assertEqual(location_ref(self.char1), LocationRef.room(self.room1.id))
        self.assertEqual(location_ref(self.east_gate), LocationRef.room(self.east_gate.id))

    def test_unrepresentable_location_raises_named_error(self):
        from typeclasses.rooms import InstanceRoom

        instance = create_object(InstanceRoom, key="實例")
        self.char1.location = instance
        with self.assertRaises(LocationRefError):
            location_ref(self.char1)

    def test_limbo_receive_gate_is_consulted_read_only(self):
        from typeclasses.rooms import LimboRoom

        limbo = create_object(LimboRoom, key="limbo")
        exit_obj = create_object(
            Exit, key="back", location=self.room1, destination=limbo
        )
        self.char1.location = self.room1
        edge = PhysicalEdge(
            LocationRef.room(self.room1.id),
            LocationRef.room(limbo.id),
            f"exit:{exit_obj.id}",
        )
        self.assertIsNone(resolve_exit_edge(self.char1, exit_obj))
        self.assertNotIn(edge, legal_edges(self.char1, edge.source, (self.char1,)))
        self.assertIs(
            quote_edge(self.char1, edge, (self.char1,)).status,
            TraversalStatus.UNRESOLVED,
        )
        self.assertFalse(self.char1.ndb.limbo_refused)


class LegalEdgeTests(MovementEdgeTestCase):
    def test_gate_room_discovery_contains_the_registered_crossing(self):
        self.char1.location = self.east_gate
        edges = legal_edges(
            self.char1, LocationRef.room(self.east_gate.id), (self.char1,)
        )
        expected = PhysicalEdge(
            LocationRef.room(self.east_gate.id),
            LocationRef.wilderness(WILDERNESS_NAME, *ENTRY_XY),
            f"exit:{self.gate.id}",
        )
        self.assertIn(expected, edges)
        self.assertEqual(len(edges), len(set(edges)))
        self.assertTrue(all(edge.source == expected.source for edge in edges))

    def test_locked_exit_is_not_a_legal_edge(self):
        locked = create_object(
            Exit, key="封閉", location=self.room1, destination=self.room2
        )
        locked.locks.add("traverse:false()")
        self.char1.location = self.room1
        edges = legal_edges(self.char1, LocationRef.room(self.room1.id), (self.char1,))
        self.assertNotIn(
            f"exit:{locked.id}", {edge.route for edge in edges}
        )
        self.assertIsNone(resolve_exit_edge(self.char1, locked))

    def test_approach_cell_routes_the_registered_gateway_and_no_wall_entrance(self):
        source = LocationRef.wilderness(WILDERNESS_NAME, *ENTRY_XY)
        edges = legal_edges(self.char1, source, (self.char1,))
        gateway_edges = [
            edge
            for edge in edges
            if edge.route == f"direction:{_EAST_GATE.return_direction}"
        ]
        self.assertEqual(len(gateway_edges), 1)
        self.assertEqual(
            gateway_edges[0].destination, LocationRef.room(self.east_gate.id)
        )
        for edge in edges:
            self.assertEqual(edge.source, source)
            if edge is gateway_edges[0]:
                continue
            # Only the registered crossing leaves the wilderness here; every
            # other direction is an adjacent provider-valid cell, never an
            # invented entrance through the footprint.
            self.assertEqual(edge.destination.kind, KIND_WILDERNESS)

    def test_discovery_and_quote_are_read_only(self):
        from evennia.objects.models import ObjectDB
        from typeclasses.rooms import TerrainRoom

        self._enter_wilderness()
        source = location_ref(self.char1)
        direction, edge = self._ordinary_step()
        before = (
            ObjectDB.objects.count(),
            TerrainRoom.objects.count(),
            get_world_clock().tick,
            int(getattr(self.char1, "id", 0)),
            self.char1.attributes.get("previous_traversal"),
        )
        legal_edges(self.char1, source, (self.char1,))
        quote_edge(self.char1, edge, (self.char1,))
        after = (
            ObjectDB.objects.count(),
            TerrainRoom.objects.count(),
            get_world_clock().tick,
            int(getattr(self.char1, "id", 0)),
            self.char1.attributes.get("previous_traversal"),
        )
        self.assertEqual(after, before)


class QuotedExecutionAgreementTests(MovementEdgeTestCase):
    def test_quote_matches_the_committed_gate_and_reverse_costs(self):
        self.char1.location = self.east_gate
        forward = resolve_exit_edge(self.char1, self.gate)
        self.assertIsNotNone(forward)
        quote = quote_edge(self.char1, forward, (self.char1,))
        self.assertIs(quote.status, TraversalStatus.RESOLVED)
        before = get_world_clock().tick
        self.gate.at_traverse(self.char1, self.east_gate)
        self.assertEqual(get_world_clock().tick - before, quote.cost.seconds)
        recorded = self._previous_edge(self.char1)
        self.assertEqual(recorded, forward)

        reverse = next(
            edge
            for edge in legal_edges(self.char1, recorded.destination, (self.char1,))
            if edge.destination == recorded.source
        )
        reverse_quote = quote_edge(self.char1, reverse, (self.char1,))
        self.assertIs(reverse_quote.status, TraversalStatus.RESOLVED)
        before = get_world_clock().tick
        self._direction_exit(self.char1, reverse.route.split(":", 1)[1]).at_traverse(
            self.char1, self.char1.location
        )
        self.assertEqual(get_world_clock().tick - before, reverse_quote.cost.seconds)
        self.assertEqual(self.char1.location, self.east_gate)

    def test_quote_matches_the_committed_ordinary_step_cost(self):
        self._enter_wilderness()
        direction, edge = self._ordinary_step()
        quote = quote_edge(self.char1, edge, (self.char1,))
        self.assertIs(quote.status, TraversalStatus.RESOLVED)
        before = get_world_clock().tick
        self._direction_exit(self.char1, direction).at_traverse(
            self.char1, self.char1.location
        )
        self.assertEqual(get_world_clock().tick - before, quote.cost.seconds)
        self.assertEqual(self._previous_edge(self.char1), edge)

    def test_exact_zero_arrival_is_affordable_and_one_unit_less_refuses(self):
        from world.rules.clock import CLOCK_YAML

        exit_obj = create_object(
            Exit, key="door", location=self.room1, destination=self.room2
        )
        self.char1.location = self.room1
        edge = resolve_exit_edge(self.char1, exit_obj)
        seconds = CLOCK_YAML["command_defaults"]["move"]
        rate = abs(int(get_policy().rates[FatigueActivity.FOOT_TRAVEL]))
        initialize_fatigue_state(self.char1)

        write_fatigue_state(self.char1, rate * seconds, SleepPosture.AWAKE)
        exact = quote_edge(self.char1, edge, (self.char1,))
        self.assertIs(exact.status, TraversalStatus.NON_DISTANCE)

        write_fatigue_state(self.char1, rate * seconds - 1, SleepPosture.AWAKE)
        with self.assertRaises(MovementPreflightRefused) as refused:
            quote_edge(self.char1, edge, (self.char1,))
        self.assertEqual(refused.exception.reason, "pre_destination_depletion")

    def test_partial_physiology_refuses_instead_of_pricing(self):
        exit_obj = create_object(
            Exit, key="door", location=self.room1, destination=self.room2
        )
        self.char1.location = self.room1
        edge = resolve_exit_edge(self.char1, exit_obj)
        partial = create_object(NPC, key="partial")
        partial.attributes.remove(POSTURE_ATTRIBUTE)
        partial.attributes.add(RESERVE_ATTRIBUTE, 1000)
        with self.assertRaises(FatigueStateError):
            quote_edge(self.char1, edge, (partial,))

    def test_flight_waived_step_quotes_zero_and_charges_zero(self):
        self._enter_wilderness()
        self.char1.db.skills = {"active": [], "passive": ["flight"]}
        direction, edge = self._ordinary_step()
        quotation = quote_edge(self.char1, edge, (self.char1,))
        self.assertIs(quotation.status, TraversalStatus.RESOLVED)
        self.assertEqual(quotation.cost.seconds, 0)
        before = get_world_clock().tick
        self._direction_exit(self.char1, direction).at_traverse(
            self.char1, self.char1.location
        )
        self.assertEqual(get_world_clock().tick, before)


class MovementHistoryTests(MovementEdgeTestCase):
    def test_relocated_falsy_plain_exit_records_no_completion(self):
        from typeclasses.rooms import Room

        class RaisingReceiveRoom(Room):
            def at_object_receive(self, obj, source_location, **kwargs):
                raise RuntimeError("receive failed")

        self.char1.location = self.room1
        bad = create_object(RaisingReceiveRoom, key="bad")
        exit_obj = create_object(
            Exit, key="door", location=self.room1, destination=bad
        )
        with patch("world.rules.movement_edges.log_info") as logged:
            with self.captureOnCommitCallbacks(execute=True):
                exit_obj.at_traverse(self.char1, bad)
        self.assertFalse(self.char1.attributes.has("previous_traversal"))
        logged.assert_not_called()

    def test_pooled_source_recycles_and_reload_preserves_locators(self):
        self._enter_wilderness()
        entry = self._previous_edge(self.char1)
        self.assertEqual(entry.source, LocationRef.room(self.east_gate.id))
        direction, step = self._ordinary_step()
        departure = step.source
        self._direction_exit(self.char1, direction).at_traverse(
            self.char1, self.char1.location
        )
        recorded = self._previous_edge(self.char1)
        self.assertEqual(recorded.source, departure)
        self.assertEqual(recorded.destination, location_ref(self.char1))
        # A pooled room may keep the same object while its coordinates change;
        # the retained source must still name the departure cell.
        self.char1.attributes.reset_cache()
        self.assertEqual(self._previous_edge(self.char1), recorded)

    def test_failed_traversal_retains_the_previous_record(self):
        self._enter_wilderness()
        recorded = self._previous_edge(self.char1)
        direction, _edge = self._ordinary_step()

        def failing_advance(*args, **kwargs):
            raise RuntimeError("clock advance failed")

        with patch("world.rules.clock.WorldClock.advance", failing_advance):
            with self.assertRaises(RuntimeError):
                self._direction_exit(self.char1, direction).at_traverse(
                    self.char1, self.char1.location
                )
        self.assertEqual(self._previous_edge(self.char1), recorded)
        self.assertEqual(location_ref(self.char1), recorded.destination)

    def test_teleport_invalidates_the_record(self):
        self._enter_wilderness()
        self.assertIsNotNone(self._previous_edge(self.char1))
        settle_relocation(self.char1, self.room2)
        self.assertIsNone(self._previous_edge(self.char1))
        self.assertEqual(self.char1.location, self.room2)

    def test_boundary_events_name_the_body_route_and_tick(self):
        self.char1.location = self.east_gate
        with patch("world.rules.movement_edges.log_info") as logged:
            with self.captureOnCommitCallbacks(execute=True):
                self.gate.at_traverse(self.char1, self.east_gate)
        completion = [
            call.args[0]
            for call in logged.call_args_list
            if call.args and call.args[0] == "movement_edge_completed"
        ]
        self.assertEqual(len(completion), 1)
        context = logged.call_args_list[0].kwargs["context"]
        self.assertIn("tick", context)
        self.assertIn("route", context)
        self.assertIn("source", context)
        self.assertIn("destination", context)

        with patch("world.rules.movement_edges.log_info") as invalidated:
            with self.captureOnCommitCallbacks(execute=True):
                settle_relocation(self.char1, self.room2)
        self.assertEqual(
            [
                call.args[0]
                for call in invalidated.call_args_list
                if call.args and call.args[0] == "movement_history_invalidated"
            ],
            ["movement_history_invalidated"],
        )

    def test_malformed_history_raises_and_stale_destination_is_none(self):
        edge = PhysicalEdge(
            LocationRef.room(self.room1.id),
            LocationRef.room(self.room2.id),
            f"exit:{create_object(Exit, key='door', location=self.room1, destination=self.room2).id}",
        )
        record_completed_edge(self.char1, edge)
        self.char1.location = self.room2
        self.assertEqual(read_previous_edge(self.char1), edge)
        self.char1.location = self.room1
        self.assertIsNone(read_previous_edge(self.char1))
        self.char1.attributes.add("previous_traversal", {"source": {"kind": "room"}})
        with self.assertRaises(MovementHistoryError):
            read_previous_edge(self.char1)
        self.char1.attributes.add("previous_traversal", None)
        with self.assertRaises(MovementHistoryError):
            read_previous_edge(self.char1)
        with self.assertRaises(MovementEdgeError):
            PhysicalEdge(
                LocationRef.wilderness(WILDERNESS_NAME, 1, 2),
                LocationRef.wilderness(WILDERNESS_NAME, 2, 2),
                "direction:e\n",
            )

    def test_fault_after_history_write_restores_source_history_and_tick(self):
        self.char1.location = self.east_gate
        before_tick = get_world_clock().tick
        before_history = self._previous_edge(self.char1)
        script = self._script()
        before_bookkeeping = (
            dict(script.db.itemcoordinates),
            dict(script.db.rooms),
            list(script.db.unused_rooms),
        )
        from world.rules import movement_settlement as settlement

        real_record = settlement._record_completed_history

        def record_then_raise(*args, **kwargs):
            real_record(*args, **kwargs)
            raise RuntimeError("injected post-history fault")

        with patch.object(
            settlement, "_record_completed_history", side_effect=record_then_raise
        ), patch("world.rules.movement_edges.log_info") as logged:
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError):
                    self.gate.at_traverse(self.char1, self.east_gate)

        self.assertEqual(self.char1.location, self.east_gate)
        self.assertEqual(get_world_clock().tick, before_tick)
        self.assertEqual(self._previous_edge(self.char1), before_history)
        self.assertEqual(
            (
                dict(script.db.itemcoordinates),
                dict(script.db.rooms),
                list(script.db.unused_rooms),
            ),
            before_bookkeeping,
        )
        logged.assert_not_called()


class PassageVisibilityTests(MovementEdgeTestCase):
    def test_half_open_interval_has_no_idle_endpoint_presence(self):
        body = _DummyBody(11)
        scope = TraversalScope(
            member_ids=(11,),
            source=LocationRef.room(self.room1.id),
            destination=LocationRef.room(self.room2.id),
            departure_tick=100,
            arrival_tick=150,
        )
        self.assertTrue(field_presence(body, 99))
        with traversal_scope(scope):
            self.assertFalse(field_presence(body, 100))
            self.assertFalse(field_presence(body, 149))
            self.assertTrue(field_presence(body, 150))
            self.assertTrue(field_presence(_DummyBody(12), 120))
        self.assertTrue(field_presence(body, 120))
        self.assertFalse(scope.present(149))
        self.assertTrue(scope.present(150))

    def test_committed_wilderness_step_interval_ends_at_the_accepted_tick(self):
        self._enter_wilderness()
        direction, _edge = self._ordinary_step()
        observed = {}
        from world.rules import movement_settlement as settlement

        def spy(*args, **kwargs):
            observed["scopes"] = settlement._traversal_scopes.get()
            observed["arrival_tick"] = get_world_clock().tick
            scope = observed["scopes"][0]
            observed["present_departure"] = field_presence(
                self.char1, scope.departure_tick
            )
            observed["present_before_arrival"] = field_presence(
                self.char1, scope.arrival_tick - 1
            )
            observed["present_at_arrival"] = field_presence(
                self.char1, observed["arrival_tick"]
            )

        before = get_world_clock().tick
        with patch(
            "world.quests.encounter_dispatch.activate_pending_encounters", spy
        ):
            self._direction_exit(self.char1, direction).at_traverse(
                self.char1, self.char1.location
            )
        scope = observed["scopes"][0]
        self.assertEqual(scope.departure_tick, before)
        self.assertEqual(scope.arrival_tick, observed["arrival_tick"])
        self.assertEqual(scope.destination, location_ref(self.char1))
        self.assertFalse(observed["present_departure"])
        self.assertFalse(observed["present_before_arrival"])
        self.assertTrue(observed["present_at_arrival"])


class PossessedMovementHistoryTests(MovementEdgeTestCase):
    def test_transported_party_records_the_same_edge_and_remote_unchanged(self):
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.location = self.room1
        npc = create_object(NPC, key="艾拉", location=self.room1)
        other = create_object(NPC, key="卡恩", location=self.room1)
        remote = create_object(NPC, key="遠方", location=self.room1)
        for member in (npc, other, remote):
            join_party(member, self.char1)
        enter_possession(self.char1, npc)
        remote.location = self.room2
        self.char1.location = self.east_gate
        npc.location = self.east_gate
        other.location = self.east_gate
        self.gate.at_traverse(npc, self.east_gate)

        edge = self._previous_edge(npc)
        self.assertIsNotNone(edge)
        self.assertEqual(self._previous_edge(self.char1), edge)
        self.assertEqual(self._previous_edge(other), edge)
        self.assertIsNone(self._previous_edge(remote))
        self.assertEqual(remote.location, self.room2)
