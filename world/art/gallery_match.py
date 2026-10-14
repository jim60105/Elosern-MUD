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
4. otherwise the entity's personal official selection when one is set and
   resolves inside its own content reference (``official_selection_for`` — the
   player's explicit choice REPLACES the gallery default, and every
   equipment-bound card still outranks it), else the card named by the
   record's ``default_image_id``;

Monster subjects skip steps 1-3 entirely — no equipment snapshot is ever
computed for them and no monster card is ever selected by a binding — so a
monster resolves through its default card alone. An unbound card is eligible
ONLY as the explicit default (step 4); no image the player has not chosen is
ever displayed as a surprise. Scene subjects have no gallery and always
resolve to ``None`` here.

``resolve_display_chain`` returns steps 1-4 as ORDERED SLOTS
(``bound`` | ``personal`` | ``default``) that name each source position and
carry the bounded faults it reached at that position; ``resolve_display`` is
its two-tuple projection (``card`` | ``official`` | ``none``) and
``resolve_card`` the card-only projection of that. The chain's remaining
lookups live in the presenter, which owns payload construction: the classic
``done`` asset record (step 5 — consulted only when no personal official
selection resolved), the official default for the entity's content reference
(step 6, ``official_default_for`` — resolved from the startup catalog snapshot
alone, so an entity with no reference, or a reference the snapshot does not
hold, falls through with no diagnostic beyond the resolver's own bounded
event), the terminal fallback seam (step 7), and the truthful placeholder
(step 8). This module exposes the official lookup and the seam
``fallback_for(subject)``, filling the latter from
``gallery-builtin-fallbacks``: the deterministic built-in resolver over the
six committed defaults, or ``None`` (scenes) when no fallback applies.

A personal official selection that no longer resolves — removed by an artwork
update, refused at admission, or outside the entity's content reference —
resolves ``None`` here and the chain simply continues; nothing deletes the
preference, writes a file, or enqueues a job.

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

from dataclasses import dataclass
from typing import Any

from world.art import descriptors, gallery_kinds
from world.art.formats import STORE_EXTENSIONS
from world.art.gallery import (
    empty_snapshot,
    cards_for,
    official_preferences_for,
    record_for,
    snapshot_for,
)
from world.art.paths import resolved_under_store_root
from world.art.subjects import ArtSubject
from world.observability import log_debug


@dataclass(frozen=True)
class ChainSlot:
    """One ordered source position of the equipment-to-fallback chain.

    ``layer`` names the position (``bound`` | ``personal`` | ``default``);
    ``source_identity`` is the bounded identity that position's canonical
    source id is built from (a card's image id, or the official identity a
    personal selection names), and is ``None`` only when the position carries
    no identity at all. ``facts`` is the resolving source's read-only facts
    (the tolerant card dict, or the official layer's admitted-and-resolved
    facts) and is ``None`` exactly when the position resolved nothing.
    ``faults`` holds the bounded reasons that belong at this position BEFORE
    its candidate: the reason of an explicit source that could not resolve, or
    the retained metadata fault of the very image the position resolved.
    """

    layer: str
    source_identity: str | None = None
    facts: dict | None = None
    faults: tuple[str, ...] = ()


@dataclass(frozen=True)
class DisplayChain:
    """The chain's steps 1-4: their ordered slots plus the subject's own card fact.

    ``has_cards`` reports whether the subject's record carries at least one
    valid card — a completed generation of its own — beside the slots, so a
    consumer can state the subject's recorded generation truth without reading
    the record a second time.
    """

    slots: tuple[ChainSlot, ...]
    has_cards: bool


def card_identity_resolution(subject: ArtSubject, card: dict) -> tuple[str | None, str | None]:
    """Resolve the card's stored identity to ``(identity, fault_reason)``.

    Exactly one side of the pair is set. The identity is returned only when
    the card is presentable, checked in order: the identity names the
    subject's own ``gallery/<kind>/<subject-key>/`` prefix; its extension is
    in the closed set of every store extension; ``resolved_under_store_root``
    confines it (rejecting ``..``, symlinks, and out-of-root resolutions); and
    the resolved file exists.

    A refusal returns the canonical bounded fault reason of the check that
    refused it — ''source_rejected'' for a structurally unusable identity and
    ''generated_output_missing'' for one whose readable output is gone — so a
    caller can carry the exact requested card forward as an attributed known
    fault instead of silently dropping it, and emits the same one bounded
    ``gallery_card_skipped`` debug event as before. Never a raise.
    """
    identity = card.get("stored_identity")
    capability = gallery_kinds.capabilities_for(subject.kind.value)
    kind_directory = capability.store_directory if capability.has_gallery else None
    reason = None
    fault = None
    resolved = None
    if kind_directory is None:
        reason = "subject kind has no gallery"
        fault = descriptors.REASON_SOURCE_UNAVAILABLE
    elif not isinstance(identity, str):
        reason = "identity is not text"
        fault = descriptors.REASON_SOURCE_REJECTED
    elif not identity.startswith(f"gallery/{kind_directory}/{subject.key}/"):
        reason = "identity addresses another subject"
        fault = descriptors.REASON_SOURCE_REJECTED
    elif _identity_extension(identity) not in STORE_EXTENSIONS:
        reason = "identity extension is not a store extension"
        fault = descriptors.REASON_SOURCE_REJECTED
    else:
        resolved = resolved_under_store_root(identity)
        if resolved is None:
            reason = "identity fails store-root confinement"
            fault = descriptors.REASON_SOURCE_REJECTED
        elif not resolved.is_file():
            reason = "referenced file is missing"
            fault = descriptors.REASON_GENERATED_OUTPUT_MISSING
    if reason is not None:
        log_debug(
            "gallery_card_skipped",
            context={
                "subject": subject.full(),
                "image_id": card.get("image_id"),
                "reason": reason,
            },
        )
        return None, fault
    return identity, None


def validated_card_identity(subject: ArtSubject, card: dict) -> str | None:
    """The card's stored identity only when it is presentable, else ``None``.

    The identity-only projection of :func:`card_identity_resolution`, for the
    callers that skip an unusable card instead of carrying it as a fault.
    """
    return card_identity_resolution(subject, card)[0]


def _identity_extension(identity: str) -> str:
    """The identity's store extension, or a sentinel that never matches."""
    dot = identity.rfind(".")
    return identity[dot:] if dot != -1 else ""


def resolve_display(
    subject: ArtSubject, entity: Any = None
) -> tuple[str, dict | None]:
    """The chain's steps 1-4 as one discriminated resolution.

    ``("card", card)`` when an equipment-bound card matched or the record's
    ``default_image_id`` resolved, ``("official", facts)`` when the personal
    official selection resolves at step 4 (it replaces the gallery default and
    stays behind every equipment-bound card), ``("none", None)`` when nothing
    in steps 1-4 resolved. A pure function of stored state plus the startup
    snapshot: the same record, preference, and equipment always resolve the
    same way, and nothing here writes.

    The two-tuple projection of :func:`resolve_display_chain`, which reports
    WHICH source position resolved and the bounded faults reached on the way;
    this form answers only which of the three shapes a caller builds.
    """
    for slot in resolve_display_chain(subject, entity).slots:
        if slot.facts is None:
            continue
        if slot.layer == "personal":
            return ("official", slot.facts)
        return ("card", slot.facts)
    return ("none", None)


def resolve_display_chain(subject: ArtSubject, entity: Any = None) -> DisplayChain:
    """The chain's steps 1-4 as their ordered slots, faults included.

    The slot order is the chain's precedence, independent of any array index:
    the equipment-bound card (steps 1-3), the personal official selection
    (step 4's first half), then the card named by the record's
    ``default_image_id`` (step 4's other half). The walk stops at the FIRST
    position that resolves a presentable source, but it never drops a fault: an
    explicit stored source that cannot resolve — a retained personal selection
    or a named default card — is reported as a facts-less slot carrying its
    bounded reason, BEFORE the substitute that follows it, so a consumer can
    attribute the failure to the exact position that failed. An unusable
    equipment-bound candidate is skipped operationally and contributes nothing:
    it is an unselected sibling, not a displayed source.

    A step-4 personal selection that resolves also carries the retained
    metadata fault of the very image it resolved (the startup catalog's own
    fact, never a re-derived one), so a degraded manifest is visible while its
    valid bytes still present. Scenes and every other gallery-less kind return
    no slots at all.
    """
    capability = gallery_kinds.capabilities_for(subject.kind.value)
    if not capability.has_gallery:
        return DisplayChain((), False)
    cards = cards_for(subject)
    slots: list[ChainSlot] = []
    if capability.supports_bindings:
        bound = _selected_bound_card(cards, subject, entity)
        if bound is not None:
            return DisplayChain(
                (ChainSlot("bound", str(bound["image_id"]), bound),),
                bool(cards),
            )
    selection = official_selection_slot(subject, entity)
    if selection.facts is not None:
        return DisplayChain((selection,), bool(cards))
    if selection.faults:
        slots.append(selection)
    default = _default_card_slot(subject, cards)
    if default.facts is not None:
        return DisplayChain((*slots, default), bool(cards))
    if default.faults:
        slots.append(default)
    return DisplayChain(tuple(slots), bool(cards))


def resolve_card(subject: ArtSubject, entity: Any = None) -> dict | None:
    """Resolve the CARD to display for ``subject`` under ``entity``'s equipment.

    The card-only projection of :func:`resolve_display`: the validated card
    dict (the tolerant read's stored form) or ``None`` when no card resolves —
    the caller then continues the chain at the classic asset record. A
    resolving personal official selection is step 4's other half, so it makes
    this return ``None``; the presenter's official branch owns that payload.
    """
    outcome, facts = resolve_display(subject, entity)
    return facts if outcome == "card" else None


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


def _selected_bound_card(
    cards: list[dict], subject: ArtSubject, entity: Any
) -> dict | None:
    """The card steps 1-3 select, or ``None`` when no bound card matches.

    The identity-validated binding-step projection: the matching bound cards in
    precedence order (most specific mask first, newest ``created_at``
    tie-break), the first one whose stored identity is presentable. An unusable
    candidate is skipped, exactly as the chain always skipped it.
    """
    snapshot = snapshot_for(entity) if entity is not None else empty_snapshot()
    for card in _binding_candidates(cards, snapshot):
        if validated_card_identity(subject, card) is not None:
            return card
    return None


def _default_card_slot(subject: ArtSubject, cards: list[dict]) -> ChainSlot:
    """The record's explicit default card as a chain slot.

    Consulted by every subject kind (the monster's whole chain, and the
    character's fall-through). An unbound card is legal here — this is the
    ONLY path by which an unbound card is ever displayed. ``facts`` is the
    presentable card ``default_image_id`` names; ``faults`` carries the bounded
    reason when the record NAMES a default that cannot be presented (a refused
    or vanished output, or an id no card of the record carries). A record that
    sets no default contributes an EMPTY slot: an unset preference is not a
    failure.
    """
    record = record_for(subject)
    if record is None:
        return ChainSlot("default")
    default_image_id = record.db.default_image_id
    if default_image_id is None:
        return ChainSlot("default")
    for card in cards:
        if card["image_id"] != default_image_id:
            continue
        _, fault = card_identity_resolution(subject, card)
        if fault is None:
            return ChainSlot("default", str(card["image_id"]), card)
        return ChainSlot("default", str(card["image_id"]), None, (fault,))
    return ChainSlot(
        "default",
        default_image_id if isinstance(default_image_id, str) else None,
        None,
        (descriptors.REASON_EXPLICIT_REFERENCE_MISSING,),
    )


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


def _official_facts_for(reference, identity: str, catalog) -> dict | None:
    """The catalog's own read-only facts for one admitted image, or ``None``.

    The identity must be an admitted image of the SUPPLIED content reference: a
    catalog identity alone is never enough, because a subject may present only
    what its own stored reference declares. The returned facts are the
    snapshot's own — the admitted root-relative ``identity``, its same-origin
    fingerprinted ``url``, the restart-scoped content ``fingerprint`` that is
    this resource's own version, the geometry it validated at load, and the
    pixel size it decoded — so a caller re-validates personal overrides against
    exactly those dimensions.
    """
    if reference is None:
        return None
    content = catalog.content(reference.kind, reference.key)
    if content is None or identity not in content.images:
        return None
    image = catalog.entry(identity)
    if image is None:
        return None
    url = catalog.url_for(image.identity)
    if url is None:
        return None
    return {
        "identity": image.identity,
        "fingerprint": image.fingerprint,
        "url": url,
        "face_rect": dict(image.face_rect),
        "stage": dict(image.stage),
        "image_size": dict(image.image_size),
    }


def _official_metadata_faults(identity: str) -> tuple[str, ...]:
    """The retained metadata fault of one exact admitted image, as a reason tuple.

    Identity-scoped on purpose: a fault of an unselected refused sibling is an
    operational diagnostic and never accompanies this image's candidate.
    """
    from world.art import official

    fault = official.current_catalog().fault_for(identity)
    return (fault.reason,) if fault is not None else ()


def _official_source_faults(reference, catalog) -> tuple[str, ...]:
    """The pre-substitute startup faults retained for one official content source.

    Only facts scoped to the reference itself: an unavailable content directory
    or a manifest-declared default that a deterministic substitute replaced.
    Per-image metadata faults are read through :func:`_official_metadata_faults`
    so only the image a caller actually resolved can carry one.
    """
    from world.art import official

    return tuple(
        fault.reason
        for fault in catalog.source_faults(reference.kind, reference.key)
        if fault.scope in (official.SOURCE_SCOPE_DEFAULT, official.SOURCE_SCOPE_SOURCE)
    )


def official_selection_slot(subject: ArtSubject, entity: Any = None) -> ChainSlot:
    """Step 4's first half as a chain slot: the subject's personal official selection.

    The retained preference resolves only when it names an image the startup
    snapshot admits INSIDE the entity's own official content reference; that
    slot carries the catalog's own facts, plus the retained metadata fault of
    the very image it resolved. An unset selection contributes an EMPTY slot —
    an unset preference is not a failure. A selection that IS set and cannot
    resolve contributes a bounded fault instead (a refused identity, an
    unavailable content directory, or a selection the snapshot no longer
    holds), while the preference stays stored: nothing is deleted, repaired, or
    acquired, and the chain continues to the remaining candidates.

    Imports stay local — like :func:`fallback_for` — so this module keeps its
    read-only, transport-free module-level import surface.
    """
    from world.art import official
    from world.art.official_refs import official_content_reference_for_entity

    selection = official_preferences_for(subject, entity=entity).selection
    if selection is None:
        return ChainSlot("personal")
    reference = official_content_reference_for_entity(entity)
    catalog = official.current_catalog()
    facts = _official_facts_for(reference, selection, catalog)
    if facts is not None:
        return ChainSlot(
            "personal", selection, facts, _official_metadata_faults(selection)
        )
    reason = descriptors.REASON_EXPLICIT_REFERENCE_MISSING
    if catalog.refusal_reason(selection) is not None:
        reason = descriptors.REASON_SOURCE_REJECTED
    elif reference is not None:
        reasons = _official_source_faults(reference, catalog)
        if reasons:
            reason = reasons[0]
    return ChainSlot("personal", selection, None, (reason,))


def official_selection_for(subject: ArtSubject, entity: Any = None) -> dict | None:
    """Step 4's first half: the subject's personal official selection, or ``None``.

    The facts-only projection of :func:`official_selection_slot`: a caller that
    only builds a payload asks whether the selection resolves, while the
    enumeration reads the same slot for its source position and its faults.
    """
    return official_selection_slot(subject, entity).facts


def official_default_slot(subject: ArtSubject, entity: Any = None) -> ChainSlot:
    """Step 6 as a chain slot: the entity's content reference and its default image.

    ``source_identity`` is the entity's official content reference as
    ``"<content-kind>/<content-key>"`` — the identity its candidate and its
    faults share — and ``facts`` is the snapshot's admitted default image
    inside that reference. ``faults`` carries the retained startup facts that
    precede the candidate: a source-scoped unavailability or a
    manifest-declared default that a deterministic substitute replaced, then
    the metadata fault of the very image the snapshot admits as the default.

    An entity declaring no reference contributes an EMPTY slot (a
    never-configured source is not a failure), and a reference the snapshot
    does not hold contributes no fault either: the mounted catalog simply has
    nothing for it, exactly as it has nothing for a subject that never had
    artwork. ``resolve_card`` (steps 1-4) and the presenter's classic ``done``
    asset (step 5) are consulted before this step, so a subject with runtime
    artwork keeps presenting it and a catalog default never replaces the
    player's own image.

    Imports stay local — like :func:`fallback_for` — so this module keeps its
    read-only, transport-free module-level import surface.
    """
    from world.art import official
    from world.art.official_refs import official_content_reference_for_entity

    reference = official_content_reference_for_entity(entity)
    if reference is None:
        return ChainSlot("official")
    source_identity = f"{reference.kind}/{reference.key}"
    catalog = official.current_catalog()
    faults = _official_source_faults(reference, catalog)
    content = catalog.content(reference.kind, reference.key)
    if content is None or content.default_identity is None:
        return ChainSlot("official", source_identity, None, faults)
    facts = _official_facts_for(reference, content.default_identity, catalog)
    if facts is None:
        return ChainSlot("official", source_identity, None, faults)
    return ChainSlot(
        "official",
        source_identity,
        facts,
        (*faults, *_official_metadata_faults(content.default_identity)),
    )


def official_default_for(subject: ArtSubject, entity: Any = None) -> dict | None:
    """Step 6 of the chain: the mounted catalog's default official image, or ``None``.

    The facts-only projection of :func:`official_default_slot`, so the
    availability guard the art service reads and the presentation the chain
    builds answer from one implementation. The returned facts are the
    snapshot's own: the default image's admitted root-relative ``identity``,
    its same-origin ``/art/official/<fingerprint>/<identity>`` ``url`` (the
    fingerprint is the restart-scoped cache token, computed once at load and
    never re-derived here), the pixel size the catalog decoded, and the
    ``face_rect``/``stage`` it validated at load. Nothing here calls the
    network, writes a file, enqueues a job, or mutates a record.
    """
    return official_default_slot(subject, entity).facts


__all__ = [
    "ChainSlot",
    "DisplayChain",
    "fallback_for",
    "official_default_for",
    "official_default_slot",
    "official_selection_for",
    "official_selection_slot",
    "resolve_card",
    "resolve_display",
    "resolve_display_chain",
    "validated_card_identity",
]
