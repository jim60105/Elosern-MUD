"""Data-contract test: wilderness region data contract

Self-consistency checks for the published wilderness terrain views
(map-wilderness). Every assertion reads the composed views of one explicitly
loaded candidate, so it follows the source documents instead of a copied
Python table.
"""

from tools.spec_traceability import covers_requirement

import unittest

from elosern_map_core.geometry import CELL_CENTER_OFFSET_M, cell_center_m
from elosern_map_core.terrain import REGION_KEYS
import world.maps.geography as geography
from world.lore.anchors import anchor_geography, anchors
from world.lore.nations import NATION_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.lore.wilderness_regions import (
    WildernessRegion,
    cell_size_km,
    frame_cells,
    harbor_sites,
    is_on_mainland,
    is_wilderness_cell,
    mainland_area_km2,
    mainland_boundary_km,
    regions,
)


def setUpModule():
    if not geography.is_published():
        geography.publish(geography.load_geography())


class WildernessRegionRegistryTests(unittest.TestCase):
    @covers_requirement("wilderness-terrain::wilderness-region-registry-covers-the-authored-terrain-regions")
    def test_every_classifier_region_is_declared_with_a_unique_display_name(self):
        published = regions()
        self.assertEqual(
            {key for key in published if key in REGION_KEYS},
            set(REGION_KEYS),
        )
        names = [region.display_name_zh for region in published.values()]
        self.assertEqual(len(names), len(set(names)))

    def test_every_region_carries_at_least_two_nonblank_flavor_variants(self):
        for key, region in regions().items():
            with self.subTest(region=key):
                self.assertGreaterEqual(len(region.terrain_flavor_zh), 2)
                for variant in region.terrain_flavor_zh:
                    self.assertTrue(variant.strip())

    def test_every_region_declares_a_registered_scene_archetype(self):
        for key, region in regions().items():
            with self.subTest(region=key):
                self.assertIn(region.scene_archetype, SCENE_ARCHETYPE_REGISTRY)

    def test_every_non_none_nation_key_exists_in_nation_registry(self):
        for region in regions().values():
            if region.nation_key is not None:
                self.assertIn(region.nation_key, NATION_REGISTRY)

    def test_every_region_lists_its_sorted_nominal_claimants(self):
        # Shared terrain regions are explicitly multi-nation; a single-nation
        # region lists exactly its scalar nation_key.
        for key, region in regions().items():
            with self.subTest(region=key):
                self.assertTrue(region.nominal_nation_keys)
                self.assertEqual(
                    region.nominal_nation_keys,
                    tuple(sorted(region.nominal_nation_keys)),
                )
                self.assertLessEqual(
                    {region.nation_key} - {None}, set(region.nominal_nation_keys)
                )
                if region.nation_key is not None:
                    self.assertEqual(region.nominal_nation_keys, (region.nation_key,))

    def test_dataclass_is_frozen_and_keyed_by_key_field(self):
        self.assertTrue(WildernessRegion.__dataclass_params__.frozen)
        for key, region in regions().items():
            self.assertEqual(region.key, key)

    @covers_requirement(
        "continental-geography::the-known-continent-has-frozen-geographic-declarations"
    )
    def test_mainland_boundary_is_a_closed_five_million_square_kilometre_polygon(self):
        boundary = mainland_boundary_km()
        self.assertGreaterEqual(len(boundary), 3)
        self.assertNotEqual(boundary[0], boundary[-1])
        self.assertAlmostEqual(mainland_area_km2(), 5_000_000, delta=1)
        self.assertTrue(is_on_mainland(1000, 1000))
        self.assertTrue(is_on_mainland(*boundary[0]))
        self.assertFalse(is_on_mainland(0, 0))

    @covers_requirement(
        "continental-geography::coordinate-frames-have-explicit-physical-units"
    )
    @covers_requirement(
        "map-geometry-model::geometry-is-explicit-and-snapshot-scoped"
    )
    def test_frame_covers_logical_kilometre_cells_with_metre_centers(self):
        self.assertEqual(frame_cells(), 2700)
        self.assertEqual(cell_size_km(), 1)
        self.assertEqual(CELL_CENTER_OFFSET_M, 500)
        self.assertEqual(cell_center_m((0, 0)), (500, 500))
        self.assertEqual(cell_center_m((2699, 2699)), (2_699_500, 2_699_500))
        self.assertTrue(is_wilderness_cell((0, 0)))
        self.assertTrue(is_wilderness_cell((frame_cells() - 1,) * 2))
        self.assertFalse(is_wilderness_cell((0, frame_cells())))
        self.assertFalse(is_wilderness_cell((-1, 0)))

    @covers_requirement(
        "continental-geography::the-known-continent-has-frozen-geographic-declarations"
    )
    def test_every_location_and_harbor_cell_center_lies_on_the_mainland(self):
        cells = {
            key: entry.cell for key, entry in anchor_geography().items()
        }
        regions_of_sites = harbor_sites()
        cells.update(
            {key: site.cell for key, site in regions_of_sites.items()}
        )
        self.assertTrue(cells)
        for key, cell in cells.items():
            with self.subTest(site=key):
                self.assertTrue(is_wilderness_cell(cell))
                east_m, north_m = cell_center_m(cell)
                self.assertTrue(is_on_mainland(east_m / 1000, north_m / 1000))

    @covers_requirement(
        "continental-geography::the-known-continent-has-frozen-geographic-declarations"
    )
    def test_reserved_harbor_sites_are_geography_only_and_disjoint(self):
        for key, site in harbor_sites().items():
            with self.subTest(site=key):
                self.assertEqual(site.key, key)
                self.assertTrue(site.display_name)
                self.assertTrue(site.role)
        self.assertFalse(set(harbor_sites()) & set(anchors()))


if __name__ == "__main__":
    unittest.main()
