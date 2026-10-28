"""The standalone map editor's complete job and deletion lifecycle, without the game.

One real service process per test, started from the editor's own locked
environment (``tools/map-editor``) with a scrubbed environment and no ``PATH``,
against a temporary synthetic workspace. Each test chains the operations of
one session (partition generation, cancellation and input invalidation; the
external-index guard on deletion) and asserts the effects on disk: the prior
artifact and every unrelated file stay byte-identical, nothing else appears in
the workspace (no database or cache file), and the editor's interpreter has no
game framework to import.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import time
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
ARTIFACT = "world/maps/data/district_partition.json"
DISTRICTS = "content/maps/districts.yaml"
INTERIOR = f"content/maps/interiors/{HALL}.yaml"
INDEX = "content/map-reference-context.json"
TERMINAL = {"succeeded", "cancelled", "failed"}

_NO_GAME = """
import importlib.util, json, os, sys
import elosern_map_editor.app, elosern_map_editor.partition_worker, elosern_map_core.partition
print(json.dumps({
  "importable": sorted(n for n in ("evennia", "django", "world", "typeclasses", "server") if importlib.util.find_spec(n)),
  "loaded": sorted(m for m in sys.modules if m.split(".")[0] in ("evennia", "django", "world", "typeclasses", "server")),
  "environment": sorted(k for k in os.environ if k.startswith(("DJANGO_", "EVENNIA", "MUD_"))),
}))
"""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _expected(root: Path) -> str:
    from elosern_map_core import discover_source_documents, load_authoring_world
    from elosern_map_core.partition import generate_partition, partition_input, world_snapshot

    world = load_authoring_world(discover_source_documents(root))
    return generate_partition(partition_input(world_snapshot(world)))


def _room(name: str) -> dict:
    return {"name_zh": name, "desc_zh": f"A synthetic {name}.", "scene_archetype": None, "art_key": None}


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
        self.root = Path(tempfile.mkdtemp(prefix="map-editor-independent-"))
        self.addCleanup(shutil.rmtree, self.root, True)

    def start(self, workspace: Path):
        editor = harness.EditorProcess(workspace)
        editor.__enter__()
        self.addCleanup(editor.__exit__, None, None, None)
        return editor

    def assert_no_game(self) -> None:
        result = harness.run_editor_python(_NO_GAME)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"importable": [], "loaded": [], "environment": []})

    def changed(self, workspace: Path, before: dict) -> set[str]:
        now = synthetic.tree_digest(workspace)
        return {path for path in set(now) | set(before) if now.get(path) != before.get(path)}


class IndependentGenerationLifecycleTests(_EditorCase):
    def job(self, editor, states, timeout: float = 90) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = editor.workspace_state()["partition_job"]
            if job["state"] in states:
                return job
            time.sleep(0.02)
        self.fail(f"the partition job never reached {sorted(states)}")

    @covers_requirement("map-editor-generation::explicit-generation-isolates-inputs-and-guards-publication")
    def test_cancel_and_input_change_keep_the_prior_artifact_until_a_current_run_publishes(self):
        workspace = synthetic.write_slow_partition_workspace(self.root / "workspace")
        artifact = workspace / ARTIFACT
        artifact.parent.mkdir(parents=True, exist_ok=True)
        prior = b'{"sentinel": "prior artifact"}\n'
        artifact.write_bytes(prior)
        before = synthetic.tree_digest(workspace)
        editor = self.start(workspace)

        # 1. A cancelled run publishes nothing.
        self.assertEqual(harness.partition(editor, "generate")[0], 200)
        self.job(editor, {"generating"}, 30)
        self.assertEqual(harness.partition(editor, "cancel")[0], 200)
        self.assertEqual(self.job(editor, TERMINAL)["state"], "cancelled")
        self.assertEqual(artifact.read_bytes(), prior)
        self.assertEqual(self.changed(workspace, before), set())

        # 2. An external input change during a run invalidates its result.
        self.assertEqual(harness.partition(editor, "generate")[0], 200)
        self.job(editor, {"generating"}, 30)
        data = synthetic.partitionable_districts_data()
        data["districts"]["synthetic_district"]["district_name_zh"] = "外部改名"
        (workspace / DISTRICTS).write_text(synthetic.yaml_text(data), encoding="utf-8")
        job = self.job(editor, TERMINAL)
        self.assertEqual((job["state"], job["reason"]), ("failed", "inputs_changed"))
        self.assertEqual(artifact.read_bytes(), prior)
        self.assertNotEqual(editor.workspace_state()["partition_status"]["status"], "current")
        self.assertEqual(self.changed(workspace, before), {DISTRICTS})

        # 3. A run over the adopted inputs publishes the core's own output.
        deadline = time.monotonic() + 20
        while editor.workspace_state()["external_change"]["sequence"] < 1:
            self.assertLess(time.monotonic(), deadline, "the external change was not adopted")
            time.sleep(0.05)
        self.assertEqual(harness.partition(editor, "generate")[0], 200)
        self.assertEqual(self.job(editor, TERMINAL)["state"], "succeeded")
        self.assertEqual(artifact.read_text(encoding="utf-8"), _expected(workspace))
        self.assertEqual(editor.workspace_state()["partition_status"]["status"], "current")
        # Only the externally edited document and the artifact changed: no
        # database, cache or scratch file appeared in the workspace.
        self.assertEqual(self.changed(workspace, before), {DISTRICTS, ARTIFACT})
        self.assert_no_game()


class IndependentDeletionGuardTests(_EditorCase):
    def send(self, editor, workspace: Path, name: str, document: str, arguments: dict):
        path = workspace / document
        return harness.command(editor, name, document_id=document,
                               expected=_sha(path) if path.exists() else "absent", arguments=arguments)

    @covers_requirement(
        "map-editor-relationships::deletion-requires-established-absence-of-incoming-static-references"
    )
    def test_deletion_needs_a_current_index_and_refuses_an_externally_referenced_room(self):
        workspace = synthetic.write_workspace(self.root / "workspace")
        data = synthetic.interior_data()
        data["rooms"].update(side=_room("side"), spare=_room("spare"), attic=_room("attic"))
        (workspace / INTERIOR).write_text(synthetic.yaml_text(data), encoding="utf-8")
        synthetic.write_reference_context(workspace, incoming={f"interior_room:{HALL}:side": [{
            "source": "place:side", "source_domain": "places", "source_file": "external/declarations.txt",
            "target": {"domain": "interior_room", "map_id": HALL, "object_id": "side", "cell": None}}]})
        editor = self.start(workspace)
        self.assertTrue(editor.workspace_state()["external_context_status"]["current"])

        # A current index naming the room refuses its deletion; nothing is written.
        before = synthetic.tree_digest(workspace)
        status, body = self.send(editor, workspace, "delete_room", INTERIOR, {"interior_id": HALL, "room_id": "side"})
        self.assertEqual((status, body["error"]["code"]), (409, "deletion_refused"), body)
        self.assertEqual(self.changed(workspace, before), set())

        # A room the current index does not name is deleted, without cascade.
        status, body = self.send(editor, workspace, "delete_room", INTERIOR, {"interior_id": HALL, "room_id": "spare"})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(workspace, before), {INTERIOR})
        rooms = YAML(typ="safe", pure=True).load((workspace / INTERIOR).read_text(encoding="utf-8"))["rooms"]
        self.assertEqual(set(rooms), {"front", "back", "side", "attic"})

        # Without the index, absence of external references cannot be
        # established: every deletion is refused, while edits still save.
        (workspace / INDEX).unlink()
        deadline = time.monotonic() + 20
        while editor.workspace_state()["external_context_status"]["current"]:
            self.assertLess(time.monotonic(), deadline, "the missing index was not noticed")
            time.sleep(0.05)
        before = synthetic.tree_digest(workspace)
        status, body = self.send(editor, workspace, "delete_room", INTERIOR, {"interior_id": HALL, "room_id": "attic"})
        self.assertEqual((status, body["error"]["code"]), (409, "deletion_refused"), body)
        self.assertIn("unavailable", body["error"].values())
        self.assertEqual(self.changed(workspace, before), set())
        status, body = self.send(editor, workspace, "set_room_fields", INTERIOR, {
            "interior_id": HALL, "room_id": "attic", "fields": {"name_zh": "閣樓", "desc_zh": "A synthetic attic."}})
        self.assertEqual(status, 200, body)
        self.assertEqual(self.changed(workspace, before), {INTERIOR})
        self.assert_no_game()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
