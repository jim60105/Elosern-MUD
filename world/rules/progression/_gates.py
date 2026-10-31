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
    SkillKind,
    SkillPrerequisite,
    prerequisite_consumers,
)

from ._constants import PROFICIENCY_TIP_CAP, SKILL_PROFICIENCY_XP_PER_LEVEL
from world.skills.restrictions import skill_effect_allowed
from world.skills.eligibility import skill_identity_eligible


def skill_proficiency_level(
    entity: Any,
    skill_key: str,
    *,
    proficiency: Any = None,
) -> int:
    """Return the whole proficiency level derived from stored practice XP.

    ``proficiency`` may pre-supply the persisted ``db.skill_proficiency``
    mapping a decision already read, so a per-plan gate reuses it.
    """
    stored = entity.db.skill_proficiency or {} if proficiency is None else proficiency
    return int(float(stored.get(skill_key, 0.0)) // SKILL_PROFICIENCY_XP_PER_LEVEL)


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


def is_elemental_mastery(skill: SkillDef) -> bool:
    """Return whether ``skill`` belongs to the elemental-mastery family.

    The family is the taxonomy itself — a PASSIVE of
    ``SkillCategory.ELEMENTAL_MAGIC`` — not a key suffix, an effect marker or
    a declared element. Every shipped mastery is one (all eight carry the
    category), and synthetic fixtures build mastery rows from an elementless
    enhancement template, so a key- or element-based test would silently fail
    open for them. A future non-mastery PASSIVE cannot join the category
    without receiving the whole-tree gate, which is the intended contract.
    """
    return (
        skill.kind is SkillKind.PASSIVE
        and skill.category is SkillCategory.ELEMENTAL_MAGIC
    )


def mastery_prerequisites_met(
    entity: Any,
    skill: SkillDef,
    *,
    owned_keys: Any = None,
) -> bool:
    """Return whether ``skill``'s whole declared closure is lawfully held.

    The ONE closure query shared by the use gate and by acquisition (design
    D2). Pure and side-effect free: it never repairs ownership or practice XP
    and never substitutes a conferred grant for a direct one. The target must
    be the live registered elemental-mastery definition — the supplied object
    must BE that row, so a stale or hand-built copy can never borrow another
    registered key's closure — declare a nonempty prerequisite list, and pass
    identity/effect eligibility itself — ownership of the target is
    deliberately NOT required, because acquisition asks this before granting it.

    Every ancestor reached through the declared edges must be registered,
    identity/effect eligible, directly owned, and at or above the edge's
    declared proficiency level. A local visited set keeps a shared ancestor
    from being re-traversed, and an unknown key fails closed.
    """
    if not is_elemental_mastery(skill) or not skill.prerequisites:
        return False
    registered = SKILL_REGISTRY.get(skill.key)
    if registered is None or registered is not skill:
        return False
    if not skill_identity_eligible(entity, skill) or not skill_effect_allowed(
        entity, skill.key
    ):
        return False
    owned = entity.skills.owned_keys() if owned_keys is None else owned_keys
    visited: set[str] = set()
    stack = [registered]
    while stack:
        for edge in stack.pop().prerequisites:
            ancestor = SKILL_REGISTRY.get(edge.skill_key)
            if ancestor is None:
                return False
            if not skill_identity_eligible(
                entity, ancestor
            ) or not skill_effect_allowed(entity, ancestor.key):
                return False
            if edge.skill_key not in owned:
                return False
            if skill_proficiency_level(entity, edge.skill_key) < edge.min_proficiency:
                return False
            if edge.skill_key not in visited:
                visited.add(edge.skill_key)
                stack.append(ancestor)
    return True


def _missing_closure_edge(
    entity: Any, skill: SkillDef, owned: Any
) -> SkillPrerequisite | None:
    """First unmet ownership/XP edge of a mastery's closure, or ``None``.

    Declared-edge breadth-first order, so the reported edge is deterministic
    and a low INTERNAL ancestor (not only a direct mastery parent) can be
    named. Eligibility-only failures have no numeric edge to report and yield
    ``None``; the callers that render a reason own that distinction.
    """
    visited: set[str] = set()
    queue = [skill]
    while queue:
        for edge in queue.pop(0).prerequisites:
            if edge.skill_key not in owned:
                return edge
            if skill_proficiency_level(entity, edge.skill_key) < edge.min_proficiency:
                return edge
            if edge.skill_key in visited:
                continue
            visited.add(edge.skill_key)
            ancestor = SKILL_REGISTRY.get(edge.skill_key)
            if ancestor is not None:
                queue.append(ancestor)
    return None


def can_use_skill(
    entity: Any,
    skill: SkillDef,
    *,
    owned_keys: Any = None,
) -> bool:
    """Return whether the entity may USE one skill right now (the ONE gate).

    Pure, side-effect-free predicate (DC2): ownership of the skill, then every
    declared prerequisite edge — the prereq key must also be owned and its
    derived proficiency level must reach the threshold. School-agnostic: a
    weapon skill and a spell traverse this identical path, so 主宰-tier entry
    is simply every edge on the path into that node (AND semantics). MP
    affordability and every other check stay in the resolver; this answers
    lineage eligibility only.

    An elemental-mastery passive additionally requires its COMPLETE closure
    (``mastery_prerequisites_met``). Its declared edges name ordinary
    terminals, so the immediate-edge loop above cannot see an internal edge
    left unmet by explicit imported XP; the recursive query is what denies a
    bare key, a restricted ancestor and a low internal ancestor. Ordinary
    skills keep exactly their previous behaviour.
    """
    owned = entity.skills.owned_keys() if owned_keys is None else owned_keys
    if (
        skill.key not in owned
        or not skill_identity_eligible(entity, skill)
        or not skill_effect_allowed(entity, skill.key)
    ):
        return False
    for prereq in skill.prerequisites:
        if prereq.skill_key not in owned:
            return False
        if skill_proficiency_level(entity, prereq.skill_key) < prereq.min_proficiency:
            return False
    if is_elemental_mastery(skill) and not mastery_prerequisites_met(
        entity, skill, owned_keys=owned
    ):
        return False
    return True


def missing_prerequisite(
    entity: Any,
    skill: SkillDef,
    *,
    owned_keys: Any = None,
) -> SkillPrerequisite | None:
    """Return the first unmet prerequisite edge of ``skill``, or ``None``.

    Reports in declared edge order so rejection text is deterministic. The
    caller owns the ownership check for the skill itself; this only walks the
    prerequisite list (an already-usable skill yields ``None``).

    An elemental-mastery passive walks its whole declared closure instead, so
    a low internal ancestor can be named rather than only a direct parent;
    ``None`` therefore means "no numeric edge is unmet", which is not the same
    as "usable" (an ineligible or sealed ancestor also yields ``None``).
    """
    owned = entity.skills.owned_keys() if owned_keys is None else owned_keys
    if is_elemental_mastery(skill) and skill.prerequisites:
        return _missing_closure_edge(entity, skill, owned)
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

    A stored assignment refreshes the learner's dialogue availability from the
    committed state (authored-dialogue-refresh-physical), so a proficiency
    threshold crossing changes the projected choices from any origin (study,
    another session, a scheduled tick). The zero-effect and saturated paths
    return before any write and register nothing.
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
    from world.rules.dialogue_availability import (
        affected_dialogue_owners,
        queue_dialogue_refresh,
    )

    queue_dialogue_refresh(
        affected_dialogue_owners(entity), cause="practice_xp"
    )


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
