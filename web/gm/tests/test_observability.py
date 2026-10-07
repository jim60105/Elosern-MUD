"""GM facade events: ``gm_request`` per API outcome, ``gm_denied`` per refusal.

Assertions patch the caller modules' bindings (``web.gm.middleware.log_info``
and ``web.gm.access.log_warn``), never ``world.observability.*``.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

from django.db import DatabaseError
from django.test import Client

from web.gm.access import ROUTE_LABEL_LIMIT

from tools.spec_traceability import covers_requirement
from web.gm.tests._support import GmTestCase

REPO_ROOT = Path(__file__).resolve().parents[3]
REQUEST_KEYS = {"account", "route", "method", "status"}


class GmEventTest(GmTestCase):
    def request(self, kind, url, client=None):
        client = client or self.client_for(kind)
        with mock.patch("web.gm.middleware.log_info") as log_info, \
                mock.patch("web.gm.access.log_warn") as log_warn:
            response = client.get(url)
        requests = [c.kwargs["context"] for c in log_info.call_args_list
                    if c.args[0] == "gm_request"]
        denied = [c.kwargs["context"] for c in log_warn.call_args_list
                  if c.args[0] == "gm_denied"]
        return response, requests, denied

    @covers_requirement(
        "gm-portal-access-api::facade-request-and-denial-events",
        "gm-portal-access-api::registered-backend-acceptance-coverage",
    )
    def test_api_outcomes_each_emit_one_gm_request_with_final_status(self):
        cases = (
            ("developer", "/gm/api/session", 200, self.account.username),
            ("superuser", "/gm/api/dashboard", 200, "GmSuperuser"),
            ("anonymous", "/gm/api/session", 401, "anonymous"),
            ("player", "/gm/api/dashboard", 403, self.account2.username),
            ("developer", "/gm/api/missing", 404, self.account.username),
        )
        for kind, url, status, account in cases:
            with self.subTest(kind=kind, url=url):
                response, requests, _ = self.request(kind, url)
                self.assertEqual(response.status_code, status)
                self.assertEqual(len(requests), 1)
                self.assertEqual(set(requests[0]), REQUEST_KEYS)
                self.assertEqual(requests[0]["status"], status)
                self.assertEqual(requests[0]["route"], url)
                self.assertEqual(requests[0]["account"], account)

    @covers_requirement(
        "gm-portal-access-api::facade-request-and-denial-events",
    )
    def test_denials_emit_gm_denied_for_pages_and_apis(self):
        cases = (
            ("anonymous", "/gm/", "anonymous"),
            ("anonymous", "/gm/api/dashboard", "anonymous"),
            ("player", "/gm/deep/link", self.account2.username),
            ("player", "/gm/api/session", self.account2.username),
        )
        for kind, url, account in cases:
            with self.subTest(kind=kind, url=url):
                _, _, denied = self.request(kind, url)
                self.assertEqual(denied, [{"account": account, "route": url}])

    @covers_requirement(
        "gm-portal-access-api::facade-request-and-denial-events",
    )
    def test_allowed_requests_and_pages_emit_no_denial_and_pages_no_request(self):
        _, requests, denied = self.request("developer", "/gm/")
        self.assertEqual((requests, denied), ([], []))
        _, requests, denied = self.request("developer", "/gm/api/missing")
        self.assertEqual(denied, [])
        self.assertEqual(len(requests), 1)

    @covers_requirement(
        "gm-portal-access-api::facade-request-and-denial-events",
    )
    def test_a_view_crash_still_logs_the_final_500(self):
        client = Client(raise_request_exception=False)
        client.force_login(self.account)
        with mock.patch("web.gm.views.dashboard_snapshot.build_snapshot", side_effect=RuntimeError("boom")):
            response, requests, _ = self.request("developer", "/gm/api/dashboard", client=client)
        self.assertEqual(response.status_code, 500)
        self.assertEqual([r["status"] for r in requests], [500])

    @covers_requirement(
        "gm-portal-access-api::facade-request-and-denial-events",
        "gm-portal-access-api::consistent-json-transport",
    )
    def test_an_unreadable_session_store_still_answers_and_logs_the_api(self):
        client = self.client_for("developer")
        with mock.patch(
            "web.gm.middleware.access_decision", side_effect=DatabaseError("locked")
        ), mock.patch("web.gm.middleware.log_info") as log_info, \
                mock.patch("web.gm.middleware.log_warn") as log_warn:
            response = client.get("/gm/api/session")
        self.assert_error_envelope(response, 503, "database_unreadable")
        self.assertEqual(log_warn.call_args.args[0], "gm_access_unavailable")
        statuses = [c.kwargs["context"]["status"] for c in log_info.call_args_list
                    if c.args[0] == "gm_request"]
        self.assertEqual(statuses, [503])

    @covers_requirement(
        "gm-portal-access-api::facade-request-and-denial-events",
    )
    def test_event_routes_are_truncated(self):
        url = "/gm/api/" + "x" * 500
        _, requests, denied = self.request("anonymous", url)
        self.assertEqual(len(requests[0]["route"]), ROUTE_LABEL_LIMIT + 1)
        self.assertTrue(requests[0]["route"].startswith("/gm/api/xxx"))
        self.assertEqual(denied[0]["route"], requests[0]["route"])

    @covers_requirement(
        "gm-portal-access-api::facade-request-and-denial-events",
    )
    def test_event_context_carries_no_cookie_or_token_values(self):
        client = self.client_for("developer")
        client.get("/gm/")
        secrets = [morsel.value for morsel in client.cookies.values()]
        _, requests, _ = self.request("developer", "/gm/api/session", client=client)
        rendered = json.dumps(requests)
        for secret in secrets:
            self.assertNotIn(secret, rendered)

    @covers_requirement(
        "gm-portal-access-api::facade-request-and-denial-events",
    )
    def test_gm_modules_never_enter_the_observability_freeze_list(self):
        frozen = json.loads((REPO_ROOT / "tools/observability_freeze.json").read_text())
        flat = json.dumps(frozen)
        self.assertNotIn("web/gm", flat)
        self.assertNotIn("web.gm", flat)
