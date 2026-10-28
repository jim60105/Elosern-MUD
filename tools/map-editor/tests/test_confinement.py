"""Document identities resolve only inside the allowlisted roots."""

from __future__ import annotations

import json

import pytest

import synthetic_workspace as fixture
from conftest import make_config

from elosern_map_editor import snapshot
from elosern_map_editor.app import EditorService
from elosern_map_editor.config import Limits
from elosern_map_editor.confinement import ConfinedWorkspace, ConfinementError, resolve_document_id

SETTLEMENT = f"content/maps/settlements/{fixture.SETTLEMENT_ID}.yaml"


@pytest.mark.parametrize(
    ("document_id", "code"),
    [
        ("", "invalid_document_id"),
        (None, "invalid_document_id"),
        ("content/maps/\0continent.yaml", "invalid_document_id"),
        ("content\\maps\\continent.yaml", "invalid_document_id"),
        ("/etc/passwd", "traversal"),
        ("C:/maps/continent.yaml", "traversal"),
        ("content/maps/../../etc/passwd", "traversal"),
        ("content/maps/settlements/../continent.yaml", "traversal"),
        ("./content/maps/continent.yaml", "traversal"),
        ("content//maps/continent.yaml", "traversal"),
        ("pyproject.toml", "not_allowlisted"),
        ("content/maps/settlements/notes.txt", "not_allowlisted"),
        ("world/maps/data/other.json", "not_allowlisted"),
    ],
)
def test_unsafe_or_foreign_document_ids_are_refused(document_id, code):
    with pytest.raises(ConfinementError) as raised:
        resolve_document_id(document_id)
    assert raised.value.code == code


def test_allowlisted_ids_resolve_to_themselves():
    for document_id in (
        "content/maps/continent.yaml",
        SETTLEMENT,
        "content/maps/interiors/x.yaml",
        "content/map-editor-layouts/x.yaml",
        "world/maps/data/district_partition.json",
        "content/map-reference-context.json",
    ):
        assert resolve_document_id(document_id) == document_id


def test_a_traversal_read_never_opens_anything(workspace, tmp_path):
    secret = tmp_path / "secret.yaml"
    secret.write_text("secret", encoding="utf-8")
    with pytest.raises(ConfinementError):
        ConfinedWorkspace(workspace).read_document("content/maps/../../secret.yaml", 1024)


def _state(workspace):
    return EditorService(make_config(workspace)).workspace_state()


def test_an_escaping_linked_source_is_refused_without_reading_its_target(workspace, tmp_path):
    outside = tmp_path / "outside.yaml"
    outside.write_text(fixture.yaml_text(fixture.settlement_data()).replace("Yard", "OUTSIDE-MARKER"), encoding="utf-8")
    (workspace / SETTLEMENT).unlink()
    (workspace / SETTLEMENT).symlink_to(outside)
    before = outside.read_bytes()
    state = _state(workspace)
    assert state["preview_state"] == "unavailable"
    codes = {(d["relative_path"], d["code"]) for d in state["candidate_diagnostics"]}
    assert (SETTLEMENT, "unsafe_source_path") in codes
    assert "OUTSIDE-MARKER" not in json.dumps(state, ensure_ascii=False)
    assert outside.read_bytes() == before


def test_a_linked_source_directory_is_refused(workspace, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    (workspace / "content/maps/interiors").rename(elsewhere)
    (workspace / "content/maps/interiors").symlink_to(elsewhere, target_is_directory=True)
    state = _state(workspace)
    assert state["preview_state"] == "unavailable"
    assert any(d["code"] == "unsafe_source_path" for d in state["candidate_diagnostics"])


def test_an_in_root_link_is_refused_too(workspace):
    copy = workspace / "content/maps/locations-copy.yaml"
    (workspace / "content/maps/locations.yaml").rename(copy)
    (workspace / "content/maps/locations.yaml").symlink_to(copy)
    with pytest.raises(ConfinementError) as raised:
        ConfinedWorkspace(workspace).read_document("content/maps/locations.yaml", 1 << 20)
    assert raised.value.code == "symlink_rejected"


def test_a_linked_workspace_root_is_resolved_once(workspace, tmp_path):
    alias = tmp_path / "alias"
    alias.symlink_to(workspace, target_is_directory=True)
    state = EditorService(make_config(alias)).workspace_state()
    assert state["preview_state"] == "current"


def test_an_oversized_document_is_rejected_before_parsing(workspace, monkeypatch):
    path = workspace / "content/maps/locations.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "#" * 4096 + "\n", encoding="utf-8")
    parsed: list = []
    real_load = snapshot.load_authoring_world
    monkeypatch.setattr(snapshot, "load_authoring_world", lambda sources: parsed.append(sources) or real_load(sources))
    state = EditorService(make_config(workspace, limits=Limits(max_document_bytes=2048))).workspace_state()
    assert parsed == []
    assert state["preview_state"] == "unavailable"
    assert ("content/maps/locations.yaml", "invalid_document_size") in {
        (d["relative_path"], d["code"]) for d in state["candidate_diagnostics"]
    }


def test_a_non_utf8_document_is_a_structure_diagnostic(workspace):
    (workspace / "content/maps/districts.yaml").write_bytes(b"\xff\xfe not utf-8")
    state = _state(workspace)
    assert ("content/maps/districts.yaml", "invalid_encoding") in {
        (d["relative_path"], d["code"]) for d in state["candidate_diagnostics"]
    }


def test_too_many_documents_are_refused_before_reading(workspace):
    state = EditorService(make_config(workspace, limits=Limits(max_documents=2))).workspace_state()
    assert [d["code"] for d in state["candidate_diagnostics"]] == ["too_many_documents"]
