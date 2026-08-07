"""Narrator layer: deterministic EventLog-to-prose mapping (design §7.3).

The narrator maps frozen ``EventLog`` records to Traditional Chinese prose
through the shared validation-retry-degrade guardrail (design §7.5). It is a
pure function: it reads only the deterministic EventLog data it is handed, has
no access to a write API, and returns plain prose that is never parsed back.
When the layer is disabled, the transport fails, validation retries are
exhausted, or the input exceeds the prompt bounds, the call resolves to the
deterministic template rendering of the same EventLogs via the injected
renderer, so the game stays fully playable with the LLM offline.

Boundary contract (``tests/test_ai_transport_contract.py``): this module imports
no state writer, no live transport, and no socket. The client and the template
renderer are both injected; ``world.rules.event_log`` is never imported here.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from twisted.internet import defer

from world.ai import guardrail
from world.ai.guardrail import (
    GuardrailRegistrationError,
    guarded_call,
    register_degrade_fallback,
    register_semantic_validator,
)
from world.ai.schemas import ChatRequestDescriptor
from world.prompts.loader import PromptUnavailableError, render_prompt

# Hard prompt bounds (design D2): a fixed maximum entry count, per-field
# string-length caps, and a bounded total serialized size.
MAX_ENTRIES = 60
MAX_FIELD_LENGTH = 200
MAX_TOTAL_SIZE = 12000

# Structural caps that keep the serialized record finite even when the inputs
# are pathological (unbounded logs, targets, or data items). The total-size
# drop loop trims trailing entries and then whole logs; the minimal-record
# last resort guarantees the user message is always valid JSON within bounds.
MAX_LOGS = 20
MAX_TARGETS = 20
MAX_DATA_ITEMS = 100

# Accepted-prose bound used by the length semantic validator (design D4).
MAX_PROSE_LENGTH = 2000

_TRUNCATION_MARKER = "…"
_CJK_START = "\u4e00"
_CJK_END = "\u9fff"
_TEMPLATE_PLACEHOLDER_RE = re.compile(r"\{actor\}|\{target\}|\{data\[[^\]]*\]\}")

class NarratorClientRequiredError(TypeError):
    """Raised when ``narrate_event_logs`` is called with an explicit ``None`` client."""


class NarratorNotRegisteredError(RuntimeError):
    """Raised when ``narrate_event_logs`` runs before the narrator hooks are installed."""


_NARRATOR_DEGRADED = object()

# Installed by ``register_narrator``; the sole consumer of ``world.rules``'
# template rendering is the registration site, never this module.
_template_renderer: Callable[[Sequence[Any]], str] | None = None


def _degrade_fallback() -> object:
    """Return the sentinel so the entry point can map it to the real renderer."""
    return _NARRATOR_DEGRADED


def _validate_non_empty(parsed: Any) -> list[str]:
    if not isinstance(parsed, str) or not parsed.strip():
        return ["narrated prose is empty or whitespace-only"]
    return []


def _validate_bounded_length(parsed: Any) -> list[str]:
    if isinstance(parsed, str) and len(parsed) > MAX_PROSE_LENGTH:
        return [f"narrated prose exceeds the {MAX_PROSE_LENGTH}-character length cap"]
    return []


def _validate_has_cjk(parsed: Any) -> list[str]:
    if not isinstance(parsed, str) or not any(_CJK_START <= ch <= _CJK_END for ch in parsed):
        return [
            "narrated prose contains no CJK Unified Ideograph and is not Traditional Chinese"
        ]
    return []


def _validate_no_template_placeholder(parsed: Any) -> list[str]:
    if isinstance(parsed, str) and _TEMPLATE_PLACEHOLDER_RE.search(parsed):
        return ["narrated prose echoes deterministic template-placeholder formatting syntax"]
    return []


_VALIDATORS: dict[str, Callable[[Any], list[str]]] = {
    "prose_non_empty": _validate_non_empty,
    "prose_bounded_length": _validate_bounded_length,
    "prose_has_cjk": _validate_has_cjk,
    "prose_no_template_placeholder": _validate_no_template_placeholder,
}


def _cap_string(value: str) -> str:
    if len(value) <= MAX_FIELD_LENGTH:
        return value
    return value[: MAX_FIELD_LENGTH - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER


def _cap_data(value: Any) -> Any:
    if isinstance(value, dict):
        items = list(value.items())[:MAX_DATA_ITEMS]
        return {key: _cap_data(item) for key, item in items}
    if isinstance(value, (list, tuple)):
        return [_cap_data(item) for item in value[:MAX_DATA_ITEMS]]
    if isinstance(value, str):
        return _cap_string(value)
    return value


def _capped_entry(entry: Any) -> dict[str, Any]:
    return {
        "kind": _cap_string(entry.kind),
        "actor": _cap_string(entry.actor),
        "target": _cap_string(entry.target) if entry.target is not None else None,
        "data": _cap_data(entry.data),
        "text_template": _cap_string(entry.text_template),
    }


def _unbounded_entry(entry: Any) -> dict[str, Any]:
    return {
        "kind": entry.kind,
        "actor": entry.actor,
        "target": entry.target,
        "data": entry.data,
        "text_template": entry.text_template,
    }


def _record_with_entry_cap(event_logs: Iterable[Any]) -> dict[str, Any]:
    logs = tuple(event_logs)[:MAX_LOGS]
    total = sum(len(log.entries) for log in logs)
    truncated = max(0, total - MAX_ENTRIES)
    records = []
    budget = MAX_ENTRIES
    for log in logs:
        entries = []
        for entry in log.entries:
            if budget <= 0:
                break
            entries.append(_capped_entry(entry))
            budget -= 1
        records.append(
            {
                "actor": _cap_string(log.actor),
                "skill_key": _cap_string(log.skill_key),
                "targets": [_cap_string(target) for target in log.targets[:MAX_TARGETS]],
                "time_cost_seconds": log.time_cost_seconds,
                "entries": entries,
            }
        )
        if budget <= 0:
            break
    record = {"event_logs": records}
    if truncated:
        record["truncated_entries"] = truncated
    return record


def _unbounded_record(event_logs: Iterable[Any]) -> dict[str, Any]:
    return {
        "event_logs": [
            {
                "actor": log.actor,
                "skill_key": log.skill_key,
                "targets": list(log.targets),
                "time_cost_seconds": log.time_cost_seconds,
                "entries": [_unbounded_entry(entry) for entry in log.entries],
            }
            for log in event_logs
        ]
    }


def _serialize(record: dict[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, ensure_ascii=False)


def _drop_last_entry(record: dict[str, Any]) -> bool:
    for log in reversed(record["event_logs"]):
        if log["entries"]:
            log["entries"].pop()
            if "truncated_entries" in record:
                record["truncated_entries"] += 1
            return True
    return False


def _drop_last_log(record: dict[str, Any]) -> bool:
    if record["event_logs"]:
        dropped = record["event_logs"].pop()
        if "truncated_entries" in record:
            record["truncated_entries"] += len(dropped["entries"])
        return True
    return False


def _bounded_serialization(event_logs: Iterable[Any]) -> str:
    """Serialize the event record deterministically within the hard bounds.

    Entry count, per-field lengths, log count, target count, and data-item
    count are all capped with explicit ``truncated_entries`` markers. If the
    serialized text still exceeds the total size bound, trailing entries and
    then whole logs are dropped (each drop updating the marker) until it fits,
    so the returned text is always valid JSON within ``MAX_TOTAL_SIZE``.
    """
    record = _record_with_entry_cap(event_logs)
    text = _serialize(record)
    while len(text) > MAX_TOTAL_SIZE and (_drop_last_entry(record) or _drop_last_log(record)):
        text = _serialize(record)
    return text


def _fits_field(value: Any) -> bool:
    return not isinstance(value, str) or len(value) <= MAX_FIELD_LENGTH


def _fits_data(value: Any) -> bool:
    if isinstance(value, dict):
        return all(_fits_data(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_fits_data(item) for item in value)
    return _fits_field(value)


def _fits_within_bounds(event_logs: Iterable[Any]) -> bool:
    """Return True when the input needs no truncation under the prompt bounds."""
    logs = tuple(event_logs)
    if sum(len(log.entries) for log in logs) > MAX_ENTRIES:
        return False
    for log in logs:
        if not _fits_field(log.actor) or not _fits_field(log.skill_key):
            return False
        if any(not _fits_field(target) for target in log.targets):
            return False
        for entry in log.entries:
            if not _fits_field(entry.kind) or not _fits_field(entry.actor):
                return False
            if entry.target is not None and not _fits_field(entry.target):
                return False
            if not _fits_data(entry.data):
                return False
            if not _fits_field(entry.text_template):
                return False
    return len(_serialize(_unbounded_record(logs))) <= MAX_TOTAL_SIZE


def build_narrator_prompt(
    event_logs: Iterable[Any],
) -> tuple[dict[str, str], dict[str, str]]:
    """Build a deterministic (system, user) message pair for narration.

    The user message serializes the full event record (actor, skill key,
    targets, time cost, and every entry's kind/actor/target/data and
    ``text_template``) with stable sorted JSON serialization, bounded by the
    module's hard caps.
    """
    system = {"role": "system", "content": render_prompt("narrator.system")}
    user = {"role": "user", "content": _bounded_serialization(event_logs)}
    return system, user


def _is_registered() -> bool:
    """True when the guardrail's actual registries hold every narrator hook."""
    if guardrail._degrade_fallbacks.get("narrator") is not _degrade_fallback:
        return False
    validators = guardrail._semantic_validators.get("narrator", {})
    return all(validators.get(name) is validator for name, validator in _VALIDATORS.items())


def _require_registered() -> None:
    if not _is_registered():
        raise NarratorNotRegisteredError(
            "the narrator layer is not registered; call register_narrator() first"
        )


def _uninstall_fallback() -> None:
    if guardrail._degrade_fallbacks.get("narrator") is _degrade_fallback:
        del guardrail._degrade_fallbacks["narrator"]


def _uninstall_validator(name: str) -> None:
    validators = guardrail._semantic_validators.get("narrator", {})
    if validators.get(name) is _VALIDATORS[name]:
        del validators[name]


def _uninstall_all_own_hooks() -> None:
    """Remove every narrator hook that is this module's own (by identity).

    Used for rollback so a partial-failure registration can never leave a
    half-installed narrator state behind, regardless of whether the hooks were
    installed by the failing call or pre-existed from an earlier attempt.
    Foreign hooks with the same names are left untouched.
    """
    _uninstall_fallback()
    for name in _VALIDATORS:
        _uninstall_validator(name)


def register_narrator(
    template_renderer: Callable[[Sequence[Any]], str],
) -> None:
    """Install the narrator layer's guardrail hooks atomically and idempotently.

    Registers the sentinel degrade fallback and every semantic validator, then
    installs the injected template renderer only after all hooks succeed. On a
    partial failure every narrator hook belonging to this module (by identity)
    is removed before the error propagates, so the layer is never left
    half-registered. A second call is a no-op that keeps the first renderer and
    swallows only this module's own duplicate registration, never an
    incompatible one.
    """
    if not callable(template_renderer):
        raise TypeError("template_renderer must be callable")
    if _is_registered():
        return
    try:
        if guardrail._degrade_fallbacks.get("narrator") is not _degrade_fallback:
            register_degrade_fallback("narrator", _degrade_fallback)
        for name, validator in _VALIDATORS.items():
            validators = guardrail._semantic_validators.get("narrator", {})
            if validators.get(name) is validator:
                continue
            register_semantic_validator("narrator", name, validator)
    except GuardrailRegistrationError:
        _uninstall_all_own_hooks()
        raise
    global _template_renderer
    _template_renderer = template_renderer


@defer.inlineCallbacks
def narrate_event_logs(event_logs: Iterable[Any], client: Any):
    """Map deterministic EventLogs to Traditional Chinese prose (guarded).

    Args:
        event_logs: One or more frozen ``EventLog`` records to narrate.
        client: The injected client protocol; an explicit ``None`` is rejected
            with ``NarratorClientRequiredError`` before any prompt construction
            or transport interaction.

    Returns:
        A Deferred resolving to the narrated prose, or to the injected template
        renderer's output when the input exceeds the prompt bounds or the
        guarded pipeline degrades.
    """
    if client is None:
        raise NarratorClientRequiredError(
            "narrate_event_logs requires an injected client; got None"
        )
    logs = tuple(event_logs)
    _require_registered()
    renderer = _template_renderer
    if renderer is None:
        raise NarratorNotRegisteredError(
            "the narrator layer is not registered; call register_narrator() first"
        )
    if not _fits_within_bounds(logs):
        return renderer(logs)
    try:
        system, user = build_narrator_prompt(logs)
    except PromptUnavailableError:
        return renderer(logs)
    descriptor = ChatRequestDescriptor(messages=(system, user))
    result = yield guarded_call("narrator", client, descriptor)
    if result is _NARRATOR_DEGRADED:
        return renderer(logs)
    return result
