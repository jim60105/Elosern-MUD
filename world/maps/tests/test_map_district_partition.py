"""Data-contract test: the committed district partition recomputes exactly from shipped geography

The frozen partition (``world/maps/data/district_partition.json``) is
generated from the shipped continent and district registry, so this module
regenerates it from the live terrain and compares the complete artifact byte
for byte, then checks the shipped ownership: every land cell owned once, sea
unowned, the deep forest exactly its region, every Voronoi district inside
one nation and connected to its own sources by legal steps, every landmark
in its own district, and a runtime lookup that never loads the generator.
Partition mechanics are covered by synthetic fixtures in
``tests.test_map_district_partition``.
"""

import json
import os
import subprocess
import sys
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy import ndimage

from tools import map_district_partition as generator
from tools.spec_traceability import covers_requirement
from world.lore.map_districts import MAP_DISTRICT_REGISTRY
from world.maps import district_partition

_REGENERATE = "uv run --locked python -m tools.map_district_partition"


class ShippedDistrictPartitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.inp = generator.production_input()
        cls.partition = generator.compute_partition(cls.inp)
        cls.text = generator.serialize(generator.encode(cls.partition, cls.inp))
        cls.committed = generator.DATA_PATH.read_text(encoding="utf-8")

    @covers_requirement(
        "map-district-partition::frozen-partition-and-outlines-reproduce-deterministically-offline"
    )
    def test_committed_partition_matches_a_fresh_recomputation(self):
        self.assertEqual(
            self.text,
            self.committed,
            f"the frozen district partition is stale; regenerate it with: {_REGENERATE}",
        )
        self.assertEqual(generator.DATA_PATH, district_partition.DATA_PATH)

    @covers_requirement(
        "map-district-partition::frozen-partition-and-outlines-reproduce-deterministically-offline"
    )
    def test_a_registry_change_without_regeneration_is_a_mismatch(self):
        dropped = next(d for d in self.inp.districts if d.key == "eastern_pasture")
        changed = replace(self.inp, districts=tuple(d for d in self.inp.districts if d is not dropped))
        regenerated = generator.generate(changed)
        self.assertNotEqual(regenerated, self.committed)
        self.assertNotIn('"eastern_pasture"', regenerated)

    @covers_requirement(
        "map-district-partition::offline-partition-assigns-every-land-cell-once-without-crossing-barriers"
    )
    def test_every_land_cell_has_exactly_one_owner_and_sea_none(self):
        owner, land = self.partition.owner, self.inp.land
        self.assertTrue(np.all(owner[land] > 0))
        self.assertTrue(np.all(owner[~land] == 0))
        self.assertEqual(self.partition.keys, tuple(sorted(MAP_DISTRICT_REGISTRY)))
        # The runtime decoder agrees with the raster on a lattice of the
        # frame plus every cell of every exception tile.
        frozen = district_partition.frozen_partition()
        cells = [(x, y) for y in range(0, 2700, 13) for x in range(0, 2700, 13)]
        for tx, ty in list(frozen.exceptions)[::7]:
            cells += [(tx * 5 + dx, ty * 5 + dy) for dx in range(5) for dy in range(5)]
        for x, y in cells:
            self.assertEqual(frozen.district_at((x, y)), self.partition.owner_at((x, y)), (x, y))

    @covers_requirement(
        "map-district-partition::offline-partition-assigns-every-land-cell-once-without-crossing-barriers"
    )
    def test_forest_is_exactly_its_region_and_voronoi_districts_never_straddle_a_border(self):
        owner, inp = self.partition.owner, self.inp
        forest = self.partition.keys.index("north_deep_forest") + 1
        forest_region = inp.region_names.index("north_deep_forest") + 1
        self.assertTrue(np.array_equal(owner == forest, inp.land & (inp.region == forest_region)))
        claims = {inp.nation_names[c - 1] for c in np.unique(inp.nation[owner == forest]).tolist()}
        self.assertEqual(claims, {"grandia", "valhalla"})
        for code, key in enumerate(self.partition.keys, start=1):
            if key == "north_deep_forest":
                continue
            with self.subTest(district=key):
                nations = np.unique(inp.nation[owner == code])
                self.assertEqual(nations.size, 1)

    @covers_requirement(
        "map-district-partition::offline-partition-assigns-every-land-cell-once-without-crossing-barriers"
    )
    def test_voronoi_ground_is_reached_from_its_own_sources_without_crossing(self):
        owner, fragment = self.partition.owner, self.partition.fragment
        domain = self.partition.domain
        cross = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=bool)
        for key, sources in self.partition.sources.items():
            code = self.partition.keys.index(key) + 1
            with self.subTest(district=key):
                labels, _ = ndimage.label(domain & (owner == code), structure=cross)
                seeded = set(labels[np.isin(fragment, sources)].tolist()) - {0}
                owned = set(np.unique(labels[labels > 0]).tolist())
                # Every walkable cell of the district connects by legal
                # same-nation steps to one of its own source fragments,
                # except pockets enclosed by its own claimed footprint.
                unseeded = owned - seeded
                for label in unseeded:
                    pocket = labels == label
                    ring = ndimage.binary_dilation(pocket, structure=np.ones((3, 3), bool)) & ~pocket
                    self.assertFalse(np.any(self.partition.domain[ring]), key)

    @covers_requirement(
        "map-district-partition::offline-partition-assigns-every-land-cell-once-without-crossing-barriers"
    )
    def test_every_landmark_lies_in_its_own_district(self):
        by_key = {seed.key: seed for seed in self.inp.districts}
        self.assertEqual(set(by_key), set(MAP_DISTRICT_REGISTRY))
        for key, seed in by_key.items():
            with self.subTest(district=key):
                self.assertEqual(district_partition.district_at(seed.landmark_cell), key)
        # The capital plaza landmark is inside the capital's footprint; the
        # whole footprint belongs to the plaza's district.
        royal = by_key["royal_river_valley"]
        self.assertIn(royal.landmark_cell, royal.footprint)
        for cell in royal.footprint:
            self.assertEqual(district_partition.district_at(cell), "royal_river_valley", cell)

    @covers_requirement(
        "map-district-partition::offline-partition-assigns-every-land-cell-once-without-crossing-barriers"
    )
    def test_outlines_cover_every_district_with_integer_metre_rings(self):
        document = json.loads(self.committed)
        self.assertEqual(sorted(document["outlines"]), sorted(MAP_DISTRICT_REGISTRY))
        for key, rings in document["outlines"].items():
            with self.subTest(district=key):
                self.assertTrue(rings)
                for ring in rings:
                    self.assertEqual(len(ring) % 2, 0)
                    self.assertGreaterEqual(len(ring), 6)
                    self.assertTrue(all(isinstance(v, int) and 0 <= v <= 2_700_000 for v in ring))

    @covers_requirement(
        "map-district-partition::frozen-partition-and-outlines-reproduce-deterministically-offline"
    )
    def test_runtime_lookup_never_loads_the_generator(self):
        root = Path(district_partition.__file__).resolve().parents[2]
        probe = (
            "import sys\n"
            "from world.maps import district_partition as d\n"
            "assert d.district_at((1250, 2420)) == 'north_deep_forest'\n"
            "assert d.district_at((20, 20)) is None\n"
            "print(sorted(m for m in sys.modules if m.startswith(('tools', 'numpy', 'scipy'))))\n"
        )
        env = {**os.environ, "PYTHONPATH": str(root)}
        env.pop("DJANGO_SETTINGS_MODULE", None)
        result = subprocess.run(
            [sys.executable, "-c", probe], cwd=root, env=env, capture_output=True, text=True, timeout=120
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "[]")
