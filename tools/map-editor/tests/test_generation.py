"""Explicit partition jobs: admission, exclusion, cancellation and guarded publication.

Every job runs the real generation child process on a small synthetic
continent (40 one-kilometre cells). A test-only stage hook blocks the job
thread at a named point (after the child started, or after it answered and
before publication) so a cancellation, an external replacement or a write
pause lands deterministically. Assertions read the artifact bytes on disk,
the source files and the service's state.
"""

from __future__ import annotations

import http.client
import json
import threading
import time
from pathlib import Path

import pytest

import synthetic_workspace as fixture
from conftest import LiveServer, free_port, make_config
from editor_client import Editor, sha

from elosern_map_core import discover_source_documents, load_authoring_world
from elosern_map_core.partition import generate_partition, partition_input, world_snapshot
from elosern_map_editor.commands import HANDLERS, CommandError
from elosern_map_editor.writer import REPLACE, Effect

ARTIFACT = "world/maps/data/district_partition.json"
DISTRICTS = "content/maps/districts.yaml"
CONTINENT = "content/maps/continent.yaml"
INTERIOR = f"content/maps/interiors/{fixture.INTERIOR_ID}.yaml"
TERMINAL = {"succeeded", "cancelled", "failed"}


class Gate:
    """Blocks the job thread at one hook stage until released."""

    def __init__(self, stage: str) -> None:
        self.stage = stage
        self.reached = threading.Event()
        self.release = threading.Event()

    def __call__(self, stage: str) -> None:
        if stage == self.stage:
            self.reached.set()
            assert self.release.wait(30), "the test never released the job"

    def wait(self) -> None:
        assert self.reached.wait(30), f"the job never reached {self.stage}"


@pytest.fixture
def partitionable(tmp_path: Path) -> Path:
    return fixture.write_partitionable_workspace(tmp_path / "workspace")


def expected_artifact(root: Path) -> str:
    """The core's own generation over the same files, computed independently."""

    world = load_authoring_world(discover_source_documents(root))
    return generate_partition(partition_input(world_snapshot(world)))


def settle(editor: Editor, timeout: float = 30) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = editor.state()["partition_job"]
        if job["state"] in TERMINAL:
            return job
        time.sleep(0.02)
    raise AssertionError("the partition job did not finish")


def rename_district(editor: Editor) -> tuple[int, dict]:
    state = editor.state()
    expected = next(row["fingerprint"] for row in state["documents"] if row["relative_path"] == DISTRICTS)
    arguments = {"district_id": "synthetic_district", "field": "district_name_zh", "value": "改名區"}
    return editor.raw("set_district_field", editor.envelope(DISTRICTS, expected, arguments))


def write_sentinel(root: Path) -> bytes:
    path = root / ARTIFACT
    path.parent.mkdir(parents=True, exist_ok=True)
    data = b'{"sentinel": "prior artifact"}\n'
    path.write_bytes(data)
    return data


def _external_rename(root: Path) -> None:
    data = fixture.partitionable_districts_data()
    data["districts"]["synthetic_district"]["district_name_zh"] = "外部改名"
    (root / DISTRICTS).write_text(fixture.yaml_text(data), encoding="utf-8")


# -- success ------------------------------------------------------------------
def test_explicit_job_publishes_the_core_output_atomically(partitionable):
    editor = Editor(partitionable)
    assert editor.state()["partition_status"]["status"] == "unavailable"
    # A layout edit before the job: its history must survive the publication.
    assert editor.move("front", 2, 3)[0] == 200
    status, body = editor.partition("generate")
    assert status == 200 and body["job"]["state"] in {"generating", "publishing", "succeeded"}
    job = settle(editor)
    assert job["state"] == "succeeded", job
    published = (partitionable / ARTIFACT).read_text(encoding="utf-8")
    assert published == expected_artifact(partitionable)
    assert job["published_fingerprint"] == sha(partitionable / ARTIFACT)
    state = editor.state()
    assert state["partition_status"]["status"] == "current"
    assert state["partition_status"]["game_ready"] is True
    assert state["partition_status"]["artifact_fingerprint"] == job["published_fingerprint"]
    assert state["history"]["undo"] is not None
    assert state["external_change"]["sequence"] == 0
    assert [p.name for p in (partitionable / ARTIFACT).parent.iterdir()] == ["district_partition.json"]
    # A watcher reconciliation of the artifact's own change is no external
    # source change: the history stays.
    editor.follow()
    state = editor.state()
    assert state["external_change"]["sequence"] == 0 and state["history"]["undo"] is not None
    outlines = editor.client.get("/api/partition/outlines").json()
    assert outlines["artifact_fingerprint"] == job["published_fingerprint"]
    assert set(outlines["outlines"]) == set(json.loads(published)["outlines"])


def test_a_saved_relevant_edit_makes_the_output_stale_until_regenerated(partitionable):
    editor = Editor(partitionable)
    editor.partition("generate")
    assert settle(editor)["state"] == "succeeded"
    before = (partitionable / ARTIFACT).read_bytes()
    assert rename_district(editor)[0] == 200
    state = editor.state()
    # No automatic regeneration: the old output stays, labelled older-input.
    assert (partitionable / ARTIFACT).read_bytes() == before
    assert state["partition_job"]["state"] == "succeeded"
    assert state["partition_status"]["status"] == "stale"
    assert state["partition_status"]["game_ready"] is False
    assert state["partition_status"]["input_signature"] != state["partition_status"]["expected_signature"]
    assert any(item["code"] == "stale_partition" for item in state["diagnostics"])
    editor.partition("generate")
    assert settle(editor)["state"] == "succeeded"
    assert editor.state()["partition_status"]["status"] == "current"


# -- admission and exclusion ------------------------------------------------------
def test_a_second_job_is_rejected_and_world_commands_wait(partitionable):
    gate = Gate("spawned")
    editor = Editor(partitionable, partition_hook=gate)
    # A world edit before the job leaves an undo entry on a world document.
    assert rename_district(editor)[0] == 200
    sources = fixture.tree_digest(partitionable)
    history = editor.state()["history"]
    assert editor.partition("generate")[0] == 200
    gate.wait()
    status, body = editor.partition("generate")
    assert status == 409 and body["error"]["code"] == "job_running"
    for name in sorted(HANDLERS):
        status, body = editor.raw(name, editor.envelope(CONTINENT, "absent", {}))
        assert status == 423, name
        assert body["error"]["reason"] == "partition_generating", name
    status, body = editor.undo()
    assert status == 423 and body["error"]["reason"] == "partition_generating"
    assert editor.state()["history"] == history
    assert fixture.tree_digest(partitionable) == sources
    # Layouts cannot change a generation input: they stay admitted.
    assert editor.move("front", 4, 1)[0] == 200
    # The authoritative check sits at the single publication point too.
    with pytest.raises(CommandError) as caught:
        editor.service.apply_effect(
            Effect(REPLACE, DISTRICTS, "x"), None, command="probe", segment="segment-a"
        )
    assert caught.value.details["reason"] == "partition_generating"
    gate.release.set()
    assert settle(editor)["state"] == "succeeded"
    assert rename_district(editor)[0] == 200


def test_admission_requires_a_current_snapshot_of_the_partition_sources(partitionable):
    editor = Editor(partitionable)
    _external_rename(partitionable)  # not reread yet (no watcher here)
    status, body = editor.partition("generate")
    assert status == 409 and body["error"]["code"] == "stale_snapshot"
    assert editor.state()["partition_job"]["state"] == "idle"
    stale = {"session_generation": editor.generation, "snapshot_revision": -1}
    assert editor.partition("generate", stale)[1]["error"]["code"] == "stale_snapshot"
    assert editor.partition("generate", {"session_generation": "other", "snapshot_revision": 0})[0] == 409
    assert editor.partition("generate", {"session_generation": editor.generation})[0] == 400


# -- cancellation and failure --------------------------------------------------
def test_cancel_keeps_the_prior_artifact_and_admits_writes_again(partitionable):
    prior = write_sentinel(partitionable)
    gate = Gate("spawned")
    editor = Editor(partitionable, partition_hook=gate)
    editor.partition("generate")
    gate.wait()
    status, body = editor.partition("cancel")
    assert status == 200 and body["job"]["state"] == "cancelled"
    gate.release.set()
    job = settle(editor)
    assert job["state"] == "cancelled"
    assert (partitionable / ARTIFACT).read_bytes() == prior
    status, body = editor.partition("cancel")
    assert status == 409 and body["error"]["code"] == "job_not_running"
    assert body["error"]["job"]["state"] == "cancelled"
    assert rename_district(editor)[0] == 200


def test_a_failed_generation_keeps_the_prior_artifact(workspace):
    # The default synthetic world leaves a walkable component unseeded.
    prior = write_sentinel(workspace)
    editor = Editor(workspace)
    editor.partition("generate")
    job = settle(editor)
    assert job["state"] == "failed" and job["reason"] == "generation_failed"
    assert any("unseeded walkable component" in line for line in job["problems"])
    assert (workspace / ARTIFACT).read_bytes() == prior
    assert editor.state()["partition_status"]["game_ready"] is False


def test_a_timed_out_generation_fails_and_keeps_the_prior_artifact(partitionable):
    prior = write_sentinel(partitionable)
    editor = Editor(partitionable, partition_timeout_seconds=0.001)
    editor.partition("generate")
    job = settle(editor)
    assert job["state"] == "failed" and job["reason"] == "timeout"
    assert (partitionable / ARTIFACT).read_bytes() == prior


def test_cancel_after_publication_reports_completion(partitionable):
    editor = Editor(partitionable)
    editor.partition("generate")
    assert settle(editor)["state"] == "succeeded"
    published = (partitionable / ARTIFACT).read_bytes()
    status, body = editor.partition("cancel")
    assert status == 409 and body["error"]["job"]["state"] == "succeeded"
    assert (partitionable / ARTIFACT).read_bytes() == published


def test_cancel_before_publication_wins_and_cancel_during_publication_does_not(partitionable):
    prior = write_sentinel(partitionable)
    gate = Gate("generated")
    editor = Editor(partitionable, partition_hook=gate)
    editor.partition("generate")
    gate.wait()  # the child answered; publication has not started
    assert editor.partition("cancel")[0] == 200
    gate.release.set()
    assert settle(editor)["state"] == "cancelled"
    assert (partitionable / ARTIFACT).read_bytes() == prior

    seen: list[dict] = []
    holder: dict = {}

    def fault(stage: str) -> None:
        if stage == "before_publish" and holder["service"].partitions.describe()["state"] == "publishing":
            try:
                holder["service"]._cancel_partition()
            except Exception as error:  # the JobRejected answer
                seen.append({"code": error.code, **error.details})

    racing = Editor(partitionable, fault=fault)
    holder["service"] = racing.service
    racing.partition("generate")
    assert settle(racing)["state"] == "succeeded"
    assert seen and seen[0]["code"] == "job_not_running" and seen[0]["job"]["state"] == "publishing"
    assert (partitionable / ARTIFACT).read_text(encoding="utf-8") == expected_artifact(partitionable)


# -- invalidation and the publication recheck -----------------------------------
def test_an_external_replace_during_generation_prevents_publication(partitionable):
    prior = write_sentinel(partitionable)
    gate = Gate("generated")
    editor = Editor(partitionable, partition_hook=gate)
    editor.partition("generate")
    gate.wait()
    # No watcher and no reread: only the publication recheck can see it.
    _external_rename(partitionable)
    gate.release.set()
    job = settle(editor)
    assert job["state"] == "failed" and job["reason"] == "inputs_changed"
    assert (partitionable / ARTIFACT).read_bytes() == prior


def test_followed_source_change_invalidates_the_running_job(partitionable):
    prior = write_sentinel(partitionable)
    gate = Gate("spawned")
    editor = Editor(partitionable, partition_hook=gate)
    editor.partition("generate")
    gate.wait()
    _external_rename(partitionable)
    editor.follow()
    job = editor.state()["partition_job"]
    assert job["state"] == "failed" and job["reason"] == "inputs_changed"
    gate.release.set()
    assert settle(editor)["state"] == "failed"
    assert (partitionable / ARTIFACT).read_bytes() == prior


def test_an_unrelated_followed_change_keeps_the_job(partitionable):
    gate = Gate("spawned")
    editor = Editor(partitionable, partition_hook=gate)
    editor.partition("generate")
    gate.wait()
    data = fixture.interior_data()
    data["rooms"]["front"]["name_zh"] = "外部改名"
    (partitionable / INTERIOR).write_text(fixture.yaml_text(data), encoding="utf-8")
    editor.follow()
    assert editor.state()["partition_job"]["state"] == "generating"
    gate.release.set()
    assert settle(editor)["state"] == "succeeded"


def test_publication_is_refused_while_the_preview_is_stale(partitionable):
    prior = write_sentinel(partitionable)
    gate = Gate("generated")
    editor = Editor(partitionable, partition_hook=gate, settle_seconds=0)
    editor.partition("generate")
    gate.wait()
    (partitionable / INTERIOR).write_text("rooms: [unclosed\n", encoding="utf-8")
    editor.follow()
    assert editor.state()["preview_state"] == "stale"
    gate.release.set()
    job = settle(editor)
    assert job["state"] == "failed" and job["reason"] == "stale_preview"
    assert (partitionable / ARTIFACT).read_bytes() == prior


def test_publication_is_refused_while_writes_are_paused(partitionable):
    prior = write_sentinel(partitionable)
    gate = Gate("generated")
    armed = {"on": False}

    def fault(stage: str) -> None:
        if armed["on"] and stage == "flush_directory":
            armed["on"] = False
            raise OSError(5, "injected flush failure")

    editor = Editor(partitionable, partition_hook=gate, fault=fault)
    editor.partition("generate")
    gate.wait()
    armed["on"] = True
    status, body = editor.move("front", 7, 7)  # a layout edit is admitted
    assert status == 500 and body["error"]["code"] == "save_uncertain"
    assert editor.state()["write_pause"]["paused"] is True
    gate.release.set()
    job = settle(editor)
    assert job["state"] == "failed" and job["reason"] == "write_paused"
    assert (partitionable / ARTIFACT).read_bytes() == prior


# -- responsiveness ---------------------------------------------------------------
def test_requests_stay_responsive_while_a_job_runs(partitionable):
    gate = Gate("spawned")
    port = free_port()
    with LiveServer(make_config(partitionable, port=port), partition_hook=gate) as server:
        def call(method: str, path: str, body: dict | None = None) -> tuple[int, dict, float]:
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            headers = {"Host": f"127.0.0.1:{port}"}
            if method == "POST":
                session = call("GET", "/api/session")[1]
                headers.update({"Origin": f"http://127.0.0.1:{port}", "X-Map-Editor-Token": session["token"],
                                "Content-Type": "application/json"})
            started = time.monotonic()
            connection.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
            response = connection.getresponse()
            payload = json.loads(response.read() or b"{}")
            connection.close()
            return response.status, payload, time.monotonic() - started

        state = call("GET", "/api/workspace")[1]
        body = {"session_generation": state["session_generation"], "snapshot_revision": state["snapshot_revision"]}
        assert call("POST", "/api/partition/generate", body)[0] == 200
        gate.wait()
        for _ in range(5):
            status, state, elapsed = call("GET", "/api/workspace")
            assert status == 200 and state["partition_job"]["state"] == "generating"
            assert elapsed < 2.0
        status, payload, elapsed = call("POST", "/api/partition/cancel",
                                        {"session_generation": state["session_generation"]})
        assert status == 200 and payload["job"]["state"] == "cancelled" and elapsed < 2.0
        gate.release.set()
        assert server.service.partitions.describe()["state"] == "cancelled"
        assert not (partitionable / ARTIFACT).exists()


# -- unexpected errors never leave a job running ---------------------------------
def test_an_unexpected_publication_error_ends_the_job_and_admits_writes(partitionable, monkeypatch):
    prior = write_sentinel(partitionable)
    editor = Editor(partitionable)

    def broken(*args, **kwargs):
        raise RuntimeError("injected recheck failure")

    monkeypatch.setattr(editor.service, "_publication_refusal", broken)
    editor.partition("generate")
    job = settle(editor)
    assert job["state"] == "failed" and job["reason"] == "internal_error"
    assert any("injected recheck failure" in line for line in job["problems"])
    assert (partitionable / ARTIFACT).read_bytes() == prior
    assert editor.service.partitions.running is False
    assert rename_district(editor)[0] == 200
    assert editor.partition("generate")[0] == 200


def test_an_unexpected_job_thread_error_ends_the_job(partitionable):
    def hook(stage: str) -> None:
        if stage == "generated":
            raise RuntimeError("injected thread failure")

    editor = Editor(partitionable, partition_hook=hook)
    editor.partition("generate")
    job = settle(editor)
    assert job["state"] == "failed" and job["reason"] == "internal_error"
    assert not (partitionable / ARTIFACT).exists()
    assert rename_district(editor)[0] == 200


def test_an_oversized_answer_fails_and_keeps_the_prior_artifact(partitionable):
    prior = write_sentinel(partitionable)
    editor = Editor(partitionable)
    editor.service.partitions.max_output_bytes = 16
    editor.partition("generate")
    job = settle(editor)
    assert job["state"] == "failed" and job["reason"] == "output_too_large"
    assert (partitionable / ARTIFACT).read_bytes() == prior
