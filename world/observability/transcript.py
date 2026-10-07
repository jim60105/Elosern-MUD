"""Retained full-payload LLM call transcript (GM portal S2a).

Every guarded LLM call leaves JSON-lines records in
``server/logs/llm/YYYY-MM-DD.jsonl`` (server local date): one ``exchange``
per settled real transport attempt (written by ``world.ai.client``) and one
terminal ``outcome`` per guarded call (written by ``world.ai.guardrail``),
correlated by ``call_id``. The operational log stays single-line and bounded;
this file is where full prompts and model output live.

Invariants:

- Depends only on the standard library and Django settings.
- Never raises on an operational failure (unserialisable record, unwritable
  directory, unreadable file, malformed line): it writes one best-effort line
  to stderr and returns. ``BaseException`` is never swallowed.
- Disabled (``LLM_TRANSCRIPT_ENABLED`` false): ``write`` is a no-op and
  ``find`` raises :class:`TranscriptDisabled` so a lookup can never be
  mistaken for "no records". :func:`is_enabled` is the non-raising probe.
- Credentials never reach disk: ``write`` takes the secrets known to the
  writer, scrubs every string (keys included) structurally, then scrubs the
  serialised line for the raw and JSON-escaped forms as a second pass.
- Appends hold a process lock; lookups read without it (a torn trailing
  line is absorbed by the malformed-line skip) so the reactor-thread writer
  never waits on a web-thread scan.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
from collections.abc import Iterable, Mapping
from datetime import date, timedelta
from typing import Any

DEFAULT_RETENTION_DAYS = 14
REDACTED = "[redacted]"
# Shorter "secrets" are ignored: replacing them would mangle ordinary text
# and could corrupt an already-inserted redaction marker.
MIN_SECRET_LENGTH = 4
_FILE_PATTERN = re.compile(r"^(\d{4}-\d{2}-\d{2})\.jsonl$")
_lock = threading.Lock()


class TranscriptDisabled(Exception):
    """Raised by :func:`find` when transcripts are disabled by settings."""


def _settings() -> Any:
    from django.conf import settings

    return settings


def _transcript_dir() -> str:
    """Directory holding the dated files (test seam)."""
    return os.path.join(_settings().GAME_DIR, "server", "logs", "llm")


def _today() -> date:
    """Server local date (test seam)."""
    return date.today()


def _stderr(message: str) -> None:
    """Best-effort single diagnostic line; its own failure is contained."""
    try:
        print(f"[llm_transcript] {message}", file=sys.stderr)
    except Exception:  # observability: ignore R2: stderr is the last-resort sink; nothing remains to report to
        return


def is_enabled() -> bool:
    """Whether transcripts are enabled; unreadable settings count as disabled."""
    try:
        return bool(getattr(_settings(), "LLM_TRANSCRIPT_ENABLED", True))
    except Exception:  # observability: ignore R2: unreadable settings fail closed to the inert no-write mode
        return False


def retention_days() -> int:
    """Configured retention window in days (at least 1)."""
    try:
        value = getattr(_settings(), "LLM_TRANSCRIPT_RETENTION_DAYS", DEFAULT_RETENTION_DAYS)
    except Exception:  # observability: ignore R2: settings unavailable means the documented default
        return DEFAULT_RETENTION_DAYS
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return DEFAULT_RETENTION_DAYS
    return value


def _oldest_kept(today: date) -> date:
    return today - timedelta(days=retention_days() - 1)


def _path_for(day: date) -> str:
    return os.path.join(_transcript_dir(), f"{day.isoformat()}.jsonl")


def _usable(secrets: Iterable[str]) -> tuple[str, ...]:
    """Non-blank secrets, longest first (blank would match everywhere)."""
    unique = {
        secret for secret in secrets
        if isinstance(secret, str) and len(secret.strip()) >= MIN_SECRET_LENGTH
    }
    return tuple(sorted(unique, key=lambda secret: (-len(secret), secret)))


def redact_text(text: str, secrets: Iterable[str]) -> str:
    """Replace every non-blank secret occurring in ``text``."""
    for secret in _usable(secrets):
        text = text.replace(secret, REDACTED)
    return text


def redact(value: Any, secrets: Iterable[str]) -> Any:
    """Structurally scrub every string (and mapping key) inside ``value``."""
    usable = _usable(secrets)
    if not usable:
        return value
    if isinstance(value, str):
        return redact_text(value, usable)
    if isinstance(value, Mapping):
        return {
            (redact_text(key, usable) if isinstance(key, str) else key): redact(item, usable)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item, usable) for item in value]
    return value


def _redact_line(line: str, secrets: tuple[str, ...]) -> str:
    """Second pass: a secret's JSON-escaped form differs from its raw form."""
    for secret in secrets:
        line = line.replace(secret, REDACTED)
        escaped = json.dumps(secret, ensure_ascii=False)[1:-1]
        if escaped != secret:
            line = line.replace(escaped, REDACTED)
    return line


def write(record: Mapping[str, Any], *, secrets: Iterable[str] = ()) -> None:
    """Append one record as a JSON line to today's file; never raises."""
    try:
        if not is_enabled():
            return
        usable = _usable(secrets)
        line = json.dumps(redact(dict(record), usable), ensure_ascii=False)
        line = _redact_line(line, usable)
        with _lock:
            directory = _transcript_dir()
            os.makedirs(directory, exist_ok=True)
            with open(_path_for(_today()), "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
    except Exception as error:  # observability: ignore R2: transcript failures must never reach gameplay; stderr diagnostic instead
        _stderr(f"write failed: {type(error).__name__}: {error}")


def _read_matches(path: str, call_id: str) -> list[dict]:
    matches: list[dict] = []
    malformed = 0
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if call_id not in line:
                continue
            try:
                record = json.loads(line)
            except ValueError:  # observability: ignore R2: counted and reported once per file below
                malformed += 1
                continue
            if isinstance(record, dict) and record.get("call_id") == call_id:
                matches.append(record)
    if malformed:
        _stderr(f"skipped {malformed} malformed line(s) in {os.path.basename(path)}")
    return matches


def find(call_id: str) -> list[dict]:
    """Every record for ``call_id``, newest date first, file order within a date.

    Raises :class:`TranscriptDisabled` when transcripts are disabled. Reading
    is best-effort: an unreadable file is diagnosed to stderr and skipped, so
    the result may be incomplete or empty but the call never fails otherwise.
    """
    if not is_enabled():
        raise TranscriptDisabled()
    results: list[dict] = []
    try:
        today = _today()
        days = [today - timedelta(days=offset) for offset in range(retention_days())]
    except Exception as error:  # observability: ignore R2: lookup failure is a stderr diagnostic, never an exception
        _stderr(f"find failed: {type(error).__name__}: {error}")
        return results
    for day in days:
        try:
            path = _path_for(day)
            if not os.path.exists(path):
                continue
            results.extend(_read_matches(path, call_id))
        except Exception as error:  # observability: ignore R2: an unreadable day is skipped with a stderr diagnostic
            _stderr(f"read failed for {day.isoformat()}: {type(error).__name__}: {error}")
    return results


def prune() -> None:
    """Delete dated files older than the retention window; never raises."""
    try:
        directory = _transcript_dir()
        if not os.path.isdir(directory):
            return
        oldest = _oldest_kept(_today())
        with _lock:
            for name in os.listdir(directory):
                match = _FILE_PATTERN.match(name)
                if match is None:
                    continue
                try:
                    if date.fromisoformat(match.group(1)) < oldest:
                        os.remove(os.path.join(directory, name))
                except Exception as error:  # observability: ignore R2: one undeletable file must not stop the sweep
                    _stderr(f"prune skipped {name}: {type(error).__name__}: {error}")
    except Exception as error:  # observability: ignore R2: retention failures must never abort startup
        _stderr(f"prune failed: {type(error).__name__}: {error}")
