"""Repository contract: the authored geography sources load in the pure core.

The continental geography and every static geographic location are authored in
``content/maps/{continent,locations}.yaml``. This check loads those two real
documents in an interpreter where Evennia, Django, ``world`` and ``typeclasses``
cannot be imported, and asserts the source-level contracts a consumer relies
on: schema identity, region prose validity, classifier coverage, units and the
absence of any fabricated local map for a location.

Mechanism-level behavior (publication, joins, snapshot isolation) is owned by
``world.maps.tests.test_geography_source`` under the Evennia test runner.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "packages" / "map-core"

ISOLATED_GEOGRAPHY = textwrap.dedent(
    """
    import json
    import sys
    from pathlib import Path

    FORBIDDEN = {"evennia", "django", "twisted", "world", "typeclasses"}

    class Blocker:
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in FORBIDDEN:
                raise AssertionError(f"map core imported forbidden namespace {name}")
            return None

    sys.meta_path.insert(0, Blocker())
    sys.path.insert(0, sys.argv[1])

    from elosern_map_core import (
        METRES_PER_WILDERNESS_CELL,
        REGION_KEYS,
        TerrainDefinition,
        is_within_frame,
        nominal_nation_for_coordinates,
        parse_document,
        polygon_area_km2,
        region_for_coordinates,
        terrain_description,
    )
    from elosern_map_core.schema import LOCATION_KINDS

    root = Path(sys.argv[2])
    continent_text = (root / "content/maps/continent.yaml").read_text(encoding="utf-8")
    locations_text = (root / "content/maps/locations.yaml").read_text(encoding="utf-8")
    continent = parse_document("content/maps/continent.yaml", continent_text)
    locations = parse_document("content/maps/locations.yaml", locations_text)
    document = continent.document
    terrain = TerrainDefinition(
        frame_cells=document.terrain.frame_cells,
        mainland_boundary_km=document.terrain.mainland_boundary_km,
        forest_edge=document.terrain.forest_edge,
        waterway_routes={
            key: value.route for key, value in document.terrain.waterways.items()
        },
        waterway_fords={
            key: value.fords for key, value in document.terrain.waterways.items()
        },
        border_river_key=document.terrain.border_river_key,
        ridge_base_x=document.terrain.ridge_base_x,
        ridge_period=document.terrain.ridge_period,
        ridge_step=document.terrain.ridge_step,
        ridge_min_x=document.terrain.ridge_min_x,
        ridge_max_x=document.terrain.ridge_max_x,
        ridge_north_limit=document.terrain.ridge_north_limit_y,
        ridge_passes=document.terrain.ridge_passes,
        coastal_y_max=document.terrain.coastal_y_max,
        mountain_corridor_half_width=document.terrain.ridge_corridor_half_width,
        region_flavors={
            key: value.terrain_flavor_zh for key, value in document.regions.items()
        },
    )
    frame = document.terrain.frame_cells
    sample = []
    for y in range(0, frame, 173):
        for x in range(0, frame, 173):
            sample.append(
                [
                    region_for_coordinates(terrain, x, y),
                    nominal_nation_for_coordinates(terrain, x, y),
                    terrain_description(terrain, x, y),
                ]
            )
    print(
        json.dumps(
            {
                "identity": [continent.identity, locations.identity],
                "frame_cells": frame,
                "cell_size_km": document.terrain.cell_size_km,
                "metres_per_cell": METRES_PER_WILDERNESS_CELL,
                "mainland_area_km2": polygon_area_km2(
                    document.terrain.mainland_boundary_km
                ),
                "region_keys": sorted(document.regions),
                "classifier_keys": sorted(REGION_KEYS),
                "region_scene_archetypes": {
                    key: value.scene_archetype
                    for key, value in document.regions.items()
                },
                "region_variant_counts": {
                    key: len(value.terrain_flavor_zh)
                    for key, value in document.regions.items()
                },
                "region_names": sorted(
                    value.display_name_zh for value in document.regions.values()
                ),
                "location_kinds": sorted(LOCATION_KINDS),
                "locations": {
                    key: {
                        "kind": value.kind,
                        "cell": list(value.cell),
                        "in_frame": is_within_frame(frame, value.cell),
                        "display_name_zh": value.display_name_zh,
                        "description": value.description,
                        "geographic_constraint": value.geographic_constraint,
                    }
                    for key, value in locations.document.locations.items()
                },
                "harbor_cells": {
                    key: list(value.cell)
                    for key, value in document.harbor_sites.items()
                },
                "sample_classification": sample,
            }
        )
    )
    """
)


def _load_geography() -> dict:
    result = subprocess.run(
        [sys.executable, "-I", "-c", ISOLATED_GEOGRAPHY, str(PACKAGE_ROOT), str(REPO_ROOT)],
        capture_output=True,
        text=True,
        cwd=tempfile.mkdtemp(),
        timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


class MapGeographicSourcesContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geography = _load_geography()

    @covers_requirement(
        "map-geographic-sources::geographic-yaml-is-the-sole-map-facing-authority"
    )
    def test_the_core_loads_both_canonical_documents_without_game_imports(self):
        identity = self.geography["identity"]
        self.assertEqual(len(identity), 2)
        self.assertTrue(all(identity))

    def test_declared_regions_cover_every_classifier_result(self):
        self.assertEqual(self.geography["region_keys"], self.geography["classifier_keys"])
        for region, nation, description in self.geography["sample_classification"]:
            with self.subTest(region=region, nation=nation):
                self.assertIn(region, self.geography["region_keys"])
                self.assertTrue(nation)
                self.assertTrue(description)
        names = self.geography["region_names"]
        self.assertEqual(len(names), len(set(names)))

    def test_every_region_declares_two_nonblank_variants_and_its_scene(self):
        for key, count in self.geography["region_variant_counts"].items():
            with self.subTest(region=key):
                self.assertGreaterEqual(count, 2)
        for key, scene in self.geography["region_scene_archetypes"].items():
            with self.subTest(region=key):
                self.assertIsInstance(scene, str)
                self.assertTrue(scene)

    def test_frame_and_mainland_keep_their_declared_units(self):
        self.assertEqual(self.geography["cell_size_km"], 1)
        self.assertEqual(self.geography["metres_per_cell"], 1000)
        self.assertAlmostEqual(
            self.geography["mainland_area_km2"], 5_000_000, delta=1
        )

    def test_every_location_is_map_face_only_and_inside_the_frame(self):
        locations = self.geography["locations"]
        self.assertTrue(locations)
        for key, location in locations.items():
            with self.subTest(location=key):
                self.assertIn(location["kind"], self.geography["location_kinds"])
                self.assertTrue(location["in_frame"])
                self.assertTrue(location["display_name_zh"])
                self.assertTrue(location["geographic_constraint"])
                self.assertNotIn("population", location)
                self.assertNotIn("nation_key", location)
        for key, cell in self.geography["harbor_cells"].items():
            with self.subTest(harbor=key):
                self.assertTrue(0 <= cell[0] < self.geography["frame_cells"])
                self.assertTrue(0 <= cell[1] < self.geography["frame_cells"])
        self.assertFalse(set(locations) & set(self.geography["harbor_cells"]))

    def test_unbuilt_locations_have_no_local_map_document(self):
        settlements = REPO_ROOT / "content" / "maps" / "settlements"
        interiors = REPO_ROOT / "content" / "maps" / "interiors"
        authored = set()
        for directory in (settlements, interiors):
            if directory.is_dir():
                for path in directory.glob("*.yaml"):
                    authored.add(path.stem)
        self.assertFalse(
            authored & set(self.geography["locations"]),
            "a geographic location must not fabricate a settlement or interior",
        )


if __name__ == "__main__":
    unittest.main()
