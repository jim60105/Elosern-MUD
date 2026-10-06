"""S1 API payloads, the JSON envelope, and the shell response.

Session reports the real account, permission level, aware server time, and
the project version; health performs a real database read and never reaches
an external service; failures use matching statuses and envelopes; S1 has no
production write endpoint.
"""

from __future__ import annotations

import socket
import tomllib
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.db import DatabaseError
from django.shortcuts import resolve_url
from django.test import Client
from django.utils import timezone

from web.gm.tests._support import GmTestCase

REPO_ROOT = Path(__file__).resolve().parents[3]


def project_version() -> str:
    with (REPO_ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)["project"]["version"]


class GmSessionApiTest(GmTestCase):
    def test_session_reports_developer_identity_time_and_version(self):
        data = self.assert_ok_envelope(self.client_for("developer").get("/gm/api/session"))
        self.assertEqual(
            set(data), {"account_name", "permission_level", "server_time", "game_version"}
        )
        self.assertEqual(data["account_name"], self.account.username)
        self.assertEqual(data["permission_level"], "Developer")
        self.assertEqual(data["game_version"], project_version())
        server_time = datetime.fromisoformat(data["server_time"])
        self.assertIsNotNone(server_time.tzinfo)
        self.assertLess(abs(timezone.now() - server_time), timedelta(minutes=1))

    def test_session_reports_superuser_level(self):
        data = self.assert_ok_envelope(self.client_for("superuser").get("/gm/api/session"))
        self.assertEqual(data["account_name"], self.superuser.username)
        self.assertEqual(data["permission_level"], "superuser")

    def test_unreadable_version_source_is_an_error_not_a_fabricated_value(self):
        with mock.patch("web.gm.views.game_version", side_effect=OSError("gone")), \
                mock.patch("web.gm.views.log_error") as log_error:
            response = self.client_for("developer").get("/gm/api/session")
        self.assert_error_envelope(response, 500, "version_unavailable")
        self.assertEqual(log_error.call_args.args[0], "gm_version_unavailable")


    def test_misshapen_version_source_is_an_error_envelope(self):
        from web.gm import version

        version.game_version.cache_clear()
        try:
            with mock.patch("web.gm.version.tomllib.load", return_value={"project": "0.1.0"}):
                response = self.client_for("developer").get("/gm/api/session")
        finally:
            version.game_version.cache_clear()
        self.assert_error_envelope(response, 500, "version_unavailable")


class GmHealthApiTest(GmTestCase):
    def test_health_reports_django_and_database_without_network(self):
        with mock.patch.object(
            socket, "create_connection", side_effect=AssertionError("network probe")
        ) as connect:
            data = self.assert_ok_envelope(self.client_for("developer").get("/gm/api/health"))
        self.assertEqual(data, {"django": "ok", "database": "readable"})
        connect.assert_not_called()

    def test_health_reads_the_database(self):
        with mock.patch("web.gm.views.AccountDB") as account_db:
            account_db.objects.order_by.return_value.values_list.return_value = [1]
            self.assert_ok_envelope(self.client_for("developer").get("/gm/api/health"))
        account_db.objects.order_by.assert_called_once_with()

    def test_unreadable_database_returns_503_without_claiming_readable(self):
        client = self.client_for("developer")
        with mock.patch("web.gm.views.AccountDB") as account_db, \
                mock.patch("web.gm.views.log_warn") as log_warn:
            account_db.objects.order_by.side_effect = DatabaseError("disk I/O error")
            response = client.get("/gm/api/health")
        self.assert_error_envelope(response, 503, "database_unreadable")
        self.assertNotIn(b"readable\"", response.content.replace(b"unreadable", b""))
        self.assertEqual(log_warn.call_args.args[0], "gm_health_database_unreadable")


class GmMethodAndWriteSurfaceTest(GmTestCase):
    def test_read_only_apis_reject_other_methods_with_envelope(self):
        client = self.client_for("developer")  # CSRF checks are off by default
        for url in ("/gm/api/session", "/gm/api/health"):
            for method in ("post", "put", "patch", "delete"):
                with self.subTest(url=url, method=method):
                    response = getattr(client, method)(url)
                    self.assert_error_envelope(response, 405, "method_not_allowed")
                    self.assertEqual(response["Allow"], "GET, HEAD")

    def test_no_production_gm_route_accepts_a_write(self):
        client = self.client_for("developer")
        for url in ("/gm/", "/gm/x", "/gm/api", "/gm/api/session", "/gm/api/health",
                    "/gm/api/write"):
            with self.subTest(url=url):
                self.assertGreaterEqual(client.post(url, {"x": "1"}).status_code, 400)

    def test_rest_api_stays_disabled(self):
        self.assertFalse(settings.REST_API_ENABLED)

    def test_api_responses_are_not_cacheable(self):
        response = self.client_for("developer").get("/gm/api/session")
        self.assertEqual(response["Cache-Control"], "no-store")


class GmShellTest(GmTestCase):
    def test_shell_references_stable_gm_assets_and_configured_login(self):
        response = self.client_for("developer").get("/gm/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn(f'{settings.STATIC_URL}gm/dist/index.js', content)
        self.assertIn(f'{settings.STATIC_URL}gm/dist/index.css', content)
        self.assertIn(f'data-login-url="{resolve_url(settings.LOGIN_URL)}"', content)
        self.assertIn(f'data-logout-url="{resolve_url(settings.LOGOUT_URL)}"', content)
        # Isolation: the game bundle is never loaded by the GM shell.
        self.assertNotIn("webclient/app/dist", content)
        self.assertNotIn("evennia.js", content)

    def test_shell_issues_a_readable_csrf_cookie(self):
        client = Client()
        client.force_login(self.account)
        response = client.get("/gm/")
        cookie = response.cookies.get(settings.CSRF_COOKIE_NAME)
        self.assertIsNotNone(cookie)
        self.assertTrue(cookie.value)
        self.assertFalse(cookie["httponly"])
