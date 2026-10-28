"""The watch coordinator against a real filesystem and a real server.

Each test runs uvicorn (with the lifespan, so the coordinator watches) on a
loopback port against a temporary synthetic workspace and changes files the
way an external writer does. Assertions poll the service state; the
``following.batches`` counter proves that delayed notifications of the
service's own writes were actually reconciled.
"""

from __future__ import annotations

import http.client
import json
import os
import time
from pathlib import Path

import synthetic_workspace as fixture
from conftest import LiveServer, free_port, make_config

from elosern_map_editor import watching
from elosern_map_editor.watching import watch_plan

LAYOUT = f"content/map-editor-layouts/{fixture.INTERIOR_ID}.yaml"
SETTLEMENT = f"content/maps/settlements/{fixture.SETTLEMENT_ID}.yaml"


def _wait(predicate, message: str, timeout: float = 15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.05)
    raise AssertionError(message)


class Client:
    def __init__(self, live: LiveServer) -> None:
        self.live = live
        self.port = live.port
        session = self.request("GET", "/api/session")[1]
        self.token, self.generation = session["token"], session["session_generation"]

    def request(self, method, path, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Host": f"127.0.0.1:{self.port}"}
        if method == "POST":
            headers.update({"Origin": f"http://127.0.0.1:{self.port}", "X-Map-Editor-Token": self.token,
                            "Content-Type": "application/json"})
        connection.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
        response = connection.getresponse()
        payload = response.read()
        connection.close()
        return response.status, json.loads(payload)

    def state(self) -> dict:
        return self.request("GET", "/api/workspace")[1]

    def move(self, x: int, y: int):
        state = self.state()
        expected = next((l["fingerprint"] for l in state["world"]["layouts"] if l["id"] == fixture.INTERIOR_ID),
                        "absent")
        return self.request("POST", "/api/commands/move_interior_layout", {
            "session_generation": self.generation,
            "snapshot_revision": state["snapshot_revision"],
            "segment": "watch-segment",
            "document_id": LAYOUT,
            "expected_document_fingerprint": expected,
            "arguments": {"interior_id": fixture.INTERIOR_ID, "room_id": "back", "x": x, "y": y},
        })

    def batches(self) -> int:
        return self.state()["following"]["batches"]

    def quiet(self, settle: float) -> None:
        """Wait until the watcher has reconciled and then stayed idle."""

        _wait(lambda: self.state()["following"]["active"], "the watcher never became active")
        last, since = self.batches(), time.monotonic()
        while time.monotonic() - since < max(1.0, settle * 6):
            time.sleep(0.05)
            now = self.batches()
            if now != last:
                last, since = now, time.monotonic()


def _server(workspace: Path, **overrides) -> LiveServer:
    return LiveServer(make_config(workspace, port=free_port(), watch=True, **overrides))


def _replace(path: Path, text: str) -> None:
    temporary = path.with_name(f".{path.name}.external")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _layout(x: int, y: int) -> str:
    return f"version: 1\nkind: layout\nid: {fixture.INTERIOR_ID}\npositions:\n  back: {{x: {x}, y: {y}}}\n"


def test_own_saves_with_real_delayed_notifications_keep_history_and_an_external_one_is_adopted(workspace):
    with _server(workspace) as live:
        client = Client(live)
        client.quiet(live.service.config.settle_seconds)
        before = client.batches()
        assert client.move(1, 1)[0] == 200
        assert client.move(2, 2)[0] == 200
        revision = client.state()["snapshot_revision"]
        _wait(lambda: client.batches() > before, "the own writes produced no reconciled notification")
        client.quiet(live.service.config.settle_seconds)
        state = client.state()
        assert state["snapshot_revision"] == revision
        assert state["history"]["undo"] is not None
        assert state["external_change"]["sequence"] == 0
        # An external replacement at the same path with different bytes.
        _replace(workspace / LAYOUT, _layout(7, 8))
        state = _wait(lambda: (s := client.state())["external_change"]["sequence"] == 1 and s,
                      "the external replacement was not adopted")
        assert state["history"]["undo"] is None
        rooms = {room["id"]: room["layout_position"] for room in state["world"]["interiors"][0]["rooms"]}
        assert rooms["back"] == [7, 8]
        assert (workspace / LAYOUT).read_text(encoding="utf-8") == _layout(7, 8)


def test_malformed_then_corrected_sources_follow_through_real_events(workspace):
    with _server(workspace) as live:
        client = Client(live)
        client.quiet(live.service.config.settle_seconds)
        world = client.state()["world"]
        (workspace / SETTLEMENT).write_text("version: 1\nkind: [unclosed\n", encoding="utf-8")
        state = _wait(lambda: (s := client.state())["preview_state"] == "stale" and s, "no stale preview")
        assert state["world"] == world
        assert client.move(1, 1)[1]["error"]["reason"] == "stale_preview"
        assert not (workspace / LAYOUT).exists()
        corrected = fixture.settlement_data()
        corrected["nodes"]["yard"]["x_m"] = 640
        _replace(workspace / SETTLEMENT, fixture.yaml_text(corrected))
        _wait(lambda: client.state()["preview_state"] == "current", "the correction was not adopted")
        assert client.move(1, 1)[0] == 200


def test_a_created_layout_directory_and_a_deleted_document_are_followed(workspace):
    with _server(workspace) as live:
        client = Client(live)
        client.quiet(live.service.config.settle_seconds)
        assert not (workspace / "content/map-editor-layouts").exists()
        (workspace / "content/map-editor-layouts").mkdir()
        (workspace / LAYOUT).write_text(_layout(3, 4), encoding="utf-8")
        _wait(lambda: client.state()["world"]["layouts"], "the created layout was not adopted")
        (workspace / LAYOUT).unlink()
        _wait(lambda: not client.state()["world"]["layouts"], "the deleted layout was not followed")


def test_a_root_that_appears_later_starts_to_be_watched(workspace):
    # The reference context names an external closure directory that does
    # not exist yet: it is watched through its nearest existing ancestor.
    context = fixture.write_reference_context(workspace)
    external = workspace / "external"
    for path in sorted(external.rglob("*"), reverse=True):
        path.unlink()
    external.rmdir()
    plan = watch_plan(workspace, ("external/**/*.txt",))
    assert str(external) in plan.targets and str(workspace) in plan.flat
    with _server(workspace) as live:
        client = Client(live)
        client.quiet(live.service.config.settle_seconds)
        assert client.state()["external_context_status"]["current"] is False
        fixture.write_reference_context(workspace)
        _wait(lambda: client.state()["external_context_status"]["current"], "the created closure was not read")
        # After the restart the new directory is watched recursively.
        _wait(lambda: str(external) in live_plan(live).recursive, "the plan did not take the new root")
        client.quiet(live.service.config.settle_seconds)
        (external / "declarations.txt").write_text("changed\n", encoding="utf-8")
        _wait(lambda: not client.state()["external_context_status"]["current"],
              "a change inside the new root was not followed")
    assert context.exists()


def live_plan(live: LiveServer):
    return watch_plan(live.service.config.workspace_root,
                      watching.discovery_rules(live.service.config.workspace_root))


def test_a_watcher_failure_is_reported_and_retried(workspace, monkeypatch):
    real = watching.watchfiles.awatch
    calls = []

    def flaky(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise OSError(28, "inotify watch limit reached")
        return real(*args, **kwargs)

    monkeypatch.setattr(watching.watchfiles, "awatch", flaky)
    with _server(workspace) as live:
        client = Client(live)
        _wait(lambda: client.state()["following"]["error"], "the failure was not reported")
        assert client.state()["following"]["active"] is False
        _wait(lambda: (f := client.state()["following"])["active"] and f["error"] is None,
              "the watcher did not recover")
        (workspace / "content/map-editor-layouts").mkdir()
        (workspace / LAYOUT).write_text(_layout(5, 5), encoding="utf-8")
        _wait(lambda: client.state()["world"]["layouts"], "the recovered watcher did not follow")
    assert not live.thread.is_alive()


def test_the_plan_confines_rules_and_covers_nested_roots(tmp_path):
    root = tmp_path
    for directory in ("content/maps", "world/lore/a", "world/maps/data", "tools"):
        (root / directory).mkdir(parents=True)
    plan = watch_plan(root, ("world/lore/**/*.py", "world/lore/a/*.py", "tools/one.py",
                             "../outside/*.py", "/abs/*.py", "**/*.py", "content/x/*.yaml"))
    assert plan.recursive == tuple(sorted((str(root / "content"), str(root / "world/lore"))))
    assert plan.flat == tuple(sorted((str(root / "tools"), str(root / "world/maps/data"))))
    assert set(plan.targets) == {str(root / "tools/one.py"), str(root / "world/maps/data/district_partition.json")}
    accept = watching.flat_filter(plan.targets)
    assert accept(None, str(root / "tools/one.py"))
    assert not accept(None, str(root / "tools/other.py"))
