import unittest
from unittest.mock import patch
from world.maps.bootstrap import sync_grid, sync_wilderness

from ._support import (
    EAST_APPROACH,
    EAST_GATE_XYZ,
    SOUTH_APPROACH,
    SOUTH_GATE_XYZ,
    _T_MAP_KEY,
    _T_PLAZA_XYZ,
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

        cave = WildernessEntryPoint(
            anchor_key="t_dungeon_point",
            shape=("#",),
            origin_xy=(10, 10),
            gates=(WildernessGate("n", (0, 0), _T_MAP_KEY),),
        )
        with patch(
            "world.lore.wilderness_entry.WILDERNESS_ENTRY_REGISTRY",
            {"t_dungeon_point": cave},
        ):
            gateways = _registered_gateways()
        self.assertEqual(
            gateways,
            [((10, 10), ((0, 0), _T_MAP_KEY), "t_dungeon_point")],
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


if __name__ == "__main__":
    unittest.main()
