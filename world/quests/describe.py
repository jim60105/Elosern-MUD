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
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.monster_species import (
    MONSTER_SPECIES_REGISTRY,
    MONSTER_VARIANT_REGISTRY,
)
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY
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
    line, note = describe_objective_parts(objective)
    return line if note is None else f"{line}（{note}）"


def describe_objective_parts(objective: QuestObjective) -> tuple[str, str | None]:
    """Return the requirement and optional counted-variant note separately."""
    if objective.kind is ObjectiveKind.DEFEAT:
        if objective.region_key is not None:
            return _describe_species_hunt(objective)
        if objective.requires_bound_targets:
            return f"討伐綁定的目標 {objective.quantity} 個", None
        tier = MONSTER_TIER_REGISTRY.get(objective.monster_tier)
        if tier is None:
            raise QuestDescribeError(f"unknown monster tier {objective.monster_tier!r}")
        return f"討伐 {objective.quantity} 隻{tier.display_name_zh}魔物", None
    if objective.kind is ObjectiveKind.REACH:
        return f"抵達{describe_destination(objective.destination)}", None
    if objective.kind is ObjectiveKind.ESCORT:
        return f"護送所有保護對象至{describe_destination(objective.destination)}", None
    if objective.kind is ObjectiveKind.ACQUIRE:
        item = ITEM_REGISTRY.get(objective.item_key)
        if item is None:
            raise QuestDescribeError(f"unknown item {objective.item_key!r}")
        return f"收集 {objective.quantity} 個{item.display_name_zh}", None
    if objective.kind is ObjectiveKind.DELIVER:
        item = ITEM_REGISTRY.get(objective.item_key)
        if item is None:
            raise QuestDescribeError(f"unknown item {objective.item_key!r}")
        return f"交付 {objective.quantity} 個{item.display_name_zh}", None
    raise QuestDescribeError(f"unknown ObjectiveKind {objective.kind!r}")


def _countable_variant_names(objective: QuestObjective) -> tuple[str, ...]:
    """The countable variants' display names in one stable (key) order."""
    names: list[str] = []
    for variant_key in sorted(objective.countable_variant_keys):
        variant = MONSTER_VARIANT_REGISTRY.get(variant_key)
        if variant is None:
            raise QuestDescribeError(f"unknown monster variant {variant_key!r}")
        names.append(variant.display_name_zh)
    return tuple(names)


def _describe_species_hunt(objective: QuestObjective) -> tuple[str, str | None]:
    """Render one regional species-hunt objective from the shared registries."""
    region = WILDERNESS_REGION_REGISTRY.get(objective.region_key)
    if region is None:
        raise QuestDescribeError(
            f"unknown wilderness region {objective.region_key!r}"
        )
    species = MONSTER_SPECIES_REGISTRY.get(objective.species_key)
    if species is None:
        raise QuestDescribeError(
            f"unknown monster species {objective.species_key!r}"
        )
    variants = "、".join(_countable_variant_names(objective))
    return (
        f"在{region.display_name_zh}討伐 {objective.quantity} 隻"
        f"{species.display_name_zh}",
        f"計數變體：{variants}",
    )


def _grade_line(definition: QuestDefinition) -> str:
    """Render the authored guild grade the definition alone carries.

    The grade is never derived from a targeted individual's danger grade; an
    authored rank with no registry row still renders as authored rather than
    failing a view over a definition registration accepted.
    """
    rank = GUILD_RANK_REGISTRY.get(definition.rank)
    return f"階級：{definition.rank if rank is None else rank.display_name_zh}"


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


def describe_reward_parts(reward: Any) -> dict[str, Any]:
    """Return reward values with registry-owned item names in declared order."""
    items = []
    for quantity in reward.items:
        item = ITEM_REGISTRY.get(quantity.item_key)
        if item is None:
            raise QuestDescribeError(f"unknown item {quantity.item_key!r}")
        items.append({
            "item_key": quantity.item_key,
            "display_name": item.display_name_zh,
            "quantity": quantity.quantity,
        })
    return {"copper": reward.copper, "merit": reward.merit, "items": items}


def describe_reward(offer: Any) -> str:
    """Render one offer's reward into a single Traditional Chinese line."""
    reward = describe_reward_parts(offer.reward)
    item_text = "、".join(
        f"{item['display_name']} × {item['quantity']}"
        for item in reward["items"]
    )
    line = f"獎勵：銅 {reward['copper']}、功績 {reward['merit']}"
    if item_text:
        line += f"、{item_text}"
    return line


def _reward_line(offer: Any) -> str:
    return describe_reward(offer)


def describe_deadline(deadline_tick: int | None, current_tick: int) -> str | None:
    """Render the remaining-deadline line, or ``None`` when no deadline exists.

    This is the public rendering seam the services panel uses so its quest
    rows reuse the exact prose the ``guild show`` command produces.
    """
    return _deadline_line(deadline_tick, current_tick)


def describe_quest_detail(
    record: Any,
    definition: QuestDefinition,
    offer: Any,
    current_tick: int,
) -> str:
    """Render one quest record's full detail from a definition and optional offer.

    ``current_tick`` is injected by the caller so the renderer never reads the
    world clock. The reward section is omitted when ``offer`` is ``None``. The
    authored grade is always rendered; the rating rationale and background
    flavor sections render verbatim and are omitted when the definition does
    not carry them (never fabricated).
    """
    stage = definition.stages[record.stage_index]
    state_value = getattr(record.state, "value", record.state)
    lines = [
        f"{definition.display_name}",
        f"狀態：{_STATE_LABELS.get(state_value, str(state_value))}",
        f"階段：{record.stage_index + 1}",
        f"目標：{describe_objective(stage.objective)}",
        f"進度：{record.stage_progress} / {stage.objective.quantity}",
        _grade_line(definition),
    ]
    if definition.rating_rationale_zh is not None:
        lines.append(f"評價理由：{definition.rating_rationale_zh}")
    if definition.background_flavor_zh is not None:
        lines.append(f"背景：{definition.background_flavor_zh}")
    deadline = _deadline_line(record.deadline_tick, current_tick)
    if deadline is not None:
        lines.append(deadline)
    if offer is not None:
        lines.append(_reward_line(offer))
    return "\n".join(lines)
