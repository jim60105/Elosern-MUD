"""Deterministic translation boundary from validated quest proposals (quest-runtime D-1).

Change 15 reserved a narrow conversion boundary for change 20: the one
sanctioned translator from a validated JSON-safe proposal payload to the closed
runtime type. ``compile_quest_blueprint`` re-validates every constraint the
``scenario_director`` guardrail checked against the same immutable
``world.lore`` registries and maps the payload onto ``QuestDefinition`` plus a
``QuestReward`` and an issuance descriptor (issuer key and settlement mode).
``register_generated_quest`` publishes the compiled definition, its issuance
(a guild offer or a private commission, dispatched by the issuer namespace),
and the stage spawn requirements as one all-or-nothing, durable-first
operation: the serialized payload is appended to
the ``generated_quest_store`` Script before any process-local registry is
touched, and startup restore reconciles store to registries (design D2/D3).

This package is deterministic: it contains no generative or transport
dependency, accepts only plain validated data (never a proposal object from the
generative package), and reads the same lore registries the guardrail validators
read, so the two sides cannot drift. The layering is acyclic:
:mod:`~world.quests.compile.contracts` (frozen values, the compile exception,
the spawn-requirement registry) <- :mod:`~world.quests.compile.fields` <-
:mod:`~world.quests.compile.canonical` <-
:mod:`~world.quests.compile.compiler` <- :mod:`~world.quests.compile.payload`
<- :mod:`~world.quests.compile.registration` (the only writer of
``SCENE_REQUIREMENT_REGISTRY``).
"""

from world.quests.compile.canonical import (
    _definition_key,
    _npc_req_canonical,
    _stage_requirement_canonical,
)
from world.quests.compile.compiler import (
    _compile_issuance,
    _validate_scene_bound_rules,
    compile_quest_blueprint,
    scene_requirements_for,
)
from world.quests.compile.contracts import (
    CompiledQuest,
    IssuanceDescriptor,
    QuestCompileError,
    StageNpcCharacterization,
    StageSpawnRequirement,
    _CJK_END,
    _CJK_START,
    _DESTINATION_KIND_BY_VALUE,
    _OBJECTIVE_KIND_BY_VALUE,
    _QUEST_TYPE_BY_VALUE,
    _TEMPLATE_PLACEHOLDER_RE,
    _has_cjk,
    _reject,
)
from world.quests.compile.fields import (
    _compile_characterization,
    _compile_location,
    _compile_objective,
    _require_int,
    _require_mapping,
    _validate_reward,
    _validate_scene_fields,
    _validate_strings,
)
from world.quests.compile.payload import (
    _characterization_from_payload,
    _compiled_to_payload,
    _db_safe,
    _locator_from_payload,
    _objective_from_payload,
    _requirement_from_payload,
    _stage_from_payload,
    _validate_restored_payload,
    payload_to_registrations,
)
from world.quests.compile.registration import (
    _publish_registration,
    register_generated_quest,
    register_restored_quest,
)

__all__ = [
    "CompiledQuest",
    "IssuanceDescriptor",
    "QuestCompileError",
    "SCENE_REQUIREMENT_REGISTRY",
    "StageNpcCharacterization",
    "StageSpawnRequirement",
    "compile_quest_blueprint",
    "payload_to_registrations",
    "register_generated_quest",
    "register_restored_quest",
    "scene_requirements_for",
]


def __getattr__(name: str):
    """Delegate the mutable registry read to its owning module.

    ``SCENE_REQUIREMENT_REGISTRY`` lives in
    :mod:`world.quests.compile.contracts` -- the compile boundary remains the
    single writer (``registration._publish_registration``) and ``compiler``
    reads the same object through its own import, exactly as the single-module
    boundary did. The historical ``world.quests.compile.SCENE_REQUIREMENT_REGISTRY``
    read resolves live here so a package-path mutation is visible through
    every other path, with no frozen second binding in this module's
    namespace.
    """
    if name == "SCENE_REQUIREMENT_REGISTRY":
        from world.quests.compile import contracts as _contracts_module

        return _contracts_module.SCENE_REQUIREMENT_REGISTRY
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
