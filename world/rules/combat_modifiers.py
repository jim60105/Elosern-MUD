"""Pure combat-modifier query for design section 6.4.

Merges the rule-table matches with the worn-equipment bundle from
``world.rules.equipment_effects.equipment_adjustments`` (P2) in BOTH
evaluation paths, so to-hit, damage, estimation, preview, cost, and resist
consumers share one effective bundle. The merge appends AFTER rule-table
matching so ``matched_combat_modifiers`` keeps its per-rule breakdown free
of equipment contributions.
"""

import math
from pathlib import Path
import re
from typing import Any

from world.lore.sexual_vocab import AROUSAL_LEVELS, CLIMAX_PHASE_LEVELS, EXPOSURE_LEVELS
from world.rules.buffs import active_buff_keys_from_storage, entity_active_buffs
from world.rules.equipment_effects import equipment_adjustments, effective_exposure
from world.rules.rulebook.schema import evaluate_condition, load_rules
from world.rules.sexual_state import PLEASURE_CONFIG
from world.rules.stored_sexual_reads import StoredLevel, stored_sexual_level
from world.skills.equipment import dual_wielding_from_storage

_RULES = load_rules(Path(__file__).parent / "rulebook" / "combat_modifiers.yaml")

# Percentage adjustments may be fractional after a conferred grant scales a
# whole-number percentage ("+5%" at scale 0.5 becomes "+2.5%"), so both the
# merge and the scaling paths accept an optional fractional part.
_PERCENT_RE = re.compile(r"[+-]\d+(?:\.\d+)?%")


_StoredLevel = StoredLevel


def _stored_sexual_level(entity: Any, field: str) -> Any:
    """Read one stored sexual level without materializing the handler.

    Arousal is the derived level — resolved from the stored pleasure counter
    through ``PLEASURE_CONFIG`` here, in the rules layer — while every
    genuinely stored ordered level is read through the neutral shared reader
    (``world.rules.stored_sexual_reads``), which both this module and the
    effective-exposure overlay in ``equipment_effects`` consume.
    """
    from collections.abc import Mapping

    if field == "arousal":
        traits = entity.attributes.get(
            "sexual_traits", default=None, category="traits"
        )
        if isinstance(traits, Mapping) and "pleasure" in traits:
            raw = traits["pleasure"]
            base = raw.get("base") if isinstance(raw, Mapping) else None
            if isinstance(base, int) and not isinstance(base, bool):
                # Defensive: CounterTrait.base's own setter clamps writes into
                # [0, 100], so an out-of-range stored value implies corrupted
                # storage; clamp it so the ordinal lookup still resolves.
                base = min(100, max(0, base))
                return _StoredLevel(
                    PLEASURE_CONFIG.ordinal_for(base), AROUSAL_LEVELS
                )
            return None
    return stored_sexual_level(entity, field)


def build_no_create_condition_context(entity: Any) -> dict[str, Any]:
    """Build the combat-modifier condition context from stored state only.

    Reads the persisted buff cache and stored sexual traits or baseline without
    materializing ``entity.buffs`` or ``entity.sexual``, and the dual-wield
    equipment fact without materializing ``entity.equipment``. Returns a context
    accepted by :func:`matched_combat_modifiers` so preview and revalidation
    never create a persistent attribute or write state. The entity itself is
    passed through for ``skill_owned`` conditions, which resolve against
    ``entity.skills.owned_keys()`` (a pure stored-data read).

    The exposure slot carries the EFFECTIVE level (stored ordinal plus the
    summed equipment ``exposure_bias``, clamped) from the pure
    :func:`effective_exposure` overlay, in the same immutable
    :class:`StoredLevel` view the other fields use — reading it never
    materializes a handler or writes state, so the no-create contract holds.
    """
    context: dict[str, Any] = {"active_buffs": active_buff_keys_from_storage(entity)}
    for field, levels in (
        ("arousal", AROUSAL_LEVELS),
        ("climax_phase", CLIMAX_PHASE_LEVELS),
    ):
        value = _stored_sexual_level(entity, field)
        if isinstance(value, str) and value in levels:
            context[field] = _StoredLevel(levels.index(value), levels)
        elif isinstance(value, _StoredLevel):
            context[field] = value
    exposure = effective_exposure(entity)
    if isinstance(exposure, str) and exposure in EXPOSURE_LEVELS:
        context["exposure"] = _StoredLevel(EXPOSURE_LEVELS.index(exposure), EXPOSURE_LEVELS)
    elif isinstance(exposure, StoredLevel):
        context["exposure"] = exposure
    context["entity"] = entity
    context["dual_wielding"] = dual_wielding_from_storage(entity)
    return context


def evaluate_combat_modifiers_no_create(entity: Any) -> dict[str, Any]:
    """Return the merged matching bundle from stored state without handlers.

    The equipment fold reads only ``entity.db.equipment`` through the
    accessor's fail-closed normalization, so the no-create contract (no
    handler materialization, no writes) holds for the equipment contribution
    too.
    """
    result: dict[str, Any] = {}
    for _, adjustments in matched_combat_modifiers(
        entity, context=build_no_create_condition_context(entity)
    ):
        result = _merge_adjustments(result, adjustments)
    return _merge_adjustments(result, equipment_adjustments(entity))


def _build_context(entity) -> dict[str, Any]:
    context: dict[str, Any] = {"active_buffs": entity_active_buffs(entity)}
    sexual = getattr(entity, "sexual", None)
    if sexual is not None:
        context["arousal"] = sexual.arousal
        context["climax_phase"] = sexual.climax_phase
    # The exposure slot is the effective overlay (stored + worn bias, clamped)
    # as the shared immutable level view — never the raw trait — so the
    # handler path and the no-create path fill the identical view type
    # (add-equipment-sexual-effects D1).
    exposure = effective_exposure(entity)
    if isinstance(exposure, str) and exposure in EXPOSURE_LEVELS:
        context["exposure"] = _StoredLevel(EXPOSURE_LEVELS.index(exposure), EXPOSURE_LEVELS)
    elif isinstance(exposure, StoredLevel):
        context["exposure"] = exposure
    context["entity"] = entity
    context["dual_wielding"] = dual_wielding_from_storage(entity)
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


def apply_cost_modifier(amount: int, percentage: str | None) -> int:
    """Apply one signed percentage cost adjustment with floor rounding.

    ``None`` returns ``amount`` unchanged. Otherwise the signed, possibly
    fractional percentage (the ``X_cost`` bundle vocabulary) is parsed with
    ``_PERCENT_RE`` and the adjusted cost is
    ``max(0, floor(amount * (1 + pct / 100)))``: reductions can make a cast
    free at zero but never negative. A missing, non-string, or malformed
    percentage raises ``ValueError`` (fail loud, matching
    :func:`adjusted_agility`).
    """
    if percentage is None:
        return amount
    if not isinstance(percentage, str) or _PERCENT_RE.fullmatch(percentage) is None:
        raise ValueError(f"invalid percentage modifier {percentage!r}")
    return max(0, math.floor(amount * (1 + float(percentage[:-1]) / 100)))


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
    never matching, and the stored dual-wield equipment fact is injected the
    same way. A ``skill_owned`` rule that matches only through a conferred
    grant (the entity does not own the skill) returns the grant's scaled-down
    adjustment instead of the full bundle.
    """
    if context is None:
        context = _build_context(entity)
    else:
        context = dict(context)
        context.setdefault("entity", entity)
        context.setdefault("dual_wielding", dual_wielding_from_storage(entity))
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
    return _merge_adjustments(result, equipment_adjustments(entity))


def adjusted_agility(entity: Any, modifiers: dict[str, Any] | None = None) -> float:
    """Return the effective agility with bundle adjustments, floored at zero.

    Both agility components of the merged bundle apply, in order: the
    percentage string (rule-table rows and percent-shaped gear) scales the
    effective skill value, then the flat ``agility_flat`` addend (flat gear
    such as ``ashen_scimitar``) is added. The result is clamped at 0 so heavy
    gear can never invert an agility-driven inequality (to-hit, overwhelm
    estimation, resist scoring, flee contest). ``combat.roll_initiative``
    deliberately keeps its raw-agility exception and does not call this.
    ``modifiers`` may be a caller-evaluated bundle to avoid a re-read.
    """
    if modifiers is None:
        modifiers = evaluate_combat_modifiers(entity)
    agility = float(entity.skills.effective_value("agility"))
    percent = modifiers.get("agility")
    if percent is not None:
        if not isinstance(percent, str) or _PERCENT_RE.fullmatch(percent) is None:
            raise ValueError(f"invalid percentage modifier {percent!r}")
        agility *= 1 + float(percent[:-1]) / 100
    agility += float(modifiers.get("agility_flat", 0))
    return max(0.0, agility)
