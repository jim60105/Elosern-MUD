"""Map editor interior commands, driven against the real service process.

The service runs as a child process from its own locked environment with a
scrubbed environment and no ``PATH`` against a temporary synthetic workspace.
Every assertion inspects the files on disk: a standalone room or interior
writes only its interior document and never a service record or a layout, a
duplicated room gets a new identity without relationships, a service-joined
room keeps its identity when its prose changes, and layout operations write
only the layout document while the world (and every settlement route length)
stays byte-for-byte and fingerprint-for-fingerprint unchanged.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from ruamel.yaml import YAML

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

HALL = synthetic.INTERIOR_ID
INTERIOR = f"content/maps/interiors/{HALL}.yaml"
LAYOUT = f"content/map-editor-layouts/{HALL}.yaml"
ANNEX = "content/maps/interiors/synthetic_annex.yaml"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fields(name: str) -> dict:
    return {"name_zh": name, "desc_zh": "A synthetic room.", "scene_archetype": None, "art_key": None}


class InteriorProcessTests(unittest.TestCase):
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
        self.root = Path(tempfile.mkdtemp(prefix="map-editor-interiors-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.workspace = synthetic.write_workspace(self.root / "workspace")

    def start(self):
        editor = harness.EditorProcess(self.workspace)
        editor.__enter__()
        self.addCleanup(editor.__exit__, None, None, None)
        return editor

    def send(self, editor, name, document, arguments):
        path = self.workspace / document
        return harness.command(editor, name, document_id=document,
                               expected=_sha(path) if path.exists() else "absent", arguments=arguments)

    def changed(self, before):
        now = synthetic.tree_digest(self.workspace)
        return {path for path in set(now) | set(before) if now.get(path) != before.get(path)}

    def data(self, document=INTERIOR):
        return YAML(typ="safe", pure=True).load((self.workspace / document).read_text(encoding="utf-8"))

    @covers_requirement("map-editor-interiors::interior-editing-keeps-topology-separate-from-presentation-layout")
    def test_a_standalone_interior_and_room_write_only_their_document(self):
        editor = self.start()
        before = synthetic.tree_digest(self.workspace)
        status, body = self.send(editor, "create_interior", ANNEX, {
            "interior_id": "synthetic_annex", "room_id": "annex_lobby", "fields": _fields("別館")})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(before), {ANNEX})
        annex = self.data(ANNEX)
        self.assertEqual((annex["exterior"], annex["connections"]), (None, []))
        status, body = self.send(editor, "create_room", ANNEX, {
            "interior_id": "synthetic_annex", "room_id": "annex_store", "fields": _fields("倉庫")})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(before), {ANNEX})
        self.assertFalse((self.workspace / "content/map-editor-layouts").exists())
        state = editor.workspace_state()
        self.assertEqual([row for row in state["diagnostics"] if row["category"] == "structure"], [])
        rooms = next(row for row in state["world"]["interiors"] if row["id"] == "synthetic_annex")["rooms"]
        self.assertEqual([room["id"] for room in rooms], ["annex_lobby", "annex_store"])
        self.assertTrue(all(room["layout_position"] is None for room in rooms))

    @covers_requirement("map-editor-interiors::interior-editing-keeps-topology-separate-from-presentation-layout")
    def test_a_duplicated_room_has_a_new_identity_and_no_relationship(self):
        editor = self.start()
        connections = self.data()["connections"]
        before = synthetic.tree_digest(self.workspace)
        status, body = self.send(editor, "duplicate_room", INTERIOR, {
            "interior_id": HALL, "room_id": "front", "new_room_id": "front_twin"})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(before), {INTERIOR})
        data = self.data()
        self.assertEqual(data["rooms"]["front_twin"], data["rooms"]["front"])
        self.assertEqual(data["connections"], connections)
        self.assertEqual(data["exterior"]["room"], "front")
        # The same ID again, here or in another interior, is refused unwritten.
        before = synthetic.tree_digest(self.workspace)
        status, _ = self.send(editor, "create_interior", ANNEX, {
            "interior_id": "synthetic_annex", "room_id": "front_twin", "fields": _fields("x")})
        self.assertEqual(status, 422)
        self.assertEqual(self.changed(before), set())

    @covers_requirement("map-editor-interiors::interior-editing-keeps-topology-separate-from-presentation-layout")
    def test_an_existing_service_room_keeps_its_identity_when_its_prose_changes(self):
        key = f"interior_room:{HALL}:back"
        synthetic.write_reference_context(self.workspace, incoming={key: [{
            "source": "place:back", "source_domain": "places", "source_file": "external/declarations.txt",
            "target": {"domain": "interior_room", "map_id": HALL, "object_id": "back", "cell": None}}]})
        editor = self.start()
        before = synthetic.tree_digest(self.workspace)
        status, body = self.send(editor, "set_room_fields", INTERIOR, {
            "interior_id": HALL, "room_id": "back", "fields": {"name_zh": "改名後室", "desc_zh": "改寫的描述。"}})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(before), {INTERIOR})
        self.assertEqual(list(self.data()["rooms"]), ["front", "back"])
        state = editor.workspace_state()
        self.assertEqual([row["id"] for row in state["world"]["interiors"]], [HALL])
        self.assertTrue(state["external_context_status"]["current"])
        self.assertEqual([row["source"] for row in state["external_incoming_references"][key]], ["place:back"])
        # The join still protects the room: deletion is refused, nothing written.
        before = synthetic.tree_digest(self.workspace)
        status, _ = self.send(editor, "delete_room", INTERIOR, {"interior_id": HALL, "room_id": "back"})
        self.assertEqual(status, 409)
        self.assertEqual(self.changed(before), set())

    @covers_requirement("map-editor-interiors::interior-editing-keeps-topology-separate-from-presentation-layout")
    def test_layout_operations_leave_the_world_and_its_routes_unchanged(self):
        editor = self.start()
        state = editor.workspace_state()
        fingerprint = state["world"]["fingerprint"]
        lengths = {road["id"]: road["length_m"] for road in state["world"]["settlements"][0]["roads"]}
        diagnostics = state["diagnostics"]
        before = synthetic.tree_digest(self.workspace)
        status, body = self.send(editor, "arrange_interior_layout", LAYOUT, {
            "interior_id": HALL, "positions": [{"room_id": "front", "x": 0, "y": 0}, {"room_id": "back", "x": 1, "y": 0}]})
        self.assertEqual(status, 200, body)
        status, body = self.send(editor, "move_interior_layout", LAYOUT, {
            "interior_id": HALL, "room_id": "back", "x": 2, "y": 3})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(before), {LAYOUT})
        state = editor.workspace_state()
        self.assertEqual(state["world"]["fingerprint"], fingerprint)
        self.assertEqual({road["id"]: road["length_m"] for road in state["world"]["settlements"][0]["roads"]}, lengths)
        self.assertEqual(state["diagnostics"], diagnostics)
        self.assertEqual(self.data(LAYOUT)["positions"], {"front": {"x": 0, "y": 0}, "back": {"x": 2, "y": 3}})
        # No coordinate or distance enters the interior source.
        for room in self.data()["rooms"].values():
            self.assertEqual(set(room), {"name_zh", "desc_zh", "scene_archetype", "art_key"})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
