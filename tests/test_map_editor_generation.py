"""Explicit map-editor partition jobs, against the real service process.

The service runs as a child process from its own locked environment (with the
core generation extra) with a scrubbed environment and no ``PATH``, against a
temporary synthetic workspace. Its jobs run the real generation in a further
child process. Every assertion inspects the artifact bytes on disk, the
source files or the service's state:

- an explicit job on unchanged inputs publishes exactly the core's output for
  those files and the output becomes current and game-ready;
- a saved relevant edit makes the old output stale (older-input revision,
  readiness withheld) without any automatic regeneration;
- while an observed worker is stopped, requests stay responsive, a second job
  and every world-data command are refused, and a cancel keeps the last artifact;
- an external replacement of a partition source during the job prevents its
  publication as current and keeps the last artifact.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import signal
import subprocess
import tempfile
import time
import unittest
from contextlib import contextmanager
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

ARTIFACT = "world/maps/data/district_partition.json"
DISTRICTS = "content/maps/districts.yaml"
LOCATIONS = "content/maps/locations.yaml"
TERMINAL = {"succeeded", "cancelled", "failed"}


def _partition_worker(editor) -> tuple[int, str] | None:
    """Find this service's worker through the OS, on Linux and macOS."""
    assert editor.process is not None
    listing = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,stat=,command="],
        capture_output=True, text=True, check=True, timeout=5,
    )
    for line in listing.stdout.splitlines():
        columns = line.split(None, 3)
        if len(columns) != 4:
            continue
        pid, parent, state, command = columns
        if int(parent) == editor.process.pid and "-m elosern_map_editor.partition_worker" in command:
            return int(pid), state
    return None


@contextmanager
def held_partition_job(editor, timeout: float = 30):
    """Hold the real worker at an OS-observed stop, leaving the service live.

    Acquiring the worker still requires observing it before it exits. Once
    stopped, browsing, cancellation and file following need no generation-time
    margin. No service hook or synthetic worker replaces real generation.
    """
    deadline = time.monotonic() + timeout
    worker = None
    try:
        while time.monotonic() < deadline:
            worker = _partition_worker(editor)
            if worker is not None:
                os.kill(worker[0], signal.SIGSTOP)
                break
            job = editor.workspace_state()["partition_job"]
            if job["state"] in TERMINAL:
                raise AssertionError(f"the partition job ended before its worker was observed: {job}")
            time.sleep(0.01)
        else:
            raise AssertionError("the partition worker did not appear")

        while time.monotonic() < deadline:
            observed = _partition_worker(editor)
            if observed is None or observed[0] != worker[0]:
                raise AssertionError("the partition worker exited before its stop was observed")
            if "T" in observed[1]:
                job = editor.workspace_state()["partition_job"]
                if job["state"] != "generating" or not job["job_id"]:
                    raise AssertionError(f"the stopped worker has no generating job: {job}")
                yield job
                return
            time.sleep(0.01)
        raise AssertionError("the partition worker did not stop")
    finally:
        # Entry assertions can fail after SIGSTOP too. Re-identify the child
        # before resuming; a successful cancel/invalidation normally killed it.
        if worker is not None:
            observed = _partition_worker(editor)
            if observed is not None and observed[0] == worker[0]:
                try:
                    os.kill(worker[0], signal.SIGCONT)
                except ProcessLookupError:
                    pass  # The service reaped the worker after the OS read.


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _expected(root: Path) -> str:
    from elosern_map_core import discover_source_documents, load_authoring_world
    from elosern_map_core.partition import generate_partition, partition_input, world_snapshot

    world = load_authoring_world(discover_source_documents(root))
    return generate_partition(partition_input(world_snapshot(world)))


def _sentinel(root: Path) -> bytes:
    path = root / ARTIFACT
    path.parent.mkdir(parents=True, exist_ok=True)
    data = b'{"sentinel": "prior artifact"}\n'
    path.write_bytes(data)
    return data


class PartitionJobProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            harness.editor_python()
        except harness.EditorUnavailable as error:
            if harness.skip_allowed():
                raise unittest.SkipTest(str(error)) from error
            raise

    def setUp(self):
        root = Path(tempfile.mkdtemp(prefix="map-editor-generation-"))
        self.addCleanup(shutil.rmtree, root, True)
        self.root = root

    def start(self, workspace: Path):
        editor = harness.EditorProcess(workspace)
        editor.__enter__()
        self.addCleanup(editor.__exit__, None, None, None)
        return editor

    def settle(self, editor, timeout: float = 90) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = editor.workspace_state()["partition_job"]
            if job["state"] in TERMINAL:
                return job
            time.sleep(0.05)
        self.fail("the partition job did not finish")

    def location_edit(self, editor, value: str):
        state = editor.workspace_state()
        expected = next(row["fingerprint"] for row in state["documents"] if row["relative_path"] == LOCATIONS)
        return harness.command(
            editor, "set_location_field", document_id=LOCATIONS, expected=expected,
            arguments={"location_id": synthetic.LOCATION_ID, "field": "display_name_zh", "value": value},
        )

    @covers_requirement("map-editor-generation::explicit-generation-isolates-inputs-and-guards-publication")
    @covers_requirement("map-editor-generation::partition-status-distinguishes-source-persistence-from-output-freshness")
    def test_unchanged_input_publishes_the_core_output_and_an_edit_only_marks_it_stale(self):
        workspace = synthetic.write_partitionable_workspace(self.root / "workspace")
        editor = self.start(workspace)
        status, body = harness.partition(editor, "generate")
        self.assertEqual(status, 200, body)
        job = self.settle(editor)
        self.assertEqual(job["state"], "succeeded", job)
        self.assertEqual((workspace / ARTIFACT).read_text(encoding="utf-8"), _expected(workspace))
        state = editor.workspace_state()
        self.assertEqual(state["partition_status"]["status"], "current")
        self.assertTrue(state["partition_status"]["game_ready"])

        published = (workspace / ARTIFACT).read_bytes()
        status, body = self.location_edit(editor, "改名城")
        self.assertEqual(status, 200, body)
        state = editor.workspace_state()
        self.assertEqual((workspace / ARTIFACT).read_bytes(), published)
        self.assertEqual(state["partition_job"]["state"], "succeeded")
        self.assertEqual(state["partition_status"]["status"], "stale")
        self.assertFalse(state["partition_status"]["game_ready"])
        self.assertNotEqual(
            state["partition_status"]["input_signature"], state["partition_status"]["expected_signature"]
        )

    @covers_requirement("map-editor-generation::explicit-generation-isolates-inputs-and-guards-publication")
    def test_browsing_then_cancelling_keeps_the_last_output_and_admits_nothing_else(self):
        workspace = synthetic.write_slow_partition_workspace(self.root / "workspace")
        prior = _sentinel(workspace)
        editor = self.start(workspace)
        sources = synthetic.tree_digest(workspace)
        self.assertEqual(harness.partition(editor, "generate")[0], 200)
        with held_partition_job(editor) as generating:
            for _ in range(5):
                started = time.monotonic()
                state = editor.workspace_state()
                self.assertLess(time.monotonic() - started, 2.0)
                self.assertEqual(state["partition_job"]["state"], "generating")
                self.assertEqual(state["partition_job"]["job_id"], generating["job_id"])
            status, body = harness.partition(editor, "generate")
            self.assertEqual((status, body["error"]["code"]), (409, "job_running"))
            status, body = self.location_edit(editor, "改名城")
            self.assertEqual(status, 423, body)
            self.assertEqual(body["error"]["reason"], "partition_generating")
            status, body = harness.partition(editor, "cancel")
            self.assertEqual(status, 200, body)
            job = self.settle(editor)
            self.assertEqual(job["state"], "cancelled")
            self.assertEqual(job["job_id"], generating["job_id"])
        self.assertEqual((workspace / ARTIFACT).read_bytes(), prior)
        self.assertEqual(synthetic.tree_digest(workspace), sources)
        # The world is writable again once the job ended.
        self.assertEqual(self.location_edit(editor, "改名城")[0], 200)

    @covers_requirement("map-editor-generation::explicit-generation-isolates-inputs-and-guards-publication")
    def test_an_external_source_replace_during_generation_prevents_current_publication(self):
        workspace = synthetic.write_slow_partition_workspace(self.root / "workspace")
        prior = _sentinel(workspace)
        editor = self.start(workspace)
        self.assertEqual(harness.partition(editor, "generate")[0], 200)
        with held_partition_job(editor) as generating:
            data = synthetic.partitionable_districts_data()
            data["districts"]["synthetic_district"]["district_name_zh"] = "外部改名"
            (workspace / DISTRICTS).write_text(synthetic.yaml_text(data), encoding="utf-8")
            job = self.settle(editor)
            self.assertEqual(job["state"], "failed", job)
            self.assertEqual(job["reason"], "inputs_changed")
            self.assertEqual(job["job_id"], generating["job_id"])
        self.assertEqual((workspace / ARTIFACT).read_bytes(), prior)
        self.assertNotEqual(editor.workspace_state()["partition_status"]["status"], "current")


if __name__ == "__main__":
    unittest.main()
