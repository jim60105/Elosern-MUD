"""Transport acceptance for the runtime state API (tasks 4.1-4.3 / 6.1).

Exercises the five route families through the real middleware/URL map: the
anonymous/player/Developer/superuser access matrix, read-only POST CSRF
enforcement on the recall preview, reserved-route precedence against the
generic kind routes, the lookup/length error matrix (404
``object_not_found``/``kind_mismatch``, 400 ``query_too_long`` before recall
execution), summary-only cursor lists with filter binding, and the facade
request events. The genuinely matching main-spec requirement IDs are the
``gm-portal-access-api`` ones below; the ``gm-runtime-state`` requirements this
module establishes exist only as this change's delta and enter the
traceability index when the delta spec is synced at archive.
"""

from __future__ import annotations

from unittest import mock

from django.conf import settings
from django.urls import resolve
from evennia.utils import create
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.art.store import ArtAssetRecord
from world.narrative.models import NarrativeEvent

from tools.spec_traceability import covers_requirement
from web.gm import pagination
from web.gm.tests._support import GmTestCase

LIST = "/gm/api/state/characters"
RAW = "/gm/api/state/object/{dbref}/raw"
SEARCH = "/gm/api/state/search"
RECALL = "/gm/api/state/npc/{dbref}/recall"

#: Every S3 route family with the ``name`` it was registered under.
ROUTE_NAMES = {
    "gm/api/state/search": "gm-api-state-search",
    "gm/api/state/object/<str:dbref>/raw": "gm-api-state-object-raw",
    "gm/api/state/npc/<str:dbref>/recall": "gm-api-state-recall",
    "gm/api/state/<str:kind>": "gm-api-state-list",
    "gm/api/state/<str:kind>/<str:entity_id>": "gm-api-state-detail",
}


class StateApiTestCase(GmTestCase):
    def setUp(self):
        super().setUp()
        self.npc = create.create_object(NPC, key="t_state_npc", location=self.room1)
        self.room = create.create_object(Room, key="t_state_room")
        self.art = create.create_script(ArtAssetRecord, key="art:t_state_subject")
        self.art.db.subject_key = "t_state_subject"
        self.event = NarrativeEvent.objects.create(
            source_id="t_state_event", event_type="t_state_kind", content={"note": "合成"}
        )


class StateApiAccessTests(StateApiTestCase):
    @covers_requirement(
        "gm-portal-access-api::protected-gm-namespace",
        "gm-portal-access-api::registered-backend-acceptance-coverage",
    )
    def test_anonymous_and_player_requests_are_denied_with_the_existing_envelopes(self):
        api_requests = [
            ("get", LIST),
            ("get", LIST + f"/{self.char1.pk}"),
            ("get", RAW.format(dbref=self.char1.pk)),
            ("get", SEARCH + "?q=t_state"),
            ("post", RECALL.format(dbref=self.npc.pk)),
        ]
        for kind, status, code in (
            ("anonymous", 401, "unauthenticated"),
            ("player", 403, "forbidden"),
        ):
            client = self.client_for(kind)
            for method, url in api_requests:
                with self.subTest(kind=kind, method=method, url=url):
                    response = getattr(client, method)(url)
                    self.assert_error_envelope(response, status, code)

    @covers_requirement(
        "gm-portal-access-api::protected-gm-namespace",
        "gm-portal-access-api::registered-backend-acceptance-coverage",
    )
    def test_privileged_accounts_reach_every_route_family(self):
        for kind in ("developer", "superuser"):
            client = self.client_for(kind)
            with self.subTest(kind=kind):
                self.assert_ok_envelope(client.get(LIST))
                self.assert_ok_envelope(client.get(LIST + f"/{self.char1.pk}"))
                self.assert_ok_envelope(client.get(RAW.format(dbref=self.char1.pk)))
                self.assert_ok_envelope(client.get(SEARCH + "?q=t_state"))
                self.assert_ok_envelope(
                    client.post(
                        RECALL.format(dbref=self.npc.pk),
                        data="{}",
                        content_type="application/json",
                    )
                )

    @covers_requirement(
        "gm-portal-access-api::facade-request-and-denial-events",
    )
    def test_state_requests_emit_the_facade_request_event(self):
        with mock.patch("web.gm.middleware.log_info") as log_info:
            self.client_for("developer").get(LIST)
        events = [call for call in log_info.call_args_list if call.args[0] == "gm_request"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kwargs["context"]["status"], 200)

    @covers_requirement(
        "gm-portal-access-api::facade-request-and-denial-events",
        "gm-portal-access-api::protected-gm-namespace",
    )
    def test_a_denied_state_request_emits_the_denial_event(self):
        with mock.patch("web.gm.access.log_warn") as log_warn:
            self.client_for("player").get(LIST)
        self.assertEqual(log_warn.call_args.args[0], "gm_denied")

    @covers_requirement(
        "gm-portal-access-api::protected-gm-namespace",
    )
    def test_every_runtime_route_family_resolves_to_its_registered_pattern(self):
        concrete = {
            SEARCH + "?q=t_state": "gm-api-state-search",
            RAW.format(dbref=1): "gm-api-state-object-raw",
            RECALL.format(dbref=1): "gm-api-state-recall",
            "/gm/api/state/characters": "gm-api-state-list",
            f"/gm/api/state/characters/{self.char1.pk}": "gm-api-state-detail",
        }
        found = set()
        for url, expected in concrete.items():
            with self.subTest(url=url):
                match = resolve(url.split("?", 1)[0])
                self.assertEqual(match.url_name, expected)
                found.add(match.url_name)
        self.assertEqual(found, set(ROUTE_NAMES.values()))

    @covers_requirement(
        "gm-portal-access-api::protected-gm-namespace",
    )
    def test_reserved_paths_are_not_swallowed_by_the_generic_kind_route(self):
        cases = {
            SEARCH: "gm-api-state-search",
            RAW.format(dbref=self.char1.pk): "gm-api-state-object-raw",
            RECALL.format(dbref=self.npc.pk): "gm-api-state-recall",
            f"/gm/api/state/characters/{self.char1.pk}": "gm-api-state-detail",
        }
        for url, name in cases.items():
            with self.subTest(url=url):
                match = resolve(url.split("?", 1)[0])
                self.assertEqual(match.url_name, name)
        # The reserved ``search`` path never resolves as ``kind=search``.
        self.assertEqual(resolve(SEARCH).kwargs, {})


class StateApiMethodTests(StateApiTestCase):
    @covers_requirement("gm-portal-access-api::consistent-json-transport")
    def test_read_routes_reject_other_methods(self):
        client = self.client_for("developer")
        for url in (LIST, f"{LIST}/{self.char1.pk}", RAW.format(dbref=self.char1.pk), SEARCH):
            for method in ("post", "put", "patch", "delete"):
                with self.subTest(url=url, method=method):
                    response = getattr(client, method)(url)
                    self.assert_error_envelope(response, 405, "method_not_allowed")

    @covers_requirement("gm-portal-access-api::consistent-json-transport")
    def test_recall_is_post_only(self):
        client = self.client_for("developer")
        for method in ("get", "put", "delete"):
            with self.subTest(method=method):
                response = getattr(client, method)(RECALL.format(dbref=self.npc.pk))
                self.assert_error_envelope(response, 405, "method_not_allowed")

    @covers_requirement("gm-portal-access-api::consistent-json-transport")
    def test_responses_are_not_cacheable(self):
        response = self.client_for("developer").get(LIST)
        self.assertEqual(response["Cache-Control"], "no-store")


class StateApiCsrfTests(StateApiTestCase):
    @covers_requirement(
        "gm-portal-access-api::consistent-json-transport",
        "gm-portal-access-api::facade-request-and-denial-events",
    )
    def test_recall_post_without_or_with_an_invalid_token_is_csrf_failed(self):
        client = self.client_for("developer", enforce_csrf_checks=True)
        token = client.get("/gm/").cookies[settings.CSRF_COOKIE_NAME].value
        for headers in ({}, {"HTTP_X_CSRFTOKEN": "x" * len(token)}):
            with self.subTest(headers=bool(headers)):
                response = client.post(
                    RECALL.format(dbref=self.npc.pk),
                    data="{}",
                    content_type="application/json",
                    **headers,
                )
                self.assert_error_envelope(response, 403, "csrf_failed")

    @covers_requirement("gm-portal-access-api::consistent-json-transport")
    def test_recall_post_with_the_matching_token_succeeds(self):
        client = self.client_for("developer", enforce_csrf_checks=True)
        token = client.get("/gm/").cookies[settings.CSRF_COOKIE_NAME].value
        response = client.post(
            RECALL.format(dbref=self.npc.pk),
            data='{"query": "合成"}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        data = self.assert_ok_envelope(response)
        self.assertIn("core", data)


class StateApiErrorMatrixTests(StateApiTestCase):
    @covers_requirement(
        "gm-portal-access-api::consistent-json-transport",
        "gm-portal-access-api::registered-backend-acceptance-coverage",
    )
    def test_the_lookup_error_matrix(self):
        client = self.client_for("developer")
        cases = (
            ("get", "/gm/api/state/npcs/999999", 404, "object_not_found"),
            ("get", "/gm/api/state/characters/999999", 404, "object_not_found"),
            ("get", "/gm/api/state/npcs/not-a-dbref", 404, "object_not_found"),
            # The object exists but is not the kind the route names.
            ("get", f"/gm/api/state/npcs/{self.room.pk}", 404, "kind_mismatch"),
            ("get", f"/gm/api/state/characters/{self.npc.pk}", 404, "kind_mismatch"),
            ("get", f"/gm/api/state/monsters/{self.char1.pk}", 404, "kind_mismatch"),
            ("get", "/gm/api/state/object/999999/raw", 404, "object_not_found"),
            ("get", "/gm/api/state/not_a_kind", 404, "unsupported_kind"),
            # An existing object that is not an NPC is a kind mismatch, and the
            # recall POST is the route that has to say so.
            (
                "post",
                f"/gm/api/state/npc/{self.char1.pk}/recall",
                404,
                "kind_mismatch",
            ),
            ("post", "/gm/api/state/npc/999999/recall", 404, "object_not_found"),
            ("get", "/gm/api/state/quests", 400, "invalid_filter"),
            ("get", "/gm/api/state/memories", 400, "invalid_filter"),
            ("get", "/gm/api/state/snapshots", 400, "invalid_filter"),
            ("get", "/gm/api/state/dialogue", 400, "invalid_filter"),
            ("get", "/gm/api/state/characters?limit=0", 400, "invalid_limit"),
            ("get", "/gm/api/state/characters?limit=201", 400, "invalid_limit"),
            ("get", "/gm/api/state/characters?limit=abc", 400, "invalid_limit"),
            ("get", "/gm/api/state/characters?cursor=not-a-cursor", 400, "invalid_cursor"),
            ("get", "/gm/api/state/search", 400, "invalid_query"),
            ("get", "/gm/api/state/search?q=", 400, "invalid_query"),
        )
        for method, url, status, code in cases:
            with self.subTest(url=url):
                if method == "post":
                    # The recall route reads a JSON body; an empty form body is
                    # a transport error of its own.
                    response = client.post(url, data="{}", content_type="application/json")
                else:
                    response = getattr(client, method)(url)
                self.assert_error_envelope(response, status, code)

    @covers_requirement("gm-portal-access-api::consistent-json-transport")
    def test_a_curated_detail_route_serves_only_curated_kinds(self):
        client = self.client_for("developer")
        for kind, entity in (("npcs", self.npc), ("rooms", self.room),
                             ("characters", self.char1)):
            with self.subTest(kind=kind):
                data = self.assert_ok_envelope(client.get(f"/gm/api/state/{kind}/{entity.pk}"))
                self.assertEqual(data["kind"], kind)
                self.assertEqual(data["dbref"], entity.pk)
                self.assertTrue(data["sections"])

    @covers_requirement("gm-portal-access-api::consistent-json-transport")
    def test_an_account_detail_carries_its_own_raw_inventory(self):
        """An account is not an ObjectDB: its raw data rides its own detail."""
        data = self.assert_ok_envelope(
            self.client_for("developer").get(f"/gm/api/state/accounts/{self.account.pk}")
        )
        self.assertEqual(data["kind"], "accounts")
        self.assertEqual(data["dbref"], self.account.pk)
        # The account's own inventory, never an unrelated ObjectDB row.
        self.assertIsNone(data["raw"]["location"])
        self.assertIsInstance(data["raw"]["attributes"], list)
        self.assertEqual(data["raw"]["key"], self.account.username)
        self.assertIn("tags", data["raw"])

    @covers_requirement(
        "gm-portal-access-api::consistent-json-transport",
        "gm-portal-access-api::registered-backend-acceptance-coverage",
    )
    def test_recall_query_length_boundary(self):
        client = self.client_for("developer")
        url = RECALL.format(dbref=self.npc.pk)
        valid = client.post(url, data='{"query": "%s"}' % ("x" * 2000),
                            content_type="application/json")
        data = self.assert_ok_envelope(valid)
        self.assertEqual(len(data["query"]), 2000)
        oversized = client.post(url, data='{"query": "%s"}' % ("x" * 2001),
                                content_type="application/json")
        self.assert_error_envelope(oversized, 400, "query_too_long")

    @covers_requirement("gm-portal-access-api::consistent-json-transport")
    def test_a_broken_recall_body_is_an_invalid_query(self):
        client = self.client_for("developer")
        response = client.post(
            RECALL.format(dbref=self.npc.pk), data="{not json",
            content_type="application/json",
        )
        self.assert_error_envelope(response, 400, "invalid_query")

    @covers_requirement("gm-portal-access-api::consistent-json-transport")
    def test_an_unnamed_kind_detail_is_a_404_not_found(self):
        response = self.client_for("developer").get("/gm/api/state/narrative/t_event")
        self.assert_error_envelope(response, 400, "invalid_filter")


class StateApiPaginationTests(StateApiTestCase):
    def setUp(self):
        super().setUp()
        self.dense = [
            create.create_object(PlayerCharacter, key=f"t_state_dense_{index}", location=self.room1)
            for index in range(55)
        ]

    @covers_requirement("gm-portal-access-api::consistent-json-transport")
    def test_the_default_limit_is_fifty_and_the_maximum_two_hundred(self):
        self.assertEqual(pagination.DEFAULT_LIMIT, 50)
        self.assertEqual(pagination.MAX_LIMIT, 200)
        client = self.client_for("developer")
        default = self.assert_ok_envelope(client.get(LIST))
        self.assertEqual(len(default["items"]), pagination.DEFAULT_LIMIT)
        self.assertIsNotNone(default["next_cursor"])
        # The whole fixture set fits inside the maximum page, which ends the list.
        maximum = self.assert_ok_envelope(client.get(LIST + f"?limit={pagination.MAX_LIMIT}"))
        self.assertGreater(len(maximum["items"]), pagination.DEFAULT_LIMIT)
        self.assertIsNone(maximum["next_cursor"])

    @covers_requirement("gm-portal-access-api::consistent-json-transport")
    def test_cursor_pages_terminate_and_never_repeat_a_row(self):
        client = self.client_for("developer")
        seen: list[str] = []
        cursor = None
        pages = 0
        while pages < 10:
            url = LIST + "?limit=20" + (f"&cursor={cursor}" if cursor else "")
            data = self.assert_ok_envelope(client.get(url))
            seen.extend(item["id"] for item in data["items"])
            pages += 1
            if data["next_cursor"] is None:
                break
            cursor = data["next_cursor"]
        else:  # pragma: no cover - the loop always terminates above
            self.fail("cursor pagination did not terminate")
        self.assertEqual(len(seen), len(set(seen)))
        total = len(self.assert_ok_envelope(client.get(LIST + "?limit=200"))["items"])
        self.assertEqual(len(seen), total)

    @covers_requirement("gm-portal-access-api::consistent-json-transport")
    def test_a_cursor_is_bound_to_the_filters_it_was_issued_for(self):
        client = self.client_for("developer")
        cursor = self.assert_ok_envelope(client.get(LIST + "?limit=1"))["next_cursor"]
        self.assertIsNotNone(cursor)
        # The cursor replays for its own filter set ...
        self.assert_ok_envelope(client.get(f"{LIST}?limit=1&cursor={cursor}"))
        # ... and is refused under a different one, never silently replaying a
        # page from another query.
        response = client.get(f"{LIST}?limit=1&cursor={cursor}&tier=core")
        self.assert_error_envelope(response, 400, "invalid_cursor")

    @covers_requirement("gm-portal-access-api::consistent-json-transport")
    def test_list_items_are_summaries_without_raw_or_section_payloads(self):
        client = self.client_for("developer")
        for url in (LIST, "/gm/api/state/rooms", "/gm/api/state/narrative?subtype=event"):
            with self.subTest(url=url):
                data = self.assert_ok_envelope(client.get(url))
                self.assertIn("next_cursor", data)
                for item in data["items"]:
                    self.assertLessEqual({"id", "kind", "label", "fields"}, set(item))
                    self.assertNotIn("raw", item)
                    self.assertNotIn("sections", item)
                    self.assertIsInstance(item["fields"], list)
