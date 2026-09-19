"""The frozen ``QuestBlueprint`` proposal vocabulary (design §7.1).

The closed, deeply immutable AI proposal types exchanged between the
scenario-director generative layer, the deterministic compiler, and the
hand-written template pool. Immutability is enforced by construction: every
``__post_init__`` walks nested values and rejects any mutable container, so a
proposal is safe to hand across the ``world/ai`` boundary unchanged. The
boundary contract (``tests/test_ai_transport_contract.py``): this module
imports no state writer, no typeclass, no live transport, and no socket.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from world.ai.immutable import (
    reject_mutable_containers as _reject_mutable_containers,
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
    """One stage's NPC requirement: role, tier, disposition, and story-driven
    characterization (design D1).

    ``display_name`` and ``title`` are the REQUIRED authored identity fields
    (npc-title-authored-identities D5): the structural layer keeps the
    defaulted ``str | None`` shape so a missing field surfaces as the shared
    helper's named guardrail diagnostic instead of a constructor error. Paired
    ``age``/``apparent_age``, ``portrait``, and the optional authored
    persona/background flavor block stay optional. All fields are authored by
    the generative layer like speech and bounded deterministically by the
    shared ``world.quests.characterization`` helper. ``portrait`` is a frozen
    value object so the immutability-by-construction guard stays intact.
    """

    role: str
    tier: str
    disposition: str | None = None
    display_name: str | None = None
    title: str | None = None
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
                                {"title": requirement.title}
                                if requirement.title is not None
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
                        title=requirement.get("title"),
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
