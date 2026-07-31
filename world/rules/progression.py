"""Deterministic magic-level and skill-practice progression rules."""

from pathlib import Path
from math import isfinite
from typing import Any, Iterable

import yaml

from world.lore.races import RACE_REGISTRY
from world.rules.buffs import growth_rate_multiplier
from world.rules.clock import AdvanceSource
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
MAGIC_GROWTH_MULTIPLIER_PREFIX = "growth_rate:magic:"


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
