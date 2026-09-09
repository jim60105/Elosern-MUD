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

Steps 5-7 (the classic ``done`` asset record, the terminal fallback seam, and
the truthful placeholder) live in the presenter, which owns payload
construction; this module exposes the seam ``fallback_for(subject)`` and
fills it from ``gallery-builtin-fallbacks``: the deterministic built-in
resolver over the six committed defaults, or ``None`` (scenes) when no
fallback applies.

Every candidate is identity-validated through
``validated_card_identity`` — subject prefix, closed store-extension set, and
the ``world/art/paths.py`` store-root confinement check (symlinks and
out-of-root resolutions refuse the card) — plus file existence. A card that
fails any check is skipped and resolution continues with the next candidate
or the next step; a broken URL is never emitted.

Import discipline: read-only gallery APIs only (``cards_for``, ``record_for``
without ``create``, ``snapshot_for``) — this module names no record class and
performs no write of its own (a subject-record consolidation inside the
read path may still retire duplicate rows under the single-writer model). It
never imports the generative-transport packages or
``world.art.connectivity``, keeping the connectivity import boundary intact.
"""

from typing import Any

from world.art.formats import STORE_EXTENSIONS
from world.art.gallery import (
    GALLERY_KIND_DIRECTORIES,
    empty_snapshot,
    cards_for,
    record_for,
    snapshot_for,
)
from world.art.paths import resolved_under_store_root
from world.art.subjects import ArtSubject, ArtSubjectKind
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
    kind_directory = GALLERY_KIND_DIRECTORIES.get(subject.kind)
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
    if subject.kind not in GALLERY_KIND_DIRECTORIES:
        return None
    cards = cards_for(subject)
    if subject.kind is ArtSubjectKind.CHARACTER:
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


def fallback_for(subject: ArtSubject, entity=None) -> dict | None:
    """The terminal fallback seam: consulted after the classic asset record.

    Filled by ``gallery-builtin-fallbacks`` with the deterministic built-in
    resolver: declared registry key -> sex/age band -> deterministic
    subject-key hash over the six committed defaults. The presenter passes
    the entity it already resolved; a bare ``fallback_for(subject)`` call
    recovers only a deterministic identification (primary-key path for
    digit-only keys, unique pk-ordered attribute scan otherwise — an
    ambiguous shared stable key recovers no entity, failing closed), and
    scene subjects resolve ``None`` which falls through to the truthful
    placeholder. Every resolution emits the
    ``gallery_fallback_used`` event naming subject and resolved key and
    writes nothing. The presenter is the seam's only consumer and gives
    whatever it returns the shared default face rectangle unless the seam
    carries one; the returned ``identity`` is a validated ``defaults/``-branch
    identity the media route serves (the route refuses to serve anything
    else).
    """
    from world.art.gallery_fallback import resolve_fallback

    resolution = resolve_fallback(subject, entity=entity)
    if resolution is None:
        return None
    key = resolution.pop("key")
    from world.observability import log_info

    log_info(
        "gallery_fallback_used",
        context={"subject": subject.full(), "kind": subject.kind.value, "key": key},
    )
    return resolution


__all__ = [
    "fallback_for",
    "resolve_card",
    "validated_card_identity",
]
