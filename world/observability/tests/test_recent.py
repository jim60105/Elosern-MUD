"""Tests for the process-local recent-event buffers (gm-portal-s2b)."""

import threading
import unittest
from unittest.mock import MagicMock, patch

from django.test import override_settings

from tools.spec_traceability import covers_requirement
from world.observability import api, recent


class _BufferCase(unittest.TestCase):
    def setUp(self):
        recent.reset()
        self.addCleanup(recent.reset)


class BufferBoundsTests(_BufferCase):
    @covers_requirement('gm-operations-dashboard::bounded-recent-event-snapshots')
    def test_capacity_bound_evicts_the_oldest_entries(self):
        with override_settings(GM_RECENT_LLM_CAPACITY=3, GM_RECENT_ISSUE_CAPACITY=2):
            recent.reset()
            for index in range(5):
                recent.record("info", "llm_call", "mod.f:1", {"seq": index}, None)
                recent.record("warn", "thing_failed", "mod.g:2", {"seq": index}, "ValueError: x")
            snap = recent.snapshot()
        self.assertEqual([e["context"]["seq"] for e in snap["llm"]], [2, 3, 4])
        self.assertEqual([e["context"]["seq"] for e in snap["issues"]], [3, 4])
        self.assertEqual((snap["llm_capacity"], snap["issue_capacity"]), (3, 2))
        self.assertEqual(snap["issues"][-1]["exc"], "ValueError: x")
        self.assertEqual(snap["issues"][-1]["caller"], "mod.g:2")

    def test_only_llm_calls_and_warn_error_events_qualify(self):
        recent.record("info", "cmd_in", "m:1", {}, None)
        recent.record("debug", "llm_call_retry", "m:1", {}, None)
        recent.record("warn", "llm_call", "m:1", {}, None)
        recent.record("error", "boom", "m:1", {}, None)
        snap = recent.snapshot()
        self.assertEqual([e["event"] for e in snap["llm"]], ["llm_call"])
        self.assertEqual([e["event"] for e in snap["issues"]], ["llm_call", "boom"])

    def test_invalid_capacity_settings_fall_back_to_defaults(self):
        with override_settings(GM_RECENT_LLM_CAPACITY=0, GM_RECENT_ISSUE_CAPACITY=True):
            recent.reset()
            snap = recent.snapshot()
        self.assertEqual(snap["llm_capacity"], recent.DEFAULT_LLM_CAPACITY)
        self.assertEqual(snap["issue_capacity"], recent.DEFAULT_ISSUE_CAPACITY)

    @covers_requirement('gm-operations-dashboard::bounded-recent-event-snapshots')
    def test_reset_starts_an_empty_epoch(self):
        recent.record("error", "boom", "m:1", {}, None)
        recent.reset()
        self.assertEqual(recent.snapshot()["issues"], [])


class SnapshotIsolationTests(_BufferCase):
    @covers_requirement('gm-operations-dashboard::bounded-recent-event-snapshots')
    def test_snapshot_and_caller_mutations_do_not_change_stored_entries(self):
        context = {"layer": "narrator"}
        recent.record("info", "llm_call", "m:1", context, None)
        context["layer"] = "mutated-by-caller"
        first = recent.snapshot()
        first["llm"][0]["context"]["layer"] = "mutated-by-reader"
        first["llm"][0]["event"] = "changed"
        first["llm"].clear()
        again = recent.snapshot()["llm"][0]
        self.assertEqual(again["context"]["layer"], "narrator")
        self.assertEqual(again["event"], "llm_call")

    @covers_requirement('gm-operations-dashboard::bounded-recent-event-snapshots')
    def test_concurrent_writers_and_mutating_readers_stay_bounded(self):
        with override_settings(GM_RECENT_LLM_CAPACITY=50):
            recent.reset()
            errors = []

            def writer(base):
                for index in range(400):
                    recent.record("info", "llm_call", "m:1", {"seq": base + index}, None)

            def reader():
                try:
                    for _ in range(200):
                        for entry in recent.snapshot()["llm"]:
                            entry["context"]["seq"] = -1
                except Exception as error:  # pragma: no cover - surfaced below
                    errors.append(error)

            threads = [threading.Thread(target=writer, args=(n * 1000,)) for n in range(4)]
            threads += [threading.Thread(target=reader) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            entries = recent.snapshot()["llm"]
        self.assertEqual(errors, [])
        self.assertEqual(len(entries), 50)
        self.assertTrue(all(entry["context"]["seq"] >= 0 for entry in entries))


class FacadeFeedTests(_BufferCase):
    @covers_requirement('observability-logging::facade-is-the-sole-game-code-log-entry-point')
    def test_facade_writes_the_line_before_feeding_the_sink(self):
        order = []
        logger = MagicMock()
        logger.log_warn.side_effect = lambda line: order.append(("line", line))
        real_record = recent.record

        def spy(*args):
            order.append(("sink", args[1]))
            return real_record(*args)

        with patch.object(api, "_get_evennia_logger", return_value=logger), \
                patch.object(recent, "record", side_effect=spy):
            api.log_warn("thing_failed", context={"room": 7})
        self.assertEqual([kind for kind, _ in order], ["line", "sink"])
        entry = recent.snapshot()["issues"][0]
        self.assertEqual((entry["event"], entry["context"]), ("thing_failed", {"room": 7}))
        self.assertTrue(entry["caller"].startswith(__name__))

    @covers_requirement('gm-operations-dashboard::bounded-recent-event-snapshots')
    @covers_requirement('observability-logging::facade-is-the-sole-game-code-log-entry-point')
    def test_a_failing_sink_keeps_the_written_line_and_never_raises(self):
        logger = MagicMock()
        with patch.object(api, "_get_evennia_logger", return_value=logger), \
                patch.object(recent, "record", side_effect=RuntimeError("sink broke")):
            api.log_error("thing_failed", context={"room": 7})
        self.assertIn("[error] thing_failed", logger.log_err.call_args_list[0].args[0])

    def test_stderr_fallback_still_feeds_the_sink(self):
        with patch.object(api, "_get_evennia_logger", side_effect=ImportError("no logger")), \
                patch.object(api, "_fallback_stderr") as fallback:
            api.log_warn("thing_failed", context={})
        fallback.assert_called_once()
        self.assertEqual(recent.snapshot()["issues"][0]["event"], "thing_failed")

    def test_verbose_off_still_captures_llm_calls_and_warnings(self):
        logger = MagicMock()
        with override_settings(VERBOSE=False), \
                patch.object(api, "_get_evennia_logger", return_value=logger):
            api.log_debug("llm_call", context={"layer": "x"})
            api.log_info("llm_call", context={"layer": "narrator"})
            api.log_warn("thing_failed", context={})
        snap = recent.snapshot()
        self.assertEqual([e["context"]["layer"] for e in snap["llm"]], ["narrator"])
        self.assertEqual([e["event"] for e in snap["issues"]], ["thing_failed"])

    def test_reentrant_logging_from_a_context_copy_does_not_recurse(self):
        from collections.abc import Mapping

        class Noisy(Mapping):
            """Logs on its second iteration: the sink's copy, after rendering."""

            def __init__(self):
                self.iterations = 0

            def __getitem__(self, key):
                return {"room": 1}[key]

            def __len__(self):
                return 1

            def __iter__(self):
                self.iterations += 1
                if self.iterations == 2:
                    api.log_warn("nested_event", context={})
                return iter(["room"])

        logger = MagicMock()
        with patch.object(api, "_get_evennia_logger", return_value=logger):
            api.log_warn("outer_event", context=Noisy())
        events = [e["event"] for e in recent.snapshot()["issues"]]
        self.assertEqual(events, ["outer_event"])
