"""Authoritative static reference-context export and independent freshness tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import django
from django.db.backends.base.base import BaseDatabaseWrapper

from elosern_map_core.documents import QualifiedRef
from elosern_map_core.reference_context import (
    DELETION_ALLOWED,
    DELETION_REFUSED_REFERENCED,
    DELETION_REFUSED_UNAVAILABLE,
    EXPORTER_VERSION,
    SCHEMA_VERSION,
    STATUS_CHANGED,
    STATUS_CURRENT,
    STATUS_INCOMPATIBLE,
    STATUS_MEMBERSHIP_MISMATCH,
    STATUS_MISSING,
    ReferenceContextDocument,
    ReferenceContextFreshness,
    check_reference_context_freshness,
    check_workspace_freshness,
    decode_reference_context,
    encode_reference_context,
)
from tools import map_reference_context as exporter


def _forbid_db(*args, **kwargs):
    raise RuntimeError("Live database access is fatal during static reference export")


class FatalDatabaseAccessTests(unittest.TestCase):
    """The exporter must never read or create a live database connection."""

    def test_real_registry_construction_with_live_db_access_forbidden(self):
        # Patch connect, cursor, and _cursor on BaseDatabaseWrapper
        with (
            mock.patch.object(BaseDatabaseWrapper, "connect", _forbid_db),
            mock.patch.object(BaseDatabaseWrapper, "cursor", _forbid_db),
            mock.patch.object(BaseDatabaseWrapper, "_cursor", _forbid_db),
        ):
            doc = exporter.build_reference_context_document()
            self.assertIsInstance(doc, ReferenceContextDocument)
            self.assertEqual(doc.schema_version, SCHEMA_VERSION)
            self.assertEqual(doc.exporter_version, EXPORTER_VERSION)
            self.assertTrue(doc.external_identifiers)
            self.assertTrue(doc.incoming_references)

    def test_export_in_subprocess_with_guarded_database(self):
        script = """
from tools import map_reference_context as exp
exp._bootstrap()

# Install fatal guard on all database operations
from unittest.mock import patch
from django.db.backends.base.base import BaseDatabaseWrapper

def _fatal(*args, **kwargs):
    raise RuntimeError("Fatal DB access")

with patch.object(BaseDatabaseWrapper, "connect", _fatal), patch.object(BaseDatabaseWrapper, "cursor", _fatal), patch.object(BaseDatabaseWrapper, "_cursor", _fatal):
    text = exp.export_reference_context_text()
    assert len(text) > 1000

    # Also prove that any attempt to touch DB would fail
    from evennia.server.models import ServerConfig
    try:
        ServerConfig.objects.count()
        failed = False
    except RuntimeError:
        failed = True
    assert failed, "database guard did not catch direct query"

print("SUBPROCESS_SUCCESS")
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=exporter.REPOSITORY_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertIn("SUBPROCESS_SUCCESS", result.stdout, msg=f"stdout={result.stdout}\nstderr={result.stderr}")
        self.assertEqual(result.returncode, 0)


class DeterministicExportTests(unittest.TestCase):
    """Two exports from identical sources must be byte-for-byte identical."""

    def test_reproducible_byte_identical_output(self):
        first = exporter.export_reference_context_text()
        second = exporter.export_reference_context_text()
        self.assertEqual(first, second)

    def test_identifiers_and_incoming_references_structure(self):
        doc = exporter.build_reference_context_document()
        # Verify required identifier families exist and are sorted
        for family in ("scene_archetypes", "quest_definitions", "nations", "titles", "service_hosts", "races"):
            self.assertIn(family, doc.external_identifiers)
            identifiers = doc.external_identifiers[family]
            self.assertGreater(len(identifiers), 0)
            self.assertEqual(identifiers, tuple(sorted(identifiers)))

        # Verify incoming references are non-empty and have valid provenance
        self.assertGreater(len(doc.incoming_references), 0)
        for target_key, refs in doc.incoming_references.items():
            self.assertTrue(target_key.startswith(("interior_room:", "settlement_node:", "location:")))
            for ref in refs:
                self.assertTrue(ref.source)
                self.assertTrue(ref.source_file)
                self.assertTrue(ref.source_domain)
                self.assertIsInstance(ref.target, QualifiedRef)


class GeometryExclusionTests(unittest.TestCase):
    """Moving a settlement node coordinate alone does not invalidate the external reference context."""

    def test_coordinate_change_alone_leaves_fingerprint_and_targets_identical(self):
        before_doc = exporter.build_reference_context_document()

        from world.maps import map_data
        settlement_snapshot = map_data.current()
        first_graph_key = next(iter(settlement_snapshot.graphs))
        graph = settlement_snapshot.graphs[first_graph_key]
        first_node_id = next(iter(graph.nodes))
        orig_node = graph.nodes[first_node_id]

        # Simulate moving that node's spatial coordinate
        from elosern_map_core.sparse import SparseNode
        moved_node = SparseNode(
            node_id=orig_node.node_id,
            x=orig_node.x + 50,
            y=orig_node.y + 50,
            prototype=orig_node.prototype,
        )
        new_nodes = dict(graph.nodes)
        new_nodes[first_node_id] = moved_node

        from elosern_map_core.sparse import SparseSettlementGraph
        new_graph = SparseSettlementGraph(
            map_id=graph.map_id,
            nodes=new_nodes.values(),
            roads=graph.roads,
            options=graph.options,
            exit_prototype=graph.exit_prototype,
        )
        new_graphs = dict(settlement_snapshot.graphs)
        new_graphs[first_graph_key] = new_graph

        from dataclasses import replace
        moved_snapshot = replace(settlement_snapshot, graphs=new_graphs)

        with mock.patch("world.maps.map_data._PUBLISHED", moved_snapshot):
            after_doc = exporter.build_reference_context_document()

        # The external closure and fingerprint must be completely unchanged
        self.assertEqual(before_doc.fingerprint, after_doc.fingerprint)
        self.assertEqual(before_doc.source_manifest, after_doc.source_manifest)
        self.assertEqual(before_doc.incoming_references, after_doc.incoming_references)


class FreshnessAndMutationTests(unittest.TestCase):
    """External closure additions, removals, modifications, or version mismatches invalidate freshness."""

    def setUp(self):
        self.doc = exporter.build_reference_context_document()
        self.current_hashes = dict(self.doc.source_manifest)
        self.discovered = list(self.doc.source_manifest.keys())

    def test_current_when_sources_match(self):
        freshness = check_reference_context_freshness(
            self.doc,
            self.current_hashes,
            discovered_files=self.discovered,
        )
        self.assertTrue(freshness.current)
        self.assertEqual(freshness.status, STATUS_CURRENT)

    def test_synthetic_external_file_addition_invalidates_membership(self):
        added_hashes = dict(self.current_hashes)
        added_hashes["world/lore/synthetic_added_file.py"] = "abcdef123456"
        discovered = self.discovered + ["world/lore/synthetic_added_file.py"]

        freshness = check_reference_context_freshness(
            self.doc,
            added_hashes,
            discovered_files=discovered,
        )
        self.assertFalse(freshness.current)
        self.assertEqual(freshness.status, STATUS_MEMBERSHIP_MISMATCH)
        self.assertTrue(any("synthetic_added_file.py" in r for r in freshness.reasons))

    def test_synthetic_external_file_removal_invalidates_membership(self):
        removed_hashes = dict(self.current_hashes)
        first_file = self.discovered[0]
        del removed_hashes[first_file]
        discovered = [f for f in self.discovered if f != first_file]

        freshness = check_reference_context_freshness(
            self.doc,
            removed_hashes,
            discovered_files=discovered,
        )
        self.assertFalse(freshness.current)
        self.assertEqual(freshness.status, STATUS_MISSING)

    def test_tracked_file_content_modification_invalidates_freshness(self):
        changed_hashes = dict(self.current_hashes)
        first_file = self.discovered[0]
        changed_hashes[first_file] = "ffff0000ffff0000"

        freshness = check_reference_context_freshness(
            self.doc,
            changed_hashes,
            discovered_files=self.discovered,
        )
        self.assertFalse(freshness.current)
        self.assertEqual(freshness.status, STATUS_CHANGED)
        self.assertTrue(any(first_file in r for r in freshness.reasons))

    def test_version_bump_reports_incompatible(self):
        doc_incompatible = ReferenceContextDocument(
            schema_version=SCHEMA_VERSION,
            exporter_version=EXPORTER_VERSION + 1,
            external_identifiers=self.doc.external_identifiers,
            incoming_references=self.doc.incoming_references,
            source_manifest=self.doc.source_manifest,
            discovery_rules=self.doc.discovery_rules,
            fingerprint=self.doc.fingerprint,
        )
        freshness = check_reference_context_freshness(
            doc_incompatible,
            self.current_hashes,
            discovered_files=self.discovered,
        )
        self.assertFalse(freshness.current)
        self.assertEqual(freshness.status, STATUS_INCOMPATIBLE)


class CliCheckEnforcementTests(unittest.TestCase):
    """The --check CLI option enforces freshness and rejects stale output without rewriting."""

    def test_check_passes_on_committed_file(self):
        code = exporter.main(["--check"])
        self.assertEqual(code, 0)

    def test_check_fails_without_modifying_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_path = Path(tmp_dir) / "missing-reference-context.json"
            code = exporter.main(["--check", "--output", str(missing_path)])
            self.assertEqual(code, 1)
            self.assertFalse(missing_path.exists())

    def test_check_fails_without_modifying_stale_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            stale_path = Path(tmp_dir) / "stale-reference-context.json"
            stale_content = '{"schema_version": 1, "stale": true}\n'
            stale_path.write_text(stale_content, encoding="utf-8")

            code = exporter.main(["--check", "--output", str(stale_path)])
            self.assertEqual(code, 1)
            # Must NOT rewrite the stale file
            self.assertEqual(stale_path.read_text(encoding="utf-8"), stale_content)


class ConsumerIndependenceTests(unittest.TestCase):
    """Consumer-side freshness checking works without Evennia, Django, or game modules."""

    def test_freshness_checking_without_game_modules_imported(self):
        script = """
import sys
# Confirm Evennia and Django are not imported
assert "evennia" not in sys.modules
assert "django" not in sys.modules
assert "world" not in sys.modules

from elosern_map_core.reference_context import (
    decode_reference_context,
    check_reference_context_freshness,
    STATUS_CURRENT,
)
from pathlib import Path

doc_path = Path("content/map-reference-context.json")
content = doc_path.read_text(encoding="utf-8")
doc = decode_reference_context(content)

# Build file hashes purely from disk
manifest = doc.source_manifest
hashes = {}
import hashlib
for path_str in manifest:
    p = Path(path_str)
    if p.is_file():
        hashes[path_str] = hashlib.sha256(p.read_bytes()).hexdigest()

freshness = check_reference_context_freshness(doc, hashes, discovered_files=list(manifest.keys()))
assert freshness.current, f"expected current, got {freshness.status}: {freshness.reasons}"
assert "evennia" not in sys.modules
assert "django" not in sys.modules
assert "world" not in sys.modules
print("INDEPENDENT_CHECK_OK")
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=exporter.REPOSITORY_ROOT,
            capture_output=True,
            text=True,
        )
        self.assertIn("INDEPENDENT_CHECK_OK", result.stdout, msg=f"stdout={result.stdout}\nstderr={result.stderr}")
        self.assertEqual(result.returncode, 0)


class DeletionSafetyAndUndoRefusalTests(unittest.TestCase):
    """External source changes before deletion cause destructive commands and undo-remove to refuse."""

    def setUp(self):
        self.doc = exporter.build_reference_context_document()
        self.current_hashes = dict(self.doc.source_manifest)

    def test_stale_external_context_blocks_deletion_and_undo_remove(self):
        # Scenario: an external dependency changes, but the index on disk / in browser was not refreshed
        changed_hashes = dict(self.current_hashes)
        some_source = next(iter(self.current_hashes))
        changed_hashes[some_source] = "modified_hash_0000000000"

        freshness = check_reference_context_freshness(self.doc, changed_hashes)
        self.assertFalse(freshness.current)

        # Attempt to delete an unreferenced object
        unreferenced_target = QualifiedRef("settlement_node", "capital_altoria", "free_unreferenced_node")
        decision = self.doc.check_deletion_safety(unreferenced_target, freshness)

        # Must refuse because external context is unavailable
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status, DELETION_REFUSED_UNAVAILABLE)
        self.assertTrue(any("unavailable" in r for r in decision.reasons))

    def test_referenced_target_refuses_deletion_even_when_fresh(self):
        freshness = ReferenceContextFreshness(current=True, status=STATUS_CURRENT, reasons=())
        # Pick a target that is referenced by a place
        target_room = QualifiedRef("interior_room", "altoria_tailor", "altoria_tailor")
        decision = self.doc.check_deletion_safety(target_room, freshness)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status, DELETION_REFUSED_REFERENCED)
        self.assertTrue(len(decision.incoming_references) > 0)
        self.assertTrue(any("place:altoria_tailor" in r for r in decision.reasons))

    def test_unreferenced_target_allows_deletion_when_fresh(self):
        freshness = ReferenceContextFreshness(current=True, status=STATUS_CURRENT, reasons=())
        unreferenced = QualifiedRef("interior_room", "unreferenced_interior", "unreferenced_room")
        decision = self.doc.check_deletion_safety(unreferenced, freshness)

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.status, DELETION_ALLOWED)
        self.assertEqual(decision.reasons, ())
