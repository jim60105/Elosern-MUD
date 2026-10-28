"""Interior commands over the real ASGI app and a synthetic workspace.

Every assertion inspects the disk: a source command writes only its interior
document, a layout command only its layout document, a rejection leaves every
byte unchanged, and room IDs are never renamed. The synthetic interior
``synthetic_hall`` has rooms ``front`` and ``back`` joined by ``front>back``
(``in``) and ``back>front`` (``out``); its exterior opens ``front`` onto the
settlement node ``yard``.
"""

from __future__ import annotations

import pytest
from ruamel.yaml import YAML

import synthetic_workspace as fixture
from editor_client import Editor, sha

HALL = fixture.INTERIOR_ID
INTERIOR = f"content/maps/interiors/{HALL}.yaml"
LAYOUT = f"content/map-editor-layouts/{HALL}.yaml"
ANNEX = "content/maps/interiors/synthetic_annex.yaml"
ANNEX_LAYOUT = "content/map-editor-layouts/synthetic_annex.yaml"


def _send(editor: Editor, name: str, document: str, arguments: dict, **overrides):
    path = editor.workspace / document
    expected = sha(path) if path.exists() else "absent"
    return editor.raw(name, editor.envelope(document, expected, arguments, **overrides))


def _data(workspace, document=INTERIOR):
    return YAML(typ="safe", pure=True).load((workspace / document).read_text(encoding="utf-8"))


def _changed(before: dict, workspace) -> set[str]:
    after = fixture.tree_digest(workspace)
    return {path for path in set(before) | set(after) if before.get(path) != after.get(path)}


def _fields(name="倉庫", desc="A synthetic store room.", scene=None, art=None) -> dict:
    return {"name_zh": name, "desc_zh": desc, "scene_archetype": scene, "art_key": art}


def _create_room(editor, room_id="store", interior=HALL, document=INTERIOR, **fields):
    return _send(editor, "create_room", document, {"interior_id": interior, "room_id": room_id,
                                                   "fields": _fields(**fields)})


def _create_annex(editor, room_id="annex_lobby"):
    return _send(editor, "create_interior", ANNEX, {"interior_id": "synthetic_annex", "room_id": room_id,
                                                    "fields": _fields(name="別館")})


def _connection(source, destination, label, **extra):
    return {"interior_id": HALL, "source": source, "destination": destination, "label": label, **extra}


def _place_reference(room_id: str, interior: str = HALL) -> dict:
    return {f"interior_room:{interior}:{room_id}": [{
        "source": f"place:{room_id}", "source_domain": "places", "source_file": "external/declarations.txt",
        "target": {"domain": "interior_room", "map_id": interior, "object_id": room_id, "cell": None}}]}


# -- documents and rooms ------------------------------------------------------------
def test_a_standalone_interior_writes_only_its_document_and_no_service_or_layout(workspace):
    fixture.write_reference_context(workspace)
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    status, body = _create_annex(editor)
    assert status == 200 and body["changed"] is True
    assert _changed(before, workspace) == {ANNEX}
    data = _data(workspace, ANNEX)
    assert (data["exterior"], data["connections"], data["interior_links"]) == (None, [], [])
    assert list(data["rooms"]) == ["annex_lobby"]
    state = editor.state()
    annex = next(row for row in state["world"]["interiors"] if row["id"] == "synthetic_annex")
    assert annex["layout_relative_path"] is None
    assert [row for row in state["diagnostics"] if row["category"] == "structure"] == []
    # Undo is object-removing: with a current index it removes the file.
    assert editor.undo()[0] == 200
    assert not (workspace / ANNEX).exists()
    assert editor.redo()[0] == 200
    assert list(_data(workspace, ANNEX)["rooms"]) == ["annex_lobby"]


def test_undoing_a_creation_needs_a_current_index(workspace):
    editor = Editor(workspace)
    assert _create_room(editor)[0] == 200
    after = fixture.tree_digest(workspace)
    status, body = editor.undo()
    assert status == 409 and body["error"]["guard"] == "unavailable"
    assert fixture.tree_digest(workspace) == after
    assert "store" in _data(workspace)["rooms"]


def test_a_new_room_writes_only_the_interior_and_never_a_layout(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    status, body = _create_room(editor)
    assert status == 200, body
    assert _changed(before, workspace) == {INTERIOR}
    assert not (workspace / "content/map-editor-layouts").exists()
    room = next(r for r in next(i for i in editor.state()["world"]["interiors"] if i["id"] == HALL)["rooms"]
                if r["id"] == "store")
    assert room["layout_position"] is None
    assert _data(workspace)["rooms"]["store"] == _fields()


def test_duplicating_a_room_copies_values_and_no_relationship(workspace):
    editor = Editor(workspace)
    connections = _data(workspace)["connections"]
    before = fixture.tree_digest(workspace)
    status, _ = _send(editor, "duplicate_room", INTERIOR, {"interior_id": HALL, "room_id": "front",
                                                          "new_room_id": "front_copy"})
    assert status == 200
    assert _changed(before, workspace) == {INTERIOR}
    data = _data(workspace)
    assert data["rooms"]["front_copy"] == data["rooms"]["front"]
    assert data["connections"] == connections
    assert data["exterior"]["room"] == "front"


@pytest.mark.parametrize(
    ("name", "document", "arguments", "status", "code"),
    [
        ("create_room", INTERIOR, {"interior_id": HALL, "room_id": "back", "fields": _fields()}, 422, "validation_failed"),
        ("duplicate_room", INTERIOR, {"interior_id": HALL, "room_id": "front", "new_room_id": "back"}, 422,
         "validation_failed"),
        ("create_room", INTERIOR, {"interior_id": HALL, "room_id": "store", "fields": {"name_zh": "x"}}, 400,
         "invalid_command"),
        ("create_room", INTERIOR, {"interior_id": HALL, "room_id": "store", "fields": _fields(name="")}, 422,
         "validation_failed"),
        ("create_room", ANNEX, {"interior_id": HALL, "room_id": "store", "fields": _fields()}, 400, "cross_document"),
        ("set_room_fields", INTERIOR, {"interior_id": HALL, "room_id": "front", "fields": {"id": "renamed"}}, 400,
         "invalid_command"),
        ("set_room_fields", INTERIOR, {"interior_id": HALL, "room_id": "ghost", "fields": {"name_zh": "x"}}, 422,
         "validation_failed"),
        ("create_interior", ANNEX, {"interior_id": "synthetic_annex", "room_id": "front", "fields": _fields()}, 422,
         "validation_failed"),
        ("create_interior", INTERIOR, {"interior_id": HALL, "room_id": "fresh", "fields": _fields()}, 422,
         "validation_failed"),
    ],
)
def test_rejected_room_commands_write_nothing(workspace, name, document, arguments, status, code):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    answer = _send(editor, name, document, arguments)
    assert answer[0] == status and answer[1]["error"]["code"] == code
    assert fixture.tree_digest(workspace) == before


def test_a_room_id_of_another_interior_is_refused_on_the_fresh_disk(workspace):
    fixture.write_reference_context(workspace)
    editor = Editor(workspace)
    assert _create_annex(editor)[0] == 200
    # Another interior gains `cellar` on disk; the published snapshot is older.
    data = _data(workspace)
    data["rooms"]["cellar"] = _fields(name="地窖")
    (workspace / INTERIOR).write_text(fixture.yaml_text(data), encoding="utf-8")
    before = fixture.tree_digest(workspace)
    status, body = _create_room(editor, "cellar", interior="synthetic_annex", document=ANNEX)
    assert status == 422
    assert [row["code"] for row in body["error"]["diagnostics"]] == ["duplicate_room_identity"]
    assert fixture.tree_digest(workspace) == before


def test_a_duplicate_the_baseline_already_holds_does_not_block_other_edits(workspace):
    data = _data(workspace)
    annex = {"version": 1, "kind": "interior", "id": "synthetic_annex",
             "rooms": {"back": _fields(name="重複")}, "connections": [], "interior_links": [], "exterior": None}
    (workspace / ANNEX).write_text(fixture.yaml_text(annex), encoding="utf-8")
    assert "back" in data["rooms"]
    editor = Editor(workspace)
    status, body = _send(editor, "set_room_fields", INTERIOR, {"interior_id": HALL, "room_id": "front",
                                                               "fields": {"name_zh": "新前廳"}})
    assert status == 200, body
    assert _data(workspace)["rooms"]["front"]["name_zh"] == "新前廳"


def test_editing_prose_keeps_the_room_identity_and_its_service_join(workspace):
    fixture.write_reference_context(workspace, incoming=_place_reference("back"))
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    status, _ = _send(editor, "set_room_fields", INTERIOR, {"interior_id": HALL, "room_id": "back",
                                                           "fields": {"name_zh": "改名", "desc_zh": "新描述"}})
    assert status == 200
    assert _changed(before, workspace) == {INTERIOR}
    assert list(_data(workspace)["rooms"]) == ["front", "back"]
    state = editor.state()
    assert [row["id"] for row in state["world"]["interiors"]] == [HALL]
    assert state["external_context_status"]["current"] is True
    assert state["external_incoming_references"][f"interior_room:{HALL}:back"][0]["source"] == "place:back"


def test_room_scene_status_follows_the_current_index(workspace):
    data = _data(workspace)
    data["rooms"]["front"]["scene_archetype"] = "synthetic_scene"
    (workspace / INTERIOR).write_text(fixture.yaml_text(data), encoding="utf-8")
    editor = Editor(workspace)
    rooms = {r["id"]: r for r in editor.state()["world"]["interiors"][0]["rooms"]}
    assert (rooms["front"]["scene_status"], rooms["back"]["scene_status"]) == ("unavailable", "none")


# -- deletion -------------------------------------------------------------------------
def test_room_deletion_is_refused_by_every_map_reference_and_never_cascades(workspace):
    fixture.write_reference_context(workspace)
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    # `front` is named by both connections and the exterior; `back` by both connections.
    for room_id, kinds in (("front", {"connection", "exterior"}), ("back", {"connection"})):
        status, body = _send(editor, "delete_room", INTERIOR, {"interior_id": HALL, "room_id": room_id})
        assert status == 409 and body["error"]["guard"] == "internal"
        assert {row["kind"] for row in body["error"]["internal_references"]} == kinds
    assert fixture.tree_digest(workspace) == before


def test_another_interiors_link_and_a_landmark_refuse_room_deletion(workspace):
    fixture.write_reference_context(workspace)
    editor = Editor(workspace)
    assert _create_room(editor, "store")[0] == 200
    annex = {"version": 1, "kind": "interior", "id": "synthetic_annex", "rooms": {"annex_lobby": _fields()},
             "connections": [], "exterior": None,
             "interior_links": [{"source_room": "annex_lobby", "target_interior": HALL, "target_room": "store",
                                 "label": "door", "return_label": None}]}
    (workspace / ANNEX).write_text(fixture.yaml_text(annex), encoding="utf-8")
    editor.reload()
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "delete_room", INTERIOR, {"interior_id": HALL, "room_id": "store"})
    assert status == 409 and body["error"]["internal_references"][0]["kind"] == "interior_link"
    # Removing the whole document is refused by the same link.
    status, body = _send(editor, "delete_interior", INTERIOR, {"interior_id": HALL})
    assert status == 409 and body["error"]["guard"] == "internal"
    assert "interior_link" in {row["kind"] for row in body["error"]["internal_references"]}
    assert fixture.tree_digest(workspace) == before


def test_a_district_landmark_refuses_room_deletion(workspace):
    fixture.write_reference_context(workspace)
    editor = Editor(workspace)
    assert _create_room(editor, "store")[0] == 200
    districts = YAML(typ="safe", pure=True).load((workspace / "content/maps/districts.yaml").read_text("utf-8"))
    districts["districts"]["synthetic_district"]["landmark"] = {
        "domain": "interior_room", "map_id": HALL, "object_id": "store", "cell": None}
    (workspace / "content/maps/districts.yaml").write_text(fixture.yaml_text(districts), encoding="utf-8")
    editor.reload()
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "delete_room", INTERIOR, {"interior_id": HALL, "room_id": "store"})
    assert status == 409 and body["error"]["internal_references"][0]["kind"] == "landmark"
    assert fixture.tree_digest(workspace) == before


def test_an_unreferenced_room_is_deleted_and_undo_restores_the_bytes(workspace):
    fixture.write_reference_context(workspace)
    editor = Editor(workspace)
    assert _create_room(editor, "store")[0] == 200
    saved = (workspace / INTERIOR).read_bytes()
    before = fixture.tree_digest(workspace)
    status, _ = _send(editor, "delete_room", INTERIOR, {"interior_id": HALL, "room_id": "store"})
    assert status == 200
    assert _changed(before, workspace) == {INTERIOR}
    assert "store" not in _data(workspace)["rooms"]
    assert editor.undo()[0] == 200
    assert (workspace / INTERIOR).read_bytes() == saved


def test_a_service_joined_or_unindexed_room_is_refused_at_execution(workspace):
    editor = Editor(workspace)
    assert _create_room(editor, "store")[0] == 200
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "delete_room", INTERIOR, {"interior_id": HALL, "room_id": "store"})
    assert status == 409 and body["error"]["guard"] == "unavailable"
    fixture.write_reference_context(workspace, incoming=_place_reference("store"))
    editor.reload()
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "delete_room", INTERIOR, {"interior_id": HALL, "room_id": "store"})
    assert status == 409 and body["error"]["refusals"][0]["status"] == "referenced"
    assert fixture.tree_digest(workspace) == before


def test_deleting_an_interior_removes_its_document_and_leaves_its_layout(workspace):
    fixture.write_reference_context(workspace)
    editor = Editor(workspace)
    assert _create_annex(editor)[0] == 200
    assert _send(editor, "arrange_interior_layout", ANNEX_LAYOUT, {
        "interior_id": "synthetic_annex", "positions": [{"room_id": "annex_lobby", "x": 2, "y": 1}]})[0] == 200
    saved = (workspace / ANNEX).read_bytes()
    before = fixture.tree_digest(workspace)
    status, _ = _send(editor, "delete_interior", ANNEX, {"interior_id": "synthetic_annex"})
    assert status == 200
    assert _changed(before, workspace) == {ANNEX}
    assert (workspace / ANNEX_LAYOUT).exists()
    assert editor.undo()[0] == 200
    assert (workspace / ANNEX).read_bytes() == saved


def test_deleting_an_interior_without_a_current_index_is_refused(workspace):
    # Its rooms are removed objects; an index that is not current proves nothing.
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "delete_interior", INTERIOR, {"interior_id": HALL})
    assert status == 409 and body["error"]["guard"] == "unavailable"
    assert fixture.tree_digest(workspace) == before


# -- connections -----------------------------------------------------------------------
def test_a_two_way_connection_is_one_operation_and_one_history_entry(workspace):
    fixture.write_reference_context(workspace)
    editor = Editor(workspace)
    assert _create_room(editor, "store")[0] == 200
    after_room = (workspace / INTERIOR).read_bytes()
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "create_connection", INTERIOR, _connection("back", "store", "東 / 往倉庫", return_label="西"))
    assert status == 200, body
    assert _changed(before, workspace) == {INTERIOR}
    triples = {(c["source"], c["destination"], c["label"]) for c in _data(workspace)["connections"]}
    assert {("back", "store", "東 / 往倉庫"), ("store", "back", "西")} <= triples
    # One undo removes both entries.
    assert editor.undo()[0] == 200
    assert (workspace / INTERIOR).read_bytes() == after_room


@pytest.mark.parametrize(
    ("arguments", "status", "code"),
    [
        (_connection("front", "back", "in", return_label=None), 422, "validation_failed"),  # duplicate
        (_connection("front", "ghost", "x", return_label=None), 422, "validation_failed"),
        (_connection("front", "front", "loop", return_label=None), 422, "validation_failed"),
        (_connection("front", "back", "   ", return_label=None), 400, "invalid_command"),
        (_connection("front", "back", " padded", return_label=None), 400, "invalid_command"),
        # The forward triple is new but the reverse one exists: nothing is written.
        (_connection("front", "back", "new", return_label="out"), 422, "validation_failed"),
        (_connection("front", "back", "new"), 400, "invalid_command"),
    ],
)
def test_rejected_connections_write_nothing(workspace, arguments, status, code):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    answer = _send(editor, "create_connection", INTERIOR, arguments)
    assert answer[0] == status and answer[1]["error"]["code"] == code
    assert fixture.tree_digest(workspace) == before


def test_a_connection_is_relabelled_retargeted_and_deleted_in_its_document(workspace):
    editor = Editor(workspace)
    assert _create_room(editor, "store")[0] == 200
    before = fixture.tree_digest(workspace)
    status, _ = _send(editor, "set_connection", INTERIOR, {**_connection("front", "back", "in"),
                                                          "value": {"source": "front", "destination": "store",
                                                                    "label": "裡面"}})
    assert status == 200
    assert _changed(before, workspace) == {INTERIOR}
    triples = [(c["source"], c["destination"], c["label"]) for c in _data(workspace)["connections"]]
    assert triples == [("front", "store", "裡面"), ("back", "front", "out")]
    status, _ = _send(editor, "delete_connection", INTERIOR, _connection("back", "front", "out"))
    assert status == 200
    assert [(c["source"], c["destination"]) for c in _data(workspace)["connections"]] == [("front", "store")]
    status, body = _send(editor, "delete_connection", INTERIOR, _connection("back", "front", "out"))
    assert status == 422 and body["error"]["diagnostics"][0]["code"] == "unknown_connection"


# -- layout ----------------------------------------------------------------------------
def test_arranging_writes_only_the_layout_and_never_world_geometry(workspace):
    editor = Editor(workspace)
    fingerprint = editor.state()["world"]["fingerprint"]
    before = fixture.tree_digest(workspace)
    positions = [{"room_id": "front", "x": 0, "y": 0}, {"room_id": "back", "x": 1, "y": 0}]
    status, body = _send(editor, "arrange_interior_layout", LAYOUT, {"interior_id": HALL, "positions": positions})
    assert status == 200 and body["changed"] is True
    assert _changed(before, workspace) == {LAYOUT}
    state = editor.state()
    assert state["world"]["fingerprint"] == fingerprint
    assert {r["id"]: r["layout_position"] for r in state["world"]["interiors"][0]["rooms"]} == {
        "front": [0, 0], "back": [1, 0]}
    # Rooms carry no coordinate or distance field of any kind.
    assert set(state["world"]["interiors"][0]["rooms"][0]) == {
        "id", "qualified_ref", "name_zh", "desc_zh", "scene_archetype", "art_key", "layout_position", "scene_status"}
    # The same positions again write nothing.
    status, body = _send(editor, "arrange_interior_layout", LAYOUT, {"interior_id": HALL, "positions": positions})
    assert status == 200 and body["changed"] is False
    # A merge keeps the other rooms' positions.
    assert _send(editor, "arrange_interior_layout", LAYOUT, {
        "interior_id": HALL, "positions": [{"room_id": "back", "x": 4, "y": 2}]})[0] == 200
    assert _data(workspace, LAYOUT)["positions"] == {"front": {"x": 0, "y": 0}, "back": {"x": 4, "y": 2}}


@pytest.mark.parametrize(
    ("document", "positions", "status", "code"),
    [
        (LAYOUT, [{"room_id": "front", "x": 0, "y": 0}, {"room_id": "front", "x": 1, "y": 0}], 400, "invalid_command"),
        (LAYOUT, [{"room_id": "front", "x": 100_001, "y": 0}], 400, "invalid_command"),
        (LAYOUT, [{"room_id": "front", "x": 1.5, "y": 0}], 400, "invalid_command"),
        (LAYOUT, [{"room_id": "ghost", "x": 0, "y": 0}], 422, "validation_failed"),
        (LAYOUT, [], 400, "invalid_command"),
        (INTERIOR, [{"room_id": "front", "x": 0, "y": 0}], 400, "cross_document"),
    ],
)
def test_rejected_arrangements_write_nothing(workspace, document, positions, status, code):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    answer = _send(editor, "arrange_interior_layout", document, {"interior_id": HALL, "positions": positions})
    assert answer[0] == status and answer[1]["error"]["code"] == code
    assert fixture.tree_digest(workspace) == before
