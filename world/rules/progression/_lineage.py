"""Lineage auto-seed: fixed-point proficiency, ownership closure, records.

The import/scene-build auto-seed family (DC6): the proficiency fixed point,
the prerequisite-ownership closure, and the two entity/record writers built
from them.
"""

from collections.abc import Sequence
from typing import Any

from world.skills.registry import SKILL_REGISTRY, SkillKind

from ._constants import SKILL_PROFICIENCY_XP_PER_LEVEL


def seed_lineage_proficiency(
    owned_keys: Sequence[str], explicit: dict[str, float] | None = None
) -> dict[str, float]:
    """Return the proficiency map satisfying every edge of the owned skills.

    The import/scene-build auto-seed (DC6): for each owned skill, every
    prerequisite edge whose derived level falls short is seeded to EXACTLY
    ``min_proficiency * SKILL_PROFICIENCY_XP_PER_LEVEL`` — the minimal value
    meeting the threshold, never above. An explicit entry always wins, even
    when it leaves an edge unmet (the record author said what they meant).
    Resolution runs to a fixed point in registry-key order, so a chain of
    owned skills seeds every unsatisfied edge in one pass and the result is
    order-independent and deterministic. Ownership is never invented: an
    unowned prerequisite stays unowned (the use gate still denies it); this
    only writes XP for keys the entity could already have practised.
    """
    explicit_entries = {
        key: float(value)
        for key, value in (explicit or {}).items()
        if key in SKILL_REGISTRY
    }
    stored = dict(explicit_entries)
    explicit_keys = set(explicit_entries)
    owned = set(owned_keys)
    for _ in range(len(owned) + 1):
        changed = False
        for skill_key in sorted(owned):
            skill = SKILL_REGISTRY.get(skill_key)
            if skill is None:
                continue
            for prereq in skill.prerequisites:
                required = prereq.min_proficiency * SKILL_PROFICIENCY_XP_PER_LEVEL
                current = float(stored.get(prereq.skill_key, 0.0))
                if current >= required:
                    continue
                if prereq.skill_key in explicit_keys:
                    # Explicit and below the edge: the record wins; no override.
                    continue
                # A previously seeded value may be RAISED to a tighter edge
                # (max over edges), but only to that edge's exact value.
                stored[prereq.skill_key] = max(current, required)
                changed = True
        if not changed:
            break
    return stored


def lineage_ownership_closure(
    declared_keys: Sequence[str],
) -> tuple[list[str], list[str]]:
    """Return ``(active_additions, passive_additions)`` closing the lineage.

    A record or NPC that owns a deep skill but not its prerequisite chain is
    unusable under the single gate (the gate requires prerequisite
    OWNERSHIP), so import auto-seed also extends ownership transitively:
    every prerequisite of every owned skill (walking its own prerequisites)
    joins the entity's skill lists. Returned in sorted registry-key order for
    deterministic storage; only keys absent from ``declared_keys`` are
    returned, split by each skill's declared kind.
    """
    declared = set(declared_keys)
    frontier = list(declared)
    seen = set(declared)
    additions: set[str] = set()
    while frontier:
        skill_key = frontier.pop()
        skill = SKILL_REGISTRY.get(skill_key)
        if skill is None:
            continue
        for prereq in skill.prerequisites:
            if prereq.skill_key in seen:
                continue
            seen.add(prereq.skill_key)
            additions.add(prereq.skill_key)
            frontier.append(prereq.skill_key)
    active = sorted(
        key
        for key in additions
        if SKILL_REGISTRY[key].kind is SkillKind.ACTIVE
    )
    passive = sorted(key for key in additions if key not in set(active))
    return active, passive


def apply_lineage_auto_seed(entity: Any) -> None:
    """Seed one freshly-built entity's lineage (ownership + exact XP).

    The ONE auto-seed writer shared by the import loader and the scene
    builder: extends ``db.skills`` with the prerequisite-ownership closure,
    then stores the fixed-point seeded proficiency map (explicit stored
    entries win). Called inside the caller's all-or-nothing transaction, so
    a rejected import leaves nothing behind, seed included.
    """
    raw = entity.db.skills or {}
    active = list(raw.get("active", []))
    passive = list(raw.get("passive", []))
    add_active, add_passive = lineage_ownership_closure([*active, *passive])
    if add_active or add_passive:
        entity.db.skills = {
            "active": [*active, *add_active],
            "passive": [*passive, *add_passive],
        }
    entity.db.skill_proficiency = seed_lineage_proficiency(
        [*active, *add_active, *passive, *add_passive],
        entity.db.skill_proficiency,
    )


def normalize_lineage_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return one import record with its lineage auto-seed applied.

    The shared normalization the validator and the loader BOTH apply before
    any range validation: a copy whose ``skills``/``passives`` close over the
    prerequisite chain and whose ``skill_proficiency`` carries the exact
    seeded values (explicit entries win, merged records are order-independent
    and idempotent). Validating the NORMALIZED record is what makes a deep
    import provably usable while a malformed sibling field still rejects the
    whole record. Unknown skill keys pass through untouched so the existing
    semantic check keeps naming them.
    """
    normalized = dict(record)
    active = list(record.get("skills") or [])
    passive = list(record.get("passives") or [])
    add_active, add_passive = lineage_ownership_closure([*active, *passive])
    merged = seed_lineage_proficiency(
        [*active, *add_active, *passive, *add_passive],
        record.get("skill_proficiency") or {},
    )
    normalized["skills"] = [*active, *add_active]
    normalized["passives"] = [*passive, *add_passive]
    if merged:
        normalized["skill_proficiency"] = merged
    return normalized
