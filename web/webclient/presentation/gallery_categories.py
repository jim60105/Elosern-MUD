"""Gallery category sources and subject admission (webclient-gallery-categories).

The gallery window's closed category set, each bounded by its own source:

- ``mine``: every character of the account that owns the rendered puppet (the
  account roster's set), the live character first and marked current;
- ``party``: the owning character's live companions in party order;
- ``people`` / ``scene``: disabled in this programme stage;
- ``monster``: sighted visual species grouped by the threat tier of their
  default variant, in tier-registry order, each tier carrying ``seen / total``.

A subject is admitted for an actor exactly when it belongs to any enabled
category. Every function here is read-only: nothing writes a record, an
attribute or a file, and every diagnostic goes through the observability
facade.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from evennia.objects.models import ObjectDB

from world.art.subjects import (
    ArtSubject, ArtSubjectError, ArtSubjectKind, character_subject_for,
)
from world.lore.monster_species import MONSTER_SPECIES_REGISTRY, MONSTER_VARIANT_REGISTRY
from world.lore.monster_visuals import get_monster_visual_registry
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.observability import log_warn
from world.rules.account_roster import AccountRosterError, build_account_roster
from world.rules.lore_knowledge import LoreRecordError, list_discovered
from world.rules.party import bound_owner_of, live_companions

CATEGORY_KEYS = ("mine", "party", "people", "monster", "scene")
DISABLED_REASONS = {"people": "人物分類尚未開放。", "scene": "背景分類尚未開放。"}
MAX_DISPLAY_NAME = 64


class GalleryCategoryError(Exception):
    """The owning character or its account roster cannot be resolved."""


@dataclass(frozen=True)
class GallerySubjectRef:
    """One listed subject: its typed identity, live entity and caption."""

    subject: ArtSubject
    entity: Any | None
    display_name: str
    is_current: bool


@dataclass(frozen=True)
class GalleryGroup:
    """One ordered group of a category; ``seen``/``total`` on monster tiers only."""

    key: str
    label: str | None
    seen: int | None
    total: int | None
    subjects: tuple[GallerySubjectRef, ...]


@dataclass(frozen=True)
class GalleryCategory:
    """One category's summary: subject count, enabled flag, disabled reason."""

    key: str
    count: int
    enabled: bool
    reason: str | None


def _display_name(value: Any) -> str:
    return str(value)[:MAX_DISPLAY_NAME]


def gallery_owner(actor: Any) -> Any:
    """The character whose account and party the gallery follows.

    A possessed companion resolves to its bound owner; a missing or mismatched
    owner raises :class:`GalleryCategoryError`. Any other actor is its own owner.
    """
    possessed_by = getattr(getattr(actor, "db", None), "possessed_by", None)
    if possessed_by is None:
        return actor
    owner = bound_owner_of(actor)
    if owner is None or owner.pk != possessed_by:
        raise GalleryCategoryError("possessed actor has no live bound owner")
    return owner


def _mine(actor: Any) -> tuple[GalleryGroup, ...]:
    try:
        roster = build_account_roster(actor)
    except AccountRosterError as exc:
        raise GalleryCategoryError("account roster cannot be resolved") from exc
    rows = sorted(roster.characters, key=lambda row: (not row.current, row.identity))
    entities = {
        entity.pk: entity
        for entity in ObjectDB.objects.filter(id__in=[row.identity for row in rows])
    }
    refs = []
    for row in rows:
        entity = entities.get(row.identity)
        if entity is None:
            continue
        try:
            subject = character_subject_for(entity)
        except ArtSubjectError as exc:
            log_warn(
                "gallery_subject_invalid",
                context={"char": entity.pk, "category": "mine"}, exc=exc,
            )
            subject = None
        if subject is None:
            # Every account character is eligible: the owner manages their own
            # characters, so the numeric identity stands in for a named policy.
            subject = ArtSubject(ArtSubjectKind.CHARACTER, str(entity.pk))
        refs.append(GallerySubjectRef(subject, entity, _display_name(entity.key), row.current))
    return (GalleryGroup("mine", None, None, None, tuple(refs)),)


def _party(actor: Any) -> tuple[GalleryGroup, ...]:
    refs = []
    for entity in live_companions(gallery_owner(actor)):
        try:
            subject = character_subject_for(entity)
        except ArtSubjectError as exc:
            log_warn(
                "gallery_subject_invalid",
                context={"char": entity.pk, "category": "party"}, exc=exc,
            )
            continue
        if subject is None:
            continue
        refs.append(GallerySubjectRef(subject, entity, _display_name(entity.key), False))
    return (GalleryGroup("party", None, None, None, tuple(refs)),)


def _monster(actor: Any) -> tuple[GalleryGroup, ...]:
    # The holder is the rendered actor: the same object the lore codex reads,
    # so the two surfaces agree on what has been sighted. Unlike mine/party it
    # deliberately does not resolve a possessed puppet to its owner (design D4).
    try:
        seen_keys = {
            key for category, key in list_discovered(actor, tolerant=True)
            if category == "monster"
        }
    except LoreRecordError as exc:
        log_warn(
            "gallery_category_failed",
            context={"char": getattr(actor, "pk", None), "category": "monster"}, exc=exc,
        )
        seen_keys = set()
    registry = get_monster_visual_registry()
    by_tier: dict[str, list[str]] = {}
    for key in registry:
        species = MONSTER_SPECIES_REGISTRY.get(key)
        variant = (
            MONSTER_VARIANT_REGISTRY.get(species.default_variant_key)
            if species is not None else None
        )
        tier = variant.threat_tier if variant is not None else None
        if tier not in MONSTER_TIER_REGISTRY:
            log_warn(
                "gallery_category_failed",
                context={"species": key, "tier": tier, "category": "monster"},
            )
            continue
        by_tier.setdefault(tier, []).append(key)
    groups = []
    for tier_key, tier in MONSTER_TIER_REGISTRY.items():
        keys = by_tier.get(tier_key)
        if not keys:
            continue
        sighted = [key for key in keys if key in seen_keys]
        refs = []
        for key in sighted:
            try:
                # The registry is already in hand; the constructor re-validates
                # the key, so no per-species registry rebuild is needed.
                subject = ArtSubject(ArtSubjectKind.MONSTER, key)
            except ArtSubjectError as exc:
                log_warn(
                    "gallery_subject_invalid",
                    context={"species": key, "category": "monster"}, exc=exc,
                )
                continue
            refs.append(
                GallerySubjectRef(subject, None, _display_name(registry[key].display_label), False)
            )
        groups.append(
            GalleryGroup(tier_key, tier.display_name_zh, len(sighted), len(keys), tuple(refs))
        )
    return tuple(groups)


_SOURCES = {"mine": _mine, "party": _party, "monster": _monster}


def _enabled(key: str) -> bool:
    return key not in DISABLED_REASONS


def category_groups(actor: Any, key: str) -> tuple[GalleryGroup, ...]:
    """The ordered groups category ``key`` holds for ``actor``.

    A disabled category holds no groups; an unknown key raises ``KeyError``.
    """
    if key not in CATEGORY_KEYS:
        raise KeyError(key)
    if not _enabled(key):
        return ()
    return _SOURCES[key](actor)


def gallery_categories(actor: Any) -> tuple[GalleryCategory, ...]:
    """Every category in the closed order with its count and enabled state."""
    categories = []
    for key in CATEGORY_KEYS:
        if not _enabled(key):
            categories.append(GalleryCategory(key, 0, False, DISABLED_REASONS[key]))
            continue
        count = sum(len(group.subjects) for group in category_groups(actor, key))
        categories.append(GalleryCategory(key, count, True, None))
    return tuple(categories)


def category_of_subject(actor: Any, subject_key: str) -> str | None:
    """The first enabled category, in the closed order, listing ``subject_key``."""
    for key in CATEGORY_KEYS:
        if not _enabled(key):
            continue
        for group in category_groups(actor, key):
            if any(ref.subject.full() == subject_key for ref in group.subjects):
                return key
    return None


def is_subject_admitted(actor: Any, subject_key: str) -> bool:
    """Whether ``subject_key`` belongs to any enabled category for ``actor``."""
    return category_of_subject(actor, subject_key) is not None


__all__ = [
    "CATEGORY_KEYS",
    "DISABLED_REASONS",
    "GalleryCategory",
    "GalleryCategoryError",
    "GalleryGroup",
    "GallerySubjectRef",
    "category_groups",
    "category_of_subject",
    "gallery_categories",
    "gallery_owner",
    "is_subject_admitted",
]
