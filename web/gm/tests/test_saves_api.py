"""S5 save API: access matrix, CSRF, payloads, domain errors, downloads.

Every test runs against a temporary world (``server.saves.tests._support``):
the save module's layout, metadata collector, migration root, and shutdown
scheduler are patched, so no test touches the real database or art store and
no test shuts anything down.
"""

from __future__ import annotations

import io
import json
import tarfile
from unittest import mock

from django.conf import settings

from server.saves import snapshot
from server.saves.tests._support import FUTURE_MIGRATION, TempWorld, fixed_metadata
from web.gm.tests._support import GmTestCase
from tools.spec_traceability import covers_requirement

ROUTES = (
    ("get", "/gm/api/saves/"),
    ("post", "/gm/api/saves/"),
    ("post", "/gm/api/saves/{id}/restore"),
    ("post", "/gm/api/saves/{id}/delete"),
    ("get", "/gm/api/saves/{id}/download"),
)


class SavesApiTestCase(GmTestCase):
    def setUp(self):
        super().setUp()
        self.world = TempWorld()
        self.addCleanup(self.world.cleanup)
        self.shutdowns = []
        for target, value in (
            ("server.saves.snapshot.default_layout", lambda: self.world.layout),
            ("server.saves.snapshot.world_metadata", fixed_metadata),
            ("server.saves.snapshot.project_root", lambda: self.world.root),
            ("server.saves.snapshot.schedule_evennia_shutdown", lambda: self.shutdowns.append(True)),
        ):
            patcher = mock.patch(target, side_effect=value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def make(self, kind="manual", label="slot"):
        with mock.patch("server.saves.snapshot.log_info"):
            return snapshot.create_snapshot(kind, label, layout=self.world.layout, metadata=fixed_metadata)

    def post(self, client, url, body=None, **extra):
        return client.post(url, data=json.dumps(body or {}), content_type="application/json", **extra)


class SavesAccessTests(SavesApiTestCase):
    @covers_requirement("gm-save-management::protected-save-api-and-streaming-download")
    def test_access_matrix_covers_every_save_route(self):
        save = self.make()
        expected = {"anonymous": (401, "unauthenticated"), "player": (403, "forbidden")}
        for kind, (status, code) in expected.items():
            client = self.client_for(kind)
            for method, url in ROUTES:
                with self.subTest(kind=kind, url=url, method=method):
                    response = getattr(client, method)(url.format(id=save.id))
                    self.assert_error_envelope(response, status, code)
        for kind in ("developer", "superuser"):
            with self.subTest(kind=kind):
                data = self.assert_ok_envelope(self.client_for(kind).get("/gm/api/saves/"))
                self.assertEqual([item["id"] for item in data["saves"]], [save.id])
                response = self.client_for(kind).get(f"/gm/api/saves/{save.id}/download")
                self.assertEqual(response.status_code, 200)
                b"".join(response.streaming_content)
        self.assertEqual(self.client_for("developer").get("/gm/api/saves").status_code, 200)

    @covers_requirement("gm-save-management::protected-save-api-and-streaming-download")
    def test_posts_require_a_valid_csrf_token(self):
        save = self.make()
        client = self.client_for("developer", enforce_csrf_checks=True)
        token = client.get("/gm/").cookies[settings.CSRF_COOKIE_NAME].value
        for url in ("/gm/api/saves/", f"/gm/api/saves/{save.id}/delete", f"/gm/api/saves/{save.id}/restore"):
            for headers in ({}, {"HTTP_X_CSRFTOKEN": "x" * len(token)}):
                with self.subTest(url=url, token=bool(headers)):
                    self.assert_error_envelope(self.post(client, url, **headers), 403, "csrf_failed")
        self.assertEqual(len(snapshot.list_saves(layout=self.world.layout)), 1)
        self.assertEqual(self.shutdowns, [])
        response = self.post(client, "/gm/api/saves/", {"label": "with token"}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 201, response.content)


class SavesPayloadTests(SavesApiTestCase):
    def setUp(self):
        super().setUp()
        self.client = self.client_for("developer")

    @covers_requirement("gm-save-management::protected-save-api-and-streaming-download", "gm-save-management::save-operational-observability")
    def test_create_list_and_latest_restore_result(self):
        with mock.patch("web.gm.saves_api.log_info") as log_info:
            response = self.post(self.client, "/gm/api/saves/", {"label": "  before\nthe duel  "})
        self.assertEqual(response.status_code, 201)
        created = json.loads(response.content)["data"]
        self.assertEqual(created["label"], "before the duel")
        self.assertEqual(created["kind"], "manual")
        self.assertTrue(created["deletable"])
        self.assertEqual(created["clock"]["tick"], 42)
        self.assertEqual(created["players"], [{"name": "Tester", "location": "room-a"}])
        log_info.assert_called_once_with(
            "gm_action",
            context={"account": self.account.username, "action": "save_create", "target": created["id"], "outcome": "created"},
        )
        self.world.layout.result_file.write_text(json.dumps({
            "save": created["id"], "kind": "manual", "label": "before the duel",
            "outcome": "restored", "reason": None, "finished_at": "2026-10-07T00:00:00+00:00",
        }))
        data = self.assert_ok_envelope(self.client.get("/gm/api/saves/"))
        self.assertEqual(set(data), {"saves", "restore_result", "pending", "autosave_keep"})
        self.assertEqual(data["saves"][0]["id"], created["id"])
        for key in ("label", "kind", "created_at", "clock", "players", "size_bytes", "file_count", "deletable"):
            self.assertIn(key, data["saves"][0])
        self.assertEqual(data["restore_result"]["outcome"], "restored")
        self.assertEqual(data["autosave_keep"], 10)
        self.assertIsNone(data["pending"])

    def test_malformed_body_creates_an_unlabelled_save(self):
        response = self.client.post("/gm/api/saves/", data="{nope", content_type="application/json")
        self.assertEqual(json.loads(response.content)["data"]["label"], "")

    @covers_requirement("gm-save-management::protected-save-api-and-streaming-download", "gm-save-management::guarded-restore-request")
    def test_restore_request_and_its_refusals(self):
        target = self.make()
        incompatible = self.make()
        self.world.add_migration(FUTURE_MIGRATION, db=self.world.layout.saved_db(incompatible.id))
        self.assert_error_envelope(self.post(self.client, "/gm/api/saves/not-an-id/restore"), 400, "invalid_save_id")
        self.assert_error_envelope(
            self.post(self.client, "/gm/api/saves/20200101T000000-abcdef/restore"), 404, "save_not_found"
        )
        self.assert_error_envelope(
            self.post(self.client, f"/gm/api/saves/{incompatible.id}/restore"), 409, "save_incompatible"
        )
        self.assertEqual(self.shutdowns, [])
        with mock.patch("web.gm.saves_api.log_info") as log_info:
            response = self.post(self.client, f"/gm/api/saves/{target.id}/restore")
        self.assertEqual(response.status_code, 202, response.content)
        data = json.loads(response.content)["data"]
        self.assertEqual(data["save"], target.id)
        self.assertTrue(data["shutdown"])
        self.assertEqual(self.shutdowns, [True])
        self.assertEqual(log_info.call_args.kwargs["context"]["action"], "save_restore")
        listing = self.assert_ok_envelope(self.client.get("/gm/api/saves/"))
        self.assertEqual(listing["pending"], target.id)
        self.assert_error_envelope(self.post(self.client, "/gm/api/saves/"), 409, "save_in_progress")

    @covers_requirement("gm-save-management::protected-save-api-and-streaming-download")
    def test_contention_is_save_in_progress(self):
        with mock.patch("server.saves.snapshot._snapshot_lock") as lock:
            lock.acquire.return_value = False
            self.assert_error_envelope(self.post(self.client, "/gm/api/saves/"), 409, "save_in_progress")

    @covers_requirement("gm-save-management::protected-save-api-and-streaming-download")
    def test_unexpected_failure_is_save_failed(self):
        with mock.patch("server.saves.snapshot._backup_database", side_effect=OSError("disk")), mock.patch(
            "server.saves.snapshot.log_error"
        ):
            self.assert_error_envelope(self.post(self.client, "/gm/api/saves/"), 500, "save_failed")
        self.assertEqual(snapshot.list_saves(layout=self.world.layout), [])

    @covers_requirement("gm-save-management::protected-save-api-and-streaming-download", "gm-save-management::retention-and-manual-deletion")
    def test_delete_manual_and_refuse_automatic(self):
        manual, automatic = self.make(), self.make(kind="auto_restore")
        body = self.assert_error_envelope(
            self.post(self.client, f"/gm/api/saves/{automatic.id}/delete"), 409, "save_delete_forbidden"
        )
        self.assertNotEqual(body["error"]["code"], "forbidden")
        response = self.post(self.client, f"/gm/api/saves/{manual.id}/delete")
        self.assertEqual(self.assert_ok_envelope(response), {"deleted": manual.id})
        self.assertEqual([s.id for s in snapshot.list_saves(layout=self.world.layout)], [automatic.id])
        self.assert_error_envelope(self.post(self.client, f"/gm/api/saves/{manual.id}/delete"), 404, "save_not_found")

    def test_wrong_methods_are_refused(self):
        save = self.make()
        self.assert_error_envelope(self.client.get(f"/gm/api/saves/{save.id}/delete"), 405, "method_not_allowed")
        self.assert_error_envelope(self.client.post(f"/gm/api/saves/{save.id}/download"), 405, "method_not_allowed")

    @covers_requirement("gm-save-management::protected-save-api-and-streaming-download", "gm-save-management::save-operational-observability")
    def test_download_streams_an_uncompressed_tar(self):
        self.world.art("scene/forest.webp", b"forest")
        self.world.art(".saves/20200101T000000-abcdef/x.png", b"nested")
        save = self.make()
        with mock.patch("web.gm.saves_api.log_info") as log_info:
            response = self.client.get(f"/gm/api/saves/{save.id}/download")
        log_info.assert_called_once_with(
            "gm_action",
            context={"account": self.account.username, "action": "save_download", "target": save.id, "outcome": "streamed"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.streaming)
        self.assertEqual(response["Content-Type"], "application/x-tar")
        self.assertIn(f"elosern-save-{save.id}.tar", response["Content-Disposition"])
        body = b"".join(response.streaming_content)
        self.assertEqual(len(body), int(response["Content-Length"]))
        with tarfile.open(fileobj=io.BytesIO(body), mode="r:") as archive:
            names = set(archive.getnames())
        self.assertEqual(
            names,
            {f"{save.id}/manifest.json", f"{save.id}/evennia.db3", f"{save.id}/art/scene/forest.webp"},
        )
        self.assert_error_envelope(self.client.get("/gm/api/saves/bad/download"), 400, "invalid_save_id")
        self.assert_error_envelope(
            self.client.get("/gm/api/saves/20200101T000000-abcdef/download"), 404, "save_not_found"
        )
