"""Generation pipeline (pipeline design doc §4-§5).

The guarded generation entry point, the degrade fallback, the raw-wire output
schema, and the layer's atomic guardrail-hook registration. ``generate_action_options``
runs the guardrail's validation-retry-degrade loop (with the degrade fallback
and the raw-wire output schema installed by ``register_action_options``). The
same import discipline holds: no Evennia import, no state writer, no live
transport, and no module-level logger binding at module time; the only outputs
are the frozen ``OptionSet`` proposal and ``None``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

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
from world.prompts.loader import PromptUnavailableError

from world.ai.action_options.cards import (
    CONTEXT_KIND,
    FREEFORM_ACTION_CODE,
    MIN_CARDS,
    OptionSet,
    OptionsValidationError,
)
from world.ai.action_options.context import (
    ActionOptionsBindingError,
    ActionOptionsClientRequiredError,
    ActionOptionsInputError,
    ActionOptionsNotRegisteredError,
)
from world.ai.action_options.ladder import (
    _STAGE_BY_CODE,
    parse_action_options_payload,
    validate_optionset,
)
from world.ai.action_options.prompt import build_action_options_prompt

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from web.webclient.presentation.affordances import AffordanceView
    from world.ai.action_options.context import ActionOptionsContext

# ==== Generation pipeline (pipeline design doc §4-§5) ====


# The raw model wire shape (schema design doc §5): ``context_kind`` plus
# ``cards`` where a known_action card carries action_code/label and optional
# params/hint, and a freeform card carries npc_index/label and optional hint.
# The caller-injected ``fingerprint``/``status`` (and the enriched
# ``kind``/``action_code``/``params``) never appear here (design D-7); the
# exact-field parser enforces the same contract with named rejections.
ACTION_OPTIONS_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["context_kind", "cards"],
    "additionalProperties": False,
    "properties": {
        "context_kind": {"type": "string", "enum": [CONTEXT_KIND]},
        "cards": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["label"],
                "additionalProperties": False,
                "properties": {
                    "label": {"type": "string"},
                    "hint": {"type": "string"},
                    "action_code": {"type": "string"},
                    "params": {"type": "object"},
                    "npc_index": {"type": "integer", "minimum": 0},
                },
                "oneOf": [
                    {"required": ["action_code"]},
                    {"required": ["npc_index"]},
                ],
            },
        },
    },
}

_ACTION_OPTIONS_DEGRADED = object()


def _degrade_fallback() -> object:
    """Return the sentinel so the entry point can map it to the public ``None``."""
    return _ACTION_OPTIONS_DEGRADED


def _resolve_freeform_bindings(
    payload: Mapping[str, Any], npc_bindings: tuple[int, ...]
) -> dict[str, Any]:
    """Resolve every freeform card's ``{npc_index}`` against the bound NPC list.

    The prompt's bound NPC list fixes the positional order; an out-of-range
    index, or a target already bound by an earlier freeform card in the same
    proposal, rejects the card with a binding error (design D-4). Resolved
    cards carry the enriched freeform shape (``kind``, ``action_code``,
    ``params``) so the ladder's stage-0 enrichment keeps them freeform and
    stage 9 validates the binding-only params.
    """
    resolved_cards: list[dict[str, Any]] = []
    bound_targets: set[int] = set()
    for card in payload["cards"]:
        if "npc_index" not in card:
            resolved_cards.append(dict(card))
            continue
        index = card["npc_index"]
        if index < 0 or index >= len(npc_bindings):
            raise ActionOptionsBindingError(
                f"freeform npc_index {index} is outside the bound NPC list"
            )
        target = npc_bindings[index]
        if target in bound_targets:
            raise ActionOptionsBindingError(
                f"freeform npc_index {index} binds target {target} twice"
            )
        bound_targets.add(target)
        resolved = {key: value for key, value in card.items() if key != "npc_index"}
        resolved["kind"] = "freeform"
        resolved["action_code"] = FREEFORM_ACTION_CODE
        resolved["params"] = {"npc_id": target}
        resolved_cards.append(resolved)
    return {"context_kind": payload["context_kind"], "cards": resolved_cards}


def _stage_message(code: str) -> str:
    return f"stage {_STAGE_BY_CODE.get(code, 0)}: {code}"


def _evaluate_enriched(
    parsed: Any,
    *,
    fingerprint: str,
    affordances: tuple[AffordanceView, ...],
    npc_bindings: tuple[int, ...],
    leak_blocklist: frozenset[str],
) -> tuple[OptionSet | None, list[str]]:
    """Total enrichment + binding + ladder evaluation; never raises (design D-3).

    Returns ``(OptionSet, [])`` on success, or ``(None, [message])`` where the
    message is a named error for the guardrail's retry loop: ``"stage N: <code>"``
    for ladder/parse rejections, the binding error text for freeform resolution,
    and a generation-rule message for sets the ladder accepts below ``MIN_CARDS``.
    Every parsing, enrichment, binding, and ladder exception is converted here —
    nothing escapes into ``guarded_call``, which would errback the Deferred
    instead of retrying.
    """
    try:
        payload = parse_action_options_payload(parsed)
    except OptionsValidationError as exc:  # observability: ignore R2: error becomes the retry-feedback message, not a log
        return None, [_stage_message(exc.code)]
    try:
        resolved = _resolve_freeform_bindings(payload, npc_bindings)
    except ActionOptionsBindingError as exc:  # observability: ignore R2: error becomes the retry-feedback message, not a log
        return None, [str(exc)]
    try:
        optionset = validate_optionset(
            resolved,
            fingerprint=fingerprint,
            affordances=affordances,
            leak_blocklist=leak_blocklist,
        )
    except OptionsValidationError as exc:  # observability: ignore R2: error becomes the retry-feedback message, not a log
        return None, [_stage_message(exc.code)]
    except (TypeError, ValueError) as exc:  # observability: ignore R2: error becomes the bounded internal-error feedback message
        return None, [f"internal error: {type(exc).__name__}: {exc}"]
    if len(optionset.cards) < MIN_CARDS:
        return None, [f"generation rule: fewer than {MIN_CARDS} cards proposed"]
    return optionset, []


def _make_enriched_validator(
    *,
    fingerprint: str,
    affordances: tuple[AffordanceView, ...],
    npc_bindings: tuple[int, ...],
    leak_blocklist: frozenset[str],
) -> Callable[[Any], list[str]]:
    """Return the per-call semantic validator bound to this call's data (D-2).

    The closure is carried by the request descriptor, never registered: it
    captures only this call's immutable copies of the fingerprint, affordance
    tuple, NPC bindings, and leak blocklist, so an interleaved second call can
    never observe another call's data.
    """

    def validate(parsed: Any) -> list[str]:
        _, errors = _evaluate_enriched(
            parsed,
            fingerprint=fingerprint,
            affordances=affordances,
            npc_bindings=npc_bindings,
            leak_blocklist=leak_blocklist,
        )
        return errors

    return validate


def _is_registered() -> bool:
    """True when the guardrail registries hold every action_options hook."""
    if guardrail._degrade_fallbacks.get("action_options") is not _degrade_fallback:
        return False
    return _OUTPUT_SCHEMAS.get("action_options") is ACTION_OPTIONS_OUTPUT_SCHEMA


def _require_registered() -> None:
    if not _is_registered():
        raise ActionOptionsNotRegisteredError(
            "the action_options layer is not registered; call register_action_options() first"
        )


def _uninstall_fallback() -> None:
    if guardrail._degrade_fallbacks.get("action_options") is _degrade_fallback:
        del guardrail._degrade_fallbacks["action_options"]


def _uninstall_schema() -> None:
    if _OUTPUT_SCHEMAS.get("action_options") is ACTION_OPTIONS_OUTPUT_SCHEMA:
        del _OUTPUT_SCHEMAS["action_options"]


def _uninstall_all_own_hooks() -> None:
    """Remove every action_options hook this module installed (by identity)."""
    _uninstall_fallback()
    _uninstall_schema()


def register_action_options() -> None:
    """Install the action_options layer's guardrail hooks atomically and idempotently.

    Registers the sentinel degrade fallback and the raw-wire output schema
    (design D-7). No semantic validators are registered — the ladder owns every
    text gate, and the per-call closure rides the request descriptor (D-2). On
    a partial failure every hook belonging to this module (by identity) is
    removed before the error propagates, so the layer is never left
    half-registered. A second call is a no-op that keeps the first
    registration.
    """
    if _is_registered():
        return
    try:
        if guardrail._degrade_fallbacks.get("action_options") is not _degrade_fallback:
            register_degrade_fallback("action_options", _degrade_fallback)
        if _OUTPUT_SCHEMAS.get("action_options") is not ACTION_OPTIONS_OUTPUT_SCHEMA:
            register_output_schema("action_options", ACTION_OPTIONS_OUTPUT_SCHEMA)
    except (GuardrailRegistrationError, DuplicateSchemaError):
        _uninstall_all_own_hooks()
        raise


def _log_bounded_diagnostic(problem: str) -> None:
    """Log one bounded degrade diagnostic through the observability facade."""
    from world.observability import log_warn

    log_warn("action_options_diagnostic", context={"problem": problem})


@defer.inlineCallbacks


def generate_action_options(
    context: ActionOptionsContext,
    client: Any,
    *,
    fingerprint: str,
):
    """Run the action_options layer's guarded pipeline for one proposal.

    Args:
        context: The frozen bounded context (``build_options_context`` output)
            whose affordance tuple is the vocabulary-lock source and whose
            ``leak_blocklist`` feeds the ladder's leak gates.
        client: The injected client protocol (``OpenAICompatClient`` or
            ``FakeLLMClient``); an explicit ``None`` is rejected with
            ``ActionOptionsClientRequiredError`` before any prompt construction
            or transport interaction.
        fingerprint: The caller-supplied opaque situation fingerprint; carried
            through into the enriched ``OptionSet`` and into the ladder entry
            point, never rendered into the prompt.

    Returns:
        A Deferred resolving to a frozen ``OptionSet`` (``status: "ready"``,
        3-5 cards in the model's order) on success, or to ``None`` — the single
        public degraded marker — when the profile is disabled (before any
        prompt construction or transport work), the prompt key is unavailable,
        the transport fails (no retry loop; the trigger service memoizes), the
        retry budget is exhausted, or an over-budget context input raises
        ``ActionOptionsInputError``. No state change is ever made.
    """
    if client is None:
        raise ActionOptionsClientRequiredError(
            "generate_action_options requires an injected client; got None"
        )
    if not get_profile("action_options").enabled:
        return None
    _require_registered()
    try:
        system, user = build_action_options_prompt(context)
    except (PromptUnavailableError, ActionOptionsInputError) as exc:  # observability: ignore R2: logged via _log_bounded_diagnostic below
        _log_bounded_diagnostic(str(exc))
        return None
    npc_bindings = tuple(entry.npc_id for entry in context.npc_entries)
    descriptor = ChatRequestDescriptor(
        messages=(system, user),
        schema_id="action_options",
        semantic_validators={
            "enriched_optionset": _make_enriched_validator(
                fingerprint=fingerprint,
                affordances=context.affordances,
                npc_bindings=npc_bindings,
                leak_blocklist=context.leak_blocklist,
            ),
        },
    )
    text = yield guarded_call("action_options", client, descriptor)
    if text is _ACTION_OPTIONS_DEGRADED:
        return None
    parsed = json.loads(text)
    optionset, errors = _evaluate_enriched(
        parsed,
        fingerprint=fingerprint,
        affordances=context.affordances,
        npc_bindings=npc_bindings,
        leak_blocklist=context.leak_blocklist,
    )
    if optionset is None:
        _log_bounded_diagnostic(
            "accepted text failed strict re-validation: " + " | ".join(errors)
        )
        return None
    return optionset
