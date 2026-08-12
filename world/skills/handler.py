"""Skill handling from design section 5.2 and ``skills-equipment``."""

from dataclasses import dataclass
from typing import Any

from .effects import StatMultiplyEffect
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
        owned = [
            *self._raw.get("active", []),
            *self._raw.get("passive", []),
        ]
        for skill_key in dict.fromkeys(owned):
            skill = SKILL_REGISTRY.get(skill_key)
            if skill is None:
                continue
            owned_multiplier = _matching_multiplier(skill.parsed_effects, trait_key)
            if owned_multiplier is not None:
                multiplier *= owned_multiplier

        for grant in self.conferred_grants():
            if trait_key not in grant.trait_keys:
                continue
            source_skill = SKILL_REGISTRY.get(grant.skill_key)
            if source_skill is None:
                continue
            source_multiplier = _matching_multiplier(
                source_skill.parsed_effects, trait_key
            )
            if source_multiplier is not None:
                multiplier *= source_multiplier * grant.scale
        return round(base * multiplier)

    def conferred_grants(self) -> list[ConferredSkillGrant]:
        """Return explicitly recorded partial skill grants."""
        return list(self.entity.db.skill_grants or [])


def _matching_multiplier(
    parsed_effects: tuple, trait_key: str
) -> float | None:
    """Combine stat multipliers in one skill that match a trait."""
    multipliers = [
        effect.multiplier
        for effect in parsed_effects
        if isinstance(effect, StatMultiplyEffect) and effect.trait == trait_key
    ]
    if not multipliers:
        return None
    if len(multipliers) > 1:
        raise ValueError(
            f"skill defines duplicate stat multipliers for trait {trait_key!r}"
        )
    return multipliers[0]
