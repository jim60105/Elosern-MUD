"""Admission, guards, the layout handlers and the single-document writer."""

from __future__ import annotations

import errno
import json
import os

import pytest

import synthetic_workspace as fixture
from editor_client import INTERIOR, LAYOUT, Editor, sha

from elosern_map_editor.commands import removed_objects
from elosern_map_editor.writer import CREATE, REMOVE, REPLACE, Effect

WORLD = tuple(fixture.DOCUMENTS)


def _world_digest(workspace):
    return {path: sha(workspace / path) for path in WORLD}


def _no_temporaries(workspace):
    directory = workspace / "content/map-editor-layouts"
    return not directory.exists() or not [p for p in directory.iterdir() if p.name.endswith(".tmp")]


def _second_interior(workspace, interior_id="synthetic_cellar"):
    data = fixture.interior_data()
    data["id"] = interior_id
    data["rooms"] = {"stair": data["rooms"]["front"], "vault": data["rooms"]["back"]}
    data["connections"] = [{"source": "stair", "destination": "vault", "label": "down"}]
    data["exterior"] = None
    (workspace / f"content/maps/interiors/{interior_id}.yaml").write_text(fixture.yaml_text(data), encoding="utf-8")


# -- first layout, replacement and side effects ---------------------------
def test_the_first_move_creates_only_the_absent_layout_document(workspace):
    editor = Editor(workspace)
    world = _world_digest(workspace)
    assert editor.layout_fingerprint() == "absent"
    status, body = editor.move("back", 4, -2)
    assert status == 200, body
    path = workspace / LAYOUT
    assert body["fingerprint"] == sha(path)
    assert editor.positions() == {"front": None, "back": [4, -2]}
    assert _world_digest(workspace) == world
    assert sorted(p.name for p in path.parent.iterdir()) == [f"{fixture.INTERIOR_ID}.yaml"]
    assert editor.state()["history"]["undo"]["document_id"] == LAYOUT


def test_a_replacement_keeps_comments_and_other_positions(workspace):
    path = workspace / LAYOUT
    path.parent.mkdir(parents=True)
    path.write_text(
        "# arranged by hand\nversion: 1\nkind: layout\nid: synthetic_hall\npositions:\n"
        "  front: {x: 0, y: 0}  # entrance\n  back: {x: 1, y: 0}\n",
        encoding="utf-8",
    )
    editor = Editor(workspace)
    status, _ = editor.move("back", 2, 3)
    assert status == 200
    text = path.read_text(encoding="utf-8")
    assert "# arranged by hand" in text and "# entrance" in text
    assert editor.positions() == {"front": [0, 0], "back": [2, 3]}


def test_an_unchanged_position_writes_nothing(workspace):
    editor = Editor(workspace)
    editor.move("back", 1, 1)
    before = sha(workspace / LAYOUT)
    status, body = editor.move("back", 1, 1)
    assert (status, body["changed"]) == (200, False)
    assert sha(workspace / LAYOUT) == before
    assert editor.state()["history"]["redo"] is None


# -- admission -------------------------------------------------------------
def test_admission_rejects_old_sessions_revisions_and_malformed_envelopes(workspace):
    editor = Editor(workspace)
    revision = editor.state()["snapshot_revision"]
    assert editor.move("back", 1, 1, session_generation="old")[1]["error"]["code"] == "stale_session"
    status, body = editor.move("back", 1, 1, snapshot_revision=revision - 1)
    assert (status, body["error"]["code"]) == (409, "stale_snapshot")
    assert editor.move("back", 1, 1, snapshot_revision=revision + 1)[1]["error"]["code"] == "stale_snapshot"
    assert editor.raw("write_file", editor.envelope(LAYOUT, "absent", {}))[0] == 404
    assert editor.raw("move_interior_layout", "not json")[1]["error"]["code"] == "invalid_body"
    extra = {**editor.envelope(LAYOUT, "absent", {}), "path": "/etc/passwd"}
    assert editor.raw("move_interior_layout", extra)[1]["error"]["code"] == "invalid_body"
    for x in (True, 1.0, "1", 10**9):
        status, body = editor.move("back", x, 1)
        assert (status, body["error"]["code"]) == (400, "invalid_command"), x
    assert not (workspace / LAYOUT).exists()


def test_a_document_id_outside_the_named_owner_is_cross_document(workspace):
    _second_interior(workspace)
    editor = Editor(workspace)
    arguments = {"interior_id": fixture.INTERIOR_ID, "room_id": "back", "x": 1, "y": 1}
    other = "content/map-editor-layouts/synthetic_cellar.yaml"
    status, body = editor.raw("move_interior_layout", editor.envelope(other, "absent", arguments))
    assert (status, body["error"]["code"]) == (400, "cross_document")
    status, body = editor.move("vault", 1, 1)
    assert (status, body["error"]["code"]) == (400, "cross_document")
    assert body["error"]["owner"] == other
    status, body = editor.move("attic", 1, 1)
    assert (status, body["error"]["code"]) == (422, "validation_failed")
    for traversal in ("../maps/continent", "Synthetic_hall"):
        arguments = {"interior_id": traversal, "room_id": "back", "x": 1, "y": 1}
        status, body = editor.raw("move_interior_layout", editor.envelope(LAYOUT, "absent", arguments))
        assert (status, body["error"]["code"]) == (400, "invalid_command")
    assert not (workspace / "content/map-editor-layouts").exists()


def test_a_stale_preview_pauses_every_command(workspace):
    editor = Editor(workspace)
    editor.move("back", 1, 1)
    settlement = workspace / f"content/maps/settlements/{fixture.SETTLEMENT_ID}.yaml"
    settlement.write_text("version: 1\nkind: [unclosed\n", encoding="utf-8")
    editor.reload()
    layout = sha(workspace / LAYOUT)
    status, body = editor.move("back", 5, 5, expected=layout)
    assert (status, body["error"]["code"], body["error"]["reason"]) == (423, "write_paused", "stale_preview")
    assert sha(workspace / LAYOUT) == layout


# -- presence and hash guards ---------------------------------------------
def test_a_create_whose_target_appeared_preserves_the_external_file(workspace):
    editor = Editor(workspace)
    path = workspace / LAYOUT
    path.parent.mkdir(parents=True)
    external = "version: 1\nkind: layout\nid: synthetic_hall\npositions: {}\n"
    path.write_text(external, encoding="utf-8")
    status, body = editor.move("back", 1, 1, expected="absent")
    assert (status, body["error"]["code"]) == (409, "stale_document")
    assert path.read_text(encoding="utf-8") == external
    assert editor.state()["history"]["undo"] is None


def test_the_writer_recheck_catches_a_file_appearing_after_admission(workspace):
    path = workspace / LAYOUT
    external = "version: 1\nkind: layout\nid: synthetic_hall\npositions: {}\n"

    def race(stage):
        if stage == "before_publish":
            path.write_text(external, encoding="utf-8")

    editor = Editor(workspace, fault=race)
    status, body = editor.move("back", 1, 1)
    assert (status, body["error"]["code"]) == (409, "stale_document")
    assert path.read_text(encoding="utf-8") == external
    assert _no_temporaries(workspace)


def test_a_remove_whose_fingerprint_changed_preserves_the_document(workspace):
    editor = Editor(workspace)
    editor.move("back", 1, 1)
    old = editor.layout_fingerprint()
    path = workspace / LAYOUT
    path.write_text(path.read_text(encoding="utf-8") + "# edited elsewhere\n", encoding="utf-8")
    edited = sha(path)
    status, body = editor.remove_layout(expected=old)
    assert (status, body["error"]["code"]) == (409, "stale_document")
    assert sha(path) == edited
    assert editor.state()["history"]["undo"]["expected_document_fingerprint"] == old


def test_remove_interior_layout_unlinks_only_its_owner(workspace):
    editor = Editor(workspace)
    editor.move("back", 1, 1)
    world = _world_digest(workspace)
    status, body = editor.remove_layout()
    assert (status, body["fingerprint"]) == (200, "absent")
    assert not (workspace / LAYOUT).exists()
    assert _world_digest(workspace) == world
    assert editor.state()["world"]["layouts"] == []


def test_a_linked_layout_directory_is_never_followed(workspace, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace / "content/map-editor-layouts").symlink_to(outside, target_is_directory=True)
    editor = Editor(workspace)
    status, body = editor.move("back", 1, 1)
    assert status in (409, 500) and body["error"]["code"] in ("stale_document", "save_failed")
    assert list(outside.iterdir()) == []


# -- failures and uncertainty ----------------------------------------------
class Faults:
    def __init__(self):
        self.armed: dict[str, OSError] = {}
        self.calls: list[str] = []

    def __call__(self, stage):
        self.calls.append(stage)
        if stage in self.armed:
            raise self.armed.pop(stage)


@pytest.mark.parametrize("stage", ["write_temp", "flush_temp", "before_publish"])
def test_a_failure_before_publication_keeps_the_first_saved_operation(workspace, stage):
    faults = Faults()
    editor = Editor(workspace, fault=faults)
    assert editor.move("back", 1, 1)[0] == 200
    first = (workspace / LAYOUT).read_bytes()
    history = editor.state()["history"]
    faults.armed[stage] = OSError(errno.ENOSPC, "No space left on device")
    status, body = editor.move("back", 9, 9)
    assert (status, body["error"]["code"]) == (500, "save_failed")
    assert (workspace / LAYOUT).read_bytes() == first
    assert _no_temporaries(workspace)
    state = editor.state()
    assert state["history"] == history
    assert state["write_pause"]["paused"] is False
    assert editor.positions()["back"] == [1, 1]


def test_a_failed_first_creation_leaves_absence(workspace):
    faults = Faults()
    faults.armed["flush_temp"] = OSError(errno.EIO, "I/O error")
    editor = Editor(workspace, fault=faults)
    status, body = editor.move("back", 1, 1)
    assert (status, body["error"]["code"]) == (500, "save_failed")
    assert not (workspace / LAYOUT).exists()
    assert _no_temporaries(workspace)
    assert editor.state()["history"]["undo"] is None


@pytest.mark.parametrize(
    ("error", "code"),
    [(OSError(errno.ENOSPC, "full"), "save_failed"), (OSError(errno.EIO, "I/O error"), "save_uncertain")],
)
def test_a_publication_error_is_classified_by_errno(workspace, error, code):
    faults = Faults()
    editor = Editor(workspace, fault=faults)
    editor.move("back", 1, 1)
    first = (workspace / LAYOUT).read_bytes()
    faults.armed["publish"] = error
    status, body = editor.move("back", 2, 2)
    assert (status, body["error"]["code"]) == (500, code)
    assert (workspace / LAYOUT).read_bytes() == first
    assert editor.state()["write_pause"]["paused"] is (code == "save_uncertain")


def test_a_filesystem_without_hard_links_still_creates_exclusively(workspace):
    faults = Faults()
    faults.armed["publish"] = OSError(errno.EPERM, "Operation not permitted")
    editor = Editor(workspace, fault=faults)
    status, body = editor.move("back", 1, 1)
    assert status == 200, body
    assert body["fingerprint"] == sha(workspace / LAYOUT)
    assert _no_temporaries(workspace)
    assert editor.positions()["back"] == [1, 1]


def test_uncertain_durability_pauses_until_a_reread_without_retrying(workspace):
    faults = Faults()
    editor = Editor(workspace, fault=faults)
    editor.move("back", 1, 1)
    faults.armed["flush_directory"] = OSError(errno.EIO, "I/O error")
    status, body = editor.move("back", 2, 2)
    assert (status, body["error"]["code"]) == (500, "save_uncertain")
    publications = faults.calls.count("publish")
    state = editor.state()
    assert state["write_pause"] == {"paused": True, "reason": "uncertain_durability"}
    assert state["pending_intent"]["command"] == "move_interior_layout"
    assert state["pending_intent"]["document_id"] == LAYOUT
    # No saved-state claim: history still ends at the first operation.
    assert state["history"]["undo"]["expected_document_fingerprint"] == state["pending_intent"]["baseline_fingerprint"]
    on_disk = sha(workspace / LAYOUT)
    for attempt in (lambda: editor.move("back", 3, 3, expected=on_disk), editor.undo, editor.remove_layout):
        status, body = attempt()
        assert (status, body["error"]["code"]) == (423, "write_paused")
    assert faults.calls.count("publish") == publications
    assert sha(workspace / LAYOUT) == on_disk
    assert editor.reload()[0] == 200
    state = editor.state()
    assert state["write_pause"]["paused"] is False
    assert state["pending_intent"] is None
    assert state["uncertain_outcome"]["landed"] == "intended"
    assert state["history"]["undo"] is None
    assert editor.move("back", 3, 3)[0] == 200


def test_a_reread_that_does_not_load_keeps_the_uncertain_pause(workspace):
    faults = Faults()
    editor = Editor(workspace, fault=faults)
    faults.armed["flush_directory"] = OSError(errno.EIO, "I/O error")
    editor.move("back", 1, 1)
    (workspace / INTERIOR).write_text("version: 1\nkind: [unclosed\n", encoding="utf-8")
    editor.reload()
    assert editor.state()["pending_intent"] is not None
    (workspace / INTERIOR).write_text(fixture.yaml_text(fixture.interior_data()), encoding="utf-8")
    editor.reload()
    assert editor.state()["write_pause"]["paused"] is False


def test_a_failed_reread_after_publication_pauses_with_one_revision_step(workspace, monkeypatch):
    from elosern_map_editor import app as app_module

    editor = Editor(workspace)
    revision = editor.state()["snapshot_revision"]
    assert editor.move("back", 1, 1)[0] == 200
    # One own write is exactly one revision step.
    assert editor.state()["snapshot_revision"] == revision + 1
    real = app_module.read_workspace

    def broken(*args):
        raise OSError(errno.EIO, "I/O error")

    monkeypatch.setattr(app_module, "read_workspace", broken)
    status, body = editor.move("back", 2, 2)
    assert (status, body["error"]["code"]) == (500, "reread_failed")
    monkeypatch.setattr(app_module, "read_workspace", real)
    state = editor.state()
    assert state["write_pause"]["reason"] == "uncertain_durability"
    assert editor.move("back", 3, 3)[1]["error"]["code"] == "write_paused"
    editor.reload()
    state = editor.state()
    assert state["uncertain_outcome"]["landed"] == "intended"
    assert state["write_pause"]["paused"] is False
    assert editor.positions()["back"] == [2, 2]


def test_leftover_temporary_names_are_never_discovered(workspace):
    editor = Editor(workspace)
    editor.move("back", 1, 1)
    (workspace / f"content/map-editor-layouts/.{fixture.INTERIOR_ID}.yaml.dead.tmp").write_text("x: [", encoding="utf-8")
    editor.reload()
    state = editor.state()
    assert state["preview_state"] == "current"
    assert [layout["relative_path"] for layout in state["world"]["layouts"]] == [LAYOUT]


# -- object-removing guard (generic executor) ----------------------------
def test_layout_effects_remove_no_map_object(workspace):
    editor = Editor(workspace)
    text = "version: 1\nkind: layout\nid: synthetic_hall\npositions: {}\n"
    for effect in (Effect(CREATE, LAYOUT, text), Effect(REPLACE, LAYOUT, text), Effect(REMOVE, LAYOUT)):
        assert removed_objects(editor.service.workspace, editor.service.config.limits, effect) == ()


def test_removing_a_world_document_rechecks_the_external_context_at_execution(workspace):
    from elosern_map_editor.history import Presence

    editor = Editor(workspace)
    service = editor.service
    baseline = Presence(sha(workspace / INTERIOR), (workspace / INTERIOR).read_text(encoding="utf-8"))

    def remove():
        from elosern_map_editor.commands import CommandError

        try:
            return service.apply_effect(Effect(REMOVE, INTERIOR), baseline, command="internal", segment="s")
        except CommandError as error:
            return error

    # No reference index at all: absence of references cannot be proven.
    error = remove()
    assert (error.code, error.details["guard"]) == ("deletion_refused", "unavailable")
    assert (workspace / INTERIOR).exists() and service.history.undo_stack == []
    # A current index naming an incoming reference refuses too.
    fixture.write_reference_context(
        workspace,
        incoming={
            f"interior_room:{fixture.INTERIOR_ID}:front": [
                {
                    "source": "place:hall_front",
                    "source_file": "external/declarations.txt",
                    "source_domain": "places",
                    "target": {"domain": "interior_room", "map_id": fixture.INTERIOR_ID, "object_id": "front", "cell": None},
                }
            ]
        },
    )
    error = remove()
    assert error.code == "deletion_refused"
    assert error.details["refusals"][0]["status"] == "referenced"
    assert sha(workspace / INTERIOR) == baseline.fingerprint
    # The index was current when written; an external source changed since.
    fixture.write_reference_context(workspace)
    (workspace / "external/declarations.txt").write_text("changed\n", encoding="utf-8")
    error = remove()
    assert (error.code, error.details["refusals"][0]["status"]) == ("deletion_refused", "unavailable")
    assert (workspace / INTERIOR).exists() and service.history.undo_stack == []
    # Current and unreferenced: the removal is published and recorded.
    fixture.write_reference_context(workspace)
    result = remove()
    assert not isinstance(result, Exception), result
    assert not (workspace / INTERIOR).exists()
    assert [entry.document_id for entry in service.history.undo_stack] == [INTERIOR]


def test_a_removal_that_breaks_internal_references_fails_the_gate(workspace):
    from elosern_map_editor.commands import CommandError
    from elosern_map_editor.history import Presence

    fixture.write_reference_context(workspace)
    editor = Editor(workspace)
    path = workspace / f"content/maps/settlements/{fixture.SETTLEMENT_ID}.yaml"
    before = Presence(sha(path), path.read_text(encoding="utf-8"))
    with pytest.raises(CommandError) as raised:
        editor.service.apply_effect(Effect(REMOVE, f"content/maps/settlements/{fixture.SETTLEMENT_ID}.yaml"), before, command="internal", segment="s")
    # The district landmark still names a node of that settlement: the
    # fresh-baseline internal guard explains it before the authoring gate.
    assert raised.value.code == "deletion_refused"
    assert raised.value.details["internal_references"][0]["kind"] == "landmark"
    assert sha(path) == before.fingerprint
    assert json.dumps(raised.value.details)
    assert os.path.exists(path)
