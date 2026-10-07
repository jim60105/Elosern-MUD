"""GM namespace access matrix and URL-resolver protection contract.

Covers anonymous, ordinary player, Developer, and superuser accounts against
the shell, a history path, both S1 APIs, and unknown API paths, plus the
contract that every resolved GM pattern is wrapped by ``gm_required``.
"""

from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from django.shortcuts import resolve_url
from django.urls import URLPattern, URLResolver, get_resolver, include, path, resolve

from web.gm.access import PROTECTED_MARKER, is_gm_path
from tools.spec_traceability import covers_requirement
from web.gm.tests._support import GmTestCase

PAGES = ("/gm/", "/gm/some/history/path")
READ_APIS = ("/gm/api/session", "/gm/api/dashboard")
DETAIL_API = "/gm/api/llm/calls/" + "0" * 32
APIS = READ_APIS + (DETAIL_API,)
# /gm/api/health was removed with no alias (gm-portal-s2b-dashboard).
UNKNOWN_APIS = ("/gm/api/missing", "/gm/api", "/gm/api/", "/gm/api/session/", "/gm/api/health")


def gm_patterns(patterns, prefix=""):
    """Yield ``(route, callback)`` for every pattern mounted under ``gm/``."""
    for entry in patterns:
        route = prefix + str(entry.pattern)
        if isinstance(entry, URLResolver):
            yield from gm_patterns(entry.url_patterns, route)
        elif isinstance(entry, URLPattern) and route.startswith("gm/"):
            yield route, entry.callback


def unprotected(patterns):
    return sorted(
        route
        for route, callback in gm_patterns(patterns)
        if not getattr(callback, PROTECTED_MARKER, False)
    )


class GmPageAccessTest(GmTestCase):
    @covers_requirement(
        "gm-portal-access-api::protected-gm-namespace",
        "gm-portal-access-api::registered-backend-acceptance-coverage",
    )
    def test_anonymous_pages_redirect_to_login_with_next(self):
        client = self.client_for("anonymous")
        login = resolve_url(settings.LOGIN_URL)
        for page in PAGES + ("/gm/some/history/path?tab=1",):
            with self.subTest(page=page):
                response = client.get(page)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response["Location"], f"{login}?next={quote(page, safe='/')}")

    @covers_requirement(
        "gm-portal-access-api::protected-gm-namespace",
        "gm-portal-access-api::registered-backend-acceptance-coverage",
    )
    def test_ordinary_account_gets_403_page_even_with_staff_flag(self):
        for staff in (False, True):
            self.account2.is_staff = staff
            self.account2.save()
            client = self.client_for("player")
            for page in PAGES:
                with self.subTest(page=page, staff=staff):
                    response = client.get(page)
                    self.assertEqual(response.status_code, 403)
                    self.assertContains(response, "權限不足", status_code=403)
                    self.assertNotContains(response, "gm/dist/index.js", status_code=403)

    @covers_requirement(
        "gm-portal-access-api::protected-gm-namespace",
        "gm-portal-access-api::registered-backend-acceptance-coverage",
    )
    def test_privileged_accounts_receive_the_shell_independent_of_staff(self):
        self.assertFalse(self.account.is_staff)
        for kind in ("developer", "superuser"):
            client = self.client_for(kind)
            for page in PAGES:
                with self.subTest(kind=kind, page=page):
                    response = client.get(page)
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, 'id="gm-app"')

    @covers_requirement(
        "gm-portal-access-api::protected-gm-namespace",
    )
    def test_slashless_mount_never_serves_the_shell(self):
        response = self.client_for("anonymous").get("/gm")
        self.assertNotEqual(response.status_code, 200)
        self.assertNotIn(b'id="gm-app"', response.content)


class GmApiAccessTest(GmTestCase):
    @covers_requirement(
        "gm-portal-access-api::protected-gm-namespace",
        "gm-portal-access-api::consistent-json-transport",
        "gm-portal-access-api::registered-backend-acceptance-coverage",
    )
    def test_anonymous_api_requests_get_401_envelope_not_redirect(self):
        client = self.client_for("anonymous")
        for url in APIS + UNKNOWN_APIS:
            with self.subTest(url=url):
                self.assert_error_envelope(client.get(url), 401, "unauthenticated")

    @covers_requirement(
        "gm-portal-access-api::protected-gm-namespace",
        "gm-portal-access-api::consistent-json-transport",
        "gm-portal-access-api::registered-backend-acceptance-coverage",
    )
    def test_ordinary_account_api_requests_get_403_envelope(self):
        self.account2.is_staff = True
        self.account2.save()
        client = self.client_for("player")
        for url in APIS + UNKNOWN_APIS:
            with self.subTest(url=url):
                self.assert_error_envelope(client.get(url), 403, "forbidden")

    @covers_requirement(
        "gm-portal-access-api::protected-gm-namespace",
        "gm-portal-access-api::registered-backend-acceptance-coverage",
    )
    @covers_requirement('gm-operations-dashboard::landed-foundation-and-transcript-prerequisites')
    def test_privileged_accounts_reach_every_api(self):
        for kind in ("developer", "superuser"):
            client = self.client_for(kind)
            for url in READ_APIS:
                with self.subTest(kind=kind, url=url):
                    self.assert_ok_envelope(client.get(url))
            with self.subTest(kind=kind, url=DETAIL_API):
                # Reaching the view: test settings disable transcripts (409).
                self.assert_error_envelope(client.get(DETAIL_API), 409, "transcript_disabled")

    @covers_requirement(
        "gm-portal-access-api::s1-route-and-payload-scope",
        "gm-portal-access-api::consistent-json-transport",
    )
    def test_unknown_api_paths_return_404_envelope_not_the_shell(self):
        client = self.client_for("developer")
        for url in UNKNOWN_APIS:
            with self.subTest(url=url):
                response = client.get(url)
                self.assert_error_envelope(response, 404, "not_found")
                self.assertNotIn(b'id="gm-app"', response.content)


class GmResolverCoverageTest(GmTestCase):
    """Every resolved GM view carries the ``gm_required`` marker.

    The marker proves the decorator was applied at registration; the
    boundary middleware denies before any view runs, so this is the
    registration-level half of a defence in depth.
    """

    @covers_requirement(
        "gm-portal-access-api::protected-gm-namespace",
        "gm-portal-access-api::registered-backend-acceptance-coverage",
    )
    def test_every_mounted_gm_pattern_is_protected(self):
        routes = dict(gm_patterns(get_resolver().url_patterns))
        self.assertEqual(unprotected(get_resolver().url_patterns), [])
        # The fallbacks are present (and therefore covered) too.
        self.assertNotIn("gm/api/health", routes)
        for expected in ("gm/api/session", "gm/api/dashboard", "gm/api/llm/calls/<str:call_id>",
                         "gm/api", "gm/api/",
                         "gm/api/<path:rest>", "gm/", "gm/<path:rest>"):
            self.assertIn(expected, routes)

    @covers_requirement(
        "gm-portal-access-api::protected-gm-namespace",
    )
    def test_contract_detects_an_unwrapped_gm_pattern(self):
        def bare_view(request):
            return None

        synthetic = [path("gm/", include([path("api/new", bare_view), path("x", bare_view)]))]
        self.assertEqual(unprotected(synthetic), ["gm/api/new", "gm/x"])

    @covers_requirement(
        "gm-portal-access-api::protected-gm-namespace",
    )
    def test_every_gm_path_resolves_into_the_protected_gm_map(self):
        for url in PAGES + APIS + UNKNOWN_APIS:
            with self.subTest(url=url):
                self.assertTrue(is_gm_path(url))
                match = resolve(url.split("?", 1)[0])
                self.assertTrue(getattr(match.func, PROTECTED_MARKER, False))
                self.assertEqual(match.func.__module__, "web.gm.views")
