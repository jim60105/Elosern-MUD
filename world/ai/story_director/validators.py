"""The ``story_director`` guardrail vocabulary: output schema and validators.

The schema bounds the raw shape of one beat proposal; the semantic validators
enforce the gates a JSON schema cannot express (a known kind, bounded
Traditional-Chinese prose, and the absolute prohibition on a proposal claiming a
state write). A proposal carries intent only — routing and materialization stay
in the deterministic core — so the vocabulary intentionally has no ``effect``
field for a model to assert.
"""

from __future__ import annotations

from typing import Any

from world.ai.guardrail import GuardrailHooks

from world.ai.story_director.proposals import (
    BEAT_KINDS,
    MAX_RECIPIENT_CHARACTERS,
    MAX_RELATION_DELTA,
    MAX_SUMMARY_CHARACTERS,
    MAX_WRITE_CLAIMS,
    MAX_WRITE_CLAIM_CHARACTERS,
    has_cjk,
)

STORY_DIRECTOR_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["kind", "summary"],
    "additionalProperties": False,
    "properties": {
        "kind": {"enum": sorted(BEAT_KINDS)},
        "summary": {
            "type": "string",
            "minLength": 1,
            "maxLength": MAX_SUMMARY_CHARACTERS,
        },
        "recipient": {
            "type": "string",
            "maxLength": MAX_RECIPIENT_CHARACTERS,
        },
        "relation_delta": {
            "type": "integer",
            "minimum": 0,
            "maximum": MAX_RELATION_DELTA,
        },
        "writes": {
            "type": "array",
            "maxItems": MAX_WRITE_CLAIMS,
            "items": {"type": "string", "maxLength": MAX_WRITE_CLAIM_CHARACTERS},
        },
    },
}

_TEMPLATE_PLACEHOLDER_TOKENS = ("{actor}", "{target}", "{data[")


def _fallback() -> None:
    """Degrade result: no content. A director that cannot produce a valid beat
    schedules nothing rather than substituting replacement filler."""
    return None


def _validate_kind_known(parsed: Any) -> list[str]:
    kind = parsed.get("kind") if isinstance(parsed, dict) else None
    if kind not in BEAT_KINDS:
        return [f"kind must be one of {sorted(BEAT_KINDS)}."]
    return []


def _validate_summary_bounded_cjk(parsed: Any) -> list[str]:
    summary = parsed.get("summary") if isinstance(parsed, dict) else None
    if not isinstance(summary, str) or not summary.strip():
        return ["summary must contain nonempty Traditional Chinese prose."]
    if len(summary.strip()) > MAX_SUMMARY_CHARACTERS:
        return [f"summary must be at most {MAX_SUMMARY_CHARACTERS} characters."]
    if not has_cjk(summary):
        return ["summary must be written in Traditional Chinese prose."]
    return []


def _validate_no_write_claims(parsed: Any) -> list[str]:
    """A proposal may never claim a direct state write.

    Value-only proposals go through a deterministic owner; a payload asserting
    a trait/quest/room mutation is a rejected attempt, not a routed effect.
    """
    writes = parsed.get("writes") if isinstance(parsed, dict) else None
    if writes:
        return ["a beat proposal may not claim direct state writes."]
    return []


def _validate_no_template_placeholder(parsed: Any) -> list[str]:
    if not isinstance(parsed, dict):
        return []
    text = " ".join(
        str(parsed.get(field, "")) for field in ("summary", "recipient")
    )
    if any(token in text for token in _TEMPLATE_PLACEHOLDER_TOKENS):
        return ["summary/recipient must not contain a template placeholder."]
    return []


_HOOKS = GuardrailHooks(
    "story_director",
    _fallback,
    {
        "beat_kind_known": _validate_kind_known,
        "beat_summary_bounded_cjk": _validate_summary_bounded_cjk,
        "beat_no_write_claims": _validate_no_write_claims,
        "beat_no_template_placeholder": _validate_no_template_placeholder,
    },
)
