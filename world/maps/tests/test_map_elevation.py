"""Logic and mechanics tests for the wilderness elevation runtime adapter."""

from __future__ import annotations

import math
import unittest
from unittest import mock

from elosern_map_core.elevation_codec import (
    DEFAULT_CONFIG_DIGEST,
    ELEVATION_ALGORITHM_VERSION,
    ELEVATION_FORMAT_VERSION,
    ElevationBoundsError,
    ElevationDocumentError,
    ElevationMetadata,
    ElevationTileCorruptionError,
    encode_tile,
)
from world.maps import elevation, runtime
from world.maps.runtime import MapWorldError
from world.tests.geography_fixture import (
    clear_published_map_world,
    publish_shipped_map_world,
)


class ElevationRuntimeLogicTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        # Save active bundle state
        self._saved_bundle = runtime._BUNDLE
        publish_shipped_map_world()

    def tearDown(self):
        # Restore active bundle state
        if self._saved_bundle is not None:
            runtime.publish(self._saved_bundle)
        else:
            clear_published_map_world()
        super().tearDown()

    def test_unloaded_lookup_raises_without_zero_fallback(self):
        """When no elevation runtime is installed, lookups must raise ElevationNotLoadedError."""
        clear_published_map_world()
        self.assertFalse(elevation.is_loaded())
        with self.assertRaises(elevation.ElevationNotLoadedError):
            elevation.band(100, 100)
        with self.assertRaises(elevation.ElevationNotLoadedError):
            elevation.prominence_tier(100, 100)
        with self.assertRaises(elevation.ElevationNotLoadedError):
            elevation.cell_elevation(100, 100)

    def test_clear_published_world_clears_elevation_pointer(self):
        """Calling clear_published_map_world uninstall() must clear elevation."""
        publish_shipped_map_world()
        self.assertTrue(elevation.is_loaded())
        clear_published_map_world()
        self.assertFalse(elevation.is_loaded())
        with self.assertRaises(elevation.ElevationNotLoadedError):
            elevation.band(0, 0)

    def test_bounds_checks_reject_out_of_frame_and_non_integers(self):
        """Cell lookups outside 0..frame_cells-1 or with invalid types must raise ElevationBoundsError."""
        publish_shipped_map_world()
        active = elevation.current()
        frame = active.frame_cells

        # Out of bounds
        with self.assertRaises(ElevationBoundsError):
            active.cell_elevation(-1, 0)
        with self.assertRaises(ElevationBoundsError):
            active.cell_elevation(0, -1)
        with self.assertRaises(ElevationBoundsError):
            active.cell_elevation(frame, 0)
        with self.assertRaises(ElevationBoundsError):
            active.cell_elevation(0, frame)

        # Non-integers
        with self.assertRaises(ElevationBoundsError):
            active.cell_elevation(True, 10)  # bool
        with self.assertRaises(ElevationBoundsError):
            active.cell_elevation(10, 10.5)  # float
        with self.assertRaises(ElevationBoundsError):
            active.cell_elevation("10", 10)  # str

    def test_lru_cache_capacity_strictly_bounded_to_128_and_evicts(self):
        """Accessing more than 128 unique tiles keeps the cache size at 128."""
        frame = 2700
        active = elevation.current()
        cache = active._cache
        cache.clear()
        self.assertEqual(len(cache), 0)

        # Access 150 distinct tiles (frame has 43x43 = 1849 tiles)
        num_tiles_to_access = 150
        tiles_accessed = []
        for i in range(num_tiles_to_access):
            tx = i % 40
            ty = i // 40
            # Sample coordinate within tile (tx, ty)
            cx = tx * 64
            cy = ty * 64
            active.cell_elevation(cx, cy)
            tiles_accessed.append((active.fingerprint, tx, ty))

        self.assertEqual(len(cache), 128)
        self.assertLessEqual(len(cache), 128)

        # The oldest accessed tile should have been evicted
        oldest_tile = tiles_accessed[0]
        self.assertNotIn(oldest_tile, cache)

        # The most recently accessed tile should still be in the cache
        newest_tile = tiles_accessed[-1]
        self.assertIn(newest_tile, cache)

    def test_different_artifact_identity_does_not_hit_stale_cache(self):
        """Keys are tied to fingerprint, so a different artifact identity never hits old tiles."""
        active = elevation.current()
        cache = active._cache
        cache.clear()

        # Prime cache with one tile
        active.cell_elevation(0, 0)
        self.assertIn((active.fingerprint, 0, 0), cache)

        # Check with a different fingerprint
        different_fp = "0" * 64
        self.assertNotIn((different_fp, 0, 0), cache)
        self.assertIsNone(cache.get((different_fp, 0, 0)))

    def test_admission_rejection_on_missing_or_corrupt_elevation_retains_prior_bundle(self):
        """If elevation is missing or corrupt, load_candidate fails and prior bundle survives."""
        publish_shipped_map_world()
        baseline_world = runtime.current()
        baseline_elevation = elevation.current()

        # 1. Missing elevation artifact
        with mock.patch("world.maps.elevation.load_elevation", side_effect=ElevationDocumentError("missing")):
            with self.assertRaises(MapWorldError) as caught:
                runtime.load_candidate()
            self.assertIn("elevation artifact rejected", str(caught.exception))

        # Prior bundle is still intact
        self.assertEqual(runtime.current(), baseline_world)
        self.assertEqual(elevation.current(), baseline_elevation)

        # 2. Stale elevation artifact (source signature mismatch)
        stale_metadata = ElevationMetadata(
            format_version=ELEVATION_FORMAT_VERSION,
            algorithm_version=ELEVATION_ALGORITHM_VERSION,
            source_signature=[{"digest": "old", "identity": "content/maps/continent.yaml"}],
            fingerprint="fake",
            frame_cells=2700,
            tile_cells=64,
            data_sha256="fake_sha",
        )
        fake_runtime = elevation.ElevationRuntime(stale_metadata, {})
        with mock.patch("world.maps.elevation.load_elevation", return_value=fake_runtime):
            with self.assertRaises(MapWorldError) as caught:
                runtime.load_candidate()
            self.assertIn("elevation artifact is not current", str(caught.exception))

        # Prior bundle is still intact
        self.assertEqual(runtime.current(), baseline_world)
        self.assertEqual(elevation.current(), baseline_elevation)


if __name__ == "__main__":
    unittest.main()
