"""Facade API tests: routing, gating, double-write, and fault containment."""

import io
import unittest
from types import SimpleNamespace
from unittest import mock

from django.test import override_settings

from world.observability import log_debug, log_error, log_info, log_warn
from world.observability import api

from tools.spec_traceability import covers_requirement


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

    @covers_requirement('observability-logging::facade-is-the-sole-game-code-log-entry-point')
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

    @covers_requirement('observability-logging::log-error-captures-the-exception-chain-in-one-line-and-the-full-traceback-separately')
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


class LazyBindingTests(unittest.TestCase):
    """The facade must not capture evennia.logger at import time.

    ``evennia.logger`` is None until ``evennia._init()``. The contract is
    static (no module-level Evennia import in the facade sources) plus
    behavioural (a failed pre-init bind is never cached, so a later emit
    still writes).
    """

    def test_facade_sources_have_no_module_level_evennia_import(self) -> None:
        import ast
        from pathlib import Path

        for name in ("api.py", "render.py", "__init__.py"):
            path = Path(api.__file__).parent / name
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:  # module level only
                roots: list[str] = []
                if isinstance(node, ast.Import):
                    roots = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    roots = [node.module]
                for root in roots:
                    self.assertFalse(
                        root == "evennia" or root.startswith("evennia."),
                        f"{name} binds Evennia at import time",
                    )

    def test_failed_pre_init_bind_is_not_cached(self) -> None:
        # A failed bind (Evennia not initialised / logger unimportable) must
        # fall back to stderr AND leave the cache unset, so a later emission
        # after evennia._init() can still bind successfully.
        with (
            mock.patch.object(api, "_evennia_logger", None),
            mock.patch("builtins.__import__", side_effect=ImportError("pre-init")),
            mock.patch("sys.stderr", new_callable=io.StringIO) as stderr,
        ):
            log_info("pre_init_evt", context={"a": 1})
            # Assert inside the window: patch.object restores the pre-test
            # cache value on exit.
            self.assertIsNone(api._evennia_logger)
        self.assertIn("[info] pre_init_evt", stderr.getvalue())


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
    @covers_requirement('observability-logging::the-facade-never-raises')
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
