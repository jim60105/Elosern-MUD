"""Complete-state HTTP, SSE invalidation/refetch and session restarts (real server)."""

from __future__ import annotations

import http.client
import json
import time

import synthetic_workspace as fixture
from conftest import LiveServer, free_port, make_config


class Sse:
    """A minimal SSE reader over a real socket."""

    def __init__(self, port: int) -> None:
        self.connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        self.connection.request("GET", "/api/events", headers={"Host": f"127.0.0.1:{port}"})
        self.response = self.connection.getresponse()
        assert self.response.status == 200
        assert self.response.getheader("content-type").startswith("text/event-stream")

    def next_event(self) -> tuple[str, dict]:
        event, data = None, None
        while True:
            line = self.response.fp.readline().decode("utf-8")
            if line == "":
                raise EOFError("stream closed")
            line = line.rstrip("\n")
            if line.startswith("event: "):
                event = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
            elif line == "" and event is not None:
                return event, data

    def close(self) -> None:
        self.connection.close()


def _request(port, method, path, *, headers=None, body=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    all_headers = {"Host": f"127.0.0.1:{port}", **(headers or {})}
    connection.request(method, path, body=body, headers=all_headers)
    response = connection.getresponse()
    payload = response.read()
    connection.close()
    return response.status, json.loads(payload) if payload else None


def _session(port):
    return _request(port, "GET", "/api/session")[1]


def _reload(port, token, generation):
    return _request(
        port,
        "POST",
        "/api/reload",
        headers={
            "Origin": f"http://127.0.0.1:{port}",
            "X-Map-Editor-Token": token,
            "Content-Type": "application/json",
        },
        body=json.dumps({"session_generation": generation}),
    )


def _wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("condition not reached")
        time.sleep(0.02)


SETTLEMENT = f"content/maps/settlements/{fixture.SETTLEMENT_ID}.yaml"


def _move_yard(workspace, x_m):
    data = fixture.settlement_data()
    data["nodes"]["yard"]["x_m"] = x_m
    (workspace / SETTLEMENT).write_text(fixture.yaml_text(data), encoding="utf-8")


def test_invalidation_then_refetch_and_reconnect_after_a_disconnect(workspace):
    port = free_port()
    with LiveServer(make_config(workspace, port=port)) as live:
        session = _session(port)
        stream = Sse(port)
        assert stream.next_event() == (
            "status",
            {"session_generation": session["session_generation"], "snapshot_revision": 1, "preview_state": "current"},
        )
        _move_yard(workspace, 600)
        status, body = _reload(port, session["token"], session["session_generation"])
        assert (status, body["changed"], body["snapshot_revision"]) == (200, True, 2)
        event, data = stream.next_event()
        assert (event, data["snapshot_revision"]) == ("invalidate", 2)
        refetched = _request(port, "GET", "/api/workspace")[1]
        yard = {n["id"]: n for n in refetched["world"]["settlements"][0]["nodes"]}["yard"]
        assert (refetched["snapshot_revision"], yard["local_m"]) == (2, [600, 400])

        # Disconnect, change disk while no stream is open, reconnect.
        stream.close()
        _wait_for(lambda: live.service.broadcaster.client_count == 0)
        _move_yard(workspace, 700)
        assert _reload(port, session["token"], session["session_generation"])[0] == 200
        reconnected = Sse(port)
        event, data = reconnected.next_event()
        assert (event, data["snapshot_revision"]) == ("status", 3)
        refetched = _request(port, "GET", "/api/workspace")[1]
        yard = {n["id"]: n for n in refetched["world"]["settlements"][0]["nodes"]}["yard"]
        assert yard["local_m"] == [700, 400]
        reconnected.close()


def test_an_unchanged_reread_publishes_nothing(workspace):
    port = free_port()
    with LiveServer(make_config(workspace, port=port)):
        session = _session(port)
        status, body = _reload(port, session["token"], session["session_generation"])
        assert (status, body["changed"], body["snapshot_revision"]) == (200, False, 1)


def test_a_failed_reread_keeps_the_last_preview_as_stale_and_pauses_writes(workspace):
    port = free_port()
    with LiveServer(make_config(workspace, port=port)):
        session = _session(port)
        before = _request(port, "GET", "/api/workspace")[1]
        (workspace / SETTLEMENT).write_text("version: 1\nkind: [unclosed\n", encoding="utf-8")
        assert _reload(port, session["token"], session["session_generation"])[0] == 200
        state = _request(port, "GET", "/api/workspace")[1]
        assert state["preview_state"] == "stale"
        assert state["write_pause"] == {"paused": True, "reason": "stale_preview"}
        assert state["world"] == before["world"]
        assert state["snapshot_read_at"] == before["snapshot_read_at"]
        assert any(d["relative_path"] == SETTLEMENT for d in state["candidate_diagnostics"])
        # The service never rewrites the malformed file from its retained preview.
        assert (workspace / SETTLEMENT).read_text(encoding="utf-8") == "version: 1\nkind: [unclosed\n"
        _move_yard(workspace, 300)
        _reload(port, session["token"], session["session_generation"])
        recovered = _request(port, "GET", "/api/workspace")[1]
        assert (recovered["preview_state"], recovered["write_pause"]["paused"]) == ("current", False)


def test_an_old_session_token_is_rejected_after_a_restart(workspace):
    port = free_port()
    with LiveServer(make_config(workspace, port=port)):
        old = _session(port)
    with LiveServer(make_config(workspace, port=port)) as live:
        new = _session(port)
        assert new["session_generation"] != old["session_generation"]
        assert new["token"] != old["token"]
        before = _request(port, "GET", "/api/workspace")[1]
        status, body = _reload(port, old["token"], old["session_generation"])
        assert (status, body["error"]["code"]) == (401, "unauthorized")
        status, body = _reload(port, new["token"], old["session_generation"])
        assert (status, body["error"]["code"]) == (409, "stale_session")
        after = _request(port, "GET", "/api/workspace")[1]
        assert after["snapshot_revision"] == before["snapshot_revision"] == 1
        assert live.service.snapshot_revision == 1


def test_shutdown_ends_open_streams(workspace):
    port = free_port()
    live = LiveServer(make_config(workspace, port=port))
    with live:
        stream = Sse(port)
        stream.next_event()
        _wait_for(lambda: live.service.broadcaster.client_count == 1)
        started = time.monotonic()
    assert not live.thread.is_alive()
    assert time.monotonic() - started < 8
    assert live.service.broadcaster.client_count == 0
    stream.close()
