"""ScenarioDirector layer: validated quest-proposal generation (design §7.1/§7.5).

The ``scenario_director`` generative layer maps a request context to a closed,
deeply immutable ``QuestBlueprint`` proposal through the shared
validation-retry-degrade guardrail. The blueprint emits requirements, not
entities: stages carry objective kinds, ``location_req`` scene requirements,
and ``npc_req`` role tiers, so the output is fully validatable before it
touches the runtime registry. On any degrade trigger (disabled profile,
transport failure, exhausted retries, or a schema-valid-but-context-misfitting
proposal) the call resolves to a deterministic draw from the hand-written
template pool that also fits the request context, never to invalid output or
``None``.

Boundary contract (``tests/test_ai_transport_contract.py``): this module imports
no state writer, no typeclass, no live transport, and no socket. It reads only
the immutable ``world.lore`` registries and consumes the client through the
injected protocol exactly like ``narrator.py`` and ``npc_dialogue.py``. The
request context is plain data supplied by the future composition root; this
module never reads player state.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum
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
from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.guild import GUILD_BRANCH_REGISTRY, GUILD_RANK_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.prompts.loader import PromptUnavailableError, render_prompt
from world.quests.characterization import (
    characterize_errors,
    duplicate_stable_key_errors,
    race_lifespan_upper_bound,
)

# Hard prompt bounds (design D2): per-field string-length caps and a bounded
# total serialized size, so a pathological request cannot produce an unbounded
# prompt. The accepted-proposal caps are enforced by the length semantic
# validator.
MAX_CONTEXT_FIELD_LENGTH = 200
MAX_TOTAL_SIZE = 12000
MAX_NAME_LENGTH = 80
MAX_SCENE_SENTENCE_LENGTH = 500

_CJK_START = "\u4e00"
_CJK_END = "\u9fff"
_TEMPLATE_PLACEHOLDER_RE = re.compile(r"\{actor\}|\{target\}|\{data\[[^\]]*\]\}")

class BlueprintQuestType(StrEnum):
    """The closed five-value quest classification mirrored from the runtime type."""

    GATHER = "採集"
    DEFEAT = "討伐"
    ESCORT = "護衛"
    EXPLORE = "探索"
    EMERGENCY = "緊急"


class BlueprintObjectiveKind(StrEnum):
    """The closed objective-kind vocabulary of one proposal stage."""

    DEFEAT = "defeat"
    REACH_LOCATION = "reach_location"
    ESCORT = "escort"
    ACQUIRE = "acquire"


class BlueprintLocationLayer(StrEnum):
    """The destination-layer vocabulary; wilderness is not representable."""

    ANCHOR = "anchor"
    GRID = "grid"
    INSTANCE = "instance"


def _reject_mutable_containers(value: Any, path: str) -> None:
    """Reject any ``dict``/``list`` nested under ``value`` so immutability is
    enforced by construction, not only by the frozen dataclass."""
    if isinstance(value, dict) or isinstance(value, list):
        raise TypeError(f"{path} holds a mutable dict/list container")
    if isinstance(value, tuple):
        for index, item in enumerate(value):
            _reject_mutable_containers(item, f"{path}[{index}]")
    elif is_dataclass(value):
        for dataclass_field in fields(value):
            _reject_mutable_containers(
                getattr(value, dataclass_field.name),
                f"{path}.{dataclass_field.name}",
            )


@dataclass(frozen=True)
class BlueprintItemQuantity:
    """One item key plus its positive integer quantity in a proposal reward."""

    item_key: str
    quantity: int

    def __post_init__(self) -> None:
        _reject_mutable_containers(self, type(self).__name__)


@dataclass(frozen=True)
class BlueprintLocation:
    """One stage's scene requirement: a destination layer plus scene data.

    ``layer`` is ``anchor`` | ``grid`` | ``instance``; wilderness is not
    representable (the quest-blueprint spec forbids it).
    """

    layer: str
    archetype: str | None = None
    anchor_key: str | None = None
    anchor_near: str | None = None
    xyz: tuple[int, int, str] | None = None
    scene_sentence: str | None = None

    def __post_init__(self) -> None:
        _reject_mutable_containers(self, type(self).__name__)
        if self.layer not in {layer.value for layer in BlueprintLocationLayer}:
            raise ValueError(
                f"location_req.layer {self.layer!r} is outside "
                f"{[layer.value for layer in BlueprintLocationLayer]}"
            )


@dataclass(frozen=True)
class BlueprintPortrait:
    """One named portrait policy reference: exactly one ``stable_key`` field.

    ``stable_key`` means ``mode == "named"`` at spawn (design D2); there is no
    ``mode`` field in the blueprint. Frozen so the blueprint's immutability
    guard (``_reject_mutable_containers``) is preserved by construction.
    """

    stable_key: str

    def __post_init__(self) -> None:
        _reject_mutable_containers(self, type(self).__name__)


@dataclass(frozen=True)
class BlueprintNpcReq:
    """One stage's NPC requirement: role, tier, disposition, and optional
    story-driven characterization (design D1).

    ``display_name``, paired ``age``/``apparent_age``, ``portrait``, and the
    optional authored persona/background flavor block are optional per-occupant
    fields authored by the generative layer like speech and bounded
    deterministically by the shared ``world.quests.characterization`` helper.
    ``portrait`` is a frozen value object so the immutability-by-construction
    guard stays intact.
    """

    role: str
    tier: str
    disposition: str | None = None
    display_name: str | None = None
    age: int | None = None
    apparent_age: int | None = None
    portrait: BlueprintPortrait | None = None
    background: str | None = None
    persona: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _reject_mutable_containers(self, type(self).__name__)


@dataclass(frozen=True)
class BlueprintObjective:
    """One stage's progress mechanic: a closed kind plus its selectors."""

    kind: str
    quantity: int = 1
    monster_tier: str | None = None
    item_key: str | None = None

    def __post_init__(self) -> None:
        _reject_mutable_containers(self, type(self).__name__)
        if self.kind not in {kind.value for kind in BlueprintObjectiveKind}:
            raise ValueError(
                f"objective kind {self.kind!r} is outside "
                f"{[kind.value for kind in BlueprintObjectiveKind]}"
            )
        if isinstance(self.quantity, bool) or (
            not isinstance(self.quantity, int) or self.quantity < 1
        ):
            raise ValueError("objective quantity must be a positive integer")


@dataclass(frozen=True)
class BlueprintStage:
    """One explicit zero-based stage index plus its objective and requirements."""

    index: int
    objective: BlueprintObjective
    location: BlueprintLocation | None = None
    npc_reqs: tuple[BlueprintNpcReq, ...] = ()

    def __post_init__(self) -> None:
        _reject_mutable_containers(self, type(self).__name__)


@dataclass(frozen=True)
class BlueprintReward:
    """The immutable reward surfaces of one completed quest proposal."""

    copper: int
    items: tuple[BlueprintItemQuantity, ...] = ()
    merit: int = 0

    def __post_init__(self) -> None:
        _reject_mutable_containers(self, type(self).__name__)


@dataclass(frozen=True)
class BlueprintFailure:
    """The failure surfaces; ``conditions`` is a forward-declared empty seam."""

    deadline_hours: int | None = None
    conditions: tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        _reject_mutable_containers(self, type(self).__name__)
        if self.conditions:
            raise ValueError(
                "failure.conditions must stay empty in this change; "
                "deterministic failure conditions are a forward-declared seam"
            )


@dataclass(frozen=True)
class QuestBlueprint:
    """The closed, deeply immutable AI proposal (design §7.1).

    Distinct from the runtime ``QuestDefinition``: raw mappings are never
    accepted by the runtime registry, and the two types are not interchangeable.
    Immutability is enforced by construction: ``__post_init__`` walks nested
    values and rejects any mutable container, validates ``quest_type`` against
    the five ``BlueprintQuestType`` values, and requires stage indices to be
    contiguous starting at zero.
    """

    name: str
    quest_type: str
    rank: str
    issuer: str
    stages: tuple[BlueprintStage, ...]
    reward: BlueprintReward
    failure: BlueprintFailure

    def __post_init__(self) -> None:
        _reject_mutable_containers(self, type(self).__name__)
        if self.quest_type not in {quest_type.value for quest_type in BlueprintQuestType}:
            raise ValueError(
                f"quest_type {self.quest_type!r} is outside the five "
                f"{[quest_type.value for quest_type in BlueprintQuestType]} values"
            )
        if not self.stages:
            raise ValueError("a blueprint requires at least one stage")
        indices = [stage.index for stage in self.stages]
        if indices != list(range(len(self.stages))):
            raise ValueError(
                f"stage indices must be contiguous starting at zero, got {indices}"
            )

    def to_payload(self) -> dict[str, Any]:
        """Return the canonical JSON-safe proposal mapping (design D7).

        The per-stage mapping contract is pinned here and mirrored by the
        ``scenario_director`` output schema and the deterministic compiler:

        - ``quest_type`` stays a CJK value; the compiler maps it to
          ``QuestType``.
        - objective ``kind`` stays ``defeat``/``reach_location``/``escort``/
          ``acquire``; the compiler maps ``reach_location`` to
          ``ObjectiveKind.REACH`` and the rest one-to-one.
        - ``location_req.layer`` stays ``anchor``/``grid``/``instance``; the
          compiler maps them to ``DestinationKind`` (wilderness is not
          representable).
        - a DEFEAT stage declares exactly one of a known ``monster_tier`` or a
          non-empty ``npc_req`` (which becomes ``requires_bound_targets=True``).
        - an ACQUIRE stage declares a known ``item_key`` and a positive
          ``quantity``.
        - ``failure.deadline_hours`` maps to ``QuestDefinition.deadline_hours``;
          ``failure.conditions`` is accepted only as an empty list.
        """
        return {
            "name": self.name,
            "quest_type": self.quest_type,
            "rank": self.rank,
            "issuer": self.issuer,
            "stages": [
                {
                    "index": stage.index,
                    "objective": {
                        "kind": stage.objective.kind,
                        "quantity": stage.objective.quantity,
                        "monster_tier": stage.objective.monster_tier,
                        "item_key": stage.objective.item_key,
                    },
                    "location_req": (
                        None
                        if stage.location is None
                        else {
                            "layer": stage.location.layer,
                            "archetype": stage.location.archetype,
                            "anchor_key": stage.location.anchor_key,
                            "anchor_near": stage.location.anchor_near,
                            "xyz": (
                                None
                                if stage.location.xyz is None
                                else list(stage.location.xyz)
                            ),
                            "scene_sentence": stage.location.scene_sentence,
                        }
                    ),
                    "npc_req": [
                        {
                            "role": requirement.role,
                            "tier": requirement.tier,
                            "disposition": requirement.disposition,
                            **(
                                {"display_name": requirement.display_name}
                                if requirement.display_name is not None
                                else {}
                            ),
                            **(
                                {"age": requirement.age}
                                if requirement.age is not None
                                else {}
                            ),
                            **(
                                {"apparent_age": requirement.apparent_age}
                                if requirement.apparent_age is not None
                                else {}
                            ),
                            **(
                                {
                                    "portrait": {
                                        "stable_key": requirement.portrait.stable_key
                                    }
                                }
                                if requirement.portrait is not None
                                else {}
                            ),
                            **(
                                {"background": requirement.background}
                                if requirement.background is not None
                                else {}
                            ),
                            **(
                                {"persona": dict(requirement.persona)}
                                if requirement.persona
                                else {}
                            ),
                        }
                        for requirement in stage.npc_reqs
                    ],
                }
                for stage in self.stages
            ],
            "reward": {
                "copper": self.reward.copper,
                "items": [
                    {"item_key": item.item_key, "quantity": item.quantity}
                    for item in self.reward.items
                ],
                "merit": self.reward.merit,
            },
            "failure": {
                "deadline_hours": self.failure.deadline_hours,
                "conditions": list(self.failure.conditions),
            },
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "QuestBlueprint":
        """Build a frozen blueprint from a validated JSON-safe payload dict."""
        stages = tuple(
            BlueprintStage(
                index=stage["index"],
                objective=BlueprintObjective(
                    kind=stage["objective"]["kind"],
                    quantity=stage["objective"].get("quantity", 1),
                    monster_tier=stage["objective"].get("monster_tier"),
                    item_key=stage["objective"].get("item_key"),
                ),
                location=(
                    None
                    if stage.get("location_req") is None
                    else BlueprintLocation(
                        layer=stage["location_req"]["layer"],
                        archetype=stage["location_req"].get("archetype"),
                        anchor_key=stage["location_req"].get("anchor_key"),
                        anchor_near=stage["location_req"].get("anchor_near"),
                        xyz=(
                            None
                            if stage["location_req"].get("xyz") is None
                            else tuple(stage["location_req"]["xyz"])
                        ),
                        scene_sentence=stage["location_req"].get("scene_sentence"),
                    )
                ),
                npc_reqs=tuple(
                    BlueprintNpcReq(
                        role=requirement["role"],
                        tier=requirement["tier"],
                        disposition=requirement.get("disposition"),
                        display_name=requirement.get("display_name"),
                        age=requirement.get("age"),
                        apparent_age=requirement.get("apparent_age"),
                        portrait=(
                            BlueprintPortrait(
                                stable_key=requirement["portrait"]["stable_key"]
                            )
                            if requirement.get("portrait") is not None
                            else None
                        ),
                        background=requirement.get("background"),
                        persona=tuple(
                            tuple(pair)
                            for pair in (requirement.get("persona") or {}).items()
                        ),
                    )
                    for requirement in stage.get("npc_req") or ()
                ),
            )
            for stage in payload["stages"]
        )
        return cls(
            name=payload["name"],
            quest_type=payload["quest_type"],
            rank=payload["rank"],
            issuer=payload["issuer"],
            stages=stages,
            reward=BlueprintReward(
                copper=payload["reward"]["copper"],
                items=tuple(
                    BlueprintItemQuantity(item["item_key"], item["quantity"])
                    for item in payload["reward"].get("items") or ()
                ),
                merit=payload["reward"]["merit"],
            ),
            failure=BlueprintFailure(
                deadline_hours=payload["failure"]["deadline_hours"],
                conditions=tuple(payload["failure"].get("conditions") or ()),
            ),
        )


class ScenarioDirectorClientRequiredError(TypeError):
    """Raised when ``generate_quest_blueprint`` is called with an explicit ``None`` client."""


class ScenarioDirectorNotRegisteredError(RuntimeError):
    """Raised when ``generate_quest_blueprint`` runs before the layer hooks are installed."""


class ScenarioDirectorTemplateError(RuntimeError):
    """Raised when no template in the pool fits the request context."""


SCENARIO_DIRECTOR_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["name", "quest_type", "rank", "issuer", "stages", "reward", "failure"],
    "properties": {
        "name": {"type": "string"},
        "quest_type": {
            "type": "string",
            "enum": [quest_type.value for quest_type in BlueprintQuestType],
        },
        "rank": {"type": "string"},
        "issuer": {"type": "string"},
        "stages": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["index", "objective"],
                "properties": {
                    "index": {"type": "integer", "minimum": 0},
                    "objective": {
                        "type": "object",
                        "required": ["kind"],
                        "properties": {
                            "kind": {
                                "type": "string",
                                "enum": [
                                    kind.value for kind in BlueprintObjectiveKind
                                ],
                            },
                            "quantity": {"type": "integer", "minimum": 1},
                            "monster_tier": {"type": ["string", "null"]},
                            "item_key": {"type": ["string", "null"]},
                        },
                    },
                    "location_req": {
                        "anyOf": [
                            {"type": "null"},
                            {
                                "type": "object",
                                "required": ["layer"],
                                "properties": {
                                    "layer": {
                                        "type": "string",
                                        "enum": [
                                            layer.value
                                            for layer in BlueprintLocationLayer
                                        ],
                                    },
                                    "archetype": {"type": ["string", "null"]},
                                    "anchor_key": {"type": ["string", "null"]},
                                    "anchor_near": {"type": ["string", "null"]},
                                    "xyz": {
                                        "type": ["array", "null"],
                                        "items": [
                                            {"type": "integer"},
                                            {"type": "integer"},
                                            {"type": "string"},
                                        ],
                                        "minItems": 3,
                                        "maxItems": 3,
                                    },
                                    "scene_sentence": {"type": ["string", "null"]},
                                },
                            },
                        ]
                    },
                    "npc_req": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["role", "tier"],
                            "properties": {
                                "role": {"type": "string"},
                                "tier": {"type": "string"},
                                "disposition": {"type": ["string", "null"]},
                                "display_name": {"type": ["string", "null"]},
                                "age": {"type": ["integer", "null"]},
                                "apparent_age": {"type": ["integer", "null"]},
                                "portrait": {
                                    "type": ["object", "null"],
                                    "required": ["stable_key"],
                                    "properties": {
                                        "stable_key": {"type": "string"},
                                    },
                                    "additionalProperties": False,
                                },
                                "background": {"type": ["string", "null"]},
                                "persona": {
                                    "type": ["object", "null"],
                                    "properties": {
                                        "personality": {"type": "string"},
                                        "life_story": {"type": "string"},
                                        "habit": {"type": "string"},
                                    },
                                    "additionalProperties": False,
                                },
                            },
                        },
                    },
                },
            },
        },
        "reward": {
            "type": "object",
            "required": ["copper", "items", "merit"],
            "properties": {
                "copper": {"type": "integer", "minimum": 0},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["item_key", "quantity"],
                        "properties": {
                            "item_key": {"type": "string"},
                            "quantity": {"type": "integer", "minimum": 1},
                        },
                    },
                },
                "merit": {"type": "integer", "minimum": 0},
            },
        },
        "failure": {
            "type": "object",
            "required": ["deadline_hours", "conditions"],
            "properties": {
                "deadline_hours": {"type": ["integer", "null"], "minimum": 1},
                "conditions": {"type": "array", "maxItems": 0},
            },
        },
    },
}

_SCENARIO_DIRECTOR_DEGRADED = object()


def _degrade_fallback() -> object:
    """Return the sentinel so the entry point can map it to the template draw."""
    return _SCENARIO_DIRECTOR_DEGRADED


def _stages(parsed: Any) -> list[Any]:
    if not isinstance(parsed, dict):
        return []
    stages = parsed.get("stages")
    if not isinstance(stages, list):
        return []
    return stages


def _validate_rank_known(parsed: Any) -> list[str]:
    rank = parsed.get("rank") if isinstance(parsed, dict) else None
    if not isinstance(rank, str) or rank not in GUILD_RANK_REGISTRY:
        return [f"quest rank {rank!r} is not in GUILD_RANK_REGISTRY"]
    return []


def _validate_reward_in_band(parsed: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(parsed, dict):
        return errors
    rank = parsed.get("rank")
    reward = parsed.get("reward")
    guild_rank = GUILD_RANK_REGISTRY.get(rank) if isinstance(rank, str) else None
    if guild_rank is None or not isinstance(reward, dict):
        return errors
    copper = reward.get("copper")
    if isinstance(copper, bool) or not isinstance(copper, int):
        errors.append("reward copper must be an integer")
    else:
        band_floor = guild_rank.reward_min_copper
        band_ceiling = guild_rank.reward_max_copper
        if copper < band_floor or (band_ceiling is not None and copper > band_ceiling):
            errors.append(
                f"reward copper {copper} is outside {rank} rank "
                f"band [{band_floor}, {band_ceiling}]"
            )
    merit = reward.get("merit")
    if isinstance(merit, bool) or not isinstance(merit, int) or merit < 0:
        errors.append("reward merit must be a non-negative integer")
    return errors


def _validate_reward_items_known(parsed: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(parsed, dict):
        return errors
    reward = parsed.get("reward")
    if not isinstance(reward, dict):
        return errors
    items = reward.get("items")
    if not isinstance(items, list):
        return errors
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            errors.append("reward items must be objects")
            continue
        item_key = item.get("item_key")
        if not isinstance(item_key, str) or item_key not in ITEM_REGISTRY:
            errors.append(f"unknown reward item {item_key!r}")
        quantity = item.get("quantity")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            errors.append(
                f"reward item {item_key!r} quantity must be a positive integer"
            )
        if isinstance(item_key, str):
            if item_key in seen:
                errors.append(f"duplicate reward item key {item_key!r}")
            seen.add(item_key)
    return errors


def _validate_archetype_known(parsed: Any) -> list[str]:
    errors: list[str] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        location = stage.get("location_req")
        if not isinstance(location, dict):
            continue
        archetype = location.get("archetype")
        if archetype is not None and (
            not isinstance(archetype, str)
            or archetype not in SCENE_ARCHETYPE_REGISTRY
        ):
            errors.append(f"stage {index} unknown archetype {archetype!r}")
    return errors


def _validate_npc_tier_known(parsed: Any) -> list[str]:
    errors: list[str] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        requirements = stage.get("npc_req")
        if not isinstance(requirements, list):
            continue
        for requirement in requirements:
            if not isinstance(requirement, dict):
                errors.append(f"stage {index} npc_req entries must be objects")
                continue
            tier = requirement.get("tier")
            if not isinstance(tier, str) or tier not in NPC_TIER_REGISTRY:
                errors.append(f"stage {index} unknown NPC tier {tier!r}")
    return errors


def _validate_npc_characterization(parsed: Any) -> list[str]:
    """Validate every ``npc_req`` entry's optional characterization fields.

    Delegates per-entry age/name/key rules and the cross-entry duplicate
    ``stable_key`` agreement rule to the shared ``world.quests.characterization``
    helper -- the single rule source both this guardrail and the deterministic
    compiler call (design D3). The race-lifespan upper bound is resolved
    through the tier's ``race_key``; an unknown tier is reported by
    ``_validate_npc_tier_known``, so this validator skips it to avoid a second
    (redundant) diagnostic.
    """
    errors: list[str] = []
    entries: list[dict[str, Any]] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        requirements = stage.get("npc_req")
        if not isinstance(requirements, list):
            continue
        for requirement in requirements:
            if not isinstance(requirement, dict):
                continue
            entries.append(requirement)
            tier = requirement.get("tier")
            if not isinstance(tier, str) or tier not in NPC_TIER_REGISTRY:
                continue
            for message in characterize_errors(
                requirement,
                lifespan_upper_bound=race_lifespan_upper_bound(tier),
            ):
                errors.append(f"stage {index} {message}")
    errors.extend(duplicate_stable_key_errors(entries))
    return errors


def _validate_monster_tier_known(parsed: Any) -> list[str]:
    errors: list[str] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        objective = stage.get("objective")
        if not isinstance(objective, dict) or objective.get("kind") != "defeat":
            continue
        monster_tier = objective.get("monster_tier")
        if monster_tier is not None and (
            not isinstance(monster_tier, str)
            or monster_tier not in MONSTER_TIER_REGISTRY
        ):
            errors.append(f"stage {index} unknown monster tier {monster_tier!r}")
    return errors


def _validate_issuer_known(parsed: Any) -> list[str]:
    issuer = parsed.get("issuer") if isinstance(parsed, dict) else None
    if not isinstance(issuer, str) or issuer not in GUILD_BRANCH_REGISTRY:
        return [f"issuer branch {issuer!r} is not in GUILD_BRANCH_REGISTRY"]
    return []


def _validate_stage_indices_contiguous(parsed: Any) -> list[str]:
    indices = [
        stage.get("index")
        for stage in _stages(parsed)
        if isinstance(stage, dict)
    ]
    if indices != list(range(len(indices))):
        return [f"stage indices must be contiguous starting at zero, got {indices}"]
    return []


def _validate_deadline_valid(parsed: Any) -> list[str]:
    failure = parsed.get("failure") if isinstance(parsed, dict) else None
    if not isinstance(failure, dict):
        return []
    deadline = failure.get("deadline_hours")
    if deadline is not None and (
        isinstance(deadline, bool) or not isinstance(deadline, int) or deadline < 1
    ):
        return ["failure.deadline_hours must be None or a positive integer"]
    return []


def _is_cjk(text: str) -> bool:
    return any(_CJK_START <= ch <= _CJK_END for ch in text)


def _validate_strings_bounded_cjk(parsed: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(parsed, dict):
        return errors
    name = parsed.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("blueprint name is empty or whitespace-only")
    elif len(name) > MAX_NAME_LENGTH:
        errors.append(f"blueprint name exceeds the {MAX_NAME_LENGTH}-character cap")
    elif not _is_cjk(name):
        errors.append("blueprint name contains no CJK Unified Ideograph")
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        location = stage.get("location_req")
        if not isinstance(location, dict):
            continue
        sentence = location.get("scene_sentence")
        if sentence is None:
            continue
        if not isinstance(sentence, str) or not sentence.strip():
            errors.append(f"stage {index} scene_sentence is empty or whitespace-only")
        elif len(sentence) > MAX_SCENE_SENTENCE_LENGTH:
            errors.append(
                f"stage {index} scene_sentence exceeds the "
                f"{MAX_SCENE_SENTENCE_LENGTH}-character cap"
            )
        elif not _is_cjk(sentence):
            errors.append(f"stage {index} scene_sentence contains no CJK ideograph")
    return errors


def _validate_anchor_known(parsed: Any) -> list[str]:
    errors: list[str] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        location = stage.get("location_req")
        if not isinstance(location, dict) or location.get("layer") != "anchor":
            continue
        anchor_key = location.get("anchor_key")
        if not isinstance(anchor_key, str) or anchor_key not in ANCHOR_PLACEMENT_REGISTRY:
            errors.append(
                f"stage {index} ANCHOR locator references unplaced anchor {anchor_key!r}"
            )
    return errors


def _validate_defeat_selector(parsed: Any) -> list[str]:
    errors: list[str] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        objective = stage.get("objective")
        if not isinstance(objective, dict) or objective.get("kind") != "defeat":
            continue
        has_tier = objective.get("monster_tier") is not None
        npc_req = stage.get("npc_req")
        has_npc = isinstance(npc_req, list) and bool(npc_req)
        if has_tier == has_npc:
            errors.append(
                f"stage {index} DEFEAT must declare exactly one of a known "
                "monster_tier or a non-empty npc_req"
            )
    return errors


def _validate_scene_bound_rules(parsed: Any) -> list[str]:
    """Enforce the shared scene-bound rules the compiler also enforces (D5).

    Occupant-bearing scenes (any ``npc_req``) must be instance-layer so spawned
    entities always live in a reclaimable instance room; an ESCORT stage is
    refused entirely until a protected-entity binding flow exists; a
    bound-target DEFEAT quantity must not exceed its ``npc_req`` count; and
    ``anchor_near`` must name a placed anchor.
    """
    errors: list[str] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        location = stage.get("location_req")
        objective = stage.get("objective")
        npc_req = stage.get("npc_req")
        layer = location.get("layer") if isinstance(location, dict) else None
        has_npc = isinstance(npc_req, list) and bool(npc_req)
        is_escort = isinstance(objective, dict) and objective.get("kind") == "escort"
        if is_escort:
            errors.append(
                f"stage {index} declares an ESCORT objective, which cannot be "
                "published until a protected-entity binding flow exists"
            )
        if has_npc and layer != "instance":
            errors.append(
                f"stage {index} declares NPC requirements outside an "
                "instance-layer destination; occupant-bearing scenes must be "
                "instances"
            )
        if (
            isinstance(objective, dict)
            and objective.get("kind") == "defeat"
            and objective.get("monster_tier") is None
            and has_npc
        ):
            quantity = objective.get("quantity", 1)
            if (
                not isinstance(quantity, bool)
                and isinstance(quantity, int)
                and quantity > len(npc_req)
            ):
                errors.append(
                    f"stage {index} bound DEFEAT quantity {quantity} exceeds "
                    f"the number of npc_req entries {len(npc_req)}"
                )
        if isinstance(location, dict):
            anchor_near = location.get("anchor_near")
            if anchor_near is not None and (
                not isinstance(anchor_near, str)
                or anchor_near not in ANCHOR_PLACEMENT_REGISTRY
            ):
                errors.append(
                    f"stage {index} anchor_near {anchor_near!r} is not a placed "
                    "anchor in ANCHOR_PLACEMENT_REGISTRY"
                )
    return errors


def _validate_objective_selectors(parsed: Any) -> list[str]:
    errors: list[str] = []
    for index, stage in enumerate(_stages(parsed)):
        if not isinstance(stage, dict):
            continue
        objective = stage.get("objective")
        if not isinstance(objective, dict):
            continue
        kind = objective.get("kind")
        if kind == "acquire":
            if objective.get("item_key") is None:
                errors.append(f"stage {index} ACQUIRE requires a known item_key")
            if objective.get("monster_tier") is not None:
                errors.append(f"stage {index} ACQUIRE cannot declare a monster_tier")
        elif kind in ("reach_location", "escort"):
            if stage.get("location_req") is None:
                errors.append(
                    f"stage {index} {kind} requires a location_req destination"
                )
            if objective.get("monster_tier") is not None:
                errors.append(
                    f"stage {index} {kind} cannot declare a monster_tier"
                )
            quantity = objective.get("quantity", 1)
            if (
                not isinstance(quantity, bool)
                and isinstance(quantity, int)
                and quantity != 1
            ):
                errors.append(
                    f"stage {index} {kind} quantity must be exactly 1; "
                    "arrival observation cannot accumulate repeated visits"
                )
    return errors


def _validate_no_template_placeholder(parsed: Any) -> list[str]:
    search_text = ""
    if isinstance(parsed, dict):
        name = parsed.get("name")
        if isinstance(name, str):
            search_text += name
        for stage in _stages(parsed):
            if not isinstance(stage, dict):
                continue
            location = stage.get("location_req")
            if isinstance(location, dict):
                sentence = location.get("scene_sentence")
                if isinstance(sentence, str):
                    search_text += sentence
    if _TEMPLATE_PLACEHOLDER_RE.search(search_text):
        return ["blueprint echoes deterministic template-placeholder formatting syntax"]
    return []


_VALIDATORS: dict[str, Any] = {
    "rank_known": _validate_rank_known,
    "reward_in_band": _validate_reward_in_band,
    "reward_items_known": _validate_reward_items_known,
    "archetype_known": _validate_archetype_known,
    "npc_tier_known": _validate_npc_tier_known,
    "npc_characterization": _validate_npc_characterization,
    "monster_tier_known": _validate_monster_tier_known,
    "anchor_known": _validate_anchor_known,
    "defeat_selector": _validate_defeat_selector,
    "scene_bound_rules": _validate_scene_bound_rules,
    "objective_selectors": _validate_objective_selectors,
    "issuer_known": _validate_issuer_known,
    "stage_indices_contiguous": _validate_stage_indices_contiguous,
    "deadline_valid": _validate_deadline_valid,
    "strings_bounded_cjk": _validate_strings_bounded_cjk,
    "no_template_placeholder": _validate_no_template_placeholder,
}


_CONTEXT_KEYS = ("requested_type", "allowed_rank", "issuer_branch", "anchor", "note")
# Optional keys dropped (in this order) if the serialized context still
# exceeds the total-size bound, so the user message is always valid bounded JSON.
_CONTEXT_DROP_ORDER = ("note", "anchor", "requested_type", "allowed_rank")


def _cap_string(value: str) -> str:
    if len(value) <= MAX_CONTEXT_FIELD_LENGTH:
        return value
    return value[:MAX_CONTEXT_FIELD_LENGTH]


def _bounded_context(context: Any) -> str:
    """Serialize the request context within the hard prompt bounds.

    Only the fixed context keys are accepted; every string value is capped to
    ``MAX_CONTEXT_FIELD_LENGTH``. If the stable sorted JSON serialization still
    exceeds ``MAX_TOTAL_SIZE``, optional keys are dropped in a fixed order until
    it fits, so the returned text is always valid JSON within the bound.
    """
    if not isinstance(context, dict):
        raise TypeError("scenario-director context must be a mapping")
    payload: dict[str, Any] = {}
    for key in _CONTEXT_KEYS:
        if key not in context or context[key] is None:
            continue
        value = context[key]
        if not isinstance(value, (str, int, float, bool)):
            raise TypeError(f"scenario-director context field {key!r} must be plain data")
        payload[key] = _cap_string(str(value)) if isinstance(value, str) else value
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    for drop_key in _CONTEXT_DROP_ORDER:
        if len(text) <= MAX_TOTAL_SIZE or drop_key not in payload:
            continue
        del payload[drop_key]
        text = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return text


def build_scenario_prompt(
    context: dict[str, Any],
) -> tuple[dict[str, str], dict[str, str]]:
    """Build a deterministic (system, user) message pair for quest generation.

    The system message fixes the director role in 伊洛瑟恩大陸, the 正體中文
    language, the no-invention fidelity rule, and the ``QuestBlueprint`` JSON
    output contract with contiguous stage indices. The user message serializes
    the request context (requested type, allowed rank, issuer branch, anchor,
    and an optional note) with stable sorted JSON and ``ensure_ascii=False``.
    Identical input always produces byte-identical prompts with no live entity
    references.
    """
    system = {"role": "system", "content": render_prompt("scenario_director.system")}
    user = {"role": "user", "content": _bounded_context(context)}
    return system, user


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


def _uninstall_fallback() -> None:
    if guardrail._degrade_fallbacks.get("scenario_director") is _degrade_fallback:
        del guardrail._degrade_fallbacks["scenario_director"]


def _uninstall_validator(name: str) -> None:
    validators = guardrail._semantic_validators.get("scenario_director", {})
    if validators.get(name) is _VALIDATORS[name]:
        del validators[name]


def _uninstall_schema() -> None:
    if _OUTPUT_SCHEMAS.get("scenario_director") is SCENARIO_DIRECTOR_OUTPUT_SCHEMA:
        del _OUTPUT_SCHEMAS["scenario_director"]


def _uninstall_all_own_hooks() -> None:
    """Remove every scenario_director hook belonging to this module (by identity).

    Foreign hooks with the same names are left untouched, so a partial-failure
    registration can never leave the layer half-installed.
    """
    _uninstall_fallback()
    for name in _VALIDATORS:
        _uninstall_validator(name)
    _uninstall_schema()


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
        if guardrail._degrade_fallbacks.get("scenario_director") is not _degrade_fallback:
            register_degrade_fallback("scenario_director", _degrade_fallback)
        for name, validator in _VALIDATORS.items():
            validators = guardrail._semantic_validators.get("scenario_director", {})
            if validators.get(name) is validator:
                continue
            register_semantic_validator("scenario_director", name, validator)
        if _OUTPUT_SCHEMAS.get("scenario_director") is not SCENARIO_DIRECTOR_OUTPUT_SCHEMA:
            register_output_schema("scenario_director", SCENARIO_DIRECTOR_OUTPUT_SCHEMA)
    except (GuardrailRegistrationError, DuplicateSchemaError):
        _uninstall_all_own_hooks()
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
