"""The capture snapshot adapter, executed in the editor's own independent environment.

Every test starts the adapter through the editor's locked environment (its own
``uv`` project, scrubbed environment, no game framework importable) against a
temporary synthetic workspace. The assertions read the returned payload, the
typed refusal and the workspace bytes, so a loader that forwards to a helper
without loading anything cannot pass: the synthetic geometry, the single read
per discovered document, the scene-metre partition outlines and the unchanged
source/layout/artifact/index bytes are all independent expectations.
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

ARTIFACT = "world/maps/data/district_partition.json"
INDEX = "content/map-reference-context.json"
SETTLEMENT = f"content/maps/settlements/{synthetic.SETTLEMENT_ID}.yaml"
DISTRICTS = "content/maps/districts.yaml"
LAYOUT = f"content/map-editor-layouts/{synthetic.INTERIOR_ID}.yaml"

_PROBE = '''
import json
import sys

from elosern_map_editor import capture_snapshot
from elosern_map_editor.confinement import ConfinedWorkspace

root = {root}
view = {view}
map_id = {map_id}
hidden = {hidden}

calls = []
original = ConfinedWorkspace.read_document


def counted(self, relative_path, limit):
    calls.append(relative_path)
    return original(self, relative_path, limit)


ConfinedWorkspace.read_document = counted
outcome = {{}}
try:
    outcome["payload"] = capture_snapshot.load_capture_snapshot(
        root, view=view, map_id=map_id, hidden_layers=hidden
    )
except capture_snapshot.CaptureSnapshotError as error:
    outcome["error"] = error.as_dict()
game = sorted(
    name for name in sys.modules
    if name.split(".")[0] in ("evennia", "django", "world", "typeclasses", "server")
)
print(json.dumps({{"calls": calls, "game_modules": game, **outcome}}))
'''


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact(root: Path) -> str:
    """The core's own partition generation over the same files (repo environment)."""

    from elosern_map_core import discover_source_documents, load_authoring_world
    from elosern_map_core.partition import generate_partition, partition_input, world_snapshot

    world = load_authoring_world(discover_source_documents(root))
    return generate_partition(partition_input(world_snapshot(world)))


def _install_partition(root: Path) -> str:
    text = _artifact(root)
    target = root / ARTIFACT
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return text


def _write_layout(root: Path) -> Path:
    path = root / LAYOUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        synthetic.yaml_text(
            {
                "version": 1,
                "kind": "layout",
                "id": synthetic.INTERIOR_ID,
                "positions": {"front": {"x": 0, "y": 0}},
            }
        ),
        encoding="utf-8",
    )
    return path


def _probe(root: Path, *, view: str, map_id: str | None = None, hidden=()) -> dict:
    # Python literals, not JSON: ``None`` is not ``null`` in the probe source.
    code = _PROBE.format(
        root=repr(str(root)),
        view=repr(view),
        map_id=repr(map_id),
        hidden=repr(tuple(hidden)),
    )
    result = harness.run_editor_python(code)
    if result.returncode != 0:
        raise AssertionError(f"the capture probe failed:\n{result.stderr[-4000:]}")
    return json.loads(result.stdout)


class _CaptureCase(unittest.TestCase):
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
        self.root = Path(tempfile.mkdtemp(prefix="map-capture-snapshot-"))
        self.addCleanup(shutil.rmtree, self.root, True)

    def workspace(self) -> Path:
        return synthetic.write_workspace(self.root / "workspace")

    def partitioned(self) -> Path:
        root = synthetic.write_partitionable_workspace(self.root / "workspace")
        _install_partition(root)
        return root

    def assert_refused(self, outcome: dict, code: str) -> dict:
        self.assertNotIn("payload", outcome)
        self.assertIn("error", outcome)
        self.assertEqual(outcome["error"]["code"], code, outcome["error"])
        return outcome["error"]

    def assert_unchanged(self, root: Path, before: dict) -> None:
        self.assertEqual(synthetic.tree_digest(root), before)


class CaptureSnapshotPayloadTests(_CaptureCase):
    def test_the_editor_environment_loads_the_complete_snapshot_with_a_single_read(self):
        root = self.partitioned()
        _write_layout(root)
        before = synthetic.tree_digest(root)

        outcome = _probe(root, view="continent")
        self.assertNotIn("error", outcome, outcome.get("error"))
        self.assertEqual(outcome["game_modules"], [])
        payload = outcome["payload"]
        self.assertEqual(sorted(payload), ["diagnostics", "partition", "world"])

        world = payload["world"]
        self.assertEqual(world["continent"]["frame_cells"], 40)
        preview = world["continent"]["terrain_preview"]
        self.assertEqual(preview["status"], "current")
        self.assertTrue(preview["samples"])
        # Independently known synthetic geometry (not read from the payload).
        locations = {row["id"]: row for row in world["locations"]}
        self.assertEqual(locations[synthetic.LOCATION_ID]["centre_m"], [5500, 5500])
        [settlement] = world["settlements"]
        self.assertEqual(
            {node["id"]: node["world_m"] for node in settlement["nodes"]}["yard"], [5800, 5900]
        )
        roads = {road["id"]: road["length_m"] for road in settlement["roads"]}
        self.assertEqual((roads["gate>yard"], roads["yard>gate"]), (500.0, 700.0))
        # Authored positions survive; the absent one stays absent for fallback.
        rooms = {room["id"]: room for room in world["interiors"][0]["rooms"]}
        self.assertEqual(rooms["front"]["layout_position"], [0, 0])
        self.assertIsNone(rooms["back"]["layout_position"])

        # One read of every discovered document, no document twice.
        calls = outcome["calls"]
        self.assertEqual(len(calls), len(set(calls)), calls)
        for relative_path in [*synthetic.DOCUMENTS, LAYOUT]:
            self.assertIn(relative_path, calls)

        # Partition outlines are continental scene metres, keyed by district.
        outlines = payload["partition"]["outlines"]
        self.assertEqual(set(outlines), {row["id"] for row in world["districts"]})
        coordinates = [value for rings in outlines.values() for ring in rings for value in ring]
        self.assertTrue(coordinates)
        self.assertTrue(all(isinstance(value, int) for value in coordinates))
        self.assertTrue(all(0 <= value <= 40 * 1000 for value in coordinates), coordinates)
        self.assertGreater(max(coordinates), 20 * 1000)
        # A fresh artifact leaves only the advisory reference-context note.
        self.assertEqual(
            [(item["category"], item["code"]) for item in payload["diagnostics"]],
            [("external", "reference_context_missing")],
        )
        self.assert_unchanged(root, before)

    def test_a_later_source_change_is_outside_the_snapshot(self):
        root = self.workspace()
        first = _probe(root, view="settlement", map_id=synthetic.SETTLEMENT_ID)["payload"]
        data = synthetic.settlement_data()
        data["nodes"]["yard"]["key"] = "Renamed yard"
        (root / SETTLEMENT).write_text(synthetic.yaml_text(data), encoding="utf-8")

        later = _probe(root, view="settlement", map_id=synthetic.SETTLEMENT_ID)["payload"]
        first_keys = {node["id"]: node["key"] for node in first["world"]["settlements"][0]["nodes"]}
        later_keys = {node["id"]: node["key"] for node in later["world"]["settlements"][0]["nodes"]}
        self.assertEqual(first_keys["yard"], "Yard")
        self.assertEqual(later_keys["yard"], "Renamed yard")
        self.assertIsNone(first["partition"])

    def test_semantic_work_in_progress_loads_without_a_reference_index(self):
        root = self.workspace()
        settlement = synthetic.settlement_data()
        settlement["nodes"]["lonely"] = {
            "x_m": 900,
            "y_m": 900,
            "prototype_parent": "grid_room",
            "key": "Lonely",
            "desc": "Unreached.",
            "anchor_key": None,
            "typeclass": None,
            "scene_archetype": None,
        }
        (root / SETTLEMENT).write_text(synthetic.yaml_text(settlement), encoding="utf-8")
        districts = synthetic.districts_data()
        districts["districts"]["synthetic_district"]["landmark"]["object_id"] = "lonely"
        (root / DISTRICTS).write_text(synthetic.yaml_text(districts), encoding="utf-8")
        before = synthetic.tree_digest(root)

        outcome = _probe(root, view="settlement", map_id=synthetic.SETTLEMENT_ID)
        self.assertNotIn("error", outcome, outcome.get("error"))
        payload = outcome["payload"]
        codes = {(item["category"], item["code"]) for item in payload["diagnostics"]}
        self.assertIn(("semantic", "unreachable_landmark"), codes)
        self.assertIn(("external", "reference_context_missing"), codes)
        self.assertTrue(payload["world"]["settlements"][0]["nodes"])
        self.assertEqual([item["severity"] for item in payload["diagnostics"] if item["category"] == "external"], ["warning"])
        self.assertFalse((root / INDEX).exists())
        self.assert_unchanged(root, before)

        synthetic.write_reference_context(root)
        (root / "external/declarations.txt").write_text("changed\n", encoding="utf-8")
        stale_digest = synthetic.tree_digest(root)
        stale = _probe(root, view="settlement", map_id=synthetic.SETTLEMENT_ID)["payload"]
        stale_codes = {(item["category"], item["code"]) for item in stale["diagnostics"]}
        self.assertIn(("external", "reference_context_not_current"), stale_codes)
        self.assertIn(("semantic", "unreachable_landmark"), stale_codes)
        self.assertTrue(stale["world"]["settlements"][0]["nodes"])
        self.assert_unchanged(root, stale_digest)


class CaptureSnapshotRefusalTests(_CaptureCase):
    def test_a_malformed_layout_is_refused_and_never_becomes_a_fallback(self):
        root = self.workspace()
        layout = root / LAYOUT
        layout.parent.mkdir(parents=True, exist_ok=True)
        layout.write_text(
            "version: 1\nkind: layout\nid: {id}\npositions:\n  front:\n    x: 0\n    y: 0\n"
            "positions:\n  back:\n    x: 1\n    y: 1\n".format(id=synthetic.INTERIOR_ID),
            encoding="utf-8",
        )
        before = synthetic.tree_digest(root)

        error = self.assert_refused(
            _probe(root, view="interior", map_id=synthetic.INTERIOR_ID), "structure"
        )
        self.assertIn(LAYOUT, json.dumps(error["diagnostics"]))
        self.assertTrue(all(item["category"] == "structure" for item in error["diagnostics"]))
        self.assert_unchanged(root, before)
        self.assertEqual(_sha(layout), before[LAYOUT])

    def test_a_malformed_source_is_refused(self):
        root = self.workspace()
        locations = root / "content/maps/locations.yaml"
        locations.write_text(locations.read_text(encoding="utf-8") + "unexpected_field: 1\n", encoding="utf-8")
        before = synthetic.tree_digest(root)

        error = self.assert_refused(
            _probe(root, view="settlement", map_id=synthetic.SETTLEMENT_ID), "structure"
        )
        self.assertIn("content/maps/locations.yaml", json.dumps(error["diagnostics"]))
        self.assert_unchanged(root, before)

    def test_absent_and_wrong_view_identities_are_refused(self):
        root = self.workspace()
        before = synthetic.tree_digest(root)

        self.assert_refused(
            _probe(root, view="settlement", map_id="absent_map"), "unknown_map"
        )
        self.assert_refused(
            _probe(root, view="interior", map_id=synthetic.SETTLEMENT_ID), "wrong_view"
        )
        self.assert_refused(
            _probe(root, view="settlement", map_id=synthetic.INTERIOR_ID), "wrong_view"
        )
        self.assert_refused(
            _probe(root, view="continent", map_id=synthetic.SETTLEMENT_ID), "invalid_map_id"
        )
        self.assert_unchanged(root, before)


class CaptureSnapshotPartitionTests(_CaptureCase):
    def test_missing_malformed_and_stale_output_is_refused_with_guidance(self):
        root = synthetic.write_partitionable_workspace(self.root / "workspace")

        # 1. Missing: the artifact was never generated.
        before = synthetic.tree_digest(root)
        error = self.assert_refused(_probe(root, view="continent"), "partition_unavailable")
        self.assertEqual(error["reason"], "missing")
        self.assertIn("regenerate_partition.py", error["guidance"])
        self.assertIn("--hide partition", error["guidance"])
        self.assertFalse((root / ARTIFACT).exists())
        self.assert_unchanged(root, before)

        # 2. Malformed body behind valid metadata.
        generated = json.loads(_artifact(root))
        key = generated["districts"][0]
        generated["outlines"][key][0].append(0)
        target = root / ARTIFACT
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(generated), encoding="utf-8")
        before = synthetic.tree_digest(root)
        error = self.assert_refused(_probe(root, view="continent"), "partition_unavailable")
        self.assertEqual(error["reason"], "malformed")
        self.assertIn("--hide partition", error["guidance"])
        self.assert_unchanged(root, before)

        # 3. Stale: generated for the previous map inputs, then a source changed.
        _install_partition(root)
        prior = (root / ARTIFACT).read_bytes()
        districts = synthetic.partitionable_districts_data()
        districts["districts"]["synthetic_district"]["district_name_zh"] = "外部改名"
        (root / DISTRICTS).write_text(synthetic.yaml_text(districts), encoding="utf-8")
        before = synthetic.tree_digest(root)
        error = self.assert_refused(_probe(root, view="continent"), "partition_unavailable")
        self.assertEqual(error["reason"], "stale")
        self.assertEqual((root / ARTIFACT).read_bytes(), prior)
        self.assert_unchanged(root, before)

    def test_hidden_partition_and_other_views_never_need_the_artifact(self):
        root = self.workspace()
        before = synthetic.tree_digest(root)

        hidden = _probe(root, view="continent", hidden=["partition", "partition"])
        self.assertNotIn("error", hidden, hidden.get("error"))
        self.assertIsNone(hidden["payload"]["partition"])
        self.assertEqual(hidden["payload"]["world"]["continent"]["terrain_preview"]["status"], "current")

        for view, map_id in (("settlement", synthetic.SETTLEMENT_ID), ("interior", synthetic.INTERIOR_ID)):
            outcome = _probe(root, view=view, map_id=map_id)
            self.assertNotIn("error", outcome, outcome.get("error"))
            self.assertIsNone(outcome["payload"]["partition"])

        self.assertNotIn(ARTIFACT, hidden["calls"])
        self.assertFalse((root / ARTIFACT).exists())
        self.assertFalse((root / INDEX).exists())
        self.assert_unchanged(root, before)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
