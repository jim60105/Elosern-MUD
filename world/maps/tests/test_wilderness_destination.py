from tools.spec_traceability import covers_requirement

"""Tests for the canonical wilderness destination resolver (fix-wilderness-web-navigation).

Covers the resolver's mirror of ``WildernessReturnExit.at_traverse`` routing:
ordinary directions resolve to the adjacent wild cell, the registered gateway
south exit resolves to its grid room, and every unroutable edge resolves to
``None``. The traversal pin tests move a real character through the real
exits and compare the recorded arrival node with the resolver's prediction,
so presentation cannot drift from traversal.
"""

import types
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase, EvenniaTest

from typeclasses.rooms import Room, TerrainRoom
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.lore.sync import sync_all
from world.maps.bootstrap import NORTH_GATE_XYZ, sync_grid, sync_wilderness
from world.maps.wilderness_destination import (
    normalize_wilderness_direction,
    resolve_wilderness_destination,
    wilderness_neighbor,
)
from world.maps.wilderness_provider import (
    WILDERNESS_MAX_X,
    WILDERNESS_MAX_Y,
    WILDERNESS_NAME,
)
from world.rules.map_knowledge import (
    encode_grid,
    encode_wild,
    parse_knowledge,
)


class WildernessDestinationResolverTests(EvenniaTestCase):
    """Resolver semantics against real TerrainRoom instances (no live gates)."""

    def _terrain(self, x: int, y: int) -> TerrainRoom:
        # nohome=True keeps db_home NULL: DEFAULT_HOME (#2) resolution is
        # unreliable inside EvenniaTestCase transactions (idmapper can serve a
        # stale rolled-back object for #2), which would fail the teardown
        # foreign-key check.
        room = create_object(TerrainRoom, key="霧野", nohome=True)
        room.ndb.active_coordinates = (x, y)
        return room

    def _fake_grid_room(self, x: int = 2, y: int = 4):
        return types.SimpleNamespace(xyz=(x, y, "capital_altoria"))

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-and-shared")
    def test_ordinary_directions_resolve_to_adjacent_wild_cells(self):
        # (50, 50) is away from the registered gateway coordinate, so every
        # direction including south is an ordinary wild step.
        room = self._terrain(50, 50)
        expected = {
            "n": (50, 51),
            "ne": (51, 51),
            "e": (51, 50),
            "se": (51, 49),
            "s": (50, 49),
            "sw": (49, 49),
            "w": (49, 50),
            "nw": (49, 51),
        }
        for direction, (nx, ny) in expected.items():
            self.assertEqual(
                resolve_wilderness_destination(room, direction),
                encode_wild(WILDERNESS_NAME, nx, ny),
                direction,
            )

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-and-shared")
    def test_contrib_exit_keys_resolve_through_the_normalizer(self):
        room = self._terrain(60, 100)
        self.assertEqual(
            resolve_wilderness_destination(room, "north"),
            encode_wild(WILDERNESS_NAME, 60, 101),
        )
        self.assertEqual(
            resolve_wilderness_destination(room, "southwest"),
            encode_wild(WILDERNESS_NAME, 59, 99),
        )
        self.assertEqual(normalize_wilderness_direction("northwest"), "nw")
        self.assertEqual(normalize_wilderness_direction("se"), "se")
        self.assertIsNone(normalize_wilderness_direction("cave"))
        self.assertIsNone(normalize_wilderness_direction(None))
        # Mixed-case long keys and short forms normalize too.
        self.assertEqual(normalize_wilderness_direction("North"), "n")
        self.assertEqual(normalize_wilderness_direction("SOUTHWEST"), "sw")
        self.assertEqual(normalize_wilderness_direction("N"), "n")
        self.assertEqual(
            resolve_wilderness_destination(room, "NORTH"),
            encode_wild(WILDERNESS_NAME, 60, 101),
        )

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-and-shared")
    def test_out_of_bounds_steps_resolve_to_none(self):
        self.assertIsNone(resolve_wilderness_destination(self._terrain(0, 0), "s"))
        self.assertIsNone(resolve_wilderness_destination(self._terrain(0, 0), "sw"))
        self.assertIsNone(resolve_wilderness_destination(self._terrain(0, 0), "w"))
        self.assertIsNone(
            resolve_wilderness_destination(self._terrain(WILDERNESS_MAX_X, WILDERNESS_MAX_Y), "n")
        )
        self.assertIsNone(
            resolve_wilderness_destination(self._terrain(WILDERNESS_MAX_X, WILDERNESS_MAX_Y), "ne")
        )
        self.assertIsNone(
            resolve_wilderness_destination(self._terrain(WILDERNESS_MAX_X, WILDERNESS_MAX_Y), "e")
        )

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-and-shared")
    def test_unroutable_rooms_and_directions_resolve_to_none(self):
        self.assertIsNone(resolve_wilderness_destination(types.SimpleNamespace(), "n"))
        room = self._terrain(5, 5)
        del room.ndb.active_coordinates
        self.assertIsNone(resolve_wilderness_destination(room, "n"))
        self.assertIsNone(resolve_wilderness_destination(self._terrain(5, 5), "up"))

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-and-shared")
    def test_gateway_south_resolves_to_the_grid_room(self):
        x, y = WILDERNESS_ENTRY_REGISTRY["capital_altoria"].wilderness_xy
        room = self._terrain(x, y)
        with patch(
            "typeclasses.exits._grid_room_for_anchor", return_value=self._fake_grid_room()
        ):
            self.assertEqual(
                resolve_wilderness_destination(room, "s"),
                encode_grid("capital_altoria", 2, 4),
            )
        # The injected rule is honored too.
        with patch(
            "typeclasses.exits._grid_room_for_anchor", return_value=self._fake_grid_room()
        ):
            self.assertEqual(
                resolve_wilderness_destination(
                    room, "south", WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
                ),
                encode_grid("capital_altoria", 2, 4),
            )

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-and-shared")
    def test_gateway_south_without_a_grid_room_resolves_to_none(self):
        x, y = WILDERNESS_ENTRY_REGISTRY["capital_altoria"].wilderness_xy
        room = self._terrain(x, y)
        with patch("typeclasses.exits._grid_room_for_anchor", return_value=None):
            self.assertIsNone(resolve_wilderness_destination(room, "s"))

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-and-shared")
    def test_south_away_from_the_gateway_is_an_ordinary_step(self):
        room = self._terrain(5, 5)
        with patch(
            "typeclasses.exits._grid_room_for_anchor", return_value=self._fake_grid_room()
        ):
            self.assertEqual(
                resolve_wilderness_destination(room, "s"),
                encode_wild(WILDERNESS_NAME, 5, 4),
            )

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-and-shared")
    def test_injected_gateway_rule_only_applies_at_its_coordinates(self):
        # An injected rule whose wilderness_xy does not match the room's
        # coordinates never applies, mirroring the return exit's lookup.
        room = self._terrain(5, 5)
        with patch(
            "typeclasses.exits._grid_room_for_anchor", return_value=self._fake_grid_room()
        ):
            self.assertEqual(
                resolve_wilderness_destination(
                    room, "s", WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
                ),
                encode_wild(WILDERNESS_NAME, 5, 4),
            )

    def test_wilderness_neighbor_matches_the_single_delta_table(self):
        # The exported geometry is the resolver's own: every direction steps
        # exactly one delta-table cell, and the shared helper agrees.
        from world.maps.wilderness_destination import DIRECTION_DELTAS

        for direction, (dx, dy) in DIRECTION_DELTAS.items():
            self.assertEqual(
                wilderness_neighbor(50, 50, direction), (50 + dx, 50 + dy), direction
            )
        self.assertEqual(
            set(DIRECTION_DELTAS),
            {"n", "ne", "e", "se", "s", "sw", "w", "nw"},
        )

    def test_wilderness_neighbor_returns_none_at_provider_edges(self):
        self.assertIsNone(wilderness_neighbor(0, 0, "sw"))
        self.assertIsNone(wilderness_neighbor(0, 0, "s"))
        self.assertIsNone(wilderness_neighbor(0, 0, "w"))
        self.assertIsNone(wilderness_neighbor(WILDERNESS_MAX_X, WILDERNESS_MAX_Y, "ne"))
        self.assertEqual(wilderness_neighbor(0, 0, "ne"), (1, 1))
        self.assertEqual(
            wilderness_neighbor(WILDERNESS_MAX_X, WILDERNESS_MAX_Y, "sw"),
            (WILDERNESS_MAX_X - 1, WILDERNESS_MAX_Y - 1),
        )

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-and-shared")
    def test_resolver_ordinary_steps_agree_with_wilderness_neighbor(self):
        # Every ordinary (non-gateway) resolution is exactly the shared
        # neighbor cell encoded -- no second delta table anywhere.
        room = self._terrain(50, 50)
        for direction in ("n", "ne", "e", "se", "s", "sw", "w", "nw"):
            nx, ny = wilderness_neighbor(50, 50, direction)
            self.assertEqual(
                resolve_wilderness_destination(room, direction),
                encode_wild(WILDERNESS_NAME, nx, ny),
                direction,
            )
        edge = self._terrain(0, 0)
        for direction in ("s", "sw", "w"):
            self.assertIsNone(wilderness_neighbor(0, 0, direction), direction)
            self.assertIsNone(resolve_wilderness_destination(edge, direction), direction)


class WildernessDestinationTraversalPinTests(EvenniaTest):
    """Pins the resolver against the real ``WildernessReturnExit`` routing."""

    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_all()
        sync_grid()
        sync_wilderness()
        from typeclasses.exits import WildernessGateExit
        from typeclasses.rooms import GridRoom

        self.north_gate = GridRoom.objects.filter_xyz(xyz=NORTH_GATE_XYZ).first()
        self.gate = [
            exit_obj
            for exit_obj in self.north_gate.exits
            if isinstance(exit_obj, WildernessGateExit)
        ][0]

    def _exit(self, key):
        return [exit_obj for exit_obj in self.char1.location.exits if exit_obj.key == key][0]

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-and-shared")
    def test_east_prediction_matches_the_recorded_arrival_node(self):
        self.gate.at_traverse(self.char1, self.north_gate)
        room = self.char1.location
        self.assertEqual(room.coordinates, (60, 100))

        predicted = resolve_wilderness_destination(room, "e")
        self.assertEqual(predicted, encode_wild(WILDERNESS_NAME, 61, 100))
        self._exit("east").at_traverse(self.char1, room)
        self.assertEqual(self.char1.location.coordinates, (61, 100))
        self.assertIn(
            predicted,
            {visit.node_id for visit in parse_knowledge(self.char1)},
        )

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-and-shared")
    def test_gateway_south_prediction_matches_the_recorded_arrival_node(self):
        self.gate.at_traverse(self.char1, self.north_gate)
        room = self.char1.location

        predicted = resolve_wilderness_destination(room, "s")
        self.assertEqual(predicted, encode_grid("capital_altoria", 2, 4))
        self._exit("south").at_traverse(self.char1, room)
        self.assertIs(self.char1.location, self.north_gate)
        self.assertIn(
            predicted,
            {visit.node_id for visit in parse_knowledge(self.char1)},
        )


if __name__ == "__main__":
    unittest.main()
