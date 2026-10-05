"""Deterministic gallery display resolution: the equipment-to-fallback chain.

``resolve_card`` decides which gallery image a subject displays, as a pure
function of stored state (the subject's card list, its explicit default, and
the entity's stored equipment — never the environment, never a write):

1. compute the entity's four-slot equipment snapshot from stored state
   (``world.art.gallery.snapshot_for``; accessories sorted, empty slot legal);
2. keep every card whose ``binding`` is not ``None`` and whose stored
   snapshot value for EVERY masked slot equals the computed value;
3. among those, the card whose mask covers the most slots wins; a tie is
   broken by the newest ``created_at``;
4. otherwise the card named by the record's ``default_image_id``;

Monster subjects skip steps 1-3 entirely — no equipment snapshot is ever
computed for them and no monster card is ever selected by a binding — so a
monster resolves through its default card alone. An unbound card is eligible
ONLY as the explicit default (step 4); no image the player has not chosen is
ever displayed as a surprise. Scene subjects have no gallery and always
resolve to ``None`` here.

The chain's remaining lookups live in the presenter, which owns payload
construction: the classic ``done`` asset record (step 5), the official
default for the entity's content reference (step 6,
``official_default_for`` — resolved from the startup catalog snapshot alone,
so an entity with no reference, or a reference the snapshot does not hold,
falls through with no diagnostic beyond the resolver's own bounded event),
the terminal fallback seam (step 7), and the truthful placeholder (step 8).
This module exposes the official lookup and the seam
``fallback_for(subject)``, filling the latter from
``gallery-builtin-fallbacks``: the deterministic built-in resolver over the
six committed defaults, or ``None`` (scenes) when no fallback applies.

Every candidate is identity-validated through
``validated_card_identity`` — subject prefix, closed store-extension set, and
the ``world/art/paths.py`` store-root confinement check (symlinks and
out-of-root resolutions refuse the card) — plus file existence. A card that
fails any check is skipped and resolution continues with the next candidate
or the next step; a broken URL is never emitted.

Import discipline: read-only gallery APIs only (``cards_for``, ``record_for``
without ``create``, ``snapshot_for``) — this module names no record class and
performs no write. Duplicate-record consolidation belongs to the writers. It
never imports the generative-transport packages or
``world.art.connectivity``, keeping the connectivity import boundary intact.
"""

from typing import Any

from world.art import gallery_kinds
from world.art.formats import STORE_EXTENSIONS
from world.art.gallery import (
    empty_snapshot,
    cards_for,
    record_for,
    snapshot_for,
)
from world.art.paths import resolved_under_store_root
from world.art.subjects import ArtSubject
from world.observability import log_debug


def validated_card_identity(subject: ArtSubject, card: dict) -> str | None:
    """Return the card's stored identity only when it is presentable.

    Checks, in order: the identity names the subject's own
    ``gallery/<kind>/<subject-key>/`` prefix; its extension is in the closed
    set of every store extension; ``resolved_under_store_root`` confines it
    (rejecting ``..``, symlinks, and out-of-root resolutions); and the
    resolved file exists. ``None`` means "skip this card" — one bounded
    ``gallery_card_skipped`` debug event, never a raise.
    """
    identity = card.get("stored_identity")
    capability = gallery_kinds.capabilities_for(subject.kind.value)
    kind_directory = capability.store_directory if capability.has_gallery else None
    reason = None
    resolved = None
    if kind_directory is None:
        reason = "subject kind has no gallery"
    elif not isinstance(identity, str):
        reason = "identity is not text"
    elif not identity.startswith(f"gallery/{kind_directory}/{subject.key}/"):
        reason = "identity addresses another subject"
    elif _identity_extension(identity) not in STORE_EXTENSIONS:
        reason = "identity extension is not a store extension"
    else:
        resolved = resolved_under_store_root(identity)
        if resolved is None:
            reason = "identity fails store-root confinement"
        elif not resolved.is_file():
            reason = "referenced file is missing"
    if reason is not None:
        log_debug(
            "gallery_card_skipped",
            context={
                "subject": subject.full(),
                "image_id": card.get("image_id"),
                "reason": reason,
            },
        )
        return None
    return identity


def _identity_extension(identity: str) -> str:
    """The identity's store extension, or a sentinel that never matches."""
    dot = identity.rfind(".")
    return identity[dot:] if dot != -1 else ""


def resolve_card(subject: ArtSubject, entity: Any = None) -> dict | None:
    """Resolve the card to display for ``subject`` under ``entity``'s equipment.

    Returns the validated card dict (the tolerant read's stored form) or
    ``None`` when nothing in the gallery resolves — the caller then continues
    the chain at the classic asset record. The same record and the same
    equipment always resolve to the same card; nothing here writes.
    """
    capability = gallery_kinds.capabilities_for(subject.kind.value)
    if not capability.has_gallery:
        return None
    cards = cards_for(subject)
    if capability.supports_bindings:
        snapshot = snapshot_for(entity) if entity is not None else empty_snapshot()
        matched = _binding_candidates(cards, snapshot)
        for card in matched:
            if validated_card_identity(subject, card) is not None:
                return card
    return _default_card(subject, cards)


def _binding_candidates(cards: list[dict], snapshot: dict) -> list[dict]:
    """Matching bound cards, most-specific mask first, newest tie-break.

    A masked slot must equal the computed snapshot value for that slot;
    unmasked slots are don't-cares. An empty snapshot is a legal matcher
    ("wearing nothing on those slots").
    """
    matched = []
    for card in cards:
        binding = card["binding"]
        if binding is None:
            continue
        mask = binding["mask"]
        if all(binding["snapshot"][slot] == snapshot[slot] for slot in mask):
            matched.append(card)
    matched.sort(key=lambda card: (-len(card["binding"]["mask"]), -card["created_at"]))
    return matched


def _default_card(subject: ArtSubject, cards: list[dict]) -> dict | None:
    """The validated card named by ``default_image_id``, or None.

    Consulted by every subject kind (the monster's whole chain, and the
    character's fall-through). An unbound card is legal here — this is the
    ONLY path by which an unbound card is ever displayed.
    """
    record = record_for(subject)
    if record is None:
        return None
    default_image_id = record.db.default_image_id
    if default_image_id is None:
        return None
    for card in cards:
        if card["image_id"] != default_image_id:
            continue
        if validated_card_identity(subject, card) is not None:
            return card
    return None


def fallback_for(subject: ArtSubject, entity=None, *, report: bool = True) -> dict | None:
    """The terminal fallback seam: consulted after the classic asset record.

    Filled by ``gallery-builtin-fallbacks`` with the deterministic built-in
    resolver: declared registry key -> sex/age band -> deterministic
    subject-key hash over the six committed defaults. The presenter passes
    the entity it already resolved; a bare ``fallback_for(subject)`` call
    recovers only a deterministic identification (primary-key path for
    digit-only keys, unique pk-ordered attribute scan otherwise — an
    ambiguous shared stable key recovers no entity, failing closed), and
    scene subjects resolve ``None`` which falls through to the truthful
    placeholder. The resolution returns ``{identity, face_rect, key}`` and
    writes nothing; the returned ``identity`` is a validated ``defaults/``
    branch identity the media route serves (the route refuses to serve
    anything else).

    ``report`` is the observability decision, not a selection decision:
    ``True`` (the terminal-presentation use) emits one ``gallery_fallback_used``
    event naming the subject, kind, and resolved key. The presenter asks for
    ``report=False`` only when it carries the resolution as the decorative
    silhouette reference beside a real portrait — the fallback is not
    presented then, so no use event is reported. Selection is identical
    either way. The event is per presentation, not per entity: every payload
    that presents the silhouette reports its own resolution (a re-presented
    subject reports again), so a reader never infers a deduplicated set.
    """
    from world.art.gallery_fallback import resolve_fallback

    resolution = resolve_fallback(subject, entity=entity)
    if resolution is None:
        return None
    if report:
        from world.observability import log_info

        log_info(
            "gallery_fallback_used",
            context={
                "subject": subject.full(),
                "kind": subject.kind.value,
                "key": resolution["key"],
            },
        )
    return resolution


def official_default_for(subject: ArtSubject, entity: Any = None) -> dict | None:
    """Step 6 of the chain: the mounted catalog's default official image.

    ``resolve_card`` (steps 1-4) and the presenter's classic ``done`` asset
    (step 5) are consulted before this lookup, so a subject with runtime
    artwork keeps presenting it and a catalog default never replaces the
    player's own image. The entity's stored provenance supplies the typed
    content reference (``official_content_reference_for_entity``): no
    reference — every dynamically generated NPC, every imported NPC, every
    monster before the separate species catalog lands, and every entity
    without a named portrait subject — resolves ``None`` here. A reference
    the snapshot does not hold (absent, refused at admission, or removed by
    an artwork update) resolves ``None`` just the same, so a stale directory
    falls through to the remaining chain with no exception, no preference
    deletion, and no acquisition attempt.

    The returned facts are the snapshot's own: the default image's admitted
    root-relative ``identity``, its same-origin
    ``/art/official/<fingerprint>/<identity>`` ``url`` (the fingerprint is the
    restart-scoped cache token, computed once at load and never re-derived
    here), the pixel size the catalog decoded, and the ``face_rect``/``stage``
    it validated at load against those dimensions (declared manifest geometry
    or the fitted default rectangle / identity placement). The presenter
    re-validates that geometry at the payload boundary and owns the wire
    budget, so this step answers from the snapshot alone: no network call, no
    filesystem write, no job enqueue, and no record mutation.

    Imports stay local — like :func:`fallback_for` — so this module keeps its
    read-only, transport-free module-level import surface.
    """
    from world.art import official
    from world.art.official_refs import official_content_reference_for_entity

    reference = official_content_reference_for_entity(entity)
    if reference is None:
        return None
    catalog = official.current_catalog()
    content = catalog.content(reference.kind, reference.key)
    if content is None or content.default_identity is None:
        return None
    image = catalog.entry(content.default_identity)
    if image is None:
        return None
    url = catalog.url_for(image.identity)
    if url is None:
        return None
    return {
        "identity": image.identity,
        "url": url,
        "face_rect": dict(image.face_rect),
        "stage": dict(image.stage),
        "image_size": dict(image.image_size),
    }


__all__ = [
    "fallback_for",
    "official_default_for",
    "resolve_card",
    "validated_card_identity",
]
