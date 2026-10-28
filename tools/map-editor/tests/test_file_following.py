"""File following: admission, ledger reconciliation and preview adoption.

Deterministic in-process mechanism tests. Each reconciliation is invoked
directly (``Editor.follow``), exactly as the watch coordinator does after a
coalesced batch, so delayed or repeated notifications are simulated without
timing. Every failure path inspects the unchanged files on disk.
"""

from __future__ import annotations

import errno
import json
import os

import pytest

import synthetic_workspace as fixture
from editor_client import INTERIOR, LAYOUT, Editor, sha

SETTLEMENT = f"content/maps/settlements/{fixture.SETTLEMENT_ID}.yaml"
MALFORMED = "version: 1\nkind: [unclosed\n"


def _layout_text(x: int, y: int, *, comment: str = "") -> str:
    return (
        f"{comment}version: 1\nkind: layout\nid: {fixture.INTERIOR_ID}\n"
        f"positions:\n  back: {{x: {x}, y: {y}}}\n"
    )


def _replace_atomically(path, text: str) -> None:
    """An external writer's create-temp-then-rename replacement."""

    temporary = path.with_name(f".{path.name}.external")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _with_history(workspace) -> Editor:
    """A segment with one undo and one redo entry over an existing layout."""

    editor = Editor(workspace)
    assert editor.move("back", 1, 1)[0] == 200
    assert editor.move("back", 2, 2)[0] == 200
    assert editor.undo()[0] == 200
    history = editor.state()["history"]
    assert history["undo"] and history["redo"]
    return editor


def _every_route(editor: Editor):
    on_disk = sha(editor.workspace / LAYOUT)
    return {
        "move_interior_layout": lambda: editor.move("back", 5, 5, expected=on_disk),
        "remove_interior_layout": lambda: editor.remove_layout(expected=on_disk),
        "undo": editor.undo,
        "redo": editor.redo,
    }


class Faults:
    def __init__(self):
        self.armed: dict[str, object] = {}

    def __call__(self, stage):
        action = self.armed.pop(stage, None)
        if isinstance(action, BaseException):
            raise action
        if callable(action):
            action()


# -- admission: write pause and stale preview -------------------------------
def test_every_route_is_rejected_while_the_preview_is_stale_and_admitted_after_recovery(workspace):
    editor = _with_history(workspace)
    (workspace / SETTLEMENT).write_text(MALFORMED, encoding="utf-8")
    assert editor.follow() is True
    state = editor.state()
    assert (state["preview_state"], state["write_pause"]["paused"]) == ("stale", False)
    before = fixture.tree_digest(workspace)
    for name, attempt in _every_route(editor).items():
        status, body = attempt()
        assert (status, body["error"]["code"], body["error"]["reason"]) == (423, "write_paused", "stale_preview"), name
    assert fixture.tree_digest(workspace) == before
    # Correcting the file externally recovers automatically; writes resume.
    _replace_atomically(workspace / SETTLEMENT, fixture.yaml_text(fixture.settlement_data()))
    assert editor.follow() is True
    assert editor.state()["preview_state"] == "current"
    assert editor.move("back", 6, 6)[0] == 200
    assert editor.positions()["back"] == [6, 6]
    assert editor.remove_layout()[0] == 200
    assert not (workspace / LAYOUT).exists()


def test_every_route_is_rejected_while_writes_are_paused_and_admitted_after_the_reread(workspace):
    faults = Faults()
    editor = Editor(workspace, fault=faults)
    assert editor.move("back", 1, 1)[0] == 200
    assert editor.move("back", 2, 2)[0] == 200
    assert editor.undo()[0] == 200
    faults.armed["flush_directory"] = OSError(errno.EIO, "I/O error")
    assert editor.move("back", 3, 3)[1]["error"]["code"] == "save_uncertain"
    before = fixture.tree_digest(workspace)
    for name, attempt in _every_route(editor).items():
        status, body = attempt()
        assert (status, body["error"]["code"], body["error"]["reason"]) == (
            423, "write_paused", "uncertain_durability"), name
    assert fixture.tree_digest(workspace) == before
    # A watcher reconciliation never resolves the uncertain publication.
    editor.follow()
    assert editor.state()["write_pause"]["paused"] is True
    assert editor.reload()[0] == 200
    assert editor.state()["write_pause"]["paused"] is False
    assert editor.move("back", 4, 4)[0] == 200


def test_every_route_is_rejected_without_a_prior_preview_until_the_world_loads(workspace):
    locations = workspace / "content/maps/locations.yaml"
    original = locations.read_text(encoding="utf-8")
    locations.write_text(original + "unexpected_field: 1\n", encoding="utf-8")
    editor = Editor(workspace)
    state = editor.state()
    assert (state["preview_state"], state["world"]) == ("unavailable", None)
    before = fixture.tree_digest(workspace)
    for name in ("move_interior_layout", "remove_interior_layout", "undo", "redo"):
        arguments = {"interior_id": fixture.INTERIOR_ID}
        if name == "move_interior_layout":
            arguments.update(room_id="back", x=1, y=1)
        elif name in ("undo", "redo"):
            arguments = {}
        status, body = editor.raw(name, editor.envelope(LAYOUT, "absent", arguments))
        assert (status, body["error"]["reason"]) == (423, "unavailable_preview"), name
    # Still broken: no valid-looking empty world is ever published.
    editor.follow()
    assert editor.state()["world"] is None
    assert fixture.tree_digest(workspace) == before
    locations.write_text(original, encoding="utf-8")
    assert editor.follow() is True
    assert editor.state()["preview_state"] == "current"
    assert editor.move("back", 1, 1)[0] == 200


# -- own writes and external changes --------------------------------------
def test_delayed_notifications_of_own_saves_keep_history_then_an_external_replacement_is_adopted(workspace):
    editor = Editor(workspace)
    assert editor.move("back", 1, 1)[0] == 200
    assert editor.move("back", 2, 2)[0] == 200
    state = editor.state()
    revision, history = state["snapshot_revision"], state["history"]
    # Delayed and coalesced (repeated) notifications of the two own saves.
    assert editor.follow() is False
    assert editor.follow() is False
    state = editor.state()
    assert (state["snapshot_revision"], state["history"]) == (revision, history)
    assert state["external_change"]["sequence"] == 0
    # An external replacement at the same path, with different bytes.
    _replace_atomically(workspace / LAYOUT, _layout_text(7, 8))
    assert editor.follow() is True
    state = editor.state()
    assert state["history"]["undo"] is None and state["history"]["redo"] is None
    assert state["external_change"]["sequence"] == 1
    assert state["external_change"]["documents"] == [LAYOUT]
    assert editor.positions()["back"] == [7, 8]
    assert (workspace / LAYOUT).read_text(encoding="utf-8") == _layout_text(7, 8)


def test_an_external_write_of_the_exact_committed_bytes_is_indistinguishable_from_own_output(workspace):
    # Documented fingerprint limit: identical bytes are the same document.
    editor = Editor(workspace)
    assert editor.move("back", 1, 1)[0] == 200
    committed = (workspace / LAYOUT).read_text(encoding="utf-8")
    _replace_atomically(workspace / LAYOUT, committed)
    assert editor.follow() is False
    assert editor.state()["history"]["undo"] is not None


@pytest.mark.parametrize("change", ["create", "delete_layout", "delete_document"])
def test_external_creates_and_deletes_are_adopted_with_history_cleared(workspace, change):
    editor = Editor(workspace)
    assert editor.move("back", 1, 1)[0] == 200
    if change == "create":
        data = fixture.interior_data()
        data["id"] = "synthetic_cellar"
        data["exterior"] = None
        path = f"content/maps/interiors/{data['id']}.yaml"
        (workspace / path).write_text(fixture.yaml_text(data), encoding="utf-8")
    elif change == "delete_layout":
        path = LAYOUT
        (workspace / LAYOUT).unlink()
    else:
        data = fixture.interior_data()
        data["id"] = "synthetic_cellar"
        data["exterior"] = None
        path = f"content/maps/interiors/{data['id']}.yaml"
        (workspace / path).write_text(fixture.yaml_text(data), encoding="utf-8")
        editor.follow()
        assert editor.move("back", 2, 2)[0] == 200
        (workspace / path).unlink()
    sequence = editor.state()["external_change"]["sequence"]
    assert editor.follow() is True
    state = editor.state()
    assert state["preview_state"] == "current"
    assert state["history"]["undo"] is None
    assert state["external_change"]["sequence"] == sequence + 1
    assert state["external_change"]["documents"] == [path]
    ids = {interior["id"] for interior in state["world"]["interiors"]}
    assert ("synthetic_cellar" in ids) is (change == "create")
    if change == "delete_layout":
        assert editor.positions()["back"] is None


def test_a_rename_that_breaks_the_document_identity_keeps_a_stale_preview_until_renamed_back(workspace):
    editor = Editor(workspace)
    world = editor.state()["world"]
    renamed = workspace / "content/maps/interiors/renamed_hall.yaml"
    os.rename(workspace / INTERIOR, renamed)
    assert editor.follow() is True
    state = editor.state()
    assert state["preview_state"] == "stale"
    assert state["world"] == world
    assert any(item["relative_path"] == "content/maps/interiors/renamed_hall.yaml"
               for item in state["candidate_diagnostics"])
    os.rename(renamed, workspace / INTERIOR)
    assert editor.follow() is True
    assert editor.state()["preview_state"] == "current"


def test_malformed_content_keeps_the_prior_preview_stale_and_a_correction_is_adopted(workspace):
    editor = Editor(workspace)
    assert editor.move("back", 1, 1)[0] == 200
    before = editor.state()
    (workspace / SETTLEMENT).write_text(MALFORMED, encoding="utf-8")
    assert editor.follow() is True
    state = editor.state()
    assert state["preview_state"] == "stale"
    assert (state["world"], state["snapshot_read_at"]) == (before["world"], before["snapshot_read_at"])
    [diagnostic] = [d for d in state["candidate_diagnostics"] if d["relative_path"] == SETTLEMENT]
    assert diagnostic["line"] is not None
    assert state["external_change"]["sequence"] == 0
    # The service never rewrites the malformed file from its preview.
    assert (workspace / SETTLEMENT).read_text(encoding="utf-8") == MALFORMED
    corrected = fixture.settlement_data()
    corrected["nodes"]["yard"]["x_m"] = 600
    _replace_atomically(workspace / SETTLEMENT, fixture.yaml_text(corrected))
    assert editor.follow() is True
    state = editor.state()
    assert state["preview_state"] == "current"
    assert state["external_change"]["documents"] == [SETTLEMENT]
    nodes = {node["id"]: node for node in state["world"]["settlements"][0]["nodes"]}
    assert nodes["yard"]["local_m"] == [600, 400]


def test_restoring_the_exact_prior_bytes_after_a_failure_is_not_an_external_change(workspace):
    editor = Editor(workspace)
    assert editor.move("back", 1, 1)[0] == 200
    original = (workspace / SETTLEMENT).read_text(encoding="utf-8")
    (workspace / SETTLEMENT).write_text(MALFORMED, encoding="utf-8")
    editor.follow()
    (workspace / SETTLEMENT).write_text(original, encoding="utf-8")
    assert editor.follow() is True
    state = editor.state()
    assert state["preview_state"] == "current"
    assert state["external_change"]["sequence"] == 0
    # The failed candidate already ended the segment.
    assert state["history"]["undo"] is None


def test_a_half_written_candidate_is_reread_once_before_it_is_published_stale(workspace, monkeypatch):
    from elosern_map_editor import app as app_module

    editor = Editor(workspace)
    assert editor.move("back", 1, 1)[0] == 200
    real = app_module.read_workspace
    calls = []

    def read(*args):
        calls.append(1)
        if len(calls) == 1:
            # The first read lands mid-write; the writer finishes meanwhile.
            (workspace / SETTLEMENT).write_text(MALFORMED, encoding="utf-8")
            broken = real(*args)
            (workspace / SETTLEMENT).write_text(fixture.yaml_text(fixture.settlement_data()), encoding="utf-8")
            return broken
        return real(*args)

    monkeypatch.setattr(app_module, "read_workspace", read)
    assert editor.follow() is False
    assert len(calls) == 2
    state = editor.state()
    assert state["preview_state"] == "current"
    assert state["history"]["undo"] is not None


# -- concurrent writers and the fingerprint guard ---------------------------
def test_an_external_replacement_before_the_save_reaches_the_guard_is_kept(workspace):
    editor = Editor(workspace)
    assert editor.move("back", 1, 1)[0] == 200
    read_fingerprint = editor.layout_fingerprint()
    # The external write lands after the editor's read, before any watcher run.
    _replace_atomically(workspace / LAYOUT, _layout_text(9, 9))
    external = (workspace / LAYOUT).read_bytes()
    status, body = editor.move("back", 2, 2, expected=read_fingerprint)
    assert (status, body["error"]["code"]) == (409, "stale_document")
    assert (workspace / LAYOUT).read_bytes() == external
    # The editor reloads; nothing is merged or retried.
    editor.follow()
    assert editor.positions()["back"] == [9, 9]
    assert (workspace / LAYOUT).read_bytes() == external


def test_a_draft_submitted_against_the_old_snapshot_is_rejected_without_changing_disk(workspace):
    editor = Editor(workspace)
    assert editor.move("back", 1, 1)[0] == 200
    old = editor.state()
    old_fingerprint = editor.layout_fingerprint()
    _replace_atomically(workspace / LAYOUT, _layout_text(9, 9))
    editor.follow()
    external = (workspace / LAYOUT).read_bytes()
    arguments = {"interior_id": fixture.INTERIOR_ID, "room_id": "back", "x": 4, "y": 4}
    # Built against the held old snapshot: the revision no longer matches ...
    status, body = editor.raw("move_interior_layout", editor.envelope(
        LAYOUT, old_fingerprint, arguments, snapshot_revision=old["snapshot_revision"]))
    assert (status, body["error"]["code"]) == (409, "stale_snapshot")
    # ... and with a current revision, the document fingerprint guard rejects it.
    status, body = editor.raw("move_interior_layout", editor.envelope(LAYOUT, old_fingerprint, arguments))
    assert (status, body["error"]["code"]) == (409, "stale_document")
    assert (workspace / LAYOUT).read_bytes() == external


def test_a_concurrent_external_change_to_another_document_starts_a_new_segment(workspace):
    faults = Faults()
    editor = Editor(workspace, fault=faults)
    assert editor.move("back", 1, 1)[0] == 200
    corrected = fixture.settlement_data()
    corrected["nodes"]["yard"]["x_m"] = 650
    faults.armed["flush_directory"] = lambda: _replace_atomically(
        workspace / SETTLEMENT, fixture.yaml_text(corrected))
    assert editor.move("back", 2, 2)[0] == 200
    state = editor.state()
    assert state["external_change"]["documents"] == [SETTLEMENT]
    # The earlier operation is gone; this guarded one starts the segment.
    assert state["history"]["undo"]["expected_document_fingerprint"] == sha(workspace / LAYOUT)
    assert editor.undo()[0] == 200
    assert editor.positions()["back"] == [1, 1]
    assert editor.state()["history"]["undo"] is None


def test_an_external_overwrite_of_the_saved_document_is_never_recorded_as_own(workspace):
    faults = Faults()
    editor = Editor(workspace, fault=faults)
    assert editor.move("back", 1, 1)[0] == 200
    faults.armed["flush_directory"] = lambda: _replace_atomically(workspace / LAYOUT, _layout_text(9, 9))
    assert editor.move("back", 2, 2)[0] == 200
    state = editor.state()
    assert state["history"]["undo"] is None
    assert state["external_change"]["documents"] == [LAYOUT]
    assert editor.positions()["back"] == [9, 9]


def test_artifact_changes_publish_status_without_ending_the_segment(workspace):
    editor = Editor(workspace)
    assert editor.move("back", 1, 1)[0] == 200
    revision = editor.state()["snapshot_revision"]
    fixture.write_reference_context(workspace)
    assert editor.follow() is True
    state = editor.state()
    assert state["snapshot_revision"] == revision + 1
    assert state["external_context_status"]["status"] == "current"
    assert state["history"]["undo"] is not None
    assert state["external_change"]["sequence"] == 0


# -- sessions ----------------------------------------------------------------
def test_a_restart_rejects_the_old_tab_and_writes_after_a_fresh_read(workspace):
    old = Editor(workspace)
    assert old.move("back", 1, 1)[0] == 200
    stale_envelope = old.envelope(LAYOUT, old.layout_fingerprint(),
                                  {"interior_id": fixture.INTERIOR_ID, "room_id": "back", "x": 2, "y": 2})
    restarted = Editor(workspace)
    saved = (workspace / LAYOUT).read_bytes()
    response = restarted.client.post("/api/commands/move_interior_layout", headers=old.headers(),
                                      content=json.dumps(stale_envelope))
    assert (response.status_code, response.json()["error"]["code"]) == (401, "unauthorized")
    status, body = restarted.raw("move_interior_layout", stale_envelope)
    assert (status, body["error"]["code"]) == (409, "stale_session")
    assert (workspace / LAYOUT).read_bytes() == saved
    # The restarted service has no history to replay; a fresh read writes.
    state = restarted.state()
    assert state["history"]["undo"] is None
    assert restarted.move("back", 3, 3)[0] == 200
    assert restarted.positions()["back"] == [3, 3]
