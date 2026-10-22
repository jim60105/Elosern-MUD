"""Data-contract test: authored continental terrain, waterway and anchor-region data contract

The signed geography rows are shipped content, so this module names them: every
anchor's terrain, the bending mountain corridor and its authored pass, and the
capital/imperial waterways with their declared fords must agree with the
classifier. Mechanics (purity, bounds, pooled rooms, gate locks) stay in
``world/maps/tests/test_wilderness_provider.py`` (map-wilderness,
wilderness-anchor-footprint, rescale-wilderness-geography).
"""

from tools.spec_traceability import covers_requirement

import unittest

from world.maps.wilderness_provider import (
    RIDGE_PASSES,
    WATERWAY_FORDS,
    WATERWAY_ROUTES,
    _rasterize_routes,
    _ridge_center_x,
    is_closed_ridge_cell,
    is_inland_water_cell,
    is_land_cell,
    is_valid_wilderness_cell,
    region_for_coordinates,
)


class AuthoredTerrainContractTests(unittest.TestCase):
    @covers_requirement("wilderness-terrain::region-for-coordinates-is-a-pure-deterministic-function-covering-the-whole-bounded-map")
    def test_central_mountain_region_bends_with_the_authored_corridor(self):
        # The corridor follows the bending summit centre; it is neither a fixed
        # rectangular band nor a continuous summit wall (the pass windows below
        # are open ground).
        for y in (150, 700, 1200, 2100):
            centre = _ridge_center_x(y)
            self.assertEqual(region_for_coordinates(centre, y), "central_mountains")
            self.assertNotEqual(
                region_for_coordinates(centre - 300, y), "central_mountains"
            )
            self.assertNotEqual(
                region_for_coordinates(centre + 300, y), "central_mountains"
            )
        self.assertNotEqual(_ridge_center_x(100), _ridge_center_x(1200))

    @covers_requirement("wilderness-terrain::region-for-coordinates-is-a-pure-deterministic-function-covering-the-whole-bounded-map")
    def test_settlement_derived_anchor_cells_resolve_to_altoria_territory(self):
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

        entry = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
        cells = {entry.anchor_cell} | {
            entry.approach_cell(gate) for gate in entry.gates
        }
        self.assertTrue(cells, "the capital entry must supply anchor and gate cells")
        # Delta scenario: Altoria's anchor and both gate approaches are the
        # western hills and valleys (the signed anchor relationships).
        for cell in cells:
            self.assertEqual(region_for_coordinates(*cell), "western_hills_valleys")

    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_anchor_centres_resolve_their_authored_terrain(self):
        # Region keys are the terrain layer; nominal claims stay in
        # ``world.lore.nations``. The authored anchor relationships pin which
        # terrain each canonical anchor cell belongs to.
        from world.lore.anchors import ANCHOR_GEOGRAPHY_REGISTRY

        expected = {
            "capital_altoria": "western_hills_valleys",
            "capital_valhalla": "northwest_highland_forest",
            "capital_grandia": "eastern_plains",
            "village_ciaran": "central_mountains",
            "village_fionnen": "central_mountains",
            "village_eolas": "central_mountains",
        }
        for anchor_key, region_key in expected.items():
            cell = ANCHOR_GEOGRAPHY_REGISTRY[anchor_key].cell
            self.assertEqual(region_for_coordinates(*cell), region_key, anchor_key)

    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_principal_pass_is_open_mountain_trail_and_ridge_blocks_elsewhere(self):
        from world.rules.travel_cost import WILDERNESS_TERRAIN, terrain_speed_m_per_hour

        # The principal pass near (1410, 980) is open ground in the mountain
        # region, costed as mountain trail: an explicit slower crossing, never
        # an all-road shortcut.
        self.assertIn(980, range(*RIDGE_PASSES[1]))
        self.assertFalse(is_closed_ridge_cell((1410, 980)))
        self.assertEqual(region_for_coordinates(1410, 980), "central_mountains")
        mountain = terrain_speed_m_per_hour(WILDERNESS_TERRAIN["central_mountains"])
        self.assertLess(mountain, terrain_speed_m_per_hour("road"))
        # Away from an authored pass the summit ridge is a closed cliff wall.
        self.assertTrue(is_closed_ridge_cell((_ridge_center_x(1200), 1200)))

    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_rivers_are_authored_water_with_declared_fords(self):
        # Every ford lies on its own river, and every river starts and ends on
        # the coastal region it drains into (capital river -> southwest coast;
        # imperial rivers -> southeast coast).
        raster = _rasterize_routes(WATERWAY_ROUTES)
        for name, fords in WATERWAY_FORDS.items():
            for ford in fords:
                # The ford is on its authored river before the exemption is
                # subtracted, so a typo cannot silently remove a crossing.
                self.assertIn(ford, raster, name)
                self.assertFalse(is_inland_water_cell(ford), name)
                self.assertTrue(is_land_cell(ford), name)
        capital = WATERWAY_ROUTES["capital_river"]
        self.assertEqual(region_for_coordinates(*capital[-1]), "southwest_coast")
        for name in ("imperial_river", "imperial_east_branch"):
            self.assertEqual(
                region_for_coordinates(*WATERWAY_ROUTES[name][-1]), "southeast_coast"
            )
        # A river cell is impassable water; its declared ford is ordinary land.
        river_cell = (900, 1042)
        self.assertTrue(is_inland_water_cell(river_cell))
        self.assertFalse(is_valid_wilderness_cell(river_cell))
        self.assertFalse(is_inland_water_cell(WATERWAY_FORDS["capital_river"][0]))
        self.assertTrue(is_valid_wilderness_cell(WATERWAY_FORDS["capital_river"][0]))

    @covers_requirement("wilderness-map-provider::the-continent-remains-virtual-with-bounded-local-lookup")
    def test_anchor_and_port_centres_are_land_side(self):
        from world.lore.anchors import ANCHOR_GEOGRAPHY_REGISTRY
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
        from world.lore.wilderness_regions import HARBOR_SITE_REGISTRY

        for anchor in ANCHOR_GEOGRAPHY_REGISTRY.values():
            self.assertTrue(is_land_cell(anchor.cell), anchor.anchor_key)
        for harbor in HARBOR_SITE_REGISTRY.values():
            self.assertTrue(is_land_cell(harbor.cell), harbor.key)
        # Declaration reveals nothing: no settlement map is invented for the
        # seven unbuilt anchors.
        self.assertLessEqual(
            set(WILDERNESS_ENTRY_REGISTRY), set(ANCHOR_GEOGRAPHY_REGISTRY)
        )


if __name__ == "__main__":
    unittest.main()
