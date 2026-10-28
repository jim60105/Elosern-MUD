"""Map editor directory watching and reconnects, against the real process.

The standalone service runs as a child process with its real watcher against
a temporary synthetic workspace. The tests produce real directory events (own
saves, external replacement, malformed then corrected YAML) and restart the
service on the same port, and assert the published state and the files.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tools.spec_traceability import covers_requirement

from tests.test_map_editor_file_following import (
    LAYOUT,
    _back,
    _EditorCase,
    _layout,
    _move,
    _replace,
    _sha,
    harness,
    synthetic,
    wait_for,
)

SETTLEMENT = f"content/maps/settlements/{synthetic.SETTLEMENT_ID}.yaml"


def _quiet(editor) -> None:
    """Wait until the watcher is active and its reconciliations have settled."""

    wait_for(lambda: editor.workspace_state()["following"]["active"], "the watcher never became active")
    last, since = editor.workspace_state()["following"]["batches"], time.monotonic()
    while time.monotonic() - since < 1.5:
        time.sleep(0.1)
        now = editor.workspace_state()["following"]["batches"]
        if now != last:
            last, since = now, time.monotonic()


class WatchingProcessTests(_EditorCase):
    @covers_requirement(
        "map-editor-file-following::external-changes-are-followed-without-overwriting-them",
        "map-editor-file-following::watching-and-reconnect-retain-truthful-preview-state",
    )
    def test_own_saves_keep_history_and_a_later_external_replacement_is_adopted(self):
        with harness.EditorProcess(self.workspace) as editor:
            _quiet(editor)
            before = editor.workspace_state()["following"]["batches"]
            self.assertEqual(_move(editor, 1, 1, "absent")[0], 200)
            self.assertEqual(_move(editor, 2, 2, _sha(self.layout))[0], 200)
            revision = editor.workspace_state()["snapshot_revision"]
            wait_for(lambda: editor.workspace_state()["following"]["batches"] > before,
                     "the own saves produced no reconciled notification")
            _quiet(editor)
            state = editor.workspace_state()
            self.assertEqual(state["snapshot_revision"], revision)
            self.assertIsNotNone(state["history"]["undo"])
            self.assertEqual(state["external_change"]["sequence"], 0)
            _replace(self.layout, _layout(5, 6))
            state = wait_for(
                lambda: (s := editor.workspace_state())["external_change"]["sequence"] == 1 and s,
                "the external replacement was not adopted",
            )
            self.assertIsNone(state["history"]["undo"])
            self.assertEqual(_back(state), [5, 6])

    @covers_requirement(
        "map-editor-file-following::watching-and-reconnect-retain-truthful-preview-state",
    )
    def test_malformed_yaml_keeps_a_stale_preview_until_the_correction_is_adopted(self):
        path = self.workspace / SETTLEMENT
        with harness.EditorProcess(self.workspace) as editor:
            _quiet(editor)
            world = editor.workspace_state()["world"]
            path.write_text("version: 1\nkind: [unclosed\n", encoding="utf-8")
            state = wait_for(lambda: (s := editor.workspace_state())["preview_state"] == "stale" and s,
                             "the malformed file did not make the preview stale")
            self.assertEqual(state["world"], world)
            [diagnostic] = [d for d in state["candidate_diagnostics"] if d["relative_path"] == SETTLEMENT]
            self.assertIsNotNone(diagnostic["line"])
            status, body = _move(editor, 1, 1, "absent")
            self.assertEqual((status, body["error"]["reason"]), (423, "stale_preview"))
            self.assertFalse(self.layout.exists())
            self.assertEqual(path.read_text(encoding="utf-8"), "version: 1\nkind: [unclosed\n")
            corrected = synthetic.settlement_data()
            corrected["nodes"]["yard"]["x_m"] = 640
            _replace(path, synthetic.yaml_text(corrected))
            wait_for(lambda: editor.workspace_state()["preview_state"] == "current", "no automatic recovery")
            self.assertEqual(_move(editor, 1, 1, "absent")[0], 200)

    @covers_requirement(
        "map-editor-file-following::watching-and-reconnect-retain-truthful-preview-state",
    )
    def test_a_restart_rejects_the_old_session_and_writes_after_a_fresh_read(self):
        port = harness.free_port()
        with harness.EditorProcess(self.workspace, port=port) as editor:
            self.assertEqual(_move(editor, 1, 1, "absent")[0], 200)
            old_session = editor.session()
            old_state = editor.workspace_state()
        saved = self.layout.read_bytes()
        with harness.EditorProcess(self.workspace, port=port) as editor:
            body = {
                "session_generation": old_session["session_generation"],
                "snapshot_revision": old_state["snapshot_revision"],
                "segment": "old-tab",
                "document_id": LAYOUT,
                "expected_document_fingerprint": _sha(self.layout),
                "arguments": {"interior_id": synthetic.INTERIOR_ID, "room_id": "back", "x": 2, "y": 2},
            }
            import json

            headers = {"Origin": editor.origin, "Content-Type": "application/json"}
            status, reply = editor.request("POST", "/api/commands/move_interior_layout",
                                           headers={**headers, "X-Map-Editor-Token": old_session["token"]},
                                           body=json.dumps(body))
            self.assertEqual((status, reply["error"]["code"]), (401, "unauthorized"))
            fresh = editor.session()
            status, reply = editor.request("POST", "/api/commands/move_interior_layout",
                                           headers={**headers, "X-Map-Editor-Token": fresh["token"]},
                                           body=json.dumps(body))
            self.assertEqual((status, reply["error"]["code"]), (409, "stale_session"))
            self.assertEqual(self.layout.read_bytes(), saved)
            # The new session starts with no history to replay; a fresh read writes.
            state = editor.workspace_state()
            self.assertIsNone(state["history"]["undo"])
            self.assertEqual(_back(state), [1, 1])
            self.assertEqual(_move(editor, 3, 3, _sha(self.layout))[0], 200)
            self.assertEqual(_back(editor.workspace_state()), [3, 3])


if __name__ == "__main__":
    unittest.main()
