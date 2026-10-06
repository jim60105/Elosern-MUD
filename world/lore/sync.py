"""Idempotent DB mirror for registries from lore-world-data."""

from dataclasses import asdict
from enum import Enum
from typing import Any, Mapping

from evennia import DefaultScript
from evennia.utils.create import create_script
from evennia.utils.search import search_script

from world.observability import log_info

from .anchors import ANCHOR_REGISTRY
from .anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from .economy import PRICE_TABLE
from .elements import ELEMENT_REGISTRY
from .guild import GUILD_RANK_REGISTRY
from .magic import MAGIC_TIER_REGISTRY
from .monster_species import MONSTER_SPECIES_REGISTRY, MONSTER_VARIANT_REGISTRY
from .monster_placement import (
    AMBIENT_PLACEMENT_REGISTRY,
    MONSTER_SITE_REGISTRY,
)
from .names import NAME_PACK_REGISTRY
from .monsters import MONSTER_TIER_REGISTRY
from .nations import NATION_REGISTRY
from .races import RACE_REGISTRY, STATIC_TIER_REGISTRY, SUBRACE_REGISTRY
from .settlements import PLACE_REGISTRY, SETTLEMENT_REGISTRY
from .titles import FIXED_TITLE_REGISTRY
from .wilderness_entry import WILDERNESS_ENTRY_REGISTRY, validate_wilderness_entries
from .wilderness_regions import WILDERNESS_REGION_REGISTRY


class LoreRecord(DefaultScript):
    """Persistent, non-ticking mirror of one frozen lore entry."""


# The species/variant categories are mirrored by their own named
# synchronization step (monster-species-registry design D-S7) rather than by
# the generic loop, so the mirror's one boundary event can carry the
# registry-scoped context. This is the single declaration both the mirror
# table below and that step read, so the skip set and the step can never
# disagree.
MONSTER_SPECIES_REGISTRIES: dict[str, Mapping[str, Any]] = {
    "monster_species": MONSTER_SPECIES_REGISTRY,
    "monster_variants": MONSTER_VARIANT_REGISTRY,
}
MONSTER_SPECIES_CATEGORIES: tuple[str, ...] = tuple(MONSTER_SPECIES_REGISTRIES)

# The placement categories are mirrored by their own named step
# (`sync_monster_placement`, monster-site-placement task 1.2) for the same
# reason: the mirror's one boundary event carries placement-scoped context.
# This is the single declaration both the mirror table below and that step
# read, so the skip set and the step can never disagree.
MONSTER_PLACEMENT_REGISTRIES: dict[str, Mapping[str, Any]] = {
    "ambient_placements": AMBIENT_PLACEMENT_REGISTRY,
    "monster_sites": MONSTER_SITE_REGISTRY,
}
MONSTER_PLACEMENT_CATEGORIES: tuple[str, ...] = tuple(MONSTER_PLACEMENT_REGISTRIES)

# Categories mirrored by a named step instead of the generic loop below.
_NAMED_STEP_CATEGORIES: tuple[str, ...] = (
    MONSTER_SPECIES_CATEGORIES + MONSTER_PLACEMENT_CATEGORIES
)

_ALL_REGISTRIES: dict[str, Mapping[str, Any]] = {
    "races": RACE_REGISTRY,
    "static_tiers": STATIC_TIER_REGISTRY,
    "subraces": SUBRACE_REGISTRY,
    "elements": ELEMENT_REGISTRY,
    "magic_tiers": MAGIC_TIER_REGISTRY,
    "nations": NATION_REGISTRY,
    "guild_ranks": GUILD_RANK_REGISTRY,
    "titles": FIXED_TITLE_REGISTRY,
    "monster_tiers": MONSTER_TIER_REGISTRY,
    **MONSTER_SPECIES_REGISTRIES,
    **MONSTER_PLACEMENT_REGISTRIES,
    "anchors": ANCHOR_REGISTRY,
    "anchor_placements": ANCHOR_PLACEMENT_REGISTRY,
    "name_packs": NAME_PACK_REGISTRY,
    "wilderness_regions": WILDERNESS_REGION_REGISTRY,
    "wilderness_entries": WILDERNESS_ENTRY_REGISTRY,
    "settlements": SETTLEMENT_REGISTRY,
    "places": PLACE_REGISTRY,
    "prices": PRICE_TABLE,
}


def _db_safe(value: Any) -> Any:
    """Convert enums in dataclass output to stable primitive values."""

    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _db_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_db_safe(item) for item in value)
    if isinstance(value, list):
        return [_db_safe(item) for item in value]
    return value


def sync_one(category: str, key: str, entry: Any) -> None:
    """Create or overwrite one category-qualified lore record."""

    script_key = f"lore:{category}:{key}"
    matches = search_script(script_key)
    script = matches[0] if matches else create_script(
        LoreRecord, key=script_key, persistent=True
    )
    script.db.category = category
    script.db.fields = _db_safe(asdict(entry))


def sync_all() -> None:
    """Mirror every registry entry into persistent Evennia Script rows.

    The species/variant categories are mirrored by
    :func:`sync_monster_species` (the named species synchronization step), so
    each of their entries is still mirrored exactly once per startup.
    The ambient-placement and monster-site categories are mirrored by
    :func:`sync_monster_placement` for the same reason.
    """

    # wilderness-anchor-footprint: malformed authored wilderness data fails at
    # startup, before any lore:wilderness_entries:* Script is created or
    # updated (all-or-nothing import convention).
    validate_wilderness_entries()

    for category, registry in _ALL_REGISTRIES.items():
        if category in _NAMED_STEP_CATEGORIES:
            continue
        for key, entry in registry.items():
            sync_one(category, key, entry)
    sync_monster_species()
    sync_monster_placement()


def sync_monster_species() -> None:
    """Mirror the species and variant registries, then emit one boundary event.

    Idempotent through the shared ``sync_one`` upsert (create-or-overwrite by
    ``lore:<category>:<key>``), so repeating the step leaves the mirrored state
    unchanged. It creates and updates only ``LoreRecord`` Scripts: no monster,
    room, quest, or art record is created, modified, or deleted.

    The single boundary ``monster_species_sync`` info event carries the
    registry identifiers and their entry counts. It is deliberately not named
    ``startup_step``: that event belongs to the composition-root catalog's
    ``_startup_step`` wrapper (one per catalog step, in catalog order), and
    this step is not a catalog step.
    """
    for category, registry in MONSTER_SPECIES_REGISTRIES.items():
        for key, entry in registry.items():
            sync_one(category, key, entry)
    log_info(
        "monster_species_sync",
        context={
            category: len(registry)
            for category, registry in MONSTER_SPECIES_REGISTRIES.items()
        },
    )


def sync_monster_placement() -> None:
    """Mirror the placement registries, then emit one boundary event.

    Idempotent through the shared ``sync_one`` upsert (create-or-overwrite by
    ``lore:<category>:<key>``), so repeating the step leaves the mirrored state
    unchanged. It creates and updates only ``LoreRecord`` Scripts: no monster,
    room, quest, or art record is created, modified, or deleted. The single
    boundary ``monster_placement_sync`` info event carries the registry
    identifiers and their entry counts; like ``monster_species_sync`` it is
    deliberately not named ``startup_step``, because that event belongs to the
    composition root's catalog wrapper and this step is not a catalog step.
    """
    for category, registry in MONSTER_PLACEMENT_REGISTRIES.items():
        for key, entry in registry.items():
            sync_one(category, key, entry)
    log_info(
        "monster_placement_sync",
        context={
            category: len(registry)
            for category, registry in MONSTER_PLACEMENT_REGISTRIES.items()
        },
    )
