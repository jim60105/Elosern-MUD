"""Authoritative static reference-context export and independent freshness tests."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import random
import tempfile
from types import SimpleNamespace
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
    MONSTER_SITE_KINDS,
    ReferenceContextDocument,
    ReferenceContextError,
    ReferenceContextFreshness,
    check_reference_context_freshness,
    check_workspace_freshness,
    decode_reference_context,
    encode_reference_context,
)
from tools import map_reference_context as exporter
from tools.spec_traceability import covers_requirement


def _forbid_db(*args, **kwargs):
    raise RuntimeError("Live database access is fatal during static reference export")


class FatalDatabaseAccessTests(unittest.TestCase):
    """The exporter must never read or create a live database connection."""

    @covers_requirement("map-external-reference-context::reference-export-records-authoritative-static-dependencies")
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
import django.db.backends.base.base as base
from django.db import OperationalError

# Install fatal guard before bootstrap and game imports
def _fatal(*args, **kwargs):
    raise OperationalError("Live DB access forbidden during bootstrap or export")

base.BaseDatabaseWrapper.connect = _fatal
base.BaseDatabaseWrapper.cursor = _fatal
base.BaseDatabaseWrapper._cursor = _fatal

from tools import map_reference_context as exp
exp._bootstrap()
text = exp.export_reference_context_text()
assert len(text) > 1000

# Also prove that direct queries during export are caught and fatal
from evennia.server.models import ServerConfig
try:
    ServerConfig.objects.count()
    failed = False
except OperationalError:
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


def _ns_member(variant_key: str, minimum: int, maximum: int) -> SimpleNamespace:
    return SimpleNamespace(variant_key=variant_key, minimum=minimum, maximum=maximum)


def _synthetic_registries():
    """Synthetic placement and species rows (attribute stand-ins only)."""

    species = {
        "synthetic_species_a": SimpleNamespace(display_name_zh="合成甲"),
        "synthetic_species_b": SimpleNamespace(display_name_zh="合成乙"),
    }
    variants = {
        "synthetic_variant_a": SimpleNamespace(species_key="synthetic_species_a", display_name_zh="合成甲變種"),
        "synthetic_variant_b": SimpleNamespace(species_key="synthetic_species_b", display_name_zh="合成乙變種"),
    }
    compositions = {
        "synthetic_group_pair": SimpleNamespace(
            members=(_ns_member("synthetic_variant_b", 1, 2), _ns_member("synthetic_variant_a", 1, 1))
        ),
        "synthetic_group_single": SimpleNamespace(members=(_ns_member("synthetic_variant_a", 2, 3),)),
    }

    def zone(key, rectangles):
        return SimpleNamespace(
            key=key,
            region_key="synthetic_region",
            rectangles=rectangles,
            pool=(
                SimpleNamespace(composition_key="synthetic_group_single", weight=3),
                SimpleNamespace(composition_key="synthetic_group_pair", weight=1),
            ),
            lower_density=1,
            upper_density=2,
            cell_capacity=3,
            wave_budget=4,
            recovery_delay=3600,
            replenishment_interval=600,
        )

    def site(key, **values):
        return SimpleNamespace(
            key=key,
            kind=values.get("kind", "camp"),
            region_key="synthetic_region",
            coordinates=(5, 6),
            capacity=2,
            one_shot=values["one_shot"],
            recover_after_ticks=values["recover"],
            individual_name_zh=values["name"],
            composition_key="synthetic_group_pair",
        )

    zones = {
        "synthetic_zone_b": zone("synthetic_zone_b", ((0, 1, 0, 1),)),
        "synthetic_zone_a": zone("synthetic_zone_a", ((2, 3, 4, 5), (6, 7, 8, 9))),
    }
    sites = {
        "synthetic_site_once": site("synthetic_site_once", kind="boss_site", one_shot=True, recover=None, name="合成個體"),
        "synthetic_site_again": site("synthetic_site_again", one_shot=False, recover=86400, name=None),
    }
    return {"zones": zones, "sites": sites, "compositions": compositions, "variants": variants, "species": species}


def _shuffled(registries, seed: int):
    rng = random.Random(seed)
    shuffled = {}
    for name, rows in registries.items():
        items = list(rows.items())
        rng.shuffle(items)
        shuffled[name] = dict(items)
    return shuffled


def _document_with(section) -> ReferenceContextDocument:
    return ReferenceContextDocument(
        schema_version=SCHEMA_VERSION,
        exporter_version=EXPORTER_VERSION,
        external_identifiers={},
        incoming_references={},
        source_manifest={},
        discovery_rules=(),
        fingerprint="synthetic",
        monster_spawns=section,
    )


class MonsterSpawnExportTests(unittest.TestCase):
    """The monster spawn section is exported deterministically with resolved names."""

    def setUp(self):
        self.registries = _synthetic_registries()
        self.section = exporter.build_monster_spawn_section(**self.registries)
        self.encoded = self.section.to_dict()

    @covers_requirement("map-external-reference-context::reference-export-carries-the-monster-spawn-section")
    def test_shuffled_registries_encode_byte_identically(self):
        expected = encode_reference_context(_document_with(self.section))
        for seed in (1, 2, 3):
            section = exporter.build_monster_spawn_section(**_shuffled(self.registries, seed))
            self.assertEqual(encode_reference_context(_document_with(section)), expected)

    @covers_requirement("map-external-reference-context::reference-export-carries-the-monster-spawn-section")
    def test_rows_sort_by_key_and_keep_authored_pool_and_member_order(self):
        self.assertEqual([row["key"] for row in self.encoded["zones"]], ["synthetic_zone_a", "synthetic_zone_b"])
        self.assertEqual([row["key"] for row in self.encoded["sites"]], ["synthetic_site_again", "synthetic_site_once"])
        zone = self.encoded["zones"][0]
        self.assertEqual(
            [entry["composition_key"] for entry in zone["pool"]], ["synthetic_group_single", "synthetic_group_pair"]
        )
        self.assertEqual([entry["weight"] for entry in zone["pool"]], [3, 1])
        self.assertEqual(
            [member["variant_key"] for member in zone["pool"][1]["members"]],
            ["synthetic_variant_b", "synthetic_variant_a"],
        )
        self.assertEqual(zone["rectangles"], [[2, 3, 4, 5], [6, 7, 8, 9]])

    @covers_requirement("map-external-reference-context::reference-export-carries-the-monster-spawn-section")
    def test_member_names_resolve_and_regions_stay_keys(self):
        member = self.encoded["sites"][0]["members"][1]
        self.assertEqual(
            member,
            {
                "variant_key": "synthetic_variant_a",
                "variant_name_zh": "合成甲變種",
                "species_key": "synthetic_species_a",
                "species_name_zh": "合成甲",
                "minimum": 1,
                "maximum": 1,
            },
        )
        for row in [*self.encoded["zones"], *self.encoded["sites"]]:
            self.assertEqual(row["region_key"], "synthetic_region")
            self.assertNotIn("region_name_zh", row)

    @covers_requirement("map-external-reference-context::reference-export-carries-the-monster-spawn-section")
    def test_one_shot_and_recoverable_site_fields(self):
        sites = {row["key"]: row for row in self.encoded["sites"]}
        once, again = sites["synthetic_site_once"], sites["synthetic_site_again"]
        self.assertEqual(
            (once["one_shot"], once["recover_after_ticks"], once["individual_name_zh"]), (True, None, "合成個體")
        )
        self.assertEqual(
            (again["one_shot"], again["recover_after_ticks"], again["individual_name_zh"]), (False, 86400, None)
        )
        self.assertEqual(once["coordinates"], [5, 6])

    @covers_requirement("map-external-reference-context::reference-export-carries-the-monster-spawn-section")
    def test_placement_and_species_sources_are_in_the_source_manifest(self):
        doc = exporter.build_reference_context_document()
        self.assertIn("world/lore/monster_placement.py", doc.source_manifest)
        self.assertIn("world/lore/monster_species.py", doc.source_manifest)


def _valid_payload() -> dict:
    section = exporter.build_monster_spawn_section(**_synthetic_registries())
    return json.loads(encode_reference_context(_document_with(section)))


class MonsterSpawnDecodeTests(unittest.TestCase):
    """Decoding accepts only schema 2 documents with a well-formed section."""

    def assertRefused(self, mutate):
        payload = _valid_payload()
        mutate(payload["monster_spawns"])
        with self.assertRaises(ReferenceContextError):
            decode_reference_context(json.dumps(payload))

    @covers_requirement("map-external-reference-context::reference-decoding-refuses-a-malformed-monster-spawn-section")
    def test_encode_decode_round_trip(self):
        section = exporter.build_monster_spawn_section(**_synthetic_registries())
        encoded = encode_reference_context(_document_with(section))
        decoded = decode_reference_context(encoded)
        self.assertEqual(decoded.monster_spawns, section)
        self.assertEqual(encode_reference_context(decoded), encoded)

    @covers_requirement("map-external-reference-context::reference-decoding-refuses-a-malformed-monster-spawn-section")
    def test_refused_section_shapes(self):
        cases = {
            "unknown section key": lambda s: s.update(extra=[]),
            "unknown zone key": lambda s: s["zones"][0].update(region_name_zh="x"),
            "missing site key": lambda s: s["sites"][0].pop("capacity"),
            "missing member key": lambda s: s["zones"][0]["pool"][0]["members"][0].pop("minimum"),
            "rectangle of three": lambda s: s["zones"][0]["rectangles"].__setitem__(0, [1, 2, 3]),
            "rectangle of strings": lambda s: s["zones"][0]["rectangles"].__setitem__(0, ["1", 2, 3, 4]),
            "rectangle min above max": lambda s: s["zones"][0]["rectangles"].__setitem__(0, [5, 4, 0, 1]),
            "zone without rectangles": lambda s: s["zones"][0].update(rectangles=[]),
            "zero weight": lambda s: s["zones"][0]["pool"][0].update(weight=0),
            "negative weight": lambda s: s["zones"][0]["pool"][0].update(weight=-1),
            "member min above max": lambda s: s["sites"][0]["members"][0].update(minimum=3, maximum=2),
            "unknown site kind": lambda s: s["sites"][0].update(kind="synthetic_kind"),
        }
        for name, mutate in cases.items():
            with self.subTest(name):
                self.assertRefused(mutate)

    @covers_requirement("map-external-reference-context::reference-decoding-refuses-a-malformed-monster-spawn-section")
    def test_wrong_typed_values_raise_the_reference_context_error(self):
        cases = {
            "pool not a list": lambda s: s["zones"][0].update(pool={}),
            "rectangles not a list": lambda s: s["zones"][0].update(rectangles="0,1,0,1"),
            "members not a list": lambda s: s["sites"][0].update(members=None),
            "one_shot not a bool": lambda s: s["sites"][0].update(one_shot=1),
            "region_key not a str": lambda s: s["zones"][0].update(region_key=7),
            "bool weight": lambda s: s["zones"][0]["pool"][0].update(weight=True),
            "zone not a mapping": lambda s: s["zones"].__setitem__(0, []),
            "zones not a list": lambda s: s.update(zones={}),
        }
        for name, mutate in cases.items():
            with self.subTest(name):
                self.assertRefused(mutate)

    @covers_requirement("map-external-reference-context::reference-decoding-refuses-a-malformed-monster-spawn-section")
    def test_schema_version_one_and_missing_section_are_refused(self):
        payload = _valid_payload()
        with self.assertRaises(ReferenceContextError):
            decode_reference_context(json.dumps(dict(payload, schema_version=1)))
        with self.assertRaises(ReferenceContextError):
            decode_reference_context(json.dumps(dict(payload, monster_spawns=[])))
        payload.pop("monster_spawns")
        with self.assertRaises(ReferenceContextError):
            decode_reference_context(json.dumps(payload))

    def test_site_kind_vocabulary_matches_the_game(self):
        from world.lore.monster_placement import MONSTER_SITE_KINDS as GAME_KINDS

        self.assertEqual(GAME_KINDS, MONSTER_SITE_KINDS)


class DeterministicExportTests(unittest.TestCase):
    """Two exports from identical sources must be byte-for-byte identical."""

    @covers_requirement("map-external-reference-context::reference-export-records-authoritative-static-dependencies")
    def test_reproducible_byte_identical_output(self):
        first = exporter.export_reference_context_text()
        second = exporter.export_reference_context_text()
        self.assertEqual(first, second)

    @covers_requirement("map-external-reference-context::reference-export-records-authoritative-static-dependencies")
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

    @covers_requirement("map-external-reference-context::reference-export-records-authoritative-static-dependencies")
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

    @covers_requirement("map-external-reference-context::reference-context-freshness-covers-source-closure-and-membership")
    def test_current_when_sources_match(self):
        freshness = check_reference_context_freshness(
            self.doc,
            self.current_hashes,
            discovered_files=self.discovered,
        )
        self.assertTrue(freshness.current)
        self.assertEqual(freshness.status, STATUS_CURRENT)

    @covers_requirement("map-external-reference-context::reference-context-freshness-covers-source-closure-and-membership")
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

    @covers_requirement("map-external-reference-context::reference-context-freshness-covers-source-closure-and-membership")
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

    @covers_requirement("map-external-reference-context::reference-context-freshness-covers-source-closure-and-membership")
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

    @covers_requirement("map-external-reference-context::reference-context-freshness-covers-source-closure-and-membership")
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

    @covers_requirement("map-external-reference-context::reference-context-freshness-covers-source-closure-and-membership")
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

    @covers_requirement("map-external-reference-context::reference-context-freshness-covers-source-closure-and-membership")
    def test_freshness_checking_without_game_modules_imported(self):
        script = """
import sys
# Confirm Evennia and Django are not imported
assert "evennia" not in sys.modules
assert "django" not in sys.modules
assert "world" not in sys.modules

from elosern_map_core.reference_context import (
    decode_reference_context,
    check_workspace_freshness,
    check_reference_context_freshness,
    STATUS_CURRENT,
)
from pathlib import Path

doc_path = Path("content/map-reference-context.json")
content = doc_path.read_text(encoding="utf-8")
doc = decode_reference_context(content)

freshness = check_workspace_freshness(doc, Path("."))
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

    @covers_requirement("map-external-reference-context::reference-context-freshness-covers-source-closure-and-membership")
    def test_external_source_change_causes_destructive_command_and_undo_to_refuse(self):
        """WHEN an external dependency changes while index bytes & browser snapshot are unchanged
        THEN execution-time check reports unavailable and refuses deletion including undo,
        without changing disk or history.
        """
        from elosern_map_core.reference_context import (
            compute_dependency_fingerprint,
            execute_guarded_destructive_operation,
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            # Create external source
            ext_dir = tmp_root / "world" / "lore"
            ext_dir.mkdir(parents=True)
            ext_file = ext_dir / "places.py"
            ext_file.write_text("DATA = 'original'", encoding="utf-8")

            # Create authoring map document
            map_dir = tmp_root / "content" / "maps" / "settlements"
            map_dir.mkdir(parents=True)
            map_file = map_dir / "settlement_test.yaml"
            original_map_yaml = "nodes:\n  node_a: [10, 10]\n  node_b: [20, 20]\n"
            map_file.write_text(original_map_yaml, encoding="utf-8")

            # Generate reference context for this workspace
            import hashlib
            manifest = {"world/lore/places.py": hashlib.sha256(ext_file.read_bytes()).hexdigest()}
            rules = ("world/lore/**/*.py",)
            doc = ReferenceContextDocument(
                schema_version=SCHEMA_VERSION,
                exporter_version=EXPORTER_VERSION,
                external_identifiers={},
                incoming_references={},
                source_manifest=manifest,
                discovery_rules=rules,
                fingerprint=compute_dependency_fingerprint(manifest, SCHEMA_VERSION, EXPORTER_VERSION, rules),
            )

            # Establish initial command history
            # An undo stack containing: [initial_state, after_create_node_b]
            history_stack = ["action:create_node_b"]

            # Scenario: an external file changes on disk while doc and browser snapshot remain unchanged!
            ext_file.write_text("DATA = 'modified_content'", encoding="utf-8")

            # 1. Attempt destructive command (delete node_a)
            freshness_check = check_workspace_freshness(doc, tmp_root)
            self.assertFalse(freshness_check.current)
            self.assertEqual(freshness_check.status, STATUS_CHANGED)

            target = QualifiedRef("settlement_node", "settlement_test", "node_a")
            def delete_op():
                map_file.write_text("nodes:\n  node_b: [20, 20]\n", encoding="utf-8")
                history_stack.append("action:delete_node_a")

            result = execute_guarded_destructive_operation(doc, target, freshness_check, delete_op)
            self.assertFalse(result.executed)
            self.assertEqual(result.status, DELETION_REFUSED_UNAVAILABLE)
            # Verify disk is byte-for-byte unchanged
            self.assertEqual(map_file.read_text(encoding="utf-8"), original_map_yaml)
            # Verify history stack is unchanged
            self.assertEqual(history_stack, ["action:create_node_b"])

            # 2. Attempt object-removing undo (undoing creation of node_b)
            def undo_remove_op():
                map_file.write_text("nodes:\n  node_a: [10, 10]\n", encoding="utf-8")
                history_stack.pop()

            undo_target = QualifiedRef("settlement_node", "settlement_test", "node_b")
            undo_result = execute_guarded_destructive_operation(doc, undo_target, freshness_check, undo_remove_op)
            self.assertFalse(undo_result.executed)
            self.assertEqual(undo_result.status, DELETION_REFUSED_UNAVAILABLE)
            # Verify disk is STILL byte-for-byte unchanged
            self.assertEqual(map_file.read_text(encoding="utf-8"), original_map_yaml)
            # Verify history stack is STILL unchanged
            self.assertEqual(history_stack, ["action:create_node_b"])

class DeletionSafetyAndUndoRefusalTests(unittest.TestCase):
    """External source changes before deletion cause destructive commands and undo-remove to refuse."""

    def setUp(self):
        self.doc = exporter.build_reference_context_document()
        self.current_hashes = dict(self.doc.source_manifest)

    @covers_requirement("map-external-reference-context::reference-context-freshness-covers-source-closure-and-membership")
    def test_stale_external_context_blocks_deletion_and_undo_remove(self):
        # Scenario: an external dependency changes, but the index on disk / in browser was not refreshed
        changed_hashes = dict(self.current_hashes)
        some_source = next(iter(self.current_hashes))
        changed_hashes[some_source] = "modified_hash_0000000000"

        freshness = check_reference_context_freshness(self.doc, changed_hashes)
        self.assertFalse(freshness.current)

        # Attempt to delete an unreferenced object
        unreferenced_target = QualifiedRef("settlement_node", "t_synth_settlement", "t_synth_free_node")
        decision = self.doc.check_deletion_safety(unreferenced_target, freshness)

        # Must refuse because external context is unavailable
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status, DELETION_REFUSED_UNAVAILABLE)
        self.assertTrue(any("unavailable" in r for r in decision.reasons))

    @covers_requirement("map-external-reference-context::reference-context-freshness-covers-source-closure-and-membership")
    def test_referenced_target_refuses_deletion_even_when_fresh(self):
        freshness = ReferenceContextFreshness(current=True, status=STATUS_CURRENT, reasons=())
        # Pick a target that has an incoming reference
        first_ref_row = next(iter(self.doc.incoming_references.values()))[0]
        target_room = first_ref_row.target
        decision = self.doc.check_deletion_safety(target_room, freshness)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status, DELETION_REFUSED_REFERENCED)
        self.assertTrue(len(decision.incoming_references) > 0)
        self.assertTrue(any(first_ref_row.source in r for r in decision.reasons))

    def test_unreferenced_target_allows_deletion_when_fresh(self):
        freshness = ReferenceContextFreshness(current=True, status=STATUS_CURRENT, reasons=())
        unreferenced = QualifiedRef("interior_room", "unreferenced_interior", "unreferenced_room")
        decision = self.doc.check_deletion_safety(unreferenced, freshness)

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.status, DELETION_ALLOWED)
        self.assertEqual(decision.reasons, ())
