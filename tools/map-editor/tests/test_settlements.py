"""Settlement commands over the real ASGI app and a synthetic workspace.

Every assertion inspects the disk: a command writes only its settlement
document, a rejection leaves every byte unchanged, IDs and authored road
directions survive moves, and lengths come from the core.

Independently known synthetic geometry (see ``synthetic_workspace``): node
``gate`` at local (0, 0), ``yard`` at (300, 400); ``gate>yard`` is a straight
500 m road, ``yard>gate`` bends at (300, 0) and is 400 + 300 = 700 m.
"""

from __future__ import annotations

import errno

import pytest
from ruamel.yaml import YAML

import synthetic_workspace as fixture
from editor_client import Editor, sha
from test_document_commands import Faults

LOCATIONS = "content/maps/locations.yaml"
SETTLEMENT = f"content/maps/settlements/{fixture.SETTLEMENT_ID}.yaml"
NEW_MAP = "content/maps/settlements/wild_camp.yaml"
TOWN = fixture.SETTLEMENT_ID


def _send(editor: Editor, name: str, document: str, arguments: dict, **overrides):
    path = editor.workspace / document
    expected = sha(path) if path.exists() else "absent"
    return editor.raw(name, editor.envelope(document, expected, arguments, **overrides))


def _data(workspace, document=SETTLEMENT):
    return YAML(typ="safe", pure=True).load((workspace / document).read_text(encoding="utf-8"))


def _changed(before: dict, workspace) -> set[str]:
    after = fixture.tree_digest(workspace)
    return {path for path in set(before) | set(after) if before.get(path) != after.get(path)}


def _settlement(state: dict, settlement_id: str = TOWN) -> dict:
    return next(row for row in state["world"]["settlements"] if row["id"] == settlement_id)


def _roads(workspace, document=SETTLEMENT) -> dict:
    return {(road["source"], road["destination"]): road for road in _data(workspace, document)["roads"]}


def _node_fields(x: int, y: int, **overrides) -> dict:
    fields = {
        "x_m": x,
        "y_m": y,
        "prototype_parent": "grid_room",
        "key": "Well",
        "desc": "A synthetic well.",
        "anchor_key": None,
        "typeclass": None,
        "scene_archetype": None,
    }
    fields.update(overrides)
    return fields


def _create_node(editor, node_id="well", x=600, y=0, **overrides):
    return _send(editor, "create_node", SETTLEMENT,
                 {"settlement_id": TOWN, "node_id": node_id, "fields": _node_fields(x, y, **overrides)})


def _create_map(editor, **overrides):
    arguments = {"settlement_id": "wild_camp", "location_id": fixture.BARE_LOCATION_ID,
                 "options": None}
    arguments.update(overrides)
    return _send(editor, "create_settlement", NEW_MAP, arguments)


# -- local maps -----------------------------------------------------------------
def test_a_new_local_map_writes_only_its_document_and_stays_unfinished(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    status, body = _create_map(editor, options={"map_visual_range": 2, "map_mode": "nodes"})
    assert status == 200 and body["changed"] is True
    # No reverse location write: only the new settlement document appears.
    assert _changed(before, workspace) == {NEW_MAP}
    data = _data(workspace, NEW_MAP)
    assert (data["location_ref"], data["nodes"], data["roads"]) == (fixture.BARE_LOCATION_ID, {}, [])
    assert data["options"] == {"map_visual_range": 2, "map_mode": "nodes"}
    state = editor.state()
    location = next(row for row in state["world"]["locations"] if row["id"] == fixture.BARE_LOCATION_ID)
    assert location["local_maps"] == ["wild_camp"]
    # Saved as work in progress: diagnosed unfinished, never a playable map.
    empty = [item for item in state["diagnostics"] if item["code"] == "empty_graph"]
    assert [item["relative_path"] for item in empty] == [NEW_MAP]
    assert empty[0]["category"] == "semantic"
    assert _settlement(state, "wild_camp")["nodes"] == []
    # Undo removes the created document; redo requires its absence.
    assert editor.undo()[0] == 200
    assert not (workspace / NEW_MAP).exists()
    assert editor.redo()[0] == 200
    assert _data(workspace, NEW_MAP)["nodes"] == {}


@pytest.mark.parametrize(
    ("overrides", "status", "code"),
    [
        ({"settlement_id": TOWN}, 400, "cross_document"),
        ({"location_id": "ghost"}, 422, "validation_failed"),
        ({"settlement_id": "../escape"}, 400, "invalid_command"),
        # The removed creation frame arguments are unknown, never accepted.
        ({"anchor_cell": [30, 12]}, 400, "invalid_command"),
        ({"local_anchor_m": [0, 0]}, 400, "invalid_command"),
        ({"options": {"map_mode": "nodes"}}, 400, "invalid_command"),
        ({"options": {"map_visual_range": 0, "map_mode": "nodes"}}, 422, "validation_failed"),
    ],
)
def test_rejected_local_maps_write_nothing(workspace, overrides, status, code):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    answer = _create_map(editor, **overrides)
    assert (answer[0], answer[1]["error"]["code"]) == (status, code)
    assert fixture.tree_digest(workspace) == before


def test_an_existing_settlement_id_is_refused(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "create_settlement", SETTLEMENT,
                         {"settlement_id": TOWN, "location_id": fixture.LOCATION_ID,
                          "options": None})
    assert (status, body["error"]["diagnostics"][0]["code"]) == (422, "duplicate_identifier")
    assert fixture.tree_digest(workspace) == before


def test_map_options_and_exit_prototype_are_set_and_removed(workspace):
    editor = Editor(workspace)
    value = {"map_visual_range": 5, "map_mode": "nodes"}
    assert _send(editor, "set_settlement_field", SETTLEMENT,
                 {"settlement_id": TOWN, "field": "options", "value": value})[0] == 200
    assert _data(workspace)["options"] == value
    assert _send(editor, "set_settlement_field", SETTLEMENT,
                 {"settlement_id": TOWN, "field": "exit_prototype", "value": None})[0] == 200
    assert "exit_prototype" not in _data(workspace)
    assert _send(editor, "set_settlement_field", SETTLEMENT,
                 {"settlement_id": TOWN, "field": "exit_prototype",
                  "value": {"prototype_parent": "xyz_exit", "typeclass": None}})[0] == 200
    assert _data(workspace)["exit_prototype"] == {"prototype_parent": "xyz_exit", "typeclass": None}
    assert _settlement(editor.state())["exit_prototype"] == {"prototype_parent": "xyz_exit", "typeclass": None}


# -- nodes ------------------------------------------------------------------------
def test_a_new_node_needs_a_new_id_and_every_field(workspace):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    assert _create_node(editor)[0] == 200
    assert _changed(before, workspace) == {SETTLEMENT}
    assert _data(workspace)["nodes"]["well"] == _node_fields(600, 0)
    # An unconnected node is saveable work in progress.
    node = next(row for row in _settlement(editor.state())["nodes"] if row["id"] == "well")
    assert node["qualified_ref"] == f"settlement_node:{TOWN}:well"
    after = fixture.tree_digest(workspace)
    for node_id, extra in (("yard", {}), ("other", {"x": 300, "y": 400})):
        status, body = _create_node(editor, node_id, **extra)
        assert status == 422, body
        code = body["error"]["diagnostics"][0]["code"]
        assert code == ("duplicate_coordinate" if node_id == "other" else "duplicate_identifier")
    status, body = _send(editor, "create_node", SETTLEMENT,
                         {"settlement_id": TOWN, "node_id": "bare", "fields": {"x_m": 1, "y_m": 1}})
    assert (status, body["error"]["code"]) == (400, "invalid_command")
    assert fixture.tree_digest(workspace) == after


def test_duplicating_creates_a_new_id_without_copying_relationships(workspace):
    editor = Editor(workspace)
    status, body = _send(editor, "duplicate_node", SETTLEMENT,
                         {"settlement_id": TOWN, "node_id": "gate", "new_node_id": "gate_copy", "x_m": -100, "y_m": 0})
    assert status == 200, body
    data = _data(workspace)
    original, copy = data["nodes"]["gate"], data["nodes"]["gate_copy"]
    assert (copy["key"], copy["desc"], copy["scene_archetype"]) == (original["key"], original["desc"], original["scene_archetype"])
    # The anchor binds the location's one room: the copy is an ordinary room.
    assert (copy["prototype_parent"], copy["anchor_key"]) == ("grid_room", None)
    assert original["anchor_key"] == fixture.LOCATION_ID
    assert all("gate_copy" not in pair for pair in _roads(workspace))
    assert data["city_gate"]["node"] == "gate"
    assert [gate["destination_node"] for gate in data["wilderness_entry"]["gates"]] == ["gate"]
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "duplicate_node", SETTLEMENT,
                         {"settlement_id": TOWN, "node_id": "gate", "new_node_id": "yard", "x_m": 9, "y_m": 9})
    assert (status, body["error"]["diagnostics"][0]["code"]) == (422, "duplicate_identifier")
    assert fixture.tree_digest(workspace) == before


def test_node_fields_follow_the_core_schema(workspace):
    editor = Editor(workspace)
    fields = {"key": "Courtyard", "desc": "Line one.\nLine two.", "scene_archetype": "synthetic_scene", "typeclass": "tests.Room"}
    assert _send(editor, "set_node_fields", SETTLEMENT, {"settlement_id": TOWN, "node_id": "yard", "fields": fields})[0] == 200
    node = _data(workspace)["nodes"]["yard"]
    assert {key: node[key] for key in fields} == fields
    # One settlement has one anchor_room: demote the bound node first, then
    # switching the prototype carries the anchor key with it.
    assert _send(editor, "set_node_fields", SETTLEMENT, {"settlement_id": TOWN, "node_id": "gate", "fields": {
        "prototype_parent": "grid_room", "anchor_key": None}})[0] == 200
    assert _send(editor, "set_node_fields", SETTLEMENT, {"settlement_id": TOWN, "node_id": "yard", "fields": {
        "prototype_parent": "anchor_room", "anchor_key": fixture.LOCATION_ID}})[0] == 200
    assert _data(workspace)["nodes"]["yard"]["anchor_key"] == fixture.LOCATION_ID
    before = fixture.tree_digest(workspace)
    cases = [
        ({"prototype_parent": "grid_room"}, 422),  # anchor_key forbidden for grid_room
        ({"key": ""}, 422),
        ({"prototype_parent": "castle"}, 422),
        ({"x_m": 1}, 400),  # positions move through move_nodes
        ({"id": "renamed"}, 400),  # established IDs are read-only
    ]
    for value, expected in cases:
        status, _ = _send(editor, "set_node_fields", SETTLEMENT, {"settlement_id": TOWN, "node_id": "yard", "fields": value})
        assert status == expected, value
    assert fixture.tree_digest(workspace) == before


def test_moving_nodes_keeps_ids_directions_and_dependents(workspace):
    editor = Editor(workspace)
    state = editor.state()
    assert {road["id"]: road["length_m"] for road in _settlement(state)["roads"]} == {"gate>yard": 500.0, "yard>gate": 700.0}
    before = fixture.tree_digest(workspace)
    directions = {pair: road["direction"] for pair, road in _roads(workspace).items()}
    # One list-selected group of the one document: both nodes in one write.
    status, body = _send(editor, "move_nodes", SETTLEMENT, {"settlement_id": TOWN, "moves": [
        {"node_id": "yard", "x_m": 0, "y_m": 400}, {"node_id": "gate", "x_m": 0, "y_m": 0}]})
    assert status == 200, body
    assert _changed(before, workspace) == {SETTLEMENT}
    nodes = _data(workspace)["nodes"]
    assert (nodes["yard"]["x_m"], nodes["yard"]["y_m"]) == (0, 400)
    assert {pair: road["direction"] for pair, road in _roads(workspace).items()} == directions
    state = editor.state()
    settlement = _settlement(state)
    # Core lengths of the new geometry: 400 m straight north; back through
    # the bend (300, 0): a 3-4-5 leg of 500 m plus 300 m.
    assert {road["id"]: road["length_m"] for road in settlement["roads"]} == {"gate>yard": 400.0, "yard>gate": 800.0}
    # Every dependent still resolves to the same ID at the new coordinates.
    assert not [item for item in state["diagnostics"] if item["category"] == "structure"]
    interior = next(row for row in state["world"]["interiors"] if row["id"] == fixture.INTERIOR_ID)
    assert interior["exterior"]["node"] == "yard"
    district = state["world"]["districts"][0]
    assert district["landmark"]["object_id"] == "yard"
    yard = next(row for row in settlement["nodes"] if row["id"] == "yard")
    assert yard["world_m"] == [5500, 5500 + 400]
    # A move undoes to the exact bytes.
    assert editor.undo()[0] == 200
    assert fixture.tree_digest(workspace) == before


def test_the_first_node_places_the_map_and_an_anchor_move_reframes_the_graph(workspace):
    """The anchor node is the local frame; the projection is the evidence."""

    editor = Editor(workspace)
    status, body = _create_map(editor, options=None)
    assert (status, body["changed"]) == (200, True)
    state = editor.state()
    assert _settlement(state, "wild_camp")["world_frame"] is None

    # The first created node becomes the anchor of the location, keeping the
    # entered id, position and prose.
    status, body = _send(editor, "create_node", NEW_MAP, {"settlement_id": "wild_camp", "node_id": "camp", "fields": {
        **_node_fields(100, 200), "key": "Camp", "desc": "A camp.", "prototype_parent": "grid_room"}})
    assert status == 200, body
    node = _data(workspace, NEW_MAP)["nodes"]["camp"]
    assert (node["prototype_parent"], node["anchor_key"]) == ("anchor_room", fixture.BARE_LOCATION_ID)
    assert (node["x_m"], node["y_m"], node["key"]) == (100, 200, "Camp")
    settlement = _settlement(editor.state(), "wild_camp")
    # The bare location is cell (30, 12): its centre plus (100, 200) - (100, 200).
    assert settlement["world_frame"] == {"anchor_cell": [30, 12], "local_anchor_m": [100, 200]}
    assert [row["world_m"] for row in settlement["nodes"]] == [[30500, 12500]]

    # A second node sits in the same local frame.
    status, body = _send(editor, "create_node", NEW_MAP, {"settlement_id": "wild_camp", "node_id": "tent", "fields": {
        **_node_fields(170, 280), "key": "Tent", "desc": "A tent."}})
    assert status == 200, body
    settlement = _settlement(editor.state(), "wild_camp")
    world = {row["id"]: row["world_m"] for row in settlement["nodes"]}
    assert world == {"camp": [30500, 12500], "tent": [30570, 12580]}
    footprint = settlement["wilderness_entry"]  # none yet: the map has no gate
    assert footprint is None

    # Moving the anchor alone keeps it on the location cell's centre and shifts
    # every untouched node by the negative local delta.
    status, body = _send(editor, "move_nodes", NEW_MAP, {"settlement_id": "wild_camp", "moves": [
        {"node_id": "camp", "x_m": 130, "y_m": 250}]})
    assert status == 200, body
    settlement = _settlement(editor.state(), "wild_camp")
    assert settlement["world_frame"] == {"anchor_cell": [30, 12], "local_anchor_m": [130, 250]}
    assert {row["id"]: row["world_m"] for row in settlement["nodes"]} == {
        "camp": [30500, 12500],
        "tent": [30540, 12530],
    }
    # One undo restores the previous frame and both world positions.
    assert editor.undo()[0] == 200
    settlement = _settlement(editor.state(), "wild_camp")
    assert {row["id"]: row["world_m"] for row in settlement["nodes"]} == {
        "camp": [30500, 12500],
        "tent": [30570, 12580],
    }


@pytest.mark.parametrize(
    ("moves", "status"),
    [
        ([{"node_id": "yard", "x_m": 0, "y_m": 0}], 422),  # onto another node's coordinate
        ([{"node_id": "ghost", "x_m": 1, "y_m": 1}], 422),
        ([{"node_id": "yard", "x_m": 1, "y_m": 1}, {"node_id": "yard", "x_m": 2, "y_m": 2}], 400),
        ([{"node_id": "yard", "x_m": 1.5, "y_m": 1}], 400),
        ([], 400),
    ],
)
def test_invalid_moves_write_nothing(workspace, moves, status):
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    assert _send(editor, "move_nodes", SETTLEMENT, {"settlement_id": TOWN, "moves": moves})[0] == status
    assert fixture.tree_digest(workspace) == before


def test_a_node_of_another_settlement_is_a_cross_document_command(workspace):
    editor = Editor(workspace)
    assert _create_map(editor)[0] == 200
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "move_nodes", NEW_MAP, {"settlement_id": TOWN, "moves": [
        {"node_id": "yard", "x_m": 1, "y_m": 1}]})
    assert (status, body["error"]["code"], body["error"]["owner"]) == (400, "cross_document", SETTLEMENT)
    assert fixture.tree_digest(workspace) == before


# -- roads and bends ----------------------------------------------------------------
def test_a_bidirectional_street_is_two_directed_entries_in_one_write(workspace):
    editor = Editor(workspace)
    assert _create_node(editor, "well", 600, 0)[0] == 200
    before = fixture.tree_digest(workspace)
    undo_before = editor.state()["history"]
    status, body = _send(editor, "create_road", SETTLEMENT, {
        "settlement_id": TOWN, "source": "gate", "destination": "well", "direction": "e", "bends": [[300, -400]],
        "return": {"direction": "w", "bends": []}})
    assert status == 200, body
    assert _changed(before, workspace) == {SETTLEMENT}
    roads = _roads(workspace)
    assert (roads[("gate", "well")]["direction"], roads[("well", "gate")]["direction"]) == ("e", "w")
    assert roads[("gate", "well")]["bends"] == [{"x_m": 300, "y_m": -400}]
    lengths = {road["id"]: road["length_m"] for road in _settlement(editor.state())["roads"]}
    # Out 500 + 500 through the bend; back straight 600.
    assert (lengths["gate>well"], lengths["well>gate"]) == (1000.0, 600.0)
    # One operation: one undo removes both entries.
    assert editor.undo()[0] == 200
    assert fixture.tree_digest(workspace) == before
    assert editor.state()["history"]["undo"] == undo_before["undo"]


def test_invalid_roads_write_nothing(workspace):
    editor = Editor(workspace)
    assert _create_node(editor, "well", 600, 0)[0] == 200
    before = fixture.tree_digest(workspace)
    base = {"settlement_id": TOWN, "source": "gate", "destination": "well", "direction": "e", "bends": [], "return": None}
    cases = [
        ({"destination": "yard"}, 422),  # the ordered pair already exists
        ({"direction": "ne"}, 422),  # gate already leaves north-east
        ({"destination": "ghost"}, 422),
        ({"destination": "gate"}, 422),  # self-loop
        ({"direction": "up"}, 400),
        ({"return": {"direction": "s"}}, 400),
        ({"source": "yard", "destination": "well", "return": {"direction": "w", "bends": []}, "direction": "s"}, 422),  # yard already leaves south
        ({"bends": [[1, 2.5]]}, 400),
    ]
    for override, status in cases:
        answer = _send(editor, "create_road", SETTLEMENT, {**base, **override})
        assert answer[0] == status, (override, answer)
    assert fixture.tree_digest(workspace) == before


def test_road_edits_keep_identity_rules_and_never_recompute_direction(workspace):
    editor = Editor(workspace)
    assert _create_node(editor, "well", 600, 0)[0] == 200
    edit = {"settlement_id": TOWN, "source": "gate", "destination": "yard"}
    assert _send(editor, "set_road", SETTLEMENT, {**edit, "value": {"source": "gate", "destination": "yard", "direction": "n"}})[0] == 200
    assert _roads(workspace)[("gate", "yard")]["direction"] == "n"
    # Moving an endpoint node far east leaves the authored direction.
    assert _send(editor, "move_nodes", SETTLEMENT, {"settlement_id": TOWN, "moves": [{"node_id": "yard", "x_m": 900, "y_m": -5}]})[0] == 200
    assert _roads(workspace)[("gate", "yard")]["direction"] == "n"
    # Retarget the endpoint: identity changes, bends kept.
    assert _send(editor, "set_road", SETTLEMENT, {"settlement_id": TOWN, "source": "yard", "destination": "gate",
                                                  "value": {"source": "yard", "destination": "well", "direction": "s"}})[0] == 200
    roads = _roads(workspace)
    assert ("yard", "gate") not in roads and roads[("yard", "well")]["bends"] == [{"x_m": 300, "y_m": 0}]
    before = fixture.tree_digest(workspace)
    cases = [
        ({**edit, "value": {"source": "gate", "destination": "gate", "direction": "n"}}, 422),
        ({**edit, "value": {"source": "yard", "destination": "well", "direction": "e"}}, 422),  # existing pair
        ({"settlement_id": TOWN, "source": "yard", "destination": "well",
          "value": {"source": "gate", "destination": "well", "direction": "n"}}, 422),  # gate already leaves north
        ({"settlement_id": TOWN, "source": "well", "destination": "yard",
          "value": {"source": "well", "destination": "yard", "direction": "n"}}, 422),  # no such road
    ]
    for arguments, status in cases:
        assert _send(editor, "set_road", SETTLEMENT, arguments)[0] == status, arguments
    assert _send(editor, "delete_road", SETTLEMENT, {"settlement_id": TOWN, "source": "well", "destination": "gate"})[0] == 422
    assert fixture.tree_digest(workspace) == before


def test_bends_insert_move_and_remove_with_core_lengths(workspace):
    editor = Editor(workspace)
    road = {"settlement_id": TOWN, "source": "gate", "destination": "yard"}
    assert _send(editor, "insert_bend", SETTLEMENT, {**road, "index": 0, "point": [0, 400]})[0] == 200
    lengths = lambda: {row["id"]: row["length_m"] for row in _settlement(editor.state())["roads"]}  # noqa: E731
    assert lengths()["gate>yard"] == 700.0  # 400 north then 300 east
    assert _send(editor, "move_bend", SETTLEMENT, {**road, "index": 0, "point": [300, 0]})[0] == 200
    assert _roads(workspace)[("gate", "yard")]["bends"] == [{"x_m": 300, "y_m": 0}]
    assert lengths()["gate>yard"] == 700.0
    assert _send(editor, "insert_bend", SETTLEMENT, {**road, "index": 1, "point": [300, 200]})[0] == 200
    assert _send(editor, "remove_bend", SETTLEMENT, {**road, "index": 0})[0] == 200
    # (0,0) -> (300,200) -> (300,400): sqrt(130000) + 200.
    assert lengths()["gate>yard"] == pytest.approx(round(130000 ** 0.5 + 200, 3))
    before = fixture.tree_digest(workspace)
    assert _send(editor, "remove_bend", SETTLEMENT, {**road, "index": 4})[0] == 422
    assert _send(editor, "insert_bend", SETTLEMENT, {**road, "index": 9, "point": [1, 1]})[0] == 422
    assert _send(editor, "move_bend", SETTLEMENT, {**road, "index": 0, "point": [1, True]})[0] == 400
    assert fixture.tree_digest(workspace) == before
    assert _send(editor, "delete_road", SETTLEMENT, road)[0] == 200
    assert ("gate", "yard") not in _roads(workspace)


# -- deletion -------------------------------------------------------------------------
def test_deleting_a_referenced_node_is_refused_without_cascading(workspace):
    fixture.write_reference_context(workspace)
    editor = Editor(workspace)
    before = fixture.tree_digest(workspace)
    # yard: roads in this document, an interior exterior and a landmark.
    status, body = _send(editor, "delete_nodes", SETTLEMENT, {"settlement_id": TOWN, "node_ids": ["yard"]})
    assert (status, body["error"]["code"], body["error"]["guard"]) == (409, "deletion_refused", "internal")
    kinds = {row["kind"] for row in body["error"]["internal_references"]}
    assert kinds == {"exterior", "landmark"}
    # gate: only same-document references (roads, wilderness gate, city gate).
    status, body = _send(editor, "delete_nodes", SETTLEMENT, {"settlement_id": TOWN, "node_ids": ["gate"]})
    assert (status, body["error"]["guard"]) == (409, "internal")
    assert {row["kind"] for row in body["error"]["internal_references"]} == {"road", "wilderness_gate", "city_gate"}
    assert fixture.tree_digest(workspace) == before


def test_a_road_between_two_deleted_nodes_still_refuses(workspace):
    fixture.write_reference_context(workspace)
    editor = Editor(workspace)
    assert _create_node(editor, "well", 600, 0)[0] == 200
    assert _create_node(editor, "pump", 700, 0)[0] == 200
    assert _send(editor, "create_road", SETTLEMENT, {"settlement_id": TOWN, "source": "well", "destination": "pump",
                                                     "direction": "e", "bends": [], "return": None})[0] == 200
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "delete_nodes", SETTLEMENT, {"settlement_id": TOWN, "node_ids": ["well", "pump"]})
    assert (status, body["error"]["guard"]) == (409, "internal")
    assert {row["object_id"] for row in body["error"]["internal_references"]} == {"well>pump"}
    assert fixture.tree_digest(workspace) == before
    # Explicit removal first, then both nodes go in one operation.
    assert _send(editor, "delete_road", SETTLEMENT, {"settlement_id": TOWN, "source": "well", "destination": "pump"})[0] == 200
    assert _send(editor, "delete_nodes", SETTLEMENT, {"settlement_id": TOWN, "node_ids": ["well", "pump"]})[0] == 200
    assert {"well", "pump"}.isdisjoint(_data(workspace)["nodes"])


def test_an_unreferenced_node_needs_a_current_index_to_be_deleted(workspace):
    editor = Editor(workspace)
    assert _create_node(editor)[0] == 200
    before = fixture.tree_digest(workspace)
    # No index: external references are unknown, so deletion is refused.
    status, body = _send(editor, "delete_nodes", SETTLEMENT, {"settlement_id": TOWN, "node_ids": ["well"]})
    assert (status, body["error"]["guard"]) == (409, "unavailable")
    assert fixture.tree_digest(workspace) == before
    # An object-removing undo is checked the same way.
    history = editor.state()["history"]
    assert editor.undo()[0] == 409
    assert fixture.tree_digest(workspace) == before and editor.state()["history"] == history
    # Editing is unaffected by the missing index.
    assert _send(editor, "set_node_fields", SETTLEMENT, {"settlement_id": TOWN, "node_id": "well",
                                                         "fields": {"key": "Old well"}})[0] == 200
    fixture.write_reference_context(workspace, incoming={f"settlement_node:{TOWN}:well": [{
        "source": "synthetic_art", "source_domain": "art", "source_file": "external/declarations.txt",
        "target": {"domain": "settlement_node", "map_id": TOWN, "object_id": "well", "cell": None}}]})
    editor.reload()
    status, body = _send(editor, "delete_nodes", SETTLEMENT, {"settlement_id": TOWN, "node_ids": ["well"]})
    assert status == 409 and body["error"]["refusals"][0]["status"] == "referenced"
    fixture.write_reference_context(workspace)
    editor.reload()
    assert _send(editor, "delete_nodes", SETTLEMENT, {"settlement_id": TOWN, "node_ids": ["well"]})[0] == 200
    assert "well" not in _data(workspace)["nodes"]


def test_undoing_a_node_creation_is_refused_while_an_interior_now_names_it(workspace):
    from elosern_map_editor.commands import CommandError
    from elosern_map_editor.history import Presence
    from elosern_map_editor.writer import REPLACE, Effect

    fixture.write_reference_context(workspace)
    editor = Editor(workspace)
    service = editor.service
    assert _create_node(editor)[0] == 200
    creation = service.history.undo_stack[-1]
    # A later guarded operation points the interior's exterior at the new node.
    document = f"content/maps/interiors/{fixture.INTERIOR_ID}.yaml"
    interior = workspace / document
    text = interior.read_text(encoding="utf-8").replace("node: yard", "node: well")
    service.apply_effect(Effect(REPLACE, document, text), Presence(sha(interior), interior.read_text(encoding="utf-8")),
                         command="synthetic_exterior", segment=editor.segment)
    before = fixture.tree_digest(workspace)
    path = workspace / SETTLEMENT
    effect, _expected = creation.undo_effect()
    with pytest.raises(CommandError) as raised:
        service.apply_effect(effect, Presence(sha(path), path.read_text(encoding="utf-8")), command="undo",
                             segment=editor.segment, direction="undo")
    assert (raised.value.code, raised.value.details["guard"]) == ("deletion_refused", "internal")
    assert [row["kind"] for row in raised.value.details["internal_references"]] == ["exterior"]
    assert fixture.tree_digest(workspace) == before


# -- states -----------------------------------------------------------------------------
def test_an_uncertain_save_pauses_settlement_writes_until_a_reread(workspace):
    faults = Faults()
    editor = Editor(workspace, fault=faults)
    faults.armed["flush_directory"] = OSError(errno.EIO, "I/O error")
    status, body = _create_node(editor)
    assert (status, body["error"]["code"]) == (500, "save_uncertain")
    before = fixture.tree_digest(workspace)
    status, body = _send(editor, "move_nodes", SETTLEMENT, {"settlement_id": TOWN, "moves": [
        {"node_id": "yard", "x_m": 10, "y_m": 10}]})
    assert (status, body["error"]["code"], body["error"]["reason"]) == (423, "write_paused", "uncertain_durability")
    assert fixture.tree_digest(workspace) == before
    assert editor.reload()[0] == 200
    assert _send(editor, "move_nodes", SETTLEMENT, {"settlement_id": TOWN, "moves": [
        {"node_id": "yard", "x_m": 10, "y_m": 10}]})[0] == 200


def test_stale_previews_and_documents_reject_settlement_commands(workspace):
    editor = Editor(workspace)
    stale_fingerprint = sha(workspace / SETTLEMENT)
    (workspace / SETTLEMENT).write_text((workspace / SETTLEMENT).read_text(encoding="utf-8") + "\n# external\n",
                                        encoding="utf-8")
    before = fixture.tree_digest(workspace)
    # Not reread yet: the snapshot still holds the old fingerprint.
    status, body = editor.raw("create_node", editor.envelope(SETTLEMENT, stale_fingerprint, {
        "settlement_id": TOWN, "node_id": "well", "fields": _node_fields(600, 0)}))
    assert (status, body["error"]["code"]) == (409, "stale_document")
    assert fixture.tree_digest(workspace) == before
    (workspace / SETTLEMENT).write_text("version: 1\nkind: [unclosed\n", encoding="utf-8")
    editor.reload()
    before = fixture.tree_digest(workspace)
    status, body = _create_node(editor)
    assert (status, body["error"]["reason"]) == (423, "stale_preview")
    assert fixture.tree_digest(workspace) == before


def test_scene_references_report_valid_invalid_and_unavailable_separately(workspace):
    editor = Editor(workspace)
    assert _send(editor, "set_node_fields", SETTLEMENT, {"settlement_id": TOWN, "node_id": "yard",
                                                         "fields": {"scene_archetype": "synthetic_scene"}})[0] == 200

    def statuses():
        state = editor.state()
        return {row["id"]: row["scene_status"] for row in _settlement(state)["nodes"]}, state["external_identifiers"]

    assert statuses() == ({"gate": "unavailable", "yard": "unavailable"}, {})
    context = fixture.write_reference_context(workspace)
    editor.reload()
    # Current but empty set: every named scene is invalid, none unavailable.
    assert statuses() == ({"gate": "invalid", "yard": "invalid"}, {"scene_archetypes": []})
    import json

    document = json.loads(context.read_text(encoding="utf-8"))
    document["external_identifiers"] = {"scene_archetypes": ["synthetic_scene"]}
    context.write_text(json.dumps(document), encoding="utf-8")
    editor.reload()
    assert statuses() == ({"gate": "invalid", "yard": "valid"}, {"scene_archetypes": ["synthetic_scene"]})


# -- route preview ------------------------------------------------------------------------
def test_the_route_preview_is_the_core_planner_over_the_snapshot(workspace):
    editor = Editor(workspace)
    revision = editor.state()["snapshot_revision"]
    response = editor.client.get(f"/api/settlements/{TOWN}/route", params={"source": "yard", "destination": "gate"})
    body = response.json()
    assert response.status_code == 200
    assert (body["status"], body["length_m"], body["snapshot_revision"]) == ("route", 700.0, revision)
    assert [(step["source"], step["destination"], step["direction"]) for step in body["steps"]] == [("yard", "gate", "s")]
    assert _create_node(editor)[0] == 200
    body = editor.client.get(f"/api/settlements/{TOWN}/route", params={"source": "gate", "destination": "well"}).json()
    assert body["status"] == "no_route" and body["snapshot_revision"] > revision
    assert editor.client.get("/api/settlements/ghost/route", params={"source": "a", "destination": "b"}).status_code == 404
    assert editor.client.get(f"/api/settlements/{TOWN}/route", params={"source": "../x", "destination": "b"}).status_code == 400
