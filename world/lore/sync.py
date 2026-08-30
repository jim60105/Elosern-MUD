"""Idempotent DB mirror for registries from lore-world-data."""

from dataclasses import asdict
from enum import Enum
from typing import Any, Mapping

from evennia import DefaultScript
from evennia.utils.create import create_script
from evennia.utils.search import search_script

from .anchors import ANCHOR_REGISTRY
from .anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from .economy import PRICE_TABLE
from .elements import ELEMENT_REGISTRY
from .guild import GUILD_RANK_REGISTRY
from .magic import MAGIC_TIER_REGISTRY
from .monsters import MONSTER_TIER_REGISTRY
from .nations import NATION_REGISTRY
from .races import RACE_REGISTRY, STATIC_TIER_REGISTRY, SUBRACE_REGISTRY
from .titles import FIXED_TITLE_REGISTRY
from .wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from .wilderness_regions import WILDERNESS_REGION_REGISTRY


class LoreRecord(DefaultScript):
    """Persistent, non-ticking mirror of one frozen lore entry."""


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
    "anchors": ANCHOR_REGISTRY,
    "anchor_placements": ANCHOR_PLACEMENT_REGISTRY,
    "wilderness_regions": WILDERNESS_REGION_REGISTRY,
    "wilderness_entries": WILDERNESS_ENTRY_REGISTRY,
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
    """Mirror every registry entry into persistent Evennia Script rows."""

    for category, registry in _ALL_REGISTRIES.items():
        for key, entry in registry.items():
            sync_one(category, key, entry)
