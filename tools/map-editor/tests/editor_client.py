"""In-process command client over the real ASGI app (Starlette TestClient)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from starlette.testclient import TestClient

import synthetic_workspace as fixture
from conftest import ORIGIN, PORT, make_config

from elosern_map_editor.app import create_app, service_of

LAYOUT = f"content/map-editor-layouts/{fixture.INTERIOR_ID}.yaml"
INTERIOR = f"content/maps/interiors/{fixture.INTERIOR_ID}.yaml"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Editor:
    def __init__(
        self, workspace: Path, *, fault=None, segment: str = "segment-a", partition_hook=None, **config
    ) -> None:
        self.workspace = workspace
        self.app = create_app(make_config(workspace, **config), fault=fault, partition_hook=partition_hook)
        self.service = service_of(self.app)
        self.client = TestClient(self.app, base_url=f"http://127.0.0.1:{PORT}")
        body = self.client.get("/api/session").json()
        self.token, self.generation = body["token"], body["session_generation"]
        self.segment = segment

    def state(self) -> dict:
        return self.client.get("/api/workspace").json()

    def headers(self) -> dict:
        return {"Origin": ORIGIN, "X-Map-Editor-Token": self.token, "Content-Type": "application/json"}

    def raw(self, name: str, body) -> tuple[int, dict]:
        content = body if isinstance(body, str) else json.dumps(body)
        response = self.client.post(f"/api/commands/{name}", headers=self.headers(), content=content)
        return response.status_code, response.json()

    def envelope(self, document_id, expected, arguments, **overrides) -> dict:
        state = self.state()
        body = {
            "session_generation": self.generation,
            "snapshot_revision": state["snapshot_revision"],
            "segment": self.segment,
            "document_id": document_id,
            "expected_document_fingerprint": expected,
            "arguments": arguments,
        }
        body.update(overrides)
        return body

    def layout_fingerprint(self, interior_id: str = fixture.INTERIOR_ID) -> str:
        for layout in self.state()["world"]["layouts"]:
            if layout["id"] == interior_id:
                return layout["fingerprint"]
        return "absent"

    def move(self, room: str, x: int, y: int, *, interior: str = fixture.INTERIOR_ID, expected=None, **overrides):
        document = f"content/map-editor-layouts/{interior}.yaml"
        expected = self.layout_fingerprint(interior) if expected is None else expected
        arguments = {"interior_id": interior, "room_id": room, "x": x, "y": y}
        return self.raw("move_interior_layout", self.envelope(document, expected, arguments, **overrides))

    def remove_layout(self, *, expected=None, interior: str = fixture.INTERIOR_ID):
        document = f"content/map-editor-layouts/{interior}.yaml"
        expected = self.layout_fingerprint(interior) if expected is None else expected
        return self.raw("remove_interior_layout", self.envelope(document, expected, {"interior_id": interior}))

    def history(self, direction: str, **overrides):
        state = self.state()
        head = state["history"][direction] if state["history"]["segment"] == self.segment else None
        document = head["document_id"] if head else LAYOUT
        expected = head["expected_document_fingerprint"] if head else "absent"
        return self.raw(direction, self.envelope(document, expected, {}, **overrides))

    def undo(self, **overrides):
        return self.history("undo", **overrides)

    def redo(self, **overrides):
        return self.history("redo", **overrides)

    def reload(self) -> tuple[int, dict]:
        response = self.client.post(
            "/api/reload", headers=self.headers(), content=json.dumps({"session_generation": self.generation})
        )
        return response.status_code, response.json()

    def partition(self, action: str, body: dict | None = None) -> tuple[int, dict]:
        """``generate`` or ``cancel`` the partition job."""

        if body is None:
            body = {"session_generation": self.generation}
            if action == "generate":
                body["snapshot_revision"] = self.state()["snapshot_revision"]
        response = self.client.post(f"/api/partition/{action}", headers=self.headers(), content=json.dumps(body))
        return response.status_code, response.json()

    def follow(self) -> bool:
        """One watcher reconciliation, as after coalesced notifications."""

        return self.service.reconcile()

    def positions(self, interior_id: str = fixture.INTERIOR_ID) -> dict:
        for interior in self.state()["world"]["interiors"]:
            if interior["id"] == interior_id:
                return {room["id"]: room["layout_position"] for room in interior["rooms"]}
        raise KeyError(interior_id)


__all__ = ["Editor", "INTERIOR", "LAYOUT", "sha"]
