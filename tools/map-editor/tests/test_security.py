"""Host/Origin/token/body admission, response hardening and inert content."""

from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient

import synthetic_workspace as fixture
from conftest import ORIGIN, PORT, make_config

from elosern_map_editor import app as app_module
from elosern_map_editor.app import create_app, service_of


@pytest.fixture
def harness(workspace, dist, monkeypatch):
    application = create_app(make_config(workspace, dist))
    service = service_of(application)
    reads: list = []
    real_read = app_module.read_workspace
    monkeypatch.setattr(app_module, "read_workspace", lambda *a: reads.append(a) or real_read(*a))
    client = TestClient(application, base_url=f"http://127.0.0.1:{PORT}")
    return client, service, reads, workspace


def _token(client) -> tuple[str, str]:
    body = client.get("/api/session", headers={"Sec-Fetch-Site": "same-origin"}).json()
    return body["token"], body["session_generation"]


def _post(client, token, generation, **overrides):
    headers = {"Origin": ORIGIN, "X-Map-Editor-Token": token, "Content-Type": "application/json"}
    headers.update(overrides.pop("headers", {}))
    content = overrides.pop("content", json.dumps({"session_generation": generation}))
    return client.post("/api/reload", headers={k: v for k, v in headers.items() if v is not None}, content=content)


def test_an_admitted_reload_rereads_disk(harness):
    client, service, reads, _ = harness
    token, generation = _token(client)
    response = _post(client, token, generation)
    assert response.status_code == 200
    assert len(reads) == 1


@pytest.mark.parametrize(
    ("headers", "status", "code"),
    [
        ({"Origin": "http://localhost:3000"}, 403, "forbidden_origin"),
        ({"Origin": "null"}, 403, "forbidden_origin"),
        ({"Origin": f"http://127.0.0.1:{PORT}.example.invalid"}, 403, "forbidden_origin"),
        ({"Origin": None}, 403, "forbidden_origin"),
        ({"Sec-Fetch-Site": "same-site"}, 403, "forbidden_origin"),
        ({"Sec-Fetch-Site": "cross-site"}, 403, "forbidden_origin"),
        ({"X-Map-Editor-Token": None}, 401, "unauthorized"),
        ({"X-Map-Editor-Token": "not-the-token"}, 401, "unauthorized"),
        ({"Content-Type": "text/plain"}, 415, "unsupported_media_type"),
        ({"Content-Type": "application/x-www-form-urlencoded"}, 415, "unsupported_media_type"),
    ],
)
def test_foreign_or_unauthenticated_mutations_are_rejected_before_any_read(harness, headers, status, code):
    client, service, reads, workspace = harness
    token, generation = _token(client)
    before = (service.snapshot_revision, fixture.tree_digest(workspace))
    response = _post(client, token, generation, headers=headers)
    assert (response.status_code, response.json()["error"]["code"]) == (status, code)
    assert reads == []
    assert (service.snapshot_revision, fixture.tree_digest(workspace)) == before


@pytest.mark.parametrize("host", ["evil.example.invalid", f"127.0.0.1:{PORT + 1}", "127.0.0.1", f"localhost.:{PORT}"])
def test_a_foreign_host_is_rejected_on_every_route(harness, host):
    client, service, reads, _ = harness
    for path in ("/", "/api/session", "/api/workspace", "/api/events"):
        response = client.get(path, headers={"Host": host})
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden_host"
    assert reads == []


def test_the_token_bootstrap_refuses_other_origins(harness):
    client, *_ = harness
    for headers in ({"Origin": "http://localhost:9999"}, {"Sec-Fetch-Site": "same-site"}, {"Origin": "null"}):
        response = client.get("/api/session", headers=headers)
        assert response.status_code == 403
        assert "token" not in response.text


def test_oversized_bodies_are_rejected_before_reading(harness):
    client, service, reads, workspace = harness
    token, generation = _token(client)
    big = json.dumps({"session_generation": generation, "pad": "x" * (70 * 1024)})
    response = _post(client, token, generation, content=big)
    assert response.status_code == 413

    def chunks():
        for _ in range(80):
            yield b"x" * 1024

    response = _post(client, token, generation, content=chunks())
    assert response.status_code == 413
    assert reads == []
    assert service.snapshot_revision == 1


def test_a_reload_body_may_carry_nothing_but_the_session(harness):
    client, service, reads, workspace = harness
    token, generation = _token(client)
    before = fixture.tree_digest(workspace)
    for content in (
        json.dumps({"session_generation": generation, "relative_path": "../../etc/passwd"}),
        json.dumps([generation]),
        "not json",
    ):
        response = _post(client, token, generation, content=content)
        assert response.status_code == 400
    response = _post(client, token, generation, content=json.dumps({"session_generation": "old"}))
    assert (response.status_code, response.json()["error"]["code"]) == (409, "stale_session")
    assert reads == []
    assert fixture.tree_digest(workspace) == before


def test_other_methods_and_websockets_are_refused(harness):
    client, *_ = harness
    token, _ = _token(client)
    for method in ("PUT", "PATCH", "DELETE"):
        response = client.request(method, "/api/workspace", headers={"Origin": ORIGIN, "X-Map-Editor-Token": token})
        assert response.status_code == 405


def test_every_response_is_hardened_and_never_cross_origin(harness):
    client, *_ = harness
    for path in ("/", "/assets/app.js", "/api/workspace", "/api/session", "/nope"):
        response = client.get(path, headers={"Origin": ORIGIN})
        assert "default-src 'self'" in response.headers["content-security-policy"]
        assert response.headers["x-content-type-options"] == "nosniff"
        assert not [name for name in response.headers if name.lower().startswith("access-control-")]


@pytest.mark.parametrize(
    "path",
    ["/assets/../../pyproject.toml", "/assets/%2e%2e/%2e%2e/pyproject.toml", "/assets/..%2findex.html", "/../content/maps/continent.yaml"],
)
def test_static_traversal_serves_nothing_outside_the_build(harness, path):
    client, *_ = harness
    response = client.get(path)
    assert response.status_code == 404
    assert "elosern-map-editor" not in response.text


def test_a_missing_build_is_reported_without_serving_anything_else(workspace):
    client = TestClient(create_app(make_config(workspace)), base_url=f"http://127.0.0.1:{PORT}")
    response = client.get("/")
    assert response.status_code == 503
    assert "pnpm" in response.text
    assert client.get("/api/workspace").status_code == 200


def test_authored_prose_and_scene_ids_travel_as_inert_json_strings(harness):
    client, *_ = harness
    response = client.get("/api/workspace")
    assert response.headers["content-type"].startswith("application/json")
    nodes = {node["id"]: node for node in response.json()["world"]["settlements"][0]["nodes"]}
    assert nodes["yard"]["desc"] == fixture.HOSTILE_DESC
    assert nodes["gate"]["scene_archetype"] == fixture.URL_LIKE_SCENE
    assert "connect-src 'self'" in response.headers["content-security-policy"]
    assert "img-src 'self' data:" in response.headers["content-security-policy"]


def test_host_names_compare_case_insensitively(harness):
    client, *_ = harness
    assert client.get("/api/workspace", headers={"Host": f"LOCALHOST:{PORT}"}).status_code == 200


def test_duplicated_admission_headers_are_refused(workspace, dist):
    import asyncio

    application = create_app(make_config(workspace, dist))
    service = service_of(application)
    token = service.session.token

    def call(headers):
        sent = []

        async def receive():
            return {"type": "http.request", "body": b"{}", "more_body": False}

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/reload",
            "headers": [(k.encode(), v.encode()) for k, v in headers],
        }
        asyncio.run(application(scope, receive, send))
        return sent[0]["status"], json.loads(sent[1]["body"])["error"]["code"]

    base = [
        ("host", f"127.0.0.1:{PORT}"),
        ("origin", ORIGIN),
        ("x-map-editor-token", token),
        ("content-type", "application/json"),
    ]
    assert call(base + [("host", f"127.0.0.1:{PORT}")]) == (403, "forbidden_host")
    assert call(base + [("origin", ORIGIN)]) == (403, "forbidden_origin")
    assert call(base + [("x-map-editor-token", token)]) == (401, "unauthorized")
    assert call(base + [("content-length", "2"), ("content-length", "2")]) == (400, "invalid_content_length")
    assert service.snapshot_revision == 1
