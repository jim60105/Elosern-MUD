"""Repository contract: no Python settlement authority survives the cutover.

The settlement domain is authored YAML. This check fails when a retired
declaration module, an authored roster/table, or an import of one comes back, and
it proves the shipped document set is exactly what the game adapter discovers and
composes.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]
SETTLEMENTS_DIRECTORY = REPO_ROOT / "content" / "maps" / "settlements"
SOURCE_ROOTS = ("commands", "server", "typeclasses", "web", "world", "tools")
RETIRED_MODULES = ("world/maps/altoria_capital.py", "world/maps/village_ciaran.py")
RETIRED_SYMBOLS = ("NODE_IDS", "ROADS", "PROTOTYPES", "XYMAP_DATA")
RETIRED_IMPORTS = ("world.maps.altoria_capital", "world.maps.village_ciaran")


def _python_files():
    for root in SOURCE_ROOTS:
        for path in sorted((REPO_ROOT / root).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            yield path


class SettlementPythonAuthorityTests(unittest.TestCase):
    @covers_requirement(
        "sample-city-altoria::altoria-uses-approved-metric-outdoor-positions"
    )
    def test_retired_declaration_modules_are_gone(self):
        for relative_path in RETIRED_MODULES:
            with self.subTest(module=relative_path):
                self.assertFalse((REPO_ROOT / relative_path).exists())

    def test_no_source_imports_a_retired_settlement_module(self):
        offenders = []
        for path in _python_files():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                    names.extend(f"{node.module}.{alias.name}" for alias in node.names)
                for name in names:
                    if any(name.startswith(retired) for retired in RETIRED_IMPORTS):
                        offenders.append(f"{path.relative_to(REPO_ROOT)}: {name}")
        self.assertEqual(offenders, [])

    @covers_requirement(
        "map-settlement-sources::settlement-documents-own-complete-local-map-declarations"
    )
    def test_the_map_package_declares_no_settlement_data_table(self):
        offenders = []
        for path in sorted((REPO_ROOT / "world" / "maps").rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                targets = []
                if isinstance(node, ast.Assign):
                    targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    targets = [node.target.id]
                offenders.extend(
                    f"{path.relative_to(REPO_ROOT)}: {name}"
                    for name in targets
                    if name in RETIRED_SYMBOLS
                )
        self.assertEqual(offenders, [])


class SettlementDocumentSetTests(unittest.TestCase):
    @covers_requirement(
        "map-settlement-sources::settlement-documents-own-complete-local-map-declarations"
    )
    def test_every_discovered_document_composes_and_binds_one_location(self):
        from world.maps import map_data

        snapshot = map_data.load_settlements()
        discovered = sorted(path.stem for path in SETTLEMENTS_DIRECTORY.glob("*.yaml"))
        self.assertEqual(sorted(snapshot.settlements), discovered)
        self.assertEqual(sorted(snapshot.graphs), discovered)
        self.assertEqual(
            len(snapshot.anchor_placements), len(discovered)
        )
        self.assertEqual(
            sorted(placement.zcoord for placement in snapshot.anchor_placements.values()),
            discovered,
        )
        for document in snapshot.settlements.values():
            with self.subTest(settlement=document.identity):
                self.assertTrue(document.location_ref)
                self.assertIn(document.location_ref, snapshot.anchor_placements)
                self.assertIn(document.location_ref, snapshot.local_frame_anchors)

    def test_the_shipped_document_set_publishes_a_stable_identity(self):
        from world.maps import map_data

        once = map_data.load_settlements()
        again = map_data.load_settlements()
        self.assertEqual(once.identity, again.identity)
        self.assertEqual(
            sorted(once.fingerprints),
            sorted(again.fingerprints),
        )
        self.assertTrue(any(path.startswith("content/maps/settlements/") for path in once.fingerprints))
