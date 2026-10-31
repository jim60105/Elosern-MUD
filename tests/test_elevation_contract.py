"""Contract test: elevation generation is game-free and runtime is extra-free.

The executed evidence runs the real generator in a subprocess with every game
namespace blocked, proves repeat-byte determinism and the sea/band/tier
postconditions on a synthetic frame, and proves that importing the package's
runtime surface never pulls the generator or NumPy/SciPy.

The publication contract drives the repository's own regeneration entry point
(``.agents/skills/map-data-authoring/scripts/regenerate_elevation.py``) over a
synthetic authored world: the published artifact stays within the byte budget,
its fingerprint moves with the geography, the configuration and the algorithm
version, and a refusal never replaces prior bytes nor leaves a temporary
behind.

The requirement annotation targets the canonical requirement synced from the
wilderness-elevation-generation delta spec.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from elosern_map_core.elevation import DEFAULT_ELEVATION_CONFIG
from elosern_map_core.elevation_codec import (
    ELEVATION_ALGORITHM_VERSION,
    MAX_ELEVATION_BYTES,
    read_elevation_metadata,
)
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_TESTS = REPO_ROOT / "packages" / "map-core" / "tests"
AUTHORING_SCRIPTS = REPO_ROOT / ".agents" / "skills" / "map-data-authoring" / "scripts"

_GENERATION_PROBE = textwrap.dedent(
    """
    import json
    import sys

    BLOCKED = {"world", "evennia", "django", "twisted", "typeclasses"}

    class Blocker:
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in BLOCKED:
                raise AssertionError(f"elevation imported forbidden namespace {name}")
            return None

    sys.meta_path.insert(0, Blocker())
    loaded = {name.split(".")[0] for name in sys.modules}
    assert not (BLOCKED & loaded), sorted(BLOCKED & loaded)

    import numpy as np

    from elosern_map_core.documents import ElevationShapeDeclaration
    from elosern_map_core.elevation import (
        ELEVATION_BAND_MAX,
        PROMINENCE_TIER_MAX,
        generate_elevation,
    )
    from elosern_map_core.terrain import REGION_KEYS, TerrainDefinition

    frame = 24
    terrain = TerrainDefinition(
        frame_cells=frame,
        mainland_boundary_km=((0, 0), (frame, 0), (frame, 18), (0, 18)),
        forest_edge=((0, 15), (frame - 1, 15)),
        waterway_routes={"border_river": ((8, 10), (0, 10))},
        waterway_fords={},
        border_river_key="border_river",
        ridge_base_x=12,
        ridge_period=4,
        ridge_step=1,
        ridge_min_x=0,
        ridge_max_x=frame - 1,
        ridge_north_limit=frame - 1,
        ridge_passes=((0, 1),),
        coastal_y_max=3,
        mountain_corridor_half_width=2,
        region_flavors={key: (key,) for key in REGION_KEYS},
    )
    shapes = (
        ElevationShapeDeclaration(
            shape="circle",
            op="flatten",
            centre=(6, 6),
            radius=2,
            target_band=9,
            feather=1,
        ),
    )

    first = generate_elevation(terrain, shapes)
    second = generate_elevation(terrain, shapes)

    assert first.bands.dtype == np.uint8
    assert first.tiers.dtype == np.uint8
    assert first.bands.shape == (frame, frame)
    assert first.tiers.shape == (frame, frame)
    assert int(first.bands.max()) <= ELEVATION_BAND_MAX
    assert int(first.tiers.max()) <= PROMINENCE_TIER_MAX
    assert first.bands[6, 6] == 9
    sea_start = 18
    assert np.all(first.bands[sea_start:, :] == 0)
    assert np.all(first.tiers[sea_start:, :] == 0)
    assert first.bands.tobytes() == second.bands.tobytes()
    assert first.tiers.tobytes() == second.tiers.tobytes()
    assert not first.bands.flags.writeable
    assert not first.tiers.flags.writeable

    leaked = sorted(
        name for name in sys.modules if name.split(".")[0] in BLOCKED
    )
    print(json.dumps(leaked))
    """
)

_RUNTIME_PROBE = textwrap.dedent(
    """
    import json
    import sys

    BLOCKED = {"numpy", "scipy", "tools"}

    class Blocker:
        def find_spec(self, name, path=None, target=None):
            root = (
                name
                if name == "elosern_map_core.elevation"
                else name.split(".")[0]
            )
            if root in BLOCKED:
                raise AssertionError(f"runtime imported forbidden namespace {name}")
            return None

    sys.meta_path.insert(0, Blocker())
    loaded = {name.split(".")[0] for name in sys.modules}
    assert not (BLOCKED & loaded), sorted(BLOCKED & loaded)

    import elosern_map_core
    from elosern_map_core import elevation_codec, geometry, partition_codec, sparse, terrain
    from world.maps import elevation

    assert not hasattr(elosern_map_core, "generate_elevation")
    assert not hasattr(elosern_map_core, "elevation")
    assert elevation_codec.ELEVATION_FORMAT_VERSION == 1
    assert elevation.DATA_PATH.name == "wilderness_elevation.json"
    assert terrain.REGION_KEYS
    assert geometry.METRES_PER_WILDERNESS_CELL == 1000
    assert partition_codec.FORMAT_VERSION
    assert sparse.compass_direction(1, 0) == "e"
    leaked = sorted(
        name
        for name in sys.modules
        if name.split(".")[0] in {"numpy", "scipy"}
        or name == "elosern_map_core.elevation"
    )
    print(json.dumps(leaked))
    """
)


def _run_probe(source: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    env.pop("DJANGO_SETTINGS_MODULE", None)
    return subprocess.run(
        [sys.executable, "-c", source],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


class GenerationIsGameFreeTests(unittest.TestCase):
    @covers_requirement(
        "wilderness-elevation-generation::"
        "elevation-generation-is-deterministic-and-physically-constrained"
    )
    def test_generation_is_deterministic_and_physically_constrained_without_game_code(
        self,
    ):
        result = _run_probe(_GENERATION_PROBE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "[]")


class RuntimeWithoutGenerationExtraTests(unittest.TestCase):
    @covers_requirement(
        "wilderness-elevation-authoring::"
        "elevation-shapes-reject-invalid-candidates",
        "wilderness-elevation-runtime::"
        "runtime-elevation-rejects-stale-or-corrupt-artifacts",
    )
    def test_package_runtime_surface_imports_without_numpy_scipy_or_the_generator(
        self,
    ):
        result = _run_probe(_RUNTIME_PROBE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "[]")


def _publisher_module():
    """Import the repository's real elevation regeneration entry point."""
    if str(AUTHORING_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(AUTHORING_SCRIPTS))
    import regenerate_elevation

    return regenerate_elevation


def _synthetic_workspace(root: Path) -> None:
    """Write a complete synthetic authored world under ``root``."""
    if str(PACKAGE_TESTS) not in sys.path:
        sys.path.insert(0, str(PACKAGE_TESTS))
    import authoring_fixtures as fixtures

    continent = fixtures.continent_data()
    for region in continent["regions"].values():
        # The game-adoption gate refuses a region without a scene archetype; the
        # value is never resolved because no reference context exists here.
        region["scene_archetype"] = "wilderness"
    documents = {
        "content/maps/continent.yaml": fixtures.yaml_text(continent),
        "content/maps/locations.yaml": fixtures.yaml_text(fixtures.locations_data()),
        "content/maps/districts.yaml": fixtures.yaml_text(fixtures.districts_data()),
        "content/maps/settlements/demo_map.yaml": fixtures.yaml_text(
            fixtures.settlement_data()
        ),
    }
    for relative_path, text in documents.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class ElevationPublicationContractTests(unittest.TestCase):
    """The publisher writes one bounded, source-identified artifact atomically."""

    def _publish(self, publisher, root: Path) -> tuple[int, str]:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = publisher.main(["regenerate_elevation.py", str(root)])
        return status, output.getvalue()

    def _metadata(self, target: Path):
        return read_elevation_metadata(target.read_text(encoding="utf-8"))

    def _temporary_artifacts(self, target: Path) -> list[str]:
        """Leftover atomic-write temporaries beside the published artifact."""
        return sorted(
            path.name
            for path in target.parent.iterdir()
            if path.name.startswith(".wilderness_elevation.")
        )

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "elevation-artifacts-are-bounded-and-source-identified"
    )
    def test_published_artifact_is_bounded_and_binds_every_declared_input(self):
        publisher = _publisher_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _synthetic_workspace(root)
            target = root / publisher.ELEVATION_PATH

            status, output = self._publish(publisher, root)
            self.assertEqual(status, 0, output)
            self.assertLessEqual(target.stat().st_size, MAX_ELEVATION_BYTES)
            baseline = self._metadata(target)

            continent = root / "content/maps/continent.yaml"
            continent.write_text(
                continent.read_text(encoding="utf-8") + "# authored edit\n",
                encoding="utf-8",
            )
            status, output = self._publish(publisher, root)
            self.assertEqual(status, 0, output)
            moved_geography = self._metadata(target)
            self.assertNotEqual(moved_geography.fingerprint, baseline.fingerprint)

            # The seed is the only configuration difference from ``baseline``,
            # so a fingerprint that ignored the configuration would match it.
            with mock.patch.object(
                publisher,
                "DEFAULT_ELEVATION_CONFIG",
                replace(DEFAULT_ELEVATION_CONFIG, seed=DEFAULT_ELEVATION_CONFIG.seed + 1),
            ):
                status, output = self._publish(publisher, root)
            self.assertEqual(status, 0, output)
            changed_config = self._metadata(target)
            self.assertNotEqual(changed_config.fingerprint, moved_geography.fingerprint)

            # The patch above ends, so this publish differs from
            # ``moved_geography`` by the algorithm version alone.
            with mock.patch.object(
                publisher,
                "ELEVATION_ALGORITHM_VERSION",
                ELEVATION_ALGORITHM_VERSION + 1,
            ):
                status, output = self._publish(publisher, root)
            self.assertEqual(status, 0, output)
            changed_algorithm = self._metadata(target)
            self.assertEqual(
                changed_algorithm.algorithm_version, ELEVATION_ALGORITHM_VERSION + 1
            )
            self.assertNotEqual(
                changed_algorithm.fingerprint, moved_geography.fingerprint
            )

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "elevation-artifacts-are-bounded-and-source-identified"
    )
    def test_prior_bytes_survive_a_budget_rejection_from_the_real_publisher(self):
        publisher = _publisher_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _synthetic_workspace(root)
            target = root / publisher.ELEVATION_PATH

            # Control: this workspace really reaches the publisher, so the
            # refusal below cannot pass by never publishing anything.
            status, _output = self._publish(publisher, root)
            self.assertEqual(status, 0)
            prior = target.read_bytes()
            self.assertTrue(prior)

            with mock.patch("elosern_map_core.elevation_codec.MAX_ELEVATION_BYTES", 50):
                status, output = self._publish(publisher, root)

            self.assertEqual(status, 1)
            self.assertIn("budget constraint", output)
            self.assertEqual(target.read_bytes(), prior)
            self.assertEqual(self._temporary_artifacts(target), [])

    @covers_requirement(
        "wilderness-elevation-runtime::"
        "elevation-artifacts-are-bounded-and-source-identified"
    )
    def test_publisher_refuses_when_the_source_changes_before_publication(self):
        publisher = _publisher_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _synthetic_workspace(root)
            target = root / publisher.ELEVATION_PATH
            target.parent.mkdir(parents=True, exist_ok=True)
            prior = b'{"prior": "bytes"}\n'
            target.write_bytes(prior)

            continent = root / "content/maps/continent.yaml"
            real_generate = publisher.generate_elevation

            def generate_then_edit_the_source(*args, **kwargs):
                rasters = real_generate(*args, **kwargs)
                continent.write_text(
                    continent.read_text(encoding="utf-8") + "# edited mid-run\n",
                    encoding="utf-8",
                )
                return rasters

            with mock.patch.object(
                publisher,
                "generate_elevation",
                side_effect=generate_then_edit_the_source,
            ):
                status, output = self._publish(publisher, root)

            self.assertEqual(status, 1)
            self.assertIn("continent source changed during generation", output)
            self.assertEqual(target.read_bytes(), prior)
            self.assertEqual(self._temporary_artifacts(target), [])


if __name__ == "__main__":
    unittest.main()
