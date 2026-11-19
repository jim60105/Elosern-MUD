"""Runtime feature probes over the equipment-effect rulebook (P08 migration).

Behavior files that must bind a synthetic item to a shipped effect ROW
(immunity, attached buffs, gauge caps, prose layers, twin-capable weapon
rows) resolve the shipped row here by a semantic feature predicate with an
asserted UNIQUE match, never by the shipped key literal and never by registry
insertion order. The row is then rebound under the synthetic item's own key
inside the test's equipment-rule scope. Values stay live: callers read
magnitudes back through ``rule_for()`` so a data rework can only ever change
what a test observes, never break it.
"""

import importlib

from world.rules.equipment_effects import EQUIPMENT_EFFECT_RULES


def _rules() -> dict:
    """The loaded rulebook mapping.

    A plain dict mutated in place by ``patch.dict`` overrides, so the module
    binding IS the live view for every consumer.
    """
    return EQUIPMENT_EFFECT_RULES


def rule_for(item_key):
    """The loaded rule of one probed item key (live values, never pinned)."""
    return _rules()[item_key]


def _unique_feature(label: str, predicate) -> tuple:
    """(key, rule) for the exactly-one row matching ``predicate`` (fail-fast)."""
    matches = [pair for pair in _rules().items() if predicate(pair[1])]
    if len(matches) != 1:
        raise LookupError(
            f"equipment rulebook feature {label!r}: expected exactly one "
            f"matching row, found {len(matches)}"
        )
    return matches[0]


def unique_item_key(label: str, predicate):
    """The one shipped item key whose rule matches ``predicate`` (fail-fast)."""
    return _unique_feature(label, predicate)[0]


def unique_rule(label: str, predicate):
    """The one (item key, rule) pair matching ``predicate`` (fail-fast)."""
    return _unique_feature(label, predicate)


def first_matching_rule(label: str, predicate) -> tuple:
    """(key, rule) for the deterministically-first rulebook row matching
    ``predicate`` (sorted key order; fail-fast when nothing matches).

    Shape probes for the combat-wiring suite: the test computes every
    expected number from the returned rule's live values, so a shipped row
    being replaced by a same-shape row (different key or numbers) keeps the
    test honest instead of pinning the old data.
    """
    matches = sorted(
        (key, rule) for key, rule in _rules().items() if predicate(rule)
    )
    if not matches:
        raise LookupError(f"no equipment-effect row matches the {label} shape probe")
    return matches[0]


def gauge_cap_row_keys() -> tuple:
    """The two-plus rows carrying an ``hp`` gauge cap, ascending by cap.

    Multi-row case: asserts the caps are distinct so callers binding two rows
    provably exercise two different ceilings.
    """
    rows = [(key, rule) for key, rule in _rules().items() if rule.gauge_caps.get("hp")]
    if len(rows) < 2:
        raise LookupError("equipment rulebook: fewer than two hp gauge-cap rows")
    rows.sort(key=lambda pair: pair[1].gauge_caps["hp"])
    caps = [rule.gauge_caps["hp"] for _, rule in rows]
    if len(set(caps)) != len(caps):
        raise LookupError("equipment rulebook: hp gauge-cap rows share a cap value")
    return tuple(key for key, _ in rows)


def immune_to_key(buff_key: str):
    """The one row whose ``immune`` tuple contains ``buff_key`` (fail-fast)."""
    return unique_item_key(
        f"immune[{buff_key}]", lambda rule: buff_key in rule.immune
    )


def attached_buffs_rule():
    """The one row attaching buff instances. (item key, rule) pair."""
    return unique_rule("attached_buffs", lambda rule: bool(rule.attached_buffs))


def inventory_slot_vocabulary() -> dict:
    """The shipped slot enumeration as {slot-name: enum-member}, by name only.

    Lets slot-matrix tests iterate the CLOSED production vocabulary without
    importing the catalog-keyed enumeration module into a lint-clean file.
    """
    slots = getattr(importlib.import_module("world.lore.items"), "EquipmentSlot")
    return {member.name: member for member in slots}


def rulebook_rules(module_dotted: str) -> list:
    """The loaded rule list of one rulebook module (mutable list, live rows)."""
    return getattr(importlib.import_module(module_dotted), "_RULES")


def rule_with_id(module_dotted: str, rule_id: str):
    """The loaded rule carrying ``rule_id`` in one rulebook's rule list."""
    for rule in rulebook_rules(module_dotted):
        if rule.id == rule_id:
            return rule
    raise LookupError(f"{module_dotted}: no rule {rule_id!r}")


def display_label(code: str) -> str:
    """The shipped display label one condition code resolves through the
    status-display table (borrowed at runtime, never pinned as a literal)."""
    return getattr(
        importlib.import_module("world.rules.status_display"), "display_for"
    )(code).label


__all__ = [
    "first_matching_rule",
    "attached_buffs_rule",
    "gauge_cap_row_keys",
    "display_label",
    "immune_to_key",
    "inventory_slot_vocabulary",
    "rule_for",
    "rulebook_rules",
    "rule_with_id",
    "unique_item_key",
    "unique_rule",
]
