"""Hand-written deterministic quest catalog (quest-runtime D-2).

Content here uses only permanent world content and no AI services. The
introductory hunt completes through ordinary ``ActionResolver`` combat; change
16 supplies the player-facing accept/combat-entry/turn-in that turns this into
a playable milestone.
"""

from .definitions import (
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    register_quest_definition,
)


INTRODUCTORY_HUNT = QuestDefinition(
    key="introductory_hunt",
    display_name="討伐低階魔物",
    quest_type=QuestType.DEFEAT,
    rank="F",
    stages=(
        QuestStage(
            index=0,
            objective=QuestObjective(
                kind=ObjectiveKind.DEFEAT,
                quantity=1,
                monster_tier="low",
            ),
        ),
    ),
    deadline_hours=None,
)

QUEST_CATALOG: tuple[QuestDefinition, ...] = (INTRODUCTORY_HUNT,)


def register_catalog() -> None:
    """Register every catalog definition idempotently."""
    for definition in QUEST_CATALOG:
        register_quest_definition(definition)