"""Read-only operations snapshot for ``GET /gm/api/dashboard`` (gm-portal-s2b).

One snapshot of the recent-event buffers is taken per request; every slot is
then computed independently. A failing slot carries
``{"error": {"code": "<snake_case>", "message": "<zh-TW>"}}`` and emits one
``gm_dashboard_section_failed`` warning, while every other slot is unaffected.

Invariants:

- Read-only: no slot creates or writes a record. The world clock is read
  through ``read_world_clock`` (never ``get_world_clock``), the drain script
  through ``search_script`` (never ``GLOBAL_SCRIPTS``, which may create it).
- No LLM probes: LLM health is derived passively from buffered ``llm_call``
  events plus static profile configuration. The SD verdict is the existing
  TTL-cached ``world.art.connectivity.probe``.
- Counts and latencies describe the retained bounded buffer only, never
  lifetime totals; nothing is rebuilt from transcript history.
- The payload is JSON-safe by construction: buffered context values that are
  not JSON scalars are rendered to bounded text, so one odd value cannot fail
  the whole response outside the slot isolation.
"""

from __future__ import annotations

import math
import threading
import time
from collections import Counter
from collections.abc import Callable, Iterable
from typing import Any
from urllib.parse import urlsplit

from world.observability import log_warn
from world.observability import recent

RECENT_LLM_LIMIT = 50
RECENT_ISSUE_LIMIT = 50
ART_FAILURE_LIMIT = 10
CONTEXT_TEXT_LIMIT = 500

SECTION_MESSAGES: dict[str, str] = {
    "sd": "無法取得 sd-webui 連線狀態。",
    "translate": "無法判定翻譯後端。",
    "cutout": "無法判定去背後端。",
    "llm_summary": "無法讀取 LLM 設定檔。",
    "llm_layers": "無法計算 LLM 各層統計。",
    "llm_recent": "無法列出最近的 LLM 呼叫。",
    "art": "無法讀取美術佇列。",
    "world": "無法讀取世界狀態。",
    "errors": "無法列出最近的警告與錯誤。",
    "process": "無法讀取伺服器行程狀態。",
}


class SectionError(Exception):
    """A slot failure with a specific stable code (e.g. database_unreadable)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.message = message


#: A persistently failing slot is re-reported at most once per interval per
#: (section, code), so a polled dashboard cannot flood the recent issue
#: buffer it also displays.
FAILURE_LOG_INTERVAL_SECONDS = 60.0
_last_failure_log: dict[tuple[str, str], float] = {}
_failure_log_lock = threading.Lock()


def _report_failure(name: str, code: str, error: BaseException) -> None:
    now = time.monotonic()
    with _failure_log_lock:
        last = _last_failure_log.get((name, code))
        if last is not None and now - last < FAILURE_LOG_INTERVAL_SECONDS:
            return
        _last_failure_log[(name, code)] = now
    log_warn("gm_dashboard_section_failed", exc=error, context={"section": name, "code": code})


def _section(name: str, compute: Callable[[], Any]) -> Any:
    """Run one slot; contain its failure as a stable error object."""
    try:
        return compute()
    except SectionError as error:  # observability: ignore R2: _report_failure emits gm_dashboard_section_failed (rate-limited per section/code)
        _report_failure(name, error.code, error)
        return {"error": {"code": error.code, "message": error.message}}
    except Exception as error:  # observability: ignore R2: _report_failure emits gm_dashboard_section_failed (rate-limited per section/code)
        code = f"{name}_unavailable"
        _report_failure(name, code, error)
        return {"error": {"code": code, "message": SECTION_MESSAGES[name]}}


# --- JSON-safe projection ---------------------------------------------------


def _json_safe(value: Any) -> Any:
    """Scalars verbatim; anything else as bounded text."""
    if value is None or isinstance(value, (bool, int, str)):
        return value[:CONTEXT_TEXT_LIMIT] if isinstance(value, str) else value
    if isinstance(value, float):
        return value if math.isfinite(value) else repr(value)
    try:
        text = repr(value)
    except Exception:  # observability: ignore R2: an unrenderable value degrades in place; the slot still renders
        text = "<unrenderable>"
    return text[:CONTEXT_TEXT_LIMIT]


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) else None


def _host(url: Any) -> str | None:
    try:
        return urlsplit(str(url)).hostname
    except ValueError:  # observability: ignore R2: an unparseable configured URL simply has no displayable host
        return None


# --- services ---------------------------------------------------------------


def _sd() -> dict[str, Any]:
    from world.art.connectivity import UNKNOWN_HOST, probe

    verdict = probe()
    age = _number(verdict.age_seconds)
    # checked_at is monotonic; derive wall time from the age. The absolute
    # fallback verdict (checked_at 0.0) carries no real check time.
    fallback = verdict.checked_at == 0.0 or verdict.host == UNKNOWN_HOST
    checked_at = None if fallback or age is None or age < 0 else time.time() - age
    return {
        "ok": bool(verdict.ok),
        "code": verdict.code,
        "host": verdict.host,
        "checked_at": checked_at,
        "from_cache": bool(verdict.from_cache),
    }


def _latest_issue(issues: list[dict[str, Any]], prefix: str) -> dict[str, Any] | None:
    for entry in reversed(issues):
        if str(entry.get("event", "")).startswith(prefix):
            return {
                "ts": entry.get("ts"),
                "level": entry.get("level"),
                "event": entry.get("event"),
                "code": _json_safe(entry.get("context", {}).get("code")),
                "exc": _json_safe(entry.get("exc")),
            }
    return None


def _backend(enabled_setting: str, resolve: Callable[[], Any], issues, prefix: str) -> dict[str, Any]:
    from django.conf import settings

    if not getattr(settings, enabled_setting, False):
        kind, name = "disabled", None
    else:
        backend = resolve()
        name = type(backend).__name__
        kind = "fake" if name.startswith("Fake") else "real"
    return {"backend": kind, "class_name": name, "latest_failure": _latest_issue(issues, prefix)}


def _translate(issues) -> dict[str, Any]:
    from world.art.translate import resolve_translate_backend

    return _backend("ART_TRANSLATE_ENABLED", resolve_translate_backend, issues, "art_translate")


def _cutout(issues) -> dict[str, Any]:
    from world.art.cutout import resolve_cutout_backend

    return _backend("ART_REMBG_ENABLED", resolve_cutout_backend, issues, "art_cutout")


def _profiles() -> list[tuple[str, Any]]:
    from world.ai.profiles import LAYER_NAMES, get_profile

    return [(layer, get_profile(layer)) for layer in LAYER_NAMES]


def _llm_summary() -> dict[str, Any]:
    profiles = _profiles()
    return {"enabled": sum(1 for _, p in profiles if p.enabled), "total": len(profiles)}


# --- llm --------------------------------------------------------------------


def p95(values: list[int | float]) -> int | float | None:
    """Nearest-rank 95th percentile: sorted sample at ceil(0.95 * n) - 1."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def _layer_stats(entries: Iterable[dict[str, Any]]) -> dict[str, Any]:
    results: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    latencies: list[int | float] = []
    last_success = None
    calls = 0
    for entry in entries:
        context = entry.get("context") or {}
        calls += 1
        result = str(context.get("result", ""))
        results[result] += 1
        if result == "degraded":
            reasons[str(context.get("reason") or "unknown")] += 1
        ms = _number(context.get("ms"))
        if ms is not None:
            latencies.append(ms)
        if result == "ok":
            last_success = entry.get("ts")
    return {
        "calls": calls,
        "ok": results["ok"],
        "degraded": results["degraded"],
        "rejected": results["rejected"],
        "reasons": dict(sorted(reasons.items())),
        "mean_ms": round(sum(latencies) / len(latencies)) if latencies else None,
        "p95_ms": p95(latencies),
        "last_success_at": last_success,
    }


def _llm_layers(llm: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_layer: dict[str, list[dict[str, Any]]] = {}
    for entry in llm:
        by_layer.setdefault(str((entry.get("context") or {}).get("layer")), []).append(entry)
    layers = []
    for layer, profile in _profiles():
        stats = _layer_stats(by_layer.get(layer, []))
        layers.append({
            "layer": layer,
            "enabled": bool(profile.enabled),
            "model": profile.model,
            "endpoint_host": _host(profile.base_url),
            **stats,
        })
    return layers


def _llm_recent(llm: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for entry in reversed(llm[-RECENT_LLM_LIMIT:]):
        context = entry.get("context") or {}
        rows.append({
            "ts": entry.get("ts"),
            "call_id": _json_safe(context.get("call_id")),
            "layer": _json_safe(context.get("layer")),
            "profile": _json_safe(context.get("profile")),
            "ms": _number(context.get("ms")),
            "result": _json_safe(context.get("result")),
            "reason": _json_safe(context.get("reason")),
        })
    return rows


# --- art --------------------------------------------------------------------


def _art() -> dict[str, Any]:
    from evennia.utils.search import search_script

    from world.art.store import ArtAssetRecord, ArtAssetStatus

    counts = {status: 0 for status in (
        ArtAssetStatus.MISSING, ArtAssetStatus.PENDING, ArtAssetStatus.IN_PROGRESS,
        ArtAssetStatus.DONE, ArtAssetStatus.FAILED,
    )}
    failures = []
    for record in ArtAssetRecord.objects.all():
        status = record.db.status or ArtAssetStatus.MISSING
        counts[status] = counts.get(status, 0) + 1
        if status == ArtAssetStatus.FAILED:
            failures.append({
                "subject_key": record.db.subject_key or record.key,
                "kind": record.db.kind or None,
                "error": record.db.last_error_code,
                "ts": _number(record.db.enqueued_at),
            })
    failures.sort(key=lambda item: item["ts"] or 0, reverse=True)
    drain = search_script("art_drain")
    script = drain[0] if len(drain) else None
    return {
        "counts": counts,
        "drain": {"exists": script is not None, "running": bool(script and script.is_active)},
        "failures": failures[:ART_FAILURE_LIMIT],
    }


# --- world ------------------------------------------------------------------


def _daypart(hour: int) -> str | None:
    from world.rules.clock import CLOCK_YAML

    dayparts = sorted(CLOCK_YAML["dayparts"].items(), key=lambda item: item[1])
    if not dayparts:
        return None
    current = dayparts[-1][0]  # before the first start hour, the last daypart wraps
    for name, start in dayparts:
        if start <= hour:
            current = name
    return current


def _active_combats() -> int:
    from typeclasses.characters import PlayerCharacter
    from world.rules.combat_session.errors import CombatSessionError
    from world.rules.combat_session.records import read_session

    sessions = set()
    for player in PlayerCharacter.objects.all_family():
        try:
            record = read_session(player)
        except CombatSessionError:  # observability: ignore R2: a malformed session is not an active combat; the read model reports it elsewhere
            continue
        if record is not None and record.settled_tick is None:
            sessions.add(record.session_id)
    return len(sessions)


def _world() -> dict[str, Any]:
    from evennia import SESSION_HANDLER

    from typeclasses.rooms import InstanceRoom
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    if clock is None:
        clock_data = None
    else:
        calendar = clock.calendar
        clock_data = {
            "tick": int(clock.tick),
            "year": calendar.year,
            "season": calendar.season_name,
            "day": calendar.day_in_season,
            "hour": calendar.hour,
            "minute": calendar.minute,
            "daypart": _daypart(calendar.hour),
        }
    sessions = SESSION_HANDLER.get_sessions()
    accounts = {session.uid for session in sessions if getattr(session, "uid", None)}
    return {
        "clock": clock_data,
        "sessions": len(sessions),
        "accounts": len(accounts),
        "active_combats": _active_combats(),
        "live_instances": InstanceRoom.objects.count(),
    }


# --- errors / process -------------------------------------------------------


def _errors(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for entry in reversed(issues[-RECENT_ISSUE_LIMIT:]):
        context = entry.get("context") or {}
        rows.append({
            "ts": entry.get("ts"),
            "level": entry.get("level"),
            "event": _json_safe(entry.get("event")),
            "caller": _json_safe(entry.get("caller")),
            "context": {str(key): _json_safe(value) for key, value in sorted(
                context.items(), key=lambda item: str(item[0])) if value is not None},
            "exc": _json_safe(entry.get("exc")),
        })
    return rows


def database_readable() -> None:
    """One bounded primary-key read against a real table (raises on failure)."""
    from django.db import DatabaseError
    from evennia.accounts.models import AccountDB

    try:
        list(AccountDB.objects.order_by().values_list("id", flat=True)[:1])
    except DatabaseError as error:
        raise SectionError("database_unreadable", "資料庫目前無法讀取。") from error


def _process(snapshot: dict[str, Any]) -> dict[str, Any]:
    from evennia.utils import gametime

    database_readable()
    started = gametime.SERVER_START_TIME or None
    return {
        "django": "ok",
        "database": "readable",
        "started_at": started,
        "uptime_s": round(time.time() - started) if started else None,
        "buffers_started_at": recent.BUFFERS_STARTED,
        "now": time.time(),
        "buffers": {
            "llm": {"fill": len(snapshot["llm"]), "capacity": snapshot["llm_capacity"]},
            "issues": {"fill": len(snapshot["issues"]), "capacity": snapshot["issue_capacity"]},
        },
    }


def build_snapshot() -> dict[str, Any]:
    """The full dashboard payload; each slot is isolated from the others."""
    snapshot = recent.snapshot()
    llm, issues = snapshot["llm"], snapshot["issues"]
    return {
        "services": {
            "sd": _section("sd", _sd),
            "translate": _section("translate", lambda: _translate(issues)),
            "cutout": _section("cutout", lambda: _cutout(issues)),
            "llm": _section("llm_summary", _llm_summary),
        },
        "llm": {
            "layers": _section("llm_layers", lambda: _llm_layers(llm)),
            "recent": _section("llm_recent", lambda: _llm_recent(llm)),
            "window": {"retained": len(llm), "capacity": snapshot["llm_capacity"]},
        },
        "art": _section("art", _art),
        "world": _section("world", _world),
        "errors": {
            "recent": _section("errors", lambda: _errors(issues)),
            "window": {"retained": len(issues), "capacity": snapshot["issue_capacity"]},
        },
        "process": _section("process", lambda: _process(snapshot)),
    }
