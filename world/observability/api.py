"""Runtime log facade — the sole entry point for game-code operational logs.

Four levels, one signature shape (design §3.1)::

    log_debug(event, *, exc=None, context=None)
    log_info(event, *, exc=None, context=None)
    log_warn(event, *, exc=None, context=None)
    log_error(event, *, exc=None, context=None)

Invariants:

- The caller segment ``mod.func:line`` is derived here via ``sys._getframe``;
  callers never pass it. All four public functions delegate to one ``_emit``
  with a fixed ``caller_skip`` depth — the single contract that keeps frame
  math correct through the ``world.observability`` re-export.
- ``log_debug`` is gated by ``settings.VERBOSE`` read through a narrow guard:
  unconfigured settings counts as False (nothing written, no fallback).
- Every operational failure (frame lookup, rendering, logger import, logger
  write, even the stderr fallback) is contained; a facade call returns
  normally. ``BaseException`` (KeyboardInterrupt/SystemExit) is never
  swallowed.
- ``log_error`` double-writes: the single line (with ``tb:`` summary) plus the
  full ``traceback.format_exception`` text to the Evennia error log.
- This module depends only on stdlib, the Evennia logger, and Django
  settings — never on game modules (no import cycles).
"""

from __future__ import annotations

import sys
import traceback as traceback_module
from collections.abc import Mapping
from typing import Any

from world.observability.render import format_exception_chain, render_line

_evennia_logger: Any = None


def _get_evennia_logger() -> Any:
    """Lazily acquire the Evennia logger (test seam; cached after success)."""
    global _evennia_logger
    if _evennia_logger is None:
        from evennia.utils import logger as evennia_logger_module

        _evennia_logger = evennia_logger_module
    return _evennia_logger


def _read_verbose_setting() -> object:
    """Read settings.VERBOSE; raising seam so tests can inject failures."""
    from django.conf import settings

    return getattr(settings, "VERBOSE", False)


def _debug_enabled() -> bool:
    """VERBOSE gate that treats any settings failure as disabled."""
    try:
        return bool(_read_verbose_setting())
    except Exception:
        return False


def _caller_segment(depth: int) -> str:
    try:
        frame = sys._getframe(depth)
    except Exception:
        return "??:?:0"
    module = frame.f_globals.get("__name__", "??")
    name = frame.f_code.co_name
    return f"{module}.{name}:{frame.f_lineno}"


def _fallback_stderr(line: str) -> None:
    """Last-resort sink; its own failure is contained by the caller."""
    print(line, file=sys.stderr)


def _write(logger: Any, level: str, line: str, exc: BaseException | None) -> None:
    """Send one line to the Evennia logger with per-write containment."""
    if level == "error":
        sink = logger.log_err
    elif level == "warn":
        sink = logger.log_warn
    elif level == "debug":
        sink = logger.log_info
    else:
        sink = logger.log_info
    sink(line)
    if level == "error" and exc is not None:
        # Second, independent write: full traceback text for deep dives.
        try:
            logger.log_err("".join(
                traceback_module.format_exception(type(exc), exc, exc.__traceback__)
            ))
        except Exception:
            pass


def _emit(
    level: str,
    event: str,
    exc: BaseException | None,
    context: Mapping[str, Any] | None,
    caller_skip: int,
) -> None:
    # Frame contract (measured): from inside _caller_segment, depth 1 ==
    # _emit, depth 2 == the public log_* function, depth 3 == its caller.
    # Every public entry therefore passes ``caller_skip=3``; the re-export
    # through ``world.observability/__init__`` adds no frame.
    if level == "debug" and not _debug_enabled():
        return
    line: str | None = None
    try:
        caller = _caller_segment(caller_skip)
    except Exception:
        caller = "??:?:0"
    try:
        tb_segment = format_exception_chain(exc) if exc is not None else None
    except Exception:
        tb_segment = "<unrenderable>"
    try:
        line = render_line(level, str(event), caller, context, tb_segment)
    except Exception:
        line = f"[{level}] {_safe_str(event)} | {caller} | <render-failed>"
    if line is None:
        line = f"[{level}] <unrenderable> | {caller}"
    try:
        _write(_get_evennia_logger(), level, line, exc)
        return
    except Exception:
        pass
    try:
        _fallback_stderr(line)
    except Exception:
        return


def _safe_str(value: object) -> str:
    try:
        return str(value)
    except Exception:
        return "<unrenderable>"


def log_debug(
    event: str, *, exc: BaseException | None = None, context: Mapping[str, Any] | None = None
) -> None:
    """Verbose-gated detail event; silent unless ``settings.VERBOSE``."""
    try:
        _emit("debug", event, exc, context, caller_skip=3)
    except Exception:
        return


def log_info(
    event: str, *, exc: BaseException | None = None, context: Mapping[str, Any] | None = None
) -> None:
    """Normal-path boundary event (state edges, lifecycle, external calls)."""
    try:
        _emit("info", event, exc, context, caller_skip=3)
    except Exception:
        return


def log_warn(
    event: str, *, exc: BaseException | None = None, context: Mapping[str, Any] | None = None
) -> None:
    """Degraded-but-continuing event; ``exc`` adds a one-line ``tb:`` summary."""
    try:
        _emit("warn", event, exc, context, caller_skip=3)
    except Exception:
        return


def log_error(
    event: str, *, exc: BaseException | None = None, context: Mapping[str, Any] | None = None
) -> None:
    """Failure event; double-writes line + full traceback when ``exc`` given."""
    try:
        _emit("error", event, exc, context, caller_skip=3)
    except Exception:
        return
