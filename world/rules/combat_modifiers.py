"""Pure combat-modifier query for design section 6.4."""

from pathlib import Path
import re
from typing import Any

from world.lore.sexual_vocab import AROUSAL_LEVELS, CLIMAX_PHASE_LEVELS
from world.rules.buffs import active_buff_keys_from_storage, entity_active_buffs
from world.rules.rulebook.schema import evaluate_condition, load_rules

_RULES = load_rules(Path(__file__).parent / "rulebook" / "combat_modifiers.yaml")


class _StoredLevel:
    """Read-only ordinal mirror for stored sexual-level comparisons."""

    def __init__(self, value: int, levels: tuple[str, ...]):
        self.value = value
        self.levels = tuple(levels)

    def _ordinal_of(self, other: Any) -> int:
        if isinstance(other, _StoredLevel):
            return other.value
        if isinstance(other, str):
            return self.levels.index(other)
        return int(other)

    def __eq__(self, other: object) -> bool:
        return self.value == self._ordinal_of(other)

    def __ge__(self, other: object) -> bool:
        return self.value >= self._ordinal_of(other)

    def __gt__(self, other: object) -> bool:
        return self.value > self._ordinal_of(other)

    def __le__(self, other: object) -> bool:
        return self.value <= self._ordinal_of(other)

    def __lt__(self, other: object) -> bool:
        return self.value < self._ordinal_of(other)


def _stored_sexual_level(entity: Any, field: str) -> Any:
    """Read one stored sexual level without materializing the handler."""
    from collections.abc import Mapping

    traits = entity.attributes.get("sexual_traits", default=None, category="traits")
    if isinstance(traits, Mapping) and field in traits:
        raw = traits[field]
        if isinstance(raw, Mapping):
            value = raw.get("value")
            levels = raw.get("levels") or ()
            if isinstance(value, str):
                if levels:
                    try:
                        return _StoredLevel(levels.index(value), tuple(levels))
                    except ValueError:
                        return value
                return value
            if isinstance(value, int) and isinstance(levels, (list, tuple)) and 0 <= value < len(levels):
                return _StoredLevel(value, tuple(levels))
            return value
    from collections.abc import Mapping

    baseline = entity.attributes.get("sexual", default=None)
    if isinstance(baseline, Mapping) and isinstance(baseline.get(field), str):
        return baseline[field]
    return None


def build_no_create_condition_context(entity: Any) -> dict[str, Any]:
    """Build the combat-modifier condition context from stored state only.

    Reads the persisted buff cache and stored sexual traits or baseline without
    materializing ``entity.buffs`` or ``entity.sexual``. Returns a context
    accepted by :func:`matched_combat_modifiers` so preview and revalidation
    never create a lazy handler or default attribute.
    """
    context: dict[str, Any] = {"active_buffs": active_buff_keys_from_storage(entity)}
    for field, levels in (("arousal", AROUSAL_LEVELS), ("climax_phase", CLIMAX_PHASE_LEVELS)):
        value = _stored_sexual_level(entity, field)
        if isinstance(value, str) and value in levels:
            context[field] = _StoredLevel(levels.index(value), levels)
        elif isinstance(value, _StoredLevel):
            context[field] = value
    return context


def evaluate_combat_modifiers_no_create(entity: Any) -> dict[str, Any]:
    """Return the merged matching bundle from stored state without handlers."""
    result: dict[str, Any] = {}
    for _, adjustments in matched_combat_modifiers(
        entity, context=build_no_create_condition_context(entity)
    ):
        result = _merge_adjustments(result, adjustments)
    return result


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


def matched_combat_modifiers(
    entity, context: dict[str, Any] | None = None
) -> tuple[tuple[str, dict[str, Any]], ...]:
    """Return each matched rule ID with its exact adjustment bundle.

    This read-only query exposes the deterministic per-rule matches so
    presentation can show each condition without re-evaluating thresholds or
    reproducing modifier math. ``context`` is the condition context; when
    omitted it is rebuilt from ``entity``.
    """
    if context is None:
        context = _build_context(entity)
    matches: list[tuple[str, dict[str, Any]]] = []
    for rule in _RULES:
        if evaluate_condition(rule.when, context):
            matches.append((rule.id, dict(rule.then)))
    return tuple(matches)


def evaluate_combat_modifiers(entity) -> dict[str, Any]:
    """Return the merged matching bundle without mutating entity state."""
    result: dict[str, Any] = {}
    for _, adjustments in matched_combat_modifiers(entity):
        result = _merge_adjustments(result, adjustments)
    return result
