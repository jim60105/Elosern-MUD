"""The single implementation of the race-bounded sex rule.

World canon admits no male elf: a race declares the sex members it may carry
(``RaceProfile.allowed_sexes`` in ``world.lore.races``), and every creation
path resolves a declared or omitted sex through this one seam. The callers are
the player-creation preflight (``world.rules.character_creation``), the import
loader (``world.imports.loader``), the place-host sync
(``world.rules.guild_economy``), the shared quest/scene/encounter spawn
(``world.quests.materializer``), and the starting-companion builder
(``world.rules.starting_companions``). ``ensure_entity_sex`` is the only
production writer of an entity's ``sex`` attribute.
"""

from __future__ import annotations

from typing import Any

from world.lore.races import RACE_REGISTRY
from world.lore.sex import DEFAULT_SEX, SEX_VALUES


class IdentityError(ValueError):
    """Raised when a declared identity value cannot be resolved."""


def permitted_sexes(race_key: Any) -> tuple[str, ...]:
    """The sex members one race may carry (every member for an unresolvable race)."""
    race = RACE_REGISTRY.get(race_key) if isinstance(race_key, str) else None
    return race.allowed_sexes if race is not None else SEX_VALUES


def resolve_sex(race_key: Any, sex: str | None) -> str:
    """Resolve a declared or omitted sex against the race's declared set."""
    allowed = permitted_sexes(race_key)
    if sex is None:
        return DEFAULT_SEX if DEFAULT_SEX in allowed else allowed[0]
    if sex not in SEX_VALUES:
        raise IdentityError("sex must be one of: " + ", ".join(SEX_VALUES))
    if sex not in allowed:
        raise IdentityError(f"sex {sex!r} is not available for race {race_key!r}")
    return sex


def ensure_entity_sex(entity: Any, sex: str | None = None) -> str:
    """Write the resolved sex on one entity and return it (the creation-path seam)."""
    resolved = resolve_sex(getattr(entity, "race", None), sex)
    entity.sex = resolved
    return resolved


__all__ = ["IdentityError", "permitted_sexes", "resolve_sex", "ensure_entity_sex"]
