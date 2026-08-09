"""NPC dialogue layer: guarded `{speech, intent}` reply generation (design §7.4).

The ``npc_dialogue`` layer maps an NPC dialogue context to a validated frozen
``NPCDialogueReply`` through the shared validation-retry-degrade guardrail
(design §7.5). The intent kind is restricted to an eight-kind whitelist; the
deterministic engine verifies each intent before applying it (see
``world/rules/npc_intents.py``). When the caller injects the NPC's affinity
context (affinity-ai), it is serialized into the user payload for the model
and a no-leak semantic validator keeps the secret numbers out of player-facing
speech; persona-dialogue-injection extends the injected context with the
NPC's own persona block (system message) and the speaking player's block
(``player.persona``), and generalizes the no-leak validator to the caller's
per-call secret set so true trait values under an active disguise stay secret.
This module is generative and read-only: it never mutates state, never
imports a state writer, a typeclass, or a live transport, and it consumes the
client through the injected protocol exactly like ``narrator.py``. When the
layer is disabled, the transport fails, or the validation retries are
exhausted, ``generate_npc_reply`` resolves to ``None`` -- the single public
degraded marker -- so the caller can fall back to the NPC's authored greeting
or silence and the game stays fully playable offline.

Boundary contract (``tests/test_ai_transport_contract.py``): this module imports
no state writer, no live transport, and no socket.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass
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
from world.ai.schemas.registry import (
    DuplicateSchemaError,
    _OUTPUT_SCHEMAS,
    register_output_schema,
)
from world.prompts.loader import PromptUnavailableError, render_prompt

# Hard prompt bounds (design D2): a fixed maximum memory-line window with an
# explicit truncation marker, per-field string-length caps, and a bounded total
# serialized size, so a long conversation or pathological input cannot produce
# an unbounded request.
MAX_MEMORY_LINES = 12
MAX_STAT_KEYS = 20
MAX_FIELD_LENGTH = 200
MAX_TOTAL_SIZE = 12000

# Accepted-speech bound used by the length semantic validator (design D4).
MAX_SPEECH_LENGTH = 2000

# The affinity-delta bound for the adjust_relation intent (affinity-ai D-1):
# the schema bounds the value when present, and the per-kind semantic
# validator plus the deterministic applier enforce the exact single-field
# shape.
MAX_RELATION_DELTA = 10

# The eight whitelisted intent kinds (design §7.4).
NPC_INTENT_KINDS = (
    "give_item",
    "take_item",
    "offer_quest",
    "request_guild_exam",
    "adjust_relation",
    "reveal_lore",
    "party_invite",
    "none",
)

_TRUNCATION_MARKER = "…"
_CJK_START = "\u4e00"
_CJK_END = "\u9fff"
_TEMPLATE_PLACEHOLDER_RE = re.compile(
    r"\{actor\}|\{target\}|\{name\}|\{character\}|\{location\}|\{response\}"
    r"|\{data\[[^\]]*\]\}"
)


class NPCDialogueClientRequiredError(TypeError):
    """Raised when a reply call is made with an explicit ``None`` client."""


class NPCDialogueNotRegisteredError(RuntimeError):
    """Raised when the npc_dialogue layer's hooks are not installed."""


@dataclass(frozen=True)
class NPCDialogueReply:
    """A validated frozen NPC reply: display-only speech plus a whitelisted intent."""

    speech: str
    intent: dict[str, Any]


NPC_DIALOGUE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["speech", "intent"],
    "properties": {
        "speech": {"type": "string"},
        "intent": {
            "type": "object",
            "required": ["kind"],
            "properties": {
                "kind": {"type": "string", "enum": list(NPC_INTENT_KINDS)},
                "delta": {"type": "integer", "minimum": 0, "maximum": MAX_RELATION_DELTA},
                "accept": {"type": "boolean"},
            },
        },
    },
}

_NPC_DIALOGUE_DEGRADED = object()


def _degrade_fallback() -> object:
    """Return the sentinel so the entry point can map it to the public ``None``."""
    return _NPC_DIALOGUE_DEGRADED


def _validate_speech_not_empty(parsed: Any) -> list[str]:
    speech = parsed.get("speech") if isinstance(parsed, Mapping) else None
    if not isinstance(speech, str) or not speech.strip():
        return ["dialogue speech is empty or whitespace-only"]
    return []


def _validate_speech_bounded(parsed: Any) -> list[str]:
    speech = parsed.get("speech") if isinstance(parsed, Mapping) else None
    if isinstance(speech, str) and len(speech) > MAX_SPEECH_LENGTH:
        return [f"dialogue speech exceeds the {MAX_SPEECH_LENGTH}-character length cap"]
    return []


def _validate_speech_has_cjk(parsed: Any) -> list[str]:
    speech = parsed.get("speech") if isinstance(parsed, Mapping) else None
    if not isinstance(speech, str) or not any(
        _CJK_START <= ch <= _CJK_END for ch in speech
    ):
        return [
            "dialogue speech contains no CJK Unified Ideograph and is not Traditional Chinese"
        ]
    return []


def _validate_intent_kind(parsed: Any) -> list[str]:
    intent = parsed.get("intent") if isinstance(parsed, Mapping) else None
    if not isinstance(intent, Mapping):
        return ["dialogue intent must be an object"]
    kind = intent.get("kind")
    if kind not in NPC_INTENT_KINDS:
        return [f"dialogue intent.kind {kind!r} is outside the eight-kind whitelist"]
    return []


def _payload_without_kind(intent: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in intent.items() if key != "kind"}


def _validate_exam_payload(parsed: Any) -> list[str]:
    intent = parsed.get("intent") if isinstance(parsed, Mapping) else None
    if not isinstance(intent, Mapping) or intent.get("kind") != "request_guild_exam":
        return []
    payload = _payload_without_kind(intent)
    if set(payload) != {"target_rank"}:
        return [
            "request_guild_exam must carry exactly one payload field, target_rank"
        ]
    target_rank = payload["target_rank"]
    if not isinstance(target_rank, str) or not target_rank.strip():
        return ["request_guild_exam target_rank must be a non-empty string"]
    return []


def _validate_item_payload(parsed: Any) -> list[str]:
    intent = parsed.get("intent") if isinstance(parsed, Mapping) else None
    if not isinstance(intent, Mapping) or intent.get("kind") not in (
        "give_item",
        "take_item",
    ):
        return []
    payload = _payload_without_kind(intent)
    if set(payload) != {"item_key", "qty"}:
        return ["give_item/take_item must carry exactly item_key and qty"]
    item_key = payload["item_key"]
    if not isinstance(item_key, str) or not item_key.strip():
        return ["item intent item_key must be a non-empty string"]
    qty = payload["qty"]
    if isinstance(qty, bool) or not isinstance(qty, int) or qty < 1:
        return ["item intent qty must be a positive integer"]
    return []


def _validate_relation_payload(parsed: Any) -> list[str]:
    intent = parsed.get("intent") if isinstance(parsed, Mapping) else None
    if not isinstance(intent, Mapping) or intent.get("kind") != "adjust_relation":
        return []
    payload = _payload_without_kind(intent)
    if set(payload) != {"delta"}:
        return [
            "adjust_relation must carry exactly one payload field, delta"
        ]
    delta = payload["delta"]
    if (
        isinstance(delta, bool)
        or not isinstance(delta, int)
        or not (0 <= delta <= MAX_RELATION_DELTA)
    ):
        return [
            "adjust_relation delta must be an integer between 0 and "
            f"{MAX_RELATION_DELTA}"
        ]
    return []


def _validate_party_payload(parsed: Any) -> list[str]:
    intent = parsed.get("intent") if isinstance(parsed, Mapping) else None
    if not isinstance(intent, Mapping) or intent.get("kind") != "party_invite":
        return []
    payload = _payload_without_kind(intent)
    if set(payload) != {"accept"}:
        return [
            "party_invite must carry exactly one payload field, accept"
        ]
    if not isinstance(payload["accept"], bool):
        return ["party_invite accept must be a boolean"]
    return []


def _make_no_leak_validator(
    secrets: frozenset[str], *, secret_label: str = "secret number(s)"
) -> Callable[[Any], list[str]]:
    """Return a per-call semantic validator bound to this call's secret numbers.

    The validator is carried by the request descriptor (not registered), so an
    interleaved second dialogue call can never observe another call's secret
    numbers, and ordinary dialogue without an injected set is untouched.
    Secrets are plain decimal strings (the affinity value/cap plus true trait
    values under an active disguise) supplied by the caller. Speech is
    NFKC-normalized so fullwidth decimal digits (U+FF10-FF19) fold into ASCII
    and cannot bypass the decimal-substring check; stage names are unaffected
    and remain the sanctioned player-facing form.
    """
    def validate(parsed: Any) -> list[str]:
        speech = parsed.get("speech") if isinstance(parsed, Mapping) else None
        if not isinstance(speech, str):
            return []
        normalized = unicodedata.normalize("NFKC", speech)
        leaked = {number for number in secrets if number in normalized}
        if not leaked:
            return []
        return [
            f"dialogue speech echoes the {secret_label}: "
            + ", ".join(sorted(leaked))
        ]

    return validate


def _make_no_affinity_leak_validator(
    value: Any, cap: Any
) -> Callable[[Any], list[str]]:
    """Return a per-call validator bound to exactly this call's affinity numbers.

    Retained as the affinity call site's binding through the generalized
    secret-set factory, keeping the original error text so existing affinity
    behavior and tests are unchanged.
    """
    secrets = frozenset(
        str(number)
        for number in (value, cap)
        if isinstance(number, int) and not isinstance(number, bool)
    )
    return _make_no_leak_validator(secrets, secret_label="secret affinity number(s)")


def _validate_no_template_placeholder(parsed: Any) -> list[str]:
    search_text = ""
    if isinstance(parsed, Mapping):
        speech = parsed.get("speech")
        intent = parsed.get("intent")
        if isinstance(speech, str):
            search_text += speech
        if isinstance(intent, Mapping):
            search_text += json.dumps(intent, sort_keys=True)
    if _TEMPLATE_PLACEHOLDER_RE.search(search_text):
        return [
            "dialogue echoes deterministic template-placeholder formatting syntax"
        ]
    return []


_VALIDATORS: dict[str, Any] = {
    "speech_non_empty": _validate_speech_not_empty,
    "speech_bounded_length": _validate_speech_bounded,
    "speech_has_cjk": _validate_speech_has_cjk,
    "intent_kind_whitelist": _validate_intent_kind,
    "exam_payload_shape": _validate_exam_payload,
    "item_payload_shape": _validate_item_payload,
    "relation_payload_shape": _validate_relation_payload,
    "party_payload_shape": _validate_party_payload,
    "no_template_placeholder": _validate_no_template_placeholder,
}


def _cap_string(value: str) -> str:
    if len(value) <= MAX_FIELD_LENGTH:
        return value
    return value[: MAX_FIELD_LENGTH - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER


def _cap_value(value: Any) -> Any:
    if isinstance(value, dict):
        items = list(value.items())[:MAX_STAT_KEYS]
        return {_cap_string(str(key)): _cap_value(item) for key, item in items}
    if isinstance(value, (list, tuple)):
        return [_cap_value(item) for item in value[:MAX_STAT_KEYS]]
    if isinstance(value, str):
        return _cap_string(value)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    return str(value)


def _bounded_memory(memory: Any) -> list[str]:
    """Cap the chat-memory window deterministically with a truncation marker.

    Lines are consumed through a fixed-length window so the cap applies before
    the input is materialized: lines beyond the window are dropped from the
    front and replaced with an explicit marker stating how many earlier
    exchanges were omitted.
    """
    window = deque(maxlen=MAX_MEMORY_LINES)
    dropped = 0
    for line in memory:
        if len(window) == MAX_MEMORY_LINES:
            dropped += 1
        window.append(_cap_string(str(line)))
    lines = list(window)
    if dropped:
        lines = [f"（省略了較早的 {dropped} 則對話）", *lines]
    return lines


def _serialize(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _bounded_serialization(payload: Mapping[str, Any]) -> str:
    """Serialize the user payload deterministically within the total-size bound.

    Every input field is already hard-capped, so the text always fits on the
    first pass; the memory drop loop is a defensive last resort that removes
    the oldest memory lines (updating the marker) until the text fits.
    """
    text = _serialize(payload)
    if len(text) <= MAX_TOTAL_SIZE:
        return text
    memory = list(payload.get("memory", []))
    dropped = 0
    while True:
        if not memory:
            return _serialize({"player": {}, "memory": []})
        memory = memory[1:]
        dropped += 1
        candidate = dict(payload)
        candidate["memory"] = [f"（省略了較早的 {dropped} 則對話）", *memory]
        text = _serialize(candidate)
        if len(text) <= MAX_TOTAL_SIZE:
            return text


def _system_message(
    npc_context: Mapping[str, Any], npc_persona: str | None = None
) -> str:
    """Render the NPC dialogue system template with the capped identity values.

    ``npc_persona`` is the speaking NPC's flattened persona block (already
    bounded by the PersonaStore contract); it is substituted into the
    ``{persona}`` placeholder on every call, using an empty string when absent
    so the rendered message is byte-identical to the pre-persona baseline.
    """
    name = _cap_string(str(npc_context.get("name", "")))
    desc = _cap_string(str(npc_context.get("desc", "")))
    location = _cap_string(str(npc_context.get("location", "")))
    return render_prompt(
        "npc_dialogue.system",
        name=name,
        desc=desc,
        location=location,
        persona=npc_persona or "",
    )


def build_npc_dialogue_prompt(
    npc_context: Mapping[str, Any],
    player_context: Mapping[str, Any],
    memory: Any,
    affinity_context: Mapping[str, Any] | None = None,
    *,
    npc_persona: str | None = None,
    player_persona: str | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Build a deterministic (system, user) message pair for NPC dialogue.

    The system message fixes the NPC's role in 伊洛瑟恩大陸, the 正體中文
    language, and the ``{speech, intent}`` JSON output contract with the
    no-invention fidelity rule. The user message serializes the player's
    identity and ``disguised_stats`` (the values the NPC perceives) plus the
    bounded chat-memory window, using stable sorted JSON serialization with
    ``ensure_ascii=False``. An optional ``affinity_context`` block
    (``player.affinity`` carrying the true value, cap, and stage name) is
    injected through the same per-field bounds; ``None`` omits the block.
    Optional persona blocks (read-only context, already bounded by the
    PersonaStore contract) feed the speaking NPC's flattened block into the
    system message and the speaking player's flattened block as
    ``player.persona`` beside ``player.affinity``; ``None`` substitutes an
    empty ``{persona}`` value and omits the player block, keeping byte-identical
    output when absent. Identical input always produces byte-identical prompts
    with no live entity references.
    """
    system = {"role": "system", "content": _system_message(npc_context, npc_persona)}
    player = {
        "name": _cap_string(str(player_context.get("name", ""))),
        "disguised_stats": _cap_value(player_context.get("disguised_stats", {})),
    }
    if affinity_context is not None:
        player["affinity"] = _cap_value(dict(affinity_context))
    if player_persona is not None:
        player["persona"] = player_persona
    payload = {
        "player": player,
        "memory": _bounded_memory(memory),
    }
    user = {"role": "user", "content": _bounded_serialization(payload)}
    return system, user


def _is_registered() -> bool:
    """True when the guardrail's actual registries hold every npc_dialogue hook."""
    if guardrail._degrade_fallbacks.get("npc_dialogue") is not _degrade_fallback:
        return False
    validators = guardrail._semantic_validators.get("npc_dialogue", {})
    if not all(
        validators.get(name) is validator for name, validator in _VALIDATORS.items()
    ):
        return False
    return _OUTPUT_SCHEMAS.get("npc_dialogue") is NPC_DIALOGUE_OUTPUT_SCHEMA


def _require_registered() -> None:
    if not _is_registered():
        raise NPCDialogueNotRegisteredError(
            "the npc_dialogue layer is not registered; call register_npc_dialogue() first"
        )


def _uninstall_fallback() -> None:
    if guardrail._degrade_fallbacks.get("npc_dialogue") is _degrade_fallback:
        del guardrail._degrade_fallbacks["npc_dialogue"]


def _uninstall_validator(name: str) -> None:
    validators = guardrail._semantic_validators.get("npc_dialogue", {})
    if validators.get(name) is _VALIDATORS[name]:
        del validators[name]


def _uninstall_schema() -> None:
    if _OUTPUT_SCHEMAS.get("npc_dialogue") is NPC_DIALOGUE_OUTPUT_SCHEMA:
        del _OUTPUT_SCHEMAS["npc_dialogue"]


def _uninstall_all_own_hooks() -> None:
    """Remove every npc_dialogue hook that is this module's own (by identity).

    Used for rollback so a partial-failure registration can never leave a
    half-installed layer behind. Foreign hooks with the same names are left
    untouched.
    """
    _uninstall_fallback()
    for name in _VALIDATORS:
        _uninstall_validator(name)
    _uninstall_schema()


def register_npc_dialogue() -> None:
    """Install the npc_dialogue layer's guardrail hooks atomically and idempotently.

    Registers the sentinel degrade fallback, every semantic validator, and the
    output jsonschema. On a partial failure every hook belonging to this module
    (by identity) is removed before the error propagates, so the layer is never
    left half-registered. A second call is a no-op that keeps the first
    registration and swallows only this module's own duplicate registration,
    never an incompatible one.
    """
    if _is_registered():
        return
    try:
        if guardrail._degrade_fallbacks.get("npc_dialogue") is not _degrade_fallback:
            register_degrade_fallback("npc_dialogue", _degrade_fallback)
        for name, validator in _VALIDATORS.items():
            validators = guardrail._semantic_validators.get("npc_dialogue", {})
            if validators.get(name) is validator:
                continue
            register_semantic_validator("npc_dialogue", name, validator)
        if _OUTPUT_SCHEMAS.get("npc_dialogue") is not NPC_DIALOGUE_OUTPUT_SCHEMA:
            register_output_schema("npc_dialogue", NPC_DIALOGUE_OUTPUT_SCHEMA)
    except (GuardrailRegistrationError, DuplicateSchemaError):
        _uninstall_all_own_hooks()
        raise


@defer.inlineCallbacks
def generate_npc_reply(
    client: Any,
    *,
    npc_context: Mapping[str, Any],
    player_context: Mapping[str, Any],
    memory: Any,
    affinity_context: Mapping[str, Any] | None = None,
    npc_persona: str | None = None,
    player_persona: str | None = None,
    no_leak_secrets: frozenset[str] | None = None,
):
    """Run the npc_dialogue layer's guarded pipeline for one NPC reply.

    Args:
        client: The injected client protocol (``OpenAICompatClient`` or
            ``FakeLLMClient``); never imported directly here. An explicit
            ``None`` is rejected with ``NPCDialogueClientRequiredError`` before
            any prompt construction or transport interaction.
        npc_context: The NPC's plain-data identity (name, description,
            location) as the caller resolves it.
        player_context: The speaking player's plain-data identity and
            ``disguised_stats`` (what the NPC perceives).
        memory: The bounded chat-memory window lines for this conversation.
        affinity_context: The NPC's read-only affinity context for the
            speaking player (true value, cap, stage), injected as
            ``player.affinity`` in the user payload; ``None`` omits the block.
        npc_persona: The speaking NPC's flattened persona block (already
            bounded by the PersonaStore contract), substituted into the
            system message's ``{persona}`` placeholder; ``None`` substitutes
            an empty string and keeps the pre-persona baseline byte-identical.
        player_persona: The speaking player's flattened persona block,
            serialized as ``player.persona`` beside ``player.affinity`` when
            present; ``None`` omits the key.
        no_leak_secrets: The caller's per-call secret set as plain decimal
            strings. When non-empty the no-leak validator SHALL be installed
            regardless of the affinity context (so disguise true values stay
            protected without an affinity record); when absent, an affinity
            context still binds exactly its own value and cap as before.

    Returns:
        A Deferred resolving to a frozen ``NPCDialogueReply`` on success, or to
        ``None`` -- the single public degraded marker -- when the layer is
        disabled, the transport fails, or the retry budget is exhausted.
    """
    if client is None:
        raise NPCDialogueClientRequiredError(
            "generate_npc_reply requires an injected client; got None"
        )
    _require_registered()
    try:
        system, user = build_npc_dialogue_prompt(
            npc_context,
            player_context,
            memory,
            affinity_context=affinity_context,
            npc_persona=npc_persona,
            player_persona=player_persona,
        )
    except PromptUnavailableError:
        return None
    extra_validators = None
    if no_leak_secrets:
        extra_validators = {
            "no_leak": _make_no_leak_validator(no_leak_secrets)
        }
    elif affinity_context is not None:
        context = dict(affinity_context)
        extra_validators = {
            "no_affinity_leak": _make_no_affinity_leak_validator(
                context.get("value"), context.get("cap")
            )
        }
    descriptor = ChatRequestDescriptor(
        messages=(system, user),
        schema_id="npc_dialogue",
        semantic_validators=extra_validators,
    )
    text = yield guarded_call("npc_dialogue", client, descriptor)
    if text is _NPC_DIALOGUE_DEGRADED:
        return None
    parsed = json.loads(text)
    return NPCDialogueReply(speech=parsed["speech"], intent=parsed["intent"])
