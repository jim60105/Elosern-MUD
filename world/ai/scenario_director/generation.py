"""The guarded generation pipeline and identity-referenced registration.

The atomic ``register_scenario_director`` seam (which installs the
identity-referenced ``_HOOKS`` bundle owned by
:mod:`world.ai.scenario_director.validators`), the by-identity registration
gate, the post-guardrail context-fit gate, and the ``inlineCallbacks``
``generate_quest_blueprint`` entry point with its deterministic template-pool
degrade draw. The template pool is read through a lazy accessor so the import
direction stays one-way (templates -> proposal model) and startup registration
never forces a module-level cycle.

The boundary contract (``tests/test_ai_transport_contract.py``): this module
imports no state writer, no typeclass, no live transport, and no socket, and
consumes the client through the injected protocol exactly like ``narrator.py``
and ``npc_dialogue.py``.
"""

from __future__ import annotations

import json
from typing import Any

from twisted.internet import defer

from world.ai import guardrail
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
from world.lore.guild import GUILD_RANK_REGISTRY
from world.prompts.loader import PromptUnavailableError

from world.ai.scenario_director.blueprints import QuestBlueprint
from world.ai.scenario_director.validators import (
    _HOOKS,
    _SCENARIO_DIRECTOR_DEGRADED,
    _VALIDATORS,
    _degrade_fallback,
    SCENARIO_DIRECTOR_OUTPUT_SCHEMA,
    ScenarioDirectorClientRequiredError,
    ScenarioDirectorNotRegisteredError,
    ScenarioDirectorTemplateError,
)
from world.ai.scenario_director.prompt import build_scenario_prompt


def _is_registered() -> bool:
    """True when the guardrail's actual registries hold every scenario_director hook."""
    if guardrail._degrade_fallbacks.get("scenario_director") is not _degrade_fallback:
        return False
    validators = guardrail._semantic_validators.get("scenario_director", {})
    if not all(
        validators.get(name) is validator for name, validator in _VALIDATORS.items()
    ):
        return False
    return _OUTPUT_SCHEMAS.get("scenario_director") is SCENARIO_DIRECTOR_OUTPUT_SCHEMA


def _require_registered() -> None:
    if not _is_registered():
        raise ScenarioDirectorNotRegisteredError(
            "the scenario_director layer is not registered; "
            "call register_scenario_director() first"
        )


def _uninstall_schema() -> None:
    if _OUTPUT_SCHEMAS.get("scenario_director") is SCENARIO_DIRECTOR_OUTPUT_SCHEMA:
        del _OUTPUT_SCHEMAS["scenario_director"]


def register_scenario_director() -> None:
    """Install the scenario_director layer's guardrail hooks atomically and idempotently.

    Registers the sentinel degrade fallback, every semantic validator, and the
    output jsonschema. On a partial failure every own hook is removed before the
    error propagates. A second call is a no-op that keeps the first registration
    and swallows only this module's own duplicate-registration errors, never an
    incompatible one.
    """
    if _is_registered():
        return
    try:
        _HOOKS.install()
        if _OUTPUT_SCHEMAS.get("scenario_director") is not SCENARIO_DIRECTOR_OUTPUT_SCHEMA:
            register_output_schema("scenario_director", SCENARIO_DIRECTOR_OUTPUT_SCHEMA)
    except (GuardrailRegistrationError, DuplicateSchemaError):
        _HOOKS.uninstall_own()
        _uninstall_schema()
        raise


def _rank_order(rank_key: str) -> int | None:
    guild_rank = GUILD_RANK_REGISTRY.get(rank_key)
    return None if guild_rank is None else guild_rank.order


def _fits_context(blueprint: QuestBlueprint, context: dict[str, Any]) -> bool:
    """Return True when a validated blueprint answers the request context.

    This is the post-guardrail fitness gate (design D3): guardrail semantic
    validators are context-free by contract, so the entry point re-checks rank,
    quest type, issuer branch, and anchor against the request. An unknown
    allowed rank never matches, so a malformed request cannot be silently
    answered.
    """
    allowed_rank = context.get("allowed_rank")
    if allowed_rank is not None:
        allowed_order = _rank_order(allowed_rank)
        blueprint_order = _rank_order(blueprint.rank)
        if allowed_order is None or blueprint_order is None:
            return False
        if blueprint_order > allowed_order:
            return False
    requested_type = context.get("requested_type")
    if requested_type is not None and blueprint.quest_type != requested_type:
        return False
    issuer_branch = context.get("issuer_branch")
    if issuer_branch is not None and blueprint.issuer != issuer_branch:
        return False
    anchor = context.get("anchor")
    if anchor is not None:
        anchors = []
        for stage in blueprint.stages:
            if stage.location is None:
                continue
            if stage.location.anchor_key == anchor or stage.location.anchor_near == anchor:
                anchors.append(anchor)
        if not anchors:
            return False
    return True


def get_template_pool() -> tuple[QuestBlueprint, ...]:
    """Return the hand-written template pool through a lazy accessor.

    Importing the pool inside the call keeps the import direction one-way
    (templates -> proposal model) and avoids a module-level import cycle at
    startup registration time.
    """
    from world.ai.director_templates import QUEST_TEMPLATE_POOL

    return QUEST_TEMPLATE_POOL


def _draw_template(context: dict[str, Any]) -> QuestBlueprint:
    """Deterministically select the first pool entry fitting ``context``.

    Raises ``ScenarioDirectorTemplateError`` when no compatible template
    exists, so a caller never receives a well-formed-but-inapplicable offline
    quest.
    """
    for blueprint in get_template_pool():
        if _fits_context(blueprint, context):
            return blueprint
    raise ScenarioDirectorTemplateError(
        "no template in the pool fits the request context"
    )


@defer.inlineCallbacks
def generate_quest_blueprint(client: Any, *, context: dict[str, Any]):
    """Run the scenario_director layer's guarded pipeline for one quest proposal.

    Args:
        client: The injected client protocol (``OpenAICompatClient`` or
            ``FakeLLMClient``); never imported directly here. An explicit
            ``None`` is rejected with ``ScenarioDirectorClientRequiredError``
            before any prompt construction or transport work.
        context: The caller's plain-data request: ``requested_type``,
            ``allowed_rank``, ``issuer_branch``, ``anchor``, and an optional
            ``note``.

    Returns:
        A Deferred resolving to a frozen ``QuestBlueprint`` that both validates
        and fits the request context. On any degrade trigger the call resolves
        to a deterministic context-fitting draw from the hand-written template
        pool; when no compatible template exists it errbacks with
        ``ScenarioDirectorTemplateError``, and before registration it errbacks
        with ``ScenarioDirectorNotRegisteredError``.
    """
    if client is None:
        raise ScenarioDirectorClientRequiredError(
            "generate_quest_blueprint requires an injected client; got None"
        )
    _require_registered()
    try:
        system, user = build_scenario_prompt(context)
    except PromptUnavailableError:
        return _draw_template(context)
    descriptor = ChatRequestDescriptor(messages=(system, user), schema_id="scenario_director")
    text = yield guarded_call("scenario_director", client, descriptor)
    if text is _SCENARIO_DIRECTOR_DEGRADED:
        return _draw_template(context)
    try:
        parsed = json.loads(text)
        blueprint = QuestBlueprint.from_payload(parsed)
    except (TypeError, ValueError, KeyError):
        # A conversion failure after the guardrail accepted the text is a
        # defensive degrade trigger: never resolve to an invalid proposal.
        return _draw_template(context)
    if not _fits_context(blueprint, context):
        return _draw_template(context)
    return blueprint
