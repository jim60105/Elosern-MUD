"""Deterministic synthetic settlement generation.

Every fixture is synthetic: in-memory terrain windows for the pure generator,
and the editor's synthetic workspace for the commands. No shipped location, map
or node identifier appears here, and the command tests compare digests so a run
can never change a source it should have refused.

The structural checks are independent of the generator's own predicates: they
re-derive pairs, degrees, connectivity and bearings from the emitted document.
"""

from __future__ import annotations

import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from elosern_map_core.authoring import gate_approach_cell
from elosern_map_core.codec import (
    document_from_data,
    parse_document,
    serialize_document,
)
from elosern_map_core.roads_codec import encode_road_document

from tools.settlement_synthesis.budget import SizeBudget, size_budget
from tools.settlement_synthesis.fit_lint import lint_settlement
from tools.settlement_synthesis.generate import (
    GenerationConfig,
    GenerationError,
    GenerationInput,
    generate_settlement,
)
from tools.settlement_synthesis.geometry import (
    OCTANT_VECTORS,
    OPPOSITE,
    bearing,
    cell_of,
    octant_distance,
    point_to_cell_distance,
    world_position,
)
from tools.settlement_synthesis.roles import RoleEntry
from tools.settlement_synthesis.site import SettlementRef, analyse_site
from tools.settlement_synthesis.terrain_view import GridTerrain
from tools.settlement_synthesis.workspace import load_workspace
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parent.parent
EDITOR_TESTS = REPO_ROOT / "tools" / "map-editor" / "tests"

WINDOW = (0, 0, 30, 30)
LOCATION = (15, 15)


def _load(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, EDITOR_TESTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


synthetic = _load("synthetic_workspace")


def _window_cells(window: tuple[int, int, int, int] = WINDOW) -> frozenset[tuple[int, int]]:
    min_x, min_y, max_x, max_y = window
    return frozenset(
        (x, y) for y in range(min_y, max_y + 1) for x in range(min_x, max_x + 1)
    )


def _terrain(
    *,
    land: frozenset[tuple[int, int]] | None = None,
    inland_water: frozenset[tuple[int, int]] = frozenset(),
    impassable: frozenset[tuple[int, int]] = frozenset(),
    routes: dict | None = None,
    waterway_cells: dict | None = None,
    fords: dict | None = None,
    bands: dict | None = None,
    harbours: dict | None = None,
    window: tuple[int, int, int, int] = WINDOW,
) -> GridTerrain:
    cells = _window_cells(window)
    return GridTerrain(
        window=window,
        land=cells if land is None else frozenset(land),
        inland_water=frozenset(inland_water),
        impassable=frozenset(impassable),
        waterway_routes={} if routes is None else dict(routes),
        waterway_cells={} if waterway_cells is None else dict(waterway_cells),
        waterway_fords={} if fords is None else dict(fords),
        bands={} if bands is None else dict(bands),
        harbours={} if harbours is None else dict(harbours),
    )


def _open_terrain() -> GridTerrain:
    return _terrain()


def _river_terrain(
    *, ford: tuple[int, int] | None = None, column_x: int = 18
) -> GridTerrain:
    water = frozenset(
        (column_x, y) for y in range(0, 31) if ford is None or (column_x, y) != ford
    )
    return _terrain(
        inland_water=water,
        routes={"synthetic_river": ((column_x, 30), (column_x, 0))},
        waterway_cells={"synthetic_river": water},
        fords={} if ford is None else {"synthetic_river": (ford,)},
    )


def _coast_terrain(*, shoreline_x: int = 18) -> GridTerrain:
    return _terrain(
        land=frozenset(cell for cell in _window_cells() if cell[0] <= shoreline_x)
    )


def _slope_terrain() -> GridTerrain:
    return _terrain(bands={(x, y): y for x, y in _window_cells()})


def _ref(
    location_id: str = "site_a",
    kind: str = "town",
    nation: str | None = "nat_a",
    population: int | None = 5000,
    cell: tuple[int, int] = LOCATION,
) -> SettlementRef:
    return SettlementRef(location_id, kind, nation, population, cell)


CATALOGUE = (
    RoleEntry("market_street", "市場街", frozenset({"human_town"}), "near_anchor", 10, 0, None),
    RoleEntry("temple_forecourt", "神殿前", frozenset({"human_town"}), "high_ground", 30, 0, None),
    RoleEntry("inn_lane", "客棧巷", frozenset({"human_town"}), "near_anchor", 40, 8, None),
)


def _budget(
    footprint: int = 2,
    *,
    nodes: int = 10,
    gates: int = 2,
    loops: float = 0.2,
    radius: int | None = None,
    location_id: str = "site_a",
    population: int = 5000,
) -> SizeBudget:
    return SizeBudget(
        location_id=location_id,
        population=population,
        built_area_km2=float(footprint),
        footprint_cells=footprint,
        envelope_radius_m=(
            max(200, round(1000 * math.sqrt(footprint / math.pi)))
            if radius is None
            else radius
        ),
        node_count=nodes,
        gate_count=gates,
        loop_ratio=loops,
    )


def _input(
    ref: SettlementRef,
    terrain: GridTerrain,
    *,
    budget: SizeBudget | None = None,
    catalogue: tuple[RoleEntry, ...] = CATALOGUE,
    forced_gates: tuple[str, ...] = (),
    blocked: frozenset[tuple[int, int]] = frozenset(),
    roster: tuple[SettlementRef, ...] | None = None,
    map_id: str | None = None,
) -> GenerationInput:
    members = (ref,) if roster is None else roster
    return GenerationInput(
        map_id=ref.location_id if map_id is None else map_id,
        location=ref,
        site=analyse_site(ref, terrain, members),
        budget=_budget() if budget is None else budget,
        terrain=terrain,
        blocked=blocked,
        catalogue=catalogue,
        forced_gates=forced_gates,
        config=GenerationConfig(beast_nations=frozenset({"beastland"})),
    )


def _single_cell_input(
    ref: SettlementRef,
    road_contacts: tuple[tuple[int, int], ...] = (),
    *,
    terrain: GridTerrain | None = None,
    forced_gates: tuple[str, ...] = (),
    blocked: frozenset[tuple[int, int]] = frozenset(),
    roster: tuple[SettlementRef, ...] | None = None,
) -> GenerationInput:
    """The generator input of one village or hamlet, with its road contacts."""

    window = _open_terrain() if terrain is None else terrain
    members = (ref,) if roster is None else roster
    return GenerationInput(
        map_id=ref.location_id,
        location=ref,
        site=analyse_site(ref, window, members),
        budget=size_budget(ref),
        terrain=window,
        blocked=blocked,
        catalogue=CATALOGUE,
        forced_gates=forced_gates,
        config=GenerationConfig(beast_nations=frozenset({"beastland"})),
        road_contacts=road_contacts,
    )


def _document(result):
    return document_from_data(
        f"content/maps/settlements/{result.map_id}.yaml", result.data
    )


def _world_point(
    result, node_id: str, location_cell: tuple[int, int] = LOCATION
) -> tuple[int, int]:
    document = _document(result)
    anchor = document.local_anchor_m
    assert anchor is not None
    node = document.nodes[node_id]
    return world_position(location_cell, anchor, node.coordinate)


def _road_pairs(result) -> set[tuple[str, str]]:
    return {(road["source"], road["destination"]) for road in result.data["roads"]}


def _degrees(result) -> dict[str, int]:
    degrees = {node_id: 0 for node_id in result.data["nodes"]}
    for road in result.data["roads"]:
        degrees[road["source"]] += 1
    return degrees


def _reachable(result) -> set[str]:
    roads = result.data["roads"]
    adjacency: dict[str, list[str]] = {node_id: [] for node_id in result.data["nodes"]}
    for road in roads:
        adjacency[road["source"]].append(road["destination"])
    start = next(iter(result.data["nodes"]))
    seen = {start}
    stack = [start]
    while stack:
        for neighbour in adjacency[stack.pop()]:
            if neighbour not in seen:
                seen.add(neighbour)
                stack.append(neighbour)
    return seen


def _single_cell_geometry(result, location_cell: tuple[int, int] = LOCATION):
    document = _document(result)
    geometry = document.wilderness_geometry(location_cell)
    assert geometry is not None
    return document, geometry


def _gate_approaches(
    result, location_cell: tuple[int, int] = LOCATION
) -> list[tuple[int, int]]:
    """The exterior cell a traveller stands on to take each gate, sorted."""

    _document_, geometry = _single_cell_geometry(result, location_cell)
    return sorted(
        gate_approach_cell(geometry, gate.return_direction)
        for gate in geometry.gates
    )


def _assert_single_cell(test: unittest.TestCase, inp: GenerationInput, result) -> None:
    """The one-cell invariants every village and hamlet document keeps."""

    document, geometry = _single_cell_geometry(result, inp.location.cell)
    test.assertTrue(geometry.single_cell_footprint)
    test.assertEqual(geometry.hash_cell_count, 1)
    test.assertEqual(geometry.footprint_cells, frozenset({inp.location.cell}))
    test.assertEqual(result.footprint, frozenset({inp.location.cell}))

    anchor = document.local_anchor_m
    assert anchor is not None
    for node_id, node in document.nodes.items():
        test.assertEqual(
            cell_of(world_position(inp.location.cell, anchor, node.coordinate)),
            inp.location.cell,
            node_id,
        )

    anchor_id = document.anchor_node.node_id
    pairs = _road_pairs(result)
    for slot in result.slots:
        if slot.slot_id == anchor_id:
            continue
        test.assertIn((anchor_id, slot.slot_id), pairs)
        test.assertIn((slot.slot_id, anchor_id), pairs)

    # A forced gate is not derived from the roads, so the entrances are not
    # compared against them (design D7).
    road_contacts = None if inp.forced_gates else inp.road_contacts
    errors = [
        finding
        for finding in lint_settlement(
            document,
            inp.location.cell,
            inp.terrain,
            road_contacts=road_contacts,
        )
        if finding.severity == "error"
    ]
    test.assertEqual(errors, [])

    text = serialize_document(document, None)
    reparsed = parse_document(
        f"content/maps/settlements/{result.map_id}.yaml", text
    )
    test.assertEqual(serialize_document(reparsed.document, None), text)


def _is_connected(cells: set[tuple[int, int]]) -> bool:
    if not cells:
        return False
    start = next(iter(cells))
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for neighbour in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if neighbour in cells and neighbour not in seen:
                seen.add(neighbour)
                stack.append(neighbour)
    return seen == cells


def _assert_direction_geometry(test: unittest.TestCase, result) -> None:
    """Every direction matches its emitted segment, or a warning names it."""

    nodes = result.data["nodes"]
    for road in result.data["roads"]:
        source = nodes[road["source"]]
        destination = nodes[road["destination"]]
        direction = bearing(
            destination["x_m"] - source["x_m"],
            destination["y_m"] - source["y_m"],
        )
        if direction is None:
            continue
        if octant_distance(road["direction"], direction) > 2:
            test.assertIn(
                f"direction_deviation:{road['source']}", result.warnings
            )


class DeterminismTests(unittest.TestCase):
    @covers_requirement(
        "settlement-graph-generation::generation-is-deterministic-and-seeded-by-location-identity"
    )
    def test_repeat_runs_are_byte_identical(self) -> None:
        terrain = _open_terrain()
        first = generate_settlement(_input(_ref(), terrain))

        one = serialize_document(_document(first), None)
        again = generate_settlement(_input(_ref(), terrain))
        two = serialize_document(_document(again), None)

        self.assertEqual(one, two)
        reparsed = parse_document("content/maps/settlements/site_a.yaml", one)
        self.assertEqual(serialize_document(reparsed.document, None), one)

    @covers_requirement(
        "settlement-graph-generation::generation-is-deterministic-and-seeded-by-location-identity"
    )
    def test_different_identity_changes_the_layout(self) -> None:
        terrain = _open_terrain()

        first = generate_settlement(_input(_ref("site_a"), terrain))
        second = generate_settlement(_input(_ref("site_b"), terrain))

        def coordinates(result):
            return {
                (node["x_m"], node["y_m"]) for node in result.data["nodes"].values()
            }

        self.assertNotEqual(coordinates(first), coordinates(second))


class MorphologyTests(unittest.TestCase):
    @covers_requirement(
        "settlement-graph-generation::morphology-follows-the-site-and-a-dry-port-is-refused"
    )
    def test_selection_order(self) -> None:
        cases = (
            (
                "ring",
                _ref("site_ring", "town", "beastland"),
                _river_terrain(),
            ),
            ("harbour", _ref("site_harbour", "port"), _coast_terrain(shoreline_x=17)),
            (
                "crossing",
                _ref("site_crossing"),
                _river_terrain(ford=(18, 15)),
            ),
            ("waterside", _ref("site_waterside"), _river_terrain()),
            ("terraces", _ref("site_terraces"), _slope_terrain()),
            ("crossroads", _ref("site_crossroads"), _open_terrain()),
        )
        expected = {
            "ring": "tribal_ring",
            "harbour": "harbour_crescent",
            "crossing": "river_crossing",
            "waterside": "waterside_linear",
            "terraces": "hill_terraces",
            "crossroads": "crossroads",
        }

        for index, (label, ref, terrain) in enumerate(cases):
            with self.subTest(label=label):
                budget = _budget(6 if label == "crossing" else 5, nodes=10, radius=500,
                                 location_id=ref.location_id)
                result = generate_settlement(_input(ref, terrain, budget=budget))
                self.assertEqual(result.morphology, expected[label])

    @covers_requirement(
        "settlement-graph-generation::morphology-follows-the-site-and-a-dry-port-is-refused"
    )
    def test_dry_port_is_refused(self) -> None:
        ref = _ref("site_dry_port", "port")
        budget = _budget(2, nodes=10, radius=500, location_id=ref.location_id)

        with self.assertRaises(GenerationError) as caught:
            generate_settlement(_input(ref, _open_terrain(), budget=budget))

        self.assertIn("site_dry_port", str(caught.exception))
        self.assertIn("water_gap", str(caught.exception))


class FootprintTests(unittest.TestCase):
    @covers_requirement(
        "settlement-graph-generation::generated-footprints-are-connected-walkable-masks-centred-on-the-location"
    )
    def test_open_ground(self) -> None:
        ref = _ref()
        budget = _budget(5, nodes=10, radius=500)

        result = generate_settlement(_input(ref, _open_terrain(), budget=budget))

        self.assertEqual(len(result.footprint), 5)
        self.assertTrue(_is_connected(set(result.footprint)))
        self.assertIn(LOCATION, result.footprint)
        self.assertEqual(
            (
                (min(cell[0] for cell in result.footprint)
                 + max(cell[0] for cell in result.footprint)) // 2,
                (min(cell[1] for cell in result.footprint)
                 + max(cell[1] for cell in result.footprint)) // 2,
            ),
            LOCATION,
        )

    @covers_requirement(
        "settlement-graph-generation::generated-footprints-are-connected-walkable-masks-centred-on-the-location"
    )
    def test_blocked_cells_and_river_contact(self) -> None:
        ref = _ref()
        terrain = _river_terrain()
        budget = _budget(5, nodes=10, radius=500)
        # Both cells belong to the unblocked footprint, so ignoring `blocked`
        # would put them back.
        blocked = frozenset({(14, 15), (15, 16)})

        result = generate_settlement(
            _input(ref, terrain, budget=budget, blocked=blocked)
        )

        self.assertFalse(set(blocked) & set(result.footprint))
        river_cells = terrain.waterway_cells["synthetic_river"]
        touching = any(
            (cell[0] + dx, cell[1] + dy) in river_cells
            for cell in result.footprint
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
        )
        self.assertTrue(touching)

    @covers_requirement(
        "settlement-graph-generation::generated-footprints-are-connected-walkable-masks-centred-on-the-location"
    )
    def test_unreachable_water_is_refused(self) -> None:
        ref = _ref()
        neighbours = {
            (17 + dx, 15 + dy)
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            if (dx, dy) != (0, 0)
        }
        terrain = _terrain(
            inland_water=frozenset({(17, 15)}),
            routes={"synthetic_river": ((17, 20), (17, 0))},
            waterway_cells={"synthetic_river": frozenset({(17, 15)})},
        )

        with self.assertRaises(GenerationError) as caught:
            generate_settlement(
                _input(
                    ref,
                    terrain,
                    budget=_budget(2, nodes=10, radius=300),
                    blocked=frozenset(neighbours),
                )
            )

        self.assertIn("site_a", str(caught.exception))
        self.assertIn("water_unreachable", str(caught.exception))

    @covers_requirement(
        "settlement-graph-generation::generated-footprints-are-connected-walkable-masks-centred-on-the-location"
    )
    def test_corridor_reports_the_offset(self) -> None:
        ref = _ref()
        corridor = frozenset((x, LOCATION[1]) for x in range(0, LOCATION[0] + 1))
        terrain = _terrain(land=corridor)
        budget = _budget(5, nodes=10, radius=500)

        result = generate_settlement(_input(ref, terrain, budget=budget))

        midpoint = (
            (min(cell[0] for cell in result.footprint)
             + max(cell[0] for cell in result.footprint)) // 2,
            (min(cell[1] for cell in result.footprint)
             + max(cell[1] for cell in result.footprint)) // 2,
        )
        self.assertIn(midpoint, result.footprint)
        self.assertNotEqual(midpoint, LOCATION)
        self.assertIn("footprint_location_offset", result.warnings)

    @covers_requirement(
        "settlement-graph-generation::generated-footprints-are-connected-walkable-masks-centred-on-the-location"
    )
    def test_midpoint_outside_the_footprint_is_refused(self) -> None:
        ref = _ref()
        horizontal = {(x, 15) for x in range(12, 16)}
        vertical = {(12, y) for y in range(15, 19)}
        corridor = frozenset(horizontal | vertical)
        terrain = _terrain(
            land=corridor,
            inland_water=frozenset({(12, 18)}),
            routes={"synthetic_river": ((12, 20), (12, 0))},
            waterway_cells={"synthetic_river": frozenset({(12, 18)})},
        )
        budget = _budget(5, nodes=10, radius=500)

        with self.assertRaises(GenerationError) as caught:
            generate_settlement(_input(ref, terrain, budget=budget))

        self.assertIn("site_a", str(caught.exception))
        self.assertIn("anchor_outside_footprint", str(caught.exception))


class StructureTests(unittest.TestCase):
    @covers_requirement(
        "settlement-graph-generation::generated-graphs-satisfy-the-structure-rules-and-the-terrain-fit-lint"
    )
    def test_degree_cap_cannot_be_raised_above_six(self) -> None:
        with self.assertRaises(ValueError):
            GenerationConfig(max_degree=7)

    def _assert_structure(self, ref: SettlementRef, terrain: GridTerrain, result) -> None:
        nodes = result.data["nodes"]
        roads = result.data["roads"]
        node_count = len(nodes)

        self.assertEqual(node_count, len(result.slots))

        anchors = [
            node_id
            for node_id, node in nodes.items()
            if node["prototype_parent"] == "anchor_room"
        ]
        self.assertEqual(len(anchors), 1)
        self.assertEqual(nodes[anchors[0]]["anchor_key"], ref.location_id)
        anchor_slot = next(slot for slot in result.slots if slot.role == "anchor")
        self.assertEqual(anchor_slot.rel_m, (0.0, 0.0))

        coordinates = [(node["x_m"], node["y_m"]) for node in nodes.values()]
        self.assertEqual(len(set(coordinates)), len(coordinates))
        self.assertTrue(all(x >= 0 and y >= 0 for x, y in coordinates))

        pairs = _road_pairs(result)
        for source, destination in pairs:
            self.assertIn((destination, source), pairs)

        outgoing = {(road["source"], road["direction"]) for road in roads}
        self.assertEqual(len(outgoing), len(roads))
        degrees = _degrees(result)
        self.assertLessEqual(max(degrees.values()), 6)
        self.assertEqual(_reachable(result), set(nodes))

        loops = len(roads) // 2 - (node_count - 1)
        expected = round(0.2 * (node_count - 1))
        if loops != expected:
            self.assertIn(f"loop_shortfall:{expected - loops}", result.warnings)

        document = document_from_data(
            f"content/maps/settlements/{result.map_id}.yaml", result.data
        )
        findings = lint_settlement(document, ref.cell, terrain)
        self.assertEqual(
            [finding for finding in findings if finding.severity == "error"], []
        )

        _assert_direction_geometry(self, result)

    @covers_requirement(
        "settlement-graph-generation::generated-graphs-satisfy-the-structure-rules-and-the-terrain-fit-lint"
    )
    def test_open_riverside_and_coastal_layouts(self) -> None:
        cases = (
            ("open", _ref("site_open"), _open_terrain(), 5, "crossroads"),
            ("river", _ref("site_river"), _river_terrain(), 5, "waterside_linear"),
            (
                "coast",
                _ref("site_coast", "port"),
                _coast_terrain(shoreline_x=17),
                5,
                "harbour_crescent",
            ),
        )

        for label, ref, terrain, footprint, morphology in cases:
            with self.subTest(label=label):
                budget = _budget(
                    footprint, nodes=10, radius=500, location_id=ref.location_id
                )
                result = generate_settlement(
                    _input(ref, terrain, budget=budget, map_id=ref.location_id)
                )
                self.assertEqual(len(result.data["nodes"]), 10)
                self.assertEqual(result.morphology, morphology)
                self._assert_structure(ref, terrain, result)

    @covers_requirement(
        "settlement-graph-generation::generated-graphs-satisfy-the-structure-rules-and-the-terrain-fit-lint"
    )
    def test_collision_repaired_crossing_keeps_its_directions(self) -> None:
        # A ford on the location cell puts the plaza and the crossing on one
        # point; the document separates them by a metre, and the directions
        # must follow the emitted coordinates.
        water = frozenset((15, y) for y in range(0, 31) if y != 15)
        terrain = _terrain(
            inland_water=water,
            routes={"synthetic_river": ((15, 30), (15, 0))},
            waterway_cells={"synthetic_river": water},
            fords={"synthetic_river": ((15, 15),)},
        )
        result = generate_settlement(
            _input(
                _ref("site_ford"),
                terrain,
                budget=_budget(5, nodes=10, radius=500),
            )
        )

        self.assertEqual(result.morphology, "river_crossing")
        nodes = result.data["nodes"]
        self.assertEqual(
            nodes["ford_crossing"]["x_m"], nodes["central_plaza"]["x_m"] + 1
        )
        self.assertEqual(
            nodes["ford_crossing"]["y_m"], nodes["central_plaza"]["y_m"]
        )
        _assert_direction_geometry(self, result)


class GateTests(unittest.TestCase):
    @covers_requirement(
        "settlement-graph-generation::gates-face-their-neighbours-on-distinct-walkable-approaches"
    )
    def test_ordered_and_skipped_bearings(self) -> None:
        ref = _ref("site_gate")
        capital = _ref("cap_x", "capital", "nat_a", 90_000, (15, 21))
        neighbour = _ref("nb_east", "town", "nat_b", 4_000, (24, 15))
        terrain = _open_terrain()
        blocked = frozenset((17, y) for y in range(10, 21))
        budget = _budget(5, nodes=10, gates=3, radius=500, location_id=ref.location_id)

        result = generate_settlement(
            _input(
                ref,
                terrain,
                budget=budget,
                roster=(ref, capital, neighbour),
                forced_gates=("s",),
                blocked=blocked,
            )
        )

        gates = result.data["wilderness_entry"]["gates"]
        self.assertEqual(
            [gate["return_direction"] for gate in gates], ["n", "s", "e"]
        )
        self.assertEqual(
            [gate["destination_node"] for gate in gates],
            ["south_gate", "north_gate", "west_gate"],
        )

        anchor = next(slot for slot in result.slots if slot.role == "anchor")
        for slot in result.slots:
            if slot.role != "gate":
                continue
            outward = OCTANT_VECTORS[OPPOSITE[
                next(
                    gate["return_direction"]
                    for gate in gates
                    if gate["destination_node"] == slot.slot_id
                )
            ]]
            dot = (
                (slot.rel_m[0] - anchor.rel_m[0]) * outward[0]
                + (slot.rel_m[1] - anchor.rel_m[1]) * outward[1]
            )
            self.assertGreaterEqual(dot, 0)


class RoleTests(unittest.TestCase):
    @covers_requirement(
        "settlement-graph-generation::roles-come-from-the-catalogue-and-are-placed-by-the-site"
    )
    def test_class_and_budget_filter(self) -> None:
        catalogue = (
            RoleEntry("quay", "碼頭", frozenset({"port"}), "water_edge", 5, 0, None),
            RoleEntry("lane_far", "遠巷", frozenset({"human_town"}), "near_anchor", 20, 99, None),
            RoleEntry("market_street", "市場街", frozenset({"human_town"}), "near_anchor", 10, 0, None),
        )
        budget = _budget(5, nodes=10, radius=500)

        result = generate_settlement(
            _input(_ref(), _open_terrain(), budget=budget, catalogue=catalogue)
        )

        slot_ids = {slot.slot_id for slot in result.slots}
        self.assertIn("market_street", slot_ids)
        self.assertNotIn("quay", slot_ids)
        self.assertNotIn("lane_far", slot_ids)

    @covers_requirement(
        "settlement-graph-generation::roles-come-from-the-catalogue-and-are-placed-by-the-site"
    )
    def test_dry_and_river_sites(self) -> None:
        catalogue = (
            RoleEntry(
                "riverbank", "河岸道", frozenset({"human_town"}), "water_edge", 30, 0, "river"
            ),
        )
        dry = generate_settlement(
            _input(
                _ref("site_dry", cell=(15, 15)),
                _open_terrain(),
                budget=_budget(5, nodes=10, radius=500),
                catalogue=catalogue,
            )
        )
        self.assertNotIn("riverbank", {slot.slot_id for slot in dry.slots})

        terrain = _river_terrain()
        riverside = generate_settlement(
            _input(
                _ref("site_wet"),
                terrain,
                budget=_budget(5, nodes=10, radius=500),
                catalogue=catalogue,
            )
        )
        self.assertIn("riverbank", {slot.slot_id for slot in riverside.slots})
        point = _world_point(riverside, "riverbank")
        nearest = min(
            point_to_cell_distance(point, cell)
            for cell in terrain.waterway_cells["synthetic_river"]
        )
        self.assertLessEqual(nearest, 600)

    @covers_requirement(
        "settlement-graph-generation::roles-come-from-the-catalogue-and-are-placed-by-the-site"
    )
    def test_high_ground_goes_uphill(self) -> None:
        catalogue = (
            RoleEntry(
                "temple_forecourt", "神殿前", frozenset({"human_town"}), "high_ground", 30, 0, None
            ),
        )

        result = generate_settlement(
            _input(
                _ref(),
                _slope_terrain(),
                budget=_budget(5, nodes=10, radius=500),
                catalogue=catalogue,
            )
        )

        slot = next(slot for slot in result.slots if slot.slot_id == "temple_forecourt")
        self.assertGreater(slot.rel_m[1], 0)

    @covers_requirement(
        "settlement-graph-generation::roles-come-from-the-catalogue-and-are-placed-by-the-site"
    )
    def test_downstream_takes_the_easternmost_edge(self) -> None:
        terrain = _terrain(
            inland_water=frozenset((x, 14) for x in range(0, 31)),
            routes={"synthetic_river": ((1, 14), (29, 14))},
            waterway_cells={"synthetic_river": frozenset((x, 14) for x in range(0, 31))},
        )
        catalogue = (
            RoleEntry(
                "craft_alley", "工匠巷", frozenset({"human_town"}), "water_downstream", 50, 0, None
            ),
        )

        result = generate_settlement(
            _input(
                _ref(),
                terrain,
                budget=_budget(4, nodes=4, radius=300),
                catalogue=catalogue,
            )
        )

        slot = next(slot for slot in result.slots if slot.slot_id == "craft_alley")
        cell = cell_of(
            world_position(
                LOCATION,
                (0, 0),
                (int(round(slot.rel_m[0])), int(round(slot.rel_m[1]))),
            )
        )
        self.assertEqual(cell, (16, 15))


class SingleCellLayoutTests(unittest.TestCase):
    """A one-cell village or hamlet, with entrances that follow the roads."""

    @covers_requirement(
        "settlement-graph-generation::villages-and-hamlets-use-a-single-cell-layout-whose-entrances-follow-the-roads"
    )
    def test_through_road_gives_a_gate_per_contact(self) -> None:
        contacts = ((14, 15), (16, 15))
        village_input = _single_cell_input(
            _ref("single_village", kind="village", population=400), contacts
        )
        hamlet_input = _single_cell_input(
            _ref("single_hamlet", kind="hamlet", population=120), contacts
        )

        village = generate_settlement(village_input)
        hamlet = generate_settlement(hamlet_input)

        for inp, result in ((village_input, village), (hamlet_input, hamlet)):
            _assert_single_cell(self, inp, result)
            self.assertEqual(
                len(result.data["wilderness_entry"]["gates"]), len(contacts)
            )
            self.assertEqual(_gate_approaches(result), sorted(contacts))
            self.assertEqual(len(result.slots), inp.budget.node_count)

    @covers_requirement(
        "settlement-graph-generation::villages-and-hamlets-use-a-single-cell-layout-whose-entrances-follow-the-roads"
    )
    def test_spur_end_gives_one_gate(self) -> None:
        contacts = ((14, 15),)
        inp = _single_cell_input(
            _ref("single_village", kind="village", population=400), contacts
        )

        result = generate_settlement(inp)

        _assert_single_cell(self, inp, result)
        self.assertEqual(len(result.data["wilderness_entry"]["gates"]), 1)
        self.assertEqual(_gate_approaches(result), sorted(contacts))
        self.assertEqual(len(result.slots), inp.budget.node_count)

    @covers_requirement(
        "settlement-graph-generation::villages-and-hamlets-use-a-single-cell-layout-whose-entrances-follow-the-roads"
    )
    def test_junction_gives_a_gate_per_contact_and_one_extra_node(self) -> None:
        contacts = ((14, 15), (16, 15), (15, 16))
        village_input = _single_cell_input(
            _ref("single_village", kind="village", population=400), contacts
        )
        hamlet_input = _single_cell_input(
            _ref("single_hamlet", kind="hamlet", population=120), contacts
        )

        village = generate_settlement(village_input)
        hamlet = generate_settlement(hamlet_input)

        for inp, result in ((village_input, village), (hamlet_input, hamlet)):
            _assert_single_cell(self, inp, result)
            self.assertEqual(
                len(result.data["wilderness_entry"]["gates"]), len(contacts)
            )
            self.assertEqual(_gate_approaches(result), sorted(contacts))
            self.assertEqual(len(result.slots), inp.budget.node_count + 1)

    @covers_requirement(
        "settlement-graph-generation::villages-and-hamlets-use-a-single-cell-layout-whose-entrances-follow-the-roads"
    )
    def test_no_road_hamlet_gets_one_gate_and_a_village_is_refused(self) -> None:
        hamlet_input = _single_cell_input(
            _ref("single_hamlet", kind="hamlet", population=120)
        )
        hamlet = generate_settlement(hamlet_input)

        _assert_single_cell(self, hamlet_input, hamlet)
        gates = hamlet.data["wilderness_entry"]["gates"]
        self.assertEqual(len(gates), 1)
        self.assertEqual(len(hamlet.slots), hamlet_input.budget.node_count)
        approach = _gate_approaches(hamlet)[0]
        self.assertEqual(
            max(abs(approach[0] - LOCATION[0]), abs(approach[1] - LOCATION[1])), 1
        )
        self.assertTrue(hamlet_input.terrain.walkable(approach))
        self.assertNotIn(approach, hamlet_input.blocked)

        village_input = _single_cell_input(
            _ref("single_village", kind="village", population=400)
        )
        with self.assertRaises(GenerationError) as caught:
            generate_settlement(village_input)
        self.assertIn("no_road", str(caught.exception))

    def test_single_cell_generation_is_deterministic(self) -> None:
        def serialised(kind: str) -> str:
            inp = _single_cell_input(
                _ref(f"single_{kind}", kind=kind, population=400),
                ((14, 15), (16, 15)),
            )
            result = generate_settlement(inp)
            return serialize_document(_document(result), None)

        self.assertEqual(serialised("village"), serialised("village"))
        self.assertEqual(serialised("hamlet"), serialised("hamlet"))

    def test_hamlet_with_no_open_bearing_is_refused(self) -> None:
        neighbours = frozenset(
            (LOCATION[0] + delta_x, LOCATION[1] + delta_y)
            for delta_x, delta_y in OCTANT_VECTORS.values()
        )
        inp = _single_cell_input(
            _ref("single_hamlet", kind="hamlet", population=120),
            blocked=neighbours,
        )

        with self.assertRaises(GenerationError) as caught:
            generate_settlement(inp)

        self.assertIn("no_gate", str(caught.exception))

    def test_blocked_or_unwalkable_location_cell_is_refused(self) -> None:
        blocked = _single_cell_input(
            _ref("single_village", kind="village", population=400),
            ((14, 15),),
            blocked=frozenset({LOCATION}),
        )
        with self.assertRaises(GenerationError) as caught:
            generate_settlement(blocked)
        self.assertIn("location cell not walkable", str(caught.exception))

        sea = frozenset(
            (x, y) for y in range(0, 31) for x in range(0, 31) if (x, y) != LOCATION
        )
        flooded = _single_cell_input(
            _ref("single_village", kind="village", population=400),
            ((14, 15),),
            terrain=_terrain(land=sea),
        )
        with self.assertRaises(GenerationError) as caught:
            generate_settlement(flooded)
        self.assertIn("location cell not walkable", str(caught.exception))

    @covers_requirement(
        "settlement-graph-generation::villages-and-hamlets-use-a-single-cell-layout-whose-entrances-follow-the-roads"
    )
    def test_beast_nation_reuses_the_tribal_vocabulary(self) -> None:
        human_input = _single_cell_input(
            _ref("single_village", kind="village", population=400),
            ((14, 15), (16, 15)),
        )
        beast_input = _single_cell_input(
            _ref("single_village", kind="village", nation="beastland", population=400),
            ((14, 15), (16, 15)),
        )

        human = generate_settlement(human_input)
        beast = generate_settlement(beast_input)

        self.assertEqual(human.settlement_class, "human_town")
        self.assertEqual(beast.settlement_class, "beast_town")
        self.assertEqual(beast.morphology, "tribal_ring")
        self.assertEqual(len(beast.slots), len(human.slots))
        self.assertEqual(
            len(beast.data["wilderness_entry"]["gates"]),
            len(human.data["wilderness_entry"]["gates"]),
        )
        _assert_single_cell(self, beast_input, beast)

    def test_forced_gates_win_over_the_roads(self) -> None:
        contacts = ((14, 15), (16, 15))
        inp = _single_cell_input(
            _ref("single_village", kind="village", population=400),
            contacts,
            forced_gates=("s",),
        )

        result = generate_settlement(inp)

        _assert_single_cell(self, inp, result)
        self.assertEqual(len(result.data["wilderness_entry"]["gates"]), 1)
        self.assertEqual(_gate_approaches(result), [(15, 14)])
        self.assertEqual(len(result.slots), inp.budget.node_count)


class CommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._workspace_dir = tempfile.TemporaryDirectory()
        self._lore_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._workspace_dir.name)
        synthetic.write_workspace(self.root)
        self.towns: dict[str, tuple[int, int, int]] = {}
        self.lore_rows: dict[str, dict] = {
            "synthetic_place": {"nation": None, "population": 900_000}
        }
        self.lore = Path(self._lore_dir.name) / "lore.json"
        self._add_towns(
            {
                "synthetic_burg": (34, 8, 60_000),
                "synthetic_hamlet": (34, 14, 20_000),
            }
        )

    def _add_towns(self, towns: dict[str, tuple[int, int, int]]) -> None:
        self.towns.update(towns)
        locations = synthetic.locations_data()
        for location_id, (cell_x, cell_y, population) in self.towns.items():
            locations["locations"][location_id] = {
                "kind": "town",
                "display_name_zh": "合成城",
                "description": "A synthetic town.",
                "cell": {"cell_x": cell_x, "cell_y": cell_y},
                "geographic_constraint": "synthetic",
                "scene_archetype": None,
            }
            self.lore_rows[location_id] = {
                "nation": "nat_a",
                "population": population,
            }
        (self.root / "content" / "maps" / "locations.yaml").write_text(
            synthetic.yaml_text(locations), encoding="utf-8"
        )
        self.lore.write_text(json.dumps(self.lore_rows), encoding="utf-8")
        self.digest = synthetic.tree_digest(self.root)

    def tearDown(self) -> None:
        self._workspace_dir.cleanup()
        self._lore_dir.cleanup()

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.settlement_synthesis",
                *arguments,
                "--root",
                str(self.root),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

    def _write_existing_settlement(self, map_id: str, location_id: str) -> None:
        data = synthetic.settlement_data()
        data["id"] = map_id
        data["location_ref"] = location_id
        data["nodes"]["gate"]["anchor_key"] = location_id
        data["nodes"]["gate"]["x_m"] = 0
        data["nodes"]["gate"]["y_m"] = 0
        data["wilderness_entry"]["offset"] = {"dx": 0, "dy": 0}
        (self.root / "content" / "maps" / "settlements" / f"{map_id}.yaml").write_text(
            synthetic.yaml_text(data), encoding="utf-8"
        )

    @covers_requirement(
        "settlement-graph-generation::the-generator-never-overwrites-and-batches-in-a-fixed-order"
    )
    def test_existing_document_is_refused(self) -> None:
        # The stock workspace binds synthetic_place through a document with
        # another identity, so the refusal must find the binding, not the file.
        bound = self._run("generate", "synthetic_place", "--lore", str(self.lore))
        self.assertEqual(bound.returncode, 1, bound.stderr)
        self.assertIn("exists:", bound.stdout)
        self.assertIn("synthetic_town.yaml", bound.stdout)
        self.assertEqual(synthetic.tree_digest(self.root), self.digest)

        # A document under the canonical identity is refused before generation.
        self._write_existing_settlement("synthetic_burg", "synthetic_burg")
        digest = synthetic.tree_digest(self.root)
        canonical = self._run("generate", "synthetic_burg", "--lore", str(self.lore))
        self.assertEqual(canonical.returncode, 1, canonical.stderr)
        self.assertIn("exists: content/maps/settlements/synthetic_burg.yaml", canonical.stdout)
        self.assertEqual(synthetic.tree_digest(self.root), digest)

    @covers_requirement(
        "settlement-graph-generation::the-generator-never-overwrites-and-batches-in-a-fixed-order"
    )
    def test_plan_only_and_batch_order(self) -> None:
        plan = self._run(
            "generate", "--missing", "--nation", "nat_a", "--plan-only",
            "--lore", str(self.lore),
        )
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertEqual(synthetic.tree_digest(self.root), self.digest)
        self.assertFalse(
            (self.root / "content" / "maps" / "settlements" / "synthetic_burg.yaml").exists()
        )
        planned = _reports(plan.stdout)
        self.assertEqual(
            [report["map_id"] for report in planned],
            ["synthetic_burg", "synthetic_hamlet"],
        )

        batch = self._run(
            "generate", "--missing", "--nation", "nat_a", "--lore", str(self.lore)
        )
        self.assertEqual(batch.returncode, 0, batch.stderr)
        reports = _reports(batch.stdout)
        self.assertEqual(
            [report["map_id"] for report in reports],
            ["synthetic_burg", "synthetic_hamlet"],
        )
        settlements = self.root / "content" / "maps" / "settlements"
        self.assertTrue((settlements / "synthetic_burg.yaml").is_file())
        self.assertTrue((settlements / "synthetic_hamlet.yaml").is_file())

        footprints = []
        for map_id, cell in (("synthetic_burg", (34, 8)), ("synthetic_hamlet", (34, 14))):
            text = (settlements / f"{map_id}.yaml").read_text(encoding="utf-8")
            document = parse_document(
                f"content/maps/settlements/{map_id}.yaml", text
            ).document
            geometry = document.wilderness_geometry(cell)
            assert geometry is not None
            footprints.append(geometry.footprint_cells)
        self.assertFalse(footprints[0] & footprints[1])

        # The reload each batch step performs must see the earlier footprint.
        blocked = load_workspace(self.root, self.lore).blocked_cells("synthetic_hamlet")
        for cell in footprints[0]:
            self.assertIn(cell, blocked)

        lint = self._run("lint")
        self.assertEqual(lint.returncode, 0, lint.stdout + lint.stderr)

    @covers_requirement(
        "settlement-graph-generation::the-generator-never-overwrites-and-batches-in-a-fixed-order"
    )
    def test_blocked_cells_reserves_other_sources_and_excludes_own_location(self) -> None:
        blocked = load_workspace(self.root, self.lore).blocked_cells("synthetic_burg")

        # synthetic_town's point mask, its gate approach and its location cell.
        self.assertIn((5, 5), blocked)
        # Another town's location cell is reserved.
        self.assertIn((34, 14), blocked)
        # This map's own location row is not.
        self.assertNotIn((34, 8), blocked)

    @covers_requirement(
        "settlement-graph-generation::the-generator-never-overwrites-and-batches-in-a-fixed-order"
    )
    def test_later_batch_map_avoids_the_earlier_mask(self) -> None:
        # synthetic_edge sits two cells west of synthetic_burg; on its own its
        # footprint reaches into burg's mask, so the batch must reserve it.
        self._add_towns({"synthetic_edge": (32, 8, 20_000)})

        batch = self._run(
            "generate", "--missing", "--nation", "nat_a", "--lore", str(self.lore)
        )

        self.assertEqual(batch.returncode, 0, batch.stderr)
        self.assertEqual(
            [report["map_id"] for report in _reports(batch.stdout)],
            ["synthetic_burg", "synthetic_edge", "synthetic_hamlet"],
        )
        settlements = self.root / "content" / "maps" / "settlements"
        footprints = {}
        for map_id, cell in (
            ("synthetic_burg", (34, 8)),
            ("synthetic_edge", (32, 8)),
        ):
            text = (settlements / f"{map_id}.yaml").read_text(encoding="utf-8")
            document = parse_document(
                f"content/maps/settlements/{map_id}.yaml", text
            ).document
            geometry = document.wilderness_geometry(cell)
            assert geometry is not None
            footprints[map_id] = geometry.footprint_cells

        self.assertIn((33, 8), footprints["synthetic_burg"])
        self.assertNotIn((33, 8), footprints["synthetic_edge"])
        self.assertFalse(
            footprints["synthetic_burg"] & footprints["synthetic_edge"]
        )


class SingleCellCommandTests(unittest.TestCase):
    """The batch and replace rules of the two single-cell kinds."""

    def setUp(self) -> None:
        self._workspace_dir = tempfile.TemporaryDirectory()
        self._lore_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._workspace_dir.cleanup)
        self.addCleanup(self._lore_dir.cleanup)
        self.root = Path(self._workspace_dir.name)
        synthetic.write_workspace(self.root)
        self.lore = Path(self._lore_dir.name) / "lore.json"
        self._add_locations(
            {
                "synthetic_burg": ((34, 8), "town", 60_000),
                "synthetic_village": ((34, 14), "village", 400),
                "synthetic_hamlet": ((34, 20), "hamlet", 120),
            }
        )
        # A road through the village's cell, so its two gates follow it.
        self._write_roads(
            [
                (
                    "synthetic_road_a",
                    "synthetic_road_b",
                    [(34, 12), (34, 13), (34, 14), (34, 15)],
                )
            ]
        )
        self.digest = synthetic.tree_digest(self.root)

    def _add_locations(
        self, rows: dict[str, tuple[tuple[int, int], str, int]]
    ) -> None:
        locations = synthetic.locations_data()
        lore_rows: dict[str, dict] = {
            "synthetic_place": {"nation": None, "population": 900_000}
        }
        for location_id, (cell, kind, population) in rows.items():
            locations["locations"][location_id] = {
                "kind": kind,
                "display_name_zh": "合成聚落",
                "description": "A synthetic settlement.",
                "cell": {"cell_x": cell[0], "cell_y": cell[1]},
                "geographic_constraint": "synthetic",
                "scene_archetype": None,
            }
            lore_rows[location_id] = {"nation": "nat_a", "population": population}
        (self.root / "content" / "maps" / "locations.yaml").write_text(
            synthetic.yaml_text(locations), encoding="utf-8"
        )
        self.lore.write_text(json.dumps(lore_rows), encoding="utf-8")

    def _write_roads(self, roads: list[tuple[str, str, list[tuple[int, int]]]]) -> None:
        path = self.root / "world" / "maps" / "data" / "road_network.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            encode_road_document(
                frame_cells=40,
                source_signature="synthetic",
                nodes=["synthetic_road_a", "synthetic_road_b"],
                roads=roads,
            ),
            encoding="utf-8",
        )

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "tools.settlement_synthesis",
                *arguments,
                "--root",
                str(self.root),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )

    @covers_requirement(
        "settlement-graph-generation::the-generator-never-overwrites-and-batches-in-a-fixed-order"
    )
    def test_batch_reaches_both_kinds_and_takes_a_kind_filter(self) -> None:
        settlements = self.root / "content" / "maps" / "settlements"

        hamlets = self._run(
            "generate", "--missing", "--nation", "nat_a", "--kind", "hamlet",
            "--lore", str(self.lore),
        )

        self.assertEqual(hamlets.returncode, 0, hamlets.stderr)
        self.assertEqual(
            [report["map_id"] for report in _reports(hamlets.stdout)],
            ["synthetic_hamlet"],
        )
        self.assertTrue((settlements / "synthetic_hamlet.yaml").is_file())
        self.assertFalse((settlements / "synthetic_village.yaml").exists())

        rest = self._run(
            "generate", "--missing", "--nation", "nat_a", "--lore", str(self.lore)
        )

        self.assertEqual(rest.returncode, 0, rest.stderr)
        self.assertEqual(
            [report["map_id"] for report in _reports(rest.stdout)],
            ["synthetic_burg", "synthetic_village"],
        )
        for map_id in ("synthetic_burg", "synthetic_village"):
            self.assertTrue((settlements / f"{map_id}.yaml").is_file())

        village = parse_document(
            "content/maps/settlements/synthetic_village.yaml",
            (settlements / "synthetic_village.yaml").read_text(encoding="utf-8"),
        ).document
        geometry = village.wilderness_geometry((34, 14))
        assert geometry is not None
        self.assertTrue(geometry.single_cell_footprint)
        self.assertEqual(geometry.footprint_cells, frozenset({(34, 14)}))
        self.assertEqual(
            sorted(
                gate_approach_cell(geometry, gate.return_direction)
                for gate in geometry.gates
            ),
            [(34, 13), (34, 15)],
        )

        lint = self._run("lint")
        self.assertEqual(lint.returncode, 0, lint.stdout + lint.stderr)

    @covers_requirement(
        "settlement-graph-generation::the-generator-never-overwrites-and-batches-in-a-fixed-order"
    )
    def test_replace_is_refused_for_a_village(self) -> None:
        batch = self._run(
            "generate", "--missing", "--nation", "nat_a", "--lore", str(self.lore)
        )
        self.assertEqual(batch.returncode, 0, batch.stderr)
        digest = synthetic.tree_digest(self.root)
        bind = Path(self._lore_dir.name) / "bind.json"
        bind.write_text(json.dumps({"bindings": {}}), encoding="utf-8")

        replaced = self._run(
            "generate", "synthetic_village", "--replace", "--bind", str(bind),
            "--lore", str(self.lore),
        )

        self.assertEqual(replaced.returncode, 1, replaced.stderr)
        self.assertIn("single_cell_replace: synthetic_village", replaced.stdout)
        self.assertEqual(synthetic.tree_digest(self.root), digest)

    @covers_requirement(
        "settlement-graph-generation::the-generator-never-overwrites-and-batches-in-a-fixed-order"
    )
    def test_kind_is_an_argument_error_outside_a_batch(self) -> None:
        without_batch = self._run(
            "generate", "synthetic_village", "--kind", "village",
            "--lore", str(self.lore),
        )

        self.assertEqual(without_batch.returncode, 2)
        self.assertIn("--kind requires --missing", without_batch.stderr)
        self.assertEqual(synthetic.tree_digest(self.root), self.digest)

        unknown = self._run(
            "generate", "--missing", "--nation", "nat_a", "--kind", "thorp",
            "--lore", str(self.lore),
        )

        self.assertEqual(unknown.returncode, 2)
        self.assertIn("invalid choice", unknown.stderr)
        self.assertEqual(synthetic.tree_digest(self.root), self.digest)


def _reports(text: str) -> list[dict]:
    decoder = json.JSONDecoder()
    index = 0
    reports = []
    while True:
        while index < len(text) and text[index].isspace():
            index += 1
        if index >= len(text):
            break
        report, index = decoder.raw_decode(text, index)
        reports.append(report)
    return reports


if __name__ == "__main__":
    unittest.main()
