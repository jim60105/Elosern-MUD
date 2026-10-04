"""Guarded generation of one value-only beat proposal (story-director-beats).

The entry point runs the shared validation-retry-degrade guardrail for the
``story_director`` layer and returns at most one :class:`BeatProposal`. A
degrade trigger — disabled transport, exhausted validation, a malformed body,
or an unexpected conversion failure — resolves to ``None``: no replacement
filler and no fabricated beat, matching the boundary's no-content contract.

Registration is atomic with rollback, idempotent, and boot-tolerant, exactly
like the other layers; production wires it from ``at_server_start`` after
``evennia._init()``.
"""

from __future__ import annotations

import json
from typing import Any

from twisted.internet import defer

from world.ai.guardrail import (
    GuardrailRegistrationError,
    guarded_call,
)
from world.ai.schemas import ChatRequestDescriptor
from world.ai.schemas.registry import (
    DuplicateSchemaError,
    _OUTPUT_SCHEMAS,
    register_output_schema,
)

from world.ai.story_director.proposals import BeatProposal
from world.ai.story_director.validators import (
    STORY_DIRECTOR_OUTPUT_SCHEMA,
    _HOOKS,
)


class StoryDirectorClientRequiredError(TypeError):
    """Raised when generation is called with an explicit ``None`` client."""


class StoryDirectorNotRegisteredError(RuntimeError):
    """Raised when generation runs before the layer hooks are installed."""


def _is_registered() -> bool:
    """True when the guardrail's actual registries hold this layer's hooks."""
    from world.ai.guardrail import _degrade_fallbacks, _semantic_validators

    if _degrade_fallbacks.get("story_director") is not _HOOKS.fallback:
        return False
    registered = _semantic_validators.get("story_director", {})
    if any(registered.get(name) is not validator for name, validator in _HOOKS.validators.items()):
        return False
    return _OUTPUT_SCHEMAS.get("story_director") is STORY_DIRECTOR_OUTPUT_SCHEMA


def _require_registered() -> None:
    if not _is_registered():
        raise StoryDirectorNotRegisteredError(
            "story_director layer hooks are not registered."
        )


def _uninstall_schema() -> None:
    if _OUTPUT_SCHEMAS.get("story_director") is STORY_DIRECTOR_OUTPUT_SCHEMA:
        del _OUTPUT_SCHEMAS["story_director"]


def register_story_director() -> None:
    """Install the story_director layer's guardrail hooks atomically.

    On a partial failure every own hook is removed before the error
    propagates. A second call is a no-op that keeps the first registration and
    swallows only this module's own duplicate-registration errors.
    """
    if _is_registered():
        return
    try:
        _HOOKS.install()
        if _OUTPUT_SCHEMAS.get("story_director") is not STORY_DIRECTOR_OUTPUT_SCHEMA:
            register_output_schema("story_director", STORY_DIRECTOR_OUTPUT_SCHEMA)
    except (GuardrailRegistrationError, DuplicateSchemaError):
        _HOOKS.uninstall_own()
        _uninstall_schema()
        raise


def build_generation_descriptor(messages: tuple[dict[str, str], ...]) -> ChatRequestDescriptor:
    """The per-call descriptor carrying the story_director output contract."""
    return ChatRequestDescriptor(messages=messages, schema_id="story_director")


@defer.inlineCallbacks
def generate_beat_proposal(client: Any, messages: tuple[dict[str, str], ...]):
    """Return one frozen :class:`BeatProposal`, or ``None`` for no content.

    Args:
        client: The injected client protocol (``OpenAICompatClient`` or
            ``FakeLLMClient``); never constructed here. An explicit ``None`` is
            rejected before any prompt or transport work.
        messages: The exact captured (system, user) messages from the
            immutable narrative snapshot.
    """
    if client is None:
        raise StoryDirectorClientRequiredError(
            "generate_beat_proposal requires an injected client; got None"
        )
    _require_registered()
    descriptor = build_generation_descriptor(tuple(messages))
    text = yield guarded_call("story_director", client, descriptor)
    if text is None:
        return None
    try:
        parsed = json.loads(text)
        return BeatProposal.from_payload(parsed)
    except (TypeError, ValueError, KeyError):
        # A conversion failure after the guardrail accepted the text is a
        # defensive no-content trigger: never return an invalid proposal.
        return None
