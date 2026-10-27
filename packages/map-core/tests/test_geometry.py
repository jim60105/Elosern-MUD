"""Mechanism tests for the explicit metric transforms and sparse routing."""

from __future__ import annotations

import math
import tracemalloc

import pytest

from elosern_map_core.geometry import (
    cell_center_m,
    is_on_mainland,
    is_within_frame,
    local_to_world_m,
    polygon_area_km2,
)
from elosern_map_core.sparse import (
    SparseGraphError,
    SparseNode,
    SparseRoad,
    SparseSettlementGraph,
    build_sparse_graph,
    compass_direction,
    exit_spawn_names,
)


def _node(node_id: str, x: int, y: int, *, key: str | None = None, physical=None) -> SparseNode:
    return SparseNode(
        node_id=node_id,
        x=x,
        y=y,
        prototype={"key": key or node_id},
        physical=physical,
    )


def _road(source: str, destination: str, **kwargs) -> SparseRoad:
    return SparseRoad(
        road_id=f"{source}>{destination}",
        source_id=source,
        destination_id=destination,
        **kwargs,
    )


class TestMetricTransforms:
    def test_cell_centre_is_half_a_kilometre_into_the_cell(self):
        assert cell_center_m((2, 3)) == (2500, 3500)
        assert cell_center_m((0, 0)) == (500, 500)
        assert cell_center_m((-1, -2)) == (-500, -1500)

    def test_world_point_is_anchor_centre_plus_local_minus_local_anchor(self):
        # Independently known: cell (2, 3) centres at (2500, 3500); a local
        # position offset by (+20, +20) from the local anchor lands there plus
        # that offset.
        assert local_to_world_m((2, 3), (10, 20), (30, 40)) == (2520, 3520)
        # A local position exactly at the anchor is the cell centre.
        assert local_to_world_m((2, 3), (10, 20), (10, 20)) == (2500, 3500)
        # Moving west/south of the anchor subtracts metres.
        assert local_to_world_m((2, 3), (10, 20), (0, 0)) == (2490, 3480)

    def test_transforms_reject_non_integer_input(self):
        with pytest.raises(ValueError):
            cell_center_m((1.5, 0))  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            cell_center_m((True, 0))  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            local_to_world_m((0, 0), (0,), (0, 0))  # type: ignore[arg-type]

    def test_frame_membership_is_half_open(self):
        assert is_within_frame(4, (0, 0))
        assert is_within_frame(4, (3, 3))
        assert not is_within_frame(4, (4, 0))
        assert not is_within_frame(4, (0, -1))
        with pytest.raises(ValueError):
            is_within_frame(0, (0, 0))

    def test_polygon_area_and_land_test_use_the_explicit_ring(self):
        square = ((0, 0), (4, 0), (4, 4), (0, 4))
        assert polygon_area_km2(square) == 16
        assert is_on_mainland(square, 2, 2)
        assert not is_on_mainland(square, 5, 2)
        # Boundary points and vertices count as land.
        assert is_on_mainland(square, 0, 2)
        assert is_on_mainland(square, 4, 4)
        with pytest.raises(ValueError):
            polygon_area_km2(((0, 0), (1, 1)))


class TestDirectedRoutes:
    def _bent_graph(self) -> SparseSettlementGraph:
        # Logical coordinates are a short east step; the authored physical
        # positions are a million metres apart and the authored direction is
        # north, so no derivation can produce the stored value by accident.
        return SparseSettlementGraph(
            "t_map",
            [
                _node("gate", 0, 0, physical=(0, 0)),
                _node("pass", 1, 0, physical=(1_000_000, 0)),
            ],
            [
                _road(
                    "gate",
                    "pass",
                    bend_points=((0, 700_000),),
                    direction_hint="n",
                )
            ],
        )

    def test_length_is_physical_polyline_metres_and_direction_is_authored(self):
        graph = self._bent_graph()
        edge = graph.edge("gate", "pass")
        assert edge is not None
        assert edge.direction == "n"
        expected = 700_000 + math.hypot(1_000_000, 700_000)
        assert edge.length == pytest.approx(expected)

        plan = graph.plan("gate", "pass")
        assert [step.exit_key for step in plan] == ["north"]
        assert [step.length for step in plan] == [pytest.approx(expected)]
        assert plan[0].source.node_id == "gate"
        assert plan[-1].destination.node_id == "pass"

    def test_reverse_travel_needs_its_own_road(self):
        graph = self._bent_graph()
        assert graph.route("pass", "gate") is None
        assert graph.plan("pass", "gate") == ()

        two_way = SparseSettlementGraph(
            graph.map_id,
            graph.nodes.values(),
            [*graph.roads, _road("pass", "gate", direction_hint="s")],
        )
        reverse = two_way.route("pass", "gate")
        assert reverse is not None
        assert [(edge.source.node_id, edge.destination.node_id) for edge in reverse] == [
            ("pass", "gate")
        ]

    def test_route_stays_bounded_by_graph_size_not_coordinate_span(self):
        tracemalloc.start()
        try:
            graph = SparseSettlementGraph(
                "span",
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
            route = graph.route("west", "far")
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        assert route is not None
        assert len(route) == 3
        assert peak < 1_000_000
        assert len({round(edge.length, 6) for edge in graph.edges}) == 3

    def test_shortest_route_prefers_the_shorter_polyline(self):
        # The direct road is bent far north, so its physical length (about 42 m)
        # exceeds the three-edge southern path (30 m). A hop-minimising search
        # would still choose the single edge, so this distinguishes length
        # weighting from hop counting.
        graph = SparseSettlementGraph(
            "t_map",
            [
                _node("a", 0, 0),
                _node("b", 0, 10),
                _node("c", 10, 10),
                _node("d", 10, 0),
            ],
            [
                _road("a", "b"),
                _road("b", "c"),
                _road("c", "d"),
                _road("a", "d", bend_points=((0, 20),), direction_hint="e"),
            ],
        )
        direct = graph.edge("a", "d")
        assert direct is not None
        assert direct.length == pytest.approx(20 + math.hypot(10, 20))
        route = graph.route("a", "d")
        assert route is not None
        assert [edge.destination.node_id for edge in route] == ["b", "c", "d"]
        assert sum(edge.length for edge in route) == 30
        assert graph.route("a", "a") == ()
        assert graph.route("a", "missing") is None

    def test_plan_between_coordinates_resolves_the_bindings(self):
        graph = self._bent_graph()
        assert [step.direction for step in graph.plan_between_coordinates((0, 0), (1, 0))] == ["n"]
        assert graph.plan_between_coordinates((0, 0), (9, 9)) == ()

    def test_display_projection_is_a_read_only_xy_map_surface(self):
        graph = self._bent_graph()
        projection = graph.display_projection()
        assert projection.Z == "t_map"
        assert projection.max_X == 1
        assert projection.max_Y == 0
        start = projection.get_node_from_coord((0, 0))
        assert start is not None
        assert start.links["n"].node_id == "pass"
        assert projection.get_node_from_coord((5, 5)) is None
        assert projection.get_node_from_coord(("x", "y")) is None  # type: ignore[arg-type]


class TestGraphValidation:
    def test_two_identities_binding_one_coordinate_are_refused(self):
        with pytest.raises(SparseGraphError):
            SparseSettlementGraph(
                "t_map", [_node("a", 1, 1), _node("b", 1, 1)], []
            )

    def test_duplicate_identity_is_refused(self):
        with pytest.raises(SparseGraphError):
            SparseSettlementGraph("t_map", [_node("a", 1, 1), _node("a", 2, 2)], [])

    def test_missing_endpoint_self_loop_duplicate_pair_and_direction_are_refused(self):
        nodes = [_node("a", 0, 0), _node("b", 1, 0)]
        with pytest.raises(SparseGraphError):
            SparseSettlementGraph("t_map", nodes, [_road("a", "missing")])
        with pytest.raises(SparseGraphError):
            SparseSettlementGraph("t_map", nodes, [_road("a", "a")])
        with pytest.raises(SparseGraphError):
            SparseSettlementGraph(
                "t_map", nodes, [_road("a", "b"), _road("a", "b")]
            )
        # Two roads leaving one node in the same authored direction would spawn
        # one exit key twice.
        with pytest.raises(SparseGraphError):
            SparseSettlementGraph(
                "t_map",
                [_node("a", 0, 0), _node("b", 0, 1), _node("c", 1, 1)],
                [
                    _road("a", "b", direction_hint="n"),
                    _road("a", "c", direction_hint="n"),
                ],
            )

    def test_empty_map_and_foreign_entries_are_refused(self):
        with pytest.raises(SparseGraphError):
            SparseSettlementGraph("t_map", [], [])
        with pytest.raises(SparseGraphError):
            SparseSettlementGraph("", [_node("a", 0, 0)], [])
        with pytest.raises(SparseGraphError):
            SparseSettlementGraph("t_map", [("a", 0, 0)], [])  # type: ignore[list-item]
        with pytest.raises(SparseGraphError):
            SparseSettlementGraph(
                "t_map", [_node("a", 0, 0)], [("a", "b")]  # type: ignore[list-item]
            )

    def test_node_and_road_declarations_validate_their_own_shape(self):
        with pytest.raises(SparseGraphError):
            SparseNode(node_id="", x=0, y=0, prototype={"key": "k"})
        with pytest.raises(SparseGraphError):
            SparseNode(node_id="a", x=0, y=0, prototype={})
        with pytest.raises(SparseGraphError):
            SparseNode(node_id="a", x=0, y=0, prototype={"key": "k"}, physical=(0.5, 0))  # type: ignore[arg-type]
        with pytest.raises(SparseGraphError):
            _road("a", "b", direction_hint="up")
        with pytest.raises(SparseGraphError):
            _road("a", "b", bend_points=((0, 1.5),))  # type: ignore[arg-type]

    def test_compass_direction_requires_a_non_zero_integer_delta(self):
        assert compass_direction(1, 0) == "e"
        assert compass_direction(-3, 4) == "nw"
        assert compass_direction(0, -9) == "s"
        assert exit_spawn_names("ne")[0] == "northeast"
        with pytest.raises(SparseGraphError):
            compass_direction(0, 0)
        with pytest.raises(SparseGraphError):
            compass_direction(True, 0)  # type: ignore[arg-type]

    def test_build_sparse_graph_rejects_identity_and_position_table_drift(self):
        prototypes = {(0, 0): {"key": "start"}, (1, 0): {"key": "end"}}
        node_ids = {(0, 0): "start", (1, 0): "end"}
        with pytest.raises(SparseGraphError):
            build_sparse_graph(
                map_id="t_map",
                prototypes=prototypes,
                node_ids={(0, 0): "start"},
                roads=[],
            )
        with pytest.raises(SparseGraphError):
            build_sparse_graph(
                map_id="t_map",
                prototypes=prototypes,
                node_ids=node_ids,
                roads=[("start", "end")],
                physical_positions={(0, 0): (0, 0)},
            )
        with pytest.raises(SparseGraphError):
            build_sparse_graph(
                map_id="t_map",
                prototypes=prototypes,
                node_ids=node_ids,
                roads=[("start", "end")],
                physical_positions={(0, 0): (0, 0), (1, 0): (10, 0), (2, 0): (20, 0)},
            )

    def test_build_sparse_graph_accepts_authored_directions_and_physical_positions(self):
        graph = build_sparse_graph(
            map_id="t_map",
            prototypes={(0, 0): {"key": "start"}, (1, 0): {"key": "end"}},
            node_ids={(0, 0): "start", (1, 0): "end"},
            roads=[("start", "end", "n")],
            physical_positions={(0, 0): (0, 0), (1, 0): (1000, 0)},
        )
        edge = graph.edge("start", "end")
        assert edge is not None
        assert edge.direction == "n"
        assert edge.length == 1000
        assert graph.node("end").physical_coordinate == (1000, 0)
