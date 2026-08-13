"""Pure combat-modifier query for design section 6.4."""

from pathlib import Path
import re
from typing import Any

from world.lore.sexual_vocab import AROUSAL_LEVELS, CLIMAX_PHASE_LEVELS
from world.rules.buffs import active_buff_keys_from_storage, entity_active_buffs
from world.rules.rulebook.schema import evaluate_condition, load_rules

_RULES = load_rules(Path(__file__).parent / "rulebook" / "combat_modifiers.yaml")

# Percentage adjustments may be fractional after a conferred grant scales a
# whole-number percentage ("+5%" at scale 0.5 becomes "+2.5%"), so both the
# merge and the scaling paths accept an optional fractional part.
_PERCENT_RE = re.compile(r"[+-]\d+(?:\.\d+)?%")


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
    never create a persistent attribute or write state. The entity itself is
    passed through for ``skill_owned`` conditions, which resolve against
    ``entity.skills.owned_keys()`` (a pure stored-data read).
    """
    context: dict[str, Any] = {"active_buffs": active_buff_keys_from_storage(entity)}
    for field, levels in (("arousal", AROUSAL_LEVELS), ("climax_phase", CLIMAX_PHASE_LEVELS)):
        value = _stored_sexual_level(entity, field)
        if isinstance(value, str) and value in levels:
            context[field] = _StoredLevel(levels.index(value), levels)
        elif isinstance(value, _StoredLevel):
            context[field] = value
    context["entity"] = entity
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
    context["entity"] = entity
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
            and _PERCENT_RE.fullmatch(value)
            and _PERCENT_RE.fullmatch(current)
        ):
            merged[key] = f"{float(current[:-1]) + float(value[:-1]):+g}%"
        else:
            merged[key] = value
    return merged


def _conferred_rule_scale(entity: Any, skill_key: str) -> float:
    """Return the summed fractional scale of grants referencing one skill.

    Only grants whose referenced skill carries a ``RuleTableEffect`` count:
    the rule-table consumer never folds in a grant that is not rule-table
    shaped. Unknown skill keys contribute nothing.
    """
    from world.skills.effects import RuleTableEffect
    from world.skills.registry import SKILL_REGISTRY

    total = 0.0
    for grant in entity.skills.conferred_grants():
        if grant.skill_key != skill_key:
            continue
        skill = SKILL_REGISTRY.get(grant.skill_key)
        if skill is None:
            continue
        if any(
            isinstance(effect, RuleTableEffect)
            for effect in skill.parsed_effects
        ):
            total += grant.scale
    return total


def _scale_adjustments(adjustments: dict[str, Any], scale: float) -> dict[str, Any]:
    """Scale numeric and percentage adjustments by one fractional grant."""
    scaled: dict[str, Any] = {}
    for key, value in adjustments.items():
        if isinstance(value, (int, float)):
            scaled[key] = value * scale
        elif isinstance(value, str) and _PERCENT_RE.fullmatch(value):
            scaled[key] = f"{float(value[:-1]) * scale:+g}%"
        else:
            scaled[key] = value
    return scaled


def matched_combat_modifiers(
    entity, context: dict[str, Any] | None = None
) -> tuple[tuple[str, dict[str, Any]], ...]:
    """Return each matched rule ID with its exact adjustment bundle.

    This read-only query exposes the deterministic per-rule matches so
    presentation can show each condition without re-evaluating thresholds or
    reproducing modifier math. ``context`` is the condition context; when
    omitted it is rebuilt from ``entity``. A caller-supplied context is
    treated as a partial context: the entity is injected so ``skill_owned``
    conditions always resolve against the real entity rather than silently
    never matching. A ``skill_owned`` rule that matches only through a
    conferred grant (the entity does not own the skill) returns the grant's
    scaled-down adjustment instead of the full bundle.
    """
    if context is None:
        context = _build_context(entity)
    else:
        context = dict(context)
        context.setdefault("entity", entity)
    matches: list[tuple[str, dict[str, Any]]] = []
    for rule in _RULES:
        if not evaluate_condition(rule.when, context):
            continue
        adjustments = dict(rule.then)
        skill_key = rule.when.get("skill_owned")
        if skill_key is not None and skill_key not in entity.skills.owned_keys():
            scale = _conferred_rule_scale(entity, skill_key)
            if scale <= 0:
                continue
            adjustments = _scale_adjustments(adjustments, scale)
        matches.append((rule.id, adjustments))
    return tuple(matches)


def evaluate_combat_modifiers(entity) -> dict[str, Any]:
    """Return the merged matching bundle without mutating entity state."""
    result: dict[str, Any] = {}
    for _, adjustments in matched_combat_modifiers(entity):
        result = _merge_adjustments(result, adjustments)
    return result
