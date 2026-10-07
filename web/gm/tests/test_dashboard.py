"""The read-only operations snapshot behind ``GET /gm/api/dashboard`` (gm-portal-s2b)."""

from __future__ import annotations

import json
import time
from unittest import mock

from django.db import DatabaseError
from django.test import override_settings
from evennia.objects.models import ObjectDB
from evennia.scripts.models import ScriptDB
from evennia.typeclasses.attributes import Attribute

from tools.spec_traceability import covers_requirement
from web.gm import dashboard
from web.gm.tests._support import GmTestCase
from world.art.connectivity import ProbeResult
from world.observability import recent

URL = "/gm/api/dashboard"


def _llm_call(layer, result, ms, reason=None, call_id=None):
    recent.record("info", "llm_call", "world.ai.guardrail.settle:1", {
        "call_id": call_id or ("%032x" % ms), "layer": layer, "profile": "synthetic-model",
        "ms": ms, "result": result, "reason": reason,
    }, None)


class _DashboardCase(GmTestCase):
    def setUp(self):
        super().setUp()
        dashboard._last_failure_log.clear()
        self.addCleanup(dashboard._last_failure_log.clear)
        recent.reset()
        self.addCleanup(recent.reset)
        probe = mock.patch("world.art.connectivity.probe", return_value=ProbeResult(
            ok=True, code=None, host="sd.example.test", checked_at=1234.0,
            age_seconds=5.0, from_cache=True,
        ))
        probe.start()
        self.addCleanup(probe.stop)

    def snapshot(self):
        return self.assert_ok_envelope(self.client_for("developer").get(URL))


class DashboardSnapshotTest(_DashboardCase):
    @covers_requirement('gm-operations-dashboard::independent-read-only-dashboard-sections')
    def test_every_section_reports_its_source_data(self):
        _llm_call("narrator", "ok", 100)
        _llm_call("narrator", "degraded", 300, reason="invalid_output")
        _llm_call("narrator", "degraded", 200, reason="transport_error")
        recent.record("warn", "art_translate_failed", "world.art.translate.x:1",
                      {"code": "art_translate_unavailable"}, "TranslateError: no model")
        data = self.snapshot()

        sd = data["services"]["sd"]
        self.assertEqual((sd["ok"], sd["host"], sd["code"]), (True, "sd.example.test", None))
        self.assertIsInstance(sd["checked_at"], float)
        self.assertEqual(data["services"]["translate"]["backend"], "disabled")
        self.assertEqual(data["services"]["translate"]["latest_failure"]["event"], "art_translate_failed")
        self.assertEqual(data["services"]["cutout"]["backend"], "disabled")
        self.assertIsNone(data["services"]["cutout"]["latest_failure"])
        summary = data["services"]["llm"]
        self.assertGreater(summary["total"], 0)

        layers = {layer["layer"]: layer for layer in data["llm"]["layers"]}
        narrator = layers["narrator"]
        self.assertEqual(
            (narrator["calls"], narrator["ok"], narrator["degraded"], narrator["rejected"]), (3, 1, 2, 0)
        )
        self.assertEqual(narrator["reasons"], {"invalid_output": 1, "transport_error": 1})
        self.assertEqual((narrator["mean_ms"], narrator["p95_ms"]), (200, 300))
        self.assertIsNotNone(narrator["last_success_at"])
        self.assertIn("model", narrator)
        self.assertIn("endpoint_host", narrator)
        idle = next(layer for name, layer in layers.items() if name != "narrator")
        self.assertEqual(idle["calls"], 0)
        self.assertIsNone(idle["mean_ms"])
        self.assertIsNone(idle["p95_ms"])
        self.assertIsNone(idle["last_success_at"])

        recent_calls = data["llm"]["recent"]
        self.assertEqual([row["ms"] for row in recent_calls], [200, 300, 100])
        self.assertEqual(data["llm"]["window"], {"retained": 3, "capacity": 500})

        self.assertIn("counts", data["art"])
        self.assertIn("drain", data["art"])
        world = data["world"]
        for key in ("clock", "sessions", "accounts", "active_combats", "live_instances"):
            self.assertIn(key, world)
        self.assertEqual(data["errors"]["recent"][0]["event"], "art_translate_failed")
        self.assertEqual(data["errors"]["recent"][0]["exc"], "TranslateError: no model")
        process = data["process"]
        self.assertEqual((process["django"], process["database"]), ("ok", "readable"))
        self.assertEqual(process["buffers"]["llm"], {"fill": 3, "capacity": 500})

    def test_recent_lists_are_bounded_newest_first(self):
        for index in range(60):
            _llm_call("narrator", "ok", index + 1)
            recent.record("error", "boom", "m:1", {"seq": index}, None)
        data = self.snapshot()
        self.assertEqual(len(data["llm"]["recent"]), dashboard.RECENT_LLM_LIMIT)
        self.assertEqual(data["llm"]["recent"][0]["ms"], 60)
        self.assertEqual(len(data["errors"]["recent"]), dashboard.RECENT_ISSUE_LIMIT)
        self.assertEqual(data["errors"]["recent"][0]["context"], {"seq": 59})

    @covers_requirement('gm-operations-dashboard::independent-read-only-dashboard-sections')
    def test_counts_describe_only_the_retained_window(self):
        with override_settings(GM_RECENT_LLM_CAPACITY=2):
            recent.reset()
            for ms in (10, 20, 30):
                _llm_call("narrator", "ok", ms)
            data = self.snapshot()
        narrator = next(row for row in data["llm"]["layers"] if row["layer"] == "narrator")
        self.assertEqual(narrator["calls"], 2)
        self.assertEqual(data["llm"]["window"], {"retained": 2, "capacity": 2})

    def test_nearest_rank_p95(self):
        self.assertIsNone(dashboard.p95([]))
        self.assertEqual(dashboard.p95([7]), 7)
        self.assertEqual(dashboard.p95(list(range(1, 21))), 19)
        self.assertEqual(dashboard.p95(list(range(1, 22))), 20)

    def test_odd_context_values_are_rendered_json_safe(self):
        recent.record("warn", "odd_event", "m:1", {"blob": b"\x00bytes", "nan": float("nan"),
                                                   "nested": {"a": [1]}}, None)
        data = self.snapshot()
        context = data["errors"]["recent"][0]["context"]
        self.assertEqual(context["blob"], "b'\\x00bytes'")
        self.assertEqual(context["nan"], "nan")
        self.assertEqual(context["nested"], "{'a': [1]}")

    def test_fallback_sd_verdict_has_no_fabricated_check_time(self):
        with mock.patch("world.art.connectivity.probe", return_value=ProbeResult(
            ok=False, code="sd_internal_error", host="?", checked_at=0.0,
            age_seconds=0.0, from_cache=False,
        )):
            sd = self.snapshot()["services"]["sd"]
        self.assertEqual((sd["ok"], sd["code"], sd["checked_at"]), (False, "sd_internal_error", None))

    def test_backend_types_report_real_and_fake(self):
        class FakeCutoutBackend:
            pass

        class CTranslate2Backend:
            pass

        with override_settings(ART_TRANSLATE_ENABLED=True, ART_REMBG_ENABLED=True), \
                mock.patch("world.art.translate.resolve_translate_backend", return_value=CTranslate2Backend()), \
                mock.patch("world.art.cutout.resolve_cutout_backend", return_value=FakeCutoutBackend()):
            services = self.snapshot()["services"]
        self.assertEqual(services["translate"]["backend"], "real")
        self.assertEqual(services["cutout"]["backend"], "fake")


class DashboardIsolationTest(_DashboardCase):
    FAILURES = {
        "sd": ("world.art.connectivity.probe", ("services", "sd"), "sd_unavailable"),
        "translate": ("world.art.translate.resolve_translate_backend", ("services", "translate"),
                      "translate_unavailable"),
        "cutout": ("world.art.cutout.resolve_cutout_backend", ("services", "cutout"), "cutout_unavailable"),
        "llm_recent": ("web.gm.dashboard._llm_recent", ("llm", "recent"), "llm_recent_unavailable"),
        "art": ("world.art.store.ArtAssetRecord.objects.all", ("art",), "art_unavailable"),
        "world": ("world.rules.clock.read_world_clock", ("world",), "world_unavailable"),
        "errors": ("web.gm.dashboard._errors", ("errors", "recent"), "errors_unavailable"),
    }

    @staticmethod
    def slot(data, path):
        for key in path:
            data = data[key]
        return data

    @covers_requirement('gm-operations-dashboard::independent-read-only-dashboard-sections')
    def test_each_failing_source_only_marks_its_own_slot(self):
        all_slots = [path for _, path, _ in self.FAILURES.values()] + [("process",), ("llm", "layers")]
        for name, (target, path, code) in self.FAILURES.items():
            # Both art backends resolve unless the one under test is broken;
            # the inner target patch is applied last, so it wins.
            dashboard._last_failure_log.clear()
            with self.subTest(section=name), \
                    override_settings(ART_TRANSLATE_ENABLED=True, ART_REMBG_ENABLED=True), \
                    mock.patch("world.art.translate.resolve_translate_backend", return_value=object()), \
                    mock.patch("world.art.cutout.resolve_cutout_backend", return_value=object()), \
                    mock.patch(target, side_effect=RuntimeError("source down")), \
                    mock.patch("web.gm.dashboard.log_warn") as warn:
                data = self.snapshot()
                self.assertEqual(self.slot(data, path), {"error": {
                    "code": code, "message": mock.ANY}})
                self.assertRegex(self.slot(data, path)["error"]["message"], r"[一-鿿]")
                for other in all_slots:
                    if other != path:
                        self.assertNotIn("error", self.slot(data, other), (name, other))
                self.assertEqual(warn.call_args.args[0], "gm_dashboard_section_failed")
                self.assertEqual(warn.call_args.kwargs["context"]["section"], name)

    def test_profile_failure_isolates_llm_configuration_slots_only(self):
        with mock.patch("web.gm.dashboard._profiles", side_effect=RuntimeError("bad profiles")):
            data = self.snapshot()
        self.assertEqual(data["services"]["llm"]["error"]["code"], "llm_summary_unavailable")
        self.assertEqual(data["llm"]["layers"]["error"]["code"], "llm_layers_unavailable")
        self.assertIsInstance(data["llm"]["recent"], list)
        self.assertNotIn("error", data["process"])

    @covers_requirement('gm-operations-dashboard::independent-read-only-dashboard-sections')
    @covers_requirement('gm-portal-access-api::s1-route-and-payload-scope')
    def test_unreadable_database_reports_a_process_error_and_keeps_other_slots(self):
        with mock.patch("evennia.accounts.models.AccountDB.objects.order_by",
                        side_effect=DatabaseError("disk I/O error")):
            data = self.snapshot()
        self.assertEqual(data["process"]["error"]["code"], "database_unreadable")
        self.assertNotIn("readable", json.dumps(data["process"]).replace("unreadable", ""))
        self.assertIn("sd", data["services"])
        self.assertIsInstance(data["errors"]["recent"], list)


class DashboardFailureLogTest(_DashboardCase):
    def test_a_persistent_slot_failure_is_reported_at_most_once_per_interval(self):
        with mock.patch("web.gm.dashboard._llm_recent", side_effect=RuntimeError("down")), \
                mock.patch("web.gm.dashboard.log_warn") as warn:
            for _ in range(5):
                data = self.snapshot()
                self.assertEqual(data["llm"]["recent"]["error"]["code"], "llm_recent_unavailable")
            self.assertEqual(warn.call_count, 1)
            with mock.patch("web.gm.dashboard.time.monotonic",
                            return_value=time.monotonic() + dashboard.FAILURE_LOG_INTERVAL_SECONDS + 1):
                self.snapshot()
            self.assertEqual(warn.call_count, 2)


class DashboardReadOnlyTest(_DashboardCase):
    @covers_requirement('gm-operations-dashboard::independent-read-only-dashboard-sections')
    @covers_requirement('gm-portal-access-api::s1-route-and-payload-scope')
    def test_snapshot_creates_and_writes_nothing_and_never_calls_an_llm(self):
        ScriptDB.objects.filter(db_key="world_clock").delete()
        counts = (ObjectDB.objects.count(), ScriptDB.objects.count(), Attribute.objects.count())
        with mock.patch("world.ai.client.OpenAICompatClient.get_response",
                        side_effect=AssertionError("LLM probe")) as llm, \
                mock.patch.object(Attribute, "save", side_effect=AssertionError("attribute write")), \
                mock.patch.object(ScriptDB, "save", side_effect=AssertionError("script write")):
            data = self.snapshot()
        llm.assert_not_called()
        self.assertIsNone(data["world"]["clock"])
        self.assertEqual(
            (ObjectDB.objects.count(), ScriptDB.objects.count(), Attribute.objects.count()), counts
        )

    def test_world_clock_reports_calendar_and_daypart_when_present(self):
        from world.rules.clock import get_world_clock

        from world.rules.clock import WorldDateTime

        tick = 987654
        get_world_clock()._persist(tick)
        world = self.snapshot()["world"]
        expected = WorldDateTime.from_tick(tick)
        self.assertEqual(world["clock"]["tick"], tick)
        self.assertEqual((world["clock"]["hour"], world["clock"]["day"]), (expected.hour, expected.day_in_season))
        self.assertIsInstance(world["clock"]["daypart"], str)
        self.assertIsInstance(world["clock"]["season"], str)
