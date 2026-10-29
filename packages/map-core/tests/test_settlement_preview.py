"""Mechanism tests for settlement road lengths and the route preview.

Synthetic geometry with independently known lengths (3-4-5 triangles):
``a`` (0, 0), ``b`` (300, 400), ``c`` (300, 0).

- ``a>b`` straight: 500 m;
- ``b>a`` bending at (300, 0): 400 + 300 = 700 m;
- ``a>c`` 300 m and ``c>b`` 400 m, so the route a -> b through c is 700 m,
  longer than the straight 500 m road, which the planner must prefer.
"""

from __future__ import annotations

import pytest

from elosern_map_core import (
    road_lengths,
    settlement_route,
)
from elosern_map_core.codec import document_from_data

PATH = "content/maps/settlements/preview_map.yaml"


def _node(x: int, y: int) -> dict:
    return {
        "x_m": x,
        "y_m": y,
        "prototype_parent": "grid_room",
        "key": f"node {x},{y}",
        "desc": "",
        "anchor_key": None,
        "typeclass": None,
        "scene_archetype": None,
    }


def _settlement(nodes: dict, roads: list) -> object:
    return document_from_data(
        PATH,
        {
            "version": 1,
            "kind": "settlement",
            "id": "preview_map",
            "location_ref": "somewhere",
            "nodes": nodes,
            "roads": roads,
            "wilderness_entry": None,
            "city_gate": None,
        },
    )


def _road(source: str, destination: str, direction: str, bends=()) -> dict:
    return {
        "source": source,
        "destination": destination,
        "direction": direction,
        "bends": [{"x_m": x, "y_m": y} for x, y in bends],
    }


@pytest.fixture
def triangle():
    return _settlement(
        {"a": _node(0, 0), "b": _node(300, 400), "c": _node(300, 0)},
        [
            _road("a", "b", "n"),
            _road("b", "a", "s", bends=[(300, 0)]),
            _road("a", "c", "e"),
            _road("c", "b", "ne"),
        ],
    )


def test_road_lengths_are_physical_polylines_through_the_bends(triangle):
    lengths = road_lengths(triangle)
    assert lengths[("a", "b")] == pytest.approx(500.0)
    assert lengths[("b", "a")] == pytest.approx(700.0)
    assert lengths[("a", "c")] == pytest.approx(300.0)
    assert lengths[("c", "b")] == pytest.approx(400.0)


def test_the_route_takes_the_physically_shorter_path_with_authored_directions(triangle):
    route = settlement_route("preview_map", triangle, "a", "b")
    assert route.status == "route"
    assert [(step.source, step.destination, step.direction) for step in route.steps] == [("a", "b", "n")]
    assert route.length_m == pytest.approx(500.0)
    back = settlement_route("preview_map", triangle, "b", "c")
    # b -> a (700 m, bent) then a -> c (300 m): the only directed way to c.
    assert [step.destination for step in back.steps] == ["a", "c"]
    assert back.length_m == pytest.approx(1000.0)


def test_a_one_way_road_has_no_reverse_route():
    settlement = _settlement({"a": _node(0, 0), "b": _node(0, 10)}, [_road("a", "b", "n")])
    route = settlement_route("preview_map", settlement, "b", "a")
    assert (route.status, route.steps, route.length_m) == ("no_route", (), None)


def test_unknown_nodes_and_unbuildable_graphs_are_distinct_states(triangle):
    assert settlement_route("preview_map", triangle, "a", "ghost").status == "unknown_node"
    empty = _settlement({}, [])
    assert road_lengths(empty) == {}
    assert settlement_route("preview_map", empty, "a", "b").status == "unknown_node"
    # The same node is a route of no steps and zero length.
    lone = _settlement({"a": _node(0, 0)}, [])
    route = settlement_route("preview_map", lone, "a", "a")
    assert (route.status, route.steps, route.length_m) == ("route", (), 0)


def test_a_graph_the_core_refuses_reports_unavailable(triangle, monkeypatch):
    import elosern_map_core.authoring as authoring

    def refuse(*_args, **_kwargs):
        raise authoring.SparseGraphError("synthetic refusal")

    monkeypatch.setattr(authoring, "build_settlement_graph", refuse)
    route = settlement_route("preview_map", triangle, "a", "b")
    assert (route.status, route.steps, route.reason) == ("unavailable", (), "synthetic refusal")


def test_the_preview_dict_carries_every_step(triangle):
    data = settlement_route("preview_map", triangle, "b", "c").as_dict()
    assert data["status"] == "route"
    assert [step["direction"] for step in data["steps"]] == ["s", "e"]
    assert data["steps"][0]["length_m"] == pytest.approx(700.0)
