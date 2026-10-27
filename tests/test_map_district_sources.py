"""Repository contract: districts are authored only in content/maps/districts.yaml.

The district domain is an authored YAML document. This check fails when a
Python roster, table or import of one comes back, and it proves the shipped
document is the one the core discovers and parses: structural faults reject the
candidate, terrain faults stay loadable work in progress, and runtime adoption
rejects them. Synthetic candidates carry the mechanism checks; no shipped row,
name or count is pinned here.
"""

from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path
from unittest import mock

from elosern_map_core.authoring import AuthoringError
from elosern_map_core.diagnostics import SEMANTIC, STRUCTURE
from elosern_map_core.references import ReferenceIndex
from elosern_map_core.sources import discover_source_paths
from tools.spec_traceability import covers_requirement
from world.lore import map_districts
from world.lore.map_districts import (
    DISTRICTS_PATH,
    DistrictError,
    DistrictNotLoaded,
    build_districts,
    diagnose_districts,
    parse_districts_document,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = ("commands", "server", "typeclasses", "web", "world", "tools", "tests")
RETIRED_SYMBOL = "MAP_DISTRICT" + "_REGISTRY"
LANDMARK_DOMAINS = ("settlement_node", "wilderness_cell", "location")


def _python_files():
    for root in SOURCE_ROOTS:
        for path in sorted((REPO_ROOT / root).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            yield path


def _cell(x, y):
    return {
        "domain": "wilderness_cell",
        "map_id": None,
        "object_id": None,
        "cell": {"cell_x": x, "cell_y": y},
    }


def _row(name, landmark, kind="voronoi", region_key=None):
    return {
        "district_name_zh": f"{name}區",
        "landmark_name_zh": f"{name}碑",
        "landmark": landmark,
        "kind": kind,
        "region_key": region_key,
    }


def _node_ref(map_id, object_id):
    return {
        "domain": "settlement_node",
        "map_id": map_id,
        "object_id": object_id,
        "cell": None,
    }


def _text(rows):
    return json.dumps(
        {"version": 1, "kind": "districts", "id": "districts", "districts": rows},
        ensure_ascii=False,
    )


class DistrictAuthorityTests(unittest.TestCase):
    def test_no_python_district_roster_or_table_survives(self):
        offenders = []
        for path in _python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            relative = path.relative_to(REPO_ROOT)
            for node in tree.body:
                targets = []
                if isinstance(node, ast.Assign):
                    targets = [
                        target.id
                        for target in node.targets
                        if isinstance(target, ast.Name)
                    ]
                elif isinstance(node, ast.AnnAssign) and isinstance(
                    node.target, ast.Name
                ):
                    targets = [node.target.id]
                offenders.extend(
                    f"{relative}: {name}"
                    for name in targets
                    if name == RETIRED_SYMBOL
                )
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [alias.name for alias in node.names]
                offenders.extend(
                    f"{relative}: {name}"
                    for name in names
                    if name == RETIRED_SYMBOL
                )
        self.assertEqual(offenders, [])

    def test_the_document_is_a_discovered_source(self):
        paths = discover_source_paths(REPO_ROOT)
        self.assertIn(DISTRICTS_PATH, paths)
        self.assertEqual(paths, tuple(sorted(paths)))
        text = (REPO_ROOT / DISTRICTS_PATH).read_text(encoding="utf-8")
        document = parse_districts_document(text)
        self.assertEqual(document.relative_path, DISTRICTS_PATH)
        self.assertEqual(document.identity, "districts")
        self.assertTrue(document.districts)
        for key, district in document.districts.items():
            with self.subTest(district=key):
                self.assertEqual(district.district_id, key)
                self.assertIn(district.landmark.domain, LANDMARK_DOMAINS)
                if district.landmark.domain != "wilderness_cell":
                    self.assertIsNone(district.landmark.cell)
                if district.kind == "region":
                    self.assertIsNotNone(district.region_key)
                else:
                    self.assertIsNone(district.region_key)

    def test_the_document_round_trips_with_a_stable_identity(self):
        text = (REPO_ROOT / DISTRICTS_PATH).read_text(encoding="utf-8")
        once = parse_districts_document(text)
        again = parse_districts_document(text)
        self.assertEqual(once.fingerprint, again.fingerprint)
        self.assertEqual(tuple(once.districts), tuple(again.districts))
        self.assertEqual(
            {
                key: district.landmark
                for key, district in once.districts.items()
            },
            {
                key: district.landmark
                for key, district in again.districts.items()
            },
        )


class _Terrain:
    wilderness_name = "testland"
    max_cell = (99, 99)
    region_keys = frozenset({"plain"})

    def is_land(self, cell):
        return cell[0] < 90

    def is_walkable(self, cell):
        return self.is_land(cell)

    def is_reachable(self, cell):
        return self.is_walkable(cell)

    def region_of(self, cell):
        return "plain"

    def grid_site(self, map_key, xy):
        return None


class DistrictCandidateBoundaryTests(unittest.TestCase):
    def _build(self, rows, index=None):
        return build_districts(
            parse_districts_document(_text(rows)),
            terrain=_Terrain(),
            index=index if index is not None else ReferenceIndex.build(),
        )

    def test_structural_faults_reject_the_candidate(self):
        rows = {
            "ghost_seed": _row("合成幽", _node_ref("t_map", "nowhere")),
            "bad_region": _row("合成異", _cell(20, 20), "region", "moor"),
        }
        with self.assertRaises(DistrictError) as caught:
            self._build(rows)
        self.assertEqual(
            {item.category for item in caught.exception.diagnostics}, {STRUCTURE}
        )
        self.assertEqual(
            {item.object_id for item in caught.exception.diagnostics},
            {"ghost_seed", "bad_region"},
        )

    def test_terrain_faults_load_as_work_in_progress_and_reject_adoption(self):
        rows = {"sea_seed": _row("合成海", _cell(95, 95))}
        diagnostics = diagnose_districts(
            parse_districts_document(_text(rows)).districts,
            terrain=_Terrain(),
            index=ReferenceIndex.build(),
        )
        self.assertEqual(
            [(item.code, item.category) for item in diagnostics],
            [("landmark_in_sea", SEMANTIC)],
        )
        candidate = self._build(rows)
        self.assertEqual(
            [item.code for item in candidate.diagnostics], ["landmark_in_sea"]
        )
        with mock.patch.object(map_districts, "_PUBLISHED", None):
            baseline = self._build({"plain_seed": _row("合成平", _cell(10, 10))})
            map_districts.publish(baseline)
            with self.assertRaises(DistrictError):
                map_districts.publish(candidate)
            self.assertIs(map_districts.current(), baseline)

    def test_duplicate_and_misfiled_documents_are_structural(self):
        duplicate = _text(
            {"west_seed": _row("合成西", _cell(10, 10))}
        ).replace(
            '"west_seed":',
            '"west_seed": {},\n    "west_seed":',
            1,
        )
        with self.assertRaises(AuthoringError):
            parse_districts_document(duplicate)
        for row in (
            _row("odd_kind", _cell(10, 10), "square"),
            _row("no_region", _cell(10, 10), "region"),
            _row("loose_region", _cell(10, 10), "voronoi", "plain"),
        ):
            with self.subTest(key=next(iter(row))):
                with self.assertRaises(AuthoringError):
                    parse_districts_document(_text({next(iter(row)): row}))

    def test_runtime_reads_require_a_published_document(self):
        with mock.patch.object(map_districts, "_PUBLISHED", None):
            with self.assertRaises(DistrictNotLoaded):
                map_districts.current()


if __name__ == "__main__":
    unittest.main()
