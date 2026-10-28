"""Map editor geography commands, driven against the real service process.

The service runs as a child process from its own locked environment with a
scrubbed environment and no ``PATH`` against a temporary synthetic workspace.
Every assertion inspects the files on disk: a geography command writes only
its owning document, a rejected command leaves every byte unchanged, a new
location fabricates no local map, and a committed change recomputes the
core's terrain preview while leaving the partition artifact stale rather
than regenerated.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
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

CONTINENT = "content/maps/continent.yaml"
LOCATIONS = "content/maps/locations.yaml"
DISTRICTS = "content/maps/districts.yaml"
SETTLEMENT = f"content/maps/settlements/{synthetic.SETTLEMENT_ID}.yaml"
PARTITION = "world/maps/data/district_partition.json"
RIVER = {"kind": "waterway_route", "waterway_id": "synthetic_river"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GeographyProcessTests(unittest.TestCase):
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
        self.root = Path(tempfile.mkdtemp(prefix="map-editor-geography-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.workspace = synthetic.write_workspace(self.root / "workspace")

    def start(self):
        editor = harness.EditorProcess(self.workspace)
        editor.__enter__()
        self.addCleanup(editor.__exit__, None, None, None)
        return editor

    def send(self, editor, name, document, arguments):
        return harness.command(editor, name, document_id=document, expected=_sha(self.workspace / document),
                               arguments=arguments)

    def changed(self, before):
        now = synthetic.tree_digest(self.workspace)
        return {path for path in set(now) | set(before) if now.get(path) != before.get(path)}

    def sign_partition(self, editor):
        state = editor.workspace_state()
        signature = state["partition_status"]["expected_signature"]
        self.assertTrue(signature, "the service reports the current inputs' signature")
        target = self.workspace / PARTITION
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"version": 2, "algorithm_version": 1, "source_signature": signature,
                                      "fingerprint": "synthetic"}), encoding="utf-8")
        session = editor.session()
        editor.reload(session["token"], session["session_generation"])

    def test_a_river_point_saves_one_document_recomputes_terrain_and_stales_the_partition(self):
        editor = self.start()
        # The synthetic workspace has no artifact, so the service reports no
        # expected signature yet: write a stale one, then sign the current inputs.
        self.assertEqual(editor.workspace_state()["partition_status"]["status"], "unavailable")
        self.workspace.joinpath(PARTITION).parent.mkdir(parents=True, exist_ok=True)
        self.workspace.joinpath(PARTITION).write_text(
            json.dumps({"version": 2, "algorithm_version": 1, "source_signature": "0" * 64, "fingerprint": "s"}),
            encoding="utf-8",
        )
        session = editor.session()
        editor.reload(session["token"], session["session_generation"])
        self.sign_partition(editor)
        state = editor.workspace_state()
        self.assertEqual(state["partition_status"]["status"], "current")
        samples = state["world"]["continent"]["terrain_preview"]["samples"]
        before = synthetic.tree_digest(self.workspace)
        status, body = self.send(editor, "move_control_point", CONTINENT, {"feature": RIVER, "index": 0, "point": [20, 26]})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(before), {CONTINENT})
        state = editor.workspace_state()
        self.assertNotEqual(state["world"]["continent"]["terrain_preview"]["samples"], samples)
        self.assertEqual(state["partition_status"]["status"], "stale")
        self.assertEqual(_sha(self.workspace / PARTITION), before[PARTITION])
        # A second consecutive edit is still admitted while the partition is stale.
        status, _ = self.send(editor, "move_control_point", CONTINENT, {"feature": RIVER, "index": 0, "point": [20, 24]})
        self.assertEqual(status, 200)

    def test_a_location_and_its_local_map_are_separate_commands(self):
        editor = self.start()
        before = synthetic.tree_digest(self.workspace)
        arguments = {"location_id": "process_ruin", "kind": "dungeon", "display_name_zh": "遺跡", "description": "",
                     "geographic_constraint": "", "scene_archetype": None, "cell": [33, 8]}
        status, body = self.send(editor, "create_location", LOCATIONS, arguments)
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(before), {LOCATIONS})
        world = editor.workspace_state()["world"]
        location = next(row for row in world["locations"] if row["id"] == "process_ruin")
        self.assertEqual(location["local_maps"], [])
        self.assertFalse((self.workspace / "content/maps/settlements/process_ruin.yaml").exists())

    def test_rejected_and_cross_document_commands_write_nothing(self):
        editor = self.start()
        before = synthetic.tree_digest(self.workspace)
        cases = (
            ("delete_location", LOCATIONS, {"location_id": synthetic.LOCATION_ID}, 409),
            ("set_footprint_cell", LOCATIONS, {"settlement_id": synthetic.SETTLEMENT_ID, "cell": [1, 1], "filled": True}, 400),
            ("set_district_field", DISTRICTS, {"district_id": "synthetic_district", "field": "landmark",
                                               "value": {"domain": "settlement_node", "map_id": synthetic.SETTLEMENT_ID,
                                                         "object_id": "ghost", "cell": None}}, 422),
            ("remove_waterway", CONTINENT, {"waterway_id": "synthetic_river"}, 409),
        )
        for name, document, arguments, expected in cases:
            with self.subTest(name=name):
                status, _ = self.send(editor, name, document, arguments)
                self.assertEqual(status, expected)
        self.assertEqual(self.changed(before), set())

    def test_footprint_and_binding_write_only_the_settlement(self):
        editor = self.start()
        before = synthetic.tree_digest(self.workspace)
        status, _ = self.send(editor, "set_footprint_cell", SETTLEMENT,
                              {"settlement_id": synthetic.SETTLEMENT_ID, "cell": [6, 5], "filled": True})
        self.assertEqual(status, 200)
        status, _ = self.send(editor, "set_binding", SETTLEMENT,
                              {"settlement_id": synthetic.SETTLEMENT_ID, "anchor_cell": [6, 5], "local_anchor_m": [0, 0]})
        self.assertEqual(status, 200)
        self.assertEqual(self.changed(before), {SETTLEMENT})
        settlement = editor.workspace_state()["world"]["settlements"][0]
        self.assertEqual(settlement["footprint"]["cells"], [[5, 5], [6, 5]])
        self.assertEqual(settlement["binding"]["anchor_cell"], [6, 5])

    def test_a_stale_preview_rejects_geography_commands(self):
        editor = self.start()
        (self.workspace / DISTRICTS).write_text("version: 1\nkind: [unclosed\n", encoding="utf-8")
        session = editor.session()
        editor.reload(session["token"], session["session_generation"])
        before = synthetic.tree_digest(self.workspace)
        status, body = self.send(editor, "move_control_point", CONTINENT, {"feature": RIVER, "index": 0, "point": [20, 25]})
        self.assertEqual((status, body["error"]["reason"]), (423, "stale_preview"))
        self.assertEqual(self.changed(before), set())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
