"""Skill handling from design section 5.2 and ``skills-equipment``."""

import math
from dataclasses import dataclass
from typing import Any

from .registry import SKILL_REGISTRY


# Change 10c/16 grant universal actions that must not depend on imported skill data.
INNATE_SKILL_KEYS: frozenset[str] = frozenset({"flee", "basic_attack"})
# Deterministic append order for the innate set (frozenset iteration order is
# not guaranteed, and combat/report consumers rely on stable ordering).
INNATE_SKILL_ORDER: tuple[str, ...] = ("flee", "basic_attack")
if set(INNATE_SKILL_ORDER) != set(INNATE_SKILL_KEYS):
    raise RuntimeError("INNATE_SKILL_ORDER must name exactly the innate keys")


@dataclass(frozen=True)
class ConferredSkillGrant:
    """A fractional grant of one source entity's multiplier skill."""

    source_key: str
    skill_key: str
    trait_keys: tuple[str, ...]
    scale: float


def _parse_stat_multiply(effect_id: str) -> tuple[str, float] | None:
    """Parse this package's one effect convention; leave other IDs opaque."""
    parts = effect_id.split(":")
    if len(parts) != 3 or parts[0] != "stat_multiply" or not parts[1]:
        return None
    try:
        multiplier = float(parts[2])
    except ValueError:
        return None
    if not math.isfinite(multiplier):
        return None
    return parts[1], multiplier


class SkillHandler:
    """Read imported skill ownership and compute transient effective values."""

    def __init__(self, entity: Any):
        self.entity = entity

    @property
    def _raw(self) -> dict[str, list[str]]:
        raw = self.entity.db.skills
        return raw or {"active": [], "passive": []}

    def owned_keys(self) -> list[str]:
        """Return active and passive owned skill keys in stored order."""
        return [
            *self._raw.get("active", []),
            *self._raw.get("passive", []),
            *INNATE_SKILL_ORDER,
        ]

    def effective_value(self, trait_key: str) -> int:
        """Return a derived multiplied value without mutating stored traits."""
        base = getattr(self.entity.traits, trait_key).value
        multiplier = 1.0
        for skill_key in dict.fromkeys(self._raw.get("active", [])):
            skill = SKILL_REGISTRY.get(skill_key)
            if skill is None:
                continue
            owned_multiplier = _matching_multiplier(skill.effects, trait_key)
            if owned_multiplier is not None:
                multiplier *= owned_multiplier

        for grant in self.conferred_grants():
            if trait_key not in grant.trait_keys:
                continue
            source_skill = SKILL_REGISTRY.get(grant.skill_key)
            if source_skill is None:
                continue
            source_multiplier = _matching_multiplier(source_skill.effects, trait_key)
            if source_multiplier is not None:
                multiplier *= source_multiplier * grant.scale
        return round(base * multiplier)

    def conferred_grants(self) -> list[ConferredSkillGrant]:
        """Return explicitly recorded partial skill grants."""
        return list(self.entity.db.skill_grants or [])


def _matching_multiplier(effects: list[str], trait_key: str) -> float | None:
    """Combine stat multipliers in one skill that match a trait."""
    multipliers: list[float] = []
    for effect_id in effects:
        parsed = _parse_stat_multiply(effect_id)
        if parsed is not None and parsed[0] == trait_key:
            multipliers.append(parsed[1])
    if not multipliers:
        return None
    if len(multipliers) > 1:
        raise ValueError(
            f"skill defines duplicate stat multipliers for trait {trait_key!r}"
        )
    return multipliers[0]
