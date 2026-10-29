"""The one-shot capture loader: confinement, structure policy and partition admission."""

from __future__ import annotations

import json

import pytest
import synthetic_workspace as fixture

from elosern_map_core import discover_source_documents, load_authoring_world
from elosern_map_core.partition import generate_partition, partition_input, world_snapshot
from elosern_map_editor.capture_snapshot import CaptureSnapshotError, load_capture_snapshot
from elosern_map_editor.config import Limits
from elosern_map_editor.confinement import ConfinedWorkspace
from elosern_map_editor.snapshot import read_workspace

ARTIFACT = "world/maps/data/district_partition.json"
INDEX = "content/map-reference-context.json"
LAYOUT = f"content/map-editor-layouts/{fixture.INTERIOR_ID}.yaml"
SETTLEMENT = f"content/maps/settlements/{fixture.SETTLEMENT_ID}.yaml"
INTERIOR = f"content/maps/interiors/{fixture.INTERIOR_ID}.yaml"
DISTRICTS = "content/maps/districts.yaml"
#: The synthetic frame is 40 one-kilometre cells: a metre coordinate can reach
#: 40000 while a frame-cell coordinate stays below 40.
FRAME_METRES = 40 * 1000


def _artifact_text(root) -> str:
    """The core's own generation over the same files, computed independently."""

    world = load_authoring_world(discover_source_documents(root))
    return generate_partition(partition_input(world_snapshot(world)))


def _install_partition(root) -> str:
    text = _artifact_text(root)
    target = root / ARTIFACT
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return text


def _positioned_layout(root, positions: dict | None = None):
    path = root / LAYOUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        fixture.yaml_text(
            {
                "version": 1,
                "kind": "layout",
                "id": fixture.INTERIOR_ID,
                "positions": {"front": {"x": 0, "y": 0}} if positions is None else positions,
            }
        ),
        encoding="utf-8",
    )
    return path


def _reads(monkeypatch) -> list[str]:
    """Record every confined document read of one invocation."""

    calls: list[str] = []
    original = ConfinedWorkspace.read_document

    def counted(self, relative_path, limit):
        calls.append(relative_path)
        return original(self, relative_path, limit)

    monkeypatch.setattr(ConfinedWorkspace, "read_document", counted)
    return calls


def _partitioned(tmp_path):
    """The partitionable synthetic workspace with one real partition artifact."""

    workspace = fixture.write_partitionable_workspace(tmp_path / "workspace")
    _install_partition(workspace)
    return workspace


def test_a_fresh_snapshot_projects_once_and_writes_nothing(tmp_path, monkeypatch):
    workspace = _partitioned(tmp_path)
    _positioned_layout(workspace)
    before = fixture.tree_digest(workspace)
    calls = _reads(monkeypatch)

    result = load_capture_snapshot(workspace, view="continent")

    assert sorted(result) == ["diagnostics", "partition", "world"]
    world = result["world"]
    assert world["continent"]["frame_cells"] == 40
    preview = world["continent"]["terrain_preview"]
    assert preview["status"] == "current"
    assert preview["columns"] > 0 and preview["samples"]
    # Independently known synthetic geometry: anchor (0,0) -> cell (5,5) keeps
    # its centre, node yard sits 300/400 m from it, and the two roads are 500
    # and 700 m long.
    locations = {row["id"]: row for row in world["locations"]}
    assert locations[fixture.LOCATION_ID]["centre_m"] == [5500, 5500]
    assert locations[fixture.LOCATION_ID]["local_maps"] == [fixture.SETTLEMENT_ID]
    [settlement] = world["settlements"]
    assert {node["id"]: node["world_m"] for node in settlement["nodes"]}["yard"] == [5800, 5900]
    roads = {road["id"]: road["length_m"] for road in settlement["roads"]}
    assert (roads["gate>yard"], roads["yard>gate"]) == (500.0, 700.0)
    # Authored layout positions survive; the missing room keeps no position,
    # which is the renderer's deterministic fallback input.
    rooms = {room["id"]: room for room in world["interiors"][0]["rooms"]}
    assert rooms["front"]["layout_position"] == [0, 0]
    assert rooms["back"]["layout_position"] is None
    assert world["layouts"][0]["relative_path"] == LAYOUT

    # One read per discovered document, and every world source was read.
    assert len(calls) == len(set(calls))
    assert {path for path, _ in ConfinedWorkspace(workspace).discover_world()} <= set(calls)

    # Outlines keep the codec's continental metre frame (frame cells would be < 40).
    outlines = result["partition"]["outlines"]
    assert set(outlines) == {district["id"] for district in world["districts"]}
    coordinates = [value for rings in outlines.values() for ring in rings for value in ring]
    assert coordinates
    assert all(isinstance(value, int) and 0 <= value <= FRAME_METRES for value in coordinates)
    assert max(coordinates) > FRAME_METRES // 2
    # A fresh artifact produces no staleness diagnostic; only the advisory
    # reference-context note remains.
    assert [(item["category"], item["code"]) for item in result["diagnostics"]] == [
        ("external", "reference_context_missing")
    ]
    assert fixture.tree_digest(workspace) == before


def test_a_later_source_change_is_not_part_of_the_snapshot(tmp_path):
    workspace = fixture.write_workspace(tmp_path / "workspace")
    first = load_capture_snapshot(workspace, view="settlement", map_id=fixture.SETTLEMENT_ID)
    assert first["partition"] is None
    assert {node["id"]: node["key"] for node in first["world"]["settlements"][0]["nodes"]}["yard"] == "Yard"

    data = fixture.settlement_data()
    data["nodes"]["yard"]["key"] = "Renamed yard"
    (workspace / SETTLEMENT).write_text(fixture.yaml_text(data), encoding="utf-8")

    assert {node["id"]: node["key"] for node in first["world"]["settlements"][0]["nodes"]}["yard"] == "Yard"
    second = load_capture_snapshot(workspace, view="settlement", map_id=fixture.SETTLEMENT_ID)
    assert {node["id"]: node["key"] for node in second["world"]["settlements"][0]["nodes"]}["yard"] == "Renamed yard"


def test_partition_freshness_uses_the_single_loaded_snapshot(tmp_path, monkeypatch):
    workspace = _partitioned(tmp_path)
    continent = workspace / "content/maps/continent.yaml"
    original = ConfinedWorkspace.read_document
    rewritten: list[str] = []

    def rewrite_after_read(self, relative_path, limit):
        data = original(self, relative_path, limit)
        if relative_path == "content/maps/continent.yaml" and not rewritten:
            rewritten.append(relative_path)
            changed = fixture.continent_data()
            for region in changed["regions"].values():
                region["display_name_zh"] = "改寫區名"
            continent.write_text(fixture.yaml_text(changed), encoding="utf-8")
        return data

    monkeypatch.setattr(ConfinedWorkspace, "read_document", rewrite_after_read)

    result = load_capture_snapshot(workspace, view="continent")

    # The bytes on disk changed after the snapshot read them: a rescan would
    # make the artifact stale, a single read keeps it current.
    assert rewritten == ["content/maps/continent.yaml"]
    assert result["world"]["continent"]["regions"][0]["display_name_zh"] != "改寫區名"
    assert result["partition"]["outlines"]
    assert all(item["code"] != "stale_partition" for item in result["diagnostics"])


MALFORMED_LAYOUTS = {
    "duplicate_key": (
        "version: 1\nkind: layout\nid: {id}\npositions:\n  front:\n    x: 0\n    y: 0\n"
        "positions:\n  back:\n    x: 1\n    y: 1\n"
    ),
    "invalid_coordinate": None,
    "orphan_layout": (
        "version: 1\nkind: layout\nid: absent_interior\npositions:\n  front:\n    x: 0\n    y: 0\n"
        "positions:\n  back:\n    x: 1\n    y: 1\n"
    ),
}


@pytest.mark.parametrize("name", sorted(MALFORMED_LAYOUTS))
def test_a_malformed_layout_is_refused_while_the_editor_keeps_it(tmp_path, name):
    workspace = fixture.write_workspace(tmp_path / "workspace")
    layout = workspace / (LAYOUT if name != "orphan_layout" else "content/map-editor-layouts/absent_interior.yaml")
    layout.parent.mkdir(parents=True, exist_ok=True)
    text = MALFORMED_LAYOUTS[name]
    if text is None:
        text = fixture.yaml_text(
            {
                "version": 1,
                "kind": "layout",
                "id": fixture.INTERIOR_ID,
                "positions": {"front": {"x": 1.5, "y": 0}},
            }
        )
    else:
        text = text.format(id=fixture.INTERIOR_ID)
    layout.write_text(text, encoding="utf-8")
    before = fixture.tree_digest(workspace)

    with pytest.raises(CaptureSnapshotError) as raised:
        load_capture_snapshot(workspace, view="interior", map_id=fixture.INTERIOR_ID)
    error = raised.value
    assert error.code == "structure"
    assert layout.relative_to(workspace).as_posix() in json.dumps(error.as_dict())
    assert all(item["category"] == "structure" for item in error.diagnostics)
    assert fixture.tree_digest(workspace) == before

    # The interactive editor still loads its partial projection (unchanged policy).
    read = read_workspace(ConfinedWorkspace(workspace), Limits())
    assert read.loaded is True
    assert any(
        item["relative_path"] == layout.relative_to(workspace).as_posix() for item in read.diagnostics
    )


def test_a_malformed_source_document_is_refused(tmp_path):
    workspace = fixture.write_workspace(tmp_path / "workspace")
    locations = workspace / "content/maps/locations.yaml"
    locations.write_text(locations.read_text(encoding="utf-8") + "unexpected_field: 1\n", encoding="utf-8")
    before = fixture.tree_digest(workspace)

    with pytest.raises(CaptureSnapshotError) as raised:
        load_capture_snapshot(workspace, view="settlement", map_id=fixture.SETTLEMENT_ID)

    assert raised.value.code == "structure"
    assert "content/maps/locations.yaml" in json.dumps(raised.value.as_dict())
    assert fixture.tree_digest(workspace) == before


def test_an_escaping_source_link_is_refused_without_exposing_it(tmp_path):
    workspace = fixture.write_workspace(tmp_path / "workspace")
    outside = tmp_path / "outside.yaml"
    outside.write_text(
        "version: 1\nkind: settlement\nid: leaked\nlocation_ref: outside_secret\n", encoding="utf-8"
    )
    (workspace / "content/maps/settlements/leaked.yaml").symlink_to(outside)
    before = fixture.tree_digest(workspace)

    with pytest.raises(CaptureSnapshotError) as raised:
        load_capture_snapshot(workspace, view="settlement", map_id=fixture.SETTLEMENT_ID)

    reported = json.dumps(raised.value.as_dict())
    assert raised.value.code == "structure"
    assert "content/maps/settlements/leaked.yaml" in reported
    assert "outside_secret" not in reported
    assert fixture.tree_digest(workspace) == before


def test_loadable_semantic_work_in_progress_ignores_a_missing_or_stale_index(tmp_path):
    workspace = fixture.write_workspace(tmp_path / "workspace")
    settlement = fixture.settlement_data()
    settlement["nodes"]["lonely"] = {
        "x_m": 900,
        "y_m": 900,
        "prototype_parent": "grid_room",
        "key": "Lonely",
        "desc": "Unreached.",
        "anchor_key": None,
        "typeclass": None,
        "scene_archetype": None,
    }
    (workspace / SETTLEMENT).write_text(fixture.yaml_text(settlement), encoding="utf-8")
    districts = fixture.districts_data()
    districts["districts"]["synthetic_district"]["landmark"]["object_id"] = "lonely"
    (workspace / DISTRICTS).write_text(fixture.yaml_text(districts), encoding="utf-8")
    before = fixture.tree_digest(workspace)

    missing = load_capture_snapshot(workspace, view="settlement", map_id=fixture.SETTLEMENT_ID)
    codes = {(item["category"], item["code"]) for item in missing["diagnostics"]}
    assert ("semantic", "unreachable_landmark") in codes
    assert ("external", "reference_context_missing") in codes
    assert missing["world"]["settlements"][0]["nodes"]
    assert not (workspace / INDEX).exists()
    assert fixture.tree_digest(workspace) == before

    fixture.write_reference_context(workspace)
    (workspace / "external/declarations.txt").write_text("changed\n", encoding="utf-8")
    stale_digest = fixture.tree_digest(workspace)
    stale = load_capture_snapshot(workspace, view="settlement", map_id=fixture.SETTLEMENT_ID)
    stale_codes = {(item["category"], item["code"]) for item in stale["diagnostics"]}
    assert ("external", "reference_context_not_current") in stale_codes
    assert ("semantic", "unreachable_landmark") in stale_codes
    assert stale["world"]["settlements"][0]["nodes"]
    assert fixture.tree_digest(workspace) == stale_digest


def test_a_missing_partition_is_refused_with_regeneration_guidance(tmp_path):
    workspace = fixture.write_workspace(tmp_path / "workspace")
    before = fixture.tree_digest(workspace)

    with pytest.raises(CaptureSnapshotError) as raised:
        load_capture_snapshot(workspace, view="continent")

    error = raised.value
    assert (error.code, error.reason) == ("partition_unavailable", "missing")
    assert "regenerate_partition.py" in error.guidance
    assert "--hide partition" in error.guidance
    assert fixture.tree_digest(workspace) == before


@pytest.mark.parametrize("name", ["not_an_object", "no_metadata", "null_row", "odd_ring", "missing_outline"])
def test_a_malformed_partition_is_refused_even_with_valid_metadata(tmp_path, name):
    workspace = fixture.write_partitionable_workspace(tmp_path / "workspace")
    generated = json.loads(_artifact_text(workspace))
    if name == "not_an_object":
        text = "[]"
    elif name == "no_metadata":
        text = '{"version": 2}'
    else:
        key = generated["districts"][0]
        if name == "null_row":
            generated["coarse"][0] = None
        elif name == "odd_ring":
            generated["outlines"][key][0].append(0)
        else:
            generated["outlines"].pop(key)
        text = json.dumps(generated)
    target = workspace / ARTIFACT
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    before = fixture.tree_digest(workspace)

    with pytest.raises(CaptureSnapshotError) as raised:
        load_capture_snapshot(workspace, view="continent")

    error = raised.value
    assert (error.code, error.reason) == ("partition_unavailable", "malformed")
    assert "regenerate_partition.py" in error.guidance
    assert fixture.tree_digest(workspace) == before


def test_a_stale_partition_is_refused_and_the_artifact_is_preserved(tmp_path):
    workspace = _partitioned(tmp_path)
    target = workspace / ARTIFACT
    before = target.read_bytes()
    districts = fixture.partitionable_districts_data()
    districts["districts"]["synthetic_district"]["district_name_zh"] = "外部改名"
    (workspace / DISTRICTS).write_text(fixture.yaml_text(districts), encoding="utf-8")
    digest = fixture.tree_digest(workspace)

    with pytest.raises(CaptureSnapshotError) as raised:
        load_capture_snapshot(workspace, view="continent")

    error = raised.value
    assert (error.code, error.reason) == ("partition_unavailable", "stale")
    assert "--hide partition" in error.guidance
    assert target.read_bytes() == before
    assert fixture.tree_digest(workspace) == digest
    # Hiding it admits the same workspace, independently of the artifact.
    hidden = load_capture_snapshot(workspace, view="continent", hidden_layers=("partition",))
    assert hidden["partition"] is None
    assert hidden["world"]["continent"]["terrain_preview"]["status"] == "current"


def test_views_without_a_visible_partition_never_read_the_artifact(tmp_path, monkeypatch):
    workspace = fixture.write_workspace(tmp_path / "workspace")
    calls = _reads(monkeypatch)

    hidden = load_capture_snapshot(workspace, view="continent", hidden_layers=["partition", "partition"])
    settlement = load_capture_snapshot(workspace, view="settlement", map_id=fixture.SETTLEMENT_ID)
    interior = load_capture_snapshot(workspace, view="interior", map_id=fixture.INTERIOR_ID)

    assert [item["partition"] for item in (hidden, settlement, interior)] == [None, None, None]
    assert hidden["world"]["continent"]["terrain_preview"]["status"] == "current"
    assert interior["world"]["interiors"][0]["rooms"]
    assert ARTIFACT not in calls
    assert not (workspace / ARTIFACT).exists()
    assert not (workspace / INDEX).exists()


@pytest.mark.parametrize(
    ("view", "map_id", "code"),
    [
        ("continent", fixture.SETTLEMENT_ID, "invalid_map_id"),
        ("settlement", None, "invalid_map_id"),
        ("settlement", "", "invalid_map_id"),
        ("settlement", "absent_map", "unknown_map"),
        ("interior", "absent_map", "unknown_map"),
        ("interior", fixture.SETTLEMENT_ID, "wrong_view"),
        ("settlement", fixture.INTERIOR_ID, "wrong_view"),
        ("region", None, "invalid_view"),
    ],
)
def test_the_requested_identity_is_resolved_against_the_loaded_world(tmp_path, view, map_id, code):
    workspace = fixture.write_workspace(tmp_path / "workspace")
    before = fixture.tree_digest(workspace)

    with pytest.raises(CaptureSnapshotError) as raised:
        load_capture_snapshot(workspace, view=view, map_id=map_id)

    assert raised.value.code == code
    assert fixture.tree_digest(workspace) == before


def test_hidden_layer_names_must_be_strings(tmp_path):
    workspace = fixture.write_workspace(tmp_path / "workspace")

    with pytest.raises(CaptureSnapshotError) as raised:
        load_capture_snapshot(workspace, view="continent", hidden_layers=[b"partition"])

    assert raised.value.code == "invalid_hidden_layers"
