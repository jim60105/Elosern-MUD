"""Map editor file following, driven against the real service process.

The service runs as a child process from its own locked environment (scrubbed
environment, no ``PATH``) against a temporary synthetic workspace, with its
real directory watcher. An external writer changes files on disk; every
assertion reads the files and the service state: loadable external changes are
adopted without any editor-side write, and an editor save that raced an
external replacement is rejected with the external bytes intact.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

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


def _layout(x: int, y: int) -> str:
    return f"version: 1\nkind: layout\nid: {synthetic.INTERIOR_ID}\npositions:\n  back: {{x: {x}, y: {y}}}\n"


def _replace(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.external")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _move(editor, x, y, expected, **overrides):
    arguments = {"interior_id": synthetic.INTERIOR_ID, "room_id": "back", "x": x, "y": y}
    return harness.command(
        editor, "move_interior_layout", document_id=LAYOUT, expected=expected, arguments=arguments, **overrides
    )


def _back(state: dict):
    rooms = state["world"]["interiors"][0]["rooms"]
    return {room["id"]: room["layout_position"] for room in rooms}["back"]


def wait_for(predicate, message: str, timeout: float = 20.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.05)
    raise AssertionError(message)


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
        self.root = Path(tempfile.mkdtemp(prefix="map-editor-following-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.workspace = synthetic.write_workspace(self.root / "workspace")
        self.layout = self.workspace / LAYOUT


class ExternalChangeProcessTests(_EditorCase):
    def test_a_loadable_external_replacement_is_adopted_without_an_editor_write(self):
        with harness.EditorProcess(self.workspace) as editor:
            self.assertEqual(_move(editor, 1, 1, "absent")[0], 200)
            self.assertIsNotNone(editor.workspace_state()["history"]["undo"])
            _replace(self.layout, _layout(7, 8))
            state = wait_for(
                lambda: (s := editor.workspace_state())["external_change"]["sequence"] == 1 and s,
                "the external replacement was not adopted",
            )
            self.assertEqual(_back(state), [7, 8])
            self.assertIsNone(state["history"]["undo"])
            self.assertEqual(state["external_change"]["documents"], [LAYOUT])
            self.assertEqual(state["preview_state"], "current")
        # No editor-side write happened after the external one.
        self.assertEqual(self.layout.read_text(encoding="utf-8"), _layout(7, 8))

    def test_a_save_racing_an_external_replacement_is_rejected_with_the_external_bytes_intact(self):
        with harness.EditorProcess(self.workspace) as editor:
            self.assertEqual(_move(editor, 1, 1, "absent")[0], 200)
            read = _sha(self.layout)
            state = editor.workspace_state()
            # The external replacement lands between the editor's read and its save.
            _replace(self.layout, _layout(9, 9))
            external = self.layout.read_bytes()
            status, body = _move(editor, 2, 2, read, snapshot_revision=state["snapshot_revision"])
            self.assertEqual(status, 409, body)
            self.assertIn(body["error"]["code"], {"stale_document", "stale_snapshot"})
            self.assertEqual(self.layout.read_bytes(), external)
            # The service reloads the external content; nothing merged or retried.
            state = wait_for(
                lambda: (s := editor.workspace_state())["external_change"]["sequence"] == 1 and s,
                "the external replacement was not adopted",
            )
            self.assertEqual(_back(state), [9, 9])
            # A save built against the held old snapshot is rejected by the guard.
            status, body = _move(editor, 3, 3, read)
            self.assertEqual((status, body["error"]["code"]), (409, "stale_document"))
            self.assertEqual(self.layout.read_bytes(), external)


if __name__ == "__main__":
    unittest.main()
