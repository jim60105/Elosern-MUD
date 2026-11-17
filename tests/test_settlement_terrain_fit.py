"""Settlement site analysis, size budget and the terrain-fit lint.

Every fixture is synthetic: in-memory terrain windows for the pure functions,
and the editor's own synthetic workspace for the commands. No shipped location,
map or node identifier appears here, and every command run is checked for a
read-only workspace.
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

from elosern_map_core.codec import document_from_data
from elosern_map_core.roads_codec import encode_road_document

from tools.settlement_synthesis.budget import (
    BudgetConfig,
    BudgetError,
    Tier,
    size_budget,
)
from tools.settlement_synthesis.fit_lint import (
    CROSSING_WORDS,
    WATER_EDGE_WORDS,
    lint_settlement,
    words,
)
from tools.settlement_synthesis.site import SettlementRef, analyse_site
from tools.settlement_synthesis.terrain_view import GridTerrain
from tools.settlement_synthesis.workspace import WorkspaceError, load_workspace
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parent.parent
EDITOR_TESTS = REPO_ROOT / "tools" / "map-editor" / "tests"

WINDOW = (0, 0, 20, 20)

#: The location cell every lint fixture resolves its local frame against.
LOCATION_CELL = (10, 10)

#: The anchor's local metre point, which puts it on the location cell centre.
ANCHOR_LOCAL = (2000, 500)


def _load(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, EDITOR_TESTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


synthetic = _load("synthetic_workspace")


def _window_cells(
    window: tuple[int, int, int, int] = WINDOW,
) -> frozenset[tuple[int, int]]:
    min_x, min_y, max_x, max_y = window
    return frozenset(
        (x, y) for x in range(min_x, max_x + 1) for y in range(min_y, max_y + 1)
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


def _node(x_m: int, y_m: int, *, anchor: bool = False) -> dict:
    return {
        "x_m": x_m,
        "y_m": y_m,
        "prototype_parent": "anchor_room" if anchor else "grid_room",
        "key": "Fit Room",
        "desc": "",
        "anchor_key": "fit_place" if anchor else None,
        "typeclass": None,
        "scene_archetype": None,
    }


def _road(source: str, destination: str, direction: str) -> dict:
    return {
        "source": source,
        "destination": destination,
        "direction": direction,
        "bends": [],
    }


def _document(
    nodes,
    roads=(),
    shape=None,
    offset=(0, 0),
    gates=(),
    single_cell_footprint=None,
):
    wilderness_entry = None
    if shape is not None:
        wilderness_entry = {
            "shape": list(shape),
            "offset": {"dx": offset[0], "dy": offset[1]},
            "gates": [dict(gate) for gate in gates],
        }
        if single_cell_footprint is not None:
            wilderness_entry["single_cell_footprint"] = single_cell_footprint
    data = {
        "version": 1,
        "kind": "settlement",
        "id": "fit_case",
        "location_ref": "fit_place",
        "options": {"map_visual_range": 2, "map_mode": "nodes"},
        "nodes": dict(nodes),
        "roads": [dict(road) for road in roads],
        "wilderness_entry": wilderness_entry,
    }
    return document_from_data("content/maps/settlements/fit_case.yaml", data)


def _river_terrain() -> GridTerrain:
    """A river column at x=12 with a ford at (12, 5)."""

    water = frozenset(
        (12, y) for y in range(0, 21) if y != 5
    )
    return _terrain(
        inland_water=water,
        routes={"r": ((12, 20), (12, 0))},
        waterway_cells={"r": water},
        fords={"r": ((12, 5),)},
    )


def _ref(
    location_id: str = "site_a",
    kind: str = "town",
    nation: str | None = "nat_a",
    population: int | None = 5000,
    cell: tuple[int, int] = (10, 10),
) -> SettlementRef:
    return SettlementRef(location_id, kind, nation, population, cell)


#: One gate per direction, with the node it targets: the node stands outward
#: along the gate's bearing from the anchor, so no gate-side warning fires.
GATE_NODES = {
    "w": ("gate_w", 3000, 500),
    "e": ("gate_e", 1000, 500),
    "n": ("gate_n", 2000, -500),
    "s": ("gate_s", 2000, 1500),
}


def _entrance_document(
    directions: tuple[str, ...],
    *,
    shape: tuple[str, ...] = ("#",),
    single_cell_footprint: bool = True,
) -> object:
    """One map whose gates take the given return directions."""

    nodes = {"inn": _node(*ANCHOR_LOCAL, anchor=True)}
    gates = []
    for direction in directions:
        node_id, x_m, y_m = GATE_NODES[direction]
        nodes[node_id] = _node(x_m, y_m)
        gates.append({"return_direction": direction, "destination_node": node_id})
    return _document(
        nodes,
        shape=list(shape),
        gates=gates,
        single_cell_footprint=True if single_cell_footprint else None,
    )


def _road_network_text(roads) -> str:
    return encode_road_document(
        frame_cells=40,
        source_signature="synthetic",
        nodes=[f"synthetic_road_{letter}" for letter in ("a", "b", "c")],
        roads=roads,
    )


class SiteContextTests(unittest.TestCase):
    @covers_requirement(
        "settlement-terrain-fit::site-context-derives-water-relief-and-neighbour-bearings-from-terrain"
    )
    def test_river_contact_with_flow(self) -> None:
        cells = frozenset((13, y) for y in range(0, 21))
        terrain = _terrain(
            inland_water=cells,
            routes={"r": ((13, 20), (13, 0))},
            waterway_cells={"r": cells},
        )

        context = analyse_site(_ref(), terrain, (_ref(),), radius=8)

        self.assertEqual(len(context.rivers), 1)
        contact = context.rivers[0]
        self.assertEqual((contact.kind, contact.name), ("river", "r"))
        self.assertAlmostEqual(contact.distance_cells, 3.0)
        self.assertEqual(contact.nearest_cell, (13, 10))
        self.assertEqual(contact.bearing, "e")
        self.assertEqual(contact.downstream, "s")

    @covers_requirement(
        "settlement-terrain-fit::site-context-derives-water-relief-and-neighbour-bearings-from-terrain"
    )
    def test_sea_contact_and_absent_water(self) -> None:
        coast = _terrain(
            land=frozenset(cell for cell in _window_cells() if cell[0] >= 7)
        )

        context = analyse_site(_ref(), coast, (_ref(),), radius=8)

        self.assertIsNotNone(context.sea)
        assert context.sea is not None
        self.assertEqual(context.sea.kind, "sea")
        self.assertIsNone(context.sea.name)
        self.assertIsNone(context.sea.downstream)
        self.assertAlmostEqual(context.sea.distance_cells, 4.0)
        self.assertEqual(context.sea.nearest_cell, (6, 10))
        self.assertEqual(context.sea.bearing, "w")
        self.assertEqual(context.rivers, ())

        inland = analyse_site(_ref(), _terrain(), (_ref(),), radius=8)

        self.assertEqual(inland.rivers, ())
        self.assertIsNone(inland.sea)

    @covers_requirement(
        "settlement-terrain-fit::site-context-derives-water-relief-and-neighbour-bearings-from-terrain"
    )
    def test_uphill_bearing_and_flat_ground(self) -> None:
        rising = _terrain(bands={(x, y): y for x, y in _window_cells()})

        context = analyse_site(_ref(), rising, (_ref(),), relief_radius=3)

        self.assertEqual(context.relief, 6)
        self.assertEqual(context.uphill, "n")

        flat = _terrain(bands={(x, y): 5 for x, y in _window_cells()})
        flat_context = analyse_site(_ref(), flat, (_ref(),), relief_radius=3)

        self.assertEqual(flat_context.relief, 0)
        self.assertIsNone(flat_context.uphill)

    @covers_requirement(
        "settlement-terrain-fit::site-context-derives-water-relief-and-neighbour-bearings-from-terrain"
    )
    def test_neighbours_and_capital_bearing(self) -> None:
        site = _ref("site_a")
        capital = _ref("cap_x", "capital", "nat_a", 90_000, (10, 16))
        town = _ref("nb_b", "town", "nat_b", 3_000, (2, 10))
        city = _ref("nb_a", "city", "nat_c", 30_000, (18, 10))
        village = _ref("elven_village", "elven_village", None, 120, (11, 11))
        roster = (site, capital, town, city, village)

        context = analyse_site(site, _terrain(), roster)

        self.assertEqual(
            [feature.feature_id for feature in context.neighbours],
            ["cap_x", "nb_a", "nb_b"],
        )
        self.assertEqual(context.capital_bearing, "n")

        capital_context = analyse_site(capital, _terrain(), roster)

        self.assertIsNone(capital_context.capital_bearing)

    @covers_requirement(
        "settlement-terrain-fit::site-context-derives-water-relief-and-neighbour-bearings-from-terrain"
    )
    def test_fords_and_harbours_report_distance_and_bearing(self) -> None:
        terrain = _terrain(
            inland_water=frozenset({(13, 10)}),
            routes={"r": ((13, 20), (13, 0))},
            waterway_cells={"r": frozenset({(13, 10)})},
            fords={"r": ((12, 12), (12, 20))},
            harbours={"harbour_near": (10, 13), "harbour_far": (10, 30)},
        )

        context = analyse_site(
            _ref(), terrain, (_ref(),), radius=8, harbour_radius=5
        )

        self.assertEqual([ford.cell for ford in context.fords], [(12, 12)])
        ford = context.fords[0]
        self.assertEqual(ford.feature_id, "r")
        self.assertAlmostEqual(ford.distance_cells, math.hypot(2, 2))
        self.assertEqual(ford.bearing, "ne")

        self.assertEqual(
            [harbour.feature_id for harbour in context.harbours],
            ["harbour_near"],
        )
        harbour = context.harbours[0]
        self.assertEqual(harbour.cell, (10, 13))
        self.assertAlmostEqual(harbour.distance_cells, 3.0)
        self.assertEqual(harbour.bearing, "n")


class SizeBudgetTests(unittest.TestCase):
    @staticmethod
    def _config(**overrides) -> BudgetConfig:
        values = {
            "reference_population": 10_000,
            "reference_density_per_ha": 150.0,
            "area_exponent": 0.714,
            "min_footprint_cells": 2,
            "tiers": (Tier(0, 6, 2, 0.15),),
            "capital_tier": Tier(0, 28, 4, 0.35),
            "single_cell_nodes": {"village": 4, "hamlet": 2},
        }
        values.update(overrides)
        return BudgetConfig(**values)

    @covers_requirement(
        "settlement-terrain-fit::size-budget-follows-the-population-area-relation-with-a-multi-cell-floor"
    )
    def test_area_scales_by_the_configured_exponent(self) -> None:
        config = self._config(
            reference_density_per_ha=100.0, area_exponent=0.5
        )

        budget = size_budget(_ref(population=40_000), config)

        self.assertEqual(budget.built_area_km2, 2.0)
        self.assertEqual(budget.footprint_cells, 2)
        self.assertEqual(
            budget.envelope_radius_m, round(1000 * math.sqrt(2 / math.pi))
        )

    @covers_requirement(
        "settlement-terrain-fit::size-budget-follows-the-population-area-relation-with-a-multi-cell-floor"
    )
    def test_multi_cell_floor(self) -> None:
        config = self._config(
            reference_population=1_000,
            reference_density_per_ha=100.0,
            area_exponent=1.0,
        )

        small = size_budget(_ref(population=3_000), config)
        large = size_budget(_ref(population=32_000), config)

        self.assertAlmostEqual(small.built_area_km2, 0.3)
        self.assertEqual(small.footprint_cells, 2)
        self.assertAlmostEqual(large.built_area_km2, 3.2)
        self.assertEqual(large.footprint_cells, 4)

    @covers_requirement(
        "settlement-terrain-fit::size-budget-follows-the-population-area-relation-with-a-multi-cell-floor"
    )
    def test_tier_tables(self) -> None:
        config = self._config(
            tiers=(Tier(100, 5, 3, 0.5), Tier(0, 3, 2, 0.1)),
            capital_tier=Tier(0, 9, 4, 0.4),
        )

        self.assertEqual(size_budget(_ref(population=99), config).node_count, 3)
        self.assertEqual(size_budget(_ref(population=100), config).node_count, 5)
        self.assertEqual(size_budget(_ref(population=101), config).node_count, 5)

        capital = size_budget(_ref(kind="capital", population=1), config)

        self.assertEqual(
            (capital.node_count, capital.gate_count, capital.loop_ratio),
            (9, 4, 0.4),
        )

    @covers_requirement(
        "settlement-terrain-fit::size-budget-follows-the-population-area-relation-with-a-multi-cell-floor"
    )
    def test_rejected_inputs(self) -> None:
        config = self._config()
        cases = (
            ("elven_village", 100),
            ("dungeon", 100),
            ("town", 0),
            ("town", None),
            ("village", 0),
            ("hamlet", None),
        )

        for kind, population in cases:
            with self.subTest(kind=kind, population=population):
                with self.assertRaises(BudgetError) as caught:
                    size_budget(
                        _ref("site_z", kind, None, population), config
                    )
                self.assertIn("site_z", str(caught.exception))

    @covers_requirement(
        "settlement-terrain-fit::size-budget-follows-the-population-area-relation-with-a-multi-cell-floor"
    )
    def test_config_validation(self) -> None:
        with self.assertRaises(ValueError):
            self._config(min_footprint_cells=1)

    @covers_requirement(
        "settlement-terrain-fit::size-budget-follows-the-population-area-relation-with-a-multi-cell-floor"
    )
    def test_single_cell_kinds(self) -> None:
        config = self._config(single_cell_nodes={"village": 3, "hamlet": 2})

        village = size_budget(_ref(kind="village", population=5_000), config)
        hamlet = size_budget(_ref(kind="hamlet", population=5_000), config)
        town = size_budget(_ref(kind="town", population=5_000), config)

        self.assertEqual(
            (village.footprint_cells, village.node_count, village.gate_count,
             village.loop_ratio),
            (1, 3, 0, 0.0),
        )
        self.assertEqual(
            (hamlet.footprint_cells, hamlet.node_count, hamlet.gate_count,
             hamlet.loop_ratio),
            (1, 2, 0, 0.0),
        )
        # Both kinds keep the area and the envelope radius of the formula.
        for small in (village, hamlet):
            self.assertEqual(small.built_area_km2, town.built_area_km2)
            self.assertEqual(small.envelope_radius_m, town.envelope_radius_m)

        # A town at the village's population still gets the two-cell floor and
        # its own tier's targets.
        self.assertEqual(town.footprint_cells, 2)
        self.assertEqual(
            (town.node_count, town.gate_count, town.loop_ratio), (6, 2, 0.15)
        )

    @covers_requirement(
        "settlement-terrain-fit::size-budget-follows-the-population-area-relation-with-a-multi-cell-floor"
    )
    def test_single_cell_table_validation(self) -> None:
        for table in (
            {"village": 4},
            {"village": 4, "hamlet": 2, "town": 3},
            {"village": 4, "hamlet": 1},
            {"village": 0, "hamlet": 2},
        ):
            with self.subTest(table=table):
                with self.assertRaises(ValueError):
                    self._config(single_cell_nodes=table)


class WaterAndCrossingLintTests(unittest.TestCase):
    @covers_requirement(
        "settlement-terrain-fit::terrain-fit-lint-flags-dry-water-edge-roles-and-unbridged-crossings"
    )
    def test_water_edge_distance(self) -> None:
        nodes = {
            "inn": _node(*ANCHOR_LOCAL, anchor=True),
            "quay": _node(3200, 500),
            "riverbank_road": _node(2000, 1500),
        }

        findings = lint_settlement(
            _document(nodes), LOCATION_CELL, _river_terrain()
        )

        dry = {
            finding.object_id
            for finding in findings
            if finding.code == "fit_water_role_dry"
        }
        self.assertEqual(dry, {"riverbank_road"})

    @covers_requirement(
        "settlement-terrain-fit::terrain-fit-lint-flags-dry-water-edge-roles-and-unbridged-crossings"
    )
    def test_crossing_words(self) -> None:
        nodes = {
            "inn": _node(*ANCHOR_LOCAL, anchor=True),
            "plain_a": _node(3000, 500),
            "plain_b": _node(5000, 500),
            "bridge": _node(3000, 1500),
            "bank_far": _node(5000, 1500),
            "approach_a": _node(3000, -4500),
            "approach_b": _node(5000, -4500),
        }
        roads = [
            _road("plain_a", "plain_b", "e"),
            _road("bridge", "bank_far", "e"),
            _road("approach_a", "approach_b", "e"),
        ]

        findings = lint_settlement(
            _document(nodes, roads), LOCATION_CELL, _river_terrain()
        )

        crossings = {
            finding.object_id
            for finding in findings
            if finding.code == "fit_unbridged_crossing"
        }
        self.assertEqual(crossings, {"plain_a>plain_b"})

    @covers_requirement(
        "settlement-terrain-fit::terrain-fit-lint-flags-dry-water-edge-roles-and-unbridged-crossings"
    )
    def test_whole_word_tokens(self) -> None:
        self.assertEqual(words("quayside") & WATER_EDGE_WORDS, frozenset())
        self.assertNotIn("quay", words("quayside"))
        self.assertIn("ford", words("old_ford_lane"))
        self.assertTrue(words("old_ford_lane") & CROSSING_WORDS)


class FootprintAndGateLintTests(unittest.TestCase):
    @covers_requirement(
        "settlement-terrain-fit::terrain-fit-lint-checks-footprint-water-gate-side-and-gate-approach"
    )
    def test_multi_cell_containment_and_water(self) -> None:
        nodes = {
            "inn": _node(*ANCHOR_LOCAL, anchor=True),
            "market": _node(3000, 500),
            "outside_inn": _node(1000, 500),
            "water_node": _node(4000, 500),
        }
        document = _document(
            nodes,
            shape=["##"],
            gates=[{"return_direction": "e", "destination_node": "outside_inn"}],
        )

        findings = lint_settlement(document, LOCATION_CELL, _river_terrain())

        outside = {
            finding.object_id
            for finding in findings
            if finding.code == "fit_node_outside_footprint"
        }
        self.assertIn("outside_inn", outside)
        self.assertNotIn("market", outside)
        in_water = {
            finding.object_id
            for finding in findings
            if finding.code == "fit_node_in_water"
        }
        self.assertEqual(in_water, {"water_node"})

    @covers_requirement(
        "settlement-terrain-fit::terrain-fit-lint-checks-footprint-water-gate-side-and-gate-approach"
    )
    def test_gate_side_and_approach(self) -> None:
        nodes = {
            "inn": _node(*ANCHOR_LOCAL, anchor=True),
            "west_inn": _node(0, 500),
            "north_yard": _node(2500, 0),
        }
        document = _document(
            nodes,
            shape=["##"],
            gates=[
                {"return_direction": "w", "destination_node": "west_inn"},
                {"return_direction": "n", "destination_node": "north_yard"},
            ],
        )
        terrain = _terrain(impassable=frozenset({(10, 9)}))

        findings = lint_settlement(document, LOCATION_CELL, terrain)

        warnings = {
            (finding.code, finding.object_id)
            for finding in findings
            if finding.severity == "warning"
        }
        errors = {
            (finding.code, finding.object_id)
            for finding in findings
            if finding.severity == "error"
        }
        self.assertIn(("fit_gate_side", "gate:w"), warnings)
        self.assertIn(("fit_gate_approach_blocked", "gate:n"), errors)
        self.assertNotIn(("fit_gate_side", "gate:n"), warnings)
        self.assertNotIn(("fit_gate_approach_blocked", "gate:w"), errors)

    @covers_requirement(
        "settlement-terrain-fit::terrain-fit-lint-checks-footprint-water-gate-side-and-gate-approach"
    )
    def test_concealed_point_entry(self) -> None:
        nodes = {
            "inn": _node(*ANCHOR_LOCAL, anchor=True),
            "market": _node(3000, 500),
            "outside_inn": _node(1000, 500),
            "water_node": _node(4000, 500),
        }
        document = _document(
            nodes,
            shape=["#"],
            gates=[{"return_direction": "e", "destination_node": "outside_inn"}],
        )

        findings = lint_settlement(document, LOCATION_CELL, _river_terrain())

        codes = {finding.code for finding in findings}
        self.assertNotIn("fit_node_outside_footprint", codes)
        self.assertNotIn("fit_gate_side", codes)
        self.assertNotIn("fit_gate_approach_blocked", codes)
        self.assertIn(
            ("fit_node_in_water", "water_node"),
            {(finding.code, finding.object_id) for finding in findings},
        )

    @covers_requirement(
        "settlement-terrain-fit::terrain-fit-lint-checks-footprint-water-gate-side-and-gate-approach"
    )
    def test_one_cell_physical_footprint(self) -> None:
        nodes = {
            "inn": _node(*ANCHOR_LOCAL, anchor=True),
            "outside_inn": _node(1000, 500),
        }
        gates = [{"return_direction": "e", "destination_node": "outside_inn"}]
        # The approach cell of the one-cell footprint is the adjacent land cell
        # the outside node stands on; making it impassable blocks the gate.
        terrain = _terrain(impassable=frozenset({(9, 10)}))

        flagged = lint_settlement(
            _document(
                nodes,
                shape=["#"],
                gates=gates,
                single_cell_footprint=True,
            ),
            LOCATION_CELL,
            terrain,
        )
        findings = {(finding.code, finding.object_id) for finding in flagged}
        self.assertIn(("fit_node_outside_footprint", "outside_inn"), findings)
        self.assertIn(("fit_gate_approach_blocked", "gate:e"), findings)

        unflagged = lint_settlement(
            _document(nodes, shape=["#"], gates=gates),
            LOCATION_CELL,
            terrain,
        )
        codes = {finding.code for finding in unflagged}
        self.assertNotIn("fit_node_outside_footprint", codes)
        self.assertNotIn("fit_gate_approach_blocked", codes)


class RoadContactTests(unittest.TestCase):
    """The road cells that touch a location cell, from the committed artifact."""

    def setUp(self) -> None:
        self._workspace_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._workspace_dir.cleanup)
        self.root = synthetic.write_workspace(Path(self._workspace_dir.name))

    def _write_artifact(self, text: str) -> None:
        path = self.root / "world" / "maps" / "data" / "road_network.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_contacts_follow_each_road_and_union_across_roads(self) -> None:
        self._write_artifact(
            _road_network_text(
                [
                    (
                        "synthetic_road_a",
                        "synthetic_road_b",
                        [(10, 10), (11, 10), (12, 10)],
                    ),
                    (
                        "synthetic_road_b",
                        "synthetic_road_c",
                        [(11, 10), (11, 11), (11, 12)],
                    ),
                ]
            )
        )

        view = load_workspace(self.root)

        # An inner cell of one road has the cell before and the cell after it.
        self.assertEqual(view.road_contacts((11, 11)), ((11, 10), (11, 12)))
        # A road's last cell has exactly one contact.
        self.assertEqual(view.road_contacts((12, 10)), ((11, 10),))
        # A cell on two roads has the union, sorted and without duplicates.
        self.assertEqual(
            view.road_contacts((11, 10)), ((10, 10), (11, 11), (12, 10))
        )
        # A cell on no road has none.
        self.assertEqual(view.road_contacts((30, 30)), ())

    def test_absent_artifact_gives_no_contact(self) -> None:
        self.assertFalse(
            (self.root / "world" / "maps" / "data" / "road_network.json").exists()
        )

        view = load_workspace(self.root)

        self.assertEqual(view.road_contacts((10, 10)), ())
        self.assertEqual(view.road_contacts((0, 0)), ())

    def test_corrupt_artifact_raises(self) -> None:
        self._write_artifact("{ not a road document")

        view = load_workspace(self.root)

        with self.assertRaises(WorkspaceError) as caught:
            view.road_contacts((10, 10))
        self.assertIn("road_network.json", str(caught.exception))


class EntranceLintTests(unittest.TestCase):
    """A one-cell village or hamlet's gates checked against its road contacts."""

    def _codes(self, findings, code: str = "fit_entrance_mismatch"):
        return [finding for finding in findings if finding.code == code]

    @covers_requirement(
        "settlement-terrain-fit::terrain-fit-lint-checks-single-cell-entrances-against-road-contacts"
    )
    def test_matching_and_mismatching_gates(self) -> None:
        contacts = ((9, 10), (11, 10))

        matched = lint_settlement(
            _entrance_document(("w", "e")),
            LOCATION_CELL,
            _terrain(),
            road_contacts=contacts,
        )
        self.assertEqual(self._codes(matched), [])

        # Gate w alone approaches (11, 10): the road contact (9, 10) is unserved.
        missing = self._codes(
            lint_settlement(
                _entrance_document(("w",)),
                LOCATION_CELL,
                _terrain(),
                road_contacts=contacts,
            )
        )
        self.assertEqual(len(missing), 1)
        self.assertEqual(
            (missing[0].severity, missing[0].object_id, missing[0].map_id),
            ("error", "gates", "fit_case"),
        )
        self.assertIn("(9, 10)", missing[0].message)

        # The n gate approaches (10, 9), which no road touches.
        extra = self._codes(
            lint_settlement(
                _entrance_document(("w", "e", "n")),
                LOCATION_CELL,
                _terrain(),
                road_contacts=contacts,
            )
        )
        self.assertEqual(len(extra), 1)
        self.assertIn("(10, 9)", extra[0].message)

    @covers_requirement(
        "settlement-terrain-fit::terrain-fit-lint-checks-single-cell-entrances-against-road-contacts"
    )
    def test_missing_and_extra_report_together(self) -> None:
        # Gate w serves (11, 10) and gate n walks onto (10, 9), so the road
        # contact (9, 10) is unserved and (10, 9) has no road at all.
        findings = self._codes(
            lint_settlement(
                _entrance_document(("w", "n")),
                LOCATION_CELL,
                _terrain(),
                road_contacts=((9, 10), (11, 10)),
            )
        )

        self.assertEqual(len(findings), 1)
        self.assertIn("road cells with no gate (9, 10)", findings[0].message)
        self.assertIn("gate cells with no road (10, 9)", findings[0].message)

    @covers_requirement(
        "settlement-terrain-fit::terrain-fit-lint-checks-single-cell-entrances-against-road-contacts"
    )
    def test_no_road_contact(self) -> None:
        one_gate = self._codes(
            lint_settlement(
                _entrance_document(("w",)),
                LOCATION_CELL,
                _terrain(),
                road_contacts=(),
            )
        )
        self.assertEqual(one_gate, [])

        two_gates = self._codes(
            lint_settlement(
                _entrance_document(("w", "e")),
                LOCATION_CELL,
                _terrain(),
                road_contacts=(),
            )
        )
        self.assertEqual(len(two_gates), 1)
        self.assertEqual(two_gates[0].severity, "error")
        self.assertIn("no road touches cell 10, 10", two_gates[0].message)

    @covers_requirement(
        "settlement-terrain-fit::terrain-fit-lint-checks-single-cell-entrances-against-road-contacts"
    )
    def test_national_settlements_are_unaffected(self) -> None:
        # A multi-cell footprint, and a concealed one-cell entry, are never
        # compared against roads even when the caller supplies contacts.
        footprint = lint_settlement(
            _entrance_document(("w", "e"), shape=("##",), single_cell_footprint=False),
            LOCATION_CELL,
            _terrain(),
            road_contacts=((30, 30),),
        )
        self.assertEqual(self._codes(footprint), [])

        point = lint_settlement(
            _entrance_document(("w", "e"), single_cell_footprint=False),
            LOCATION_CELL,
            _terrain(),
            road_contacts=((30, 30),),
        )
        self.assertEqual(self._codes(point), [])

        # Without contacts the check does not run at all.
        unchecked = self._codes(
            lint_settlement(
                _entrance_document(("w", "e")), LOCATION_CELL, _terrain()
            )
        )
        self.assertEqual(unchecked, [])


class DirectionDriftLintTests(unittest.TestCase):
    @covers_requirement(
        "settlement-terrain-fit::road-direction-drift-is-a-warning"
    )
    def test_drifted_and_adjacent_directions(self) -> None:
        nodes = {
            "inn": _node(*ANCHOR_LOCAL, anchor=True),
            "src_e": _node(1000, 1000),
            "dst_e": _node(2000, 1000),
            "src_ne": _node(1000, 1500),
            "dst_ne": _node(2000, 1500),
            "src_n": _node(1000, 2000),
            "dst_n": _node(2000, 2000),
        }
        roads = [
            _road("src_e", "dst_e", "e"),
            _road("src_ne", "dst_ne", "ne"),
            _road("src_n", "dst_n", "n"),
        ]
        document = _document(nodes, roads)
        before = {key: value for key, value in document.data.items()}

        findings = lint_settlement(document, LOCATION_CELL, _terrain())

        drift = [
            finding
            for finding in findings
            if finding.code == "fit_direction_drift"
        ]
        self.assertEqual(
            [(finding.object_id, finding.severity) for finding in drift],
            [("src_n>dst_n", "warning")],
        )
        self.assertEqual(document.data, before)
        self.assertEqual(
            [road.direction for road in document.roads], ["e", "ne", "n"]
        )


class CommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self._workspace_dir = tempfile.TemporaryDirectory()
        self._lore_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._workspace_dir.name)
        synthetic.write_workspace(self.root)
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

    def _write_location_kind(self, kind: str) -> None:
        locations = synthetic.locations_data()
        locations["locations"][synthetic.LOCATION_ID]["kind"] = kind
        (
            self.root / "content" / "maps" / "locations.yaml"
        ).write_text(synthetic.yaml_text(locations), encoding="utf-8")

    def _write_settlement(self, data: dict) -> None:
        path = (
            self.root
            / "content"
            / "maps"
            / "settlements"
            / f"{synthetic.SETTLEMENT_ID}.yaml"
        )
        path.write_text(synthetic.yaml_text(data), encoding="utf-8")

    def _write_road_artifact(self, text: str) -> None:
        path = self.root / "world" / "maps" / "data" / "road_network.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    @covers_requirement(
        "settlement-terrain-fit::the-fit-commands-are-read-only-and-report-by-exit-status"
    )
    def test_clean_workspace_lints_with_no_finding(self) -> None:
        result = self._run("lint")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("fit: 0 errors, 0 warnings", result.stdout)
        self.assertEqual(synthetic.tree_digest(self.root), self.digest)

    @covers_requirement(
        "settlement-terrain-fit::the-fit-commands-are-read-only-and-report-by-exit-status"
    )
    def test_dry_water_edge_node_fails_the_lint(self) -> None:
        data = synthetic.settlement_data()
        data["nodes"]["quay"] = _node(300, 0)
        data["roads"].append(_road("gate", "quay", "e"))
        data["roads"].append(_road("quay", "gate", "w"))
        path = self.root / "content" / "maps" / "settlements" / "synthetic_town.yaml"
        path.write_text(synthetic.yaml_text(data), encoding="utf-8")
        digest = synthetic.tree_digest(self.root)

        result = self._run("lint")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(
            "fit_water_role_dry synthetic_town quay", result.stdout
        )
        self.assertEqual(synthetic.tree_digest(self.root), digest)

    @covers_requirement(
        "settlement-terrain-fit::the-fit-commands-are-read-only-and-report-by-exit-status"
    )
    def test_duplicate_key_fails_to_load(self) -> None:
        path = self.root / "content" / "maps" / "settlements" / "synthetic_town.yaml"
        path.write_text(
            path.read_text(encoding="utf-8") + "\nnodes: {}\n", encoding="utf-8"
        )
        digest = synthetic.tree_digest(self.root)

        result = self._run("lint")

        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("synthetic_town.yaml", result.stderr)
        self.assertEqual(synthetic.tree_digest(self.root), digest)

    @covers_requirement(
        "settlement-terrain-fit::the-fit-commands-are-read-only-and-report-by-exit-status"
    )
    def test_warning_only_still_exits_zero(self) -> None:
        data = synthetic.settlement_data()
        data["nodes"]["walk_a"] = _node(500, 0)
        data["nodes"]["walk_b"] = _node(800, 0)
        data["roads"].append(_road("walk_a", "walk_b", "n"))
        path = self.root / "content" / "maps" / "settlements" / "synthetic_town.yaml"
        path.write_text(synthetic.yaml_text(data), encoding="utf-8")
        digest = synthetic.tree_digest(self.root)

        result = self._run("lint")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "fit_direction_drift synthetic_town walk_a>walk_b", result.stdout
        )
        self.assertIn("fit: 0 errors, 1 warnings", result.stdout)
        self.assertEqual(synthetic.tree_digest(self.root), digest)

    @covers_requirement(
        "settlement-terrain-fit::the-fit-commands-are-read-only-and-report-by-exit-status"
    )
    def test_bent_road_crossing_outside_the_node_window_is_reported(self) -> None:
        data = synthetic.settlement_data()
        data["nodes"]["walk_b"] = _node(300, 0)
        data["roads"].append(
            {
                "source": "gate",
                "destination": "walk_b",
                "direction": "n",
                "bends": [{"x_m": 0, "y_m": 15000}],
            }
        )
        path = self.root / "content" / "maps" / "settlements" / "synthetic_town.yaml"
        path.write_text(synthetic.yaml_text(data), encoding="utf-8")
        digest = synthetic.tree_digest(self.root)

        result = self._run("lint")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(
            "fit_unbridged_crossing synthetic_town gate>walk_b", result.stdout
        )
        self.assertEqual(synthetic.tree_digest(self.root), digest)

    @covers_requirement(
        "settlement-terrain-fit::the-fit-commands-are-read-only-and-report-by-exit-status"
    )
    def test_lore_override_drives_the_site_and_budget_commands(self) -> None:
        lore = Path(self._lore_dir.name) / "lore.json"
        lore.write_text(
            json.dumps(
                {
                    "synthetic_place": {"nation": None, "population": 20000},
                }
            ),
            encoding="utf-8",
        )
        lore_before = lore.read_bytes()

        budget = self._run(
            "budget", "synthetic_place", "--lore", str(lore)
        )
        self.assertEqual(budget.returncode, 0, budget.stderr)
        self.assertIn("footprint_cells", json.loads(budget.stdout))

        site = self._run("site", "synthetic_place", "--lore", str(lore))
        self.assertEqual(site.returncode, 0, site.stderr)
        payload = json.loads(site.stdout)
        self.assertEqual(
            [contact["name"] for contact in payload["rivers"]],
            ["synthetic_river"],
        )

        unknown = self._run("site", "no_such_place", "--lore", str(lore))
        self.assertEqual(unknown.returncode, 2)

        self.assertEqual(synthetic.tree_digest(self.root), self.digest)
        self.assertEqual(lore.read_bytes(), lore_before)

    def test_budget_command_accepts_a_village(self) -> None:
        self._write_location_kind("village")
        lore = Path(self._lore_dir.name) / "lore.json"
        lore.write_text(
            json.dumps(
                {"synthetic_place": {"nation": None, "population": 120}}
            ),
            encoding="utf-8",
        )
        digest = synthetic.tree_digest(self.root)

        result = self._run(
            "budget", "synthetic_place", "--lore", str(lore)
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            (
                payload["footprint_cells"],
                payload["node_count"],
                payload["gate_count"],
                payload["loop_ratio"],
            ),
            (1, 4, 0, 0.0),
        )
        self.assertEqual(synthetic.tree_digest(self.root), digest)

    @covers_requirement(
        "settlement-terrain-fit::terrain-fit-lint-checks-single-cell-entrances-against-road-contacts"
    )
    def test_lint_matches_a_village_gate_to_its_road_contact(self) -> None:
        self._write_location_kind("village")
        data = synthetic.settlement_data()
        data["wilderness_entry"]["single_cell_footprint"] = True
        data["wilderness_entry"]["gates"] = [
            {"return_direction": "w", "destination_node": "gate"}
        ]
        self._write_settlement(data)
        # The road ends on the village cell from the east, so the single
        # contact of cell (5, 5) is (6, 5) and the west gate walks onto it.
        self._write_road_artifact(
            _road_network_text(
                [
                    (
                        "synthetic_road_a",
                        "synthetic_road_b",
                        [(5, 5), (6, 5), (7, 5)],
                    )
                ]
            )
        )
        digest = synthetic.tree_digest(self.root)

        matched = self._run("lint")

        self.assertEqual(matched.returncode, 0, matched.stdout + matched.stderr)
        self.assertNotIn("fit_entrance_mismatch", matched.stdout)
        self.assertEqual(synthetic.tree_digest(self.root), digest)

        # The north gate walks onto (5, 4) instead, and the road contact is
        # left without a gate.
        data["wilderness_entry"]["gates"] = [
            {"return_direction": "n", "destination_node": "gate"}
        ]
        self._write_settlement(data)
        digest = synthetic.tree_digest(self.root)

        mismatched = self._run("lint")

        self.assertEqual(mismatched.returncode, 1, mismatched.stderr)
        self.assertIn(
            "fit_entrance_mismatch synthetic_town gates", mismatched.stdout
        )
        self.assertIn("(6, 5)", mismatched.stdout)
        self.assertEqual(synthetic.tree_digest(self.root), digest)

    @covers_requirement(
        "settlement-terrain-fit::terrain-fit-lint-checks-single-cell-entrances-against-road-contacts"
    )
    def test_national_kind_is_not_checked_against_roads(self) -> None:
        # The map is a one-cell physical footprint with two gates and the
        # artifact never touches its cell: passing empty contacts would report
        # the entrance mismatch, so exit 0 proves the command passed None.
        data = synthetic.settlement_data()
        data["wilderness_entry"]["single_cell_footprint"] = True
        data["wilderness_entry"]["gates"] = [
            {"return_direction": "n", "destination_node": "gate"},
            {"return_direction": "e", "destination_node": "yard"},
        ]
        self._write_settlement(data)
        self._write_road_artifact(
            _road_network_text(
                [
                    (
                        "synthetic_road_a",
                        "synthetic_road_b",
                        [(20, 20), (21, 20), (21, 21)],
                    )
                ]
            )
        )
        digest = synthetic.tree_digest(self.root)

        result = self._run("lint")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("fit_entrance_mismatch", result.stdout)
        self.assertEqual(synthetic.tree_digest(self.root), digest)


if __name__ == "__main__":
    unittest.main()
