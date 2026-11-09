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

The ``monster`` category is a species bestiary with two research stages
(lore-species-research). A species is *sighted* when ``monster:<species>``
is in ``lore_discovered`` and *defeated* when its key is also in
``character.db.lore_species_defeated``, a second append-only set this module
alone writes. ``record_species_sighting`` and ``record_species_defeat`` are
its writers (a defeat also records the sighting), ``list_species_defeated``
its reader, and the ``schedule_species_*_best_effort`` helpers the
post-commit, never-failing entry points the combat hooks use.
"""

from collections.abc import Callable, Mapping, Set as ABCSet
from dataclasses import dataclass
from typing import Any

from world.lore.elements import ELEMENT_REGISTRY
from world.lore.guild import GUILD_RANK_REGISTRY
from world.lore.magic import MAGIC_TIER_REGISTRY
from world.lore.monster_species import MONSTER_SPECIES_REGISTRY
from world.lore.nations import NATION_REGISTRY
from world.lore.races import RACE_REGISTRY
from world.observability import log_warn

# The persisted codex attribute name. All stored entries are namespaced
# ``category:key`` identifiers.
KNOWLEDGE_ATTR = "lore_discovered"

# The persisted defeated-species attribute name: an append-only set of bare
# species keys (no category prefix).
DEFEATED_ATTR = "lore_species_defeated"

# Player-facing category labels used by the listing groups and presentation panels.
CATEGORY_LABELS: dict[str, str] = {
    "race": "種族",
    "nation": "國家",
    "region": "地域",
    "monster": "魔物",
    "element": "元素",
    "magic": "魔法",
    "anchor": "地點",
    "guild": "公會",
}


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
        loader: The callable returning the registry this category resolves to
            (exactly one per category). Map-owned categories read the published
            geography at call time, so a reload is always observed.
        card_fields: The player-facing card fields declared for this
            category, in rendering order.
    """

    loader: Callable[[], Mapping[str, Any]]
    card_fields: tuple[str, ...]

    @property
    def registry(self) -> Mapping[str, Any]:
        """The current registry for this category."""

        return self.loader()


def _constant(registry: Mapping[str, Any]) -> Callable[[], Mapping[str, Any]]:
    return lambda: registry


def _published(attribute: str) -> Callable[[], Mapping[str, Any]]:
    def load() -> Mapping[str, Any]:
        from world.maps.geography import current

        return getattr(current(), attribute)

    return load


CODE_CATEGORIES: dict[str, CodexCategory] = {
    "race": CodexCategory(_constant(RACE_REGISTRY), ("display_name_zh", "description")),
    "nation": CodexCategory(_constant(NATION_REGISTRY), ("display_name_zh", "capital_name_zh")),
    "region": CodexCategory(
        _published("regions"), ("display_name_zh", "terrain_flavor_zh")
    ),
    # The species registry is a frozen MappingProxyType, so the loader reads
    # this module's binding at call time instead of capturing the object at
    # import: a swapped binding (synthetic test scopes) is always observed.
    "monster": CodexCategory(
        lambda: MONSTER_SPECIES_REGISTRY,
        ("display_name_zh", "published_appearance_zh"),
    ),
    "element": CodexCategory(_constant(ELEMENT_REGISTRY), ("display_name_zh", "description")),
    "magic": CodexCategory(_constant(MAGIC_TIER_REGISTRY), ("display_name_zh", "description")),
    "anchor": CodexCategory(_published("anchors"), ("display_name_zh", "description")),
    "guild": CodexCategory(_constant(GUILD_RANK_REGISTRY), ("display_name_zh", "description")),
}


def _namespaced_id(category: str, key: str) -> str:
    return f"{category}:{key}"


def _validated_record(record: Any, *, tolerant: bool = False) -> set[str]:
    """Strictly parse a stored codex record, raising on corrupt content.

    Every stored identifier must be a namespaced ``category:key`` string whose
    category is in ``CODE_CATEGORIES`` and whose key resolves in that
    category's registry; anything else is a corrupt record. Structural shape
    (exactly one delimiter, non-empty category and key) is ALWAYS enforced —
    a malformed identifier is corruption, never a vanished key. When
    ``tolerant`` is True (used by the presentation panel), well-formed
    identifiers whose keys no longer resolve in their registry are preserved
    so the presenter can omit them cleanly instead of degrading the entire
    panel. The returned set is a fresh copy so the caller never mutates the
    stored value.
    """
    if not isinstance(record, ABCSet) or not all(
        isinstance(item, str) for item in record
    ):
        raise LoreRecordError("lore codex record is not a set of strings")
    for item in record:
        if ":" not in item:
            raise LoreRecordError(f"lore codex entry {item!r} is not namespaced")
        category, _, key = item.partition(":")
        if not category or not key or ":" in key:
            raise LoreRecordError(f"lore codex entry {item!r} is malformed")
        codex = CODE_CATEGORIES.get(category)
        if codex is None:
            raise LoreRecordError(f"lore codex entry {item!r} has an unknown category")
        if not tolerant and key not in codex.registry:
            raise LoreRecordError(f"lore codex entry {item!r} has an unresolvable key")
    return set(record)


def _schedule_lore_codex_push(player: Any) -> None:
    """Register the codex push strictly after the surrounding transaction commits.

    Django's ``on_commit`` already runs the callback synchronously in
    autocommit mode; a registration failure (manual transaction management)
    must NEVER fall back to an inline push, because an inline push could
    publish state that the open transaction later rolls back. The callback
    keeps the reveal write itself isolated from any presentation failure, and
    the captured causal publication group makes its panel push coalesce with
    the same commit's checkpoint presentation.
    """

    def _safe_push() -> None:
        try:
            from web.webclient.presentation.lore_codex_push import push_lore_codex_update

            push_lore_codex_update(player)
        except Exception as error:
            log_warn(
                "lore_codex_push_schedule_failed",
                context={"char": str(getattr(player, "pk", "?"))},
                exc=error,
            )

    from world.rules.presentation_events import on_publication_commit

    try:
        on_publication_commit(_safe_push)
    except Exception as error:
        log_warn(
            "lore_codex_push_register_failed",
            context={"char": str(getattr(player, "pk", "?"))},
            exc=error,
        )


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
    _schedule_lore_codex_push(player)


def reveal_lore_best_effort(player: Any, category: str, key: str) -> bool:
    """Record one discovered lore entry, swallowing and logging any failure.

    This is the best-effort boundary for deterministic gameplay callers
    (arrival, defeat, origin). It delegates exclusively to
    :func:`record_lore_reveal` and returns whether the reveal landed or was
    already discovered; any failure is logged through the observability facade
    with its exception and context dict.
    """
    try:
        record_lore_reveal(player, category, key)
        return True
    except Exception as exc:
        log_warn(
            "lore_reveal_failed",
            exc=exc,
            context={
                "char": str(getattr(player, "key", player)),
                "category": category,
                "key": key,
            },
        )
        return False


def schedule_lore_reveal_best_effort(
    player: Any, category: str, key: str | None
) -> None:
    """Schedule a best-effort lore reveal to execute after transaction commit.

    Protects both key validation and transaction registration so unexpected
    failures never bubble into gameplay. The registration captures the current
    causal publication group, so the reveal's own codex push joins it.
    """
    if not isinstance(key, str) or not key or not isinstance(category, str) or not category:
        return
    try:
        from world.rules.presentation_events import on_publication_commit

        on_publication_commit(
            lambda: reveal_lore_best_effort(player, category, key)
        )
    except Exception as exc:
        log_warn(
            "lore_reveal_failed",
            exc=exc,
            context={
                "char": str(getattr(player, "key", player)),
                "category": category,
                "key": key,
            },
        )


def _require_species_key(species_key: Any) -> None:
    """Reject a key that does not resolve in the monster (species) category."""
    if not isinstance(species_key, str) or species_key not in CODE_CATEGORIES["monster"].registry:
        raise LoreKeyError(f"no lore entry {species_key!r} in category 'monster'")


def _validated_species_record(record: Any, *, tolerant: bool = False) -> set[str]:
    """Strictly parse a stored defeated-species record, raising on corrupt content.

    The record must be a set of non-empty str keys without ``':'``; strict mode
    also requires each key to resolve in ``CODE_CATEGORIES["monster"]``. When
    ``tolerant`` is True, a well-formed key that no longer resolves is kept.
    Anything else raises :class:`LoreRecordError`. Returns a fresh copy.
    """
    if not isinstance(record, ABCSet) or not all(
        isinstance(item, str) for item in record
    ):
        raise LoreRecordError("defeated species record is not a set of strings")
    registry = CODE_CATEGORIES["monster"].registry
    for item in record:
        if not item or ":" in item:
            raise LoreRecordError(f"defeated species entry {item!r} is malformed")
        if not tolerant and item not in registry:
            raise LoreRecordError(f"defeated species entry {item!r} is unresolvable")
    return set(record)


def list_species_defeated(player: Any, *, tolerant: bool = False) -> tuple[str, ...]:
    """Return the defeated species keys in sorted order.

    A player with no record reads as ``()``. A malformed record raises
    :class:`LoreRecordError` (the stored value is never reset or fabricated).
    """
    current = getattr(player.db, DEFEATED_ATTR)
    if current is None:
        return ()
    return tuple(sorted(_validated_species_record(current, tolerant=tolerant)))


def record_species_sighting(player: Any, species_key: str) -> None:
    """Record that the player has sighted one species (``monster:<key>``).

    Validates the key (:class:`LoreKeyError`) and writes exclusively through
    :func:`record_lore_reveal`, so the codex keeps its single writer and its
    one-push-per-change rule.
    """
    _require_species_key(species_key)
    record_lore_reveal(player, "monster", species_key)


def record_species_defeat(player: Any, species_key: str) -> None:
    """Record that the player has defeated one species (implies the sighting).

    Validates the key and the stored defeated record strictly BEFORE any write,
    records the sighting, then appends the key to the defeated set and
    schedules one codex push only when that set changed. A repeat defeat is a
    no-op success; a corrupt record raises and is never rewritten.
    """
    _require_species_key(species_key)
    current = getattr(player.db, DEFEATED_ATTR)
    current = set() if current is None else _validated_species_record(current)
    record_species_sighting(player, species_key)
    if species_key in current:
        return
    updated = set(current)
    updated.add(species_key)
    setattr(player.db, DEFEATED_ATTR, updated)
    _schedule_lore_codex_push(player)


def _species_failure_context(player: Any, species_key: Any, stage: str) -> dict[str, Any]:
    return {
        "char": str(getattr(player, "key", player)),
        "category": "monster",
        "key": species_key,
        "stage": stage,
    }


def _species_best_effort(player: Any, species_key: str, stage: str) -> None:
    """Run one species writer, logging (never raising) any failure."""
    writer = record_species_defeat if stage == "defeated" else record_species_sighting
    try:
        writer(player, species_key)
    except Exception as exc:
        log_warn(
            "lore_reveal_failed",
            exc=exc,
            context=_species_failure_context(player, species_key, stage),
        )


def _schedule_species_best_effort(player: Any, species_key: Any, stage: str) -> None:
    if not isinstance(species_key, str) or not species_key:
        return
    try:
        from world.rules.presentation_events import on_publication_commit

        on_publication_commit(
            lambda: _species_best_effort(player, species_key, stage)
        )
    except Exception as exc:
        log_warn(
            "lore_reveal_failed",
            exc=exc,
            context=_species_failure_context(player, species_key, stage),
        )


def schedule_species_sighting_best_effort(player: Any, species_key: str | None) -> None:
    """Schedule a best-effort species sighting to run after the transaction commits."""
    _schedule_species_best_effort(player, species_key, "sighted")


def schedule_species_defeat_best_effort(player: Any, species_key: str | None) -> None:
    """Schedule a best-effort species defeat to run after the transaction commits."""
    _schedule_species_best_effort(player, species_key, "defeated")


def list_discovered(player: Any, *, tolerant: bool = False) -> tuple[tuple[str, str], ...]:
    """Return the discovered ``(category, key)`` pairs in deterministic order.

    The listing is ordered by category mapping order, then key, and never
    includes entries that were not revealed. A player with no record lists as
    empty. A malformed record raises :class:`LoreRecordError` (the stored
    value is never reset or fabricated).
    """
    current = player.db.lore_discovered
    if current is None:
        return ()
    record = _validated_record(current, tolerant=tolerant)
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
