"""Authoritative visual-species registry for monster art representations.

Design reference: fix-monster-species-portraits D1.

Separates art visual identity from combat mechanics: the visual registry is
exactly the projection of the complete combat species registry, each species
contributing its public appearance through a pure adapter. No visual
declaration exists without a combat species.
"""

from dataclasses import dataclass
from typing import Mapping

from world.lore.monster_species import (
    MONSTER_SPECIES_REGISTRY,
    MonsterSpecies,
)

# Reserved stable-key grammar: lowercase letters, numbers, underscores.
# Must start with letter. Threat-tier names and internal reserved tokens are rejected.
RESERVED_KEYS = frozenset({
    "low",
    "mid",
    "high",
    "calamity",
    "monster_anon",
    "character_anon",
    "anon",
    "default",
})


@dataclass(frozen=True)
class MonsterVisualDeclaration:
    """Public appearance projection of a monster visual species."""

    stable_key: str
    display_label: str
    published_appearance_zh: str


def adapt_combat_species(species: MonsterSpecies) -> MonsterVisualDeclaration:
    """Project a complete MonsterSpecies into its public art visual appearance."""
    return MonsterVisualDeclaration(
        stable_key=species.key,
        display_label=species.display_name_zh,
        published_appearance_zh=species.published_appearance_zh or species.display_name_zh,
    )


def build_monster_visual_registry(
    combat_species_registry: Mapping[str, MonsterSpecies] | None = None,
) -> dict[str, MonsterVisualDeclaration]:
    """Project the combat species registry into the visual species registry.

    Every complete combat species contributes exactly one declaration keyed by
    its stable key. A reserved key, or a mapping key that disagrees with its
    row's own key (which is also how two entries declaring one duplicate key
    surface), is an authoring error raised before any consumer can observe
    the registry.
    """
    active_combat = (
        combat_species_registry
        if combat_species_registry is not None
        else MONSTER_SPECIES_REGISTRY
    )
    registry: dict[str, MonsterVisualDeclaration] = {}
    for key, species in active_combat.items():
        if key in RESERVED_KEYS:
            raise ValueError(f"Combat species key '{key}' is reserved")
        if species.key != key:
            raise ValueError(
                f"Combat species mapping key '{key}' disagrees with its row key '{species.key}'"
            )
        registry[key] = adapt_combat_species(species)
    return registry


# Active registry getter (pure, dynamic to reflect test-scoped synthetic registries)
def get_monster_visual_registry() -> dict[str, MonsterVisualDeclaration]:
    """Return the visual registry projected from the current combat species state."""
    return build_monster_visual_registry()


def is_registered_monster_visual_key(key: str) -> bool:
    """Check if key is an admitted monster visual species key."""
    if not isinstance(key, str) or not key or key in RESERVED_KEYS:
        return False
    return key in get_monster_visual_registry()
