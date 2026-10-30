"""Contract test: elevation generation is game-free and runtime is extra-free.

The executed evidence runs the real generator in a subprocess with every game
namespace blocked, proves repeat-byte determinism and the sea/band/tier
postconditions on a synthetic frame, and proves that importing the package's
runtime surface never pulls the generator or NumPy/SciPy.

The requirement annotation targets the canonical requirement synced from the
wilderness-elevation-generation delta spec.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]

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
    from elosern_map_core import geometry, partition_codec, sparse, terrain

    assert not hasattr(elosern_map_core, "generate_elevation")
    assert not hasattr(elosern_map_core, "elevation")
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
        "elevation-shapes-reject-invalid-candidates"
    )
    def test_package_runtime_surface_imports_without_numpy_scipy_or_the_generator(
        self,
    ):
        result = _run_probe(_RUNTIME_PROBE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "[]")


if __name__ == "__main__":
    unittest.main()
