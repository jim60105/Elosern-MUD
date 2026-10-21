"""Data-contract test: wilderness region data contract
Self-consistency checks for the wilderness terrain registry (map-wilderness)."""

from tools.spec_traceability import covers_requirement

import unittest
from dataclasses import fields

from world.lore.anchors import ANCHOR_GEOGRAPHY_REGISTRY, ANCHOR_REGISTRY
from world.lore.nations import NATION_REGISTRY
from world.lore.wilderness_regions import (
    CELL_CENTER_OFFSET_M,
    CONTINENT_CELL_SIZE_KM,
    CONTINENT_FRAME_CELLS,
    HARBOR_SITE_REGISTRY,
    MAINLAND_BOUNDARY_KM,
    WILDERNESS_REGION_REGISTRY,
    HarborSite,
    WildernessRegion,
    cell_center_m,
    is_on_mainland,
    is_wilderness_cell,
    mainland_area_km2,
)

EXPECTED_KEYS = {
    "central_mountains",
    "eastern_plains",
    "southeast_coast",
    "western_hills_valleys",
    "southwest_coast",
    "northwest_highland_forest",
    "north_deep_forest",
}


class WildernessRegionRegistryTests(unittest.TestCase):
    @covers_requirement("wilderness-terrain::wilderness-region-registry-covers-exactly-the-seven-world-info-md-terrain-regions")
    def test_registry_has_exactly_seven_entries_with_unique_names(self):
        self.assertEqual(set(WILDERNESS_REGION_REGISTRY), EXPECTED_KEYS)
        names = [region.display_name_zh for region in WILDERNESS_REGION_REGISTRY.values()]
        self.assertEqual(len(names), len(set(names)))

    def test_every_region_carries_at_least_two_flavor_variants(self):
        for region in WILDERNESS_REGION_REGISTRY.values():
            self.assertGreaterEqual(len(region.terrain_flavor_zh), 2)

    def test_every_non_none_nation_key_exists_in_nation_registry(self):
        for region in WILDERNESS_REGION_REGISTRY.values():
            if region.nation_key is not None:
                self.assertIn(region.nation_key, NATION_REGISTRY)

    def test_dataclass_is_frozen_and_keyed_by_key_field(self):
        self.assertTrue(WildernessRegion.__dataclass_params__.frozen)
        for key, region in WILDERNESS_REGION_REGISTRY.items():
            self.assertEqual(region.key, key)

    @covers_requirement(
        "continental-geography::the-known-continent-has-frozen-geographic-declarations"
    )
    def test_mainland_boundary_is_a_closed_five_million_square_kilometre_polygon(self):
        self.assertEqual(
            MAINLAND_BOUNDARY_KM,
            (
                (450, 100),
                (1850, 100),
                (2400, 450),
                (2600, 1350),
                (1930, 2250),
                (1800, 2600),
                (750, 2550),
                (200, 2050),
                (100, 1050),
                (300, 350),
            ),
        )
        self.assertEqual(mainland_area_km2(), 5_000_000)
        # Boundary vertices and edges are land; the ocean margin is not.
        self.assertTrue(is_on_mainland(450, 100))
        self.assertTrue(is_on_mainland(1850, 100))
        self.assertTrue(is_on_mainland(1400, 1300))
        self.assertFalse(is_on_mainland(449, 100))
        self.assertFalse(is_on_mainland(0, 0))

    @covers_requirement(
        "continental-geography::coordinate-frames-have-explicit-physical-units"
    )
    def test_frame_covers_2700_logical_kilometre_cells_with_metre_centers(self):
        self.assertEqual(CONTINENT_FRAME_CELLS, 2700)
        self.assertEqual(CONTINENT_CELL_SIZE_KM, 1)
        self.assertEqual(CELL_CENTER_OFFSET_M, 500)
        self.assertEqual(cell_center_m((0, 0)), (500, 500))
        self.assertEqual(cell_center_m((860, 1080)), (860_500, 1_080_500))
        self.assertEqual(
            cell_center_m((2699, 2699)),
            (2699 * 1000 + 500, 2699 * 1000 + 500),
        )
        self.assertTrue(is_wilderness_cell((0, 0)))
        self.assertTrue(is_wilderness_cell((2699, 2699)))
        self.assertFalse(is_wilderness_cell((-1, 0)))
        self.assertFalse(is_wilderness_cell((0, 2700)))

    @covers_requirement(
        "continental-geography::the-known-continent-has-frozen-geographic-declarations"
    )
    def test_every_anchor_and_harbor_cell_center_lies_on_the_mainland(self):
        cells = {
            key: entry.cell for key, entry in ANCHOR_GEOGRAPHY_REGISTRY.items()
        }
        cells.update({key: entry.cell for key, entry in HARBOR_SITE_REGISTRY.items()})
        for key, cell in cells.items():
            with self.subTest(site=key):
                self.assertTrue(is_wilderness_cell(cell))
                east_m, north_m = cell_center_m(cell)
                self.assertTrue(is_on_mainland(east_m / 1000, north_m / 1000))

    @covers_requirement(
        "continental-geography::the-known-continent-has-frozen-geographic-declarations"
    )
    def test_six_reserved_harbor_sites_are_land_side_geography_only(self):
        self.assertEqual(
            {key: site.cell for key, site in HARBOR_SITE_REGISTRY.items()},
            {
                "kingdom_southwest_main_port": (301, 350),
                "kingdom_western_secondary_port": (201, 700),
                "kingdom_southern_secondary_port": (600, 101),
                "imperial_southeast_main_port": (2070, 241),
                "imperial_southeast_secondary_port": (2400, 454),
                "imperial_southern_secondary_port": (1700, 101),
            },
        )
        self.assertEqual(
            {key: site.role for key, site in HARBOR_SITE_REGISTRY.items()},
            {
                "kingdom_southwest_main_port": "River/sea transfer and foreign trade",
                "kingdom_western_secondary_port": "Western mining and craft exports",
                "kingdom_southern_secondary_port": "Southern coastal supply",
                "imperial_southeast_main_port": "Agricultural and magical-goods exports",
                "imperial_southeast_secondary_port": "Eastern coastal collection",
                "imperial_southern_secondary_port": "Southern coastal transfer",
            },
        )
        self.assertEqual(
            {field.name for field in fields(HarborSite)},
            {"key", "display_name", "cell", "role"},
        )
        self.assertTrue(HarborSite.__dataclass_params__.frozen)
        self.assertFalse(set(HARBOR_SITE_REGISTRY) & set(ANCHOR_REGISTRY))
