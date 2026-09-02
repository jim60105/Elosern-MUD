"""Validation-retry-degrade guardrail for generative proposals (design §7.5).

``guarded_call`` is one generic pipeline: resolve the layer profile, call the
injected client, validate the returned text against the declared output schema
and every registered semantic validator (plus any per-call validators carried
by the request descriptor), retry up to ``1 + max_retries`` total
calls with the validation errors appended, and degrade to the layer's
registered fallback when the budget is exhausted or a transport failure occurs.
Semantic validators and degrade fallbacks are registered per layer by name so
changes 18-21 add their hooks without editing the pipeline.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from typing import Any

from jsonschema import Draft7Validator
from twisted.internet import defer

from world.observability import log_debug, log_info

from world.ai.errors import LLMTransportError
from world.ai.profiles import LAYER_NAMES, UnknownLayerError, get_profile
from world.ai.schemas.descriptor import ChatRequestDescriptor
from world.ai.schemas.registry import resolve_output_schema

SemanticValidator = Callable[[Any], list[str]]
DegradeFallback = Callable[[], Any]


class GuardrailRegistrationError(ValueError):
    """Raised when a layer hook is registered twice or for an unknown layer."""


class NoDegradeFallbackError(KeyError):
    """Raised when degradation is required but no fallback is registered."""


_semantic_validators: dict[str, dict[str, SemanticValidator]] = {}
_degrade_fallbacks: dict[str, DegradeFallback] = {}


def register_semantic_validator(layer: str, name: str, validator: SemanticValidator) -> None:
    """Register a per-layer semantic validator under a stable name."""
    _require_layer(layer)
    validators = _semantic_validators.setdefault(layer, {})
    if name in validators:
        raise GuardrailRegistrationError(f"semantic validator {layer}.{name} already registered")
    validators[name] = validator


def register_degrade_fallback(layer: str, fallback: DegradeFallback) -> None:
    """Register the single degrade fallback for a layer."""
    _require_layer(layer)
    if layer in _degrade_fallbacks:
        raise GuardrailRegistrationError(f"degrade fallback for {layer} already registered")
    _degrade_fallbacks[layer] = fallback


def _require_layer(layer: str) -> None:
    if layer not in LAYER_NAMES:
        raise UnknownLayerError(layer)


def _degrade(layer: str) -> Any:
    fallback = _degrade_fallbacks.get(layer)
    if fallback is None:
        raise NoDegradeFallbackError(layer)
    return fallback()


def _emit_call(layer: str, profile: Any, started: float, result: str, reason: str | None) -> None:
    """Write the single ``llm_call`` boundary event for one guarded call."""
    context: dict[str, Any] = {
        "layer": layer,
        "profile": profile.model,
        "ms": int((time.monotonic() - started) * 1000),
        "result": result,
    }
    if reason is not None:
        context["reason"] = reason
    log_info("llm_call", context=context)


def _jsonschema_errors(instance: Any, schema: Mapping[str, Any]) -> list[str]:
    validator = Draft7Validator(schema)
    return [error.message for error in validator.iter_errors(instance)]


def _validate_output(
    layer: str,
    text: str,
    output_schema: Mapping[str, Any] | None,
    extra_validators: Mapping[str, SemanticValidator] | None = None,
) -> list[str]:
    """Validate one returned text; raise ``LLMTransportError`` if unparseable.

    When an output schema is declared, the text must parse as JSON; an
    unparseable body is a transport failure per the guardrail contract and
    degrades immediately rather than entering the retry loop. Per-call
    semantic validators carried by the request descriptor run after the
    layer's registered ones.
    """
    if output_schema is not None:
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise LLMTransportError(
                "malformed", "returned text is not valid JSON for the declared schema"
            ) from exc
        errors = _jsonschema_errors(parsed, output_schema)
    else:
        parsed = text
        errors = []
    for validator in _semantic_validators.get(layer, {}).values():
        errors.extend(validator(parsed))
    if extra_validators:
        for validator in extra_validators.values():
            errors.extend(validator(parsed))
    return errors


def _error_message(errors: list[str]) -> dict[str, str]:
    return {"role": "user", "content": "Validation failed: " + " | ".join(errors)}


@defer.inlineCallbacks
def guarded_call(layer: str, client: Any, descriptor: ChatRequestDescriptor):
    """Run the validation-retry-degrade pipeline for one guarded call.

    Args:
        layer: One of ``LAYER_NAMES``.
        client: The injected client protocol (``OpenAICompatClient`` or
            ``FakeLLMClient``); never imported directly here.
        descriptor: The layer-neutral per-call request descriptor.

    Returns:
        A Deferred resolving to the accepted text, or the layer's degrade
        fallback result when the profile is disabled, a transport failure
        occurs, or the retry budget is exhausted.

    Observability: exactly one ``llm_call`` boundary event per call —
    ``ok``, ``degraded`` (with the degrade reason), or ``rejected`` when an
    unexpected error escapes the pipeline (including a failing degrade
    fallback); escaping errors are re-raised unchanged. The degraded event
    is written only after the fallback actually returned, so a raising
    fallback yields one ``rejected`` event, never a prior ``degraded``.
    """
    profile = get_profile(layer)
    started = time.monotonic()
    try:
        result = yield _guarded_pipeline(layer, profile, client, descriptor, started)
    except Exception as error:
        _emit_call(layer, profile, started, "rejected", f"unexpected_error:{type(error).__name__}")
        raise
    return result


@defer.inlineCallbacks
def _guarded_pipeline(
    layer: str, profile: Any, client: Any, descriptor: ChatRequestDescriptor, started: float
):
    """One validation-retry-degrade pass; emits its own terminal event."""
    if not profile.enabled:
        fallback = _degrade(layer)
        _emit_call(layer, profile, started, "degraded", "profile_disabled")
        return fallback

    output_schema = resolve_output_schema(
        descriptor.output_schema, descriptor.schema_id
    )
    budget = 1 + profile.max_retries
    messages = descriptor.messages
    for attempt in range(budget):
        attempt_descriptor = ChatRequestDescriptor(
            messages,
            output_schema,
            descriptor.schema_id,
            descriptor.semantic_validators,
        )
        try:
            text = yield client.get_response(attempt_descriptor)
        except LLMTransportError:  # observability: ignore R2: llm_call event below; the client layer owns the llm_transport_error chain
            fallback = _degrade(layer)
            _emit_call(layer, profile, started, "degraded", "transport_error")
            return fallback
        try:
            errors = _validate_output(
                layer,
                text,
                output_schema,
                attempt_descriptor.semantic_validators,
            )
        except LLMTransportError:  # observability: ignore R2: llm_call event below; unparseable output is fully named by the degrade reason
            fallback = _degrade(layer)
            _emit_call(layer, profile, started, "degraded", "transport_error")
            return fallback
        if not errors:
            _emit_call(layer, profile, started, "ok", None)
            return text
        log_debug(
            "llm_call_retry",
            context={"layer": layer, "attempt": attempt, "errors": len(errors)},
        )
        if attempt < budget - 1:
            messages = messages + (_error_message(errors),)
    fallback = _degrade(layer)
    _emit_call(layer, profile, started, "degraded", "invalid_output")
    return fallback
