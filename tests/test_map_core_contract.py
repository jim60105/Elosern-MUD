"""Contract test: the pure map core is installed, locked and game-import free.

The package at ``packages/map-core`` owns the settlement graph, the metric
transforms and the deterministic terrain rules. This repository-level check
establishes the boundary the package claims:

* the game environment imports the *installed* distribution (its own lock, not a
  path guess), and the game's real adapters read their declarations through it;
* the package's modules import and calculate with Evennia, Django and ``world``
  absent, using only their own source tree; and
* the root project declares and locks the local dependency.

Mechanism tests for the calculations themselves live in
``packages/map-core/tests``.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "packages" / "map-core"

ISOLATED_CALCULATION = textwrap.dedent(
    """
    import json
    import sys

    FORBIDDEN = {"evennia", "django", "twisted", "world", "typeclasses"}

    class Blocker:
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in FORBIDDEN:
                raise AssertionError(f"map core imported forbidden namespace {name}")
            return None

    sys.meta_path.insert(0, Blocker())
    sys.path.insert(0, sys.argv[1])

    from elosern_map_core.geometry import cell_center_m, local_to_world_m
    from elosern_map_core.sparse import (
        SparseNode,
        SparseRoad,
        SparseSettlementGraph,
    )
    from elosern_map_core.terrain import (
        REGION_KEYS,
        TerrainDefinition,
        region_for_coordinates,
    )

    def world(forest_row, coastal):
        return TerrainDefinition(
            frame_cells=20,
            mainland_boundary_km=((0, 0), (20, 0), (20, 20), (0, 20)),
            forest_edge=((0, forest_row), (19, forest_row)),
            waterway_routes={"border_river": ((10, 6), (0, 6))},
            waterway_fords={},
            border_river_key="border_river",
            ridge_base_x=5,
            ridge_period=5,
            ridge_step=1,
            ridge_min_x=0,
            ridge_max_x=19,
            ridge_north_limit=19,
            ridge_passes=((0, 0),),
            coastal_y_max=coastal,
            mountain_corridor_half_width=1,
            region_flavors={key: ("x", "y") for key in REGION_KEYS},
        )

    cosy = world(12, 3)
    roomy = world(17, 8)
    graph = SparseSettlementGraph(
        "core",
        [
            SparseNode("start", 0, 0, {"key": "start"}),
            SparseNode("end", 0, 500, {"key": "end"}),
        ],
        [SparseRoad("start>end", "start", "end")],
    )
    route = graph.route("start", "end")
    print(
        json.dumps(
            {
                "cell_center": cell_center_m((2, 3)),
                "world_point": local_to_world_m((2, 3), (10, 20), (30, 40)),
                "route_ids": [edge.destination.node_id for edge in route],
                "route_length": sum(edge.length for edge in route),
                "region_a": region_for_coordinates(cosy, 8, 14),
                "region_b": region_for_coordinates(roomy, 8, 14),
                "region_a_again": region_for_coordinates(cosy, 8, 14),
            }
        )
    )
    """
)


def _run_isolated(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-I", "-c", ISOLATED_CALCULATION, *arguments],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
    )


class InstalledDistributionTests(unittest.TestCase):
    def test_the_game_environment_resolves_the_locked_package(self):
        # ``-I`` drops the current directory and the user site from ``sys.path``,
        # so an import here resolves through the synced environment only.
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                "import importlib.metadata as m; import elosern_map_core as c;"
                "print(m.version('elosern-map-core')); print(c.__name__)",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.split(), ["0.1.0", "elosern_map_core"])

    def test_game_adapters_read_their_declarations_through_the_core(self):
        from elosern_map_core.geometry import cell_center_m
        from elosern_map_core.sparse import SparseSettlementGraph
        from world.lore.anchors import (
            ANCHOR_GEOGRAPHY_REGISTRY,
            LOCAL_FRAME_ANCHOR_REGISTRY,
            world_position_m,
        )
        from world.maps.map_data import SETTLEMENT_GRAPHS

        self.assertTrue(SETTLEMENT_GRAPHS)
        for graph in SETTLEMENT_GRAPHS.values():
            self.assertIsInstance(graph, SparseSettlementGraph)
            self.assertGreaterEqual(len(graph.nodes), 2)

        # The registry-bound transform must be the core transform applied to
        # the registry's own values: the local anchor point lands on the anchor
        # cell centre, and any offset shifts by exactly that offset.
        for anchor_key in sorted(LOCAL_FRAME_ANCHOR_REGISTRY):
            with self.subTest(anchor=anchor_key):
                center = cell_center_m(ANCHOR_GEOGRAPHY_REGISTRY[anchor_key].cell)
                frame = LOCAL_FRAME_ANCHOR_REGISTRY[anchor_key]
                anchor_east, anchor_north = frame.local_anchor_m
                self.assertEqual(world_position_m(anchor_key, frame.local_anchor_m), center)
                self.assertEqual(
                    world_position_m(anchor_key, (anchor_east + 30, anchor_north - 40)),
                    (center[0] + 30, center[1] - 40),
                )

    def test_root_project_declares_and_locks_the_local_dependency(self):
        project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
        self.assertIn("elosern-map-core", project["project"]["dependencies"])
        self.assertEqual(
            project["tool"]["uv"]["sources"]["elosern-map-core"],
            {"path": "packages/map-core", "editable": True},
        )

        lock = tomllib.loads((REPO_ROOT / "uv.lock").read_text())
        entries = [
            entry for entry in lock["package"] if entry["name"] == "elosern-map-core"
        ]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["version"], "0.1.0")
        self.assertEqual(entries[0]["source"], {"editable": "packages/map-core"})


class ImportBoundaryTests(unittest.TestCase):
    def test_core_calculations_run_with_evennia_django_and_world_absent(self):
        completed = _run_isolated(str(PACKAGE_ROOT))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        observed = json.loads(completed.stdout)

        self.assertEqual(observed["cell_center"], [2500, 3500])
        self.assertEqual(observed["world_point"], [2520, 3520])
        self.assertEqual(observed["route_ids"], ["end"])
        self.assertEqual(observed["route_length"], 500)
        # Two independently built worlds classify the same cell differently, and
        # the first world's answer is stable after the second ran.
        self.assertNotEqual(observed["region_a"], observed["region_b"])
        self.assertEqual(observed["region_a"], observed["region_a_again"])

if __name__ == "__main__":
    unittest.main()
