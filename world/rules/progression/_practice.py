"""Practice XP growth: elemental eligibility, owned growth, XP formula.

The shared growth-factor composite and its two element-keyed inputs live
here; both practice entry points (in the package ``__init__``) scale through
:func:`_practice_growth_factors`, so the formula has exactly one home.
"""

from math import isfinite
from typing import Any

from world.lore.elements import ELEMENT_REGISTRY
from world.skills.effects import GrowthRateEffect
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
)

from ._constants import SKILL_PRACTICE_XP_PER_USE
from ._gates import _race_learning_multiplier
from ._scaling import element_affinity_multiplier


def _is_elemental_magic(skill: SkillDef) -> bool:
    """Return whether the elemental factors may scale this skill's practice.

    A skill qualifies when the catalog says it is an ACTIVE elemental spell
    whose declared element names a registered :data:`ELEMENT_REGISTRY` entry.
    The catalog identity -- kind, category and element -- decides a spell's
    learning domain, never its parsed effects, so damage-free elemental
    healing, buff, control, cleansing and mixed-effect spells learn at the
    same affinity and owned scoped-growth rates as elemental damage (design
    D1). ``shadow_slash`` and the other element-tagged PHYSICAL martial rows
    stay at the neutral ``1.0``, as do PASSIVE enhancements, elementless
    actions and every other category: the accrual formula reads no school
    bias, but affinity is an elemental-magic concept by definition.
    """
    return (
        skill.kind is SkillKind.ACTIVE
        and skill.category is SkillCategory.ELEMENTAL_MAGIC
        and skill.element is not None
        and skill.element.key in ELEMENT_REGISTRY
    )


def _owned_growth_factor(entity: Any, skill: SkillDef) -> float:
    """Return the owned-skill growth factor for one practised skill.

    The product of the multipliers of every scoped ``growth_rate`` effect
    carried by a skill the actor OWNS whose declared scope equals the
    practised skill's element (design D3). ``1.0`` for a skill of any other
    element and for a skill declaring no element, so an unscoped acceleration
    is not expressible. The same ``_is_elemental_magic`` predicate the
    affinity factor uses decides what "the practised skill's element" means:
    a physical skill carrying an element takes ``1.0``, exactly as the
    affinity factor already treats it, so the two element-keyed factors never
    disagree about what an elemental skill is.

    Within a single owned skill, two ``growth_rate`` effects sharing the
    practised scope raise, mirroring ``_matching_multiplier()``'s duplicate
    guard; across different owned skills, matching multipliers multiply.
    Conferred grants are deliberately excluded: only the actor's OWNED skills
    confer the scoped factor (design D3), unlike ``effective_value()`` which
    folds ``conferred_grants()`` in for ``stat_multiply``.
    """
    if not _is_elemental_magic(skill):
        return 1.0
    scope = skill.element.key
    from world.skills.restrictions import skill_effect_allowed

    factor = 1.0
    for skill_key in dict.fromkeys(entity.skills.owned_keys()):
        if not skill_effect_allowed(entity, skill_key):
            continue
        owned = SKILL_REGISTRY.get(skill_key)
        if owned is None:
            continue
        multipliers = [
            effect.multiplier
            for effect in owned.parsed_effects
            if isinstance(effect, GrowthRateEffect) and effect.scope == scope
        ]
        if len(multipliers) > 1:
            raise ValueError(
                f"skill {skill_key!r} defines duplicate growth_rate effects "
                f"for scope {scope!r}"
            )
        for multiplier in multipliers:
            factor *= multiplier
    return float(factor)


def _practice_growth_factors(entity: Any, skill: SkillDef) -> float:
    """Return the shared growth-factor composite for one skill's practice.

    Race ``learning_multiplier`` x element-affinity multiplier (``1.0`` for
    any skill outside ACTIVE elemental magic) x ``growth_rate_multiplier(entity)``
    (the conferred-buff pull path) x the owned-skill growth factor
    (:func:`_owned_growth_factor`, the scoped ``growth_rate`` effects of the
    skills the entity owns). One formula, two entry points: the per-use grant
    and the booked-hourly settlement both scale their base amount by this
    composite, so learning, affinity, and the two growth sources can never
    diverge between them. Every factor is a finite, non-negative query; the
    composite is validated before any caller writes it.
    """
    from world.rules.buffs import growth_rate_multiplier

    element_factor = (
        element_affinity_multiplier(entity, skill.element.key)
        if _is_elemental_magic(skill)
        else 1.0
    )
    factors = (
        _race_learning_multiplier(entity)
        * element_factor
        * growth_rate_multiplier(entity)
        * _owned_growth_factor(entity, skill)
    )
    if not isfinite(factors) or factors < 0:
        raise ValueError(f"practice factors produced an invalid {factors!r}")
    return float(factors)


def practice_xp_amount(entity: Any, skill: SkillDef) -> float:
    """Return the closed-form practice XP one use of ``skill`` is worth.

    ``SKILL_PRACTICE_XP_PER_USE`` scaled by the shared
    :func:`_practice_growth_factors` composite. Reads no school and no magic
    stat.
    """
    amount = SKILL_PRACTICE_XP_PER_USE * _practice_growth_factors(entity, skill)
    if not isfinite(amount) or amount < 0:
        raise ValueError(f"practice XP formula produced an invalid {amount!r}")
    return float(amount)
