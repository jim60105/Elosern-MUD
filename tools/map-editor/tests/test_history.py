"""Undo/redo of the uninterrupted manual segment through the same writer."""

from __future__ import annotations

import errno

import synthetic_workspace as fixture
from editor_client import INTERIOR, LAYOUT, Editor, sha

from elosern_map_editor.commands import CommandError
from elosern_map_editor.history import Presence
from elosern_map_editor.writer import CREATE, Effect

COMMENTED = (
    "# kept by hand\nversion: 1\nkind: layout\nid: synthetic_hall\npositions:\n"
    "  front: {x: 0, y: 0}  # door side\n  back: {x: 2, y: 1}\n"
)


def _layout_entry(editor):
    return [layout for layout in editor.state()["world"]["layouts"] if layout["id"] == fixture.INTERIOR_ID]


def test_create_undo_to_absence_and_redo_while_absent(workspace):
    editor = Editor(workspace)
    path = workspace / LAYOUT
    assert editor.move("back", 3, 1)[0] == 200
    created = path.read_bytes()
    status, body = editor.undo()
    assert (status, body["fingerprint"]) == (200, "absent")
    assert not path.exists()
    # The derived association goes with the document.
    assert _layout_entry(editor) == []
    assert editor.positions() == {"front": None, "back": None}
    history = editor.state()["history"]
    assert history["undo"] is None and history["redo"]["expected_document_fingerprint"] == "absent"
    status, _ = editor.redo()
    assert status == 200
    assert path.read_bytes() == created
    assert editor.positions()["back"] == [3, 1]


def test_redo_of_a_creation_requires_absence(workspace):
    editor = Editor(workspace)
    path = workspace / LAYOUT
    editor.move("back", 3, 1)
    editor.undo()
    path.write_text(COMMENTED, encoding="utf-8")
    history = editor.state()["history"]
    status, body = editor.redo()
    assert (status, body["error"]["code"]) == (409, "stale_document")
    assert path.read_text(encoding="utf-8") == COMMENTED
    assert editor.state()["history"] == history


def test_remove_then_undo_restores_the_exact_retained_bytes(workspace):
    path = workspace / LAYOUT
    path.parent.mkdir(parents=True)
    path.write_text(COMMENTED, encoding="utf-8")
    editor = Editor(workspace)
    assert editor.remove_layout()[0] == 200
    assert not path.exists()
    status, _ = editor.undo()
    assert status == 200
    assert path.read_text(encoding="utf-8") == COMMENTED
    assert editor.positions() == {"front": [0, 0], "back": [2, 1]}
    assert editor.redo()[0] == 200
    assert not path.exists()


def test_undo_of_a_replacement_restores_the_prior_bytes(workspace):
    path = workspace / LAYOUT
    path.parent.mkdir(parents=True)
    path.write_text(COMMENTED, encoding="utf-8")
    editor = Editor(workspace)
    editor.move("back", 7, 7)
    editor.move("front", 5, 5)
    assert editor.undo()[0] == 200
    assert editor.undo()[0] == 200
    assert path.read_text(encoding="utf-8") == COMMENTED
    status, body = editor.undo()
    assert (status, body["error"]["code"]) == (409, "history_empty")


def test_an_inverse_the_current_world_forbids_changes_neither_disk_nor_history(workspace):
    path = workspace / LAYOUT
    path.parent.mkdir(parents=True)
    path.write_text(COMMENTED, encoding="utf-8")
    editor = Editor(workspace)
    editor.remove_layout()
    history = editor.state()["history"]
    # The interior disappears on disk before the inverse runs.
    (workspace / INTERIOR).unlink()
    status, body = editor.undo()
    assert (status, body["error"]["code"]) == (422, "validation_failed")
    assert not path.exists()
    assert editor.state()["history"] == history


def test_a_stale_inverse_changes_neither_disk_nor_history(workspace):
    editor = Editor(workspace)
    editor.move("back", 1, 1)
    path = workspace / LAYOUT
    path.write_text(COMMENTED, encoding="utf-8")
    history = editor.state()["history"]
    status, body = editor.undo()
    assert (status, body["error"]["code"]) == (409, "stale_document")
    assert path.read_text(encoding="utf-8") == COMMENTED
    assert editor.state()["history"] == history


def test_an_uncertain_inverse_keeps_the_stacks_and_pauses(workspace):
    armed = {}

    def fault(stage):
        if stage in armed:
            raise armed.pop(stage)

    editor = Editor(workspace, fault=fault)
    editor.move("back", 1, 1)
    history = editor.state()["history"]
    armed["flush_directory"] = OSError(errno.EIO, "I/O error")
    status, body = editor.undo()
    assert (status, body["error"]["code"]) == (500, "save_uncertain")
    state = editor.state()
    assert state["history"] == history
    assert state["write_pause"]["reason"] == "uncertain_durability"


def test_mismatched_history_heads_are_rejected(workspace):
    editor = Editor(workspace)
    editor.move("back", 1, 1)
    head = editor.state()["history"]["undo"]
    body = editor.envelope(head["document_id"], "absent", {})
    status, response = editor.raw("undo", body)
    assert (status, response["error"]["code"]) == (409, "stale_history")
    assert (workspace / LAYOUT).exists()


def test_each_operation_is_one_entry_and_a_new_operation_clears_redo(workspace):
    editor = Editor(workspace)
    for x in (1, 2, 3):
        editor.move("back", x, 0)
    editor.undo()
    assert editor.positions()["back"] == [2, 0]
    assert editor.state()["history"]["redo"] is not None
    editor.move("front", 4, 4)
    assert editor.state()["history"]["redo"] is None
    editor.undo()
    editor.undo()
    assert editor.positions() == {"front": None, "back": [1, 0]}


def test_another_segment_starts_with_empty_history(workspace):
    editor = Editor(workspace)
    editor.move("back", 1, 1)
    refreshed = Editor.__new__(Editor)
    refreshed.__dict__.update(editor.__dict__)
    refreshed.segment = "segment-after-refresh"
    status, body = refreshed.undo()
    assert (status, body["error"]["code"]) == (409, "history_empty")
    assert refreshed.move("front", 2, 2)[0] == 200
    # The first segment's history is gone, not resumable.
    assert editor.state()["history"]["segment"] == "segment-after-refresh"
    status, body = editor.undo()
    assert (status, body["error"]["code"]) == (409, "history_empty")


def test_own_writes_keep_history_and_an_adopted_external_change_clears_it(workspace):
    editor = Editor(workspace)
    editor.move("back", 1, 1)
    editor.undo()
    editor.redo()
    assert editor.reload()[1]["changed"] is False
    assert editor.state()["history"]["undo"] is not None
    # An artifact change does not count as a source/layout change.
    fixture.write_reference_context(workspace)
    editor.reload()
    assert editor.state()["history"]["undo"] is not None
    node = workspace / f"content/maps/settlements/{fixture.SETTLEMENT_ID}.yaml"
    node.write_text(node.read_text(encoding="utf-8") + "# external edit\n", encoding="utf-8")
    assert editor.reload()[1]["changed"] is True
    history = editor.state()["history"]
    assert history == {"segment": None, "undo": None, "redo": None}
    assert (workspace / LAYOUT).exists()


def test_settlement_creation_undo_is_an_object_removing_guarded_inverse(workspace):
    """A created world document's undo removes objects and needs a current index."""

    editor = Editor(workspace)
    service = editor.service
    data = fixture.settlement_data()
    data["id"] = "synthetic_village"
    # One location binds one settlement: the created document claims the bare
    # location the synthetic town does not use.
    data["location_ref"] = fixture.BARE_LOCATION_ID
    data["binding"]["anchor_cell"] = {"cell_x": 30, "cell_y": 12}
    data["nodes"]["gate"]["prototype_parent"] = "grid_room"
    data["nodes"]["gate"]["anchor_key"] = None
    data["wilderness_entry"] = None
    data["city_gate"] = None
    path = "content/maps/settlements/synthetic_village.yaml"
    text = fixture.yaml_text(data)
    try:
        service.apply_effect(Effect(CREATE, path, text), Presence("absent", None), command="internal", segment=editor.segment)
    except CommandError as error:  # pragma: no cover - diagnostic aid
        raise AssertionError(error.details) from error
    created = sha(workspace / path)
    history = editor.state()["history"]
    status, body = editor.undo()
    assert (status, body["error"]["code"]) == (409, "deletion_refused")
    assert sha(workspace / path) == created
    assert editor.state()["history"] == history
    fixture.write_reference_context(workspace)
    assert editor.undo()[0] == 200
    assert not (workspace / path).exists()
    world = workspace / INTERIOR
    assert world.exists()
    assert editor.redo()[0] == 200
    assert sha(workspace / path) == created
