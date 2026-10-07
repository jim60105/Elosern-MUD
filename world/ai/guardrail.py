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
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import uuid4

from jsonschema import Draft7Validator
from twisted.internet import defer

from world.observability import log_debug, log_info
from world.observability import transcript as llm_transcript

from world.ai.errors import LLMTransportError
from world.ai.profiles import LAYER_NAMES, UnknownLayerError, get_profile, profile_secrets
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


@dataclass(frozen=True)
class GuardrailHooks:
    """One layer's guardrail hooks, installed and rolled back as a unit.

    Encapsulates the skip-if-identity registration dance every layer used to
    hand-roll: the degrade fallback is registered only when the registry holds
    a different object (``is not`` this hook's own), and each semantic
    validator only when the entry is not this hook's own — so a second call is
    a no-op and foreign hooks with the same names are never overridden. Layer
    keys are validated by ``_require_layer`` inside the registrar functions.

    On a partial failure (``GuardrailRegistrationError``, e.g. a foreign hook
    already holds one of the names) every own hook is removed by identity —
    regardless of whether it was installed by the failing call or
    pre-existed from an earlier attempt — before the error re-raises, so a
    layer is never left half-registered and foreign hooks stay untouched.
    The layer modules keep their public ``register_*`` functions and data
    declarations; this helper is the single copy of the mutation dance.
    """

    layer: str
    fallback: DegradeFallback
    validators: Mapping[str, SemanticValidator]

    def install(self) -> None:
        """Register the layer's fallback and validators; roll back own hooks on failure."""
        try:
            if _degrade_fallbacks.get(self.layer) is not self.fallback:
                register_degrade_fallback(self.layer, self.fallback)
            for name, validator in self.validators.items():
                registered = _semantic_validators.get(self.layer, {})
                if registered.get(name) is validator:
                    continue
                register_semantic_validator(self.layer, name, validator)
        except GuardrailRegistrationError:
            self.uninstall_own()
            raise

    def uninstall_own(self) -> None:
        """Delete only the hooks whose object is this module's own."""
        fallbacks = _degrade_fallbacks
        if fallbacks.get(self.layer) is self.fallback:
            del fallbacks[self.layer]
        validators = _semantic_validators.get(self.layer, {})
        for name, validator in self.validators.items():
            if validators.get(name) is validator:
                del validators[name]


def _degrade(layer: str) -> Any:
    fallback = _degrade_fallbacks.get(layer)
    if fallback is None:
        raise NoDegradeFallbackError(layer)
    return fallback()


def _timestamp() -> str:
    """Local ISO-8601 timestamp with offset for transcript records."""
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


class CallIdTap:
    """Forwarding client wrapper that remembers the guarded ``call_id``.

    ``guarded_call`` reports its identifier to the client it was handed
    (``record_call_id``), so a caller that wraps its client in a fresh tap
    per request can name the actual call in its own failure event — even
    when the call degraded without reaching the transport. ``latest`` stays
    ``None`` when no guarded call happened, so nothing is fabricated. Wrap
    outermost: inner forwarding wrappers do not relay ``record_call_id``.
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.call_ids: list[str] = []

    def record_call_id(self, call_id: str) -> None:
        self.call_ids.append(call_id)

    @property
    def latest(self) -> str | None:
        return self.call_ids[-1] if self.call_ids else None

    def get_response(self, descriptor: ChatRequestDescriptor):
        return self._inner.get_response(descriptor)


class _GuardedCall:
    """Correlation state for one guarded call: id, timing, per-attempt errors."""

    def __init__(self, layer: str, profile: Any) -> None:
        self.call_id = uuid4().hex
        self.layer = layer
        self.profile = profile
        self.started = time.monotonic()
        self.attempts: list[dict[str, Any]] = []

    def descriptor(
        self,
        attempt: int,
        messages: tuple[dict[str, str], ...],
        output_schema: Mapping[str, Any] | None,
        base: ChatRequestDescriptor,
    ) -> ChatRequestDescriptor:
        return ChatRequestDescriptor(
            messages,
            output_schema,
            base.schema_id,
            base.semantic_validators,
            call_id=self.call_id,
            attempt=attempt,
            layer=self.layer,
        )

    def note_attempt(self, attempt: int, errors: list[str]) -> None:
        self.attempts.append({"attempt": attempt, "validation_errors": list(errors)})

    def settle(self, result: str, reason: str | None, final_text: str | None = None) -> None:
        """Write the single ``llm_call`` event and the transcript ``outcome``.

        Neither sink raises (the facade and the transcript both contain their
        own failures), so settling can never turn a degraded call into a
        second, ``rejected`` settlement.
        """
        ms = int((time.monotonic() - self.started) * 1000)
        context: dict[str, Any] = {
            "call_id": self.call_id,
            "layer": self.layer,
            "profile": self.profile.model,
            "ms": ms,
            "result": result,
        }
        if reason is not None:
            context["reason"] = reason
        log_info("llm_call", context=context)
        try:
            secrets = profile_secrets(self.profile)
        except Exception:  # observability: ignore R2: an unreadable profile skips the outcome record rather than risk an unscrubbed write
            return
        llm_transcript.write(
            {
                "kind": "outcome",
                "call_id": self.call_id,
                "ts": _timestamp(),
                "layer": self.layer,
                "profile": self.profile.model,
                "ms": ms,
                "result": result,
                "reason": reason,
                "attempts": self.attempts,
                "final_text": final_text if result == "ok" else None,
            },
            secrets=secrets,
        )


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

    Observability: exactly one ``llm_call`` boundary event and one
    transcript ``outcome`` record per call, sharing a fresh ``call_id`` —
    ``ok``, ``degraded`` (with the degrade reason), or ``rejected`` when an
    unexpected error escapes the pipeline (including a failing degrade
    fallback); escaping errors are re-raised unchanged. The degraded
    settlement is written only after the fallback actually returned, so a
    raising fallback yields one ``rejected`` settlement, never a prior
    ``degraded``. An unknown layer raises before any call exists, so it
    settles nothing. Each attempt descriptor carries the ``call_id``,
    attempt index and layer so a real transport stamps its ``exchange``.
    """
    profile = get_profile(layer)
    call = _GuardedCall(layer, profile)
    record_call_id = getattr(client, "record_call_id", None)
    if callable(record_call_id):
        record_call_id(call.call_id)
    try:
        result = yield _guarded_pipeline(layer, profile, client, descriptor, call)
    except Exception as error:
        call.settle("rejected", f"unexpected_error:{type(error).__name__}")
        raise
    return result


@defer.inlineCallbacks
def _guarded_pipeline(
    layer: str, profile: Any, client: Any, descriptor: ChatRequestDescriptor, call: _GuardedCall
):
    """One validation-retry-degrade pass; settles its own terminal outcome."""
    if not profile.enabled:
        fallback = _degrade(layer)
        call.settle("degraded", "profile_disabled")
        return fallback

    output_schema = resolve_output_schema(
        descriptor.output_schema, descriptor.schema_id
    )
    budget = 1 + profile.max_retries
    messages = descriptor.messages
    for attempt in range(budget):
        attempt_descriptor = call.descriptor(attempt, messages, output_schema, descriptor)
        try:
            text = yield client.get_response(attempt_descriptor)
        except LLMTransportError:  # observability: ignore R2: llm_call event below; the client layer owns the llm_transport_error chain
            call.note_attempt(attempt, [])
            fallback = _degrade(layer)
            call.settle("degraded", "transport_error")
            return fallback
        try:
            errors = _validate_output(
                layer,
                text,
                output_schema,
                attempt_descriptor.semantic_validators,
            )
        except LLMTransportError:  # observability: ignore R2: llm_call event below; unparseable output is fully named by the degrade reason
            call.note_attempt(attempt, [])
            fallback = _degrade(layer)
            call.settle("degraded", "transport_error")
            return fallback
        call.note_attempt(attempt, errors)
        if not errors:
            call.settle("ok", None, final_text=text)
            return text
        log_debug(
            "llm_call_retry",
            context={
                "call_id": call.call_id,
                "layer": layer,
                "attempt": attempt,
                "errors": len(errors),
            },
        )
        if attempt < budget - 1:
            messages = messages + (_error_message(errors),)
    fallback = _degrade(layer)
    call.settle("degraded", "invalid_output")
    return fallback
