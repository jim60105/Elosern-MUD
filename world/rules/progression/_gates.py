"""The race multiplier, the ONE use gate, the accrual writer, and unlocks.

The pure gate helpers whose freeform consumers live in ``_scaling`` stay
there; this slice carries the ownership predicate, the single
``db.skill_proficiency`` writer, and the unlock-announcement helpers.
"""

from math import isfinite
from typing import Any

from world.lore.races import RACE_REGISTRY
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillPrerequisite,
    prerequisite_consumers,
)

from ._constants import PROFICIENCY_TIP_CAP, SKILL_PROFICIENCY_XP_PER_LEVEL


def skill_proficiency_level(entity: Any, skill_key: str) -> int:
    """Return the whole proficiency level derived from stored practice XP."""
    proficiency = entity.db.skill_proficiency or {}
    return int(float(proficiency.get(skill_key, 0.0)) // SKILL_PROFICIENCY_XP_PER_LEVEL)


def proficiency_cap(skill_key: str) -> int:
    """Return the derived tip cap for one skill (D6, rule 1).

    ``cap(S)`` is the maximum ``min_proficiency`` over every edge consuming
    ``S`` — read from the registry's load-time reverse-edge map, so branching
    and merging topologies need no special case — or ``PROFICIENCY_TIP_CAP``
    when nobody consumes it. A ceiling is therefore never below any single
    consuming edge, so a saturated prerequisite never blocks its child.
    """
    consumers = prerequisite_consumers(skill_key)
    if not consumers:
        return PROFICIENCY_TIP_CAP
    return max(min_proficiency for _, min_proficiency in consumers)


def _race_learning_multiplier(entity: Any) -> float:
    race_key = getattr(entity, "race", None)
    race = RACE_REGISTRY.get(race_key) if race_key else None
    return float(race.learning_multiplier) if race is not None else 1.0


def can_use_skill(entity: Any, skill: SkillDef) -> bool:
    """Return whether the entity may USE one skill right now (the ONE gate).

    Pure, side-effect-free predicate (DC2): ownership of the skill, then every
    declared prerequisite edge — the prereq key must also be owned and its
    derived proficiency level must reach the threshold. School-agnostic: a
    weapon skill and a spell traverse this identical path, so 主宰-tier entry
    is simply every edge on the path into that node (AND semantics). MP
    affordability and every other check stay in the resolver; this answers
    lineage eligibility only.
    """
    owned = entity.skills.owned_keys()
    if skill.key not in owned:
        return False
    for prereq in skill.prerequisites:
        if prereq.skill_key not in owned:
            return False
        if skill_proficiency_level(entity, prereq.skill_key) < prereq.min_proficiency:
            return False
    return True


def missing_prerequisite(entity: Any, skill: SkillDef) -> SkillPrerequisite | None:
    """Return the first unmet prerequisite edge of ``skill``, or ``None``.

    Reports in declared edge order so rejection text is deterministic. The
    caller owns the ownership check for the skill itself; this only walks the
    prerequisite list (an already-usable skill yields ``None``).
    """
    owned = entity.skills.owned_keys()
    for prereq in skill.prerequisites:
        if prereq.skill_key not in owned:
            return prereq
        if skill_proficiency_level(entity, prereq.skill_key) < prereq.min_proficiency:
            return prereq
    return None


def award_practice_xp(entity: Any, skill_key: str, xp: float) -> None:
    """THE accrual writer for ``db.skill_proficiency``; saturating at the cap.

    Every practice entry point (the per-use grant and the booked-practice
    settlement) routes through this one primitive, so the two can never
    diverge at a cap boundary: once
    ``skill_proficiency_level(entity, skill_key)`` reaches
    :func:`proficiency_cap`, further XP is dropped and the stored value never
    exceeds ``cap * SKILL_PROFICIENCY_XP_PER_LEVEL``. Fails closed on a
    non-finite or negative amount before any write.
    """
    if isinstance(xp, bool) or not isinstance(xp, (int, float)) or not isfinite(xp):
        raise ValueError(f"practice XP must be a finite number, got {xp!r}")
    if xp < 0:
        raise ValueError(f"practice XP must be non-negative, got {xp!r}")
    if xp == 0:
        return
    cap = proficiency_cap(skill_key)
    stored = dict(entity.db.skill_proficiency or {})
    current = float(stored.get(skill_key, 0.0))
    if current // SKILL_PROFICIENCY_XP_PER_LEVEL >= cap:
        return
    stored[skill_key] = min(
        current + float(xp), cap * SKILL_PROFICIENCY_XP_PER_LEVEL
    )
    entity.db.skill_proficiency = stored


def unlock_candidates_for(skill_key: str) -> tuple[SkillDef, ...]:
    """Registry definitions of every skill whose edge consumes ``skill_key``.

    The reverse-edge consumers are exactly the skills whose ``can_use_skill``
    verdict a grant to ``skill_key`` could flip; derivation order follows the
    cached consumer tuple, which is deterministic.
    """
    return tuple(
        SKILL_REGISTRY[key]
        for key, _ in prerequisite_consumers(skill_key)
        if key in SKILL_REGISTRY
    )


def unlock_line(skill: SkillDef) -> str:
    """The one Traditional-Chinese line announcing one newly usable skill."""
    prefix = "新法術可用" if skill.category is SkillCategory.ELEMENTAL_MAGIC else "新技能可用"
    return f"{prefix}：{skill.label}"
