"""Data-contract test: wilderness entry data contract
Registry v2 self-consistency and validation checks (wilderness-anchor-footprint)."""

import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from elosern_map_core.references import settlement_node_ref
from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.wilderness_entry import (
    WILDERNESS_ENTRY_REGISTRY,
    WildernessEntryPoint,
    WildernessGate,
)
from world.tests.geography_fixture import publish_shipped_geography


def setUpModule():
    # The provider frame bounds and the gate approach walks read the published
    # geography; the registry itself is the published settlement world.
    publish_shipped_geography()


def _capital():
    """The shipped capital entry, read after the settlement world is published."""
    return WILDERNESS_ENTRY_REGISTRY["capital_altoria"]


def _point_entry(anchor_key="capital_altoria", anchor=(500, 500), gates=None):
    """A throwaway point-shape (cave) entry for helper/validation tests."""
    if gates is None:
        gates = (WildernessGate("n", _capital().gate_for("n").destination),)
    return WildernessEntryPoint(anchor_key, ("#",), anchor, gates)


class WildernessEntryRegistryShapeTests(unittest.TestCase):
    @covers_requirement(
        "village-ciaran-map::the-village-has-a-wilderness-footprint-disjoint-from-every-other-settlement"
    )
    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-links-a-grid-placed-anchor-to-an-authored-wilderness-footprint-and-gates"
    )
    def test_registry_has_two_v2_entries_keyed_by_settlement(self):
        self.assertEqual(
            list(WILDERNESS_ENTRY_REGISTRY),
            ["capital_altoria", "village_ciaran"],
        )
        self.assertEqual(_capital().anchor_key, "capital_altoria")
        self.assertEqual(_capital().hash_cell_count, 40)
        self.assertEqual(_capital().origin_xy, (857, 1076))
        self.assertEqual(
            [
                (gate.return_direction, gate.z_map_key, gate.destination.object_id)
                for gate in _capital().gates
            ],
            [
                ("n", "capital_altoria", "south_gate"),
                ("w", "capital_altoria", "east_gate"),
            ],
        )
        village = WILDERNESS_ENTRY_REGISTRY["village_ciaran"]
        self.assertEqual(village.anchor_key, "village_ciaran")
        self.assertLess(village.hash_cell_count, _capital().hash_cell_count)
        self.assertTrue(village.is_point_shape)
        self.assertEqual(
            [
                (gate.return_direction, gate.z_map_key, gate.destination.object_id)
                for gate in village.gates
            ],
            [("n", "village_ciaran", "hidden_path")],
        )
        # A point entrance contributes no footprint at all, so it can never
        # collide with the capital's mask or another village-wide obstacle.
        self.assertEqual(village.footprint_cells, frozenset())

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-links-a-grid-placed-anchor-to-an-authored-wilderness-footprint-and-gates"
    )
    def test_village_derived_geometry_matches_the_authored_mask(self):
        village = WILDERNESS_ENTRY_REGISTRY["village_ciaran"]
        self.assertEqual(village.origin_xy, (1366, 554))
        self.assertEqual(village.shape, ("#",))
        self.assertEqual(village.anchor_cell, (1366, 554))
        # Point semantics: the approach cell IS the anchor cell, and only the
        # authored direction is the gateway.
        self.assertEqual(village.approach_cell(village.gate_for("n")), (1366, 554))
        gate = village.gate_for("n")
        # The gate returns to the village's entrance node on its own map.
        self.assertEqual(
            gate.destination,
            settlement_node_ref("village_ciaran", "hidden_path"),
        )

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-links-a-grid-placed-anchor-to-an-authored-wilderness-footprint-and-gates"
    )
    def test_derived_geometry_matches_the_authored_mask(self):
        # The authored mask rows are contract: 40 km² inside a 7x9 km box, the
        # plaza cell as derived anchor, and one exterior approach per gate ray.
        self.assertEqual(
            _capital().shape,
            (
                "#.....#",
                "##...##",
                ".#####.",
                "#######",
                "#######",
                "####..#",
                "#..#.##",
                "####...",
                "..##...",
            ),
        )
        self.assertEqual(_capital().hash_cell_count, 40)
        self.assertEqual(_capital().anchor_cell, (860, 1080))
        self.assertIn(_capital().anchor_cell, _capital().footprint_cells)
        self.assertEqual(
            _capital().footprint_cells,
            frozenset(
                (_capital().origin_xy[0] + col, _capital().origin_xy[1] + row)
                for row, line in enumerate(_capital().shape)
                for col, char in enumerate(line)
                if char == "#"
            ),
        )
        self.assertEqual(_capital().approach_cell(_capital().gate_for("n")), (860, 1077))
        self.assertEqual(_capital().approach_cell(_capital().gate_for("w")), (864, 1080))
        self.assertFalse(_capital().is_point_shape)
        # 4-connected: every mask cell is reachable from the anchor cell.
        seen = {_capital().anchor_cell}
        frontier = [_capital().anchor_cell]
        while frontier:
            cx, cy = frontier.pop()
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                neighbour = (cx + dx, cy + dy)
                if neighbour in _capital().footprint_cells and neighbour not in seen:
                    seen.add(neighbour)
                    frontier.append(neighbour)
        self.assertEqual(seen, set(_capital().footprint_cells))

    def test_point_shape_entry_expresses_cave_semantics(self):
        point = _point_entry()
        self.assertTrue(point.is_point_shape)
        self.assertEqual(point.footprint_cells, frozenset())
        self.assertEqual(point.anchor_cell, (500, 500))
        # approach_cell IS the anchor cell for a point-shape gate.
        self.assertEqual(point.approach_cell(point.gates[0]), point.anchor_cell)

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-links-a-grid-placed-anchor-to-an-authored-wilderness-footprint-and-gates"
    )
    def test_every_entrys_anchor_key_exists_in_anchor_placement_registry(self):
        for entry in WILDERNESS_ENTRY_REGISTRY.values():
            self.assertIn(entry.anchor_key, ANCHOR_PLACEMENT_REGISTRY)

    def test_gate_lookup_by_return_direction(self):
        self.assertEqual(_capital().gate_for("n").destination.object_id, "south_gate")
        self.assertEqual(_capital().gate_for("w").destination.object_id, "east_gate")
        # The capital's second gate is the 東門 since the replan; the old
        # 北門 directions are authored nowhere.
        self.assertIsNone(_capital().gate_for("s"))
        self.assertIsNone(_capital().gate_for("e"))

    @covers_requirement(
        "village-ciaran-map::the-village-has-a-wilderness-footprint-disjoint-from-every-other-settlement"
    )
    def test_gate_identity_is_globally_unique(self):
        keys = set()
        for entry in WILDERNESS_ENTRY_REGISTRY.values():
            for gate in entry.gates:
                pair = (entry.approach_cell(gate), gate.return_direction)
                self.assertNotIn(pair, keys)
                keys.add(pair)


class WildernessEntryValidationTests(unittest.TestCase):
    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-authored-data-is-validated-before-persistence"
    )
    def test_shipped_registry_validates(self):
        from world.maps import runtime

        world = runtime.current()
        self.assertIn("capital_altoria", world.settlements.wilderness_entries)
        self.assertIn("village_ciaran", world.settlements.wilderness_entries)
        self.assertTrue(WILDERNESS_ENTRY_REGISTRY)

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-authored-data-is-validated-before-persistence"
    )
    def test_village_gate_validates_against_the_shared_map_assembly(self):
        from world.maps import runtime

        world = runtime.current()
        village = world.settlements.wilderness_entries["village_ciaran"]
        self.assertEqual(village.anchor_key, "village_ciaran")
        self.assertEqual(len(village.gates), 1)
        self.assertEqual(village.gates[0].z_map_key, "village_ciaran")

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-authored-data-is-validated-before-persistence"
    )
    def test_malformed_entries_are_each_rejected(self):
        from world.maps import runtime
        from world.maps.map_data import SettlementError, build_settlements
        from elosern_map_core.codec import document_from_data

        world = runtime.current()
        shipped = dict(world.settlements.settlements)
        locations = world.geography.locations

        # Disconnected footprint candidate
        malformed_data = dict(shipped["capital_altoria"].data)
        malformed_data["wilderness_entry"] = {
            "shape": ["#.#"],
            "offset": {"dx": 58, "dy": 98},
            "gates": [{"return_direction": "n", "destination_node": "south_gate"}],
        }
        candidate = document_from_data(shipped["capital_altoria"].relative_path, malformed_data)
        with self.assertRaises(SettlementError) as caught:
            build_settlements(
                {**shipped, "capital_altoria": candidate},
                locations,
                frame_cells=world.geography.frame_cells,
            )
        self.assertIn("not 4-connected", str(caught.exception))

        # Point entry with multiple gates
        point_data = dict(shipped["village_ciaran"].data)
        point_data["wilderness_entry"] = {
            "shape": ["#"],
            "offset": {"dx": 35, "dy": 270},
            "gates": [
                {"return_direction": "n", "destination_node": "hidden_path"},
                {"return_direction": "s", "destination_node": "village_plaza"},
            ],
        }
        candidate_point = document_from_data(shipped["village_ciaran"].relative_path, point_data)
        with self.assertRaises(SettlementError) as caught:
            build_settlements(
                {**shipped, "village_ciaran": candidate_point},
                locations,
                frame_cells=world.geography.frame_cells,
            )
        self.assertIn("point-shape entry must have exactly one gate", str(caught.exception))

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-authored-data-is-validated-before-persistence"
    )
    def test_sync_all_refuses_to_mirror_malformed_registry(self):
        from world.lore.sync import sync_all
        from world.maps import runtime
        from world.maps.runtime import MapWorldError
        from elosern_map_core.sources import make_source_document

        saved = runtime._BUNDLE
        runtime._uninstall()
        try:
            sources = list(runtime._read_sources(None))
            malformed_sources = []
            for src in sources:
                if src.relative_path.endswith("capital_altoria.yaml"):
                    text = src.text.replace('    - "#######"\n    - "#######"', '    - "......."\n    - "......."')
                    malformed_sources.append(make_source_document(src.relative_path, text))
                else:
                    malformed_sources.append(src)
            with patch("world.lore.sync.sync_one") as mock_sync_one:
                with patch("world.maps.runtime._read_sources", return_value=tuple(malformed_sources)):
                    with self.assertRaises(MapWorldError) as caught:
                        sync_all()
                    self.assertIn("not 4-connected", str(caught.exception))
                mock_sync_one.assert_not_called()
        finally:
            if saved is not None:
                runtime._install(saved)

class WildernessEntryBoundsTests(unittest.TestCase):
    def test_entry_cells_are_within_provider_bounds(self):
        from world.maps.wilderness_provider import WILDERNESS_MAX_X, WILDERNESS_MAX_Y

        for cell in _capital().footprint_cells | {
            _capital().approach_cell(gate) for gate in _capital().gates
        }:
            x, y = cell
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x, WILDERNESS_MAX_X)
            self.assertLessEqual(y, WILDERNESS_MAX_Y)

    def test_every_entry_has_gate_approach_cells_off_the_south_edge(self):
        # A gate approach cell at y == 0 would have its return exit locked
        # invalid by the contrib's own edge handling; validation's provider-
        # rectangle rule guards this, asserted here for every shipped gate.
        for entry in WILDERNESS_ENTRY_REGISTRY.values():
            for gate in entry.gates:
                self.assertGreater(entry.approach_cell(gate)[1], 0)

    def test_core_and_runtime_gate_approach_calculations_agree(self):
        from elosern_map_core.authoring import (
            gate_approach_cell,
            _DIRECTION_DELTAS as CORE_DELTAS,
            _OPPOSITE_DIRECTION as CORE_OPPOSITE,
        )
        from world.lore.wilderness_entry import DIRECTION_DELTAS, OPPOSITE_DIRECTION

        self.assertEqual(CORE_DELTAS, DIRECTION_DELTAS)
        self.assertEqual(CORE_OPPOSITE, OPPOSITE_DIRECTION)

        for anchor_key, entry in WILDERNESS_ENTRY_REGISTRY.items():
            for gate in entry.gates:
                game_approach = entry.approach_cell(gate)
                core_approach = gate_approach_cell(entry, gate.return_direction)
                self.assertIsNotNone(game_approach)
                self.assertEqual(
                    core_approach,
                    game_approach,
                    f"Mismatch on {anchor_key} gate {gate.return_direction}",
                )
