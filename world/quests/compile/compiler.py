"""Deterministic blueprint-to-runtime translation (quest-runtime D-1).

The compile half of the ``world.quests.compile`` package:
``compile_quest_blueprint`` re-validates a validated JSON-safe proposal
payload and maps it onto the closed runtime type, ``_compile_issuance``
resolves its issuer descriptor, and ``scene_requirements_for`` reads the
registry owned by :mod:`world.quests.compile.contracts`. This module is
deterministic: it contains no generative or transport dependency, accepts
only plain validated data (never a proposal object from the generative
package), and reads the same lore registries the guardrail validators read,
so the two sides cannot drift.
"""

from dataclasses import dataclass
from typing import Any

from world.lore.guild import GUILD_BRANCH_REGISTRY, GUILD_RANK_REGISTRY
from world.quests.characterization import (
    duplicate_display_name_errors,
    duplicate_stable_key_errors,
)
from world.quests.compile.canonical import _definition_key
from world.quests.compile.contracts import (
    CompiledQuest,
    IssuanceDescriptor,
    QuestCompileError,
    SCENE_REQUIREMENT_REGISTRY,
    StageSpawnRequirement,
    _QUEST_TYPE_BY_VALUE,
    _reject,
)
from world.quests.compile.fields import (
    _compile_location,
    _compile_objective,
    _require_int,
    _require_mapping,
    _validate_reward,
    _validate_scene_fields,
    _validate_strings,
)
from world.quests.definitions import (
    DestinationKind,
    MAX_DEFINITION_PROSE_LENGTH,
    ObjectiveKind,
    QuestDefinition,
    QuestDefinitionError,
    QuestObjective,
    QuestStage,
    RoomLocator,
    validate_definition,
)
from world.rules.guild_offers import (
    QuestReward,
)
from world.rules.quest_issuance import (
    IssuerKeyError,
    Settlement,
    guild_issuer_key,
    issuer_is_authorized,
    parse_issuer_key,
)


def _validate_scene_bound_rules(
    stage_index: int,
    location: RoomLocator | None,
    objective: QuestObjective,
    npc_reqs: tuple[tuple[str, str, str | None], ...],
    *,
    package_roles: frozenset[str] = frozenset(),
) -> None:
    """Enforce the shared scene-bound rules the guardrail also checks (D5).

    Occupant-bearing scenes (any ``npc_req``) must be instance-layer so spawned
    entities always live in a reclaimable instance room, never a permanent map
    room. An ESCORT stage is refused entirely until a protected-entity binding
    flow exists: permanent-location stages are never bound to protected
    entities today (the SceneBuilder locates permanent rooms only, so a bound
    entity could never be spawned into an ESCORT destination), which would
    leave the quest structurally uncompletable. A bound-target DEFEAT must
    declare a quantity no greater than its ``npc_req`` count so the objective
    is always satisfiable by defeating the bound targets.

    The instance-only rule has exactly one bounded exception (design §5.1):
    ``package_roles`` is a *published package's own* validated role set, never a
    caller flag. It lifts the rule only when every declared occupant role is one
    of those package-owned roles AND the objective needs no stage binding -- a
    bound-target DEFEAT can only bind an instance room, so at a permanent
    destination it would be left uncompletable. A standalone payload (the
    direct compile path) passes no ``package_roles`` and keeps the blanket
    rejection unchanged, and ESCORT stays refused on both paths.
    """
    if objective.kind is ObjectiveKind.ESCORT:
        _reject(
            f"stage {stage_index} declares an ESCORT objective, which cannot be "
            "published until a protected-entity binding flow exists"
        )
    has_occupants = bool(npc_reqs)
    roles = {entry[0] for entry in npc_reqs}
    package_owned = (
        bool(package_roles) and bool(roles) and roles.issubset(package_roles)
    )
    # Derived from the objective's own binding requirement, so a future
    # bound-target objective kind cannot slip through the exception.
    needs_stage_binding = objective.requires_bound_targets
    if has_occupants and not (
        location is not None and location.kind is DestinationKind.BOUND_INSTANCE
    ) and not (package_owned and not needs_stage_binding):
        _reject(
            f"stage {stage_index} declares NPC requirements outside an "
            "instance-layer destination; occupant-bearing scenes must be instances "
            "unless every occupant role is a validated package role on an "
            "objective that needs no stage binding"
        )
    if (
        objective.kind is ObjectiveKind.DEFEAT
        and objective.requires_bound_targets
        and objective.quantity > len(npc_reqs)
    ):
        _reject(
            f"stage {stage_index} bound DEFEAT quantity {objective.quantity} exceeds "
            f"the number of npc_req entries {len(npc_reqs)}"
        )


@dataclass(frozen=True)
class CompiledBlueprintCore:
    """The issuer-independent part of a compiled proposal.

    The definition, the reward, the per-stage spawn requirements, and the rank
    are shared by the strict direct compile path (which resolves one concrete
    issuance) and the scene-package path (whose issuance may stay a validated
    symbolic role declaration until activation). Splitting them here keeps one
    definition/stage compiler rather than growing a second one.
    """

    definition: QuestDefinition
    reward: QuestReward
    stage_requirements: tuple[StageSpawnRequirement, ...]
    rank: str
    issuer: Any


def compile_blueprint_core(
    validated_payload: Any,
    *,
    package_roles: frozenset[str] = frozenset(),
) -> CompiledBlueprintCore:
    """Re-validate a validated proposal payload into its issuer-independent core.

    Accepts the JSON-safe mapping produced by the proposal's ``to_payload()``
    contract (never a proposal object). Every constraint the guardrail semantic
    validators checked -- rank, reward band, item keys, archetype, NPC tiers,
    monster tier, branch, contiguous indices, deadline, and empty conditions --
    is re-checked here against the same ``world.lore`` registries, plus the
    runtime's own definition rules, and ``QuestCompileError`` names the failing
    field before any mutation.

    ``package_roles`` is the published package's own validated role set when the
    caller is the scene-package boundary; it enables the single bounded
    permanent-occupant exception documented on
    :func:`_validate_scene_bound_rules` and is never a free-form caller flag.
    """
    payload = _require_mapping(validated_payload, "payload")

    _validate_strings(None, "payload.name", payload.get("name"), 80, required=True)
    name = payload["name"]

    # The two authored prose fields beside the guild grade (design D-Q5): both
    # ride the same bounded zh-TW validator and are optional, so a blueprint
    # that authors neither still compiles with both absent.
    _validate_strings(
        None,
        "payload.rating_rationale_zh",
        payload.get("rating_rationale_zh"),
        MAX_DEFINITION_PROSE_LENGTH,
        required=False,
    )
    _validate_strings(
        None,
        "payload.background_flavor_zh",
        payload.get("background_flavor_zh"),
        MAX_DEFINITION_PROSE_LENGTH,
        required=False,
    )
    rating_rationale_zh = payload.get("rating_rationale_zh")
    background_flavor_zh = payload.get("background_flavor_zh")

    quest_type_value = payload.get("quest_type")
    if not isinstance(quest_type_value, str) or quest_type_value not in _QUEST_TYPE_BY_VALUE:
        _reject(f"unknown quest_type {quest_type_value!r}")
    quest_type = _QUEST_TYPE_BY_VALUE[quest_type_value]

    rank = payload.get("rank")
    if not isinstance(rank, str) or rank not in GUILD_RANK_REGISTRY:
        _reject(f"unknown quest rank {rank!r}")

    reward = _validate_reward(rank, payload.get("reward"))

    stages_payload = payload.get("stages")
    if not isinstance(stages_payload, list) or not stages_payload:
        _reject("payload.stages must be a non-empty array")
    indices = [
        stage.get("index")
        for stage in stages_payload
        if isinstance(stage, dict)
    ]
    if indices != list(range(len(stages_payload))):
        _reject(f"stage indices must be contiguous starting at zero, got {indices}")

    failure = _require_mapping(payload.get("failure"), "failure")
    deadline = failure.get("deadline_hours")
    if deadline is not None and (
        isinstance(deadline, bool) or not isinstance(deadline, int) or deadline < 1
    ):
        _reject("failure.deadline_hours must be None or a positive integer")
    conditions = failure.get("conditions")
    if conditions != []:
        _reject(
            "failure.conditions must be exactly an empty list; "
            "deterministic failure conditions are a forward-declared seam"
        )

    quest_stages: list[QuestStage] = []
    stage_requirements: list[StageSpawnRequirement] = []
    all_npc_entries: list[dict[str, Any]] = []
    for position, stage_payload in enumerate(stages_payload):
        stage_payload = _require_mapping(stage_payload, f"stages[{position}]")
        index = _require_int(stage_payload.get("index"), f"stages[{position}].index")
        if index != position:
            _reject(
                f"stages[{position}].index must equal its array position, got {index}"
            )

        location_payload = stage_payload.get("location_req")
        location = None
        if location_payload is not None:
            location = _compile_location(location_payload)
        npc_req_payload = stage_payload.get("npc_req")
        if not isinstance(npc_req_payload, list):
            _reject(f"stage {position} npc_req must be an array")
        for entry in npc_req_payload:
            if isinstance(entry, dict):
                all_npc_entries.append(entry)
        (
            archetype,
            anchor_near,
            scene_sentence,
            npc_reqs,
            characterizations,
        ) = _validate_scene_fields(
            position,
            location_payload,
            npc_req_payload,
        )
        objective = _compile_objective(
            position,
            stage_payload.get("objective"),
            location,
            bool(npc_reqs),
        )
        _validate_scene_bound_rules(
            position, location, objective, npc_reqs, package_roles=package_roles
        )
        quest_stages.append(QuestStage(index=index, objective=objective))
        stage_requirements.append(
            StageSpawnRequirement(
                index=index,
                objective_kind=objective.kind,
                location=location,
                archetype=archetype,
                anchor_near=anchor_near,
                scene_sentence=scene_sentence,
                npc_reqs=npc_reqs,
                characterizations=characterizations,
            )
        )

    for message in duplicate_stable_key_errors(all_npc_entries):
        _reject(message)
    for message in duplicate_display_name_errors(all_npc_entries):
        _reject(message)

    definition_fields = {
        "display_name": name,
        "quest_type": quest_type.value,
        "rank": rank,
        "stages": [
            {
                "index": stage.index,
                "objective": {
                    "kind": stage.objective.kind.value,
                    "quantity": stage.objective.quantity,
                    "monster_tier": stage.objective.monster_tier,
                    "destination": (
                        None
                        if stage.objective.destination is None
                        else {
                            "kind": stage.objective.destination.kind.value,
                            "anchor_key": stage.objective.destination.anchor_key,
                            "xyz": stage.objective.destination.xyz,
                        }
                    ),
                    "requires_bound_targets": stage.objective.requires_bound_targets,
                    "item_key": stage.objective.item_key,
                },
            }
            for stage in quest_stages
        ],
        "deadline_hours": deadline,
        "rating_rationale_zh": rating_rationale_zh,
        "background_flavor_zh": background_flavor_zh,
    }
    key = _definition_key(definition_fields, tuple(stage_requirements))
    definition = QuestDefinition(
        key=key,
        display_name=name,
        quest_type=quest_type,
        rank=rank,
        stages=tuple(quest_stages),
        deadline_hours=deadline,
        rating_rationale_zh=rating_rationale_zh,
        background_flavor_zh=background_flavor_zh,
    )
    try:
        validate_definition(definition)
    except QuestDefinitionError as error:
        raise QuestCompileError(str(error)) from error

    return CompiledBlueprintCore(
        definition=definition,
        reward=reward,
        stage_requirements=tuple(stage_requirements),
        rank=rank,
        issuer=payload.get("issuer"),
    )


def compile_quest_blueprint(validated_payload: Any) -> CompiledQuest:
    """Re-validate a validated proposal payload and map it onto the runtime type.

    The strict direct path: the issuer-independent core is compiled and the
    declared issuer is resolved to exactly one concrete issuance. A
    character-namespaced key must name a carrier authorized to issue today, so
    this path never publishes a merely planned symbolic commission.
    """
    core = compile_blueprint_core(validated_payload)
    descriptor = _compile_issuance(core.issuer, core.reward)
    return CompiledQuest(
        definition=core.definition,
        reward=core.reward,
        issuance=descriptor,
        stage_requirements=core.stage_requirements,
    )


def _compile_issuance(issuer: Any, reward: QuestReward) -> IssuanceDescriptor:
    """Map a payload's declared issuer onto its issuance descriptor.

    The declared value is either a registered branch key (the pipeline's
    guardrail declares the bare branch; a ``guild:<branch key>`` full form is
    accepted equally) or a character-namespaced issuer key. A guild issuance
    settles by counter; a private commission settles automatically and may
    grant zero merit, and its key must name a carrier authorized to issue.
    Every violation raises ``QuestCompileError`` before any mutation.
    """
    if not isinstance(issuer, str) or not issuer:
        _reject(f"unknown issuer branch {issuer!r}")
    if issuer in GUILD_BRANCH_REGISTRY:
        return IssuanceDescriptor(
            issuer_key=guild_issuer_key(issuer),
            settlement=Settlement.COUNTER,
        )
    try:
        parsed = parse_issuer_key(issuer)
    except IssuerKeyError as error:
        _reject(f"unknown issuer branch {issuer!r}: {error}")
    if parsed.namespace == "guild":
        if parsed.remainder not in GUILD_BRANCH_REGISTRY:
            _reject(f"unknown issuer branch {parsed.remainder!r}")
        return IssuanceDescriptor(
            issuer_key=guild_issuer_key(parsed.remainder),
            settlement=Settlement.COUNTER,
        )
    if not issuer_is_authorized(issuer):
        _reject(f"issuer {issuer!r} names no carrier authorized to issue")
    if reward.merit != 0:
        _reject(
            f"private commission {issuer!r} cannot grant guild merit, "
            f"got {reward.merit}"
        )
    return IssuanceDescriptor(issuer_key=issuer, settlement=Settlement.AUTO)


def scene_requirements_for(definition_key: str) -> tuple[StageSpawnRequirement, ...]:
    """Return one definition's registered spawn requirements, or an empty tuple.

    A hand-written catalog definition (never compiled through this boundary) has
    no entry and reads back ``()``, so the SceneBuilder can distinguish a
    generated scene from a hand-written stage with no scene.
    """
    return SCENE_REQUIREMENT_REGISTRY.get(definition_key, ())
