import unittest
from unittest.mock import patch
from world.maps.bootstrap import sync_grid, sync_wilderness

from ._support import (
    EAST_APPROACH,
    EAST_GATE_XYZ,
    SOUTH_APPROACH,
    SOUTH_GATE_XYZ,
    _T_MAP_KEY,
    _NORTH_FACE,
    _T_PLAZA_XYZ,
    _city_gate_row_for,
    _t_anchor_display,
    _t_region_display_for,
)


class LocalMapGatewayResolutionTests(unittest.TestCase):
    """Pure unit tests for the gateway predicate and far-side namer (wave 1).

    Reads the real shipped wilderness-entry registry (one entry, the sample
    city, two gates) directly -- no DB needed for the pure lookup
    functions.
    """

    def test_registered_gateways_yields_the_shipped_capital_gates(self):
        from web.webclient.presentation.local_map import _registered_gateways

        triples = set(_registered_gateways())
        self.assertIn(
            (SOUTH_APPROACH, (SOUTH_GATE_XYZ[:2], _T_MAP_KEY), _T_MAP_KEY), triples
        )
        self.assertIn(
            (EAST_APPROACH, (EAST_GATE_XYZ[:2], _T_MAP_KEY), _T_MAP_KEY), triples
        )

    def test_registered_gateways_yields_a_point_shape_entrys_own_anchor_cell(self):
        from web.webclient.presentation.local_map import _registered_gateways
        from world.lore.wilderness_entry import WildernessEntryPoint, WildernessGate

        gate_row = _city_gate_row_for(_NORTH_FACE)
        cave = WildernessEntryPoint(
            anchor_key="t_dungeon_point",
            shape=("#",),
            origin_xy=(10, 10),
            gates=(WildernessGate("n", gate_row.gate),),
        )
        with patch(
            "world.lore.wilderness_entry.WILDERNESS_ENTRY_REGISTRY",
            {"t_dungeon_point": cave},
        ):
            gateways = _registered_gateways()
        self.assertEqual(
            gateways,
            [((10, 10), (SOUTH_GATE_XYZ[:2], SOUTH_GATE_XYZ[2]), "t_dungeon_point")],
        )

    def test_wilderness_gateway_at_matches_only_registered_approach_cells(self):
        from web.webclient.presentation.local_map import _wilderness_gateway_at

        self.assertIsNotNone(_wilderness_gateway_at(*EAST_APPROACH))
        self.assertIsNotNone(_wilderness_gateway_at(*SOUTH_APPROACH))
        # Immediately north of the east approach is outside every footprint:
        # not itself an approach cell.
        self.assertIsNone(_wilderness_gateway_at(EAST_APPROACH[0], EAST_APPROACH[1] + 1))

    def test_grid_gateway_at_matches_only_registered_gate_rooms(self):
        from web.webclient.presentation.local_map import _grid_gateway_at

        self.assertIsNotNone(_grid_gateway_at(*EAST_GATE_XYZ))
        # The plaza AnchorRoom is an in-map landmark, not a registered gate.
        self.assertIsNone(_grid_gateway_at(*_T_PLAZA_XYZ))

    def test_grid_gateway_at_rejects_a_gate_on_a_different_z_map_key(self):
        from web.webclient.presentation.local_map import _grid_gateway_at

        # Same coordinates, wrong map: the registry's own z_map_key must
        # match, never just the (x, y) pair (design D3's cross-space guard).
        self.assertIsNone(
            _grid_gateway_at(EAST_GATE_XYZ[0], EAST_GATE_XYZ[1], "some_other_map")
        )
        self.assertIsNotNone(_grid_gateway_at(*EAST_GATE_XYZ))

    def test_gateway_far_side_label_wilderness_names_the_anchor(self):
        from web.webclient.presentation.local_map import _gateway_far_side_label

        label = _gateway_far_side_label("wilderness", EAST_APPROACH, _T_MAP_KEY)
        self.assertEqual(label, _t_anchor_display(_T_MAP_KEY))
        self.assertNotEqual(label, _t_region_display_for(*EAST_APPROACH))

    def test_gateway_far_side_label_grid_names_the_far_side_region(self):
        from web.webclient.presentation.local_map import _gateway_far_side_label

        label = _gateway_far_side_label("grid", EAST_APPROACH, _T_MAP_KEY)
        self.assertEqual(label, _t_region_display_for(*EAST_APPROACH))


class GatewayTableMemoTests(unittest.TestCase):
    """The registered-gateway table is built once per published input set.

    Every entry is synthetic (point-shape, reusing a gate destination probed
    from the live registry); only call counts and returned rows are asserted.
    """

    def setUp(self):
        from web.webclient.presentation.local_map import gateways
        from world.maps.published import SourceMemo

        self.gateways = gateways
        memo = patch.object(gateways, "_GATEWAY_TABLE", SourceMemo())
        memo.start()
        self.addCleanup(memo.stop)
        self.gate = _city_gate_row_for(_NORTH_FACE).gate
        self.gate_xy = SOUTH_GATE_XYZ[:2]
        self.gate_z = SOUTH_GATE_XYZ[2]

    def _point(self, anchor_key, origin_xy, shape=("#",)):
        from world.lore.wilderness_entry import WildernessEntryPoint, WildernessGate

        return WildernessEntryPoint(
            anchor_key=anchor_key,
            shape=shape,
            origin_xy=origin_xy,
            gates=(WildernessGate("n", self.gate),),
        )

    def _registry(self, *entries):
        return patch(
            "world.lore.wilderness_entry.WILDERNESS_ENTRY_REGISTRY",
            {entry.anchor_key: entry for entry in entries},
        )

    def _spies(self):
        from world.maps import static_references

        builds = patch.object(
            self.gateways,
            "_build_gateway_table",
            wraps=self.gateways._build_gateway_table,
        )
        indexes = patch(
            "world.maps.static_references.settlement_reference_index",
            wraps=static_references.settlement_reference_index,
        )
        return builds, indexes

    def test_repeated_lookups_build_one_table_and_one_settlement_index(self):
        builds, indexes = self._spies()
        with self._registry(
            self._point("t_alpha", (10, 10)), self._point("t_beta", (12, 10))
        ), builds as build_spy, indexes as index_spy:
            self.assertEqual(len(self.gateways._registered_gateways()), 2)
            for _ in range(20):
                self.assertIsNotNone(self.gateways._wilderness_gateway_at(10, 10))
                self.assertIsNotNone(
                    self.gateways._grid_gateway_at(*self.gate_xy, self.gate_z)
                )
        self.assertEqual(build_spy.call_count, 1)
        self.assertEqual(index_spy.call_count, 1)

    def test_a_new_registry_or_settlement_graph_source_rebuilds_the_table(self):
        from world.maps import map_data

        builds, _ = self._spies()
        with builds as build_spy:
            with self._registry(self._point("t_alpha", (10, 10))):
                self.assertEqual(
                    [row[2] for row in self.gateways._registered_gateways()],
                    ["t_alpha"],
                )
            with self._registry(self._point("t_beta", (14, 11))):
                rows = self.gateways._registered_gateways()
                self.assertEqual(
                    rows, [((14, 11), (self.gate_xy, self.gate_z), "t_beta")]
                )
                self.assertIsNone(self.gateways._wilderness_gateway_at(10, 10))
                self.assertEqual(build_spy.call_count, 2)
                with patch.object(
                    map_data,
                    "SETTLEMENT_GRAPHS",
                    dict(map_data.SETTLEMENT_GRAPHS.source),
                ):
                    self.assertEqual(self.gateways._registered_gateways(), rows)
                    self.assertEqual(build_spy.call_count, 3)

    def test_a_gate_without_an_approach_cell_is_skipped_without_error(self):
        empty = self._point("t_empty", (20, 20), shape=(".",))
        with self._registry(empty, self._point("t_valid", (10, 10))):
            rows = self.gateways._registered_gateways()
            self.assertEqual([row[2] for row in rows], ["t_valid"])
            self.assertIsNone(self.gateways._wilderness_gateway_at(20, 20))

    def test_duplicate_cells_return_the_first_registered_gate(self):
        with self._registry(
            self._point("t_first", (10, 10)), self._point("t_second", (10, 10))
        ):
            self.assertEqual(self.gateways._wilderness_gateway_at(10, 10)[2], "t_first")
            self.assertEqual(
                self.gateways._grid_gateway_at(*self.gate_xy, self.gate_z)[2],
                "t_first",
            )
            self.assertEqual(
                [row[2] for row in self.gateways._registered_gateways()],
                ["t_first", "t_second"],
            )

    def test_mutating_the_returned_rows_does_not_change_the_table(self):
        with self._registry(self._point("t_alpha", (10, 10))):
            rows = self.gateways._registered_gateways()
            expected = list(rows)
            self.assertTrue(expected)
            rows.clear()
            self.assertEqual(self.gateways._registered_gateways(), expected)


if __name__ == "__main__":
    unittest.main()
