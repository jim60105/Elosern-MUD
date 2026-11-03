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

    @covers_requirement("map-editor-geography::continental-authored-inputs-have-direct-and-explicit-editing-controls")
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

    @covers_requirement("map-editor-geography::district-landmark-positions-are-placed-on-the-continent-canvas")
    def test_district_landmarks_project_their_referent_centre_and_a_wilderness_move_writes_only_districts(self):
        data = synthetic.partitionable_districts_data()
        data["districts"]["synthetic_location_mark"] = {
            "district_name_zh": "合成地點區",
            "landmark_name_zh": "合成地點地標",
            "landmark": {"domain": "location", "map_id": None, "object_id": synthetic.LOCATION_ID, "cell": None},
            "kind": "voronoi",
            "region_key": None,
        }
        data["districts"]["synthetic_room_mark"] = {
            "district_name_zh": "合成房間區",
            "landmark_name_zh": "合成房間地標",
            "landmark": {"domain": "interior_room", "map_id": synthetic.INTERIOR_ID, "object_id": "front",
                         "cell": None},
            "kind": "voronoi",
            "region_key": None,
        }
        (self.workspace / DISTRICTS).write_text(synthetic.yaml_text(data), encoding="utf-8")
        # A stale artifact makes the service report the expected signature.
        self.workspace.joinpath(PARTITION).parent.mkdir(parents=True, exist_ok=True)
        self.workspace.joinpath(PARTITION).write_text(
            json.dumps({"version": 2, "algorithm_version": 1, "source_signature": "0" * 64, "fingerprint": "s"}),
            encoding="utf-8",
        )
        editor = self.start()
        state = editor.workspace_state()
        if state["preview_state"] != "current":
            print(state["diagnostics"])
        self.assertEqual(state["preview_state"], "current")
        rows = {row["id"]: row for row in state["world"]["districts"]}
        # A settlement-node landmark sits at the node's derived world position.
        self.assertIsNone(rows["synthetic_district"]["landmark"]["cell"])
        self.assertEqual(rows["synthetic_district"]["landmark_centre_m"], [5800, 5900])
        # A wilderness landmark projects its cell as a pair and its cell centre.
        self.assertEqual(rows["synthetic_north"]["landmark"]["cell"], [3, 25])
        self.assertEqual(rows["synthetic_north"]["landmark_centre_m"], [3500, 25500])
        location = next(row for row in state["world"]["locations"] if row["id"] == synthetic.LOCATION_ID)
        self.assertEqual(rows["synthetic_location_mark"]["landmark_centre_m"], location["centre_m"])
        self.assertIsNone(rows["synthetic_room_mark"]["landmark_centre_m"])

        self.sign_partition(editor)
        before = synthetic.tree_digest(self.workspace)

        def move(cell):
            return self.send(editor, "set_district_field", DISTRICTS, {
                "district_id": "synthetic_north",
                "field": "landmark",
                "value": {"domain": "wilderness_cell", "map_id": None, "object_id": None, "cell": cell},
            })

        status, body = move([4, 26])
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(before), {DISTRICTS})
        authored = YAML(typ="safe", pure=True).load((self.workspace / DISTRICTS).read_text(encoding="utf-8"))
        self.assertEqual(authored["districts"]["synthetic_north"]["landmark"]["cell"], {"cell_x": 4, "cell_y": 26})
        state = editor.workspace_state()
        row = next(row for row in state["world"]["districts"] if row["id"] == "synthetic_north")
        self.assertEqual(row["landmark"]["cell"], [4, 26])
        self.assertEqual(row["landmark_centre_m"], [4500, 26500])
        self.assertEqual(state["partition_status"]["status"], "stale")
        self.assertEqual(_sha(self.workspace / PARTITION), before[PARTITION])

        # A negative cell is refused and writes nothing.
        before = synthetic.tree_digest(self.workspace)
        status, body = move([-1, 26])
        self.assertEqual(status, 400, body)
        self.assertEqual(synthetic.tree_digest(self.workspace), before)

        # A water cell saves as diagnosed work in progress.
        status, body = move([20, 20])
        self.assertEqual(status, 200, body)
        codes = {item["code"] for item in editor.workspace_state()["diagnostics"]}
        self.assertIn("unreachable_landmark", codes)

    @covers_requirement("map-editor-geography::continental-authored-inputs-have-direct-and-explicit-editing-controls")
    @covers_requirement(
        "wilderness-terrain::"
        "the-physical-ridge-is-a-continuous-forked-barrier"
    )
    def test_ridge_route_points_and_zero_passes_round_trip(self):
        editor = self.start()
        stem = {"kind": "ridge_route", "route": "stem"}
        west = {"kind": "ridge_route", "route": "west"}
        east = {"kind": "ridge_route", "route": "east"}
        before = synthetic.tree_digest(self.workspace)
        status, body = self.send(editor, "move_control_point", CONTINENT,
                                 {"feature": stem, "index": 1, "point": [24, 12]})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(before), {CONTINENT})
        self.assertEqual(
            editor.workspace_state()["world"]["continent"]["ridge_routes"]["stem"][1],
            [24, 12],
        )
        # Moving either crotch point updates all three shared points at once.
        status, body = self.send(editor, "move_control_point", CONTINENT,
                                 {"feature": west, "index": 0, "point": [26, 30]})
        self.assertEqual(status, 200, body)
        routes = editor.workspace_state()["world"]["continent"]["ridge_routes"]
        self.assertEqual(routes["stem"][-1], [26, 30])
        self.assertEqual(routes["west"][0], [26, 30])
        self.assertEqual(routes["east"][0], [26, 30])
        # Shared-point deletion and detaching insertions are refused with no write.
        protected = synthetic.tree_digest(self.workspace)
        for name, arguments in (
            ("remove_control_point", {"feature": stem, "index": 3}),
            ("remove_control_point", {"feature": west, "index": 0}),
            ("insert_control_point", {"feature": west, "index": 0, "point": [27, 31]}),
            ("insert_control_point", {"feature": stem, "index": 4, "point": [27, 31]}),
        ):
            status, body = self.send(editor, name, CONTINENT, arguments)
            self.assertEqual(status, 409, (name, body))
        self.assertEqual(synthetic.tree_digest(self.workspace), protected)
        # The pass list may be empty and round-trips to empty.
        self.assertEqual(self.send(editor, "add_ridge_pass", CONTINENT, {"y_min": 20, "y_max": 22})[0], 200)
        self.assertEqual(self.send(editor, "remove_ridge_pass", CONTINENT, {"index": 0})[0], 200)
        self.assertEqual(editor.workspace_state()["world"]["continent"]["ridge"]["passes"], [])
        # A retired periodic parameter is refused with no write.
        retired = synthetic.tree_digest(self.workspace)
        status, body = self.send(editor, "set_terrain_parameter", CONTINENT, {"field": "ridge.base_x", "value": 5})
        self.assertEqual(status, 400, body)
        self.assertEqual(synthetic.tree_digest(self.workspace), retired)

    @covers_requirement("map-editor-geography::continental-authored-inputs-have-direct-and-explicit-editing-controls")
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

    @covers_requirement("map-editor-geography::continental-authored-inputs-have-direct-and-explicit-editing-controls")
    def test_footprint_writes_only_the_settlement_and_binding_is_gone(self):
        editor = self.start()
        before = synthetic.tree_digest(self.workspace)
        status, _ = self.send(editor, "set_footprint_cell", SETTLEMENT,
                              {"settlement_id": synthetic.SETTLEMENT_ID, "cell": [6, 5], "filled": True})
        self.assertEqual(status, 200)
        # The removed command is unknown and writes nothing.
        status, _ = self.send(editor, "set_binding", SETTLEMENT,
                              {"settlement_id": synthetic.SETTLEMENT_ID, "anchor_cell": [6, 5], "local_anchor_m": [0, 0]})
        self.assertEqual(status, 404)
        self.assertEqual(self.changed(before), {SETTLEMENT})
        settlement = editor.workspace_state()["world"]["settlements"][0]
        self.assertEqual(settlement["footprint"]["cells"], [[5, 5], [6, 5]])
        # Growth to the east keeps the origin, so the offset stays (0, 0).
        self.assertEqual(settlement["footprint"]["offset"], [0, 0])
        self.assertEqual(settlement["footprint"]["shape"], ["##"])
        self.assertNotIn("binding", settlement)
        self.assertEqual(settlement["world_frame"], {"anchor_cell": [5, 5], "local_anchor_m": [0, 0]})

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
