"""Pure unit tests for the reference-context codec, freshness checker and deletion safety."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

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
    IncomingReference,
    ReferenceContextDocument,
    ReferenceContextError,
    ReferenceContextFreshness,
    canonical_target_key,
    check_reference_context_freshness,
    check_workspace_freshness,
    compute_dependency_fingerprint,
    decode_reference_context,
    discover_external_sources,
    encode_reference_context,
)


def _sample_document() -> ReferenceContextDocument:
    rules = ("world/lore/**/*.py", "world/quests/**/*.py")
    manifest = {
        "world/lore/settlements/places_altoria.py": "aaaabbbbccccdddd1111222233334444",
        "world/quests/catalog.py": "555566667777888899990000aaaabbbb",
    }
    incoming = {
        "settlement_node:altoria_capital:north_gate": (
            IncomingReference(
                source="city_gate:altoria_north",
                source_file="world/maps/city_gates.py",
                source_domain="city_gates",
                target=QualifiedRef(domain="settlement_node", map_id="altoria_capital", object_id="north_gate"),
            ),
        ),
        "interior_room:places_altoria_middle:tailor": (
            IncomingReference(
                source="place:altoria_tailor",
                source_file="world/lore/settlements/places_altoria.py",
                source_domain="places",
                target=QualifiedRef(domain="interior_room", map_id="places_altoria_middle", object_id="tailor"),
            ),
        ),
    }
    fingerprint = compute_dependency_fingerprint(
        manifest,
        SCHEMA_VERSION,
        EXPORTER_VERSION,
        rules,
    )
    return ReferenceContextDocument(
        schema_version=SCHEMA_VERSION,
        exporter_version=EXPORTER_VERSION,
        external_identifiers={
            "scene_archetypes": ("synthetic_scene_a", "synthetic_scene_b"),
            "nations": ("altoria", "grandia"),
        },
        incoming_references=incoming,
        source_manifest=manifest,
        discovery_rules=rules,
        fingerprint=fingerprint,
    )


def test_encode_and_decode_roundtrip():
    doc = _sample_document()
    encoded = encode_reference_context(doc)
    decoded = decode_reference_context(encoded)

    assert decoded.schema_version == doc.schema_version
    assert decoded.exporter_version == doc.exporter_version
    assert decoded.fingerprint == doc.fingerprint
    assert decoded.external_identifiers == doc.external_identifiers
    assert decoded.source_manifest == doc.source_manifest
    assert decoded.discovery_rules == doc.discovery_rules
    assert len(decoded.incoming_references) == len(doc.incoming_references)

    target_ref = QualifiedRef("settlement_node", "altoria_capital", "north_gate")
    incoming = decoded.incoming_references_for(target_ref)
    assert len(incoming) == 1
    assert incoming[0].source == "city_gate:altoria_north"
    assert incoming[0].source_domain == "city_gates"
    assert incoming[0].target == target_ref


def test_malformed_document_rejections():
    with pytest.raises(ReferenceContextError, match="invalid reference-context JSON"):
        decode_reference_context("{not-json")

    with pytest.raises(ReferenceContextError, match="schema_version must be an integer"):
        decode_reference_context(json.dumps({"schema_version": "1"}))

    with pytest.raises(ReferenceContextError, match="unsupported schema_version 99"):
        decode_reference_context(json.dumps({"schema_version": 99}))

    with pytest.raises(ReferenceContextError, match="exporter_version must be an integer"):
        decode_reference_context(json.dumps({"schema_version": SCHEMA_VERSION, "exporter_version": None}))


def test_identifier_lookup_and_queries():
    doc = _sample_document()
    assert doc.is_valid_identifier("scene_archetypes", "synthetic_scene_a")
    assert not doc.is_valid_identifier("scene_archetypes", "non_existent")
    assert not doc.is_valid_identifier("unknown_family", "synthetic_scene_a")
    assert doc.identifier_set("nations") == frozenset({"altoria", "grandia"})


def test_incoming_references_and_target_keys():
    doc = _sample_document()
    target_node = QualifiedRef("settlement_node", "altoria_capital", "north_gate")
    assert doc.has_incoming_references(target_node)
    assert doc.has_incoming_references("settlement_node:altoria_capital:north_gate")

    target_free = QualifiedRef("settlement_node", "altoria_capital", "unreferenced_node")
    assert not doc.has_incoming_references(target_free)
    assert doc.incoming_references_for(target_free) == ()


def test_freshness_current_state():
    doc = _sample_document()
    current_hashes = dict(doc.source_manifest)
    discovered = list(doc.source_manifest.keys())

    freshness = check_reference_context_freshness(
        doc,
        current_hashes,
        discovered_files=discovered,
    )
    assert freshness.current
    assert freshness.status == STATUS_CURRENT
    assert freshness.reasons == ()
    assert bool(freshness) is True


def test_freshness_incompatible_version():
    doc = _sample_document()
    doc_incompatible = ReferenceContextDocument(
        schema_version=SCHEMA_VERSION,
        exporter_version=EXPORTER_VERSION + 1,
        external_identifiers=doc.external_identifiers,
        incoming_references=doc.incoming_references,
        source_manifest=doc.source_manifest,
        discovery_rules=doc.discovery_rules,
        fingerprint=doc.fingerprint,
    )
    freshness = check_reference_context_freshness(
        doc_incompatible,
        dict(doc.source_manifest),
    )
    assert not freshness.current
    assert freshness.status == STATUS_INCOMPATIBLE
    assert any("exporter_version" in r for r in freshness.reasons)


def test_freshness_missing_source_file():
    doc = _sample_document()
    hashes = dict(doc.source_manifest)
    # Remove one file from available hashes
    del hashes["world/quests/catalog.py"]

    freshness = check_reference_context_freshness(doc, hashes)
    assert not freshness.current
    assert freshness.status == STATUS_MISSING
    assert any("world/quests/catalog.py" in r for r in freshness.reasons)


def test_freshness_changed_source_file():
    doc = _sample_document()
    hashes = dict(doc.source_manifest)
    hashes["world/quests/catalog.py"] = "changed_hash_value"

    freshness = check_reference_context_freshness(doc, hashes)
    assert not freshness.current
    assert freshness.status == STATUS_CHANGED
    assert any("world/quests/catalog.py" in r for r in freshness.reasons)


def test_freshness_membership_mismatch_added_and_removed():
    doc = _sample_document()
    hashes = dict(doc.source_manifest)

    # Added file
    hashes["world/lore/new_file.py"] = "somehash"
    discovered_added = list(doc.source_manifest.keys()) + ["world/lore/new_file.py"]

    freshness_added = check_reference_context_freshness(
        doc,
        hashes,
        discovered_files=discovered_added,
    )
    assert not freshness_added.current
    assert freshness_added.status == STATUS_MEMBERSHIP_MISMATCH
    assert any("new untracked source file" in r for r in freshness_added.reasons)

    # Removed file
    discovered_removed = ["world/lore/settlements/places_altoria.py"]
    freshness_removed = check_reference_context_freshness(
        doc,
        hashes,
        discovered_files=discovered_removed,
    )
    assert not freshness_removed.current
    assert freshness_removed.status == STATUS_MEMBERSHIP_MISMATCH
    assert any("tracked source file(s) removed" in r for r in freshness_removed.reasons)


def test_deletion_safety_evaluations():
    doc = _sample_document()
    fresh = ReferenceContextFreshness(current=True, status=STATUS_CURRENT, reasons=())
    stale = ReferenceContextFreshness(current=False, status=STATUS_CHANGED, reasons=("file changed",))

    referenced_node = QualifiedRef("settlement_node", "altoria_capital", "north_gate")
    free_node = QualifiedRef("settlement_node", "altoria_capital", "free_node")

    # 1. Unavailable context blocks any deletion
    d1 = doc.check_deletion_safety(free_node, stale)
    assert not d1.allowed
    assert d1.status == DELETION_REFUSED_UNAVAILABLE
    assert not bool(d1)

    # 2. Fresh context blocks deletion of an object with incoming references
    d2 = doc.check_deletion_safety(referenced_node, fresh)
    assert not d2.allowed
    assert d2.status == DELETION_REFUSED_REFERENCED
    assert len(d2.incoming_references) == 1
    assert "city_gate:altoria_north" in d2.reasons[0]

    # 3. Fresh context allows deletion of unreferenced object
    d3 = doc.check_deletion_safety(free_node, fresh)
    assert d3.allowed
    assert d3.status == DELETION_ALLOWED
    assert bool(d3)


def test_workspace_discovery_and_freshness(tmp_path: Path):
    doc_dir = tmp_path / "world" / "lore"
    doc_dir.mkdir(parents=True)
    f1 = doc_dir / "places.py"
    f1.write_text("DATA = 1", encoding="utf-8")

    q_dir = tmp_path / "world" / "quests"
    q_dir.mkdir(parents=True)
    f2 = q_dir / "catalog.py"
    f2.write_text("QUESTS = []", encoding="utf-8")

    # Excluded dirs should not be discovered
    map_dir = tmp_path / "content" / "maps" / "settlements"
    map_dir.mkdir(parents=True)
    (map_dir / "altoria.yaml").write_text("nodes: {}", encoding="utf-8")

    discovered = discover_external_sources(tmp_path, ("world/lore/**/*.py", "world/quests/**/*.py"))
    assert discovered == ["world/lore/places.py", "world/quests/catalog.py"]

    import hashlib
    h1 = hashlib.sha256(f1.read_bytes()).hexdigest()
    h2 = hashlib.sha256(f2.read_bytes()).hexdigest()
    manifest = {
        "world/lore/places.py": h1,
        "world/quests/catalog.py": h2,
    }
    rules = ("world/lore/**/*.py", "world/quests/**/*.py")
    doc = ReferenceContextDocument(
        schema_version=SCHEMA_VERSION,
        exporter_version=EXPORTER_VERSION,
        external_identifiers={},
        incoming_references={},
        source_manifest=manifest,
        discovery_rules=rules,
        fingerprint=compute_dependency_fingerprint(manifest, SCHEMA_VERSION, EXPORTER_VERSION, rules),
    )

    fresh = check_workspace_freshness(doc, tmp_path)
    assert fresh.current

    # Mutate a file
    f1.write_text("DATA = 2", encoding="utf-8")
    stale = check_workspace_freshness(doc, tmp_path)
    assert not stale.current
    assert stale.status == STATUS_CHANGED


def test_malformed_incoming_reference_key_disagreement():
    doc = _sample_document()
    data = doc.to_dict()
    # Move the north_gate entry under a mismatched key
    entry = data["incoming_references"].pop("settlement_node:altoria_capital:north_gate")
    data["incoming_references"]["settlement_node:altoria_capital:other_gate"] = entry

    with pytest.raises(ReferenceContextError, match="disagrees with map key"):
        decode_reference_context(json.dumps(data))


def test_execute_guarded_destructive_operation_behavior():
    from elosern_map_core.reference_context import execute_guarded_destructive_operation

    doc = _sample_document()
    fresh = ReferenceContextFreshness(current=True, status=STATUS_CURRENT, reasons=())
    stale = ReferenceContextFreshness(current=False, status=STATUS_CHANGED, reasons=("changed",))

    op_called = []
    def op():
        op_called.append(True)

    referenced = QualifiedRef("settlement_node", "altoria_capital", "north_gate")
    free = QualifiedRef("settlement_node", "altoria_capital", "free_node")

    # Refused when stale
    res1 = execute_guarded_destructive_operation(doc, free, stale, op)
    assert not res1.executed
    assert not op_called

    # Refused when referenced
    res2 = execute_guarded_destructive_operation(doc, referenced, fresh, op)
    assert not res2.executed
    assert not op_called

    # Allowed when fresh and free
    res3 = execute_guarded_destructive_operation(doc, free, fresh, op)
    assert res3.executed
    assert op_called == [True]
