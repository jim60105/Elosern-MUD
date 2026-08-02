"""Read-only rendering of quest records and objectives into player-facing prose.

This module turns immutable quest values (``QuestObjective``, ``RoomLocator``,
``QuestRecord``, ``QuestDefinition``, ``GuildQuestOffer``) into Traditional
Chinese text. It performs no writes and never reads the world clock itself:
``current_tick`` is injected so every display rule stays a pure function.

It imports only immutable registries (quest definitions, lore anchors/monsters/
items, and the clock ratios) so the renderer stays dependency-light and
unit-testable in isolation. A kind outside the closed definition vocabulary
raises ``QuestDescribeError`` so drift fails loudly in tests.
"""

from typing import TYPE_CHECKING, Any

from world.lore.anchors import ANCHOR_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.quests.definitions import (
    DestinationKind,
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    RoomLocator,
)
from world.rules.clock import CLOCK_YAML

if TYPE_CHECKING:
    from world.quests.runtime import QuestRecord
    from world.rules.guild_offers import GuildQuestOffer

_SECONDS_PER_HOUR = CLOCK_YAML["seconds_per_hour"]

_STATE_LABELS = {
    "in_progress": "進行中",
    "completed": "已完成",
    "failed": "已失敗",
}


class QuestDescribeError(ValueError):
    """The renderer met a definition-vocabulary kind it does not recognize."""


def describe_destination(locator: RoomLocator | None) -> str:
    """Render one ``RoomLocator`` into a Traditional Chinese destination phrase."""
    if locator is None:
        raise QuestDescribeError("objective has no destination")
    if locator.kind is DestinationKind.ANCHOR:
        anchor = ANCHOR_REGISTRY.get(locator.anchor_key)
        if anchor is None:
            raise QuestDescribeError(f"unknown anchor {locator.anchor_key!r}")
        return anchor.display_name_zh
    if locator.kind is DestinationKind.GRID:
        if locator.xyz is None:
            raise QuestDescribeError("GRID locator carries no coordinates")
        x, y, _z = locator.xyz
        return f"座標 ({x}, {y})"
    if locator.kind is DestinationKind.BOUND_INSTANCE:
        return "指定的地點"
    raise QuestDescribeError(f"unknown DestinationKind {locator.kind!r}")


def describe_objective(objective: QuestObjective) -> str:
    """Render one objective into a single Traditional Chinese requirement line."""
    if objective.kind is ObjectiveKind.DEFEAT:
        if objective.requires_bound_targets:
            return f"討伐綁定的目標 {objective.quantity} 個"
        tier = MONSTER_TIER_REGISTRY.get(objective.monster_tier)
        if tier is None:
            raise QuestDescribeError(f"unknown monster tier {objective.monster_tier!r}")
        return f"討伐 {objective.quantity} 隻{tier.display_name_zh}魔物"
    if objective.kind is ObjectiveKind.REACH:
        return f"抵達{describe_destination(objective.destination)}"
    if objective.kind is ObjectiveKind.ESCORT:
        return f"護送所有保護對象至{describe_destination(objective.destination)}"
    if objective.kind is ObjectiveKind.ACQUIRE:
        item = ITEM_REGISTRY.get(objective.item_key)
        if item is None:
            raise QuestDescribeError(f"unknown item {objective.item_key!r}")
        return f"收集 {objective.quantity} 個{item.display_name_zh}"
    raise QuestDescribeError(f"unknown ObjectiveKind {objective.kind!r}")


def _deadline_line(deadline_tick: int | None, current_tick: int) -> str | None:
    """Render the remaining-deadline line, or ``None`` when no deadline exists.

    Remaining seconds are floored to whole hours. A remaining duration of less
    than one hour is reported as "不足 1 小時" rather than a misleading
    "0 小時"; a non-positive remaining value reports the quest as overdue.
    """
    if deadline_tick is None:
        return None
    remaining = deadline_tick - current_tick
    if remaining <= 0:
        return "期限：已逾期"
    hours = remaining // _SECONDS_PER_HOUR
    if hours < 1:
        return "期限：剩餘不足 1 小時"
    return f"期限：剩餘 {hours} 小時"


def _reward_line(offer: Any) -> str:
    reward = offer.reward
    item_text = "、".join(
        f"{ITEM_REGISTRY[quantity.item_key].display_name_zh} × {quantity.quantity}"
        for quantity in reward.items
    )
    line = f"獎勵：銅 {reward.copper}、功績 {reward.merit}"
    if item_text:
        line += f"、{item_text}"
    return line


def describe_quest_detail(
    record: Any,
    definition: QuestDefinition,
    offer: Any,
    current_tick: int,
) -> str:
    """Render one quest record's full detail from a definition and optional offer.

    ``current_tick`` is injected by the caller so the renderer never reads the
    world clock. The reward section is omitted when ``offer`` is ``None``.
    """
    stage = definition.stages[record.stage_index]
    state_value = getattr(record.state, "value", record.state)
    lines = [
        f"{definition.display_name}",
        f"狀態：{_STATE_LABELS.get(state_value, str(state_value))}",
        f"階段：{record.stage_index + 1}",
        f"目標：{describe_objective(stage.objective)}",
        f"進度：{record.stage_progress} / {stage.objective.quantity}",
    ]
    deadline = _deadline_line(record.deadline_tick, current_tick)
    if deadline is not None:
        lines.append(deadline)
    if offer is not None:
        lines.append(_reward_line(offer))
    return "\n".join(lines)
