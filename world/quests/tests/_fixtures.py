"""Shared fixtures for quest-runtime tests (registry isolation and builders)."""

from dataclasses import replace

from world.quests.catalog import INTRODUCTORY_HUNT, register_catalog
from world.quests.definitions import (
    DestinationKind,
    ObjectiveKind,
    QUEST_DEFINITION_REGISTRY,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    RoomLocator,
    register_quest_definition,
)


class QuestRegistryIsolation:
    """Snapshot and restore the process-global definition registry.

    ``QUEST_DEFINITION_REGISTRY`` is module-global and shared across the whole
    test process, so every quest test restores whatever it found rather than
    clearing state other tests (or the catalog) rely on.
    """

    def setUp(self):
        super().setUp()
        self._registry_items = list(QUEST_DEFINITION_REGISTRY.items())

    def tearDown(self):
        QUEST_DEFINITION_REGISTRY.clear()
        QUEST_DEFINITION_REGISTRY.update(self._registry_items)
        super().tearDown()


def defeat(tier="low", *, bound=False, quantity=1) -> QuestObjective:
    return QuestObjective(
        kind=ObjectiveKind.DEFEAT,
        quantity=quantity,
        monster_tier=None if bound else tier,
        requires_bound_targets=bound,
    )


def reach(destination: RoomLocator | None = None, quantity=1) -> QuestObjective:
    return QuestObjective(
        kind=ObjectiveKind.REACH,
        quantity=quantity,
        destination=destination,
    )


def escort(destination: RoomLocator | None = None) -> QuestObjective:
    return QuestObjective(
        kind=ObjectiveKind.ESCORT,
        destination=destination,
    )


def acquire(item_key: str, quantity: int = 1) -> QuestObjective:
    return QuestObjective(
        kind=ObjectiveKind.ACQUIRE,
        quantity=quantity,
        item_key=item_key,
    )


def anchor_locator() -> RoomLocator:
    return RoomLocator(DestinationKind.ANCHOR, anchor_key="capital_altoria")


def grid_locator(x: int = 2, y: int = 2) -> RoomLocator:
    return RoomLocator(DestinationKind.GRID, xyz=(x, y, "capital_altoria"))


def bound_instance_locator() -> RoomLocator:
    return RoomLocator(DestinationKind.BOUND_INSTANCE)


def quest(
    key: str,
    stages: tuple[QuestStage, ...] | None = None,
    *,
    quest_type: QuestType = QuestType.DEFEAT,
    rank: str = "F",
    deadline_hours: int | None = None,
) -> QuestDefinition:
    if stages is None:
        stages = (QuestStage(index=0, objective=defeat()),)
    return QuestDefinition(
        key=key,
        display_name=f"測試任務 {key}",
        quest_type=quest_type,
        rank=rank,
        stages=stages,
        deadline_hours=deadline_hours,
    )


def register(definition: QuestDefinition) -> QuestDefinition:
    """Register ``definition`` and reload it from the registry for identity."""
    register_quest_definition(definition)
    return QUEST_DEFINITION_REGISTRY[definition.key]


def register_catalog_once() -> None:
    """Register the shipped catalog definitions (idempotent snapshot-safe)."""
    if "introductory_hunt" not in QUEST_DEFINITION_REGISTRY:
        register_catalog()


def intro_hunt_key() -> str:
    return INTRODUCTORY_HUNT.key