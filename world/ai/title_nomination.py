"""Proposal-only epithet nomination layer (title-system D4, change G).

Asks the Director for exactly five ``{display, basis}`` candidate epithets
from a caller-supplied recent-event summary, validates the reply through the
closed output schema (malformed JSON, a wrong candidate count, or an overlong
field void the whole round), and then applies the deterministic collision
filters in fixed order — zh-tw form, fixed-registry display equality, the
entity's live collection (passed in, so a deleted name is renominable), and
in-batch duplicates keeping the first — returning the first three survivors.

This module is pure proposal: it holds no entity reference, reads and writes
no attribute, and imports no state writer or live transport at module time.
Persisting a ballot is performed solely by the rules-layer writer
(``world.rules.titles.persist_nomination_ballot``), scheduled by the
composition-root service. Collision rules are deliberately absent from the
prompt text: the prompt cost stays fixed and the prompt stays flat.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from twisted.internet import defer

from world.ai import guardrail
from world.ai.guardrail import (
    GuardrailRegistrationError,
    guarded_call,
    register_degrade_fallback,
)
from world.ai.profiles import get_profile
from world.ai.schemas import ChatRequestDescriptor
from world.ai.schemas.registry import (
    DuplicateSchemaError,
    _OUTPUT_SCHEMAS,
    register_output_schema,
)
from world.prompts.loader import PromptUnavailableError, render_prompt


# Round shape (design §7.2): exactly five candidates in, at most three survive
# into the ballot. Bounds mirror the rules-layer wire caps; ``basis`` is
# schema-bounded because an overlong field voids the whole round, while the
# 2–8-character display form rule is a per-candidate filter, not a schema rule.
CANDIDATES_PER_ROUND = 5
BALLOT_TOP = 3
DISPLAY_MIN_CHARS = 2
DISPLAY_MAX_CHARS = 8
BASIS_MAX_CHARS = 80
DISPLAY_WIRE_MAX_CHARS = 64
_CJK_START = "\u4e00"
_CJK_END = "\u9fff"

# Bounded prompt feed for the recent-event summary (the caller hands over
# plain EventLog-shaped records; serialization mirrors the narrator's
# discipline: entity keys and entry data only, hard-truncated, never live
# objects).
SUMMARY_MAX_LOGS = 8
SUMMARY_MAX_ENTRIES = 32
SUMMARY_MAX_FIELD_CHARS = 120
SUMMARY_MAX_TOTAL_CHARS = 8000


class TitleNominationClientRequiredError(TypeError):
    """Raised when ``generate_epithet_candidates`` gets an explicit ``None``."""


@dataclass(frozen=True)
class NominationContext:
    """Plain-data nomination inputs assembled by the scheduling service.

    Nothing here references a game entity: the service reads the collection,
    decline log, removal log, and full title through rules readers and hands
    the values over as frozen data.
    """

    player_name: str
    full_title: str
    declined: tuple[str, ...]
    owned_epithet_displays: frozenset[str]
    fixed_displays: frozenset[str]
    event_logs: tuple[Any, ...] = ()
    removed: tuple[str, ...] = ()


@dataclass(frozen=True)
class EpithetCandidate:
    """One surviving proposal: the display and its EventLog-grounded basis."""

    display: str
    basis: str


def _is_cjk(char: str) -> bool:
    return _CJK_START <= char <= _CJK_END


def display_form_valid(display: Any, player_name: str) -> bool:
    """The deterministic zh-tw form gate (design §7.2 filter 1).

    A display survives only when it is a 2–8 code-point string made entirely
    of CJK Unified Ideographs (no whitespace, no ASCII, no mixed forms) and
    does not contain the player's name as a substring.
    """
    if not isinstance(display, str):
        return False
    if not DISPLAY_MIN_CHARS <= len(display) <= DISPLAY_MAX_CHARS:
        return False
    if any(char.isspace() for char in display):
        return False
    if not all(_is_cjk(char) for char in display):
        return False
    if player_name and player_name in display:
        return False
    return True


def filter_candidates(
    candidates: Iterable[Mapping[str, Any]],
    *,
    player_name: str,
    fixed_displays: frozenset[str],
    owned_epithet_displays: frozenset[str],
) -> tuple[EpithetCandidate, ...]:
    """Apply the deterministic collision filters in the fixed spec order.

    Per candidate: display form → equality with any fixed-title registry
    display → equality with any epithet in the live collection (the
    collection is read at call time by the service, so deleted names are
    renominable) → in-batch duplicate (keep the first). The first three
    survivors form the ballot; 1–3 survivors ballot as-is. ``basis`` is NOT
    form-filtered here: the closed schema (type, non-blank, ≤80) and the
    rules-writer storage parse are its only gates, per the spec filter list.
    """
    survivors: list[EpithetCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        display = candidate.get("display")
        basis = candidate.get("basis")
        if not display_form_valid(display, player_name):
            continue
        if not isinstance(basis, str) or not basis:
            continue
        if display in fixed_displays or display in owned_epithet_displays:
            continue
        if display in seen:
            continue
        seen.add(display)
        survivors.append(EpithetCandidate(display=display, basis=basis))
        if len(survivors) == BALLOT_TOP:
            break
    return tuple(survivors)


def summarize_event_logs(event_logs: Iterable[Any]) -> str:
    """Serialize the recent-event feed to bounded JSON text (never raises).

    Mirrors the narrator's serialization shape (actor / skill_key / targets /
    entries with plain data only) under hard caps; oversized feeds drop the
    oldest logs and entries. An empty feed renders ``{"event_logs": []}``.
    """
    logs: list[dict[str, Any]] = []
    total_entries = 0
    for log in event_logs:
        if log is None:
            continue
        entries = list(getattr(log, "entries", ()) or ())
        if total_entries >= SUMMARY_MAX_ENTRIES:
            break
        remaining = SUMMARY_MAX_ENTRIES - total_entries
        kept_entries = entries[-remaining:] if len(entries) > remaining else entries
        total_entries += len(kept_entries)
        if len(logs) >= SUMMARY_MAX_LOGS:
            break
        logs.append(
            {
                "actor": _clamp(getattr(log, "actor", None)),
                "skill_key": _clamp(getattr(log, "skill_key", None)),
                "targets": [
                    _clamp(target) for target in (getattr(log, "targets", ()) or ())
                ][:8],
                "entries": [
                    {
                        "kind": _clamp(getattr(entry, "kind", None)),
                        "actor": _clamp(getattr(entry, "actor", None)),
                        "target": _clamp(getattr(entry, "target", None)),
                        "text_template": _clamp(
                            getattr(entry, "text_template", None)
                        ),
                    }
                    for entry in kept_entries
                ],
            }
        )
    def _size() -> int:
        return len(json.dumps({"event_logs": logs}, ensure_ascii=False))

    while len(logs) > 1 and _size() > SUMMARY_MAX_TOTAL_CHARS:
        logs.pop(0)
    # A single retained oversized log cannot be dropped whole (the feed must
    # keep something); trim its OLDEST entries until the serialized feed fits.
    while logs and logs[0]["entries"] and _size() > SUMMARY_MAX_TOTAL_CHARS:
        logs[0]["entries"].pop(0)
    if logs and _size() > SUMMARY_MAX_TOTAL_CHARS:
        logs.clear()
    return json.dumps({"event_logs": logs}, ensure_ascii=False)


def _clamp(value: Any) -> Any:
    if isinstance(value, str) and len(value) > SUMMARY_MAX_FIELD_CHARS:
        return value[:SUMMARY_MAX_FIELD_CHARS]
    return value


def build_nomination_prompt(context: NominationContext) -> tuple[dict, dict]:
    """Render the deterministic (system, user) pair from plain context data.

    The prompt carries form requirements only; collision rules are enforced in
    code, so no collision vocabulary ever appears here (fixed token cost).
    """
    system = {"role": "system", "content": render_prompt("title_nomination.system")}
    user = {
        "role": "user",
        "content": render_prompt(
            "title_nomination.user",
            player_name=context.player_name or "",
            full_title=context.full_title or "",
            recent_events=summarize_event_logs(context.event_logs),
            declined="、".join(context.declined) if context.declined else "無",
            removed="、".join(context.removed) if context.removed else "無",
        ),
    }
    return system, user


TITLE_NOMINATION_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["candidates"],
    "additionalProperties": False,
    "properties": {
        "candidates": {
            "type": "array",
            "minItems": CANDIDATES_PER_ROUND,
            "maxItems": CANDIDATES_PER_ROUND,
            "items": {
                "type": "object",
                "required": ["display", "basis"],
                "additionalProperties": False,
                "properties": {
                    "display": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": DISPLAY_WIRE_MAX_CHARS,
                    },
                    "basis": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": BASIS_MAX_CHARS,
                    },
                },
            },
        }
    },
}


_TITLE_NOMINATION_DEGRADED = object()


def _degrade_fallback() -> object:
    """Return the sentinel so the entry point can map it to the public None."""
    return _TITLE_NOMINATION_DEGRADED


def _registered() -> bool:
    if _degrade_fallbacks_registered() is False:
        return False
    return _OUTPUT_SCHEMAS.get("title_nomination") is TITLE_NOMINATION_OUTPUT_SCHEMA


def _degrade_fallbacks_registered() -> bool:
    return (
        guardrail._degrade_fallbacks.get("title_nomination") is _degrade_fallback
    )


def _require_registered() -> None:
    if not _registered():
        raise RuntimeError(
            "title_nomination layer is not registered; call "
            "register_title_nomination() at startup before use"
        )


def _uninstall_all_own_hooks() -> None:
    guardrail._degrade_fallbacks.pop("title_nomination", None)
    if _OUTPUT_SCHEMAS.get("title_nomination") is TITLE_NOMINATION_OUTPUT_SCHEMA:
        del _OUTPUT_SCHEMAS["title_nomination"]


def register_title_nomination() -> None:
    """Install the title_nomination guardrail hooks atomically and idempotently.

    Called from ``at_server_start`` like every other layer. Re-registration is
    idempotent; a foreign leftover registration raises
    ``GuardrailRegistrationError`` (boot-tolerant at the caller).
    """
    _require_layer_name()
    try:
        if guardrail._degrade_fallbacks.get("title_nomination") is not (
            _degrade_fallback
        ):
            register_degrade_fallback("title_nomination", _degrade_fallback)
        if _OUTPUT_SCHEMAS.get("title_nomination") is not TITLE_NOMINATION_OUTPUT_SCHEMA:
            register_output_schema("title_nomination", TITLE_NOMINATION_OUTPUT_SCHEMA)
    except (GuardrailRegistrationError, DuplicateSchemaError):
        _uninstall_all_own_hooks()
        raise


def _require_layer_name() -> None:
    from world.ai.profiles import LAYER_NAMES

    if "title_nomination" not in LAYER_NAMES:
        raise AssertionError("title_nomination missing from LAYER_NAMES")


@defer.inlineCallbacks
def generate_epithet_candidates(context: NominationContext, client: Any):
    """Run the guarded pipeline once and return the filtered ballot proposal.

    Args:
        context: Plain-data ``NominationContext`` (no entity references).
        client: The injected client protocol (``OpenAICompatClient`` or
            ``FakeLLMClient``); an explicit ``None`` is rejected before any
            prompt construction or transport interaction.

    Returns:
        A Deferred resolving to a tuple of 1–3 ``EpithetCandidate`` on
        success; ``()`` when every candidate was filtered out (the round is
        voided silently, no ballot); ``None`` when the round is void by
        contract — the profile is disabled (before any transport work), the
        prompt is unavailable, the transport fails or degrades, the closed
        schema rejects the reply (wrong count / malformed JSON / overlong
        fields), or the retry budget is exhausted. Writes nothing ever.
    """
    if client is None:
        raise TitleNominationClientRequiredError(
            "generate_epithet_candidates requires an injected client; got None"
        )
    if not get_profile("title_nomination").enabled:
        return None
    _require_registered()
    try:
        system, user = build_nomination_prompt(context)
    except (PromptUnavailableError, KeyError, TypeError) as exc:
        del exc
        return None
    descriptor = ChatRequestDescriptor(
        messages=(system, user),
        schema_id="title_nomination",
    )
    text = yield guarded_call("title_nomination", client, descriptor)
    if text is _TITLE_NOMINATION_DEGRADED:
        return None
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    candidates = parsed.get("candidates") if isinstance(parsed, Mapping) else None
    if not isinstance(candidates, Sequence) or len(candidates) != CANDIDATES_PER_ROUND:
        return None
    return filter_candidates(
        candidates,
        player_name=context.player_name,
        fixed_displays=context.fixed_displays,
        owned_epithet_displays=context.owned_epithet_displays,
    )


__all__ = [
    "BALLOT_TOP",
    "BASIS_MAX_CHARS",
    "CANDIDATES_PER_ROUND",
    "DISPLAY_MAX_CHARS",
    "DISPLAY_MIN_CHARS",
    "TITLE_NOMINATION_OUTPUT_SCHEMA",
    "EpithetCandidate",
    "NominationContext",
    "TitleNominationClientRequiredError",
    "build_nomination_prompt",
    "display_form_valid",
    "filter_candidates",
    "generate_epithet_candidates",
    "register_title_nomination",
    "summarize_event_logs",
]
