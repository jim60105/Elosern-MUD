"""Pure canonical target-fact readers (combat-target-traits D1).

This module is read-only and never mutates entity state or Evennia storage.
Facts are read strictly from persistent deterministic data (``combat_traits``,
``affinity_elements``, and live buff instances via ``entity_active_buffs``);
narrative names, race labels, and descriptions never imply a combat fact.
"""

from collections.abc import Iterable, Sequence
from typing import Any


def get_combat_traits(entity: Any) -> frozenset[str]:
    """Return the validated combat traits of an entity as a frozenset.

    Uses a no-create read over ``entity.attributes`` and ``entity.db`` so
    uninitialized entities do not materialize storage merely by being inspected
    (D1 / target-fact purity). Falls back to a plain ``combat_traits`` attribute
    only for in-memory test doubles without Evennia attribute handlers.
    Missing or empty returns an empty frozenset.
    Narrative names or labels are never consulted.
    """
    if entity is None:
        return frozenset()
    raw = None
    attributes = getattr(entity, "attributes", None)
    if attributes is not None and hasattr(attributes, "get"):
        raw = attributes.get("combat_traits")
    if raw is None:
        db = getattr(entity, "db", None)
        if db is not None:
            raw = getattr(db, "combat_traits", None)
    if raw is None:
        # Plain in-memory mock fallback; skip AttributeProperty descriptors on typeclasses
        raw = getattr(entity, "combat_traits", None)
        if hasattr(raw, "__get__"):
            raw = None
    if not raw:
        return frozenset()
    if isinstance(raw, (str, bytes)):
        return frozenset({str(raw)})
    if not isinstance(raw, Sequence) and not isinstance(raw, set) and not isinstance(raw, frozenset):
        return frozenset()
    return frozenset(str(entry) for entry in raw)


def get_affinity_elements(entity: Any) -> frozenset[str]:
    """Return the validated affinity element keys of an entity as a frozenset.

    Uses a no-create read over ``entity.db`` and ``entity.attributes``,
    matching ``world.rules.progression._affinity_elements``.
    Missing or empty returns an empty frozenset.
    """
    if entity is None:
        return frozenset()
    raw = None
    db = getattr(entity, "db", None)
    if db is not None:
        raw = getattr(db, "affinity_elements", None)
    if raw is None:
        attributes = getattr(entity, "attributes", None)
        if attributes is not None and hasattr(attributes, "get"):
            raw = attributes.get("affinity_elements")
    if raw is None:
        raw = getattr(entity, "affinity_elements", None)
        if hasattr(raw, "__get__"):
            raw = None
    if not raw:
        return frozenset()
    if isinstance(raw, (str, bytes)):
        return frozenset({str(raw)})
    if not isinstance(raw, Sequence) and not isinstance(raw, set) and not isinstance(raw, frozenset):
        return frozenset()
    return frozenset(str(entry) for entry in raw)


def get_target_facts(entity: Any) -> frozenset[str]:
    """Return the union of elemental affinities and combat traits as bare keys."""
    return get_affinity_elements(entity) | get_combat_traits(entity)


def matches_target_predicate(entity: Any, predicate: Iterable[str]) -> bool:
    """Return True if the target satisfies any fact declared in predicate.

    Empty predicate returns False. Narrative labels, descriptions, or entity
    names never imply a fact. Live buff entries (buff:<key>) match if the target
    currently holds a live, unexpired, non-paused instance of the definition key.
    """
    if not predicate:
        return False
    facts: frozenset[str] | None = None
    active_buffs: set[str] | None = None
    for entry in predicate:
        if entry.startswith("buff:"):
            if active_buffs is None:
                from world.rules.buffs import entity_active_buffs

                active_buffs = entity_active_buffs(entity)
            if entry[5:] in active_buffs:
                return True
        else:
            if facts is None:
                facts = get_target_facts(entity)
            if entry in facts:
                return True
    return False
