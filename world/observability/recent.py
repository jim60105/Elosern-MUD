"""Process-local recent-event buffers for the GM dashboard (gm-portal-s2b).

The facade feeds this sink after it has written each operational line:

- every ``llm_call`` event enters the LLM buffer
  (``GM_RECENT_LLM_CAPACITY``, default 500);
- every ``warn``/``error`` event enters the issue buffer
  (``GM_RECENT_ISSUE_CAPACITY``, default 200).

A warning ``llm_call`` would qualify for both. Each buffer is a bounded,
lock-guarded deque: overflow evicts the oldest entry. Entries carry the wall
timestamp, level, event, caller segment, a shallow copy of ``context`` and
the one-line exception summary. Reads return snapshot copies (the entry and
its top-level context dict are copied; nested values are shared, by design).

Writers run on the reactor thread and readers on Django web threads; Evennia
serves Django from the server process, so both see the same memory. The
contents reset on reload, by design: the dashboard covers "since this server
process started", and the transcript files are the only durable record.

This module depends only on the standard library and Django settings and
never calls the facade (a failing sink must not recurse into logging).
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Mapping
from typing import Any

DEFAULT_LLM_CAPACITY = 500
DEFAULT_ISSUE_CAPACITY = 200
LLM_EVENT = "llm_call"
ISSUE_LEVELS = frozenset({"warn", "error"})

#: Wall-clock time this module was (re)imported: when the current buffer
#: epoch began. Not the server start; the dashboard reports that separately.
BUFFERS_STARTED = time.time()

# Re-entrancy guard: a pathological context whose copy triggers a log call on
# the same thread must not re-enter the sink (no recursion, no deadlock).
_local = threading.local()


def _capacity(name: str, default: int) -> int:
    try:
        from django.conf import settings

        value = getattr(settings, name, default)
    except Exception:  # observability: ignore R2: unreadable settings mean the documented default; this sink never logs
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return default
    return value


class _Buffer:
    """One bounded, lock-guarded FIFO of entry dicts."""

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self._entries: deque[dict[str, Any]] = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def append(self, entry: dict[str, Any]) -> None:
        with self._lock:
            self._entries.append(entry)

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            entries = list(self._entries)
        return [_copy_entry(entry) for entry in entries]


def _copy_entry(entry: dict[str, Any]) -> dict[str, Any]:
    copied = dict(entry)
    copied["context"] = dict(entry.get("context") or {})
    return copied


_state_lock = threading.Lock()
_llm: _Buffer | None = None
_issues: _Buffer | None = None


def _buffers() -> tuple[_Buffer, _Buffer]:
    """The two buffers, created on first use with the configured capacities."""
    global _llm, _issues
    with _state_lock:
        if _llm is None or _issues is None:
            _llm = _Buffer(_capacity("GM_RECENT_LLM_CAPACITY", DEFAULT_LLM_CAPACITY))
            _issues = _Buffer(_capacity("GM_RECENT_ISSUE_CAPACITY", DEFAULT_ISSUE_CAPACITY))
        return _llm, _issues


def record(
    level: str,
    event: str,
    caller: str,
    context: Mapping[str, Any] | None,
    exc_summary: str | None,
) -> None:
    """Capture one already-written event if it qualifies for a buffer.

    The entry is fully built before any lock is taken, and the locks guard
    only the append. May raise on a pathological ``context``; the facade
    contains it. Never logs.
    """
    to_llm = event == LLM_EVENT
    to_issues = level in ISSUE_LEVELS
    if not (to_llm or to_issues) or getattr(_local, "active", False):
        return
    _local.active = True
    try:
        entry = {
            "ts": time.time(),
            "level": level,
            "event": event,
            "caller": caller,
            "context": dict(context) if context else {},
            "exc": exc_summary,
        }
        llm, issues = _buffers()
        if to_llm:
            llm.append(entry)
        if to_issues:
            issues.append(entry)
    finally:
        _local.active = False


def snapshot() -> dict[str, Any]:
    """Copies of both buffers plus their capacities, oldest entry first."""
    llm, issues = _buffers()
    return {
        "llm": llm.snapshot(),
        "issues": issues.snapshot(),
        "llm_capacity": llm.capacity,
        "issue_capacity": issues.capacity,
    }


def reset() -> None:
    """Drop both buffers; the next use re-reads the capacities (test seam)."""
    global _llm, _issues
    with _state_lock:
        _llm = None
        _issues = None
