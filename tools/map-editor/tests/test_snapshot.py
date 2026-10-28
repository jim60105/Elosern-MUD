"""The complete read model: every domain, core-derived geometry and statuses."""

from __future__ import annotations

import json

import synthetic_workspace as fixture
from conftest import make_config

from elosern_map_core import load_authoring_world, make_source_document
from elosern_map_editor.app import EditorService
from elosern_map_editor.config import Limits


def _state(workspace, **kwargs):
    return EditorService(make_config(workspace, **kwargs)).workspace_state()


def _write_partition(workspace, signature: str) -> None:
    target = workspace / "world/maps/data/district_partition.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {"version": 2, "algorithm_version": 1, "source_signature": signature, "fingerprint": "synthetic"}
        ),
        encoding="utf-8",
    )


def _core_world(workspace):
    return load_authoring_world(
        make_source_document(path, (workspace / path).read_text(encoding="utf-8")) for path in fixture.DOCUMENTS
    )


def test_a_fresh_read_loads_every_domain_and_is_writable(workspace):
    state = _state(workspace)
    assert state["preview_state"] == "current"
    assert state["write_pause"] == {"paused": False, "reason": None}
    assert state["snapshot_revision"] == 1
    world = state["world"]
    assert {document["kind"] for document in state["documents"]} == {
        "continent", "locations", "districts", "settlement", "interior",
    }
    assert world["continent"]["frame_cells"] == 40
    assert [waterway["id"] for waterway in world["continent"]["waterways"]] == ["synthetic_river"]
    locations = {row["id"]: row for row in world["locations"]}
    assert locations[fixture.LOCATION_ID]["local_maps"] == [fixture.SETTLEMENT_ID]
    assert locations[fixture.BARE_LOCATION_ID]["local_maps"] == []
    assert locations[fixture.LOCATION_ID]["centre_m"] == [5500, 5500]
    assert [row["id"] for row in world["districts"]] == ["synthetic_district"]
    [settlement] = world["settlements"]
    assert settlement["interiors"] == [fixture.INTERIOR_ID]
    nodes = {row["id"]: row for row in settlement["nodes"]}
    assert nodes["yard"]["local_m"] == [300, 400]
    assert nodes["yard"]["world_m"] == [5800, 5900]
    roads = {row["id"]: row for row in settlement["roads"]}
    assert roads["gate>yard"]["length_m"] == 500.0
    assert roads["yard>gate"]["length_m"] == 700.0
    assert roads["yard>gate"]["direction"] == "s"
    [interior] = world["interiors"]
    assert {room["id"] for room in interior["rooms"]} == {"front", "back"}
    assert interior["exterior"]["node"] == "yard"
    assert interior["layout_relative_path"] is None
    assert state["schema"]["version"] == 1


def test_every_document_fingerprint_is_the_hash_of_its_bytes_on_disk(workspace):
    state = _state(workspace)
    digests = fixture.tree_digest(workspace)
    for document in state["documents"]:
        assert document["fingerprint"] == digests[document["relative_path"]]


def test_layout_positions_attach_to_rooms_without_entering_world_documents(workspace):
    layout = workspace / f"content/map-editor-layouts/{fixture.INTERIOR_ID}.yaml"
    layout.parent.mkdir(parents=True)
    layout.write_text(
        fixture.yaml_text(
            {
                "version": 1,
                "kind": "layout",
                "id": fixture.INTERIOR_ID,
                "positions": {"front": {"x": 0, "y": 0}, "back": {"x": 2, "y": 1}},
            }
        ),
        encoding="utf-8",
    )
    state = _state(workspace)
    rooms = {room["id"]: room for room in state["world"]["interiors"][0]["rooms"]}
    assert rooms["back"]["layout_position"] == [2, 1]
    assert all(document["kind"] != "layout" for document in state["documents"])
    assert state["world"]["layouts"][0]["relative_path"].startswith("content/map-editor-layouts/")


def test_semantic_work_in_progress_loads_with_diagnostics_and_stays_writable(workspace):
    data = fixture.settlement_data()
    data["nodes"]["lonely"] = {
        "x_m": 900, "y_m": 900, "prototype_parent": "grid_room", "key": "Lonely", "desc": "Unreached.",
        "anchor_key": None, "typeclass": None, "scene_archetype": None,
    }
    (workspace / f"content/maps/settlements/{fixture.SETTLEMENT_ID}.yaml").write_text(
        fixture.yaml_text(data), encoding="utf-8"
    )
    districts = fixture.districts_data()
    districts["districts"]["synthetic_district"]["landmark"]["object_id"] = "lonely"
    (workspace / "content/maps/districts.yaml").write_text(fixture.yaml_text(districts), encoding="utf-8")
    state = _state(workspace)
    assert state["preview_state"] == "current"
    assert state["write_pause"]["paused"] is False
    assert ("semantic", "unreachable_landmark") in {
        (item["category"], item["code"]) for item in state["diagnostics"]
    }


def test_a_structural_failure_at_startup_has_no_preview_and_pauses_writes(workspace):
    path = workspace / "content/maps/locations.yaml"
    path.write_text(path.read_text(encoding="utf-8") + "unexpected_field: 1\n", encoding="utf-8")
    state = _state(workspace)
    assert state["preview_state"] == "unavailable"
    assert state["world"] is None
    assert state["write_pause"] == {"paused": True, "reason": "unavailable_preview"}
    [diagnostic] = [d for d in state["candidate_diagnostics"] if d["relative_path"] == "content/maps/locations.yaml"]
    assert diagnostic["line"] is not None


def test_partition_status_is_current_stale_or_unavailable(workspace):
    assert _state(workspace)["partition_status"]["status"] == "unavailable"
    signature = _core_world(workspace).partition_signature
    _write_partition(workspace, signature)
    current = _state(workspace)
    assert current["partition_status"]["status"] == "current"
    assert all(item["code"] != "stale_partition" for item in current["diagnostics"])
    _write_partition(workspace, "0" * 64)
    stale = _state(workspace)
    assert stale["partition_status"]["status"] == "stale"
    assert any(item["code"] == "stale_partition" for item in stale["diagnostics"])
    (workspace / "world/maps/data/district_partition.json").write_text("{not json", encoding="utf-8")
    assert _state(workspace)["partition_status"]["status"] == "unavailable"


def test_reference_context_freshness_follows_its_external_sources(workspace):
    assert _state(workspace)["external_context_status"]["status"] == "missing"
    fixture.write_reference_context(workspace)
    assert _state(workspace)["external_context_status"]["status"] == "current"
    (workspace / "external/declarations.txt").write_text("changed\n", encoding="utf-8")
    changed = _state(workspace)["external_context_status"]
    assert changed["status"] == "changed"
    assert changed["current"] is False


def test_reference_context_rules_cannot_escape_the_workspace(workspace, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("outside secret", encoding="utf-8")
    fixture.write_reference_context(workspace, rules=("../outside.txt",))
    status = _state(workspace)["external_context_status"]
    assert status["current"] is False
    assert status["status"] == "unavailable"
    assert "outside secret" not in json.dumps(status)


def test_a_linked_external_source_makes_the_context_unavailable(workspace, tmp_path):
    fixture.write_reference_context(workspace)
    outside = tmp_path / "outside.txt"
    outside.write_text("synthetic external declaration\n", encoding="utf-8")
    target = workspace / "external/declarations.txt"
    target.unlink()
    target.symlink_to(outside)
    status = _state(workspace)["external_context_status"]
    assert status["status"] == "unavailable"
    assert "symlink_rejected" in status["reasons"][0]


def test_the_external_byte_budget_bounds_hashing(workspace):
    fixture.write_reference_context(workspace)
    status = _state(workspace, limits=Limits(max_external_total_bytes=4))["external_context_status"]
    assert status["status"] == "unavailable"
