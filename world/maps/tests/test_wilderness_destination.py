from tools.spec_traceability import covers_requirement

"""Tests for the canonical wilderness destination resolver (wilderness-anchor-footprint).

Covers the resolver's mirror of ``WildernessReturnExit.at_traverse`` routing:
a registered (approach-cell, return-direction) pair resolves to its gate's
grid room, a point-shape anchor answers every direction with its single gate,
ordinary provider-valid directions resolve to the adjacent wild cell, and
every refused edge -- provider bounds, anchor footprint cells, missing gate
rooms -- resolves to ``None``. The traversal pin tests move a real character
through the real exits in every direction around both approach cells and
compare the recorded arrival node with the resolver's prediction, so
presentation cannot drift from traversal.
"""

import types
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase, EvenniaTest

from typeclasses.rooms import Room, TerrainRoom
from world.lore.wilderness_entry import (
    WILDERNESS_ENTRY_REGISTRY,
    WildernessEntryPoint,
    WildernessGate,
)
from world.lore.sync import sync_all
from world.maps.bootstrap import NORTH_GATE_XYZ, SOUTH_GATE_XYZ, sync_grid, sync_wilderness
from world.maps.wilderness_destination import (
    find_gateway,
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

CAPITAL = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
SOUTH_APPROACH = CAPITAL.approach_cell(CAPITAL.gate_for("n"))  # (60, 97)
NORTH_APPROACH = CAPITAL.approach_cell(CAPITAL.gate_for("s"))  # (60, 103)


class WildernessDestinationResolverTests(EvenniaTestCase):
    """Resolver semantics against real TerrainRoom instances (gate rooms mocked)."""

    def _terrain(self, x: int, y: int) -> TerrainRoom:
        # nohome=True keeps db_home NULL: DEFAULT_HOME (#2) resolution is
        # unreliable inside EvenniaTestCase transactions (idmapper can serve a
        # stale rolled-back object for #2), which would fail the teardown
        # foreign-key check.
        room = create_object(TerrainRoom, key="霧野", nohome=True)
        room.ndb.active_coordinates = (x, y)
        return room

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
    def test_ordinary_directions_resolve_to_adjacent_wild_cells(self):
        # (50, 50) is away from every gateway and footprint, so every
        # direction is an ordinary wild step.
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

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
    def test_contrib_exit_keys_resolve_through_the_normalizer(self):
        room = self._terrain(60, 96)
        self.assertEqual(
            resolve_wilderness_destination(room, "north"),
            encode_wild(WILDERNESS_NAME, 60, 97),
        )
        self.assertEqual(
            resolve_wilderness_destination(room, "southwest"),
            encode_wild(WILDERNESS_NAME, 59, 95),
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
            encode_wild(WILDERNESS_NAME, 60, 97),
        )

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
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

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
    def test_unroutable_rooms_and_directions_resolve_to_none(self):
        self.assertIsNone(resolve_wilderness_destination(types.SimpleNamespace(), "n"))
        room = self._terrain(5, 5)
        del room.ndb.active_coordinates
        self.assertIsNone(resolve_wilderness_destination(room, "n"))
        self.assertIsNone(resolve_wilderness_destination(self._terrain(5, 5), "up"))

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
    def test_a_gate_step_resolves_to_its_grid_room(self):
        # Delta scenario: north from (60, 97) -> 南門 (2, 0); south from
        # (60, 103) -> North Gate (2, 4).
        with patch("world.maps.wilderness_destination.grid_room_for_gate", return_value=object()):
            self.assertEqual(
                resolve_wilderness_destination(self._terrain(*SOUTH_APPROACH), "n"),
                encode_grid("capital_altoria", 2, 0),
            )
            self.assertEqual(
                resolve_wilderness_destination(self._terrain(*NORTH_APPROACH), "s"),
                encode_grid("capital_altoria", 2, 4),
            )
            # The injected rule is honored at its own gate's approach cell too.
            self.assertEqual(
                resolve_wilderness_destination(
                    self._terrain(*NORTH_APPROACH), "south", CAPITAL
                ),
                encode_grid("capital_altoria", 2, 4),
            )

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
    def test_a_gateway_whose_grid_room_is_missing_resolves_to_none(self):
        with patch("world.maps.wilderness_destination.grid_room_for_gate", return_value=None):
            self.assertIsNone(resolve_wilderness_destination(self._terrain(*NORTH_APPROACH), "s"))
            self.assertIsNone(resolve_wilderness_destination(self._terrain(*SOUTH_APPROACH), "n"))

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
    def test_the_non_gate_direction_at_an_approach_cell_is_an_ordinary_step(self):
        # Delta scenario: south from (60, 97) and north from (60, 103) are
        # ordinary steps away from the footprint.
        self.assertEqual(
            resolve_wilderness_destination(self._terrain(*SOUTH_APPROACH), "s"),
            encode_wild(WILDERNESS_NAME, 60, 96),
        )
        self.assertEqual(
            resolve_wilderness_destination(self._terrain(*NORTH_APPROACH), "n"),
            encode_wild(WILDERNESS_NAME, 60, 104),
        )

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
    def test_a_step_into_an_anchor_footprint_resolves_to_none(self):
        # Delta scenario: east from (57, 100) and west from (63, 100) both
        # face footprint cells that are no gate's approach.
        self.assertIsNone(resolve_wilderness_destination(self._terrain(57, 100), "e"))
        self.assertIsNone(resolve_wilderness_destination(self._terrain(63, 100), "w"))
        # The wrong-gate direction into the city side is likewise refused:
        # north from (60, 103) steps onto footprint (60, 104->? no) -- (60,102)
        # sits behind the south exit; north from the north approach is a valid
        # step (60, 104). The refusal is the diagonal toward mask corners:
        self.assertIsNone(resolve_wilderness_destination(self._terrain(57, 97), "ne"))

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
    def test_south_away_from_any_gateway_is_an_ordinary_step(self):
        room = self._terrain(5, 5)
        self.assertEqual(
            resolve_wilderness_destination(room, "s"),
            encode_wild(WILDERNESS_NAME, 5, 4),
        )

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
    def test_injected_gateway_rule_only_applies_where_it_advertises(self):
        # An injected rule whose gates do not cover the room's coordinates
        # never applies, mirroring the return exit's lookup.
        room = self._terrain(5, 5)
        self.assertEqual(
            resolve_wilderness_destination(room, "s", CAPITAL),
            encode_wild(WILDERNESS_NAME, 5, 4),
        )
        # And at an approach cell of ANOTHER gate of the same injected entry,
        # the injected rule still cannot hijack: (60, 97) "n" belongs to the
        # capital's "n" gate -- correct behavior is the gate, but an injected
        # rule for a different entry stays ordinary.
        other = WildernessEntryPoint(
            "capital_altoria", ("#",), (200, 200), (WildernessGate("n", (2, 0), "capital_altoria"),)
        )
        # The foreign rule does not apply, the step falls through to the
        # neighbor rule -- and (60, 98) is a footprint cell, so the resolver
        # refuses exactly like the provider does.
        self.assertIsNone(
            resolve_wilderness_destination(self._terrain(*SOUTH_APPROACH), "n", other)
        )

    def test_find_gateway_matches_the_registry_rules(self):
        hit = find_gateway(SOUTH_APPROACH, "n")
        self.assertIsNotNone(hit)
        self.assertIs(hit[0], CAPITAL)
        self.assertEqual(hit[1].grid_xy, (2, 0))
        hit = find_gateway(NORTH_APPROACH, "s")
        self.assertIsNotNone(hit)
        self.assertEqual(hit[1].grid_xy, (2, 4))
        # Wrong direction at an approach cell is no gateway.
        self.assertIsNone(find_gateway(SOUTH_APPROACH, "s"))
        self.assertIsNone(find_gateway(NORTH_APPROACH, "n"))
        # Other cells are no gateway in any direction.
        for direction in ("n", "ne", "e", "se", "s", "sw", "w", "nw"):
            self.assertIsNone(find_gateway((50, 50), direction), direction)
            self.assertIsNone(find_gateway((60, 100), direction), direction)

    def test_find_gateway_answers_every_direction_at_a_point_anchor(self):
        point = WildernessEntryPoint(
            "capital_altoria", ("#",), (120, 120), (WildernessGate("n", (2, 0), "capital_altoria"),)
        )
        with patch.dict(WILDERNESS_ENTRY_REGISTRY, {"capital_altoria": point}):
            for direction in ("n", "ne", "e", "se", "s", "sw", "w", "nw"):
                hit = find_gateway((120, 120), direction)
                self.assertIsNotNone(hit, direction)
                self.assertEqual(hit[1].grid_xy, (2, 0), direction)
            self.assertIsNone(find_gateway((121, 120), "n"))

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

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
    def test_wilderness_neighbor_returns_none_at_edges_and_footprints(self):
        self.assertIsNone(wilderness_neighbor(0, 0, "sw"))
        self.assertIsNone(wilderness_neighbor(0, 0, "s"))
        self.assertIsNone(wilderness_neighbor(0, 0, "w"))
        self.assertIsNone(wilderness_neighbor(WILDERNESS_MAX_X, WILDERNESS_MAX_Y, "ne"))
        self.assertEqual(wilderness_neighbor(0, 0, "ne"), (1, 1))
        self.assertEqual(
            wilderness_neighbor(WILDERNESS_MAX_X, WILDERNESS_MAX_Y, "sw"),
            (WILDERNESS_MAX_X - 1, WILDERNESS_MAX_Y - 1),
        )
        # Footprint exclusion: (57, 100) east -> (58, 100) is a mask cell.
        self.assertIsNone(wilderness_neighbor(57, 100, "e"))
        self.assertEqual(wilderness_neighbor(SOUTH_APPROACH[0], SOUTH_APPROACH[1] - 1, "n"), SOUTH_APPROACH)

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
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
        self.south_gate = GridRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.north_gate_exit = next(
            exit_obj
            for exit_obj in self.north_gate.exits
            if isinstance(exit_obj, WildernessGateExit)
        )
        self.south_gate_exit = next(
            exit_obj
            for exit_obj in self.south_gate.exits
            if isinstance(exit_obj, WildernessGateExit)
        )

    def _exit(self, key):
        return [exit_obj for exit_obj in self.char1.location.exits if exit_obj.key == key][0]

    def _visit_ids(self):
        return {visit.node_id for visit in parse_knowledge(self.char1)}

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
    def test_east_prediction_matches_the_recorded_arrival_node(self):
        self.north_gate_exit.at_traverse(self.char1, self.north_gate)
        room = self.char1.location
        self.assertEqual(room.coordinates, NORTH_APPROACH)

        predicted = resolve_wilderness_destination(room, "e")
        self.assertEqual(predicted, encode_wild(WILDERNESS_NAME, 61, 103))
        self._exit("east").at_traverse(self.char1, room)
        self.assertEqual(self.char1.location.coordinates, (61, 103))
        self.assertIn(predicted, self._visit_ids())

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
    def test_gateway_south_prediction_matches_the_recorded_arrival_node(self):
        self.north_gate_exit.at_traverse(self.char1, self.north_gate)
        room = self.char1.location

        predicted = resolve_wilderness_destination(room, "s")
        self.assertEqual(predicted, encode_grid("capital_altoria", 2, 4))
        self._exit("south").at_traverse(self.char1, room)
        self.assertIs(self.char1.location, self.north_gate)
        self.assertIn(predicted, self._visit_ids())

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
    def test_gateway_north_prediction_matches_the_recorded_arrival_node(self):
        self.south_gate_exit.at_traverse(self.char1, self.south_gate)
        room = self.char1.location
        self.assertEqual(room.coordinates, SOUTH_APPROACH)

        predicted = resolve_wilderness_destination(room, "n")
        self.assertEqual(predicted, encode_grid("capital_altoria", 2, 0))
        self._exit("north").at_traverse(self.char1, room)
        self.assertIs(self.char1.location, self.south_gate)
        self.assertIn(predicted, self._visit_ids())

    @covers_requirement("canonical-wilderness-destination::wilderness-destination-resolution-is-canonical-shared-and-registry-driven")
    def test_resolver_and_traversal_agree_in_every_direction_around_both_approach_cells(self):
        # Delta scenario: for each of the eight directions at each approach
        # cell, the resolver's prediction equals the room a real traversal
        # reaches (grid room at the gate direction, wild cell at valid
        # ordinary directions, refusal where the resolver returned None).
        for gate_exit, gate_room, approach, gate_direction, grid_node in (
            (
                self.north_gate_exit,
                self.north_gate,
                NORTH_APPROACH,
                "s",
                encode_grid("capital_altoria", 2, 4),
            ),
            (
                self.south_gate_exit,
                self.south_gate,
                SOUTH_APPROACH,
                "n",
                encode_grid("capital_altoria", 2, 0),
            ),
        ):
            gate_exit.at_traverse(self.char1, gate_room)
            room = self.char1.location
            self.assertEqual(room.coordinates, approach)
            for direction in ("n", "ne", "e", "se", "s", "sw", "w", "nw"):
                with self.subTest(approach=approach, direction=direction):
                    predicted = resolve_wilderness_destination(room, direction)
                    if predicted is None:
                        # Provider-invalid neighbor: the step must be refused
                        # in place.
                        self.assertFalse(
                            self._exit(_LONG[direction]).at_traverse(self.char1, room),
                            direction,
                        )
                        self.assertEqual(self.char1.location, room)
                        continue
                    if predicted == grid_node and direction == gate_direction:
                        self.assertTrue(
                            self._exit(_LONG[direction]).at_traverse(self.char1, room)
                        )
                        self.assertIs(self.char1.location, gate_room)
                        self.assertIn(predicted, self._visit_ids())
                        # Return to the approach cell for the next direction.
                        gate_exit.at_traverse(self.char1, gate_room)
                        room = self.char1.location
                        self.assertEqual(room.coordinates, approach)
                        continue
                    # Ordinary wild step: arrival equals the predicted cell.
                    self.assertTrue(
                        self._exit(_LONG[direction]).at_traverse(self.char1, room)
                    )
                    nx, ny = _decode_wild(predicted)
                    self.assertEqual(self.char1.location.coordinates, (nx, ny))
                    # Walk back to the approach cell for the next direction.
                    back = _OPPOSITE[direction]
                    self._exit(_LONG[back]).at_traverse(self.char1, self.char1.location)
                    self.assertEqual(self.char1.location.coordinates, approach)
                    room = self.char1.location


_LONG = {
    "n": "north",
    "ne": "northeast",
    "e": "east",
    "se": "southeast",
    "s": "south",
    "sw": "southwest",
    "w": "west",
    "nw": "northwest",
}
_OPPOSITE = {
    "n": "s",
    "s": "n",
    "e": "w",
    "w": "e",
    "ne": "sw",
    "sw": "ne",
    "nw": "se",
    "se": "nw",
}


def _decode_wild(node_id: str) -> tuple[int, int]:
    # Node ids are "wild:<name>:<x>:<y>".
    _, _name, x, y = node_id.split(":")
    return int(x), int(y)


if __name__ == "__main__":
    unittest.main()
