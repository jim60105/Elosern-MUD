"""Map editor entrance relationships and reference-safe deletion, against the real service process.

The service runs as a child process from its own locked environment with a
scrubbed environment and no ``PATH`` against a temporary synthetic workspace.
Every assertion inspects the files on disk or the service's history:

- editing an exterior or a two-way interior link writes exactly its owning
  document, which records both meanings in one relationship;
- the starting-room entry never gains a return, and an absent, malformed or
  wrong-domain target is refused unwritten, naming the relationship and the
  field;
- a referenced room refuses deletion and locates the declaring link; removing
  the link and then deleting the room are separate operations and nothing
  cascades;
- a missing index refuses deletion while entrance edits still save;
- an external source that changes after inspection refuses a delete and an
  object-removing undo at execution, leaving disk and history unchanged.
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

TOWN = synthetic.SETTLEMENT_ID
HALL = synthetic.INTERIOR_ID
SETTLEMENT = f"content/maps/settlements/{TOWN}.yaml"
INTERIOR = f"content/maps/interiors/{HALL}.yaml"
ANNEX = "content/maps/interiors/synthetic_annex.yaml"
YARD = f"settlement_node:{TOWN}:yard"
GATE = f"settlement_node:{TOWN}:gate"
FRONT = f"interior_room:{HALL}:front"
BACK = f"interior_room:{HALL}:back"
LOBBY = "interior_room:synthetic_annex:annex_lobby"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _annex(root: Path) -> None:
    annex = synthetic.interior_data()
    annex.update(id="synthetic_annex", connections=[], exterior=None,
                 rooms={"annex_lobby": dict(annex["rooms"]["front"], name_zh="別館大廳")})
    (root / ANNEX).write_text(synthetic.yaml_text(annex), encoding="utf-8")


class RelationshipProcessTests(unittest.TestCase):
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
        self.root = Path(tempfile.mkdtemp(prefix="map-editor-relationships-"))
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

    def history(self, editor, direction):
        head = editor.workspace_state()["history"][direction]
        return harness.command(editor, direction, document_id=head["document_id"],
                               expected=head["expected_document_fingerprint"], arguments={})

    def changed(self, before):
        now = synthetic.tree_digest(self.workspace)
        return {path for path in set(now) | set(before) if now.get(path) != before.get(path)}

    def data(self, document):
        return YAML(typ="safe", pure=True).load((self.workspace / document).read_text(encoding="utf-8"))

    @covers_requirement("map-editor-relationships::cross-layer-relationships-edit-one-owner-and-expose-both-meanings")
    def test_an_entrance_edit_writes_one_owner_recording_both_meanings(self):
        _annex(self.workspace)
        editor = self.start()
        before = synthetic.tree_digest(self.workspace)
        value = {"room": BACK, "node": GATE, "doorway_key": "Side door", "doorway_aliases": ["side"]}
        status, body = self.send(editor, "set_exterior", INTERIOR, {"interior_id": HALL, "value": value})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(before), {INTERIOR})
        status, body = self.send(editor, "create_interior_link", INTERIOR, {
            "interior_id": HALL, "source": FRONT, "target": LOBBY, "label": "passage", "return_label": "hall"})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(before), {INTERIOR})
        data = self.data(INTERIOR)
        self.assertEqual((data["exterior"]["node"], data["exterior"]["room"]), ("gate", "back"))
        self.assertEqual(data["interior_links"], [{
            "source_room": "front", "target_interior": "synthetic_annex", "target_room": "annex_lobby",
            "label": "passage", "return_label": "hall"}])
        # The target interior holds no mirrored reverse record.
        self.assertEqual(self.data(ANNEX)["interior_links"], [])
        state = editor.workspace_state()
        self.assertEqual([row for row in state["diagnostics"] if row["category"] == "structure"], [])

    @covers_requirement("map-editor-relationships::cross-layer-relationships-edit-one-owner-and-expose-both-meanings")
    def test_the_start_entry_stays_one_way_and_invalid_targets_name_their_field(self):
        editor = self.start()
        before = synthetic.tree_digest(self.workspace)
        status, body = self.send(editor, "set_city_gate", SETTLEMENT, {"settlement_id": TOWN, "value": {
            "node": YARD, "exit_key": "Gate", "exit_aliases": [], "return_label": "back"}})
        self.assertEqual(status, 400)
        self.assertIn("return_label", body["error"]["message"])
        cases = [
            ("set_exterior", INTERIOR, {"interior_id": HALL, "value": {
                "room": FRONT, "node": f"settlement_node:{TOWN}:missing", "doorway_key": "d", "doorway_aliases": []}},
             "unknown_target", "arguments.value.node", "exterior"),
            ("set_exterior", INTERIOR, {"interior_id": HALL, "value": {
                "room": FRONT, "node": BACK, "doorway_key": "d", "doorway_aliases": []}},
             "wrong_domain", "arguments.value.node", "exterior"),
            ("set_city_gate", SETTLEMENT, {"settlement_id": TOWN, "value": {
                "node": "Yard", "exit_key": "Gate", "exit_aliases": []}},
             "invalid_endpoint", "arguments.value.node", "city_gate"),
        ]
        for name, document, arguments, code, field, relationship in cases:
            status, body = self.send(editor, name, document, arguments)
            self.assertEqual(status, 422, body)
            [row] = body["error"]["diagnostics"]
            self.assertEqual((row["code"], row["field_path"], row["relationship"], row["owner"]),
                             (code, field, relationship, document))
        self.assertEqual(self.changed(before), set())
        self.assertEqual(self.data(SETTLEMENT)["city_gate"], synthetic.settlement_data()["city_gate"])

    @covers_requirement("map-editor-relationships::deletion-requires-established-absence-of-incoming-static-references")
    def test_a_referenced_room_locates_its_link_which_is_removed_before_the_room(self):
        _annex(self.workspace)
        synthetic.write_reference_context(self.workspace)
        editor = self.start()
        status, body = self.send(editor, "create_interior_link", INTERIOR, {
            "interior_id": HALL, "source": BACK, "target": LOBBY, "label": "passage", "return_label": None})
        self.assertEqual(status, 200, body)
        before = synthetic.tree_digest(self.workspace)
        status, body = self.send(editor, "delete_room", ANNEX, {"interior_id": "synthetic_annex", "room_id": "annex_lobby"})
        self.assertEqual(status, 409, body)
        [row] = body["error"]["internal_references"]
        self.assertEqual((row["kind"], row["source"], row["field_path"]),
                         ("interior_link", INTERIOR, "interior_links[0].target_room"))
        self.assertEqual(self.changed(before), set())
        status, body = self.send(editor, "delete_interior_link", INTERIOR, {
            "interior_id": HALL, "source": BACK, "target": LOBBY, "label": "passage"})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(before), {INTERIOR})
        hall = self.data(INTERIOR)
        status, body = self.send(editor, "delete_room", ANNEX, {"interior_id": "synthetic_annex", "room_id": "annex_lobby"})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.data(ANNEX)["rooms"], {})
        # Nothing cascaded: the hall kept everything else it declares.
        self.assertEqual(self.data(INTERIOR), hall)
        self.assertEqual(self.changed(before), {INTERIOR, ANNEX})

    @covers_requirement("map-editor-relationships::deletion-requires-established-absence-of-incoming-static-references")
    def test_a_missing_index_refuses_deletion_while_entrance_edits_save(self):
        editor = self.start()
        self.assertFalse(editor.workspace_state()["external_context_status"]["current"])
        status, body = self.send(editor, "set_exterior", INTERIOR, {"interior_id": HALL, "value": {
            "room": FRONT, "node": YARD, "doorway_key": "Front door", "doorway_aliases": []}})
        self.assertEqual(status, 200, body)
        before = synthetic.tree_digest(self.workspace)
        status, body = self.send(editor, "delete_location", "content/maps/locations.yaml",
                                 {"location_id": synthetic.BARE_LOCATION_ID})
        self.assertEqual(status, 409, body)
        self.assertEqual(body["error"]["code"], "deletion_refused")
        # The refusal names the unavailable index as its guard.
        self.assertIn("unavailable", body["error"].values())
        self.assertEqual(self.changed(before), set())

    @covers_requirement("map-editor-relationships::deletion-requires-established-absence-of-incoming-static-references")
    def test_an_external_change_after_inspection_refuses_a_delete_and_an_undo(self):
        synthetic.write_reference_context(self.workspace)
        editor = self.start()
        self.assertTrue(editor.workspace_state()["external_context_status"]["current"])
        fields = {"name_zh": "倉庫", "desc_zh": "A synthetic store.", "scene_archetype": None, "art_key": None}
        status, body = self.send(editor, "create_room", INTERIOR, {"interior_id": HALL, "room_id": "store", "fields": fields})
        self.assertEqual(status, 200, body)
        history = editor.workspace_state()["history"]
        # The external closure changes after the page inspected the index.
        (self.workspace / "external" / "declarations.txt").write_text("changed declaration\n", encoding="utf-8")
        before = synthetic.tree_digest(self.workspace)
        status, body = self.send(editor, "delete_room", INTERIOR, {"interior_id": HALL, "room_id": "store"})
        self.assertEqual(status, 409, body)
        self.assertEqual(body["error"]["code"], "deletion_refused")
        status, body = self.history(editor, "undo")
        self.assertEqual(status, 409, body)
        self.assertEqual(body["error"]["code"], "deletion_refused")
        self.assertEqual(self.changed(before), set())
        self.assertIn("store", self.data(INTERIOR)["rooms"])
        now = editor.workspace_state()["history"]
        self.assertEqual((now["undo"], now["redo"]), (history["undo"], history["redo"]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
