"""Normalized deterministic quest definitions (quest-runtime D-1).

This module owns the closed, immutable runtime input consumed by the quest
state machine. It is deliberately distinct from change 20's future AI
``QuestBlueprint`` proposal: raw mappings are never accepted here, and the
same structural vocabulary (type / objectives / destination layers) is the
narrow conversion target that change 20's guardrail will compile to.
"""

from dataclasses import dataclass
from enum import StrEnum

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.maps.altoria_capital import XYMAP_DATA_LIST


class QuestType(StrEnum):
    """The complete quest's classification; it does not restrict stage mechanics."""

    GATHER = "採集"
    DEFEAT = "討伐"
    ESCORT = "護衛"
    EXPLORE = "探索"
    EMERGENCY = "緊急"


class ObjectiveKind(StrEnum):
    """The deterministic progress mechanic of one stage."""

    DEFEAT = "defeat"
    REACH = "reach"
    ESCORT = "escort"
    ACQUIRE = "acquire"


class DestinationKind(StrEnum):
    """Where a static or generated destination lives."""

    ANCHOR = "anchor"
    GRID = "grid"
    BOUND_INSTANCE = "bound_instance"


class QuestDefinitionError(ValueError):
    """A definition violates the closed runtime input contract."""


KNOWN_GRID_MAP_KEYS: frozenset[str] = frozenset(
    map_data["zcoord"]
    for map_data in XYMAP_DATA_LIST
)


@dataclass(frozen=True)
class RoomLocator:
    """A destination that needs no room dbref at definition time.

    ANCHOR carries exactly ``anchor_key``; GRID carries exactly ``xyz``;
    BOUND_INSTANCE carries neither and resolves only through an accepted
    record's ``stage_room_id``.
    """

    kind: DestinationKind
    anchor_key: str | None = None
    xyz: tuple[int, int, str] | None = None


@dataclass(frozen=True)
class QuestObjective:
    """One stage's typed, fully deterministic progress criterion."""

    kind: ObjectiveKind
    quantity: int = 1
    monster_tier: str | None = None
    destination: RoomLocator | None = None
    requires_bound_targets: bool = False
    item_key: str | None = None


@dataclass(frozen=True)
class QuestStage:
    """One explicit, zero-based stage index plus its objective."""

    index: int
    objective: QuestObjective


@dataclass(frozen=True)
class QuestDefinition:
    """The immutable runtime definition of one hand-written quest."""

    key: str
    display_name: str
    quest_type: QuestType
    rank: str
    stages: tuple[QuestStage, ...]
    deadline_hours: int | None = None


def _reject(definition: QuestDefinition, message: str) -> None:
    raise QuestDefinitionError(f"{definition.key}: {message}")


def _validate_destination(
    definition: QuestDefinition,
    destination: RoomLocator | None,
    kind: ObjectiveKind,
) -> None:
    if destination is None:
        _reject(definition, f"{kind.value} objective requires a destination")
    if not isinstance(destination, RoomLocator):
        _reject(definition, "destination must be a RoomLocator")
    if destination.kind is DestinationKind.ANCHOR:
        if destination.xyz is not None:
            _reject(definition, "ANCHOR locator cannot carry XYZ coordinates")
        if not destination.anchor_key:
            _reject(definition, "ANCHOR locator requires an anchor_key")
        if destination.anchor_key not in ANCHOR_PLACEMENT_REGISTRY:
            _reject(
                definition,
                f"anchor {destination.anchor_key!r} has no reachable AnchorRoom "
                "in ANCHOR_PLACEMENT_REGISTRY",
            )
    elif destination.kind is DestinationKind.GRID:
        if destination.anchor_key is not None:
            _reject(definition, "GRID locator cannot carry an anchor_key")
        xyz = destination.xyz
        if not isinstance(xyz, tuple) or len(xyz) != 3:
            _reject(definition, "GRID locator requires an (x, y, z) tuple")
        x, y, z = xyz
        if (
            isinstance(x, bool)
            or isinstance(y, bool)
            or not isinstance(x, int)
            or not isinstance(y, int)
        ):
            _reject(definition, "GRID locator x/y must be integers")
        if not isinstance(z, str) or not z:
            _reject(definition, "GRID locator z must be a non-empty map key")
        if z not in KNOWN_GRID_MAP_KEYS:
            _reject(definition, f"grid map key {z!r} is not known to the xyzgrid")
    elif destination.kind is DestinationKind.BOUND_INSTANCE:
        if destination.anchor_key is not None or destination.xyz is not None:
            _reject(definition, "BOUND_INSTANCE locator cannot carry static location fields")
    else:
        _reject(definition, f"unknown DestinationKind {destination.kind!r}")


def _validate_objective(
    definition: QuestDefinition,
    objective: QuestObjective,
) -> None:
    if not isinstance(objective, QuestObjective):
        _reject(definition, "stages must carry QuestObjective values")
    if isinstance(objective.quantity, bool) or (
        not isinstance(objective.quantity, int) or objective.quantity < 1
    ):
        _reject(definition, "objective quantity must be a positive integer")
    if objective.kind is ObjectiveKind.DEFEAT:
        if objective.destination is not None:
            _reject(definition, "DEFEAT objective cannot declare a destination")
        has_tier = objective.monster_tier is not None
        has_bound = objective.requires_bound_targets is True
        if has_tier == has_bound:
            _reject(
                definition,
                "DEFEAT objective must declare exactly one of a known "
                "monster_tier or requires_bound_targets=True",
            )
        if has_tier and objective.monster_tier not in MONSTER_TIER_REGISTRY:
            _reject(
                definition,
                f"unknown monster tier {objective.monster_tier!r}",
            )
    elif objective.kind is ObjectiveKind.REACH:
        if objective.monster_tier is not None or objective.requires_bound_targets:
            _reject(definition, "REACH objective cannot declare defeat selectors")
        _validate_destination(definition, objective.destination, ObjectiveKind.REACH)
    elif objective.kind is ObjectiveKind.ESCORT:
        if objective.monster_tier is not None or objective.requires_bound_targets:
            _reject(definition, "ESCORT objective cannot declare defeat selectors")
        _validate_destination(definition, objective.destination, ObjectiveKind.ESCORT)
    elif objective.kind is ObjectiveKind.ACQUIRE:
        if (
            objective.monster_tier is not None
            or objective.destination is not None
            or objective.requires_bound_targets
        ):
            _reject(
                definition,
                "ACQUIRE objective cannot declare defeat selectors, a destination, "
                "or bound-target requirements",
            )
        item_key = objective.item_key
        if not isinstance(item_key, str) or not item_key:
            _reject(definition, "ACQUIRE objective requires exactly one known item_key")
        if item_key not in ITEM_REGISTRY:
            _reject(definition, f"ACQUIRE objective references unknown item {item_key!r}")
    else:
        _reject(definition, f"unknown ObjectiveKind {objective.kind!r}")


def validate_definition(definition: QuestDefinition) -> None:
    """Raise ``QuestDefinitionError`` unless ``definition`` is fully valid."""
    if not isinstance(definition, QuestDefinition):
        raise QuestDefinitionError(
            "quest definitions must be QuestDefinition values, not raw mappings"
        )
    if not isinstance(definition.key, str) or not definition.key:
        _reject(definition, "definition key must be a non-empty string")
    if not isinstance(definition.display_name, str) or not definition.display_name:
        _reject(definition, "display_name must be a non-empty string")
    if not isinstance(definition.quest_type, QuestType):
        _reject(definition, "quest_type must be a QuestType value")
    if not isinstance(definition.rank, str) or not definition.rank:
        _reject(definition, "rank must be a non-empty string")
    if not isinstance(definition.stages, tuple) or not definition.stages:
        _reject(definition, "stages must be a non-empty tuple of QuestStage values")
    deadline = definition.deadline_hours
    if deadline is not None and (
        isinstance(deadline, bool) or not isinstance(deadline, int) or deadline < 1
    ):
        _reject(
            definition,
            "deadline_hours must be None (no deadline) or a positive integer",
        )
    indices = [stage.index for stage in definition.stages]
    expected = list(range(len(definition.stages)))
    if not all(isinstance(stage, QuestStage) for stage in definition.stages):
        _reject(definition, "stages must carry QuestStage values")
    if indices != expected:
        _reject(
            definition,
            f"stage indices must be contiguous starting at zero, got {indices}",
        )
    for stage in definition.stages:
        _validate_objective(definition, stage.objective)


QUEST_DEFINITION_REGISTRY: dict[str, QuestDefinition] = {}


def register_quest_definition(definition: QuestDefinition) -> None:
    """Register one validated, immutable definition idempotently.

    Registering equal content under an existing key is a no-op; conflicting
    content under an existing key raises before replacing anything.
    """
    validate_definition(definition)
    current = QUEST_DEFINITION_REGISTRY.get(definition.key)
    if current is not None:
        if current == definition:
            return
        raise QuestDefinitionError(
            f"{definition.key}: conflicting content already registered"
        )
    QUEST_DEFINITION_REGISTRY[definition.key] = definition