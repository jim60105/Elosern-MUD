"""Geography commands over the real ASGI app and a synthetic workspace.

Every assertion inspects the disk: a command writes only its owning
document, a rejection leaves every byte unchanged, and the derived terrain
preview and partition freshness follow from the core's reading of the new
inputs. Synthetic data only.
"""

from __future__ import annotations

import errno
import json

import pytest
from ruamel.yaml import YAML

import synthetic_workspace as fixture
from editor_client import Editor, sha

from elosern_map_editor.geography import MAX_MASK_SIDE, toggled_mask

CONTINENT = "content/maps/continent.yaml"
LOCATIONS = "content/maps/locations.yaml"
DISTRICTS = "content/maps/districts.yaml"
SETTLEMENT = f"content/maps/settlements/{fixture.SETTLEMENT_ID}.yaml"
PARTITION = "world/maps/data/district_partition.json"
RIVER = {"kind": "waterway_route", "waterway_id": "synthetic_river"}


def _send(editor: Editor, name: str, document: str, arguments: dict, **overrides):
    path = editor.workspace / document
    expected = sha(path) if path.exists() else "absent"
    return editor.raw(name, editor.envelope(document, expected, arguments, **overrides))


def _data(workspace, document):
    return YAML(typ="safe", pure=True).load((workspace / document).read_text(encoding="utf-8"))


def _others_unchanged(before: dict, after: dict, written: str) -> None:
    assert {path for path in before if before[path] != after.get(path)} | (set(after) - set(before)) == {written}


def _sign_partition(editor: Editor) -> None:
    """A metadata-only artifact signed with the current inputs' signature."""

    from elosern_map_core import load_authoring_world, make_source_document

    world = load_authoring_world(
        make_source_document(path, (editor.workspace / path).read_text(encoding="utf-8")) for path in fixture.DOCUMENTS
    )
    target = editor.workspace / PARTITION
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps({"version": 2, "algorithm_version": 1, "source_signature": world.partition_signature,
                    "fingerprint": "synthetic"}),
        encoding="utf-8",
    )
    editor.reload()


# -- control points ----------------------------------------------------------
def test_moving_a_river_point_is_one_continent_write_that_stales_the_partition(workspace):
    editor = Editor(workspace)
    _sign_partition(editor)
    state = editor.state()
    assert state["partition_status"]["status"] == "current"
    preview = state["world"]["continent"]["terrain_preview"]
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "move_control_point", CONTINENT, {"feature": RIVER, "index": 0, "point": [20, 26]})
    assert status == 200 and body["changed"] is True
    after = fixture.tree_digest(workspace)
    _others_unchanged(before, after, CONTINENT)
    assert _data(workspace, CONTINENT)["terrain"]["waterways"]["synthetic_river"]["route"][0] == {"cell_x": 20, "cell_y": 26}
    state = editor.state()
    # Derived output: the core recomputed the preview; nothing regenerated.
    assert state["world"]["continent"]["terrain_preview"]["samples"] != preview["samples"]
    assert state["partition_status"]["status"] == "stale"
    assert sha(workspace / PARTITION) == before[PARTITION]
    assert any(item["code"] == "stale_partition" for item in state["diagnostics"])
    # A stale partition is not a stale preview: the next edits are admitted.
    assert state["preview_state"] == "current"
    assert _send(editor, "move_control_point", CONTINENT, {"feature": RIVER, "index": 0, "point": [20, 24]})[0] == 200
    assert _send(editor, "insert_control_point", CONTINENT,
                 {"feature": {"kind": "mainland"}, "index": 1, "point": [20, 0]})[0] == 200
    assert editor.state()["partition_status"]["status"] == "stale"


def test_insert_remove_and_undo_restore_the_exact_bytes(workspace):
    editor = Editor(workspace)
    original = (workspace / CONTINENT).read_bytes()
    assert _send(editor, "insert_control_point", CONTINENT, {"feature": RIVER, "index": 1, "point": [12, 21]})[0] == 200
    route = _data(workspace, CONTINENT)["terrain"]["waterways"]["synthetic_river"]["route"]
    assert route[1] == {"cell_x": 12, "cell_y": 21} and len(route) == 3
    assert _send(editor, "remove_control_point", CONTINENT, {"feature": RIVER, "index": 1})[0] == 200
    assert len(_data(workspace, CONTINENT)["terrain"]["waterways"]["synthetic_river"]["route"]) == 2
    assert editor.undo()[0] == 200 and editor.undo()[0] == 200
    assert (workspace / CONTINENT).read_bytes() == original


def test_mainland_points_are_kilometres_and_other_features_are_cells(workspace):
    editor = Editor(workspace)
    assert _send(editor, "move_control_point", CONTINENT,
                 {"feature": {"kind": "mainland"}, "index": 1, "point": [38, 2]})[0] == 200
    assert _send(editor, "insert_control_point", CONTINENT,
                 {"feature": {"kind": "waterway_ford", "waterway_id": "synthetic_river"}, "index": 1, "point": [15, 20]})[0] == 200
    data = _data(workspace, CONTINENT)
    assert data["mainland_boundary_km"][1] == {"east_km": 38, "north_km": 2}
    assert data["terrain"]["waterways"]["synthetic_river"]["fords"][1] == {"cell_x": 15, "cell_y": 20}
    fords = editor.state()["world"]["continent"]["waterways"][0]["fords_m"]
    assert fords[1] == [15500, 20500]


@pytest.mark.parametrize(
    ("arguments", "status", "code"),
    [
        ({"feature": RIVER, "index": 9, "point": [1, 1]}, 422, "validation_failed"),
        ({"feature": {"kind": "waterway_route", "waterway_id": "nope"}, "index": 0, "point": [1, 1]}, 422, "validation_failed"),
        ({"feature": {"kind": "sea"}, "index": 0, "point": [1, 1]}, 400, "invalid_command"),
        ({"feature": RIVER, "index": 0, "point": [-1, 1]}, 400, "invalid_command"),
        ({"feature": RIVER, "index": 0, "point": [1.5, 1]}, 400, "invalid_command"),
        ({"feature": RIVER, "index": 0, "point": [True, 1]}, 400, "invalid_command"),
    ],
)
def test_rejected_points_write_nothing(workspace, arguments, status, code):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    answer = _send(editor, "move_control_point", CONTINENT, arguments)
    assert (answer[0], answer[1]["error"]["code"]) == (status, code)
    assert fixture.tree_digest(workspace) == before


def test_removing_below_the_schema_minimum_is_refused(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "remove_control_point", CONTINENT, {"feature": RIVER, "index": 0})
    assert status == 422 and body["error"]["code"] == "validation_failed"
    assert fixture.tree_digest(workspace) == before


def test_an_unchanged_point_writes_nothing(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "move_control_point", CONTINENT, {"feature": RIVER, "index": 0, "point": [20, 20]})
    assert status == 200 and body["changed"] is False
    assert fixture.tree_digest(workspace) == before
    assert editor.state()["history"]["undo"] is None


def test_a_non_monotone_forest_edge_saves_as_diagnosed_work_in_progress(workspace):
    editor = Editor(workspace)
    status, _ = _send(editor, "move_control_point", CONTINENT,
                      {"feature": {"kind": "forest_edge"}, "index": 1, "point": [0, 30]})
    assert status == 200
    state = editor.state()
    assert any(item["code"] == "terrain_inconsistent" for item in state["diagnostics"])
    assert state["world"]["continent"]["terrain_preview"]["status"] == "unavailable"


# -- ridge, passes, waterways, regions, sites ---------------------------------
def test_ridge_parameters_and_passes_change_the_derived_walls(workspace):
    editor = Editor(workspace)
    walls = editor.state()["world"]["continent"]["terrain_preview"]["ridge_walls"]
    assert _send(editor, "set_terrain_parameter", CONTINENT, {"field": "ridge.base_x", "value": 14})[0] == 200
    assert _send(editor, "add_ridge_pass", CONTINENT, {"y_min": 20, "y_max": 22})[0] == 200
    assert _send(editor, "set_ridge_pass", CONTINENT, {"index": 0, "y_min": 3, "y_max": 5})[0] == 200
    ridge = _data(workspace, CONTINENT)["terrain"]["ridge"]
    assert ridge["base_x"] == 14 and ridge["passes"] == [{"y_min": 3, "y_max": 5}, {"y_min": 20, "y_max": 22}]
    preview = editor.state()["world"]["continent"]["terrain_preview"]
    assert preview["ridge_walls"] != walls
    assert [(row["y_min"], row["y_max"]) for row in preview["passes"]] == [(3, 5), (20, 22)]
    assert _send(editor, "remove_ridge_pass", CONTINENT, {"index": 1})[0] == 200
    assert len(_data(workspace, CONTINENT)["terrain"]["ridge"]["passes"]) == 1
    status, body = _send(editor, "set_terrain_parameter", CONTINENT, {"field": "frame_cells", "value": 9})
    assert (status, body["error"]["code"]) == (400, "invalid_command")


def test_waterways_are_created_and_the_border_river_is_never_removed(workspace):
    editor = Editor(workspace)
    route = [[30, 25], [36, 25]]
    assert _send(editor, "add_waterway", CONTINENT, {"waterway_id": "new_brook", "route": route})[0] == 200
    status, body = _send(editor, "add_waterway", CONTINENT, {"waterway_id": "new_brook", "route": route})
    assert status == 422 and body["error"]["diagnostics"][0]["code"] == "duplicate_identifier"
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "remove_waterway", CONTINENT, {"waterway_id": "synthetic_river"})
    assert (status, body["error"]["code"]) == (409, "deletion_refused")
    assert body["error"]["internal_references"][0]["field_path"] == "terrain.border_river_key"
    assert fixture.tree_digest(workspace) == before
    assert _send(editor, "remove_waterway", CONTINENT, {"waterway_id": "new_brook"})[0] == 200
    assert "new_brook" not in _data(workspace, CONTINENT)["terrain"]["waterways"]


def test_region_prose_and_classifier_fields_are_typed(workspace):
    editor = Editor(workspace)
    region = "eastern_plains"
    assert _send(editor, "set_region_field", CONTINENT,
                 {"region_id": region, "field": "terrain_flavor_zh", "value": ["一", "二", "三"]})[0] == 200
    assert _send(editor, "set_region_field", CONTINENT,
                 {"region_id": region, "field": "nation_key", "value": "synthetic_nation"})[0] == 200
    data = _data(workspace, CONTINENT)["regions"][region]
    assert data["terrain_flavor_zh"] == ["一", "二", "三"] and data["nation_key"] == "synthetic_nation"
    before = fixture.tree_digest(workspace)
    # One variant only: the core schema requires two.
    status, _ = _send(editor, "set_region_field", CONTINENT, {"region_id": region, "field": "terrain_flavor_zh", "value": ["一"]})
    assert status == 422
    status, _ = _send(editor, "set_region_field", CONTINENT, {"region_id": region, "field": "nation_key", "value": {"x": 1}})
    assert status == 400
    status, _ = _send(editor, "set_region_field", CONTINENT, {"region_id": "atlantis", "field": "nation_key", "value": None})
    assert status == 422
    assert fixture.tree_digest(workspace) == before


def test_sites_are_created_moved_and_removed(workspace):
    editor = Editor(workspace)
    site = {"site_id": "synthetic_port", "display_name": "Port", "role": "Trade", "cell": [2, 3]}
    assert _send(editor, "add_site", CONTINENT, site)[0] == 200
    assert _send(editor, "set_site_field", CONTINENT, {"site_id": "synthetic_port", "field": "cell", "value": [4, 5]})[0] == 200
    assert _data(workspace, CONTINENT)["harbor_sites"]["synthetic_port"]["cell"] == {"cell_x": 4, "cell_y": 5}
    assert editor.state()["world"]["continent"]["harbor_sites"][0]["centre_m"] == [4500, 5500]
    assert _send(editor, "remove_site", CONTINENT, {"site_id": "synthetic_port"})[0] == 200
    assert _data(workspace, CONTINENT)["harbor_sites"] == {}


# -- locations -----------------------------------------------------------------
NEW_LOCATION = {
    "location_id": "new_ruin",
    "kind": "dungeon",
    "display_name_zh": "新遺跡",
    "description": "A ruin with no local map.",
    "geographic_constraint": "synthetic",
    "scene_archetype": None,
    "cell": [33, 8],
}


def test_a_new_location_has_no_local_map_and_no_fabricated_documents(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    assert _send(editor, "create_location", LOCATIONS, NEW_LOCATION)[0] == 200
    _others_unchanged(before, fixture.tree_digest(workspace), LOCATIONS)
    world = editor.state()["world"]
    location = next(row for row in world["locations"] if row["id"] == "new_ruin")
    assert location["local_maps"] == [] and location["centre_m"] == [33500, 8500]
    assert {s["id"] for s in world["settlements"]} == {fixture.SETTLEMENT_ID}
    assert {i["id"] for i in world["interiors"]} == {fixture.INTERIOR_ID}
    assert _send(editor, "set_location_field", LOCATIONS,
                 {"location_id": "new_ruin", "field": "display_name_zh", "value": "古遺跡"})[0] == 200
    assert _data(workspace, LOCATIONS)["locations"]["new_ruin"]["display_name_zh"] == "古遺跡"


def test_location_identity_is_new_typed_and_never_renamed(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    duplicate = dict(NEW_LOCATION, location_id=fixture.LOCATION_ID)
    status, body = _send(editor, "create_location", LOCATIONS, duplicate)
    assert status == 422 and body["error"]["diagnostics"][0]["code"] == "duplicate_identifier"
    assert _send(editor, "create_location", LOCATIONS, dict(NEW_LOCATION, location_id="New Ruin"))[0] == 400
    assert _send(editor, "create_location", LOCATIONS, dict(NEW_LOCATION, kind="castle"))[0] == 422
    assert _send(editor, "create_location", LOCATIONS, dict(NEW_LOCATION, display_name_zh=""))[0] == 422
    status, _ = _send(editor, "set_location_field", LOCATIONS,
                      {"location_id": fixture.LOCATION_ID, "field": "id", "value": "renamed"})
    assert status == 400
    assert fixture.tree_digest(workspace) == before


def test_deleting_a_referenced_location_is_refused_without_cascade(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "delete_location", LOCATIONS, {"location_id": fixture.LOCATION_ID})
    assert (status, body["error"]["code"]) == (409, "deletion_refused")
    kinds = {row["kind"] for row in body["error"]["internal_references"]}
    assert kinds == {"location_ref", "anchor_key"}
    assert fixture.tree_digest(workspace) == before


def test_the_fresh_baseline_guard_refuses_an_anchor_the_snapshot_has_not_seen(workspace):
    """An external anchor added after the last read is still found on disk."""

    editor = Editor(workspace)
    # A new document binds the bare location: one anchor_room, keyed by its
    # own location_ref, so the shared core gate accepts the fresh disk world.
    outpost = fixture.settlement_data()
    outpost["id"] = "synthetic_outpost"
    outpost["location_ref"] = fixture.BARE_LOCATION_ID
    outpost["nodes"]["gate"]["anchor_key"] = fixture.BARE_LOCATION_ID
    outpost["wilderness_entry"] = None
    outpost["city_gate"] = None
    (workspace / "content/maps/settlements/synthetic_outpost.yaml").write_text(
        fixture.yaml_text(outpost), encoding="utf-8"
    )
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "delete_location", LOCATIONS, {"location_id": fixture.BARE_LOCATION_ID})
    assert (status, body["error"]["code"]) == (409, "deletion_refused")
    kinds = {row["kind"] for row in body["error"]["internal_references"]}
    assert {"location_ref", "anchor_key"} <= kinds
    assert fixture.tree_digest(workspace) == before


def test_an_unreferenced_location_needs_a_current_external_index(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "delete_location", LOCATIONS, {"location_id": fixture.BARE_LOCATION_ID})
    assert (status, body["error"]["code"], body["error"]["guard"]) == (409, "deletion_refused", "unavailable")
    assert fixture.tree_digest(workspace) == before
    fixture.write_reference_context(workspace)
    editor.reload()
    assert _send(editor, "delete_location", LOCATIONS, {"location_id": fixture.BARE_LOCATION_ID})[0] == 200
    assert fixture.BARE_LOCATION_ID not in _data(workspace, LOCATIONS)["locations"]
    # Undo recreates it through the same guards.
    assert editor.undo()[0] == 200
    assert fixture.BARE_LOCATION_ID in _data(workspace, LOCATIONS)["locations"]


# -- districts -------------------------------------------------------------------
def _landmark(domain, map_id=None, object_id=None, cell=None):
    return {"domain": domain, "map_id": map_id, "object_id": object_id, "cell": cell}


def test_district_landmarks_are_guarded_references(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    ghost = _landmark("settlement_node", fixture.SETTLEMENT_ID, "ghost")
    status, body = _send(editor, "set_district_field", DISTRICTS,
                         {"district_id": "synthetic_district", "field": "landmark", "value": ghost})
    assert status == 422 and any(item["code"] == "unknown_reference" for item in body["error"]["diagnostics"])
    assert fixture.tree_digest(workspace) == before
    # A blocked wilderness cell is saveable unfinished work, diagnosed.
    water = _landmark("wilderness_cell", cell=[20, 20])
    assert _send(editor, "set_district_field", DISTRICTS,
                 {"district_id": "synthetic_district", "field": "landmark", "value": water})[0] == 200
    _others_unchanged(before, fixture.tree_digest(workspace), DISTRICTS)
    assert any(item["code"] == "unreachable_landmark" for item in editor.state()["diagnostics"])
    assert _data(workspace, DISTRICTS)["districts"]["synthetic_district"]["landmark"]["cell"] == {"cell_x": 20, "cell_y": 20}


def test_district_membership_and_creation(workspace):
    editor = Editor(workspace)
    status, _ = _send(editor, "set_district_field", DISTRICTS,
                      {"district_id": "synthetic_district", "field": "membership", "value": {"kind": "region", "region_key": None}})
    assert status == 422
    assert _send(editor, "set_district_field", DISTRICTS,
                 {"district_id": "synthetic_district", "field": "membership",
                  "value": {"kind": "region", "region_key": "eastern_plains"}})[0] == 200
    district = _data(workspace, DISTRICTS)["districts"]["synthetic_district"]
    assert (district["kind"], district["region_key"]) == ("region", "eastern_plains")
    created = {
        "district_id": "second_district",
        "district_name_zh": "第二區",
        "landmark_name_zh": "石碑",
        "membership": {"kind": "voronoi", "region_key": None},
        "landmark": _landmark("location", object_id=fixture.BARE_LOCATION_ID),
    }
    assert _send(editor, "create_district", DISTRICTS, created)[0] == 200
    assert _data(workspace, DISTRICTS)["districts"]["second_district"]["landmark"]["object_id"] == fixture.BARE_LOCATION_ID
    # The location landmark now refers to the bare location: deletion explains it.
    status, body = _send(editor, "delete_location", LOCATIONS, {"location_id": fixture.BARE_LOCATION_ID})
    assert status == 409 and body["error"]["internal_references"][0]["kind"] == "landmark"


# -- footprint ----------------------------------------------------------------------
def test_footprint_cells_write_only_the_settlement_and_grow_the_mask(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    assert _send(editor, "set_footprint_cell", SETTLEMENT, {"settlement_id": fixture.SETTLEMENT_ID, "cell": [4, 6], "filled": True})[0] == 200
    _others_unchanged(before, fixture.tree_digest(workspace), SETTLEMENT)
    entry = _data(workspace, SETTLEMENT)["wilderness_entry"]
    # The saved value is the offset from the location cell (5, 5), never an origin.
    assert entry["offset"] == {"dx": -1, "dy": 0}
    assert entry["shape"] == [".#", "#."]
    footprint = editor.state()["world"]["settlements"][0]["footprint"]
    assert footprint["cells"] == [[4, 6], [5, 5]]
    assert footprint["origin"] == [4, 5]
    assert _send(editor, "set_footprint_cell", SETTLEMENT, {"settlement_id": fixture.SETTLEMENT_ID, "cell": [4, 6], "filled": False})[0] == 200
    assert _data(workspace, SETTLEMENT)["wilderness_entry"]["shape"] == [".#", ".."]
    # Clearing the last '#' is refused by the core mask rule.
    before = fixture.tree_digest(workspace)
    status, _ = _send(editor, "set_footprint_cell", SETTLEMENT, {"settlement_id": fixture.SETTLEMENT_ID, "cell": [5, 5], "filled": False})
    assert status == 422
    assert fixture.tree_digest(workspace) == before


def test_mask_growth_keeps_every_existing_cell(workspace):
    location_cell = (10, 10)
    entry = {"shape": ["#.", "##"], "offset": {"dx": 0, "dy": 0}}
    shape, offset = toggled_mask(entry, (8, 13), True, location_cell=location_cell)
    assert offset == {"dx": -2, "dy": 0}
    cells = {
        (location_cell[0] + offset["dx"] + c, location_cell[1] + offset["dy"] + r)
        for r, line in enumerate(shape)
        for c, ch in enumerate(line)
        if ch == "#"
    }
    assert cells == {(10, 10), (10, 11), (11, 11), (8, 13)}
    assert toggled_mask(entry, (30, 30), False, location_cell=location_cell) == (
        ["#.", "##"],
        {"dx": 0, "dy": 0},
    )
    with pytest.raises(Exception):
        toggled_mask(entry, (10 + MAX_MASK_SIDE, 10), True, location_cell=location_cell)


def test_the_removed_binding_command_is_unknown_and_writes_nothing(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    arguments = {"settlement_id": fixture.SETTLEMENT_ID, "anchor_cell": [6, 5], "local_anchor_m": [100, -50]}
    status, body = _send(editor, "set_binding", SETTLEMENT, arguments)
    assert status == 404
    assert body["error"]["code"] == "unknown_command"
    assert fixture.tree_digest(workspace) == before
    # The projection exposes only the derived frame, never editable coordinates.
    settlement = editor.state()["world"]["settlements"][0]
    assert "binding" not in settlement
    assert settlement["world_frame"]["anchor_cell"] == [5, 5]
    assert settlement["world_frame"]["local_anchor_m"] == [0, 0]


def test_footprint_conversion_refuses_a_location_changed_after_the_snapshot(workspace):
    """The absolute-cell contract never converts through a stale location cell."""

    editor = Editor(workspace)
    locations = _data(workspace, LOCATIONS)
    locations["locations"][fixture.LOCATION_ID]["cell"] = {"cell_x": 6, "cell_y": 6}
    (workspace / LOCATIONS).write_text(fixture.yaml_text(locations), encoding="utf-8")
    before = fixture.tree_digest(workspace)

    status, body = _send(
        editor,
        "set_footprint_cell",
        SETTLEMENT,
        {"settlement_id": fixture.SETTLEMENT_ID, "cell": [6, 5], "filled": True},
    )
    assert (status, body["error"]["code"]) == (409, "stale_document")
    assert "reread" in body["error"]["message"]
    assert fixture.tree_digest(workspace) == before

    # After the reread the same command converts through the new cell.
    editor.reload()
    assert _send(
        editor,
        "set_footprint_cell",
        SETTLEMENT,
        {"settlement_id": fixture.SETTLEMENT_ID, "cell": [6, 5], "filled": True},
    )[0] == 200
    entry = _data(workspace, SETTLEMENT)["wilderness_entry"]
    assert entry["offset"] == {"dx": 0, "dy": -1}
    assert entry["shape"] == ["#", "#"]
    footprint = editor.state()["world"]["settlements"][0]["footprint"]
    assert footprint["origin"] == [6, 5]
    assert footprint["cells"] == [[6, 5], [6, 6]]


def test_a_command_naming_another_document_is_cross_document(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "set_location_field", DISTRICTS,
                         {"location_id": fixture.LOCATION_ID, "field": "description", "value": "x"})
    assert (status, body["error"]["code"], body["error"]["owner"]) == (400, "cross_document", LOCATIONS)
    status, body = _send(editor, "set_footprint_cell", LOCATIONS,
                         {"settlement_id": fixture.SETTLEMENT_ID, "cell": [1, 1], "filled": True})
    assert (status, body["error"]["code"]) == (400, "cross_document")
    assert fixture.tree_digest(workspace) == before


# -- admission ------------------------------------------------------------------------
class Faults:
    def __init__(self):
        self.armed: dict[str, OSError] = {}

    def __call__(self, stage):
        if stage in self.armed:
            raise self.armed.pop(stage)


def test_geography_commands_are_rejected_while_paused(workspace):
    faults = Faults()
    editor = Editor(workspace, fault=faults)
    faults.armed["flush_directory"] = OSError(errno.EIO, "I/O error")
    status, body = _send(editor, "set_location_field", LOCATIONS,
                         {"location_id": fixture.LOCATION_ID, "field": "description", "value": "changed"})
    assert (status, body["error"]["code"]) == (500, "save_uncertain")
    before = fixture.tree_digest(workspace)
    for name, document, arguments in (
        ("move_control_point", CONTINENT, {"feature": RIVER, "index": 0, "point": [20, 25]}),
        ("create_location", LOCATIONS, NEW_LOCATION),
        ("set_footprint_cell", SETTLEMENT, {"settlement_id": fixture.SETTLEMENT_ID, "cell": [6, 6], "filled": True}),
    ):
        status, body = _send(editor, name, document, arguments)
        assert (status, body["error"]["code"], body["error"]["reason"]) == (423, "write_paused", "uncertain_durability")
    assert fixture.tree_digest(workspace) == before


def test_geography_commands_are_rejected_while_the_preview_is_stale(workspace):
    editor = Editor(workspace)
    (workspace / DISTRICTS).write_text("version: 1\nkind: [unclosed\n", encoding="utf-8")
    editor.reload()
    before = fixture.tree_digest(workspace)
    for name, document, arguments in (
        ("move_control_point", CONTINENT, {"feature": RIVER, "index": 0, "point": [20, 25]}),
        ("create_location", LOCATIONS, NEW_LOCATION),
        ("set_footprint_cell", SETTLEMENT, {"settlement_id": fixture.SETTLEMENT_ID, "cell": [6, 6], "filled": True}),
    ):
        status, body = _send(editor, name, document, arguments)
        assert (status, body["error"]["code"], body["error"]["reason"]) == (423, "write_paused", "stale_preview")
    assert fixture.tree_digest(workspace) == before



def test_undoing_a_creation_that_gained_a_reference_is_refused_and_keeps_history(workspace):
    """Undo is the same guarded removal: a reference written on disk (not yet
    adopted) refuses it, names the referrer and leaves disk and history."""

    editor = Editor(workspace)
    assert _send(editor, "create_location", LOCATIONS, NEW_LOCATION)[0] == 200
    data = fixture.districts_data()
    data["districts"]["synthetic_district"]["landmark"] = {
        "domain": "location", "map_id": None, "object_id": "new_ruin", "cell": None,
    }
    (workspace / DISTRICTS).write_text(fixture.yaml_text(data), encoding="utf-8")
    before = fixture.tree_digest(workspace)
    head = editor.state()["history"]["undo"]
    status, body = editor.undo()
    assert (status, body["error"]["code"], body["error"]["guard"]) == (409, "deletion_refused", "internal")
    assert DISTRICTS in body["error"]["message"]
    assert fixture.tree_digest(workspace) == before
    assert editor.state()["history"]["undo"] == head
