"""The deterministic built-in fallback resolver (gallery-builtin-fallbacks).

Resolves a subject to one of the six committed images in
``web/static/art/defaults/`` served through the ``/art/defaults/<key>.<ext>``
route. The vocabulary, extension, and size bound are the shared constants in
``world.art.fallback_keys`` (the same set the media route admits and the
contract test locks). Resolution is ordered:

1. a declared fallback key on the subject's registry entry wins outright —
   monsters declare through ``MONSTER_TIER_REGISTRY`` (addressed directly by
   the subject key), while preset-born players/companions and scene-spawned
   NPCs carry their provenance key on the entity (``creation_preset_key`` /
   ``npc_tier_key``) because their portrait subject key is the entity pk,
   not the registry key;
2. otherwise a monster subject resolves ``monster_anon``;
3. otherwise the stored sex and apparent age select a band (child / adult /
   elder); ``female``/``male`` resolve that band's sex key directly and any
   other sex hashes the subject's full key into the band's ordered pool.

The resolution is a pure function of the subject key plus the stored sex and
apparent age: the same subject resolves the same key on every restart, on
every process, and on every machine. Missing or malformed sex or apparent-age
values fail closed to the adult band rather than raising. Scene subjects are
not persons — they get no fallback (``None``).

The module writes nothing: no record, no card, no store copy. Import
discipline: it stays clear of the generative-transport packages and the
``world.art.connectivity`` import; the entity rediscovery seam imports
``ObjectDB``/``LivingEntity`` function-locally exactly as ``service.py``'s
``_living_entity_for_stable_key`` does.
"""

from __future__ import annotations

import hashlib
from typing import Any

from world.art.fallback_keys import FALLBACK_EXTENSION, validate_fallback_key
from world.art.gallery import DEFAULT_FACE_RECT
from world.art.subjects import (
    ArtSubject,
    ArtSubjectError,
    ArtSubjectKind,
    character_subject_for,
)
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.player_presets import PLAYER_PRESET_REGISTRY

# Apparent-age band boundaries (plain ordinary-human reading of the 0..10000
# creation range): an apparent age at or below the child ceiling is a child,
# at or above the elder floor is an elder, everything else is an adult.
CHILD_APPARENT_AGE_MAXIMUM = 12
ELDER_APPARENT_AGE_MINIMUM = 60

# The band table. Each band maps the female/male pair to one key and carries
# an ordered pool; a sex outside the pair (including ``other``, the default,
# and every malformed value) hashes into the pool. The pool order is part of
# the determinism contract and must never drift.
_AGE_BANDS: dict[str, dict[str, object]] = {
    "child": {"female": "girl", "male": "boy", "pool": ("boy", "girl")},
    "adult": {"female": "woman", "male": "man", "pool": ("man", "woman")},
    "elder": {"female": "elder", "male": "elder", "pool": ("elder",)},
}

# The fixed per-key face-rectangle map, authored against the committed
# full-body images (normalized unit-square rects). A key without its own
# entry falls back to the shared ``DEFAULT_FACE_RECT``.
FALLBACK_FACE_RECTS: dict[str, dict[str, float]] = {
    "man": {"x": 0.33, "y": 0.02, "w": 0.34, "h": 0.22},
    "woman": {"x": 0.33, "y": 0.02, "w": 0.34, "h": 0.22},
    "boy": {"x": 0.33, "y": 0.03, "w": 0.34, "h": 0.22},
    "girl": {"x": 0.33, "y": 0.03, "w": 0.34, "h": 0.22},
    "elder": {"x": 0.33, "y": 0.02, "w": 0.34, "h": 0.22},
    "monster_anon": {"x": 0.33, "y": 0.02, "w": 0.34, "h": 0.22},
}

# Entity-carried provenance attribute names written by the spawning/activation
# paths so a registry declaration can be found for subjects whose portrait key
# is the entity pk rather than a registry key.
PRESET_PROVENANCE_ATTRIBUTE = "creation_preset_key"
NPC_TIER_PROVENANCE_ATTRIBUTE = "npc_tier_key"


def fallback_face_rect(key: str) -> dict[str, float]:
    """The key's declared rectangle, or the shared default for no entry."""
    rect = FALLBACK_FACE_RECTS.get(key)
    return dict(rect) if rect is not None else dict(DEFAULT_FACE_RECT)


def fallback_identity_and_rect(key: str) -> tuple[str, dict[str, float]]:
    """The committed route-relative identity for ``key`` plus its rectangle."""
    return f"defaults/{key}{FALLBACK_EXTENSION}", fallback_face_rect(key)


def _declared_key_for_entity(entity: Any) -> str | None:
    """The fallback key declared through an entity's registry provenance.

    Reads the provenance attributes written at activation/spawn time and
    validates whatever the registry declares (a registry entry added after
    import cannot smuggle an invalid key past the construction-time sweep, so
    a declared-but-invalid value is treated as absent here, never raised).
    """
    if entity is None:
        return None
    attributes = getattr(entity, "attributes", None)
    if attributes is None:
        return None
    preset_key = attributes.get(PRESET_PROVENANCE_ATTRIBUTE)
    if isinstance(preset_key, str):
        preset = PLAYER_PRESET_REGISTRY.get(preset_key)
        if preset is not None:
            declared = preset.fallback_key
            try:
                validate_fallback_key(declared, f"preset {preset_key!r}")
            except ValueError:  # observability: ignore R2: malformed late-declared key treated as undeclared, band rule decides
                return None
            return declared
    tier_key = attributes.get(NPC_TIER_PROVENANCE_ATTRIBUTE)
    if isinstance(tier_key, str):
        tier = NPC_TIER_REGISTRY.get(tier_key)
        if tier is not None:
            declared = tier.fallback_key
            try:
                validate_fallback_key(declared, f"NPC tier {tier_key!r}")
            except ValueError:  # observability: ignore R2: malformed late-declared key treated as undeclared, band rule decides
                return None
            return declared
    return None


def _declared_key_for_subject_key(subject: ArtSubject) -> str | None:
    """A declaration addressed directly by the subject's own registry key.

    Only monsters have subject keys that ARE registry keys
    (``portrait:monster:<threat-tier>``); character subject keys are entity
    pks or authored stable keys, never preset/tier keys, so their
    declarations resolve through entity provenance instead.
    """
    if subject.kind is not ArtSubjectKind.MONSTER:
        return None
    tier = MONSTER_TIER_REGISTRY.get(subject.key)
    if tier is None:
        return None
    declared = tier.fallback_key
    try:
        validate_fallback_key(declared, f"monster tier {subject.key!r}")
    except ValueError:  # observability: ignore R2: malformed late-declared key treated as undeclared, band rule decides
        return None
    return declared


def _entity_for_character_subject(subject: ArtSubject) -> Any:
    """The living entity carrying a character's named portrait subject.

    Only used when the caller (normally the presenter) has no entity to
    thread through. Digit-only keys (player pks) take the direct ``ObjectDB``
    primary-key path, re-deriving the subject through ``character_subject_for``
    to prove the row really carries it. Every other key is a stable portrait
    key: the scan is pk-ordered and returns an entity ONLY when exactly one
    living entity carries the key — a shared stable key with different
    provenance would be nondeterministic, so an ambiguous key recovers no
    entity and resolution fails closed to the band rule (sex and apparent age
    are then absent too, closing on the adult pool). No entity is a legal
    answer.
    """
    from evennia.objects.models import ObjectDB

    from typeclasses.entities import LivingEntity

    if subject.key.isdigit():
        row = ObjectDB.objects.filter(pk=int(subject.key)).first()
        if row is not None and isinstance(row, LivingEntity):
            try:
                if character_subject_for(row) == subject:
                    return row
            except ArtSubjectError:  # observability: ignore R2: malformed policy on the pk row -> scan below fails closed
                pass
        return None
    matches = 0
    found = None
    for entity in ObjectDB.objects.order_by("id"):
        if not isinstance(entity, LivingEntity):
            continue
        try:
            derived = character_subject_for(entity)
        except ArtSubjectError:  # observability: ignore R2: scan skip; the unpaired entity yields no portrait subject
            continue
        if derived is not None and derived == subject:
            matches += 1
            found = entity
            if matches > 1:
                break
    return found if matches == 1 else None


def _band_name_for_apparent_age(apparent_age: object) -> str:
    """The band an apparent-age value selects, failing closed to adult."""
    if type(apparent_age) is not int:
        return "adult"
    if apparent_age <= CHILD_APPARENT_AGE_MAXIMUM:
        return "child"
    if apparent_age >= ELDER_APPARENT_AGE_MINIMUM:
        return "elder"
    return "adult"


def _hash_into_pool(subject_full_key: str, pool: tuple[str, ...]) -> str:
    """The pool entry a subject's full key deterministically hashes into.

    ``sha256`` over the UTF-8 full subject key — stable across processes,
    machines, and restarts (unlike ``hash()``).
    """
    digest = hashlib.sha256(subject_full_key.encode("utf-8")).digest()
    return pool[int.from_bytes(digest, "big") % len(pool)]


def fallback_key_for(subject: ArtSubject, entity: Any = None) -> str:
    """Resolve the fallback key for ``subject`` by declaration, band, hash.

    ``entity`` is the character's live entity carrying ``sex``/``apparent_age``
    and registry provenance (``None`` for monsters — their declaration and
    constant come from the tier registry — and for an unrecoverable character
    subject, which then fails closed to the adult-band pool).
    """
    declared = _declared_key_for_subject_key(subject)
    if declared is None and subject.kind is not ArtSubjectKind.MONSTER:
        declared = _declared_key_for_entity(entity)
    if declared is not None:
        return declared
    if subject.kind is ArtSubjectKind.MONSTER:
        return "monster_anon"
    sex = getattr(entity, "sex", None) if entity is not None else None
    stored = getattr(entity, "db", None) if entity is not None else None
    apparent_age = getattr(stored, "apparent_age", None) if stored is not None else None
    band = _AGE_BANDS[_band_name_for_apparent_age(apparent_age)]
    sex_key = band["female"] if sex == "female" else band["male"] if sex == "male" else None
    if sex_key is not None:
        return str(sex_key)
    return _hash_into_pool(subject.full(), band["pool"])


def resolve_fallback(subject: ArtSubject, entity: Any = None) -> dict | None:
    """The seam's resolution: ``{identity, face_rect, key}`` or ``None``.

    Scenes resolve ``None`` (no fallback image exists for a place). A
    character subject uses the entity the caller threads through; without
    one it recovers a deterministic identification through the lookup above
    (and fails closed when a shared stable key makes that ambiguous);
    monsters need no entity. Writes nothing.
    """
    if subject.kind is ArtSubjectKind.SCENE:
        return None
    if entity is None and subject.kind is ArtSubjectKind.CHARACTER:
        entity = _entity_for_character_subject(subject)
    key = fallback_key_for(subject, entity)
    identity, face_rect = fallback_identity_and_rect(key)
    return {"identity": identity, "face_rect": face_rect, "key": key}


__all__ = [
    "CHILD_APPARENT_AGE_MAXIMUM",
    "ELDER_APPARENT_AGE_MINIMUM",
    "FALLBACK_FACE_RECTS",
    "NPC_TIER_PROVENANCE_ATTRIBUTE",
    "PRESET_PROVENANCE_ATTRIBUTE",
    "fallback_face_rect",
    "fallback_identity_and_rect",
    "fallback_key_for",
    "resolve_fallback",
]
