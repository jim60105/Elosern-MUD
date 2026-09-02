"""Facade API tests: routing, gating, double-write, and fault containment."""

import io
import unittest
from types import SimpleNamespace
from unittest import mock

from django.test import override_settings

from world.observability import log_debug, log_error, log_info, log_warn
from world.observability import api


def _fake_logger() -> SimpleNamespace:
    return SimpleNamespace(
        log_info=mock.Mock(),
        log_warn=mock.Mock(),
        log_err=mock.Mock(),
    )


def _lines(mock_fn) -> list[str]:
    return [call.args[0] for call in mock_fn.call_args_list]


class RoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = _fake_logger()
        patcher = mock.patch.object(api, "_get_evennia_logger", return_value=self.logger)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_level_routing(self) -> None:
        log_info("evt_info", context={"a": 1})
        log_warn("evt_warn", context={"a": 1})
        log_error("evt_error", context={"a": 1})
        self.assertEqual(len(_lines(self.logger.log_info)), 1)
        self.assertEqual(len(_lines(self.logger.log_warn)), 1)
        self.assertEqual(len(_lines(self.logger.log_err)), 1)
        self.assertIn("[info] evt_info", _lines(self.logger.log_info)[0])
        self.assertIn("[warn] evt_warn", _lines(self.logger.log_warn)[0])
        self.assertIn("[error] evt_error", _lines(self.logger.log_err)[0])

    def test_exc_renders_tb_at_every_level(self) -> None:
        try:
            raise ValueError("boom")
        except ValueError as exc:
            log_debug("d", exc=exc, context={"a": 1})  # gated off by default
            log_warn("w", exc=exc, context={"a": 1})
            log_info("i", exc=exc, context={"a": 1})
        warn_line = _lines(self.logger.log_warn)[0]
        info_line = _lines(self.logger.log_info)[0]
        self.assertIn("tb: ValueError: boom @ ", warn_line)
        self.assertIn("tb: ValueError: boom @ ", info_line)

    def test_log_error_double_writes_full_traceback(self) -> None:
        try:
            raise RuntimeError("deep")
        except RuntimeError as exc:
            log_error("boom_event", exc=exc, context={"room": 2})
        writes = _lines(self.logger.log_err)
        self.assertEqual(len(writes), 2)
        self.assertIn("[error] boom_event", writes[0])
        self.assertIn("RuntimeError: deep", writes[1])
        self.assertIn("Traceback", writes[1])

    def test_caller_segment_is_the_test_module(self) -> None:
        _call_log_info("caller_check")
        line = _lines(self.logger.log_info)[0]
        caller = line.split(" | ")[1]
        self.assertTrue(
            caller.startswith("world.observability.tests.test_api."),
            f"unexpected caller segment: {caller}",
        )
        self.assertIn("._call_log_info:", caller)

    def test_signatures_are_keyword_only_exc_and_context(self) -> None:
        import inspect

        for fn in (log_debug, log_info, log_warn, log_error):
            params = inspect.signature(fn).parameters
            self.assertEqual(params["exc"].kind, inspect.Parameter.KEYWORD_ONLY)
            self.assertEqual(params["context"].kind, inspect.Parameter.KEYWORD_ONLY)


def _call_log_info(event: str) -> None:
    log_info(event, context={"a": 1})


class DebugGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = _fake_logger()
        patcher = mock.patch.object(api, "_get_evennia_logger", return_value=self.logger)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_debug_silent_when_verbose_false(self) -> None:
        with override_settings(VERBOSE=False):
            log_debug("quiet", context={"a": 1})
        self.logger.log_info.assert_not_called()

    def test_debug_writes_when_verbose_true(self) -> None:
        with override_settings(VERBOSE=True):
            log_debug("loud", context={"a": 1})
        self.assertEqual(len(_lines(self.logger.log_info)), 1)
        self.assertIn("[debug] loud", _lines(self.logger.log_info)[0])

    def test_unavailable_settings_counts_as_false_and_never_falls_back(self) -> None:
        with mock.patch.object(
            api, "_read_verbose_setting", side_effect=Exception("settings unavailable")
        ):
            log_debug("quiet", context={"a": 1})
        self.logger.log_info.assert_not_called()


class ContainmentTests(unittest.TestCase):
    def test_logger_failure_degrades_to_stderr(self) -> None:
        broken = SimpleNamespace(
            log_info=mock.Mock(side_effect=RuntimeError("logger down")),
            log_warn=mock.Mock(),
            log_err=mock.Mock(),
        )
        with (
            mock.patch.object(api, "_get_evennia_logger", return_value=broken),
            mock.patch("sys.stderr", new_callable=io.StringIO) as stderr,
        ):
            log_info("rescued", context={"a": 1})
        self.assertIn("[info] rescued", stderr.getvalue())

    def test_broken_context_repr_still_emits_line(self) -> None:
        class Broken:
            def __repr__(self) -> str:
                raise RuntimeError("no repr")

        logger = _fake_logger()
        with mock.patch.object(api, "_get_evennia_logger", return_value=logger):
            log_info("partial", context={"k": Broken(), "room": 3})
        line = _lines(logger.log_info)[0]
        self.assertIn("room=3", line)
        self.assertIn("k=<unrenderable>", line)

    def test_full_traceback_second_write_failure_does_not_escape(self) -> None:
        state = {"calls": 0}

        def log_err(line: str) -> None:
            state["calls"] += 1
            if state["calls"] > 1:
                raise RuntimeError("error log broken")

        logger = SimpleNamespace(log_info=mock.Mock(), log_warn=mock.Mock(), log_err=log_err)
        try:
            raise ValueError("x")
        except ValueError as exc:
            with mock.patch.object(api, "_get_evennia_logger", return_value=logger):
                log_error("dual_fail", exc=exc, context={"a": 1})
        self.assertEqual(state["calls"], 2)

    def test_logger_import_failure_falls_back_to_stderr(self) -> None:
        with (
            mock.patch.object(api, "_get_evennia_logger", side_effect=ImportError("no evennia")),
            mock.patch("sys.stderr", new_callable=io.StringIO) as stderr,
        ):
            log_warn("orphan", context={"a": 1})
        self.assertIn("[warn] orphan", stderr.getvalue())

    def test_stderr_failure_still_returns_normally(self) -> None:
        black_hole = object()  # no write() attribute -> fallback raises
        with (
            mock.patch.object(api, "_get_evennia_logger", side_effect=ImportError("gone")),
            mock.patch("sys.stderr", black_hole),
        ):
            log_error("void_event", context={"a": 1})  # must not raise

    def test_exception_chain_never_swallows_base_exception(self) -> None:
        with self.assertRaises(KeyboardInterrupt):
            with mock.patch.object(api, "_emit", side_effect=KeyboardInterrupt):
                log_info("interrupted", context={"a": 1})


if __name__ == "__main__":
    unittest.main()
