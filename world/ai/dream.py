"""Dream collaborator layer: guarded explicit exchange presentation (design 6.4).

This module owns the generative half of the W3 dream-explicit-presentation
boundary: one validated exchange that combines explicit sexual scene prose and
the obscured counterpart's dialogue while the player negotiates story direction,
and the deterministic, generation-free ending.

The layer is a separate collaborator capability, distinct from ``scenario_director``
even when both share a deployment profile: it receives only the confirmed
creative preferences and a caller-supplied spoiler-filtered adventure summary,
never StoryDirector hidden answers, system fields, or another owner's private
cognition. It declares its own guardrail hooks, output schema and profile slot,
so capability history and permissions are never shared.

Server-owned track (design 6.4)
-------------------------------

The phase a response must describe is computed by
:mod:`world.narrative.dream_track` from the durable exchange count and passed to
the model as the ``phase`` field; the per-call ``phase_fidelity`` validator
rejects any other value, so the generated response describes the server-supplied
phase and can never advance the track. The explicit sexual content itself is
accepted for this capability: only hidden metadata/spoilers, named-deity claims,
divine-mystery disclosures and authoritative state-change claims are rejected.

Offline behavior is the existing guardrail degrade path: a disabled profile,
transport failure or exhausted retry budget resolves to ``None`` (no fabricated
prose), and :func:`world.narrative.dream_track.render_ending` still closes the
session deterministically without a model call.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from twisted.internet import defer

from world.ai import guardrail
from world.ai.guardrail import (
    GuardrailHooks,
    GuardrailRegistrationError,
    guarded_call,
)
from world.ai.schemas import ChatRequestDescriptor
from world.ai.schemas.registry import (
    DuplicateSchemaError,
    _OUTPUT_SCHEMAS,
    register_output_schema,
)
from world.lore.sexual_vocab import AROUSAL_LEVELS
from world.narrative.dream_session import MAX_EXCHANGES, MAX_RENDERED_INPUT_CHARS
from world.narrative.dream_track import (
    MODE_SUMMARY,
    DreamTrackState,
    exchange_mode,
    prospective_state,
)
from world.observability import log_info
from world.prompts.loader import PromptUnavailableError, render_prompt

# Output bounds: the combined scene + dialogue response is one JSON object. At
# the conservative two-tokens-per-Traditional-Chinese-code-point estimate the
# pair costs roughly 2,800 output tokens, so the layer profile reserves 3,072.
MAX_SCENE_CHARS = 900
MAX_DIALOGUE_CHARS = 500

# Bounded prompt context: the caller-supplied adventure summary and the
# confirmed creative preferences are capped deterministically so a long history
# cannot produce an unbounded request.
MAX_ADVENTURE_LINES = 8
MAX_ADVENTURE_LINE_CHARS = 200
MAX_PREFERENCE_ITEMS = 16
MAX_PREFERENCE_ITEM_CHARS = 120

_TRUNCATION_MARKER = "…"
_CJK_START = "\u4e00"
_CJK_END = "\u9fff"

# Closed guardrail policy vocabularies for this capability. The obscured
# counterpart must never assert a named deity, disclose the canonical divine
# mysteries, leak system/metadata fields, or claim an authoritative world-state
# change. These are policy markers, not prose: the explicit scene prose itself
# is accepted.
FORBIDDEN_DIVINE_MARKERS = ("光明女神", "暗之女神", "知識女神")
FORBIDDEN_DIVINE_MYSTERY_MARKERS = ("諸神確實存在", "三位神祇", "始祖神的身分", "神的後裔")
FORBIDDEN_METADATA_MARKERS = (
    "系統提示",
    "系統欄位",
    "系統訊息",
    "metadata",
    "spoiler",
    "隱藏答案",
    "hidden_answer",
)
FORBIDDEN_STATE_CHANGE_MARKERS = (
    "任務已完成",
    "任務完成",
    "任務已接受",
    "已獲得物品",
    "已取得物品",
    "物品已入袋",
    "已解鎖",
    "等級提升",
    "經驗值增加",
    "已提升技能",
    "已加入隊伍",
    "關係已改變",
    "永久提升",
    "已治癒",
)

DREAM_EXCHANGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["scene", "dialogue", "phase"],
    "additionalProperties": False,
    "properties": {
        "scene": {
            "type": "string",
            "minLength": 1,
            "maxLength": MAX_SCENE_CHARS,
        },
        "dialogue": {
            "type": "string",
            "minLength": 1,
            "maxLength": MAX_DIALOGUE_CHARS,
        },
        "phase": {"type": "string", "enum": list(AROUSAL_LEVELS)},
    },
}


class DreamClientRequiredError(TypeError):
    """Raised when ``generate_dream_exchange`` is called with an explicit ``None`` client."""


class DreamNotRegisteredError(RuntimeError):
    """Raised when ``generate_dream_exchange`` runs before the hooks are installed."""


@dataclass(frozen=True)
class DreamExchange:
    """One validated explicit dream exchange: scene prose plus counterpart dialogue."""

    scene: str
    dialogue: str
    phase: str
    completed: int
    mode: str


_DREAM_DEGRADED = object()


def _degrade_fallback() -> object:
    """Return the sentinel so the entry point can map it to the public ``None``."""
    return _DREAM_DEGRADED


def _field(parsed: Any, name: str) -> Any:
    return parsed.get(name) if isinstance(parsed, Mapping) else None


def _response_text(parsed: Any) -> str:
    fields = (_field(parsed, "scene"), _field(parsed, "dialogue"))
    parts = [value for value in fields if isinstance(value, str)]
    return "\n".join(parts)


def _validate_scene_non_empty(parsed: Any) -> list[str]:
    scene = _field(parsed, "scene")
    if not isinstance(scene, str) or not scene.strip():
        return ["dream scene must be nonempty explicit prose"]
    return []


def _validate_dialogue_non_empty(parsed: Any) -> list[str]:
    dialogue = _field(parsed, "dialogue")
    if not isinstance(dialogue, str) or not dialogue.strip():
        return ["dream dialogue must be nonempty counterpart speech"]
    return []


def _validate_has_cjk(parsed: Any) -> list[str]:
    text = _response_text(parsed)
    if not any(_CJK_START <= ch <= _CJK_END for ch in text):
        return ["dream exchange must contain Traditional Chinese prose"]
    return []


def _validate_no_forbidden_markers(parsed: Any, markers: Sequence[str], label: str) -> list[str]:
    # Casefolded so the ASCII policy markers are matched regardless of casing
    # (the CJK markers are unaffected); the response keys are schema-closed, so
    # scanning scene+dialogue covers the whole response body.
    text = _response_text(parsed).casefold()
    return [
        f"dream response contains a forbidden {label}: {marker!r}"
        for marker in markers
        if marker and marker.casefold() in text
    ]


def _validate_no_metadata_leak(parsed: Any) -> list[str]:
    return _validate_no_forbidden_markers(parsed, FORBIDDEN_METADATA_MARKERS, "metadata marker")


def _validate_no_state_change_claim(parsed: Any) -> list[str]:
    return _validate_no_forbidden_markers(
        parsed, FORBIDDEN_STATE_CHANGE_MARKERS, "state-change claim"
    )


def _validate_no_divine_identity(parsed: Any) -> list[str]:
    errors = _validate_no_forbidden_markers(
        parsed, FORBIDDEN_DIVINE_MARKERS, "named-deity identity"
    )
    errors.extend(
        _validate_no_forbidden_markers(
            parsed, FORBIDDEN_DIVINE_MYSTERY_MARKERS, "divine-mystery disclosure"
        )
    )
    return errors


def _make_phase_validator(phase: str) -> Callable[[Any], list[str]]:
    """Return a per-call validator bound to exactly this call's supplied phase."""

    def validate(parsed: Any) -> list[str]:
        declared = _field(parsed, "phase")
        if declared != phase:
            return ["dream phase must equal the server-supplied phase"]
        return []

    return validate


def _make_no_new_question_validator() -> Callable[[Any], list[str]]:
    """Return a per-call validator rejecting a new question in the summary exchange."""

    def validate(parsed: Any) -> list[str]:
        dialogue = _field(parsed, "dialogue")
        if isinstance(dialogue, str) and any(
            mark in dialogue for mark in ("？", "?", "\ufe16")
        ):
            return ["the summary exchange must not introduce a new question"]
        return []

    return validate


_VALIDATORS: dict[str, Callable[[Any], list[str]]] = {
    "scene_non_empty": _validate_scene_non_empty,
    "dialogue_non_empty": _validate_dialogue_non_empty,
    "response_has_cjk": _validate_has_cjk,
    "no_metadata_leak": _validate_no_metadata_leak,
    "no_state_change_claim": _validate_no_state_change_claim,
    "no_divine_identity": _validate_no_divine_identity,
}

_HOOKS = GuardrailHooks(
    layer="dream",
    fallback=_degrade_fallback,
    validators=_VALIDATORS,
)


def _cap_string(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    if limit <= len(_TRUNCATION_MARKER):
        return value[:limit]
    return value[: limit - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER


def _bounded_adventure(adventure_summary: Any) -> list[str]:
    """Cap the spoiler-filtered adventure summary deterministically."""
    if not isinstance(adventure_summary, (list, tuple)):
        return []
    lines: list[str] = []
    for item in adventure_summary:
        if not isinstance(item, str):
            continue
        clean = item.strip()
        if clean:
            lines.append(_cap_string(clean, MAX_ADVENTURE_LINE_CHARS))
        if len(lines) >= MAX_ADVENTURE_LINES:
            break
    return lines


def _bounded_preferences(brief: Any) -> dict[str, Any] | None:
    """Serialize the confirmed creative preferences only (no owner identities)."""
    if brief is None:
        return None
    summary = _cap_string(str(getattr(brief, "summary", "")), MAX_ADVENTURE_LINE_CHARS)
    payload: dict[str, Any] = {"summary": summary}
    for field in ("themes", "atmosphere", "participants", "emphasis", "exclusions"):
        values = getattr(brief, field, ())
        items = [
            _cap_string(item, MAX_PREFERENCE_ITEM_CHARS)
            for item in (values or ())
            if isinstance(item, str) and item.strip()
        ]
        payload[field] = items[:MAX_PREFERENCE_ITEMS]
    return payload


def build_dream_prompt(
    *,
    state: DreamTrackState,
    mode: str,
    player_message: Any,
    brief: Any = None,
    adventure_summary: Any = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Build a deterministic (system, user) message pair for one dream exchange.

    The system message renders ``dream.system`` with the server-owned phase and
    exchange metadata; the user message serializes the bounded player message,
    confirmed creative preferences and the caller-supplied spoiler-filtered
    adventure summary with stable sorted JSON. No StoryDirector context, hidden
    answer, system field or another owner's data enters the request.
    """
    system = {
        "role": "system",
        "content": render_prompt(
            "dream.system",
            phase=state.level,
            climax_phase=state.climax_phase,
            mode=mode,
            exchange_number=str(state.completed),
            remaining=str(max(0, MAX_EXCHANGES - state.completed)),
        ),
    }
    payload: dict[str, Any] = {
        "player_message": _cap_string(
            "" if player_message is None else str(player_message),
            MAX_RENDERED_INPUT_CHARS,
        ),
    }
    preferences = _bounded_preferences(brief)
    if preferences is not None:
        payload["preferences"] = preferences
    adventure = _bounded_adventure(adventure_summary)
    if adventure:
        payload["adventure_summary"] = adventure
    user = {
        "role": "user",
        "content": json.dumps(payload, sort_keys=True, ensure_ascii=False),
    }
    return system, user


def _is_registered() -> bool:
    """True when the guardrail's actual registries hold every dream hook."""
    if guardrail._degrade_fallbacks.get("dream") is not _degrade_fallback:
        return False
    if _OUTPUT_SCHEMAS.get("dream") is not DREAM_EXCHANGE_SCHEMA:
        return False
    validators = guardrail._semantic_validators.get("dream", {})
    return all(validators.get(name) is validator for name, validator in _VALIDATORS.items())


def _require_registered() -> None:
    if not _is_registered():
        raise DreamNotRegisteredError(
            "the dream collaborator layer is not registered; call register_dream() first"
        )


def _uninstall_schema() -> None:
    if _OUTPUT_SCHEMAS.get("dream") is DREAM_EXCHANGE_SCHEMA:
        del _OUTPUT_SCHEMAS["dream"]


def register_dream() -> None:
    """Install the dream layer's guardrail hooks atomically and idempotently.

    Registers the sentinel degrade fallback, every semantic validator and the
    output jsonschema under the ``dream`` layer key. On a partial failure every
    hook belonging to this module (by identity) is removed before the error
    propagates, so the layer is never left half-registered. A second call is a
    no-op that swallows only this module's own duplicate registration, never an
    incompatible one. The ``dream`` capability shares no hook, schema or profile
    with ``scenario_director``.
    """
    if _is_registered():
        return
    try:
        _HOOKS.install()
        if _OUTPUT_SCHEMAS.get("dream") is not DREAM_EXCHANGE_SCHEMA:
            register_output_schema("dream", DREAM_EXCHANGE_SCHEMA)
    except (GuardrailRegistrationError, DuplicateSchemaError):
        _HOOKS.uninstall_own()
        _uninstall_schema()
        raise


@defer.inlineCallbacks
def generate_dream_exchange(
    client: Any,
    *,
    completed: int,
    player_message: Any,
    brief: Any = None,
    adventure_summary: Any = None,
):
    """Run the dream layer's guarded pipeline for one exchange.

    Args:
        client: The injected client protocol (``OpenAICompatClient`` or
            ``FakeLLMClient``); never imported directly here. An explicit
            ``None`` is rejected with ``DreamClientRequiredError`` before any
            prompt construction or transport interaction.
        completed: The session's durable completed-exchange count. The
            server-owned prospective phase is derived from it, so retries and
            duplicate deliveries reuse exactly that phase.
        player_message: The bounded player message for this turn.
        brief: The confirmed collaborator creative preferences (preferences
            only), or ``None``.
        adventure_summary: A caller-supplied spoiler-filtered adventure summary
            as plain strings, or ``None``.

    Returns:
        A Deferred resolving to a frozen ``DreamExchange`` on success, or to
        ``None`` -- the single public degraded marker -- when the profile is
        disabled, the transport fails, the retry budget is exhausted, the
        returned output is out of contract, or the prompt key is unavailable.
        No state change is ever made: the dream track advances only through the
        durable exchange count.
    """
    if client is None:
        raise DreamClientRequiredError(
            "generate_dream_exchange requires an injected client; got None"
        )
    _require_registered()
    state = prospective_state(completed)
    mode = exchange_mode(completed)
    try:
        system, user = build_dream_prompt(
            state=state,
            mode=mode,
            player_message=player_message,
            brief=brief,
            adventure_summary=adventure_summary,
        )
    except PromptUnavailableError:  # observability: ignore R2: a broken prompt key degrades to None; the guarded call never runs and the layer owns no prompt-layer event
        return None
    extra_validators: dict[str, Callable[[Any], list[str]]] = {
        "phase_fidelity": _make_phase_validator(state.level),
    }
    if mode == MODE_SUMMARY:
        extra_validators["no_new_question"] = _make_no_new_question_validator()
    descriptor = ChatRequestDescriptor(
        messages=(system, user),
        schema_id="dream",
        semantic_validators=extra_validators,
    )
    text = yield guarded_call("dream", client, descriptor)
    if text is _DREAM_DEGRADED:
        return None
    parsed = json.loads(text)
    log_info(
        "dream_exchange_generated",
        context={
            "layer": "dream",
            "completed": state.completed,
            "mode": mode,
            "phase": state.level,
            "climax_phase": state.climax_phase,
        },
    )
    return DreamExchange(
        scene=parsed["scene"],
        dialogue=parsed["dialogue"],
        phase=parsed["phase"],
        completed=state.completed,
        mode=mode,
    )
