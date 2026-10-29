"""Entrance relationships over the real ASGI app and a synthetic workspace.

Every assertion inspects the disk: each command writes exactly its owning
document, a two-way meaning is one record, a refusal names its relationship
and field and leaves every byte unchanged, the starting-room entry never
gains a return, and removing a reference then deleting its target are two
separate operations with nothing cascading.

The synthetic settlement ``synthetic_town`` has nodes ``gate`` and ``yard``,
one wilderness gate ``n`` onto ``gate`` and a starting-room entry onto
``gate``; the interior ``synthetic_hall`` (rooms ``front``, ``back``) opens
``front`` onto ``yard``.
"""

from __future__ import annotations

from ruamel.yaml import YAML

import synthetic_workspace as fixture
from editor_client import Editor, sha

TOWN = fixture.SETTLEMENT_ID
HALL = fixture.INTERIOR_ID
SETTLEMENT = f"content/maps/settlements/{TOWN}.yaml"
INTERIOR = f"content/maps/interiors/{HALL}.yaml"
ANNEX = "content/maps/interiors/synthetic_annex.yaml"
GATE = f"settlement_node:{TOWN}:gate"
YARD = f"settlement_node:{TOWN}:yard"
FRONT = f"interior_room:{HALL}:front"
BACK = f"interior_room:{HALL}:back"


def _send(editor: Editor, name: str, document: str, arguments: dict):
    path = editor.workspace / document
    expected = sha(path) if path.exists() else "absent"
    return editor.raw(name, editor.envelope(document, expected, arguments))


def _data(workspace, document):
    return YAML(typ="safe", pure=True).load((workspace / document).read_text(encoding="utf-8"))


def _changed(before: dict, workspace) -> set[str]:
    after = fixture.tree_digest(workspace)
    return {path for path in set(before) | set(after) if before.get(path) != after.get(path)}


def _annex(editor):
    fields = {"name_zh": "別館", "desc_zh": "A synthetic annex.", "scene_archetype": None, "art_key": None}
    status, body = _send(editor, "create_interior", ANNEX,
                         {"interior_id": "synthetic_annex", "room_id": "annex_lobby", "fields": fields})
    assert status == 200, body


def _diagnostic(body) -> dict:
    [row] = body["error"]["diagnostics"]
    return row


# -- settlement-owned ---------------------------------------------------------------
def test_a_wilderness_gate_is_created_retargeted_and_removed_in_its_settlement_only(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "create_wilderness_gate", SETTLEMENT,
                         {"settlement_id": TOWN, "return_direction": "e", "node": YARD})
    assert status == 200, body
    assert _changed(before, workspace) == {SETTLEMENT}
    gates = _data(workspace, SETTLEMENT)["wilderness_entry"]["gates"]
    assert gates == [{"return_direction": "n", "destination_node": "gate"},
                     {"return_direction": "e", "destination_node": "yard"}]
    status, body = _send(editor, "set_wilderness_gate", SETTLEMENT, {
        "settlement_id": TOWN, "return_direction": "e", "value": {"return_direction": "w", "node": YARD}})
    assert status == 200, body
    assert _data(workspace, SETTLEMENT)["wilderness_entry"]["gates"][1] == {
        "return_direction": "w", "destination_node": "yard"}
    status, body = _send(editor, "delete_wilderness_gate", SETTLEMENT, {"settlement_id": TOWN, "return_direction": "w"})
    assert status == 200, body
    assert _changed(before, workspace) <= {SETTLEMENT}
    assert _data(workspace, SETTLEMENT)["wilderness_entry"]["gates"] == gates[:1]
    # Each step was one operation: two undos restore the two-gate state.
    for _ in range(2):
        assert editor.undo()[0] == 200
    assert len(_data(workspace, SETTLEMENT)["wilderness_entry"]["gates"]) == 2


def test_the_projection_carries_each_gate_approach_cell_from_the_core(workspace):
    editor = Editor(workspace)
    settlement = editor.state()["world"]["settlements"][0]
    # A point entry: the approach is the anchor cell itself.
    assert settlement["wilderness_entry"]["gates"][0]["approach_cell"] == [5, 5]


def test_the_last_gate_is_refused_and_the_whole_entry_is_an_explicit_removal(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "delete_wilderness_gate", SETTLEMENT, {"settlement_id": TOWN, "return_direction": "n"})
    assert status == 422
    row = _diagnostic(body)
    assert (row["code"], row["relationship"], row["owner"]) == ("last_gate", "wilderness_gate", SETTLEMENT)
    assert fixture.tree_digest(workspace) == before
    status, body = _send(editor, "remove_wilderness_entry", SETTLEMENT, {"settlement_id": TOWN})
    assert status == 200, body
    assert _changed(before, workspace) == {SETTLEMENT}
    assert _data(workspace, SETTLEMENT)["wilderness_entry"] is None
    # A first gate creates a one-cell point entry at the location cell.
    status, body = _send(editor, "create_wilderness_gate", SETTLEMENT,
                         {"settlement_id": TOWN, "return_direction": "s", "node": YARD})
    assert status == 200, body
    assert _data(workspace, SETTLEMENT)["wilderness_entry"] == {
        "shape": ["#"], "offset": {"dx": 0, "dy": 0},
        "gates": [{"return_direction": "s", "destination_node": "yard"}]}


def test_a_duplicate_gate_direction_is_refused_unwritten(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "create_wilderness_gate", SETTLEMENT,
                         {"settlement_id": TOWN, "return_direction": "n", "node": YARD})
    assert status == 422
    assert _diagnostic(body)["code"] == "duplicate_gate_direction"
    assert fixture.tree_digest(workspace) == before


def test_the_starting_room_entry_stays_one_way(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    for extra in ({"return_label": "back"}, {"return": {"direction": "s"}}):
        value = {"node": YARD, "exit_key": "Gate", "exit_aliases": [], **extra}
        status, body = _send(editor, "set_city_gate", SETTLEMENT, {"settlement_id": TOWN, "value": value})
        assert status == 400
        assert next(iter(extra)) in body["error"]["message"]
    assert fixture.tree_digest(workspace) == before
    status, body = _send(editor, "set_city_gate", SETTLEMENT, {"settlement_id": TOWN, "value": {
        "node": YARD, "exit_key": "Way in", "exit_aliases": ["in", "way"]}})
    assert status == 200, body
    assert _changed(before, workspace) == {SETTLEMENT}
    assert _data(workspace, SETTLEMENT)["city_gate"] == {"node": "yard", "exit_key": "Way in",
                                                         "exit_aliases": ["in", "way"]}
    status, body = _send(editor, "set_city_gate", SETTLEMENT, {"settlement_id": TOWN, "value": None})
    assert status == 200, body
    assert _data(workspace, SETTLEMENT)["city_gate"] is None


def test_invalid_settlement_endpoints_name_their_relationship_and_field(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    cases = [
        ("create_wilderness_gate", {"settlement_id": TOWN, "return_direction": "e", "node": "Yard"},
         "invalid_endpoint", "arguments.node", "wilderness_gate"),
        ("create_wilderness_gate", {"settlement_id": TOWN, "return_direction": "e", "node": FRONT},
         "wrong_domain", "arguments.node", "wilderness_gate"),
        ("create_wilderness_gate", {"settlement_id": TOWN, "return_direction": "e", "node": "settlement_node:other:yard"},
         "wrong_map", "arguments.node", "wilderness_gate"),
        ("create_wilderness_gate", {"settlement_id": TOWN, "return_direction": "e", "node": f"settlement_node:{TOWN}:nowhere"},
         "unknown_target", "arguments.node", "wilderness_gate"),
        ("set_city_gate", {"settlement_id": TOWN, "value": {"node": "location:synthetic_place", "exit_key": "x",
                                                            "exit_aliases": []}},
         "wrong_domain", "arguments.value.node", "city_gate"),
    ]
    for name, arguments, code, field, relationship in cases:
        status, body = _send(editor, name, SETTLEMENT, arguments)
        assert status == 422, (name, arguments, body)
        row = _diagnostic(body)
        assert (row["code"], row["field_path"], row["relationship"], row["owner"]) == (
            code, field, relationship, SETTLEMENT)
    assert fixture.tree_digest(workspace) == before


# -- interior-owned -----------------------------------------------------------------
def test_an_exterior_edit_writes_only_its_interior_with_both_meanings(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    value = {"room": BACK, "node": GATE, "doorway_key": "Back door", "doorway_aliases": ["back"]}
    status, body = _send(editor, "set_exterior", INTERIOR, {"interior_id": HALL, "value": value})
    assert status == 200, body
    assert _changed(before, workspace) == {INTERIOR}
    assert _data(workspace, INTERIOR)["exterior"] == {
        "settlement": TOWN, "node": "gate", "room": "back", "doorway_key": "Back door", "doorway_aliases": ["back"]}
    # The settlement side derives the relationship: nothing mirrored there.
    assert _data(workspace, SETTLEMENT) == fixture.settlement_data()
    assert editor.undo()[0] == 200
    assert fixture.tree_digest(workspace) == before


def test_a_two_way_link_is_one_record_and_one_write(workspace):
    editor = Editor(workspace)
    _annex(editor)
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "create_interior_link", INTERIOR, {
        "interior_id": HALL, "source": BACK, "target": "interior_room:synthetic_annex:annex_lobby",
        "label": "passage", "return_label": "hall"})
    assert status == 200, body
    assert _changed(before, workspace) == {INTERIOR}
    assert _data(workspace, INTERIOR)["interior_links"] == [{
        "source_room": "back", "target_interior": "synthetic_annex", "target_room": "annex_lobby",
        "label": "passage", "return_label": "hall"}]
    status, body = _send(editor, "set_interior_link", INTERIOR, {
        "interior_id": HALL, "source": BACK, "target": "interior_room:synthetic_annex:annex_lobby", "label": "passage",
        "value": {"source": FRONT, "target": "interior_room:synthetic_annex:annex_lobby", "label": "stair",
                  "return_label": None}})
    assert status == 200, body
    assert _data(workspace, INTERIOR)["interior_links"][0] == {
        "source_room": "front", "target_interior": "synthetic_annex", "target_room": "annex_lobby",
        "label": "stair", "return_label": None}
    assert _changed(before, workspace) == {INTERIOR}
    # A link is not a qualified object: its removal needs no reference index.
    status, body = _send(editor, "delete_interior_link", INTERIOR, {
        "interior_id": HALL, "source": FRONT, "target": "interior_room:synthetic_annex:annex_lobby", "label": "stair"})
    assert status == 200, body
    assert _data(workspace, INTERIOR)["interior_links"] == []


def test_invalid_interior_endpoints_name_their_relationship_and_field(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    link = {"interior_id": HALL, "source": FRONT, "label": "x", "return_label": None}
    cases = [
        ("set_exterior", {"interior_id": HALL, "value": {"room": FRONT, "node": BACK, "doorway_key": "d",
                                                         "doorway_aliases": []}},
         "wrong_domain", "arguments.value.node", "exterior"),
        ("set_exterior", {"interior_id": HALL, "value": {"room": "interior_room:other:front", "node": YARD,
                                                         "doorway_key": "d", "doorway_aliases": []}},
         "wrong_map", "arguments.value.room", "exterior"),
        ("set_exterior", {"interior_id": HALL, "value": {"room": FRONT, "node": f"settlement_node:{TOWN}:none",
                                                         "doorway_key": "d", "doorway_aliases": []}},
         "unknown_target", "arguments.value.node", "exterior"),
        ("create_interior_link", {**link, "target": "前廳"}, "invalid_endpoint", "arguments.target", "interior_link"),
        ("create_interior_link", {**link, "target": YARD}, "wrong_domain", "arguments.target", "interior_link"),
        ("create_interior_link", {**link, "target": "interior_room:missing:room"}, "unknown_target",
         "arguments.target", "interior_link"),
        ("create_interior_link", {**link, "target": FRONT}, "self_loop", "arguments.target", "interior_link"),
    ]
    for name, arguments, code, field, relationship in cases:
        status, body = _send(editor, name, INTERIOR, arguments)
        assert status == 422, (name, arguments, body)
        row = _diagnostic(body)
        assert (row["code"], row["field_path"], row["relationship"], row["owner"]) == (
            code, field, relationship, INTERIOR)
    assert fixture.tree_digest(workspace) == before


def test_a_target_removed_on_disk_after_the_projection_is_refused_by_the_gate_with_its_relationship(workspace):
    editor = Editor(workspace)
    _annex(editor)
    # The annex disappears from disk; the published projection still lists it.
    (workspace / ANNEX).unlink()
    before = fixture.tree_digest(workspace)
    status, body = editor.raw("create_interior_link", editor.envelope(INTERIOR, sha(workspace / INTERIOR), {
        "interior_id": HALL, "source": FRONT, "target": "interior_room:synthetic_annex:annex_lobby",
        "label": "x", "return_label": None}))
    assert status == 422, body
    rows = [row for row in body["error"]["diagnostics"] if row.get("relationship")]
    assert rows and rows[0]["relationship"] == "interior_link" and rows[0]["owner"] == INTERIOR
    assert fixture.tree_digest(workspace) == before


def test_a_new_duplicate_doorway_is_refused_and_another_name_is_accepted(workspace):
    editor = Editor(workspace)
    _annex(editor)
    before = fixture.tree_digest(workspace)
    value = {"room": "interior_room:synthetic_annex:annex_lobby", "node": YARD, "doorway_key": "Door",
             "doorway_aliases": []}
    status, body = _send(editor, "set_exterior", ANNEX, {"interior_id": "synthetic_annex", "value": value})
    assert status == 422
    assert body["error"]["diagnostics"][0]["code"] == "duplicate_doorway"
    assert fixture.tree_digest(workspace) == before
    # Another doorway name on the same node is fine.
    status, body = _send(editor, "set_exterior", ANNEX, {"interior_id": "synthetic_annex",
                                                          "value": {**value, "doorway_key": "Annex"}})
    assert status == 200, body


def test_unlink_then_delete_are_separate_operations_and_nothing_cascades(workspace):
    fixture.write_reference_context(workspace)
    editor = Editor(workspace)
    # `yard` is named by two roads, the hall's exterior and the district landmark.
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "delete_nodes", SETTLEMENT, {"settlement_id": TOWN, "node_ids": ["gate"]})
    assert status == 409 and body["error"]["guard"] == "internal"
    kinds = {row["kind"] for row in body["error"]["internal_references"]}
    assert {"wilderness_gate", "city_gate", "road"} <= kinds
    assert fixture.tree_digest(workspace) == before
    steps = [
        ("delete_road", SETTLEMENT, {"settlement_id": TOWN, "source": "gate", "destination": "yard"}),
        ("delete_road", SETTLEMENT, {"settlement_id": TOWN, "source": "yard", "destination": "gate"}),
        ("set_city_gate", SETTLEMENT, {"settlement_id": TOWN, "value": None}),
        ("create_wilderness_gate", SETTLEMENT, {"settlement_id": TOWN, "return_direction": "e", "node": YARD}),
        ("delete_wilderness_gate", SETTLEMENT, {"settlement_id": TOWN, "return_direction": "n"}),
    ]
    for name, document, arguments in steps:
        snapshot = fixture.tree_digest(workspace)
        status, body = _send(editor, name, document, arguments)
        assert status == 200, (name, body)
        assert _changed(snapshot, workspace) == {document}
    interior = _data(workspace, INTERIOR)
    status, body = _send(editor, "delete_nodes", SETTLEMENT, {"settlement_id": TOWN, "node_ids": ["gate"]})
    assert status == 200, body
    assert "gate" not in _data(workspace, SETTLEMENT)["nodes"]
    # Nothing cascaded into the interior or the districts.
    assert _data(workspace, INTERIOR) == interior
    assert _data(workspace, "content/maps/districts.yaml") == fixture.districts_data()


def test_an_exterior_blocks_its_node_until_it_is_removed_in_the_interior(workspace):
    fixture.write_reference_context(workspace)
    editor = Editor(workspace)
    for name, arguments in (
        ("delete_road", {"settlement_id": TOWN, "source": "gate", "destination": "yard"}),
        ("delete_road", {"settlement_id": TOWN, "source": "yard", "destination": "gate"}),
    ):
        assert _send(editor, name, SETTLEMENT, arguments)[0] == 200
    status, body = _send(editor, "delete_nodes", SETTLEMENT, {"settlement_id": TOWN, "node_ids": ["yard"]})
    assert status == 409
    assert {row["kind"] for row in body["error"]["internal_references"]} >= {"exterior"}
    snapshot = fixture.tree_digest(workspace)
    assert _send(editor, "set_exterior", INTERIOR, {"interior_id": HALL, "value": None})[0] == 200
    assert _changed(snapshot, workspace) == {INTERIOR}
    # The district landmark still names `yard`: still refused, still separate.
    status, body = _send(editor, "delete_nodes", SETTLEMENT, {"settlement_id": TOWN, "node_ids": ["yard"]})
    assert status == 409
    assert {row["kind"] for row in body["error"]["internal_references"]} == {"landmark"}


def test_a_duplicate_doorway_already_on_disk_is_a_core_structure_error(workspace):
    annex = fixture.interior_data()
    annex.update(id="synthetic_annex", rooms={"annex_lobby": dict(annex["rooms"]["front"])}, connections=[])
    annex["exterior"] = dict(annex["exterior"], room="annex_lobby")
    (workspace / ANNEX).write_text(fixture.yaml_text(annex), encoding="utf-8")
    editor = Editor(workspace)
    state = editor.state()
    assert state["preview_state"] == "unavailable"
    assert "duplicate_doorway" in {row["code"] for row in state["candidate_diagnostics"]}
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "set_room_fields", INTERIOR,
                         {"interior_id": HALL, "room_id": "back", "fields": {"name_zh": "改名"}})
    assert (status, body["error"]["code"]) == (423, "write_paused")
    assert fixture.tree_digest(workspace) == before


def test_doorway_checks_run_through_undo_and_redo(workspace):
    editor = Editor(workspace)
    _annex(editor)
    assert _send(editor, "set_exterior", INTERIOR, {"interior_id": HALL, "value": None})[0] == 200
    value = {"room": "interior_room:synthetic_annex:annex_lobby", "node": YARD, "doorway_key": "Door",
             "doorway_aliases": []}
    # With the hall's doorway removed, the annex may take the same name.
    assert _send(editor, "set_exterior", ANNEX, {"interior_id": "synthetic_annex", "value": value})[0] == 200
    assert editor.undo()[0] == 200
    assert editor.undo()[0] == 200
    assert _data(workspace, INTERIOR)["exterior"]["doorway_key"] == "Door"
    # Redoing the hall removal is fine; redoing the annex doorway only after it.
    assert editor.redo()[0] == 200
    assert editor.redo()[0] == 200
    assert _data(workspace, ANNEX)["exterior"]["doorway_key"] == "Door"
    assert _data(workspace, INTERIOR)["exterior"] is None
