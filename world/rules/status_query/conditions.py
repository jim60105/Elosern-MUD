"""The deterministic condition-row projection shared by both panels.

``condition_values`` is the one place a read's buff-cache entries and matched
combat-modifier rules become ordered :class:`ConditionValue` rows, so the
compact ``status`` panel and the ``character`` panel can never disagree about
which conditions a member carries or in which order they appear.

``condition_source`` names a condition's origin in the shared player-facing
vocabulary. The structured provenance stays on the ``status`` panel; the
``character`` panel carries this bounded origin label instead.
"""

from typing import Any

from world.rules.status_display import display_for

from .models import ConditionValue


def condition_values(assembly: Any) -> tuple[ConditionValue, ...]:
    """Project one assembly's active buffs and matched rules into exact rows.

    Buffs come first in their cache order, then the matched combat-modifier
    rules in the deterministic match order — the ordering both panels publish.
    """
    conditions: list[ConditionValue] = []
    for buff_key, cache in assembly.buff_entries:
        definition_key = cache.get("definition_key")
        display = display_for(definition_key)
        conditions.append(
            ConditionValue(
                code=definition_key,
                label=display.label,
                severity=display.severity,
                remaining_seconds=cache.get("remaining_seconds"),
                modifiers={},
                provenance=assembly.buff_provenance[buff_key],
            )
        )
    for rule_id, adjustments in assembly.matches:
        display = display_for(rule_id)
        conditions.append(
            ConditionValue(
                code=rule_id,
                label=display.label,
                severity=display.severity,
                remaining_seconds=None,
                modifiers=dict(adjustments),
                provenance=assembly.rule_provenance[rule_id],
            )
        )
    return tuple(conditions)


#: The closed origin vocabulary a ``character`` condition row publishes. The
#: keys are the structured provenance kinds; the values are the shared
#: Traditional-Chinese origin words (the same 裝備/狀態 words the breakdown
#: layer chips use). A provenance that cannot attribute an origin says so.
CONDITION_SOURCE_LABELS = {
    "equipment": "裝備",
    "non_equipment": "狀態",
    "mixed": "裝備、狀態",
    "unknown": "未知",
}


def condition_source(provenance: Any) -> str:
    """Return the bounded origin label for one condition provenance."""
    try:
        return CONDITION_SOURCE_LABELS[provenance.kind]
    except (AttributeError, KeyError) as error:
        raise ValueError("condition provenance kind is invalid") from error


__all__ = [
    "CONDITION_SOURCE_LABELS",
    "condition_source",
    "condition_values",
]
