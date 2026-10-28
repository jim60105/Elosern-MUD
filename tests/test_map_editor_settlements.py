"""Map editor settlement commands, driven against the real service process.

The service runs as a child process from its own locked environment with a
scrubbed environment and no ``PATH`` against a temporary synthetic workspace.
Every assertion inspects the files on disk: a settlement command writes only
its settlement document, a new local map writes no location data and is
diagnosed unfinished, a moved node keeps its ID, authored road directions and
every dependent, a two-way street is two directed entries saved together with
core lengths, and refused commands leave every byte unchanged.

Independently known synthetic geometry: ``gate`` at local (0, 0), ``yard`` at
(300, 400); ``gate>yard`` is straight (500 m) and ``yard>gate`` bends at
(300, 0) (400 + 300 = 700 m).
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from ruamel.yaml import YAML

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

LOCATIONS = "content/maps/locations.yaml"
TOWN = synthetic.SETTLEMENT_ID
SETTLEMENT = f"content/maps/settlements/{TOWN}.yaml"
NEW_MAP = "content/maps/settlements/wild_camp.yaml"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SettlementProcessTests(unittest.TestCase):
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
        self.root = Path(tempfile.mkdtemp(prefix="map-editor-settlements-"))
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

    def data(self, document=SETTLEMENT):
        return YAML(typ="safe", pure=True).load((self.workspace / document).read_text(encoding="utf-8"))

    @staticmethod
    def settlement(state, settlement_id=TOWN):
        return next(row for row in state["world"]["settlements"] if row["id"] == settlement_id)

    def test_a_new_local_map_writes_only_its_document_and_is_unfinished(self):
        editor = self.start()
        before = synthetic.tree_digest(self.workspace)
        status, body = self.send(editor, "create_settlement", NEW_MAP, {
            "settlement_id": "wild_camp", "location_id": synthetic.BARE_LOCATION_ID, "anchor_cell": [30, 12],
            "local_anchor_m": [0, 0], "options": None})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(before), {NEW_MAP})
        self.assertEqual(_sha(self.workspace / LOCATIONS), before[LOCATIONS])
        state = editor.workspace_state()
        location = next(row for row in state["world"]["locations"] if row["id"] == synthetic.BARE_LOCATION_ID)
        self.assertEqual(location["local_maps"], ["wild_camp"])
        unfinished = [row for row in state["diagnostics"] if row["code"] == "empty_graph"]
        self.assertEqual([(row["relative_path"], row["category"]) for row in unfinished], [(NEW_MAP, "semantic")])
        self.assertEqual(self.data(NEW_MAP)["nodes"], {})

    def test_moving_a_referenced_node_keeps_its_id_directions_and_dependents(self):
        editor = self.start()
        directions = {(road["source"], road["destination"]): road["direction"] for road in self.data()["roads"]}
        before = synthetic.tree_digest(self.workspace)
        status, body = self.send(editor, "move_nodes", SETTLEMENT, {"settlement_id": TOWN, "moves": [
            {"node_id": "yard", "x_m": 0, "y_m": 400}]})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(before), {SETTLEMENT})
        self.assertEqual({(road["source"], road["destination"]): road["direction"] for road in self.data()["roads"]},
                         directions)
        state = editor.workspace_state()
        settlement = self.settlement(state)
        self.assertEqual({road["id"]: road["length_m"] for road in settlement["roads"]},
                         {"gate>yard": 400.0, "yard>gate": 800.0})
        self.assertEqual([row for row in state["diagnostics"] if row["category"] == "structure"], [])
        interior = next(row for row in state["world"]["interiors"] if row["id"] == synthetic.INTERIOR_ID)
        self.assertEqual(interior["exterior"]["node"], "yard")
        self.assertEqual(state["world"]["districts"][0]["landmark"]["object_id"], "yard")
        self.assertIn("yard", {row["id"] for row in settlement["nodes"]})

    def test_a_two_way_street_is_two_directed_entries_in_one_save(self):
        editor = self.start()
        fields = {"x_m": 600, "y_m": 0, "prototype_parent": "grid_room", "key": "Well", "desc": "",
                  "anchor_key": None, "typeclass": None, "scene_archetype": None}
        self.assertEqual(self.send(editor, "create_node", SETTLEMENT,
                                   {"settlement_id": TOWN, "node_id": "well", "fields": fields})[0], 200)
        before = synthetic.tree_digest(self.workspace)
        status, body = self.send(editor, "create_road", SETTLEMENT, {
            "settlement_id": TOWN, "source": "gate", "destination": "well", "direction": "e", "bends": [],
            "return": {"direction": "w", "bends": []}})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(before), {SETTLEMENT})
        roads = {(road["source"], road["destination"]): road["direction"] for road in self.data()["roads"]}
        self.assertEqual((roads[("gate", "well")], roads[("well", "gate")]), ("e", "w"))
        lengths = {road["id"]: road["length_m"] for road in self.settlement(editor.workspace_state())["roads"]}
        self.assertEqual((lengths["gate>well"], lengths["well>gate"]), (600.0, 600.0))
        status, route = editor.request("GET", f"/api/settlements/{TOWN}/route?source=well&destination=yard")
        self.assertEqual(status, 200)
        # well -> gate (600 m west) then gate -> yard (500 m straight).
        self.assertEqual((route["status"], route["length_m"]), ("route", 1100.0))

    def test_refused_and_cross_document_commands_write_nothing(self):
        synthetic.write_reference_context(self.workspace)
        editor = self.start()
        before = synthetic.tree_digest(self.workspace)
        cases = (
            ("delete_nodes", SETTLEMENT, {"settlement_id": TOWN, "node_ids": ["yard"]}, 409),
            ("move_nodes", LOCATIONS, {"settlement_id": TOWN, "moves": [{"node_id": "yard", "x_m": 1, "y_m": 1}]}, 400),
            ("move_nodes", SETTLEMENT, {"settlement_id": TOWN, "moves": [{"node_id": "yard", "x_m": 0, "y_m": 0}]}, 422),
            ("create_road", SETTLEMENT, {"settlement_id": TOWN, "source": "gate", "destination": "yard",
                                         "direction": "e", "bends": [], "return": None}, 422),
            ("set_node_fields", SETTLEMENT, {"settlement_id": TOWN, "node_id": "yard", "fields": {"id": "renamed"}}, 400),
        )
        for name, document, arguments, expected in cases:
            with self.subTest(name=name, expected=expected):
                status, _ = self.send(editor, name, document, arguments)
                self.assertEqual(status, expected)
        self.assertEqual(self.changed(before), set())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
