"""Map editor document commands, driven against the real service process.

The service runs as a child process from its own locked environment with a
scrubbed environment and no ``PATH`` against a temporary synthetic workspace.
Every assertion inspects the files on disk: a layout command writes only its
own layout document, a rejected or failed command leaves the prior bytes, and
undo of the first layout returns to absence.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parent.parent
EDITOR_TESTS = REPO_ROOT / "tools" / "map-editor" / "tests"


def _load(name: str):
    import importlib.util
    import sys

    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, EDITOR_TESTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


harness = _load("process_harness")
synthetic = _load("synthetic_workspace")

LAYOUT = f"content/map-editor-layouts/{synthetic.INTERIOR_ID}.yaml"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _move(editor, room, x, y, expected="absent", **overrides):
    arguments = {"interior_id": synthetic.INTERIOR_ID, "room_id": room, "x": x, "y": y}
    return harness.command(
        editor, "move_interior_layout", document_id=LAYOUT, expected=expected, arguments=arguments, **overrides
    )


class _EditorCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            harness.editor_python()
        except harness.EditorUnavailable as error:
            if not harness.skip_allowed():
                raise
            raise unittest.SkipTest(f"standalone editor environment unavailable: {error}") from error

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="map-editor-persistence-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.workspace = synthetic.write_workspace(self.root / "workspace")
        self.world = {path: _sha(self.workspace / path) for path in synthetic.DOCUMENTS}

    def world_now(self):
        return {path: _sha(self.workspace / path) for path in self.world}


class DocumentCommandProcessTests(_EditorCase):
    @covers_requirement(
        "map-editor-persistence::completed-commands-save-exactly-one-validated-document",
        "map-editor-persistence::drafts-and-history-obey-completed-operation-boundaries",
    )
    def test_one_move_saves_only_its_layout_and_undo_returns_to_absence(self):
        with harness.EditorProcess(self.workspace) as editor:
            status, body = _move(editor, "back", 2, 1)
            self.assertEqual(status, 200, body)
            path = self.workspace / LAYOUT
            self.assertEqual(body["fingerprint"], _sha(path))
            self.assertEqual(self.world_now(), self.world)
            state = editor.workspace_state()
            rooms = {room["id"]: room["layout_position"] for room in state["world"]["interiors"][0]["rooms"]}
            self.assertEqual(rooms["back"], [2, 1])
            # A stale expectation (the file now exists) is rejected unchanged.
            saved = path.read_bytes()
            status, body = _move(editor, "back", 9, 9, expected="absent")
            self.assertEqual((status, body["error"]["code"]), (409, "stale_document"))
            self.assertEqual(path.read_bytes(), saved)
            head = editor.workspace_state()["history"]["undo"]
            status, body = harness.command(
                editor,
                "undo",
                document_id=head["document_id"],
                expected=head["expected_document_fingerprint"],
                arguments={},
            )
            self.assertEqual((status, body["fingerprint"]), (200, "absent"))
            self.assertFalse(path.exists())
            self.assertEqual(editor.workspace_state()["world"]["layouts"], [])
        self.assertEqual(self.world_now(), self.world)

    @covers_requirement("map-editor-persistence::completed-commands-save-exactly-one-validated-document")
    def test_a_failed_write_keeps_the_first_saved_operation(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("directory permissions do not bind the superuser")
        with harness.EditorProcess(self.workspace) as editor:
            self.assertEqual(_move(editor, "back", 1, 1)[0], 200)
            path = self.workspace / LAYOUT
            first = path.read_bytes()
            history = editor.workspace_state()["history"]
            directory = path.parent
            directory.chmod(0o555)
            self.addCleanup(directory.chmod, 0o755)
            status, body = _move(editor, "back", 5, 5, expected=_sha(path))
            self.assertEqual((status, body["error"]["code"]), (500, "save_failed"))
            self.assertEqual(path.read_bytes(), first)
            self.assertEqual(sorted(p.name for p in directory.iterdir()), [path.name])
            state = editor.workspace_state()
            self.assertEqual(state["history"], history)
            self.assertFalse(state["write_pause"]["paused"])

    def test_document_ids_outside_the_named_owner_never_reach_the_disk(self):
        before = synthetic.tree_digest(self.workspace)
        with harness.EditorProcess(self.workspace) as editor:
            arguments = {"interior_id": synthetic.INTERIOR_ID, "room_id": "back", "x": 1, "y": 1}
            for document_id in (
                "../../outside.yaml",
                "content/maps/continent.yaml",
                "content/map-reference-context.json",
            ):
                status, body = harness.command(
                    editor, "move_interior_layout", document_id=document_id, expected="absent", arguments=arguments
                )
                self.assertEqual((status, body["error"]["code"]), (400, "cross_document"), document_id)
            for interior_id in ("../maps/continent", "a/b"):
                status, body = harness.command(
                    editor,
                    "move_interior_layout",
                    document_id=f"content/map-editor-layouts/{interior_id}.yaml",
                    expected="absent",
                    arguments={**arguments, "interior_id": interior_id},
                )
                self.assertEqual((status, body["error"]["code"]), (400, "invalid_command"), interior_id)
            status, body = _move(editor, "back", 1, 1, session_generation="previous-session")
            self.assertEqual((status, body["error"]["code"]), (409, "stale_session"))
        self.assertEqual(synthetic.tree_digest(self.workspace), before)
        self.assertFalse((self.root / "outside.yaml").exists())


if __name__ == "__main__":
    unittest.main()
