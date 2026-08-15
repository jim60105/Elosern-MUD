"""Deterministic magic-level and skill-practice progression rules."""

from collections.abc import Sequence
from math import floor, isfinite
from pathlib import Path
from typing import Any, Iterable

import yaml

from world.lore.elements import ELEMENT_REGISTRY
from world.lore.races import RACE_REGISTRY
from world.rules.buffs import growth_rate_multiplier
from world.rules.clock import AdvanceSource
from world.skills.cost_tiers import spell_tier_for
from world.skills.registry import SKILL_REGISTRY, SkillKind


PROGRESSION_YAML = yaml.safe_load(
    (Path(__file__).parent / "rulebook" / "progression.yaml").read_text(
        encoding="utf-8"
    )
)
MAGIC_XP_PER_LEVEL = float(PROGRESSION_YAML["magic_xp_per_level"])
STUDY_BASE_XP_PER_HOUR = float(PROGRESSION_YAML["study_base_xp_per_hour"])
COMBAT_KILL_XP_TABLE: dict[str, float] = {
    key: float(value)
    for key, value in PROGRESSION_YAML["combat_kill_xp"].items()
}
SKILL_PROFICIENCY_XP_PER_LEVEL = float(
    PROGRESSION_YAML["skill_proficiency_xp_per_level"]
)
SKILL_PRACTICE_XP_PER_USE = float(PROGRESSION_YAML["skill_practice_xp_per_use"])
AFFINITY_ELEMENT_MULTIPLIER = float(
    PROGRESSION_YAML["affinity_element_multiplier"]
)
NON_AFFINITY_ELEMENT_MULTIPLIER = float(
    PROGRESSION_YAML["non_affinity_element_multiplier"]
)
MAGIC_GROWTH_MULTIPLIER_PREFIX = "growth_rate:magic:"


def _validate_nonnegative_multiplier(value: float, name: str) -> None:
    """Fail closed on a non-finite or negative balance constant (design D5)."""
    if not isfinite(value) or value < 0:
        raise ValueError(
            f"progression constant {name} must be finite and non-negative"
        )


_validate_nonnegative_multiplier(AFFINITY_ELEMENT_MULTIPLIER, "affinity_element_multiplier")
_validate_nonnegative_multiplier(
    NON_AFFINITY_ELEMENT_MULTIPLIER, "non_affinity_element_multiplier"
)

# Display rank bands from world lore (skill-system-redesign design doc §4.1).
# The lore table writes the top band as "90+"; scanning the bands in order
# resolves the overlap at exactly 90 toward 賢者, so a human at the magic cap
# (90) reads as 賢者 and never satisfies the 主宰 gate.
MAGIC_RANK_BANDS: tuple[tuple[str, int, int | None], ...] = (
    ("學徒", 0, 15),
    ("術師", 16, 30),
    ("大師", 31, 70),
    ("賢者", 71, 90),
    ("主宰", 90, None),
)

# Mechanical cast-gate thresholds, one per rank title. 主宰's threshold is 91
# (not 90): the spell-catalog gate scenarios pin magic level 90 as below
# 主宰, and combined with the human magic cap of 90 this makes "humans can
# rarely ever cast 主宰-tier spells" (world lore) a mechanical fact.
MAGIC_TIER_THRESHOLDS: dict[str, int] = {
    "學徒": 0,
    "術師": 16,
    "大師": 31,
    "賢者": 71,
    "主宰": 91,
}


def magic_rank_title(entity: Any) -> str:
    """Return the display-only rank title for an entity's numeric magic level.

    Pure function of ``entity.traits.magic_level.value`` alone; never consults
    owned skills or any other entity state.
    """
    level = float(entity.traits.magic_level.value)
    for title, lower, upper in MAGIC_RANK_BANDS:
        if level >= lower and (upper is None or level <= upper):
            return title
    raise ValueError(f"magic level {level:g} falls outside every rank band")


def _affinity_elements(entity: Any) -> list[str]:
    """Return the validated lowercase affinity-element keys or an empty list.

    Reads ``entity.db.affinity_elements`` when the Evennia attribute handler
    exists (real characters, monsters, and NPCs), and falls back to a plain
    ``affinity_elements`` attribute so pure in-memory test entities stay
    supported. Evennia returns ``_SaverList`` wrappers (not ``list``), so the
    check accepts any non-string sequence. An absent or empty collection reads
    as neutral.
    """
    db = getattr(entity, "db", None)
    value = None
    if db is not None:
        value = getattr(db, "affinity_elements", None)
    if value is None:
        value = getattr(entity, "affinity_elements", None)
    if not value:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError("affinity_elements must be a sequence of element keys")
    return [str(entry) for entry in value]


def element_affinity_multiplier(entity: Any, element: str) -> float:
    """Return the finite per-element effective-level multiplier (element-affinity D2).

    Pure read-only query over ``entity.db.affinity_elements``: exactly ``1.1``
    when ``element`` is a declared affinity, ``0.9`` when the entity declares
    affinities and ``element`` is not among them, and exactly ``1.0`` for an
    entity with no declared affinities (the current-behavior-preserving
    default). An unrecognized element key raises ``ValueError``. Never writes
    any entity attribute.
    """
    if element not in ELEMENT_REGISTRY:
        raise ValueError(f"unknown element {element!r}")
    affinities = _affinity_elements(entity)
    if not affinities:
        return 1.0
    if element in affinities:
        return AFFINITY_ELEMENT_MULTIPLIER
    return NON_AFFINITY_ELEMENT_MULTIPLIER


def _element_effective_magic_level(entity: Any, element: str) -> int:
    """Return ``floor(magic_level * element_affinity_multiplier)`` (design D1).

    The element-effective level is a transient gate-only value: it is never a
    stored trait, never replaces ``magic_level``, and never changes
    ``magic_level.max``. It exists only for the ``can_cast_spell_tier``
    comparison.
    """
    return floor(
        float(entity.traits.magic_level.value)
        * element_affinity_multiplier(entity, element)
    )


def can_cast_spell_tier(entity: Any, element: str, tier: str) -> bool:
    """Return whether an entity may cast one tier of one element's spells.

    The element key is validated against ``ELEMENT_REGISTRY`` first and an
    unrecognized element raises ``ValueError`` even when the entity owns a
    fabricated ``<element>_mastery`` (design D6, fail-closed). ``True`` when
    the entity directly owns that element's ``<element>_mastery`` skill
    (unconditionally), or when the element-effective magic level
    ``floor(magic_level × element_affinity_multiplier)`` meets the tier's
    threshold. Conferred grants never satisfy the mastery override (design doc
    D4/D6): only ``entity.skills.owned_keys()`` counts, never
    ``conferred_grants()``.
    """
    if element not in ELEMENT_REGISTRY:
        raise ValueError(f"unknown element {element!r}")
    if f"{element}_mastery" in entity.skills.owned_keys():
        return True
    threshold = MAGIC_TIER_THRESHOLDS.get(tier)
    if threshold is None:
        raise ValueError(f"unknown magic tier {tier!r}")
    return _element_effective_magic_level(entity, element) >= threshold


def can_cast_skill(entity: Any, skill: Any) -> bool:
    """Return whether the entity may cast one skill (the shared cast gate).

    The single authoritative cast-eligibility query consumed by the action
    resolver and every deterministic AI combat policy. A skill with no derived
    tier (``spell_tier_for`` returns ``None`` — e.g. ``basic_attack``) always
    passes; an elemental spell passes only when ``can_cast_spell_tier`` allows
    it for the skill's element and tier. Any ``ValueError`` raised by either
    underlying query (a malformed MP cost, an unrecognized element key, or an
    unknown tier) is converted to ``False``, so the gate fails closed and never
    propagates into policy or preview consumers.
    """
    try:
        tier = spell_tier_for(skill)
        if tier is None:
            return True
        return can_cast_spell_tier(entity, skill.element.key, tier)
    except ValueError:
        return False


def _race_learning_multiplier(entity: Any) -> float:
    race_key = getattr(entity, "race", None)
    race = RACE_REGISTRY.get(race_key) if race_key else None
    return float(race.learning_multiplier) if race is not None else 1.0


def _self_magic_growth_multiplier(entity: Any) -> float:
    """Return the product of owned passive magic-growth effects."""
    multiplier = 1.0
    for skill_key in entity.skills.owned_keys():
        skill = SKILL_REGISTRY.get(skill_key)
        if skill is None or skill.kind is not SkillKind.PASSIVE:
            continue
        for effect_id in skill.effects:
            if effect_id.startswith(MAGIC_GROWTH_MULTIPLIER_PREFIX):
                multiplier *= float(
                    effect_id.removeprefix(MAGIC_GROWTH_MULTIPLIER_PREFIX)
                )
    return multiplier


def effective_magic_growth_multiplier(entity: Any) -> float:
    """Combine race, owned passive, and conferred magic-growth multipliers."""
    multiplier = (
        _race_learning_multiplier(entity)
        * _self_magic_growth_multiplier(entity)
        * growth_rate_multiplier(entity)
    )
    if not isfinite(multiplier) or multiplier < 0:
        raise ValueError("magic growth multiplier must be finite and non-negative")
    return multiplier


def _stored_magic_xp(entity: Any) -> float:
    """Read a persisted XP accumulator only when it is valid progression state."""
    xp = float(entity.db.magic_xp or 0.0)
    if not isfinite(xp) or xp < 0:
        raise ValueError("magic XP must be finite and non-negative")
    return xp


def _apply_level_ups(entity: Any) -> None:
    """Convert accumulated XP into capped magic levels without per-level loops."""
    magic_level = entity.traits.magic_level
    current = float(magic_level.value)
    cap = float(magic_level.max)
    if current >= cap:
        entity.db.magic_xp = 0.0
        return
    xp = _stored_magic_xp(entity)
    levels_gained = int(xp // MAGIC_XP_PER_LEVEL)
    new_level = min(cap, current + levels_gained)
    entity.db.magic_xp = (
        0.0 if new_level >= cap else xp - levels_gained * MAGIC_XP_PER_LEVEL
    )
    magic_level.current = int(new_level)


def accrue_magic_study(
    entities: Iterable[Any],
    seconds: int,
    source: AdvanceSource,
) -> None:
    """Grant closed-form ambient study XP for deliberate time skips only."""
    if seconds < 0:
        raise ValueError("seconds must be non-negative")
    if source is not AdvanceSource.SKIP:
        return
    base_xp = seconds / 3600 * STUDY_BASE_XP_PER_HOUR
    for entity in entities:
        entity.db.magic_xp = _stored_magic_xp(entity) + (
            base_xp * effective_magic_growth_multiplier(entity)
        )
        _apply_level_ups(entity)


def grant_combat_kill_xp(entity: Any, monster_tier_key: str) -> None:
    """Grant one tier-scaled combat-kill XP award through the shared pool."""
    base_xp = COMBAT_KILL_XP_TABLE[monster_tier_key]
    entity.db.magic_xp = _stored_magic_xp(entity) + (
        base_xp * effective_magic_growth_multiplier(entity)
    )
    _apply_level_ups(entity)


def grant_skill_practice_xp(entity: Any, skill_key: str, uses: int = 1) -> None:
    """Record race-scaled practice XP for one skill, independent of magic growth."""
    if uses < 0:
        raise ValueError("uses must be non-negative")
    proficiency = dict(entity.db.skill_proficiency or {})
    proficiency[skill_key] = proficiency.get(skill_key, 0.0) + (
        uses * SKILL_PRACTICE_XP_PER_USE * _race_learning_multiplier(entity)
    )
    entity.db.skill_proficiency = proficiency


def skill_proficiency_level(entity: Any, skill_key: str) -> int:
    """Return the unbounded whole proficiency level derived from practice XP."""
    proficiency = entity.db.skill_proficiency or {}
    return int(float(proficiency.get(skill_key, 0.0)) // SKILL_PROFICIENCY_XP_PER_LEVEL)
