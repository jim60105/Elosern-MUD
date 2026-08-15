"""Sexual transitions from design section 6.4 and change 7's D-7 analysis.

This module implements the ``sexual-transition-rules`` change while delegating
condition matching to the shared rulebook schema.
"""

import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from world.rules.rulebook.schema import Rule, evaluate_condition, load_rules
from world.rules.sexual_state import PLEASURE_CONFIG, _apply_climax_phase_set


FIELD_KINDS = {
    "wetness": "ordered_level",
    "shame": "ordered_level",
    "exposure": "ordered_level",
    "climax_phase": "ordered_level_cyclic",
    "pleasure": "bounded_counter",
    "sensitivity": "ordered_level_dict",
    "climax_today": "counter",
    "virgin": "flag_one_way",
    "experience_types": "append_only_set",
    "sp": "vital_gauge",
}

_FIXED_DELTA = re.compile(r"^[+-]\d+$")
_RANGE_DELTA = re.compile(r"^([+-]\d+)\.\.([+-]\d+)$")
_RULE_PATH = Path(__file__).with_name("rulebook") / "sexual.yaml"
_RESERVED_CONTEXT_KEYS = {
    "event",
    "arousal",
    "wetness",
    "shame",
    "exposure",
    "climax_phase",
    "climax_today",
    "virgin",
    "experience_types",
    "_changed",
}


class RuleConvergenceError(RuntimeError):
    """Raised when sexual transition rules do not reach a fixed point."""


@dataclass(frozen=True, eq=False)
class _OrderedLevelSnapshot:
    """Immutable pass-start value preserving ordered-level comparisons."""

    value: int
    levels: tuple[str, ...]

    def _ordinal_of(self, other: Any) -> int:
        if isinstance(other, _OrderedLevelSnapshot):
            return other.value
        if isinstance(other, str):
            return self.levels.index(other)
        return int(other)

    def __eq__(self, other: object) -> bool:
        return self.value == self._ordinal_of(other)

    def __ge__(self, other: object) -> bool:
        return self.value >= self._ordinal_of(other)


def _snapshot(trait) -> _OrderedLevelSnapshot:
    return _OrderedLevelSnapshot(trait.value, tuple(trait.levels))


def _parse_delta(spec: str) -> int | tuple[int, int]:
    """Parse a signed fixed delta or an ascending signed delta range."""
    if not isinstance(spec, str):
        raise ValueError(f"invalid delta {spec!r}")
    if _FIXED_DELTA.fullmatch(spec):
        return int(spec)
    match = _RANGE_DELTA.fullmatch(spec)
    if match:
        raw_lower, raw_upper = match.groups()
        lower, upper = int(raw_lower), int(raw_upper)
        if raw_lower[0] == raw_upper[0] and lower <= upper:
            return lower, upper
    raise ValueError(f"invalid delta {spec!r}")


def _resolve_delta(spec: str, rng: Any) -> int:
    parsed = _parse_delta(spec)
    if isinstance(parsed, int):
        return parsed
    return rng.randint(*parsed)


def _direction(before: int, after: int) -> str | None:
    if after > before:
        return "up"
    if after < before:
        return "down"
    return None


def _validate_rule_effect(rule: Rule) -> None:
    """Fail during table loading when an effect has an unsupported shape."""
    then = rule.then
    field = then.get("field")
    if field not in FIELD_KINDS:
        raise ValueError(f"rule {rule.id!r} targets unknown field {field!r}")
    kind = FIELD_KINDS[field]
    if kind == "ordered_level":
        allowed = {"field", "delta"} if "delta" in then else {"field", "set"}
    elif kind == "vital_gauge":
        allowed = {"field", "delta"}
    elif kind in {"ordered_level_dict", "counter"}:
        allowed = {"field", "delta"}
    elif kind == "bounded_counter":
        allowed = {"field", "delta"} if "delta" in then else {"field", "set"}
    elif kind in {"ordered_level_cyclic", "flag_one_way"}:
        allowed = {"field", "set"}
        if kind == "ordered_level_cyclic":
            allowed |= set(then) & {"from"}
        if kind == "flag_one_way":
            allowed.add("irreversible")
    else:
        allowed = {"field", "add"}
    if set(then) != allowed:
        raise ValueError(f"rule {rule.id!r} has invalid effect keys")
    if "delta" in then:
        parsed = _parse_delta(then["delta"])
        values = (parsed,) if isinstance(parsed, int) else parsed
        if kind == "vital_gauge" and any(value >= 0 for value in values):
            raise ValueError(f"rule {rule.id!r} vital-gauge delta must be negative")
    if kind == "counter" and then["delta"] != "+1":
        raise ValueError(f"rule {rule.id!r} counter delta must be '+1'")
    if kind == "bounded_counter" and "set" in then:
        value = then["set"]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
            raise ValueError(
                f"rule {rule.id!r} bounded-counter set must be an int "
                f"in [0, 100], got {value!r}"
            )
    if kind == "flag_one_way" and then["set"] is not False:
        raise ValueError(f"rule {rule.id!r} may only clear its one-way flag")


def _load_rules() -> list[Rule]:
    rules = load_rules(_RULE_PATH)
    for rule in rules:
        _validate_rule_effect(rule)
    return rules


_RULES = _load_rules()


def _apply_then(
    entity,
    then: dict[str, Any],
    context: dict[str, Any],
    rng: Any,
) -> tuple[str | None, str | None]:
    """Apply one owner-defined effect and report an actual field change."""
    field = then["field"]
    kind = FIELD_KINDS[field]

    if kind == "ordered_level":
        trait = getattr(entity.sexual, field)
        before = trait.value
        if "delta" in then:
            trait.value += _resolve_delta(then["delta"], rng)
        else:
            trait.value = trait.levels.index(then["set"])
        direction = _direction(before, trait.value)
    elif kind == "bounded_counter":
        trait = entity.sexual.pleasure
        before_ordinal = PLEASURE_CONFIG.ordinal_for(trait.value)
        if "delta" in then:
            trait.base += _resolve_delta(then["delta"], rng)
        else:
            trait.base = then["set"]
        after_ordinal = PLEASURE_CONFIG.ordinal_for(trait.value)
        direction = _direction(before_ordinal, after_ordinal)
        field = "arousal"
    elif kind == "ordered_level_cyclic":
        if "from" in then and entity.sexual.climax_phase.level != then["from"]:
            return None, None
        direction = _apply_climax_phase_set(entity, then["set"])
    elif kind == "ordered_level_dict":
        part = context["part"]
        trait = entity.sexual.sensitivity[part]
        before = trait.value
        trait.value += _resolve_delta(then["delta"], rng)
        direction = _direction(before, trait.value)
    elif kind == "counter":
        before = entity.sexual.climax_today
        entity.sexual.record_climax()
        direction = _direction(before, entity.sexual.climax_today)
    elif kind == "flag_one_way":
        before = entity.sexual.virgin
        entity.sexual.virgin = then["set"]
        direction = "down" if before and not entity.sexual.virgin else None
    elif kind == "append_only_set":
        before = entity.sexual.experience_types
        entity.sexual.add_experience_type(then["add"])
        direction = "up" if entity.sexual.experience_types != before else None
    else:
        trait = getattr(entity.traits, field)
        before = trait.value
        trait.current += _resolve_delta(then["delta"], rng)
        direction = _direction(before, trait.value)

    if direction is None:
        return None, None
    return field, direction


def _build_context(
    entity,
    event: str | None,
    changed: dict[str, str],
    event_context: dict[str, Any],
) -> dict[str, Any]:
    """Build shared-condition context from live deterministic state."""
    return {
        "event": event,
        "arousal": _snapshot(entity.sexual.arousal),
        "wetness": _snapshot(entity.sexual.wetness),
        "shame": _snapshot(entity.sexual.shame),
        "exposure": _snapshot(entity.sexual.exposure),
        "climax_phase": _snapshot(entity.sexual.climax_phase),
        "climax_today": entity.sexual.climax_today,
        "virgin": entity.sexual.virgin,
        "experience_types": entity.sexual.experience_types,
        "_changed": changed,
        **event_context,
    }


def apply_event(
    entity,
    event: str,
    *,
    rng: Any = None,
    max_passes: int = 50,
    **event_context: Any,
) -> dict[str, str]:
    """Apply the event-driven rule table until it reaches a fixed point."""
    if max_passes <= 0:
        raise ValueError("max_passes must be positive")
    collisions = _RESERVED_CONTEXT_KEYS & set(event_context)
    if collisions:
        names = ", ".join(sorted(collisions))
        raise ValueError(f"event context overrides reserved keys: {names}")
    rng = rng or random
    changed_this_pass: dict[str, str] = {}
    all_changes: dict[str, str] = {}
    current_event: str | None = event
    for _ in range(max_passes):
        context = _build_context(
            entity, current_event, changed_this_pass, event_context
        )
        changed_this_pass = {}
        for rule in _RULES:
            if evaluate_condition(rule.when, context):
                field, direction = _apply_then(
                    entity, rule.then, context, rng
                )
                if field is not None and direction is not None:
                    changed_this_pass[field] = direction
                    all_changes[field] = direction
        if not changed_this_pass:
            return all_changes
        current_event = None
    raise RuleConvergenceError(
        f"sexual transition rules did not converge after {max_passes} passes"
    )
