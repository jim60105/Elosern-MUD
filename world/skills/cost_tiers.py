"""MP cost tiers for spell skills (skill-system-redesign design doc §4.3, D9).

The five tiers are keyed by the world-lore rank titles; later spell-catalog
proposals pick a range from here instead of inventing ad hoc costs. The level
band is descriptive (the design doc's rank-title table and this cost table
share the 90 boundary); nothing in this module gates on it.

``spell_tier_for`` is the mechanical tier-label lookup: an elemental spell's
tier is derived from its MP cost band because ``SkillDef`` deliberately has no
tier field. The numeric cast gate that once consumed it retired with the
magic-XP engine (``magic-xp-engine-retirement``); the label is catalog data
only until the lineage gate reads the registry tree.
"""

from typing import NamedTuple

from .registry import SkillDef, SkillKind, TargetSpec


class CostTier(NamedTuple):
    """One MP cost tier: a level band plus single- and area-effect ranges."""

    min_level: int
    max_level: int | None
    single_mp: tuple[int, int]
    area_mp: tuple[int, int]


MP_COST_TIERS: dict[str, CostTier] = {
    "學徒": CostTier(0, 15, (10, 16), (14, 20)),
    "術師": CostTier(16, 30, (20, 28), (26, 34)),
    "大師": CostTier(31, 70, (35, 48), (45, 60)),
    "賢者": CostTier(71, 90, (65, 85), (80, 110)),
    "主宰": CostTier(90, None, (120, 150), (140, 180)),
}


# Effect prefixes whose magnitude is proportional to the cast's scale.
_FREEFORM_SCALABLE_PREFIXES = frozenset({"damage", "heal", "self_heal"})


def is_freeform_eligible(skill: SkillDef) -> bool:
    """Return whether one skill is shape-eligible for freeform scaling.

    ``True`` exactly when the skill is ACTIVE, carries an element, declares a
    positive integer ``mp`` cost, has a non-empty ``effects`` list, and every
    effect prefix is one of ``damage``, ``heal``, or ``self_heal``. Any other
    shape — PASSIVE skills, non-elemental skills, skills without an ``mp``
    cost, skills with an empty ``effects`` list, or skills carrying a buff,
    status, cleanse, movement, or conferral effect — returns ``False``. The
    predicate never reads entity state.
    """
    if skill.kind is not SkillKind.ACTIVE or skill.element is None:
        return False
    mp_cost = skill.cost.get("mp")
    if isinstance(mp_cost, bool) or not isinstance(mp_cost, int) or mp_cost <= 0:
        return False
    if not skill.effects:
        return False
    return all(
        effect_id.partition(":")[0] in _FREEFORM_SCALABLE_PREFIXES
        for effect_id in skill.effects
    )


def _band_contains(band: tuple[int, int], cost: int) -> bool:
    lower, upper = band
    return lower <= cost <= upper


def spell_tier_for(skill: SkillDef) -> str | None:
    """Return the magic-tier data label for one elemental spell skill.

    An elemental spell is an ACTIVE skill carrying both an element and an
    ``mp`` cost; everything else returns ``None`` (no tier label). The tier
    is the unique §4.3 band containing the skill's MP cost: the column
    matching the skill's target spec (``SELF`` counts as single/direct) is
    preferred, then the other column, because a few catalog costs
    intentionally sit in the opposite column of their tier. An elemental
    spell whose ``mp`` cost is absent, not a positive integer, or outside
    every band raises ``ValueError`` — a content-authoring error that must
    fail closed rather than silently leave a spell without a tier label.
    """
    if skill.kind is not SkillKind.ACTIVE or skill.element is None:
        return None
    mp_cost = skill.cost.get("mp")
    if mp_cost is None:
        return None
    if not isinstance(mp_cost, int) or mp_cost <= 0:
        raise ValueError(
            f"elemental spell {skill.key!r} must carry a positive integer "
            f"mp cost, got {mp_cost!r}"
        )
    preferred = (
        "area_mp" if skill.target_spec is TargetSpec.AREA else "single_mp"
    )
    fallback = "single_mp" if preferred == "area_mp" else "area_mp"
    for column in (preferred, fallback):
        for tier, tier_data in MP_COST_TIERS.items():
            if _band_contains(getattr(tier_data, column), mp_cost):
                return tier
    raise ValueError(
        f"elemental spell {skill.key!r} mp cost {mp_cost} falls outside "
        f"every tier band"
    )
