"""Deterministic state writes for skill effects.

The future ``ActionResolver`` calls these core primitives only after it has
validated ownership, resources, and targets. Keeping writes under
``world.rules`` preserves the project's single-writer boundary.
"""

from typing import Any

from world.skills.handler import ConferredSkillGrant


def record_conferred_grant(
    entity: Any,
    source_key: str,
    skill_key: str,
    trait_keys: tuple[str, ...],
    scale: float,
) -> None:
    """Persist grant data after the resolver has validated the action."""
    grants = list(entity.db.skill_grants or [])
    grants.append(ConferredSkillGrant(source_key, skill_key, trait_keys, scale))
    entity.db.skill_grants = grants


def apply_disguise_effect(entity: Any, overrides: dict[str, int]) -> None:
    """Persist display-only overrides after deterministic resolution."""
    entity.db.disguised_stats = dict(overrides)
