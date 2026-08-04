"""Deterministic translation boundary from validated quest proposals (quest-runtime D-1).

Change 15 reserved a narrow conversion boundary for change 20: the one
sanctioned translator from a validated JSON-safe proposal payload to the closed
runtime type. ``compile_quest_blueprint`` re-validates every constraint the
``scenario_director`` guardrail checked against the same immutable
``world.lore`` registries and maps the payload onto ``QuestDefinition`` plus a
``QuestReward`` and issuer branch. ``register_generated_quest`` publishes the
compiled definition and its offer as one all-or-nothing operation.

This module is deterministic: it contains no generative or transport
dependency, accepts only plain validated data (never a proposal object from the
generative package), and reads the same lore registries the guardrail validators
read, so the two sides cannot drift.
"""

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.guild import GUILD_BRANCH_REGISTRY, GUILD_RANK_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.quests.definitions import (
    KNOWN_GRID_MAP_KEYS,
    QUEST_DEFINITION_REGISTRY,
    DestinationKind,
    ObjectiveKind,
    QuestDefinition,
    QuestDefinitionError,
    QuestObjective,
    QuestStage,
    QuestType,
    RoomLocator,
    register_quest_definition,
    validate_definition,
)
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildQuestOffer,
    ItemQuantity,
    QuestReward,
    register_guild_offer,
)


class QuestCompileError(ValueError):
    """A validated proposal payload violates the compile contract."""


_QUEST_TYPE_BY_VALUE = {quest_type.value: quest_type for quest_type in QuestType}
_OBJECTIVE_KIND_BY_VALUE = {
    "reach_location": ObjectiveKind.REACH,
    "defeat": ObjectiveKind.DEFEAT,
    "escort": ObjectiveKind.ESCORT,
    "acquire": ObjectiveKind.ACQUIRE,
}
_DESTINATION_KIND_BY_VALUE = {
    "anchor": DestinationKind.ANCHOR,
    "grid": DestinationKind.GRID,
    "instance": DestinationKind.BOUND_INSTANCE,
}


@dataclass(frozen=True)
class StageSpawnRequirement:
    """One stage's preserved spawn requirements for change 21's SceneBuilder.

    Plain validated data carrying the objective kind, the destination locator,
    the scene requirement (archetype, anchor hint, sentence), and the NPC role
    requirements, so the SceneBuilder can consume them without importing the
    generative package.
    """

    index: int
    objective_kind: ObjectiveKind
    location: RoomLocator | None
    archetype: str | None
    anchor_near: str | None
    scene_sentence: str | None
    npc_reqs: tuple[tuple[str, str, str | None], ...]


# Process-local spawn-requirement registry, keyed by definition key (D4). It
# lives here -- the compile boundary -- because it is the only place the
# transient ``CompiledQuest.stage_requirements`` is registered atomically with
# the definition and offer. Like ``QUEST_DEFINITION_REGISTRY`` and
# ``GUILD_OFFER_REGISTRY``, it does not survive a server restart.
SCENE_REQUIREMENT_REGISTRY: dict[str, tuple[StageSpawnRequirement, ...]] = {}


@dataclass(frozen=True)
class CompiledQuest:
    """The closed immutable runtime translation of one validated proposal."""

    definition: QuestDefinition
    reward: QuestReward
    issuer_branch_key: str
    stage_requirements: tuple[StageSpawnRequirement, ...]


def _reject(message: str) -> None:
    raise QuestCompileError(message)


_CJK_START = "\u4e00"
_CJK_END = "\u9fff"
_TEMPLATE_PLACEHOLDER_RE = re.compile(r"\{actor\}|\{target\}|\{data\[[^\]]*\]\}")


def _has_cjk(text: str) -> bool:
    return any(_CJK_START <= ch <= _CJK_END for ch in text)


def _validate_strings(
    stage_index: int | None,
    field: str,
    value: Any,
    max_length: int,
    *,
    required: bool,
) -> None:
    if not isinstance(value, str) or not value.strip():
        if required:
            _reject(f"{field} must be a non-empty string")
        return
    if len(value) > max_length:
        _reject(f"{field} exceeds the {max_length}-character cap")
    if not _has_cjk(value):
        _reject(f"{field} contains no CJK Unified Ideograph and is not Traditional Chinese")
    if _TEMPLATE_PLACEHOLDER_RE.search(value):
        _reject(f"{field} echoes deterministic template-placeholder formatting syntax")


def _require_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _reject(f"{field} must be an object")
    return value


def _require_int(value: Any, field: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        _reject(f"{field} must be an integer")
    if minimum is not None and value < minimum:
        _reject(f"{field} must be at least {minimum}")
    return value


def _validate_reward(
    rank: str,
    reward_payload: Any,
) -> QuestReward:
    reward = _require_mapping(reward_payload, "reward")
    copper = _require_int(reward.get("copper"), "reward.copper", minimum=0)
    merit = _require_int(reward.get("merit"), "reward.merit", minimum=0)

    guild_rank = GUILD_RANK_REGISTRY.get(rank)
    if guild_rank is None:
        _reject(f"unknown quest rank {rank!r}")
    band_floor = guild_rank.reward_min_copper
    band_ceiling = guild_rank.reward_max_copper
    if copper < band_floor:
        _reject(f"reward copper {copper} is below {rank} rank minimum {band_floor}")
    if band_ceiling is not None and copper > band_ceiling:
        _reject(f"reward copper {copper} is above {rank} rank maximum {band_ceiling}")

    items = reward.get("items")
    if not isinstance(items, list):
        _reject("reward.items must be an array")
    quantities: list[ItemQuantity] = []
    seen: set[str] = set()
    for position, item in enumerate(items):
        item = _require_mapping(item, f"reward.items[{position}]")
        item_key = item.get("item_key")
        if not isinstance(item_key, str) or not item_key:
            _reject(f"reward.items[{position}].item_key must be a non-empty string")
        if item_key not in ITEM_REGISTRY:
            _reject(f"unknown reward item {item_key!r}")
        quantity = _require_int(
            item.get("quantity"), f"reward.items[{position}].quantity", minimum=1
        )
        if item_key in seen:
            _reject(f"duplicate reward item key {item_key!r}")
        seen.add(item_key)
        quantities.append(ItemQuantity(item_key, quantity))
    return QuestReward(copper=copper, items=tuple(quantities), merit=merit)


def _compile_location(location_payload: Any) -> RoomLocator:
    location = _require_mapping(location_payload, "location_req")
    layer = location.get("layer")
    if not isinstance(layer, str) or layer not in _DESTINATION_KIND_BY_VALUE:
        _reject(f"unknown destination layer {layer!r}; wilderness is not representable")
    if layer == "wilderness":
        _reject("wilderness destinations cannot be declared")

    if layer == "anchor":
        anchor_key = location.get("anchor_key")
        if not isinstance(anchor_key, str) or not anchor_key:
            _reject("ANCHOR locator requires a non-empty anchor_key")
        if anchor_key not in ANCHOR_PLACEMENT_REGISTRY:
            _reject(f"anchor {anchor_key!r} has no reachable AnchorRoom in placement registry")
        return RoomLocator(DestinationKind.ANCHOR, anchor_key=anchor_key)

    if layer == "grid":
        xyz = location.get("xyz")
        if not isinstance(xyz, list) or len(xyz) != 3:
            _reject("GRID locator requires an [x, y, z] coordinate list")
        x, y, z = xyz
        if (
            isinstance(x, bool)
            or isinstance(y, bool)
            or not isinstance(x, int)
            or not isinstance(y, int)
            or not isinstance(z, str)
            or not z
        ):
            _reject("GRID locator requires integer x/y and a non-empty map key z")
        if z not in KNOWN_GRID_MAP_KEYS:
            _reject(f"grid map key {z!r} is not known to the xyzgrid")
        return RoomLocator(DestinationKind.GRID, xyz=(x, y, z))

    if layer == "instance":
        if location.get("anchor_key") is not None or location.get("xyz") is not None:
            _reject("BOUND_INSTANCE locator cannot carry static location fields")
        return RoomLocator(DestinationKind.BOUND_INSTANCE)

    _reject(f"unknown destination layer {layer!r}")  # pragma: no cover


def _validate_scene_fields(
    stage_index: int,
    location_payload: Any,
    npc_req_payload: Any,
) -> tuple[str | None, str | None, str | None, tuple[tuple[str, str, str | None], ...]]:
    """Validate archetype, anchor hint, scene sentence, and NPC requirements."""
    archetype = None
    anchor_near = None
    scene_sentence = None
    if isinstance(location_payload, dict):
        archetype = location_payload.get("archetype")
        if archetype is not None and (
            not isinstance(archetype, str)
            or archetype not in SCENE_ARCHETYPE_REGISTRY
        ):
            _reject(f"stage {stage_index} unknown archetype {archetype!r}")
        anchor_near = location_payload.get("anchor_near")
        if anchor_near is not None and not isinstance(anchor_near, str):
            _reject(f"stage {stage_index} anchor_near must be a string or None")
        if anchor_near is not None and anchor_near not in ANCHOR_PLACEMENT_REGISTRY:
            _reject(
                f"stage {stage_index} anchor_near {anchor_near!r} "
                "is not a placed anchor in ANCHOR_PLACEMENT_REGISTRY"
            )
        scene_sentence = location_payload.get("scene_sentence")
        _validate_strings(
            stage_index,
            f"stage {stage_index} scene_sentence",
            scene_sentence,
            500,
            required=False,
        )

    if not isinstance(npc_req_payload, list):
        _reject(f"stage {stage_index} npc_req must be an array")
    npc_reqs: list[tuple[str, str, str | None]] = []
    for position, requirement in enumerate(npc_req_payload):
        requirement = _require_mapping(
            requirement, f"stage {stage_index} npc_req[{position}]"
        )
        role = requirement.get("role")
        if not isinstance(role, str) or not role:
            _reject(f"stage {stage_index} npc_req[{position}].role must be a string")
        tier = requirement.get("tier")
        if not isinstance(tier, str) or tier not in NPC_TIER_REGISTRY:
            _reject(f"stage {stage_index} npc_req[{position}] unknown tier {tier!r}")
        disposition = requirement.get("disposition")
        if disposition is not None and not isinstance(disposition, str):
            _reject(
                f"stage {stage_index} npc_req[{position}].disposition "
                "must be a string or None"
            )
        npc_reqs.append((role, tier, disposition))
    return archetype, anchor_near, scene_sentence, tuple(npc_reqs)


def _compile_objective(
    stage_index: int,
    objective_payload: Any,
    location: RoomLocator | None,
    has_npc_reqs: bool,
) -> QuestObjective:
    objective = _require_mapping(objective_payload, f"stage {stage_index}.objective")
    kind_value = objective.get("kind")
    if not isinstance(kind_value, str) or kind_value not in _OBJECTIVE_KIND_BY_VALUE:
        _reject(f"stage {stage_index} unknown objective kind {kind_value!r}")
    kind = _OBJECTIVE_KIND_BY_VALUE[kind_value]
    quantity = _require_int(
        objective.get("quantity", 1), f"stage {stage_index}.objective.quantity", minimum=1
    )

    if kind is ObjectiveKind.DEFEAT:
        monster_tier = objective.get("monster_tier")
        has_tier = monster_tier is not None
        if has_tier == has_npc_reqs:
            _reject(
                f"stage {stage_index} DEFEAT objective must declare exactly one of "
                "a known monster_tier or a non-empty npc_req"
            )
        if has_tier:
            if not isinstance(monster_tier, str) or monster_tier not in MONSTER_TIER_REGISTRY:
                _reject(f"stage {stage_index} unknown monster tier {monster_tier!r}")
            return QuestObjective(
                kind=kind,
                quantity=quantity,
                monster_tier=monster_tier,
            )
        return QuestObjective(
            kind=kind,
            quantity=quantity,
            requires_bound_targets=True,
        )

    if kind is ObjectiveKind.ACQUIRE:
        item_key = objective.get("item_key")
        if not isinstance(item_key, str) or not item_key:
            _reject(f"stage {stage_index} ACQUIRE objective requires a known item_key")
        if item_key not in ITEM_REGISTRY:
            _reject(f"stage {stage_index} ACQUIRE references unknown item {item_key!r}")
        return QuestObjective(
            kind=kind,
            quantity=quantity,
            item_key=item_key,
        )

    if kind in (ObjectiveKind.REACH, ObjectiveKind.ESCORT):
        if location is None:
            _reject(f"stage {stage_index} {kind.value} objective requires a destination")
        return QuestObjective(
            kind=kind,
            quantity=quantity,
            destination=location,
        )

    _reject(f"stage {stage_index} unknown objective kind {kind_value!r}")  # pragma: no cover


def _definition_key(
    definition_fields: dict[str, Any],
    stage_requirements: tuple[StageSpawnRequirement, ...],
) -> str:
    """Return the stable content-digest key for a compiled definition.

    ``sha256`` over the canonical serialization of the definition's own fields
    **plus the canonical serialization of the compiled per-stage spawn
    requirements**, hex-prefixed. Equal content always yields an equal key;
    different content never collides. Folding the scene requirements into the
    digest means two blueprints with identical runtime stages but different
    scenes (archetype, ``anchor_near``, ``scene_sentence``, or ``npc_reqs``)
    get different keys, so one can never silently overwrite the other's
    spawn-requirement entry. Reward and issuer are offer-level and excluded, so
    two blueprints with identical stages but different rewards share a
    definition key and surface as offer conflicts through
    ``register_generated_quest``.
    """
    canonical = json.dumps(
        {
            "definition": definition_fields,
            "stage_requirements": [
                _stage_requirement_canonical(requirement)
                for requirement in stage_requirements
            ],
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"ai_{digest[:16]}"


def _stage_requirement_canonical(requirement: StageSpawnRequirement) -> dict[str, Any]:
    """Serialize one ``StageSpawnRequirement`` into a canonical JSON-safe dict.

    This is the single canonical shape used both for the definition content
    digest and for equality against a previously registered requirement entry,
    so two compilations of identical scenes compare equal by construction.
    """
    location = requirement.location
    return {
        "index": requirement.index,
        "objective_kind": requirement.objective_kind.value,
        "location": (
            None
            if location is None
            else {
                "kind": location.kind.value,
                "anchor_key": location.anchor_key,
                "xyz": None if location.xyz is None else list(location.xyz),
            }
        ),
        "archetype": requirement.archetype,
        "anchor_near": requirement.anchor_near,
        "scene_sentence": requirement.scene_sentence,
        "npc_reqs": [
            {"role": role, "tier": tier, "disposition": disposition}
            for role, tier, disposition in requirement.npc_reqs
        ],
    }


def _validate_scene_bound_rules(
    stage_index: int,
    location: RoomLocator | None,
    objective: QuestObjective,
    npc_reqs: tuple[tuple[str, str, str | None], ...],
) -> None:
    """Enforce the shared scene-bound rules the guardrail also checks (D5).

    Occupant-bearing scenes (any ``npc_req``) must be instance-layer so spawned
    entities always live in a reclaimable instance room, never a permanent map
    room. An ESCORT stage must be a permanent destination (never instance): the
    SceneBuilder locates permanent rooms only, so an ESCORT scene never spawns
    its protected entities into the destination room (which would auto-complete
    the escort on entry) and never pollutes a permanent map. A bound-target
    DEFEAT must declare a quantity no greater than its ``npc_req`` count so the
    objective is always satisfiable by defeating the bound targets.
    """
    has_occupants = bool(npc_reqs)
    if has_occupants and not (
        location is not None and location.kind is DestinationKind.BOUND_INSTANCE
    ):
        _reject(
            f"stage {stage_index} declares NPC requirements outside an "
            "instance-layer destination; occupant-bearing scenes must be instances"
        )
    if (
        objective.kind is ObjectiveKind.ESCORT
        and location is not None
        and location.kind is DestinationKind.BOUND_INSTANCE
    ):
        _reject(
            f"stage {stage_index} declares an ESCORT objective at an instance "
            "destination; ESCORT scenes must be permanent rooms (located only, "
            "never instance-materialized)"
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


def compile_quest_blueprint(validated_payload: Any) -> CompiledQuest:
    """Re-validate a validated proposal payload and map it onto the runtime type.

    Accepts the JSON-safe mapping produced by the proposal's ``to_payload()``
    contract (never a proposal object). Every constraint the guardrail semantic
    validators checked -- rank, reward band, item keys, archetype, NPC tiers,
    monster tier, branch, contiguous indices, deadline, and empty conditions --
    is re-checked here against the same ``world.lore`` registries, plus the
    runtime's own definition rules, and ``QuestCompileError`` names the failing
    field before any mutation.
    """
    payload = _require_mapping(validated_payload, "payload")

    _validate_strings(None, "payload.name", payload.get("name"), 80, required=True)
    name = payload["name"]

    quest_type_value = payload.get("quest_type")
    if not isinstance(quest_type_value, str) or quest_type_value not in _QUEST_TYPE_BY_VALUE:
        _reject(f"unknown quest_type {quest_type_value!r}")
    quest_type = _QUEST_TYPE_BY_VALUE[quest_type_value]

    rank = payload.get("rank")
    if not isinstance(rank, str) or rank not in GUILD_RANK_REGISTRY:
        _reject(f"unknown quest rank {rank!r}")

    issuer = payload.get("issuer")
    if not isinstance(issuer, str) or issuer not in GUILD_BRANCH_REGISTRY:
        _reject(f"unknown issuer branch {issuer!r}")

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
        (
            archetype,
            anchor_near,
            scene_sentence,
            npc_reqs,
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
        _validate_scene_bound_rules(position, location, objective, npc_reqs)
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
            )
        )

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
    }
    key = _definition_key(definition_fields, tuple(stage_requirements))
    definition = QuestDefinition(
        key=key,
        display_name=name,
        quest_type=quest_type,
        rank=rank,
        stages=tuple(quest_stages),
        deadline_hours=deadline,
    )
    try:
        validate_definition(definition)
    except QuestDefinitionError as error:
        raise QuestCompileError(str(error)) from error

    return CompiledQuest(
        definition=definition,
        reward=reward,
        issuer_branch_key=issuer,
        stage_requirements=tuple(stage_requirements),
    )


def scene_requirements_for(definition_key: str) -> tuple[StageSpawnRequirement, ...]:
    """Return one definition's registered spawn requirements, or an empty tuple.

    A hand-written catalog definition (never compiled through this boundary) has
    no entry and reads back ``()``, so the SceneBuilder can distinguish a
    generated scene from a hand-written stage with no scene.
    """
    return SCENE_REQUIREMENT_REGISTRY.get(definition_key, ())


def register_generated_quest(compiled: CompiledQuest) -> None:
    """Register one compiled definition, its offer, and its spawn requirements
    all-or-nothing.

    Preflights all three registries' equal/conflict states before writing any,
    so a conflicting definition, offer, or spawn-requirement entry raises
    ``QuestCompileError`` before any mutation. Otherwise the definition is
    written first, then the offer and the requirement entry; if a later write
    fails despite preflight (defensive), every entry this call added -- the
    definition, the offer, and the requirements -- is rolled back together, so
    a generated definition is never left registered without its offer or its
    scene requirements.
    """
    definition = compiled.definition
    requirements = compiled.stage_requirements
    offer = GuildQuestOffer(
        definition_key=definition.key,
        issuer_branch_key=compiled.issuer_branch_key,
        reward=compiled.reward,
    )

    definition_current = QUEST_DEFINITION_REGISTRY.get(definition.key)
    offer_current = GUILD_OFFER_REGISTRY.get(
        (definition.key, compiled.issuer_branch_key)
    )
    requirement_current = SCENE_REQUIREMENT_REGISTRY.get(definition.key)
    if definition_current is not None and definition_current != definition:
        _reject(f"conflicting definition already registered under {definition.key!r}")
    if offer_current is not None and offer_current != offer:
        _reject(
            f"conflicting offer already registered for {definition.key!r} "
            f"at branch {compiled.issuer_branch_key!r}"
        )
    if requirement_current is not None and requirement_current != requirements:
        _reject(
            f"conflicting spawn requirements already registered under "
            f"{definition.key!r}"
        )

    definition_added = definition_current is None
    offer_added = offer_current is None
    requirement_added = requirement_current is None
    register_quest_definition(definition)
    try:
        register_guild_offer(offer)
        SCENE_REQUIREMENT_REGISTRY[definition.key] = requirements
    except Exception:
        if definition_added:
            QUEST_DEFINITION_REGISTRY.pop(definition.key, None)
        if offer_added:
            GUILD_OFFER_REGISTRY.pop((definition.key, compiled.issuer_branch_key), None)
        if requirement_added:
            SCENE_REQUIREMENT_REGISTRY.pop(definition.key, None)
        raise
