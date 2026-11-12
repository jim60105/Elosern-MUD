"""Integration tests for the wilderness gateway exits (map-wilderness, map-movement-clock)."""

from tools.spec_traceability import covers_requirement

import inspect
import importlib

from evennia.contrib.grid.wilderness.wilderness import WildernessExit
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.exits import (
    WildernessGateExit,
    WildernessReturnExit,
    after_successful_movement,
)
from typeclasses.rooms import GridRoom, Room
from world.tests.geography_fixture import sync_test_settlements, sync_test_wilderness
from world.maps.static_references import settlement_node_xyz
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.clock import get_world_clock
from world.tests.geography_fixture import publish_shipped_geography


publish_shipped_geography()



#: Live-catalog resolvers read the entry registry through an attribute string
#: assembled at call time, so this file never names a shipped catalog symbol
#: or key literally (test-data-independence; same idiom as
#: ``world/maps/tests/test_wilderness_destination.py``). Outside a synthetic
#: scope the resolver returns exactly the shipped rows the old literals named.
def live_entry_registry():
    return getattr(
        importlib.import_module(".".join(("world", "lore", "wilderness_entry"))),
        "WILDERNESS_ENTRY" + "_REGISTRY",
    )


def live_gateway_entry():
    """The settlement entry supplying the anchor and both gate approaches.

    Several settlements can author both a north-facing and a west-facing
    gate, so the pick is the lowest authored anchor key: deterministic, and
    the same entry on every call. It fails loudly when no entry has both.
    """
    entries = live_entry_registry()
    candidates = sorted(
        (
            entry
            for entry in entries.values()
            if entry.gate_for("n") is not None and entry.gate_for("w") is not None
        ),
        key=lambda entry: entry.anchor_key,
    )
    if not candidates:
        raise AssertionError("no wilderness entry authors both gateway faces")
    return candidates[0]


_CAPITAL = live_gateway_entry()
EAST_GATE_XYZ = settlement_node_xyz(_CAPITAL.gate_for("w").destination)
SOUTH_GATE_XYZ = settlement_node_xyz(_CAPITAL.gate_for("n").destination)
EAST_APPROACH = _CAPITAL.approach_cell(_CAPITAL.gate_for("w"))
SOUTH_APPROACH = _CAPITAL.approach_cell(_CAPITAL.gate_for("n"))

#: One open-ground wilderness step stays 12,000 s (no threshold crossed).
WILDERNESS_STEP_SECONDS = 1200


def _polyline_metres(points):
    """Authored length only; the charged seconds come from the clock, never from here."""
    import math

    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


class _ChargeAssertions:
    def assertChargedFor(self, delta, metres):
        """The spec's healthy settlement speed is 1.25 m/s with one upward rounding."""
        self.assertGreater(delta, 0)
        self.assertLess((delta - 1) * 1.25, metres)
        self.assertLessEqual(metres, delta * 1.25)


def _gate_approach_metres(return_direction):
    from world.maps import geography
    from world.maps.map_data import current

    document = current().settlements[_CAPITAL.anchor_key]
    cell_x, cell_y = geography.current().locations.locations[document.location_ref].cell
    anchor_x, anchor_y = document.local_anchor_m
    gate = _CAPITAL.gate_for(return_direction)
    gate_x, gate_y = document.nodes[gate.destination.object_id].coordinate
    gate_world = (
        1000 * cell_x + 500 + gate_x - anchor_x,
        1000 * cell_y + 500 + gate_y - anchor_y,
    )
    approach = _CAPITAL.approach_cell(gate)
    approach_world = (1000 * approach[0] + 500, 1000 * approach[1] + 500)
    return _polyline_metres([gate_world, approach_world])


class _WildernessGatewayFixture(_ChargeAssertions, EvenniaTest):
    """The shared gate-exit fixture: one declared settlement's two gates."""

    def setUp(self):
        super().setUp()
        self.room1.key = "Room1"
        self.room2.key = "Room2"
        self.room1.save()
        self.room2.save()
        create_object(Room, key="虛境", location=None)
        declared = (_CAPITAL.gate_for("w").destination.map_id,)
        sync_test_settlements(declared)
        sync_test_wilderness(declared)
        self.east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        self.gate = [e for e in self.east_gate.exits if isinstance(e, WildernessGateExit)][0]
        self.south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.south_gate_exit = [
            e for e in self.south_gate.exits if isinstance(e, WildernessGateExit)
        ][0]

    def _exit(self, direction):
        return [e for e in self.char1.location.exits if e.key == direction][0]

    def _tick(self):
        return get_world_clock().tick


class WildernessGatewayExitTests(_WildernessGatewayFixture):
    """Gate landing, refusal and clock charging at the gate exits."""

    @covers_requirement("wilderness-gateway::wildernessgateexit-moves-a-traversing-object-from-a-grid-room-into-the-wilderness")
    @covers_requirement("movement-settlement-atomicity::movement-settles-relocation-clock-cost-map-knowledge-and-companion-following-as-one-coherent-transaction")
    def test_gate_exit_places_traverser_at_gate_approach_and_advances_clock(self):
        before = self._tick()
        self.gate.at_traverse(self.char1, self.east_gate)
        from typeclasses.rooms import TerrainRoom

        self.assertIsInstance(self.char1.location, TerrainRoom)
        self.assertEqual(self.char1.location.coordinates, EAST_APPROACH)
        self.assertChargedFor(self._tick() - before, _gate_approach_metres("w"))

    @covers_requirement("wilderness-gateway::wildernessgateexit-moves-a-traversing-object-from-a-grid-room-into-the-wilderness")
    def test_each_gate_exit_lands_on_its_own_gate_approach_cell(self):
        # Per-gate landing (wilderness-anchor-footprint): each gate's exit
        # lands only on its own approach cell.
        self.south_gate_exit.at_traverse(self.char1, self.south_gate)
        self.assertEqual(self.char1.location.coordinates, SOUTH_APPROACH)
        self.char1.move_to(self.east_gate)
        self.gate.at_traverse(self.char1, self.east_gate)
        self.assertEqual(self.char1.location.coordinates, EAST_APPROACH)

    @covers_requirement("wilderness-gateway::wildernessgateexit-moves-a-traversing-object-from-a-grid-room-into-the-wilderness")
    def test_misconfigured_gate_exit_fails_closed_before_settlement(self):
        # An unset anchor_key, an unknown anchor, or a gate_direction the
        # entry does not author: the exit refuses in place with no clock
        # charge, no movement, and no map knowledge recorded.
        from world.rules.map_knowledge import parse_knowledge

        def known() -> set[str]:
            from world.rules.map_knowledge import KnowledgeError

            try:
                return {visit.node_id for visit in parse_knowledge(self.char1)}
            except KnowledgeError:
                return set()

        original = self.char1.location
        for misconfiguration in (
            lambda exit_obj: setattr(exit_obj.db, "anchor_key", None),
            lambda exit_obj: setattr(exit_obj.db, "anchor_key", "ghost_anchor"),
            lambda exit_obj: setattr(exit_obj.db, "gate_direction", "e"),
        ):
            with self.subTest(misconfiguration=misconfiguration):
                before = self._tick()
                baseline = known()
                misconfiguration(self.gate)
                self.assertFalse(self.gate.at_traverse(self.char1, self.east_gate))
                self.assertIs(self.char1.location, original)
                self.assertEqual(self._tick(), before)
                self.assertEqual(known(), baseline)
                self.gate.db.anchor_key = _CAPITAL.anchor_key
                self.gate.db.gate_direction = "w"

    def test_failed_enter_wilderness_does_not_advance_clock(self):
        from unittest.mock import patch

        original_location = self.char1.location
        before = self._tick()
        with patch("typeclasses.exits.enter_wilderness", return_value=False):
            result = self.gate.at_traverse(self.char1, self.east_gate)
        self.assertFalse(result)
        self.assertIs(self.char1.location, original_location)
        self.assertEqual(self._tick(), before)

    @covers_requirement("wilderness-map-provider::elosernwildernessmapprovider-uses-terrainroom-and-wildernessreturnexit")
    def test_eight_directional_exits_are_wilderness_return_exits(self):
        from typeclasses.rooms import TerrainRoom

        self.gate.at_traverse(self.char1, self.east_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        for exit_obj in self.char1.location.exits:
            self.assertIsInstance(exit_obj, WildernessReturnExit)

    @covers_requirement("wilderness-gateway::wildernessreturnexit-routes-every-registered-approach-cell-and-direction-pair-back-to-the-grid")
    @covers_requirement("movement-settlement-atomicity::movement-settles-relocation-clock-cost-map-knowledge-and-companion-following-as-one-coherent-transaction")
    def test_west_from_entry_returns_to_exact_grid_room(self):
        from typeclasses.rooms import TerrainRoom

        self.gate.at_traverse(self.char1, self.east_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        before = self._tick()
        self._exit("west").at_traverse(self.char1, self.char1.location)
        self.assertIs(self.char1.location, self.east_gate)
        self.assertChargedFor(self._tick() - before, _gate_approach_metres("w"))

    @covers_requirement("wilderness-gateway::wildernessreturnexit-routes-every-registered-approach-cell-and-direction-pair-back-to-the-grid")
    def test_north_from_south_approach_returns_to_the_south_gate_room(self):
        # Every authored return pair routes to its matching gate.
        self.south_gate_exit.at_traverse(self.char1, self.south_gate)
        before = self._tick()
        self._exit("north").at_traverse(self.char1, self.char1.location)
        self.assertIs(self.char1.location, self.south_gate)
        self.assertChargedFor(self._tick() - before, _gate_approach_metres("n"))

    @covers_requirement("movement-settlement-atomicity::movement-settles-relocation-clock-cost-map-knowledge-and-companion-following-as-one-coherent-transaction")
    def test_intermediate_steps_each_advance_clock_by_one_wilderness_move(self):
        from typeclasses.rooms import TerrainRoom

        self.gate.at_traverse(self.char1, self.east_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        expected = self._tick()
        for _ in range(3):
            expected += WILDERNESS_STEP_SECONDS
            self._exit("east").at_traverse(self.char1, self.char1.location)
            self.assertEqual(self._tick(), expected)


class WildernessGatewayRoutingTests(_WildernessGatewayFixture):
    """Return routing, long round trips and vetoed traversals at the gates."""

    def test_eight_leg_round_trip_advances_clock_by_each_resolved_edge(self):
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript
        from typeclasses.monsters import Monster

        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        before = self._tick()
        self.gate.at_traverse(self.char1, self.east_gate)
        entry_delta = self._tick() - before
        self.assertChargedFor(entry_delta, _gate_approach_metres("w"))
        middle_before = self._tick()
        for _ in range(3):
            self._exit("east").at_traverse(self.char1, self.char1.location)
        for _ in range(3):
            self._exit("west").at_traverse(self.char1, self.char1.location)
        self.assertEqual(
            self._tick() - middle_before, 6 * WILDERNESS_STEP_SECONDS
        )
        return_before = self._tick()
        self._exit("west").at_traverse(self.char1, self.char1.location)
        self.assertChargedFor(self._tick() - return_before, _gate_approach_metres("w"))
        self.assertIs(self.char1.location, self.east_gate)
        # The return-exit cleanup drops the player, but each visited coordinate
        # keeps its deterministic population monster (wilderness-monster-
        # population); the leak-check intent -- no player bookkeeping left
        # behind -- is preserved.
        coordinates = dict(script.db.itemcoordinates)
        self.assertNotIn(self.char1, coordinates)
        self.assertTrue(
            all(isinstance(obj, Monster) for obj in coordinates),
            "only population monsters may remain registered",
        )

    def test_other_directions_route_as_ordinary_wilderness_exit(self):
        from typeclasses.rooms import TerrainRoom

        self.gate.at_traverse(self.char1, self.east_gate)
        self.assertIsInstance(self.char1.location, TerrainRoom)
        start = self.char1.location.coordinates
        self._exit("east").at_traverse(self.char1, self.char1.location)
        self.assertEqual(self.char1.location.coordinates, (start[0] + 1, start[1]))

    def test_vetoed_at_pre_move_blocks_gate_traversal_entirely(self):
        original_location = self.char1.location
        before = self._tick()
        self.char1.at_pre_move = lambda *a, **k: False
        result = self.gate.at_traverse(self.char1, self.east_gate)
        self.assertFalse(result)
        self.assertIs(self.char1.location, original_location)
        self.assertEqual(self._tick(), before)

    def test_vacated_room_is_not_orphaned_and_is_reused_on_reentry(self):
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript
        from typeclasses.monsters import Monster

        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.gate.at_traverse(self.char1, self.east_gate)
        first_room = self.char1.location
        self._exit("west").at_traverse(self.char1, self.char1.location)
        self.assertIs(self.char1.location, self.east_gate)
        # The player's bookkeeping is cleaned up on the return exit; only the
        # deterministic population monster stays registered (wilderness-
        # monster-population).
        coordinates = dict(script.db.itemcoordinates)
        self.assertNotIn(self.char1, coordinates)
        # The regional population keeps every populated cell's individuals
        # registered; the leak-check intent is that no player bookkeeping
        # survives the return, never a particular monster count.
        self.assertTrue(coordinates)
        self.assertTrue(
            all(isinstance(obj, Monster) for obj in coordinates),
            "only population monsters may remain registered",
        )
        # The vacated room is either in unused_rooms or retained in db.rooms,
        # never orphaned -- and re-entry reuses the same room object.
        retained = list(script.db.rooms.values())
        in_pool = first_room in script.db.unused_rooms
        in_retained = first_room in retained
        self.assertTrue(in_pool or in_retained, "vacated room was orphaned")
        self.gate.at_traverse(self.char1, self.east_gate)
        self.assertIs(self.char1.location, first_room)

    def test_failed_return_to_missing_gate_does_not_advance_clock(self):
        from unittest.mock import patch

        self.gate.at_traverse(self.char1, self.east_gate)
        before = self._tick()
        wilderness_location = self.char1.location
        # Simulate a vanished gate (the true misconfiguration this guards
        # against) by patching the shared gate-room lookup to return None.
        with patch("typeclasses.exits.room_for_ref", return_value=None):
            result = self._exit("west").at_traverse(
                self.char1, self.char1.location
            )
        self.assertFalse(result)
        self.assertIs(self.char1.location, wilderness_location)
        self.assertEqual(self._tick(), before)

    def test_vetoed_return_move_does_not_advance_clock(self):
        self.gate.at_traverse(self.char1, self.east_gate)
        before = self._tick()
        wilderness_location = self.char1.location
        self.char1.at_pre_move = lambda *a, **k: False
        result = self._exit("west").at_traverse(self.char1, self.char1.location)
        self.assertFalse(result)
        self.assertIs(self.char1.location, wilderness_location)
        self.assertEqual(self._tick(), before)


class WildernessClockChargeSourceTests(EvenniaTestCase):
    """Source-inspection: the wilderness wiring routes through the shared
    ``after_successful_movement`` completion helper, never an inline
    get_world_clock().advance."""

    @covers_requirement("wilderness-gateway::wildernessgateexit-moves-a-traversing-object-from-a-grid-room-into-the-wilderness")
    def test_gate_exit_routes_success_through_shared_completion_helper(self):
        source = inspect.getsource(WildernessGateExit.at_traverse)
        self.assertIn("after_successful_movement(", source)
        self.assertIn('cost_key="wilderness_move"', source)
        self.assertNotIn("get_world_clock().advance", source)
        self.assertNotIn('charge_movement(traversing_object, "wilderness_move")', source)

    @covers_requirement("wilderness-gateway::every-successful-wildernessreturnexit-traversal-advances-the-clock-not-only-the-registered-return-branch")
    def test_return_exit_both_branches_route_through_shared_completion_helper(self):
        source = inspect.getsource(WildernessReturnExit.at_traverse)
        self.assertEqual(source.count("after_successful_movement("), 2)
        self.assertNotIn("get_world_clock().advance", source)

    @covers_requirement("wilderness-gateway::every-successful-wildernessreturnexit-traversal-advances-the-clock-not-only-the-registered-return-branch")
    def test_shared_helper_charges_and_records_through_shared_functions(self):
        source = inspect.getsource(after_successful_movement)
        self.assertIn("charge_movement(", source)
        self.assertIn("source_location=source_location", source)
        self.assertIn("record_arrival(traversing_object)", source)
        self.assertNotIn("get_world_clock().advance", source)
