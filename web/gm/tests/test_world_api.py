"""Transport acceptance for the authored world-data API (gm-portal-s4-world-data).

Every registry read runs against a small synthetic index patched over
``world.lore.registry_index.REGISTRY_INDEX`` (no shipped registry is read), and
every source read runs against a temporary game directory, so the assertions
are about the transport contract: the access matrix on every page and API,
envelopes and the 404 codes, stable key pagination bound to the query,
cross-registry search, entry details with forward and inverse references, the
request-time source allowlist and its escape rejections, the CSRF-protected
prompt reload with its diagnostics and facade events, and that none of it
writes persistent state or source files, with or without network access.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from unittest import mock

from django.conf import settings
from django.test import Client, override_settings
from evennia.objects.models import ObjectDB
from evennia.scripts.models import ScriptDB
from evennia.typeclasses.attributes import Attribute
from evennia.typeclasses.tags import Tag

from web.gm import pagination, world_api
from web.gm.readers import world as world_reader
from web.gm.tests._support import GmTestCase
from world.lore import registry_index
from world.lore.registry_index import RegistrySpec
from world.lore.registry_refs import ref, ref_many
from world.prompts.loader import PromptLibrary, PromptLibraryError, reset_prompt_library


@dataclass(frozen=True)
class Hollow:
    key: str
    display_name_zh: str
    depth: int = 1


@dataclass(frozen=True)
class Marking:
    note: str
    hollow_key: str | None = field(default=None, metadata=ref("t_hollows", inverse="marked_by", nullable=True))


@dataclass(frozen=True)
class Critter:
    key: str
    display_name_zh: str
    home_key: str = field(metadata=ref("t_hollows", inverse="residents"))
    roams: tuple[str, ...] = field(default=(), metadata=ref_many("t_hollows", inverse="roamers"))
    markings: tuple[Marking, ...] = ()


@dataclass(frozen=True)
class Trinket:
    label_text: str
    weight: float


HOLLOWS = {
    "t_hollow_east": Hollow("t_hollow_east", "東窪", depth=3),
    "t_hollow_west": Hollow("t_hollow_west", "西窪"),
}
CRITTERS = {
    f"t_critter_{index:02d}": Critter(f"t_critter_{index:02d}", f"小獸{index:02d}", home_key="t_hollow_east")
    for index in range(60)
}
CRITTERS["t_marked"] = Critter(
    "t_marked",
    "斑紋獸",
    home_key="t_hollow_west",
    roams=("t_hollow_east", "t_hollow_west"),
    markings=(Marking("銀色月光的紋路", hollow_key="t_hollow_east"),),
)
CRITTERS["t_lost"] = Critter("t_lost", "迷途獸", home_key="t_hollow_gone")
TRINKETS = {"t_trinket_moon": Trinket("月光小飾", 0.5)}


def _spec(name, label, group, rows, *summary):
    view = MappingProxyType(rows)
    return RegistrySpec(name, label, group, lambda: view, f"fixtures/{name}.py", tuple(summary))


INDEX = (
    _spec("t_critters", "合成小獸", "生物", CRITTERS, "display_name_zh", "home_key"),
    _spec("t_hollows", "合成窪地", "世界", HOLLOWS),
    _spec("t_trinkets", "合成飾品", "物品與經濟", TRINKETS),
)

REGISTRY = "/gm/api/registry"
SOURCES = "/gm/api/sources"
RELOAD = "/gm/api/sources/prompts/reload"


def _data(response):
    return json.loads(response.content)["data"]


class WorldApiTestCase(GmTestCase):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(registry_index, "REGISTRY_INDEX", INDEX)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.developer = self.client_for("developer")


class RegistryApiTest(WorldApiTestCase):
    def test_inventory_lists_every_registry_grouped_with_metadata(self):
        for path in (REGISTRY, f"{REGISTRY}/"):
            with self.subTest(path=path):
                data = self.assert_ok_envelope(self.developer.get(path))
                self.assertEqual(data["groups"], list(registry_index.GROUPS))
                self.assertEqual(
                    [(item["name"], item["group"], item["entry_count"]) for item in data["items"]],
                    [("t_hollows", "世界", 2), ("t_critters", "生物", 62), ("t_trinkets", "物品與經濟", 1)],
                )
                critters = data["items"][1]
                self.assertEqual(critters["label"], "合成小獸")
                self.assertEqual(critters["source_path"], "fixtures/t_critters.py")
                self.assertEqual(critters["summary_fields"], ["display_name_zh", "home_key"])
                # No declared summary: the first string field other than the key.
                self.assertEqual(data["items"][0]["summary_fields"], ["display_name_zh"])
                self.assertEqual(data["items"][2]["summary_fields"], ["label_text"])

    def test_entry_list_pages_in_key_order_with_default_and_maximum_limits(self):
        first = self.assert_ok_envelope(self.developer.get(f"{REGISTRY}/t_critters"))
        self.assertEqual(len(first["items"]), pagination.DEFAULT_LIMIT)
        keys = [item["key"] for item in first["items"]]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(first["items"][0]["label"], "小獸00")
        self.assertEqual(
            first["items"][0]["summary"],
            [{"field": "display_name_zh", "value": "小獸00"}, {"field": "home_key", "value": "t_hollow_east"}],
        )
        self.assertEqual(first["registry"]["name"], "t_critters")
        self.assertEqual(first["total"], 62)
        second = self.assert_ok_envelope(
            self.developer.get(f"{REGISTRY}/t_critters", {"cursor": first["next_cursor"]})
        )
        self.assertEqual(len(second["items"]), 12)
        self.assertIsNone(second["next_cursor"])
        self.assertEqual(sorted(keys + [item["key"] for item in second["items"]]), sorted(CRITTERS))
        everything = self.assert_ok_envelope(self.developer.get(f"{REGISTRY}/t_critters", {"limit": "200"}))
        self.assertEqual(len(everything["items"]), 62)
        self.assert_error_envelope(
            self.developer.get(f"{REGISTRY}/t_critters", {"limit": "201"}), 400, "invalid_limit"
        )
        self.assert_error_envelope(
            self.developer.get(f"{REGISTRY}/t_critters", {"cursor": "%%%"}), 400, "invalid_cursor"
        )

    def test_entry_list_query_filters_nested_strings_and_binds_the_cursor(self):
        nested = self.assert_ok_envelope(self.developer.get(f"{REGISTRY}/t_critters", {"q": "銀色月光"}))
        self.assertEqual([item["key"] for item in nested["items"]], ["t_marked"])
        self.assertEqual(nested["q"], "銀色月光")
        paged = self.assert_ok_envelope(
            self.developer.get(f"{REGISTRY}/t_critters", {"q": "CRITTER_", "limit": "25"})
        )
        self.assertEqual(len(paged["items"]), 25)
        follow = self.assert_ok_envelope(
            self.developer.get(
                f"{REGISTRY}/t_critters", {"q": "CRITTER_", "limit": "25", "cursor": paged["next_cursor"]}
            )
        )
        self.assertTrue(all(item["key"].startswith("t_critter_") for item in follow["items"]))
        self.assert_error_envelope(
            self.developer.get(f"{REGISTRY}/t_critters", {"q": "t_", "cursor": paged["next_cursor"]}),
            400,
            "invalid_cursor",
        )
        self.assert_error_envelope(
            self.developer.get(f"{REGISTRY}/t_critters", {"q": "x" * 201}), 400, "invalid_query"
        )

    def test_cross_registry_search_returns_every_match_sorted_without_paging(self):
        data = self.assert_ok_envelope(self.developer.get(f"{REGISTRY}/", {"q": "月光"}))
        self.assertEqual(
            data,
            {"items": [{"registry": "t_critters", "key": "t_marked"}, {"registry": "t_trinkets", "key": "t_trinket_moon"}]},
        )
        many = self.assert_ok_envelope(self.developer.get(REGISTRY, {"q": "t_"}))
        self.assertEqual(len(many["items"]), 65)
        self.assertNotIn("next_cursor", many)
        self.assertEqual(
            [(item["registry"], item["key"]) for item in many["items"]],
            sorted((item["registry"], item["key"]) for item in many["items"]),
        )
        empty = self.assert_ok_envelope(self.developer.get(REGISTRY, {"q": "沒有這個字"}))
        self.assertEqual(empty, {"items": []})

    def test_entry_detail_carries_fields_references_and_grouped_referrers(self):
        marked = self.assert_ok_envelope(self.developer.get(f"{REGISTRY}/t_critters/t_marked"))
        self.assertEqual(marked["label"], "斑紋獸")
        self.assertEqual(
            marked["fields"],
            {
                "key": "t_marked",
                "display_name_zh": "斑紋獸",
                "home_key": "t_hollow_west",
                "roams": ["t_hollow_east", "t_hollow_west"],
                "markings": [{"note": "銀色月光的紋路", "hollow_key": "t_hollow_east"}],
            },
        )
        self.assertEqual(
            [(item["field_path"], item["registry"], item["key"], item["exists"]) for item in marked["references"]],
            [
                ("home_key", "t_hollows", "t_hollow_west", True),
                ("roams[0]", "t_hollows", "t_hollow_east", True),
                ("roams[1]", "t_hollows", "t_hollow_west", True),
                ("markings[0].hollow_key", "t_hollows", "t_hollow_east", True),
            ],
        )
        self.assertEqual(marked["references"][0]["label"], "西窪")
        self.assertEqual(marked["referrers"], [])
        east = self.assert_ok_envelope(self.developer.get(f"{REGISTRY}/t_hollows/t_hollow_east"))
        groups = {group["inverse"]: group["items"] for group in east["referrers"]}
        self.assertEqual(sorted(groups), ["marked_by", "residents", "roamers"])
        self.assertEqual(len(groups["residents"]), 60)
        self.assertEqual(
            groups["marked_by"],
            [
                {
                    "registry": "t_critters",
                    "registry_label": "合成小獸",
                    "key": "t_marked",
                    "label": "斑紋獸",
                    "field_path": "markings[0].hollow_key",
                }
            ],
        )
        lost = self.assert_ok_envelope(self.developer.get(f"{REGISTRY}/t_critters/t_lost"))
        self.assertEqual(
            lost["references"][0] | {"label": None},
            {
                "field_path": "home_key",
                "registry": "t_hollows",
                "registry_label": "合成窪地",
                "key": "t_hollow_gone",
                "label": None,
                "exists": False,
                "inverse": "residents",
            },
        )
        trinket = self.assert_ok_envelope(self.developer.get(f"{REGISTRY}/t_trinkets/t_trinket_moon"))
        self.assertEqual(trinket["fields"], {"label_text": "月光小飾", "weight": 0.5})

    def test_unknown_registry_and_key_use_their_codes(self):
        self.assert_error_envelope(self.developer.get(f"{REGISTRY}/t_absent"), 404, "registry_not_found")
        self.assert_error_envelope(self.developer.get(f"{REGISTRY}/t_absent/t_x"), 404, "registry_not_found")
        self.assert_error_envelope(
            self.developer.get(f"{REGISTRY}/t_critters/t_absent"), 404, "entry_not_found"
        )
        self.assert_error_envelope(self.developer.get(f"{REGISTRY}/t_critters/"), 404, "not_found")

    def test_registry_routes_refuse_writes(self):
        for path in (REGISTRY, f"{REGISTRY}/t_critters", f"{REGISTRY}/t_critters/t_marked", f"{SOURCES}/"):
            with self.subTest(path=path):
                self.assert_error_envelope(self.developer.post(path), 405, "method_not_allowed")

    def test_authored_link_only_names_present_entries(self):
        self.assertEqual(
            world_reader.authored_link("t_hollows", "t_hollow_east", "東窪"),
            {"kind": "registry", "registry": "t_hollows", "id": "t_hollow_east", "label": "東窪"},
        )
        self.assertIsNone(world_reader.authored_link("t_hollows", "t_generated_only"))
        self.assertIsNone(world_reader.authored_link("t_absent", "t_hollow_east"))
        self.assertIsNone(world_reader.authored_link("t_hollows", None))


class SourceViewerTest(WorldApiTestCase):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.game = Path(temporary.name) / "game"
        self.rulebook = self.game / "world" / "rules" / "rulebook"
        (self.rulebook / "commerce").mkdir(parents=True)
        (self.game / "prompts").mkdir()
        (self.rulebook / "alpha.yaml").write_text("schema: 1\n# 註解\nvalue: 2\n", encoding="utf-8")
        (self.rulebook / "commerce" / "alpha.yaml").write_text("shops: []\n", encoding="utf-8")
        (self.game / "prompts" / "alpha.yaml").write_text("prompts: {}\n", encoding="utf-8")
        (self.rulebook / "notes.txt").write_text("not yaml\n", encoding="utf-8")
        (self.rulebook / "folder.yaml").mkdir()
        outside = Path(temporary.name) / "secret.yaml"
        outside.write_text("secret: true\n", encoding="utf-8")
        os.symlink(outside, self.rulebook / "escape.yaml")
        override = override_settings(GAME_DIR=str(self.game), PROMPT_ROOT=str(self.game / "prompts"))
        override.enable()
        self.addCleanup(override.disable)

    def test_allowlist_qualifies_names_and_is_rebuilt_per_request(self):
        data = self.assert_ok_envelope(self.developer.get(f"{SOURCES}/"))
        self.assertEqual(
            [(item["name"], item["group"], item["source_path"], item["reloadable"]) for item in data["items"]],
            [
                ("prompts/alpha.yaml", "prompts", "prompts/alpha.yaml", True),
                ("rulebook/alpha.yaml", "rulebook", "world/rules/rulebook/alpha.yaml", False),
                ("rulebook/commerce/alpha.yaml", "commerce", "world/rules/rulebook/commerce/alpha.yaml", False),
            ],
        )
        (self.rulebook / "beta.yaml").write_text("added: true\n", encoding="utf-8")
        names = [item["name"] for item in self.assert_ok_envelope(self.developer.get(SOURCES))["items"]]
        self.assertIn("rulebook/beta.yaml", names)

    def test_source_text_is_disk_content_with_provenance(self):
        data = self.assert_ok_envelope(self.developer.get(f"{SOURCES}/rulebook/alpha.yaml"))
        self.assertEqual(data["text"], "schema: 1\n# 註解\nvalue: 2\n")
        self.assertEqual(data["line_count"], 3)
        self.assertEqual(data["source_path"], "world/rules/rulebook/alpha.yaml")
        self.assertFalse(data["reloadable"])
        commerce = self.assert_ok_envelope(self.developer.get(f"{SOURCES}/rulebook/commerce/alpha.yaml"))
        self.assertEqual(commerce["text"], "shops: []\n")
        prompts = self.assert_ok_envelope(self.developer.get(f"{SOURCES}/prompts/alpha.yaml"))
        self.assertTrue(prompts["reloadable"])

    def test_escape_attempts_are_source_not_found(self):
        attempts = (
            "rulebook/escape.yaml",
            "rulebook/notes.txt",
            "rulebook/folder.yaml",
            "rulebook/missing.yaml",
            "rulebook/../../../secret.yaml",
            "rulebook/%2e%2e/%2e%2e/secret.yaml",
            "rulebook/..%2f..%2fsecret.yaml",
            "alpha.yaml",
            "commerce/alpha.yaml",
            str(self.rulebook / "alpha.yaml").lstrip("/"),
            "/etc/passwd",
            "rulebook/alpha.yaml%00",
        )
        for name in attempts:
            with self.subTest(name=name):
                self.assert_error_envelope(self.developer.get(f"{SOURCES}/{name}"), 404, "source_not_found")
        listed = [item["name"] for item in self.assert_ok_envelope(self.developer.get(SOURCES))["items"]]
        self.assertNotIn("rulebook/escape.yaml", listed)

    def test_undecodable_file_is_source_not_found(self):
        (self.rulebook / "binary.yaml").write_bytes(b"\xff\xfe\x00bad")
        self.assert_error_envelope(self.developer.get(f"{SOURCES}/rulebook/binary.yaml"), 404, "source_not_found")


class PromptReloadTest(WorldApiTestCase):
    def _csrf_client(self) -> tuple[Client, str]:
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.account)
        client.get("/gm/")
        return client, client.cookies["csrftoken"].value

    def test_reload_resets_then_loads_and_returns_diagnostics(self):
        broken = PromptLibraryError("npc.yaml", "t_prompt_key", "prompt text is empty")
        library = PromptLibrary(root=str(Path(settings.GAME_DIR) / "prompts"), texts={"t_ok": "x"}, errors={"t_prompt_key": broken})
        calls = []
        client, token = self._csrf_client()
        with (
            mock.patch.object(world_api, "reset_prompt_library", side_effect=lambda: calls.append("reset")),
            mock.patch.object(world_api, "load_prompt_library", side_effect=lambda: calls.append("load") or library),
            mock.patch.object(world_api, "log_info") as log_info,
        ):
            data = self.assert_ok_envelope(client.post(RELOAD, HTTP_X_CSRFTOKEN=token))
        self.assertEqual(calls, ["reset", "load"])
        self.assertEqual(data["outcome"], "degraded")
        self.assertEqual(data["available"], 1)
        self.assertEqual(data["root"], "prompts")
        self.assertEqual(data["unavailable"], [{"key": "t_prompt_key", "file": "npc.yaml", "problem": "prompt text is empty"}])
        events = {call.args[0]: call.kwargs["context"] for call in log_info.call_args_list}
        self.assertEqual(
            events["gm_action"],
            {"account": self.account.username, "action": "prompts_reload", "target": "prompts", "outcome": "degraded"},
        )
        self.assertEqual(events["gm_prompts_reloaded"]["outcome"], "degraded")
        self.assertEqual(events["gm_prompts_reloaded"]["unavailable"], ["t_prompt_key"])
        self.assertNotIn("x", json.dumps(events["gm_prompts_reloaded"]["unavailable"]))

    def test_real_loader_success_then_failure_follows_loader_semantics(self):
        self.addCleanup(reset_prompt_library)
        client, token = self._csrf_client()
        healthy = self.assert_ok_envelope(client.post(RELOAD, HTTP_X_CSRFTOKEN=token))
        self.assertEqual(healthy["outcome"], "ok")
        self.assertEqual(healthy["available"], healthy["total"])
        with tempfile.TemporaryDirectory() as empty, override_settings(PROMPT_ROOT=empty):
            failed = self.assert_ok_envelope(client.post(RELOAD, HTTP_X_CSRFTOKEN=token))
        self.assertEqual(failed["outcome"], "degraded")
        self.assertEqual(failed["available"], 0)
        self.assertEqual(len(failed["unavailable"]), failed["total"])

    def test_reload_requires_csrf_and_post_before_touching_the_loader(self):
        client, _token = self._csrf_client()
        with (
            mock.patch.object(world_api, "reset_prompt_library") as reset,
            mock.patch.object(world_api, "load_prompt_library") as load,
        ):
            self.assert_error_envelope(client.post(RELOAD), 403, "csrf_failed")
            self.assert_error_envelope(client.post(RELOAD, HTTP_X_CSRFTOKEN="wrong" * 8), 403, "csrf_failed")
            self.assert_error_envelope(self.developer.get(RELOAD), 405, "method_not_allowed")
        reset.assert_not_called()
        load.assert_not_called()

    def test_raised_loader_failure_is_an_envelope_and_an_event(self):
        client, token = self._csrf_client()
        with (
            mock.patch.object(world_api, "reset_prompt_library"),
            mock.patch.object(world_api, "load_prompt_library", side_effect=RuntimeError("boom")),
            mock.patch.object(world_api, "log_error") as log_error,
            mock.patch.object(world_api, "log_info") as log_info,
        ):
            self.assert_error_envelope(client.post(RELOAD, HTTP_X_CSRFTOKEN=token), 500, "prompt_reload_failed")
        self.assertEqual(log_error.call_args.args[0], "gm_prompts_reloaded")
        self.assertEqual(log_error.call_args.kwargs["context"]["outcome"], "failed")
        self.assertEqual(log_info.call_args.kwargs["context"]["outcome"], "failed")


class AccessAndBoundaryTest(WorldApiTestCase):
    API_GETS = (
        REGISTRY,
        f"{REGISTRY}/?q=t_",
        f"{REGISTRY}/t_critters",
        f"{REGISTRY}/t_critters/t_marked",
        f"{SOURCES}/",
        f"{SOURCES}/rulebook/combat.yaml",
    )
    PAGES = ("/gm/world", "/gm/world/t_critters", "/gm/world/t_critters/t_marked", "/gm/world/sources/prompts/art.yaml")

    def test_access_matrix_covers_every_page_and_api(self):
        for path in self.API_GETS:
            with self.subTest(path=path):
                self.assert_error_envelope(self.client_for("anonymous").get(path), 401, "unauthenticated")
                self.assert_error_envelope(self.client_for("player").get(path), 403, "forbidden")
                for kind in ("developer", "superuser"):
                    self.assertEqual(self.client_for(kind).get(path).status_code, 200, (kind, path))
        for kind, status in (("anonymous", 401), ("player", 403)):
            self.assert_error_envelope(self.client_for(kind).post(RELOAD), status, {401: "unauthenticated", 403: "forbidden"}[status])
        for path in self.PAGES:
            with self.subTest(page=path):
                anonymous = self.client_for("anonymous").get(path)
                self.assertEqual(anonymous.status_code, 302)
                self.assertIn("next=", anonymous["Location"])
                self.assertEqual(self.client_for("player").get(path).status_code, 403)
                for kind in ("developer", "superuser"):
                    page = self.client_for(kind).get(path)
                    self.assertEqual(page.status_code, 200)
                    self.assertIn(b"gm/dist/index.js", page.content)

    def test_requests_and_denials_emit_their_facade_events(self):
        with mock.patch("web.gm.middleware.log_info") as log_info, mock.patch("web.gm.access.log_warn") as log_warn:
            self.developer.get(f"{REGISTRY}/t_critters")
            self.client_for("player").get(f"{SOURCES}/")
        requests = [call.kwargs["context"] for call in log_info.call_args_list if call.args[0] == "gm_request"]
        self.assertIn({"account": self.account.username, "route": f"{REGISTRY}/t_critters", "method": "GET", "status": 200}, requests)
        denied = [call.kwargs["context"] for call in log_warn.call_args_list if call.args[0] == "gm_denied"]
        self.assertEqual(denied[0]["route"], f"{SOURCES}/")
        self.assertEqual(denied[0]["account"], self.account2.username)

    def _source_digest(self) -> str:
        digest = hashlib.sha256()
        roots = (Path(settings.GAME_DIR) / "world" / "rules" / "rulebook", Path(settings.GAME_DIR) / "prompts")
        for root in roots:
            for path in sorted(root.rglob("*.yaml")):
                digest.update(path.read_bytes())
        return digest.hexdigest()

    def _row_counts(self) -> tuple[int, ...]:
        return (ObjectDB.objects.count(), Attribute.objects.count(), ScriptDB.objects.count(), Tag.objects.count())

    def test_reads_and_reload_change_no_rows_attributes_or_source_bytes_offline(self):
        before = (self._source_digest(), self._row_counts())
        snapshot = {name: dict(spec.loader()) for name, spec in ((spec.name, spec) for spec in INDEX)}
        client, token = Client(enforce_csrf_checks=True), None
        client.force_login(self.account)
        client.get("/gm/")
        token = client.cookies["csrftoken"].value

        def offline(*_args, **_kwargs):
            raise OSError("network disabled for this test")

        self.addCleanup(reset_prompt_library)
        with mock.patch.object(socket.socket, "connect", offline), mock.patch.object(socket, "create_connection", offline):
            for path in self.API_GETS:
                self.assertEqual(client.get(path).status_code, 200, path)
            self.assert_ok_envelope(client.post(RELOAD, HTTP_X_CSRFTOKEN=token))
        self.assertEqual((self._source_digest(), self._row_counts()), before)
        self.assertEqual({spec.name: dict(spec.loader()) for spec in INDEX}, snapshot)
