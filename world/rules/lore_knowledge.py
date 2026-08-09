"""Sole writer and readers of the player's lore codex (lore-knowledge-codex).

This module owns ``character.db.lore_discovered``, an append-only set of
namespaced ``category:key`` identifiers naming registry entries the player has
learned about through dialogue. It is the only module that writes that
attribute; the ``lore`` command and the dialogue applier read exclusively
through :func:`list_discovered` and :func:`lore_card`.

``CODE_CATEGORIES`` is the closed category-to-registry mapping: each of the
eight codex categories resolves to exactly one immutable ``world/lore/``
registry, and each category declares its own player-facing card fields.
``record_lore_reveal`` is the sole writer (append-only; repeat reveals are
no-ops; unknown categories and unresolvable keys reject with named errors),
``list_discovered`` returns a deterministic discovered-only listing, and
``lore_card`` renders one registry entry through the declared card fields,
never a raw dataclass dump.
"""

from collections.abc import Mapping, Set as ABCSet
from dataclasses import dataclass
from typing import Any

from world.lore.anchors import ANCHOR_REGISTRY
from world.lore.elements import ELEMENT_REGISTRY
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.magic import MAGIC_TIER_REGISTRY
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.nations import NATION_REGISTRY
from world.lore.races import RACE_REGISTRY
from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY

# The persisted codex attribute name. All stored entries are namespaced
# ``category:key`` identifiers.
KNOWLEDGE_ATTR = "lore_discovered"


class LoreCategoryError(ValueError):
    """A codex category is outside the closed category mapping."""


class LoreKeyError(ValueError):
    """A codex key does not resolve in its category's registry."""


class LoreRecordError(ValueError):
    """The stored codex record is missing, malformed, or has invalid content."""


@dataclass(frozen=True)
class CodexCategory:
    """One codex category: its exactly-one registry and card field names.

    Attributes:
        registry: The immutable ``world/lore/`` registry this category
            resolves to (exactly one per category).
        card_fields: The player-facing card fields declared for this
            category, in rendering order.
    """

    registry: Mapping[str, Any]
    card_fields: tuple[str, ...]


CODE_CATEGORIES: dict[str, CodexCategory] = {
    "race": CodexCategory(RACE_REGISTRY, ("key", "description")),
    "nation": CodexCategory(NATION_REGISTRY, ("display_name_zh", "capital_anchor_key")),
    "region": CodexCategory(
        WILDERNESS_REGION_REGISTRY, ("display_name_zh", "terrain_flavor_zh")
    ),
    "monster": CodexCategory(
        MONSTER_TIER_REGISTRY, ("display_name_zh", "description", "example_monsters_zh")
    ),
    "element": CodexCategory(ELEMENT_REGISTRY, ("display_name_zh", "description")),
    "magic": CodexCategory(MAGIC_TIER_REGISTRY, ("display_name_zh", "description")),
    "anchor": CodexCategory(ANCHOR_REGISTRY, ("display_name_zh", "description")),
    "guild": CodexCategory(GUILD_RANK_REGISTRY, ("key", "description")),
}


def _namespaced_id(category: str, key: str) -> str:
    return f"{category}:{key}"


def _validated_record(record: Any) -> set[str]:
    """Strictly parse a stored codex record, raising on corrupt content.

    Every stored identifier must be a namespaced ``category:key`` string whose
    category is in ``CODE_CATEGORIES`` and whose key resolves in that
    category's registry; anything else is a corrupt record. The returned set
    is a fresh copy so the caller never mutates the stored value.
    """
    if not isinstance(record, ABCSet) or not all(
        isinstance(item, str) for item in record
    ):
        raise LoreRecordError("lore codex record is not a set of strings")
    for item in record:
        if ":" not in item:
            raise LoreRecordError(f"lore codex entry {item!r} is not namespaced")
        category, _, key = item.partition(":")
        codex = CODE_CATEGORIES.get(category)
        if codex is None:
            raise LoreRecordError(f"lore codex entry {item!r} has an unknown category")
        if key not in codex.registry:
            raise LoreRecordError(f"lore codex entry {item!r} has an unresolvable key")
    return set(record)


def record_lore_reveal(player: Any, category: str, key: str) -> None:
    """Record one discovered lore entry (the sole writer of the codex).

    ``category`` must be in ``CODE_CATEGORIES`` and ``key`` must resolve in
    that category's registry; otherwise a named error is raised and the record
    is unchanged. A repeat reveal of the same entry is a no-op success. A
    corrupt pre-existing record is rejected with a named error and never
    overwritten or reset.
    """
    codex = CODE_CATEGORIES.get(category)
    if codex is None:
        raise LoreCategoryError(f"unknown lore category {category!r}")
    if key not in codex.registry:
        raise LoreKeyError(f"no lore entry {key!r} in category {category!r}")
    current = player.db.lore_discovered
    if current is None:
        current = set()
    else:
        current = _validated_record(current)
    entry = _namespaced_id(category, key)
    if entry in current:
        return
    updated = set(current)
    updated.add(entry)
    player.db.lore_discovered = updated


def list_discovered(player: Any) -> tuple[tuple[str, str], ...]:
    """Return the discovered ``(category, key)`` pairs in deterministic order.

    The listing is ordered by category mapping order, then key, and never
    includes entries that were not revealed. A player with no record lists as
    empty. A malformed record raises :class:`LoreRecordError` (the stored
    value is never reset or fabricated).
    """
    current = player.db.lore_discovered
    if current is None:
        return ()
    record = _validated_record(current)
    by_category: dict[str, set[str]] = {
        category: set() for category in CODE_CATEGORIES
    }
    for item in record:
        category, _, key = item.partition(":")
        by_category[category].add(key)
    return tuple(
        (category, key)
        for category, keys in by_category.items()
        for key in sorted(keys)
    )


def _card_value(value: Any) -> str:
    """Convert one registry field value to its player-facing card text."""
    if isinstance(value, (tuple, list)):
        return "\n".join(str(item) for item in value)
    return str(value)


def lore_card(category: str, key: str) -> dict[str, str]:
    """Render one registry entry as a player-facing card.

    The card contains exactly the category's declared card fields from
    ``CODE_CATEGORIES``, in declared order, never a raw dataclass dump. An
    unknown category raises :class:`LoreCategoryError` and an unresolvable
    key raises :class:`LoreKeyError` rather than fabricating a card.
    """
    codex = CODE_CATEGORIES.get(category)
    if codex is None:
        raise LoreCategoryError(f"unknown lore category {category!r}")
    entry = codex.registry.get(key)
    if entry is None:
        raise LoreKeyError(f"no lore entry {key!r} in category {category!r}")
    return {
        field: _card_value(getattr(entry, field)) for field in codex.card_fields
    }
