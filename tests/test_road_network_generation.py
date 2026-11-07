"""Mechanism tests for the offline road network generator.

Every raster here is a small synthetic map built in this file, and every
expectation follows from its geometry: no shipped region, location or count is
read or pinned, and the generator's tuning values are chosen per test rather
than taken from the authored parameter document. Ground is uniform unless a
test says otherwise, and tests that compare costs disable the noise. On uniform
ground many cheapest paths tie, so assertions check legality, ends and costs,
never an exact cell sequence, unless the geometry makes the cheapest path
unique (a pure straight line).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

from elosern_map_core.authoring import load_authoring_world
from elosern_map_core.roads import (
    Road,
    RoadGenerationError,
    RoadInput,
    RoadNode,
    compute_roads,
    generate_road_network,
    road_input,
    verify_roads,
)
from elosern_map_core.roads_codec import decode_road_network, read_road_metadata
from elosern_map_core.schema import LOCATION_KINDS
from elosern_map_core.sources import make_source_document
from elosern_map_core.terrain import REGION_KEYS
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_TESTS = REPO_ROOT / "packages" / "map-core" / "tests"
if str(PACKAGE_TESTS) not in sys.path:
    sys.path.insert(0, str(PACKAGE_TESTS))

import authoring_fixtures as fixtures  # noqa: E402

ROAD_PATH = "content/maps/road_network.yaml"
#: A configured node kind and an unconfigured one, never named literally.
NODE_KIND = LOCATION_KINDS[1]
OTHER_KIND = LOCATION_KINDS[4]
#: Synthetic region names for raster-level inputs.
PLAIN = "region_plain"
BARRIER = "region_barrier"


# --------------------------------------------------------------------------
# Raster-level inputs


def _input(
    walkable: np.ndarray,
    nodes: dict[str, list[tuple[int, int]]],
    *,
    region: np.ndarray | None = None,
    bands: np.ndarray | None = None,
    **overrides,
) -> RoadInput:
    size = walkable.shape[0]
    values = dict(
        size=size,
        walkable=walkable,
        region=region if region is not None else np.ones((size, size), dtype=np.uint8),
        region_names=(BARRIER, PLAIN),
        bands=bands if bands is not None else np.zeros((size, size), dtype=np.int16),
        region_speeds={PLAIN: 4000, BARRIER: 4000},
        nodes=tuple(RoadNode(key, tuple(sorted(cells))) for key, cells in sorted(nodes.items())),
        blocked=frozenset(),
        point_gateways={},
        forbidden_regions=(),
        slope_factor_per_band=0.0,
        noise_amplitude=0.0,
        noise_wavelength_cells=8.0,
        noise_seed=3,
        detour_limit=100.0,
        reuse_factor=1.0,
        source_signature="synthetic-signature",
    )
    values.update(overrides)
    return RoadInput(**values)


def _open(size: int) -> np.ndarray:
    return np.ones((size, size), dtype=bool)


def _pairs(roads) -> set[tuple[str, str]]:
    return {(road.first, road.second) for road in roads}


def _octile(dx: int, dy: int) -> float:
    dx, dy = abs(dx), abs(dy)
    return min(dx, dy) * 2**0.5 + abs(dx - dy)


class _Legality:
    def assertLegalRoad(self, inp: RoadInput, road: Road, open_cells: np.ndarray) -> None:
        for x, y in road.cells:
            self.assertTrue(open_cells[y, x], f"{road}: {(x, y)} is not open")
        for (ax, ay), (bx, by) in zip(road.cells, road.cells[1:]):
            dx, dy = bx - ax, by - ay
            self.assertEqual(max(abs(dx), abs(dy)), 1, f"{road}: jump {(ax, ay)}->{(bx, by)}")
            if dx and dy:
                self.assertTrue(open_cells[ay, ax + dx] and open_cells[ay + dy, ax])


# --------------------------------------------------------------------------
# Authoring-level inputs


def _road_document(**overrides) -> dict:
    data = {
        "version": 1,
        "kind": "road_network",
        "id": "road_network",
        "node_kinds": [NODE_KIND],
        "forbidden_regions": [],
        "slope_factor_per_band": 0.0,
        "noise_amplitude": 0.0,
        "noise_wavelength_cells": 8,
        "noise_seed": 5,
        "detour_limit": 100,
        "reuse_factor": 1,
    }
    data.update(overrides)
    return data


def _location(kind: str, cell: tuple[int, int]) -> dict:
    return {
        "kind": kind,
        "display_name_zh": "合成地點",
        "description": "A synthetic place.",
        "cell": {"cell_x": cell[0], "cell_y": cell[1]},
        "geographic_constraint": "synthetic",
        "scene_archetype": None,
    }


def _settlement(settlement_id: str, location: str, entry) -> dict:
    data = fixtures.settlement_data(entry=entry)
    data["id"] = settlement_id
    data["location_ref"] = location
    data["nodes"]["gate"]["anchor_key"] = location
    return data


def _point(direction: str) -> dict:
    return {
        "shape": ["#"],
        "offset": {"dx": 0, "dy": 0},
        "gates": [{"return_direction": direction, "destination_node": "gate"}],
    }


def _world(locations: dict, settlements: dict, *, road: dict | None = None):
    """A synthetic world; the fixture's demo settlement stays off every node kind."""
    rows = {"demo_location": _location(OTHER_KIND, (5, 12))}
    rows.update(locations)
    location_document = {"version": 1, "kind": "locations", "id": "locations", "locations": rows}
    documents = list(
        fixtures.custom_sources(locations=location_document, settlement=fixtures.settlement_data())
    )
    for settlement_id, data in sorted(settlements.items()):
        documents.append(
            make_source_document(
                f"content/maps/settlements/{settlement_id}.yaml", fixtures.yaml_text(data)
            )
        )
    if road is not False:
        documents.append(
            make_source_document(ROAD_PATH, fixtures.yaml_text(road or _road_document()))
        )
    return load_authoring_world(tuple(documents))


def _authored_input(world) -> RoadInput:
    size = world.continent.terrain.frame_cells
    return road_input(
        world,
        np.zeros((size, size), dtype=np.int16),
        {region: 4000 for region in REGION_KEYS},
        "synthetic-elevation",
    )


class RoadNodeTests(unittest.TestCase):
    """Road nodes are the gated settlements of the configured kinds."""

    @covers_requirement(
        "road-network-generation::road-nodes-are-the-gated-settlements-of-the-configured-kinds"
    )
    def test_only_gated_settlements_of_configured_kinds_are_nodes(self):
        world = _world(
            {
                "gated": _location(NODE_KIND, (3, 5)),
                "undocumented": _location(NODE_KIND, (8, 5)),
                "gateless": _location(NODE_KIND, (13, 5)),
                "other_kind": _location(OTHER_KIND, (17, 5)),
            },
            {
                "gated_map": _settlement("gated_map", "gated", _point("w")),
                "gateless_map": _settlement("gateless_map", "gateless", None),
                "other_map": _settlement("other_map", "other_kind", _point("e")),
            },
        )
        inp = _authored_input(world)
        self.assertEqual([node.key for node in inp.nodes], ["gated"])
        self.assertEqual(inp.nodes[0].approaches, ((3, 5),))
        # The unconfigured kind's point anchor is closed to roads; a node's is not.
        self.assertIn((17, 5), inp.blocked)
        self.assertNotIn((3, 5), inp.blocked)
        self.assertEqual(inp.point_gateways[(3, 5)], frozenset({(2, 5)}))

    @covers_requirement(
        "road-network-generation::road-nodes-are-the-gated-settlements-of-the-configured-kinds"
    )
    def test_absent_parameter_document_names_it(self):
        world = _world({}, {}, road=False)
        with self.assertRaises(RoadGenerationError) as caught:
            _authored_input(world)
        self.assertIn(ROAD_PATH, str(caught.exception))

    @covers_requirement(
        "road-network-generation::road-nodes-are-the-gated-settlements-of-the-configured-kinds"
    )
    def test_new_settlement_document_joins_with_no_other_change(self):
        locations = {
            "first": _location(NODE_KIND, (3, 5)),
            "late": _location(NODE_KIND, (15, 5)),
        }
        settlements = {"first_map": _settlement("first_map", "first", _point("w"))}
        before = _authored_input(_world(locations, settlements))
        settlements["late_map"] = _settlement("late_map", "late", _point("e"))
        after = _authored_input(_world(locations, settlements))
        self.assertEqual([node.key for node in before.nodes], ["first"])
        self.assertEqual([node.key for node in after.nodes], ["first", "late"])
        self.assertNotEqual(before.source_signature, after.source_signature)


class RoadCostFieldTests(_Legality, unittest.TestCase):
    """The road cost field admits only legal walkable steps."""

    @covers_requirement(
        "road-network-generation::the-road-cost-field-admits-only-legal-walkable-steps"
    )
    def test_river_is_crossed_only_at_its_ford(self):
        walkable = _open(21)
        walkable[:, 10] = False
        walkable[2, 10] = True  # the ford, far from the straight line y = 15
        inp = _input(walkable, {"node_a": [(3, 15)], "node_b": [(17, 15)]})
        (road,) = compute_roads(inp)
        self.assertLegalRoad(inp, road, walkable)
        self.assertEqual([cell for cell in road.cells if cell[0] == 10], [(10, 2)])

    @covers_requirement(
        "road-network-generation::the-road-cost-field-admits-only-legal-walkable-steps"
    )
    def test_corners_are_not_cut(self):
        walkable = _open(12)
        for k in range(2, 9):
            walkable[k, k + 1] = False  # beside every step of the diagonal
        inp = _input(walkable, {"node_a": [(2, 2)], "node_b": [(8, 8)]})
        (road,) = compute_roads(inp)
        self.assertLegalRoad(inp, road, walkable)
        steps = set(zip(road.cells, road.cells[1:]))
        self.assertNotIn(((2, 2), (3, 3)), steps)

    def _hill_road(self, low: int, high: int) -> tuple[Road, np.ndarray]:
        size = 15
        hill = np.zeros((size, size), dtype=bool)
        hill[0:11, 6:9] = True
        bands = np.where(hill, high, low).astype(np.int16)
        inp = _input(
            _open(size),
            {"node_a": [(1, 5)], "node_b": [(13, 5)]},
            bands=bands,
            slope_factor_per_band=1.0,
        )
        (road,) = compute_roads(inp)
        return road, hill

    @covers_requirement(
        "road-network-generation::the-road-cost-field-admits-only-legal-walkable-steps"
    )
    def test_steep_steps_cost_more_in_both_directions(self):
        # Climbing the hill costs eleven flat steps each way; the detour round
        # its north end costs only a few extra diagonals.
        for low, high in ((0, 10), (10, 0)):
            with self.subTest(low=low, high=high):
                road, hill = self._hill_road(low, high)
                self.assertFalse(any(hill[y, x] for x, y in road.cells))

    @covers_requirement(
        "road-network-generation::the-road-cost-field-admits-only-legal-walkable-steps"
    )
    def test_forbidden_region_separates_networks(self):
        walkable = _open(21)
        region = np.full((21, 21), 2, dtype=np.uint8)
        region[:, 9:12] = 1  # the barrier band is the only link between sides
        inp = _input(
            walkable,
            {
                "west_a": [(2, 4)],
                "west_b": [(2, 16)],
                "east_a": [(18, 4)],
                "east_b": [(18, 16)],
            },
            region=region,
            forbidden_regions=(BARRIER,),
        )
        network = decode_road_network(generate_road_network(inp))
        pairs = {(first, second) for first, second, _ in network.roads}
        self.assertEqual(pairs, {("west_a", "west_b"), ("east_a", "east_b")})
        self.assertFalse(any(9 <= x <= 11 for x, _ in network.cells))

    @covers_requirement(
        "road-network-generation::the-road-cost-field-admits-only-legal-walkable-steps"
    )
    def test_roads_stay_off_footprints_and_hidden_gateways(self):
        footprint = {
            "shape": ["###", "###", "###"],
            "offset": {"dx": -1, "dy": -1},
            "gates": [{"return_direction": "s", "destination_node": "gate"}],
        }
        world = _world(
            {
                "west": _location(NODE_KIND, (3, 5)),
                "east": _location(NODE_KIND, (19, 5)),
                "walled": _location(OTHER_KIND, (8, 5)),
                "hidden": _location(OTHER_KIND, (14, 5)),
            },
            {
                "west_map": _settlement("west_map", "west", _point("w")),
                "east_map": _settlement("east_map", "east", _point("e")),
                "walled_map": _settlement("walled_map", "walled", footprint),
                "hidden_map": _settlement("hidden_map", "hidden", _point("n")),
            },
        )
        inp = _authored_input(world)
        footprint_cells = {(x, y) for x in range(7, 10) for y in range(4, 7)}
        hidden_anchor = (14, 5)  # the hidden gateway cell, on the line y = 5
        self.assertEqual([node.key for node in inp.nodes], ["east", "west"])
        (road,) = compute_roads(inp)
        self.assertEqual((road.cells[0], road.cells[-1]), ((19, 5), (3, 5)))
        self.assertFalse(footprint_cells & set(road.cells))
        self.assertNotIn(hidden_anchor, road.cells)
        self.assertEqual(verify_roads(inp, (road,)), [])


class RoadTopologyTests(unittest.TestCase):
    """Road topology is a relative neighbourhood graph with detour repair."""

    @covers_requirement(
        "road-network-generation::road-topology-is-a-relative-neighbourhood-graph-with-detour-repair"
    )
    def test_middle_settlement_removes_the_long_pair(self):
        inp = _input(
            np.ones((21, 21), dtype=bool),
            {"node_a": [(2, 10)], "node_b": [(10, 10)], "node_c": [(18, 10)]},
        )
        self.assertEqual(
            _pairs(compute_roads(inp)), {("node_a", "node_b"), ("node_b", "node_c")}
        )

    TRIANGLE = {"node_a": [(2, 2)], "node_b": [(20, 2)], "node_c": [(11, 13)]}

    @covers_requirement(
        "road-network-generation::road-topology-is-a-relative-neighbourhood-graph-with-detour-repair"
    )
    def test_large_detour_adds_a_road(self):
        direct = _octile(18, 0)
        through = _octile(9, 11) * 2
        detour = through / direct  # about 1.64: c is closer to both ends
        self.assertTrue(1.5 < detour < 1.9)
        for limit, expected in (
            (1.3, {("node_a", "node_b"), ("node_a", "node_c"), ("node_b", "node_c")}),
            (1.95, {("node_a", "node_c"), ("node_b", "node_c")}),
        ):
            with self.subTest(limit=limit):
                inp = _input(_open(23), self.TRIANGLE, detour_limit=limit)
                self.assertEqual(_pairs(compute_roads(inp)), expected)

    @covers_requirement(
        "road-network-generation::road-topology-is-a-relative-neighbourhood-graph-with-detour-repair"
    )
    def test_terrain_changes_the_neighbourhood(self):
        open_ground = _open(23)
        walled = _open(23)
        walled[6, 0:15] = False  # a wall that sends a's walk to c round its end
        plain = _pairs(compute_roads(_input(open_ground, self.TRIANGLE)))
        wall = _pairs(compute_roads(_input(walled, self.TRIANGLE)))
        self.assertEqual(plain, {("node_a", "node_c"), ("node_b", "node_c")})
        self.assertEqual(wall, {("node_a", "node_b"), ("node_b", "node_c")})


class RoadRoutingTests(_Legality, unittest.TestCase):
    """Roads are routed cheapest first and reuse earlier cells."""

    # c's two gates sit level with a and b, so each pure straight line is the
    # unique cheapest path at full price: a and b are exactly 40 from c.
    TRUNK = {"node_a": [(1, 4)], "node_b": [(1, 18)], "node_c": [(41, 4), (41, 18)]}

    def _trunk(self, reuse: float) -> dict[tuple[str, str], Road]:
        roads = compute_roads(_input(_open(44), self.TRUNK, reuse_factor=reuse))
        return {(road.first, road.second): road for road in roads}

    @covers_requirement(
        "road-network-generation::roads-are-routed-cheapest-first-and-reuse-earlier-cells"
    )
    def test_later_roads_merge_into_a_trunk(self):
        shared = {}
        for reuse in (1.0, 0.4):
            roads = self._trunk(reuse)
            self.assertIn(("node_a", "node_c"), roads)
            self.assertIn(("node_b", "node_c"), roads)
            shared[reuse] = len(
                set(roads["node_a", "node_c"].cells) & set(roads["node_b", "node_c"].cells)
            )
        self.assertEqual(shared[1.0], 0)
        self.assertGreater(shared[0.4], shared[1.0])

    @covers_requirement(
        "road-network-generation::roads-are-routed-cheapest-first-and-reuse-earlier-cells"
    )
    def test_roads_end_at_gates_and_a_gate_serves_several_roads(self):
        inp = _input(_open(44), self.TRUNK, reuse_factor=0.4)
        roads = compute_roads(inp)
        gates = {node.key: set(node.approaches) for node in inp.nodes}
        for road in roads:
            self.assertLegalRoad(inp, road, inp.walkable)
            self.assertIn(road.cells[0], gates[road.first])
            self.assertIn(road.cells[-1], gates[road.second])
        # The b-c road takes the gate that is cheapest along the earlier road,
        # not the nearest one by position.
        ends = [road.cells[-1] for road in roads if road.second == "node_c"]
        self.assertEqual(ends, [(41, 4), (41, 4)])


class RoadRefusalTests(unittest.TestCase):
    """Generation refuses an invalid network."""

    @covers_requirement(
        "road-network-generation::generation-refuses-an-invalid-network"
    )
    def test_isolated_node_is_named(self):
        walkable = _open(20)
        walkable[:, 14] = False
        inp = _input(walkable, {"node_a": [(2, 2)], "node_b": [(10, 10)], "node_c": [(17, 5)]})
        with self.assertRaises(RoadGenerationError) as caught:
            generate_road_network(inp)
        self.assertIn("node node_c: has no road", caught.exception.problems)

    @covers_requirement(
        "road-network-generation::generation-refuses-an-invalid-network"
    )
    def test_unusable_gate_approach_is_named(self):
        walkable = _open(12)
        walkable[3, 3] = False
        region = np.full((12, 12), 2, dtype=np.uint8)
        region[9, 9] = 1
        inp = _input(
            walkable,
            {"node_a": [(3, 3)], "node_b": [(9, 9)], "node_c": [(5, 6)]},
            region=region,
            forbidden_regions=(BARRIER,),
        )
        with self.assertRaises(RoadGenerationError) as caught:
            generate_road_network(inp)
        self.assertIn(
            "node node_a: gate approach (3, 3) is off the cost field", caught.exception.problems
        )
        self.assertIn(
            "node node_b: gate approach (9, 9) is off the cost field", caught.exception.problems
        )

    @covers_requirement(
        "road-network-generation::generation-refuses-an-invalid-network"
    )
    def test_undeclared_region_code_is_refused(self):
        region = np.full((8, 8), 2, dtype=np.uint8)
        region[0, 0] = 3  # only two region names are declared
        inp = _input(_open(8), {"node_a": [(2, 2)], "node_b": [(5, 5)]}, region=region)
        with self.assertRaises(RoadGenerationError) as caught:
            generate_road_network(inp)
        self.assertIn(
            "a region code lies outside the declared region names", caught.exception.problems
        )

    @covers_requirement(
        "road-network-generation::generation-refuses-an-invalid-network"
    )
    def test_shared_gate_approach_is_named(self):
        inp = _input(_open(8), {"node_a": [(2, 2)], "node_b": [(2, 2), (5, 5)]})
        with self.assertRaises(RoadGenerationError) as caught:
            generate_road_network(inp)
        self.assertIn(
            "node node_b: gate approach (2, 2) is shared with node_a", caught.exception.problems
        )

    @covers_requirement(
        "road-network-generation::generation-refuses-an-invalid-network"
    )
    def test_self_check_names_every_hand_built_fault(self):
        walkable = _open(12)
        walkable[:, 6] = False  # two networks: x < 6 and x > 6
        walkable[3, 3] = False
        walkable[1, 2] = False
        inp = _input(
            walkable,
            {
                "node_a": [(1, 1)],
                "node_b": [(4, 1)],
                "node_c": [(1, 9)],
                "node_d": [(4, 9)],
                "node_e": [(9, 1)],
                "node_f": [(9, 9)],
            },
            point_gateways={(9, 9): frozenset({(9, 8)})},
        )
        roads = [
            # An unwalkable cell.
            Road("node_a", "node_b", ((1, 1), (2, 1), (3, 1), (4, 1))),
            # A corner cut past (3, 3) and a jump.
            Road("node_a", "node_c", ((1, 1), (1, 2), (2, 3), (3, 4), (2, 5), (1, 9))),
            # Wrong end cell.
            Road("node_c", "node_d", ((1, 9), (2, 9), (3, 9))),
            # Joins the west and east networks.
            Road("node_d", "node_e", ((4, 9), (5, 9), (6, 9), (7, 9), (9, 1))),
            # Leaves the point gateway (9, 9) in its gate direction.
            Road("node_e", "node_f", ((9, 1),) + tuple((9, y) for y in range(2, 10))),
        ]
        problems = verify_roads(inp, roads)
        expected = [
            "road node_a--node_b: cell (2, 1) is off the cost field",
            "road node_a--node_c: illegal step (2, 3) -> (3, 4)",
            "road node_a--node_c: illegal step (2, 5) -> (1, 9)",
            "road node_c--node_d: does not end at gates of its settlements",
            "road node_d--node_e: cell (6, 9) is off the cost field",
            "road node_d--node_e: joins separate networks",
            "road node_e--node_f: leaves point gateway (9, 9) in its gate direction",
        ]
        for problem in expected:
            self.assertIn(problem, problems)

    @covers_requirement(
        "road-network-generation::generation-refuses-an-invalid-network"
    )
    def test_self_check_names_a_split_network(self):
        inp = _input(
            _open(12),
            {"node_a": [(1, 1)], "node_b": [(3, 1)], "node_c": [(8, 8)], "node_d": [(10, 8)]},
        )
        roads = [
            Road("node_a", "node_b", ((1, 1), (2, 1), (3, 1))),
            Road("node_c", "node_d", ((8, 8), (9, 8), (10, 8))),
        ]
        problems = verify_roads(inp, roads)
        self.assertEqual(problems, ["network 1: nodes node_c, node_d are not connected"])

    def test_a_valid_hand_built_network_passes(self):
        inp = _input(_open(8), {"node_a": [(1, 1)], "node_b": [(3, 3)]})
        self.assertEqual(verify_roads(inp, [Road("node_a", "node_b", ((1, 1), (2, 2), (3, 3)))]), [])


class RoadDeterminismTests(unittest.TestCase):
    """Generation is deterministic."""

    def _noisy(self) -> RoadInput:
        walkable = _open(40)
        walkable[20, 5:35] = False
        bands = np.zeros((40, 40), dtype=np.int16)
        bands[25:, :] = 3
        return _input(
            walkable,
            {
                "node_a": [(3, 3)],
                "node_b": [(36, 4)],
                "node_c": [(20, 36)],
                "node_d": [(4, 30)],
            },
            bands=bands,
            slope_factor_per_band=0.2,
            noise_amplitude=0.3,
            noise_wavelength_cells=6.0,
            detour_limit=1.5,
            reuse_factor=0.5,
        )

    @covers_requirement(
        "road-network-generation::generation-is-deterministic"
    )
    def test_repeat_runs_match_byte_for_byte(self):
        self.assertEqual(generate_road_network(self._noisy()), generate_road_network(self._noisy()))

    @covers_requirement(
        "road-network-generation::generation-is-deterministic"
    )
    def test_artifact_decodes_to_the_result(self):
        inp = self._noisy()
        text = generate_road_network(inp)
        network = decode_road_network(text)
        self.assertEqual(
            network.roads,
            tuple((road.first, road.second, road.cells) for road in compute_roads(inp)),
        )
        self.assertEqual(network.nodes, tuple(node.key for node in inp.nodes))
        self.assertEqual(read_road_metadata(text).source_signature, inp.source_signature)


if __name__ == "__main__":
    unittest.main()
