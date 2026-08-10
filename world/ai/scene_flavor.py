"""Scene-flavor layer: guarded Traditional Chinese atmosphere paragraph generation.

The ``scene_builder``-profile layer turns a bounded scene context into a
Traditional Chinese atmosphere paragraph through the shared
validation-retry-degrade guardrail (design §7.5). It is a pure function: it
reads only the deterministic context fragments it is handed, has no access to a
write API, and returns plain prose that is never parsed back. When the profile
is disabled, the transport fails, the validation retries are exhausted, the
prompt key is unavailable, or the input exceeds the prompt bounds, the call
resolves to ``None`` -- the single public degraded marker -- so the
scene-flavor-apply caller can leave the room without flavor and the game stays
fully playable offline.

The mechanical "no fabricated numbers" gate (scene-flavor design B4) lands as a
deterministic rule: any returned flavor containing a digit character is a
validation failure and retried under the profile's retry budget.

Boundary contract (``tests/test_ai_transport_contract.py``): this module imports
no state writer, no live transport, and no socket. The client is injected;
``world.ai.guardrail`` registers the hooks under the ``scene_builder`` layer key
because the guardrail and profile registries key strictly by ``LAYER_NAMES``.
"""

from __future__ import annotations

import json
from collections.abc import Callable
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
from world.prompts.loader import PromptUnavailableError, render_prompt

# Flavor length bounds enforced by the length semantic validator (design D4):
# the flavor must be a real 50-200 character paragraph, never a one-word echo.
MIN_FLAVOR_LENGTH = 50
MAX_FLAVOR_LENGTH = 200

# Per-field string-length cap for context fragments (design D3).
MAX_FIELD_LENGTH = 200

_TRUNCATION_MARKER = "…"
_CJK_START = "\u4e00"
_CJK_END = "\u9fff"


class SceneFlavorClientRequiredError(TypeError):
    """Raised when ``generate_scene_flavor`` is called with an explicit ``None`` client."""


class SceneFlavorNotRegisteredError(RuntimeError):
    """Raised when ``generate_scene_flavor`` runs before the hooks are installed."""


@dataclass(frozen=True)
class SceneFlavorContext:
    """Bounded deterministic context for one scene-flavor generation.

    Every field is capped with ``_cap_string`` before rendering, so identical
    contexts produce byte-identical (system, user) pairs with no live entity
    references. The caller (scene-flavor-apply) supplies these fragments from
    deterministic sources.
    """

    scene_sentence: str
    quest_context: str
    room_name: str
    region: str


_SCENE_FLAVOR_DEGRADED = object()


def _degrade_fallback() -> object:
    """Return the sentinel so the entry point can map it to the public ``None``."""
    return _SCENE_FLAVOR_DEGRADED


def _validate_non_empty(parsed: Any) -> list[str]:
    if not isinstance(parsed, str) or not parsed.strip():
        return ["scene flavor is empty or whitespace-only"]
    return []


def _validate_bounded_length(parsed: Any) -> list[str]:
    if isinstance(parsed, str) and not (MIN_FLAVOR_LENGTH <= len(parsed) <= MAX_FLAVOR_LENGTH):
        return [
            f"scene flavor length {len(parsed)} is outside the "
            f"{MIN_FLAVOR_LENGTH}-{MAX_FLAVOR_LENGTH} character bound"
        ]
    return []


def _validate_has_cjk(parsed: Any) -> list[str]:
    if not isinstance(parsed, str) or not any(_CJK_START <= ch <= _CJK_END for ch in parsed):
        return [
            "scene flavor contains no CJK Unified Ideograph and is not Traditional Chinese"
        ]
    return []


def _validate_no_digits(parsed: Any) -> list[str]:
    if isinstance(parsed, str) and any(ch.isdecimal() for ch in parsed):
        return ["scene flavor contains a digit character (no fabricated numbers are allowed)"]
    return []


_VALIDATORS: dict[str, Callable[[Any], list[str]]] = {
    "flavor_non_empty": _validate_non_empty,
    "flavor_bounded_length": _validate_bounded_length,
    "flavor_has_cjk": _validate_has_cjk,
    "flavor_no_digits": _validate_no_digits,
}


def _cap_string(value: str) -> str:
    if len(value) <= MAX_FIELD_LENGTH:
        return value
    return value[: MAX_FIELD_LENGTH - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER


def build_scene_flavor_prompt(
    context: SceneFlavorContext,
) -> tuple[dict[str, str], dict[str, str]]:
    """Build a deterministic (system, user) message pair for scene flavor.

    The system message renders ``scene_builder.system`` with the four capped
    context fragments; the user message serializes the bounded structured
    context with stable sorted JSON serialization and ``ensure_ascii=False``
    (mirroring npc_dialogue's role-in-system / data-in-user split).
    """
    system = {
        "role": "system",
        "content": render_prompt(
            "scene_builder.system",
            scene_sentence=_cap_string(context.scene_sentence),
            quest_context=_cap_string(context.quest_context),
            room_name=_cap_string(context.room_name),
            region=_cap_string(context.region),
        ),
    }
    payload = {
        "scene_sentence": _cap_string(context.scene_sentence),
        "quest_context": _cap_string(context.quest_context),
        "room_name": _cap_string(context.room_name),
        "region": _cap_string(context.region),
    }
    user = {
        "role": "user",
        "content": json.dumps(payload, sort_keys=True, ensure_ascii=False),
    }
    return system, user


def _is_registered() -> bool:
    """True when the guardrail's actual registries hold every scene-flavor hook."""
    if guardrail._degrade_fallbacks.get("scene_builder") is not _degrade_fallback:
        return False
    validators = guardrail._semantic_validators.get("scene_builder", {})
    return all(validators.get(name) is validator for name, validator in _VALIDATORS.items())


def _require_registered() -> None:
    if not _is_registered():
        raise SceneFlavorNotRegisteredError(
            "the scene-flavor layer is not registered; call register_scene_flavor() first"
        )


def _uninstall_fallback() -> None:
    if guardrail._degrade_fallbacks.get("scene_builder") is _degrade_fallback:
        del guardrail._degrade_fallbacks["scene_builder"]


def _uninstall_validator(name: str) -> None:
    validators = guardrail._semantic_validators.get("scene_builder", {})
    if validators.get(name) is _VALIDATORS[name]:
        del validators[name]


def _uninstall_all_own_hooks() -> None:
    """Remove every scene-flavor hook that is this module's own (by identity).

    Used for rollback so a partial-failure registration can never leave a
    half-installed scene-flavor state behind. Foreign hooks with the same names
    are left untouched.
    """
    _uninstall_fallback()
    for name in _VALIDATORS:
        _uninstall_validator(name)


def register_scene_flavor() -> None:
    """Install the scene-flavor layer's guardrail hooks atomically and idempotently.

    Registers the sentinel degrade fallback and every semantic validator under
    the ``scene_builder`` layer key. On a partial failure every hook belonging to
    this module (by identity) is removed before the error propagates, so the
    layer is never left half-registered. A second call is a no-op that swallows
    only this module's own duplicate registration, never an incompatible one.
    """
    if _is_registered():
        return
    try:
        if guardrail._degrade_fallbacks.get("scene_builder") is not _degrade_fallback:
            register_degrade_fallback("scene_builder", _degrade_fallback)
        for name, validator in _VALIDATORS.items():
            validators = guardrail._semantic_validators.get("scene_builder", {})
            if validators.get(name) is validator:
                continue
            register_semantic_validator("scene_builder", name, validator)
    except GuardrailRegistrationError:
        _uninstall_all_own_hooks()
        raise


@defer.inlineCallbacks
def generate_scene_flavor(context: SceneFlavorContext, client: Any):
    """Run the scene-flavor layer's guarded pipeline for one scene.

    Args:
        context: The bounded deterministic scene context to flavor.
        client: The injected client protocol (``OpenAICompatClient`` or
            ``FakeLLMClient``); an explicit ``None`` is rejected with
            ``SceneFlavorClientRequiredError`` before any prompt construction
            or transport interaction.

    Returns:
        A Deferred resolving to the flavor paragraph, or to ``None`` -- the
        single public degraded marker -- when the profile is disabled, the
        transport fails, the retry budget is exhausted, or the prompt key is
        unavailable. No state change is ever made.
    """
    if client is None:
        raise SceneFlavorClientRequiredError(
            "generate_scene_flavor requires an injected client; got None"
        )
    _require_registered()
    try:
        system, user = build_scene_flavor_prompt(context)
    except PromptUnavailableError:
        return None
    descriptor = ChatRequestDescriptor(messages=(system, user))
    result = yield guarded_call("scene_builder", client, descriptor)
    if result is _SCENE_FLAVOR_DEGRADED:
        return None
    return result
