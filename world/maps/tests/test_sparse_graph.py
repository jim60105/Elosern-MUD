"""Pure tests for the sparse settlement graph and its route adapter."""

from math import hypot
import tracemalloc
import unittest

from tools.spec_traceability import covers_requirement

from elosern_map_core.sparse import (
    SparseGraphError,
    SparseNode,
    SparseRoad,
    SparseSettlementGraph,
    build_sparse_graph,
    compass_direction,
)


def _node(node_id, x, y, key=None):
    return SparseNode(
        node_id=node_id,
        x=x,
        y=y,
        prototype={"key": key or node_id, "prototype_parent": "grid_room"},
    )


def _road(source, destination, **kwargs):
    return SparseRoad(
        road_id=f"{source}>{destination}",
        source_id=source,
        destination_id=destination,
        **kwargs,
    )


class SparseGraphValidationTests(unittest.TestCase):
    @covers_requirement("grid-room-sync::sparse-authored-graphs-synchronize-without-identity-loss")
    def test_two_identities_binding_the_same_coordinate_are_refused(self):
        # The refusal happens at construction, before any caller can persist a
        # room, tag, reference or cached coordinate.
        with self.assertRaises(SparseGraphError):
            SparseSettlementGraph(
                "t_map",
                [_node("a", 1, 1), _node("b", 1, 1)],
                [],
            )

    def test_duplicate_identity_is_refused(self):
        with self.assertRaises(SparseGraphError):
            SparseSettlementGraph(
                "t_map",
                [_node("a", 1, 1), _node("a", 2, 2)],
                [],
            )

    def test_unknown_road_endpoint_is_refused(self):
        with self.assertRaises(SparseGraphError):
            SparseSettlementGraph(
                "t_map",
                [_node("a", 0, 0), _node("b", 1, 0)],
                [_road("a", "missing")],
            )

    def test_self_loop_duplicate_pair_and_duplicate_direction_are_refused(self):
        nodes = [_node("a", 0, 0), _node("b", 1, 0)]
        with self.subTest("self-loop"):
            with self.assertRaises(SparseGraphError):
                SparseSettlementGraph("t_map", nodes, [_road("a", "a")])
        with self.subTest("duplicate ordered pair"):
            with self.assertRaises(SparseGraphError):
                SparseSettlementGraph(
                    "t_map",
                    nodes,
                    [
                        _road("a", "b"),
                        SparseRoad(
                            road_id="second",
                            source_id="a",
                            destination_id="b",
                        ),
                    ],
                )
        with self.subTest("duplicate outgoing direction"):
            with self.assertRaises(SparseGraphError):
                SparseSettlementGraph(
                    "t_map",
                    [_node("a", 0, 0), _node("b", 1, 0), _node("c", 2, 0)],
                    # Both roads leave ``a`` east.
                    [_road("a", "b"), _road("a", "c")],
                )

    def test_identity_table_and_prototypes_must_describe_the_same_cells(self):
        prototypes = {(0, 0): {"key": "起點"}, (1, 0): {"key": "終點"}}
        with self.assertRaises(SparseGraphError):
            build_sparse_graph(
                map_id="t_map",
                prototypes=prototypes,
                node_ids={(0, 0): "start"},
                roads=(("start", "end"),),
            )

    def test_compass_direction_rejects_non_integer_and_zero_deltas(self):
        self.assertEqual(compass_direction(1, 0), "e")
        self.assertEqual(compass_direction(0, -1), "s")
        self.assertEqual(compass_direction(-1, 1), "nw")
        with self.assertRaises(SparseGraphError):
            compass_direction(0, 0)
        with self.assertRaises(SparseGraphError):
            compass_direction(True, 0)


class SparseRouteTests(unittest.TestCase):
    def _huge_graph(self):
        # Four nodes spanning millions of coordinate units connected by only
        # three straight roads of unequal physical length.
        return SparseSettlementGraph(
            "t_map",
            [
                _node("west", 0, 0),
                _node("north", 1_000_000, 7),
                _node("east", 1_000_003, 2_000_000),
                _node("far", 3_000_000, 2_000_001),
            ],
            [
                _road("west", "north"),
                _road("north", "east"),
                _road("east", "far"),
            ],
        )

    @covers_requirement("grid-room-sync::sparse-authored-graphs-synchronize-without-identity-loss")
    def test_route_uses_the_three_explicit_roads_with_their_physical_lengths(self):
        graph = self._huge_graph()
        route = graph.route("west", "far")
        self.assertIsNotNone(route)
        self.assertEqual(
            [(edge.source.node_id, edge.destination.node_id) for edge in route],
            [("west", "north"), ("north", "east"), ("east", "far")],
        )
        # Independently known lengths from the authored coordinates.
        expected = (
            hypot(1_000_000, 7)
            + hypot(3, 1_999_993)
            + hypot(1_999_997, 1)
        )
        self.assertAlmostEqual(sum(edge.length for edge in route), expected)
        self.assertEqual(len({round(edge.length, 6) for edge in graph.edges}), 3)

    def test_route_allocates_by_graph_size_not_coordinate_span(self):
        # A meter lattice over these coordinates would be untenable; the
        # search must stay bounded by the four nodes and three roads.
        tracemalloc.start()
        try:
            graph = self._huge_graph()
            route = graph.route("west", "far")
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertEqual(len(route), 3)
        self.assertLess(peak, 1_000_000)

    def test_plan_names_the_exit_and_tracks_unequal_steps(self):
        graph = self._huge_graph()
        plan = graph.plan("west", "far")
        self.assertEqual(
            [step.exit_key for step in plan], ["northeast", "northeast", "northeast"]
        )
        self.assertEqual(plan[0].source.node_id, "west")
        self.assertEqual(plan[-1].destination.node_id, "far")

    def test_unreachable_and_unknown_routes_return_no_route(self):
        graph = SparseSettlementGraph(
            "t_map",
            [_node("a", 0, 0), _node("b", 10, 10)],
            [],
        )
        self.assertIsNone(graph.route("a", "b"))
        self.assertIsNone(graph.route("a", "unknown"))
        self.assertEqual(graph.plan("a", "b"), ())
        self.assertEqual(graph.route("a", "a"), ())


class PhysicalGeometryTests(unittest.TestCase):
    """Authored meter positions drive lengths without rewriting compass exits."""

    def test_physical_positions_must_cover_exactly_the_authored_identities(self):
        prototypes = {(0, 0): {"key": "起點"}, (1, 0): {"key": "終點"}}
        node_ids = {(0, 0): "start", (1, 0): "end"}
        with self.assertRaises(SparseGraphError):
            build_sparse_graph(
                map_id="t_map",
                prototypes=prototypes,
                node_ids=node_ids,
                roads=[("start", "end")],
                physical_positions={(0, 0): (0, 0)},
            )
        with self.assertRaises(SparseGraphError):
            build_sparse_graph(
                map_id="t_map",
                prototypes=prototypes,
                node_ids=node_ids,
                roads=[("start", "end")],
                physical_positions={(0, 0): (0, 0), (1, 0): (10, 0), (1, 1): (1, 1)},
            )

    def test_lengths_use_physical_positions_while_direction_uses_logical_ones(self):
        graph = build_sparse_graph(
            map_id="t_map",
            prototypes={
                (0, 0): {"key": "起點"},
                (1, 0): {"key": "終點"},
            },
            node_ids={(0, 0): "start", (1, 0): "end"},
            roads=[("start", "end")],
            physical_positions={(0, 0): (0, 0), (1, 0): (1000, 0)},
        )
        edge = graph.edge("start", "end")
        self.assertEqual(edge.length, 1000)
        self.assertEqual(edge.direction, "e")
        self.assertEqual(graph.node("end").physical_coordinate, (1000, 0))

    @covers_requirement("grid-room-sync::sparse-authored-graphs-synchronize-without-identity-loss")
    def test_shipped_settlement_graphs_carry_distinct_meter_positions(self):
        from world.maps.map_data import SETTLEMENT_GRAPHS

        self.assertTrue(SETTLEMENT_GRAPHS)
        for map_id, graph in SETTLEMENT_GRAPHS.items():
            with self.subTest(map_id=map_id):
                # The authored coordinate IS the integer-metre local position;
                # no second physical table survives the cutover.
                positions = [node.coordinate for node in graph.nodes.values()]
                self.assertEqual(len(set(positions)), len(positions))
                self.assertTrue(
                    all(node.physical is None for node in graph.nodes.values())
                )
                # Compass exits remain the authored octants, declared on each
                # directed road rather than guessed from oblique metre deltas.
                for edge in graph.edges:
                    self.assertIsNotNone(edge.road.direction_hint)
                    self.assertEqual(edge.direction, edge.road.direction_hint)
                # Meter spacing is unequal: a path charges unequal lengths.
                self.assertGreater(len({round(edge.length, 6) for edge in graph.edges}), 1)
