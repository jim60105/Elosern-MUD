"""CSRF convention for GM writes, exercised with real CSRF enforcement.

Uses a test-only protected POST view (``csrf_urls``); access precedence is
anonymous 401 and unauthorized 403 before token validation, permitted
accounts get the ``csrf_failed`` envelope for missing/invalid tokens, and the
matching ``X-CSRFToken`` header is accepted. Non-GM CSRF failures keep
Django's stock page.
"""

from __future__ import annotations

from unittest import mock

from django.conf import settings
from django.shortcuts import resolve_url
from django.test import override_settings

from web.gm.tests._support import GmTestCase

WRITE_URL = "/gm/api/_test/write"


@override_settings(ROOT_URLCONF="web.gm.tests.csrf_urls")
class GmCsrfConventionTest(GmTestCase):
    def enforced(self, kind):
        client = self.client_for(kind, enforce_csrf_checks=True)
        token = None
        if kind in ("developer", "superuser"):
            response = client.get("/gm/")
            token = response.cookies[settings.CSRF_COOKIE_NAME].value
        return client, token

    def gm_requests(self, log_info):
        return [c for c in log_info.call_args_list if c.args[0] == "gm_request"]

    def test_permitted_post_without_or_with_invalid_token_is_csrf_failed(self):
        client, token = self.enforced("developer")
        for headers in ({}, {"HTTP_X_CSRFTOKEN": "x" * len(token)}):
            with self.subTest(headers=bool(headers)), \
                    mock.patch("web.gm.middleware.log_info") as log_info:
                response = client.post(WRITE_URL, data="{}", content_type="application/json",
                                       **headers)
                self.assert_error_envelope(response, 403, "csrf_failed")
                events = self.gm_requests(log_info)
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0].kwargs["context"]["status"], 403)

    def test_permitted_post_with_matching_token_succeeds(self):
        client, token = self.enforced("developer")
        with mock.patch("web.gm.middleware.log_info") as log_info:
            response = client.post(WRITE_URL, data="{}", content_type="application/json",
                                   HTTP_X_CSRFTOKEN=token)
        self.assertEqual(self.assert_ok_envelope(response), {"accepted": True})
        self.assertEqual(self.gm_requests(log_info)[0].kwargs["context"]["status"], 200)

    def test_anonymous_post_is_401_before_token_validation(self):
        client, _ = self.enforced("anonymous")
        for headers in ({}, {"HTTP_X_CSRFTOKEN": "a" * 32}):
            with self.subTest(headers=bool(headers)), \
                    mock.patch("web.gm.middleware.log_info") as log_info, \
                    mock.patch("web.gm.access.log_warn") as log_warn:
                response = client.post(WRITE_URL, **headers)
                self.assert_error_envelope(response, 401, "unauthenticated")
                events = self.gm_requests(log_info)
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0].kwargs["context"]["status"], 401)
                self.assertEqual(log_warn.call_args.args[0], "gm_denied")
                self.assertEqual(log_warn.call_args.kwargs["context"]["account"], "anonymous")

    def test_unauthorized_post_is_403_forbidden_before_token_validation(self):
        client, _ = self.enforced("player")
        response = client.post(WRITE_URL)
        self.assert_error_envelope(response, 403, "forbidden")

    def test_non_gm_csrf_failure_keeps_the_stock_page(self):
        client, _ = self.enforced("anonymous")
        response = client.post(resolve_url(settings.LOGIN_URL), {"username": "x"})
        self.assertEqual(response.status_code, 403)
        self.assertNotEqual(response.get("Content-Type"), "application/json")
        self.assertNotIn(b"csrf_failed", response.content)

    def test_logout_through_the_project_flow_uses_the_cookie_token(self):
        client, token = self.enforced("developer")
        response = client.post(resolve_url(settings.LOGOUT_URL),
                               {"csrfmiddlewaretoken": token})
        self.assertIn(response.status_code, (200, 302))
        self.assert_error_envelope(client.get("/gm/api/session"), 401, "unauthenticated")
