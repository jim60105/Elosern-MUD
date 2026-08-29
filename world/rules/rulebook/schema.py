"""Shared declarative rule primitives for every rulebook table.

The future ``sexual.yaml`` table is expected to import ``Condition``,
``evaluate_condition``, and ``load_rules`` rather than reimplement matching.
Effects remain opaque to this module and are interpreted by each table owner.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

Condition = dict[str, Any]


class MissingRuleIdError(ValueError):
    """Raised when a declarative rule has no usable ID."""


class DuplicateRuleIdError(ValueError):
    """Raised when a declarative rule ID occurs more than once."""


@dataclass(frozen=True)
class Rule:
    """One identified rule with an owner-defined effect."""

    id: str
    when: Condition
    then: dict[str, Any]


def load_rules(path: Path) -> list[Rule]:
    """Load a YAML list of uniquely identified rules."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path}: expected a YAML list")
    rules: list[Rule] = []
    seen: set[str] = set()
    for position, entry in enumerate(raw, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"{path}: entry {position} must be a mapping")
        rule_id = entry.get("id")
        if not isinstance(rule_id, str) or not rule_id.strip():
            raise MissingRuleIdError(f"{path}: entry {position} is missing id")
        if rule_id in seen:
            raise DuplicateRuleIdError(f"{path}: duplicate rule id {rule_id!r}")
        when, then = entry.get("when"), entry.get("then")
        if not isinstance(when, dict) or not isinstance(then, dict):
            raise ValueError(f"{path}: rule {rule_id!r} requires mapping when/then")
        seen.add(rule_id)
        rules.append(Rule(rule_id, dict(when), dict(then)))
    return rules


def evaluate_condition(when: Condition, context: Mapping[str, Any]) -> bool:
    """Evaluate all recognized conditions in *when* with implicit AND."""
    recognized = {
        "event", "field", "equals", "gte", "field_changed", "direction",
        "buff_active", "skill_owned", "dual_wielding", "equipment_worn",
    }
    unknown = set(when) - recognized
    if unknown:
        raise ValueError(f"unrecognized condition key: {sorted(unknown)[0]}")

    checks: list[bool] = []
    if "event" in when:
        checks.append(context.get("event") == when["event"])
    if "field" in when:
        field = when["field"]
        if "equals" not in when and "gte" not in when:
            raise ValueError("field condition requires equals or gte")
        if field not in context:
            checks.append(False)
        else:
            if "equals" in when:
                checks.append(context[field] == when["equals"])
            if "gte" in when:
                checks.append(context[field] >= when["gte"])
    elif "equals" in when or "gte" in when:
        raise ValueError("equals/gte requires field")
    if "field_changed" in when:
        if "direction" not in when:
            raise ValueError("field_changed requires direction")
        checks.append(
            context.get("_changed", {}).get(when["field_changed"]) == when["direction"]
        )
    elif "direction" in when:
        raise ValueError("direction requires field_changed")
    if "buff_active" in when:
        checks.append(when["buff_active"] in context.get("active_buffs", set()))
    if "skill_owned" in when:
        entity = context.get("entity")
        granted_keys = (
            {grant.skill_key for grant in entity.skills.conferred_grants()}
            if entity is not None
            else set()
        )
        checks.append(
            entity is not None
            and (
                when["skill_owned"] in entity.skills.owned_keys()
                or when["skill_owned"] in granted_keys
            )
        )
    if "dual_wielding" in when:
        if not isinstance(when["dual_wielding"], bool):
            raise ValueError("dual_wielding condition requires a boolean value")
        checks.append(context.get("dual_wielding") == when["dual_wielding"])
    if "equipment_worn" in when:
        # Generic membership mechanism only: referential validation (the
        # value must name a slot-bearing ITEM_REGISTRY member) is table-
        # specific and runs at each table owner's load site. A non-string
        # value is malformed data and must never silently mis-match. A
        # missing or non-collection context fact fails the condition closed
        # — a rule whose context lacks the worn-item fact never matches.
        item_key = when["equipment_worn"]
        if not isinstance(item_key, str):
            raise ValueError("equipment_worn condition requires a string item key")
        worn = context.get("worn_item_keys")
        if not isinstance(worn, (set, frozenset)):
            worn = frozenset()
        checks.append(item_key in worn)
    return bool(checks) and all(checks)