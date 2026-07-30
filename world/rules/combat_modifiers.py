"""Pure combat-modifier query for design section 6.4."""

from pathlib import Path
import re
from typing import Any

from world.rules.buffs import entity_active_buffs
from world.rules.rulebook.schema import evaluate_condition, load_rules

_RULES = load_rules(Path(__file__).parent / "rulebook" / "combat_modifiers.yaml")


def _build_context(entity) -> dict[str, Any]:
    context: dict[str, Any] = {"active_buffs": entity_active_buffs(entity)}
    sexual = getattr(entity, "sexual", None)
    if sexual is not None:
        context["arousal"] = sexual.arousal
        context["climax_phase"] = sexual.climax_phase
    return context


def _merge_adjustments(result: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Add numeric and percentage adjustments; later non-additive values replace."""
    merged = dict(result)
    for key, value in incoming.items():
        current = merged.get(key)
        if isinstance(value, (int, float)) and isinstance(current, (int, float)):
            merged[key] = current + value
        elif (
            isinstance(value, str)
            and isinstance(current, str)
            and re.fullmatch(r"[+-]\d+%", value)
            and re.fullmatch(r"[+-]\d+%", current)
        ):
            merged[key] = f"{int(current[:-1]) + int(value[:-1]):+d}%"
        else:
            merged[key] = value
    return merged


def evaluate_combat_modifiers(entity) -> dict[str, Any]:
    """Return the merged matching bundle without mutating entity state."""
    context = _build_context(entity)
    result: dict[str, Any] = {}
    for rule in _RULES:
        if evaluate_condition(rule.when, context):
            result = _merge_adjustments(result, rule.then)
    return result
