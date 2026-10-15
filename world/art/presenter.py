"""Read-only resolution primitives for the art store (design D8).

The presenter resolves a validated subject to its status, same-origin media
URL, aspect, and alternative text, or to a truthful placeholder kind/label.
ONE canonical enumerator owns the portrait source policy: the ordered chain of
the equipment-bound card, the personal official selection, the record's
default card, the classic ``done`` asset record, the mounted catalog's
official default for the entity's content reference, and the authoritative
alpha terminal. ``_enumerate_portrait`` walks that chain exactly once and
projects it as the canonical artwork descriptor
(``describe_portrait``/``describe_entity``, using the frozen
``world.art.descriptors`` vocabulary with each position's stable source id and
rank and every reached fault at its own position). The portrait wire cut over
to the canonical descriptor (change ``unified-portrait-image-contract``), so no
portrait flat projection exists any more: a portrait consumer reads
``describe_entity``/``describe_portrait`` and the shipped serializers project
the descriptor.

``describe_scene`` owns the SCENE source policy with the same discipline: one
read-only walk of the authored per-room operator override, the scene
archetype's own generated artwork, the optional operator scene default, the
required bundled type illustration and the distinct declared terminal image,
projected as the canonical descriptor with each position's own stable source
id and rank, every reached fault at its position, the retained startup facts of
each operator source, the scene's independent recorded generation truth and the
retention authorizations that keep a still-applicable known-good image on
screen. A scene whose authored metadata cannot be honored states that
configuration failure explicitly and falls back to the declared town terminal —
never an invented or silently missing scene, and never a synthetic pending
generation.

``describe_dream_scene`` owns the DREAM stage's chain (change
``unified-dream-rendering``) with the same vocabulary: the dream is not an
explorable archetype, so its positions are the optional operator-preferred
official identity, the required bundled ``dream_throne`` illustration and the
distinct declared town terminal, with null generation facts and no retention.
The dream's narrative read model reads that descriptor instead of resolving a
raw artwork URL of its own.

Every canonical resource carries the closed origin vocabulary: ``runtime`` for
the scene's own generated output, ``official`` for an operator catalog image,
``bundled_official`` for a committed bundled illustration and ``silhouette``
for the built-in portrait alpha terminal. An official default is presented only
when the catalog's URL fits ``MAX_PORTRAIT_MEDIA_URL``, the shared wire
ceiling: an official identity embeds an operator-chosen filename, so an
over-budget URL falls through exactly like an absent reference instead of
failing the whole panel.
It never exposes ``out_path``, the store root, or any absolute filesystem path.
Change 23f's browser panel consumes these primitives; this change owns them.
"""

from dataclasses import dataclass

from world.observability import log_warn

from world.art import descriptors
from world.art.formats import STORE_EXTENSIONS
from world.art.gallery import (
    DEFAULT_FACE_RECT,
    GalleryRecordError,
    OfficialPreferences,
    default_face_rect,
    official_preferences_for,
    validate_face_rect,
    validate_stage,
    identity_stage,
)
from world.art.gallery_fallback import fallback_identity_and_rect, fallback_key_for_entity
from world.art.gallery_kinds import capabilities_for
from world.art.gallery_match import (
    fallback_for,
    official_default_slot,
    resolve_display_chain,
)
from world.art.paths import resolved_under_store_root
from world.art.queue import pending_gallery_jobs, record_key
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import (
    ArtSubject,
    ArtSubjectError,
    ArtSubjectKind,
    character_ages,
    character_subject_for,
    monster_subject_for,
)

# The CLOSED portrait-origin discriminator vocabulary (art-gallery-fallback
# owns it here): ``runtime`` for a card or classic image the payload itself
# carries, ``official`` for the mounted catalog's read-only default for the
# entity's content reference, ``silhouette`` when only the built-in fallback
# resolved, and ``placeholder`` when nothing did. The origin is computed from
# the branch that produced the payload, never inferred from the presence of a
# URL; `official-art-resolution-contracts` extends the vocabulary with
# ``official`` exactly here, and both wire validators mirror the same value.
ORIGIN_RUNTIME = "runtime"
ORIGIN_OFFICIAL = "official"
ORIGIN_SILHOUETTE = "silhouette"
ORIGIN_PLACEHOLDER = "placeholder"

# The declared town terminal: the closed terminal vocabulary's town member
# (``world.art.scene_definitions.TERMINAL_SCENE_KEYS``), and the permitted
# fallback a scene whose authored metadata cannot be honored is shown with —
# never a normal archetype's own declared terminal.
TOWN_TERMINAL_KEY = "city_street"

# The wire ceiling every portrait payload URL must fit: the art-panel and
# roster validators both bound a payload URL at this many code points. Card,
# classic, and fallback identities are bounded by construction (the shared
# subject-key contract), but an official identity embeds an
# operator-chosen filename, so the official step presents a URL only inside
# this ceiling and otherwise falls through. Pinned equal to the presentation
# layer's ``MAX_MEDIA_URL`` by ``web.webclient.presentation.tests.test_art_panel``.
MAX_PORTRAIT_MEDIA_URL = 256

# The fixed aspect ratio of every gallery card / fallback image payload:
# portrait geometry is a presenter-side constant (cards store no ratio),
# matching the wire validator's portrait aspect.
GALLERY_ASPECT_RATIO = "3:4"


def _record_for(subject: ArtSubject) -> ArtAssetRecord | None:
    return ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()


def media_url_for(identity: str) -> str:
    """Build the same-origin media URL for a validated stored identity."""
    return f"/art/{identity}"


def _validated_output_identity(subject: ArtSubject, identity: str | None) -> str | None:
    """Return a presentable identity only when its expected file still exists.

    The STORED identity is validated against the subject's directory/key
    shape and the closed set of ALL store extensions — never equality with
    the currently configured ``expected_output_identity`` — so a store
    mid-way through a format switch keeps presenting every existing asset
    until that subject is regenerated under the new format.
    """
    if not isinstance(identity, str) or not identity:
        return None
    expected_prefix = f"{_subject_directory(subject)}/"
    stem = f"{subject.key}."
    if not identity.startswith(expected_prefix) or not identity[len(expected_prefix):].startswith(stem):
        return None
    extension = identity[len(expected_prefix) + len(stem) - 1:]
    if extension.lower() not in STORE_EXTENSIONS:
        return None
    resolved = resolved_under_store_root(identity)
    if resolved is None or not resolved.is_file():
        return None
    return identity


def _subject_directory(subject: ArtSubject) -> str:
    """The store directory a subject's identity must live in."""
    if subject.kind is ArtSubjectKind.SCENE:
        return "scene"
    if subject.kind is ArtSubjectKind.MONSTER:
        return "portrait/monster"
    return "portrait/character"


@dataclass(frozen=True)
class _PortraitAttempt:
    """One ordered canonical attempt of a subject's portrait chain.

    A candidate carries the source position it occupies and its canonical
    resource (identity, version, same-origin URL, authored origin and validated
    geometry); a fault carries only that position and its bounded reason, never
    a URL.
    """

    source_id: str
    rank: int
    resource: dict | None = None
    fault: str | None = None


@dataclass(frozen=True)
class _PortraitEnumeration:
    """One subject's canonical descriptor plus the facts its flat payload needs."""

    descriptor: dict
    record: ArtAssetRecord | None
    attempt: _PortraitAttempt | None
    silhouette: dict | None


def _slot_source(layer: str, source_identity: str | None) -> tuple[str, int]:
    """The canonical source id and rank of one gallery chain slot position."""
    identity = source_identity or ""
    if layer == "bound":
        return descriptors.portrait_bound_source_id(identity), descriptors.PORTRAIT_RANK_BOUND
    if layer == "personal":
        return descriptors.portrait_personal_source_id(identity), descriptors.PORTRAIT_RANK_PERSONAL
    if layer == "official":
        return descriptors.portrait_official_source_id(identity), descriptors.PORTRAIT_RANK_OFFICIAL
    return descriptors.portrait_default_source_id(identity), descriptors.PORTRAIT_RANK_DEFAULT


def _card_geometry(subject: ArtSubject, card: dict) -> dict:
    """The validated canonical geometry of one resolved card.

    The ONE place a card's presentation geometry is validated, so the canonical
    descriptor and the flat payload can never disagree about it. A stored
    rectangle or placement triple that fails validation degrades to the
    fitted/shared default or identity placement with exactly one bounded
    diagnostic — never a failed payload, and never a repaired record.
    """
    try:
        face_rect = validate_face_rect(card["face_rect"], image_size=card.get("image_size"))
    except GalleryRecordError:  # observability: ignore R2: malformed rect degrades per contract; payload must never fail
        log_warn("art_face_rect_invalid", context={"subject": subject.full()})
        face_rect = default_face_rect(card["image_size"]) if card.get("image_size") else dict(DEFAULT_FACE_RECT)
    try:
        stage = validate_stage(card.get("stage"))
    except GalleryRecordError:  # observability: ignore R2: malformed placement degrades with its bounded diagnostic
        log_warn("art_stage_invalid", context={"subject": subject.full(), "image_id": card.get("image_id")})
        stage = identity_stage()
    image_size = card.get("image_size")
    return descriptors.geometry(
        image_size=descriptors.image_size_payload(**image_size) if image_size else None,
        face_rect=face_rect,
        stage=stage,
        aspect_ratio=GALLERY_ASPECT_RATIO,
    )


def _official_geometry(
    subject: ArtSubject, official: dict, preferences: OfficialPreferences
) -> dict:
    """The validated canonical geometry of one resolved official image.

    The subject's own geometry override for this identity takes precedence
    component by component, read from the caller's single tolerant preference
    snapshot; a stored rectangle the CURRENT bytes invalidate degrades to the
    catalog's metadata-or-fitted rectangle with ONE bounded
    ``art_official_override_invalid`` diagnostic, and the stored preference
    itself is retained because this builder only ever reads it. The catalog's
    geometry is then re-validated exactly as a stored card's is, so neither a
    snapshot that cannot have come from the catalog's own admission nor
    replaced bytes can ship unvalidated geometry.
    """
    image_size = official.get("image_size")
    face_rect = official["face_rect"]
    stage = official["stage"]
    override = preferences.geometry.get(official["identity"])
    if override is not None and "face_rect" in override:
        try:
            face_rect = validate_face_rect(override["face_rect"], image_size=image_size)
        except GalleryRecordError:  # observability: ignore R2: the retained preference degrades to the catalog's geometry with the bounded diagnostic below
            log_warn(
                "art_official_override_invalid",
                context={
                    "subject": subject.full(),
                    "identity": official.get("identity"),
                    "component": "face_rect",
                },
            )
    if override is not None and "stage" in override:
        stage = override["stage"]
    try:
        face_rect = validate_face_rect(face_rect, image_size=image_size)
    except GalleryRecordError:  # observability: ignore R2: malformed rect degrades per contract; payload must never fail
        log_warn("art_face_rect_invalid", context={"subject": subject.full()})
        face_rect = default_face_rect(image_size) if image_size else dict(DEFAULT_FACE_RECT)
    try:
        stage = validate_stage(stage)
    except GalleryRecordError:  # observability: ignore R2: malformed placement degrades with its bounded diagnostic
        log_warn(
            "art_stage_invalid",
            context={"subject": subject.full(), "identity": official.get("identity")},
        )
        stage = identity_stage()
    return descriptors.geometry(
        image_size=descriptors.image_size_payload(**image_size) if image_size else None,
        face_rect=face_rect,
        stage=stage,
        aspect_ratio=GALLERY_ASPECT_RATIO,
    )


def _card_attempt(subject: ArtSubject, slot) -> _PortraitAttempt:
    """One resolved gallery chain slot as a canonical runtime candidate."""
    card = slot.facts
    identity = card["stored_identity"]
    source_id, rank = _slot_source(slot.layer, slot.source_identity)
    return _PortraitAttempt(
        source_id,
        rank,
        descriptors.resource(
            identity,
            descriptors.identity_version(identity),
            media_url_for(identity),
            descriptors.ORIGIN_RUNTIME,
            geometry_payload=_card_geometry(subject, card),
        ),
    )


def _personal_attempt(subject: ArtSubject, slot, entity) -> _PortraitAttempt:
    """One resolved personal official selection as a canonical official candidate.

    The caller's single tolerant preference snapshot supplies the subject's
    geometry override, so a selection presentation performs exactly two
    preference reads — the chain's step-4 read and this override read — and
    corrupt stored state is reported once per read, the same discipline the
    tolerant card read follows.
    """
    facts = slot.facts
    source_id, rank = _slot_source(slot.layer, slot.source_identity)
    return _PortraitAttempt(
        source_id,
        rank,
        descriptors.resource(
            facts["identity"],
            facts["fingerprint"],
            facts["url"],
            descriptors.ORIGIN_OFFICIAL,
            geometry_payload=_official_geometry(
                subject, facts, official_preferences_for(subject, entity=entity)
            ),
        ),
    )


def _classic_attempts(
    subject: ArtSubject, record: ArtAssetRecord | None
) -> tuple[list[_PortraitAttempt], _PortraitAttempt | None]:
    """The classic ``done`` asset record's attempts: its bounded fault or its candidate.

    The record's own validated output identity is the whole original (the one
    digest convention of the classic layer is its identity plus the generation
    token that published it), so a vanished output contributes a
    generated-output-missing fault at this exact position and a recorded
    failure a generation-failed one — while a record that is merely absent,
    queued, or claimed contributes nothing at all.
    """
    source_id = descriptors.portrait_classic_source_id(subject.full())
    rank = descriptors.PORTRAIT_RANK_CLASSIC
    if record is None:
        return [], None
    status = record.db.status
    if status == ArtAssetStatus.DONE:
        identity = _validated_output_identity(subject, record.db.output_identity)
        if identity is None:
            log_warn("art_asset_output_missing", context={"subject": subject.full()})
            return [_PortraitAttempt(source_id, rank, fault=descriptors.REASON_GENERATED_OUTPUT_MISSING)], None
        return [], _PortraitAttempt(
            source_id,
            rank,
            descriptors.resource(
                identity,
                _published_output_version(record, identity),
                media_url_for(identity),
                descriptors.ORIGIN_RUNTIME,
                geometry_payload=descriptors.geometry(
                    face_rect=dict(DEFAULT_FACE_RECT),
                    stage=identity_stage(),
                    aspect_ratio=record.db.aspect_ratio,
                ),
            ),
        )
    if status == ArtAssetStatus.FAILED:
        return [_PortraitAttempt(source_id, rank, fault=descriptors.REASON_GENERATION_FAILED)], None
    return [], None


def _generation_facts(
    subject: ArtSubject,
    record: ArtAssetRecord | None,
    has_cards: bool,
    gallery_failed: bool,
) -> tuple[str, str]:
    """The subject's recorded generation key and state, independent of any candidate.

    A pure read of stored state: a live gallery request or a claimed/pending
    classic record is ``pending``; a recorded failure (the gallery record's
    retained error, the classic record's own error code, or a failed classic
    record) is ``failed``; a stored card or a ``done`` classic record is
    ``done``; anything else is factually ``missing``. Nothing here erases a
    recorded failure or invents an active job, so a subject whose generation is
    deliberately disabled and unstarted claims nothing, while a finished
    official image can never complete a pending or failed generation of the
    subject's own.
    """
    pending = bool(pending_gallery_jobs(subject)) if capabilities_for(
        subject.kind.value
    ).has_gallery else False
    recorded = descriptors.normalize_generation_state(
        record.db.status if record is not None else None
    )
    if pending or recorded == descriptors.GENERATION_PENDING:
        state = descriptors.GENERATION_PENDING
    elif (
        gallery_failed
        or (record is not None and record.db.last_error_code)
        or recorded == descriptors.GENERATION_FAILED
    ):
        state = descriptors.GENERATION_FAILED
    elif has_cards or recorded == descriptors.GENERATION_DONE:
        state = descriptors.GENERATION_DONE
    else:
        state = descriptors.GENERATION_MISSING
    return subject.full(), state


def _alpha_terminal(fallback) -> dict | None:
    """The resolved seam's alpha-mask terminal for a descriptor, or ``None``.

    The authoritative deterministic alpha selector's resolution at its own
    rank, carrying the committed identity's version and rectangle: the same
    terminal vocabulary the gallery preview uses, so the portrait and gallery
    surfaces name one non-competing fallback.
    """
    if not isinstance(fallback, dict):
        return None
    identity, key = fallback.get("identity"), fallback.get("key")
    if not isinstance(identity, str) or not identity or not isinstance(key, str) or not key:
        return None
    try:
        rect = validate_face_rect(fallback.get("face_rect"))
    except GalleryRecordError:  # observability: ignore R2: the seam's rectangle defaults per contract
        rect = dict(DEFAULT_FACE_RECT)
    return descriptors.terminal(
        descriptors.TERMINAL_ALPHA_MASK,
        descriptors.portrait_alpha_source_id(key),
        descriptors.PORTRAIT_RANK_ALPHA,
        descriptors.resource(
            identity,
            descriptors.identity_version(identity),
            media_url_for(identity),
            descriptors.ORIGIN_SILHOUETTE,
            geometry_payload=descriptors.geometry(
                face_rect=rect, aspect_ratio=GALLERY_ASPECT_RATIO
            ),
        ),
    )


def _enumerate_portrait(subject: ArtSubject, entity=None) -> _PortraitEnumeration:
    """Walk one subject's portrait chain ONCE and project it canonically.

    The one production selector: the ordered attempt list keeps every reached
    fault at its own source position (an explicit selection or default that
    cannot resolve precedes the substitute that follows it) and stops at the
    first resolving candidate, so a healthy earlier candidate prevents later
    fault accumulation. The canonical descriptor and the current flat payload
    are both projections of THIS result, so selection can never disagree
    between them. A read-only walk: nothing here creates a record, enqueues a
    job, repairs geometry, or touches a file, and the terminal seam is
    consulted exactly once with its report decided by whether a real image
    resolved.
    """
    record = _record_for(subject)
    attempts: list[_PortraitAttempt] = []
    candidate: _PortraitAttempt | None = None
    chain = resolve_display_chain(subject, entity)
    for slot in chain.slots:
        source_id, rank = _slot_source(slot.layer, slot.source_identity)
        for identity, reason in slot.faults:
            # A fault names its OWN failed source identity: two facts of one
            # layer (a replaced manifest default and a degraded image) must
            # never collide on one source id at one rank.
            attempts.append(
                _PortraitAttempt(_slot_source(slot.layer, identity)[0], rank, fault=reason)
            )
        if slot.facts is None:
            continue
        # An official identity embeds an operator-chosen filename, so a URL
        # outside the shared wire budget falls through exactly like an absent
        # reference: one oversized filename must never fail the panel.
        if slot.layer == "personal" and len(slot.facts["url"]) > MAX_PORTRAIT_MEDIA_URL:
            log_warn(
                "art_official_url_over_wire_budget",
                context={"subject": subject.full(), "identity": slot.facts["identity"]},
            )
            attempts.append(
                _PortraitAttempt(source_id, rank, fault=descriptors.REASON_CONFIGURATION_INVALID)
            )
            continue
        candidate = (
            _personal_attempt(subject, slot, entity)
            if slot.layer == "personal"
            else _card_attempt(subject, slot)
        )
        attempts.append(candidate)
        break
    if candidate is None:
        classic_faults, classic = _classic_attempts(subject, record)
        attempts.extend(classic_faults)
        if classic is not None:
            candidate = classic
            attempts.append(classic)
    if candidate is None:
        official = official_default_slot(subject, entity)
        if official.source_identity is not None:
            source_id, rank = _slot_source("official", official.source_identity)
            faults: list[_PortraitAttempt] = []
            for identity, reason in official.faults:
                faults.append(
                    _PortraitAttempt(
                        _slot_source("official", identity)[0], rank, fault=reason
                    )
                )
            if official.facts is not None:
                if len(official.facts["url"]) <= MAX_PORTRAIT_MEDIA_URL:
                    candidate = _PortraitAttempt(
                        source_id,
                        rank,
                        descriptors.resource(
                            official.facts["identity"],
                            official.facts["fingerprint"],
                            official.facts["url"],
                            descriptors.ORIGIN_OFFICIAL,
                            geometry_payload=_official_geometry(
                                subject,
                                official.facts,
                                official_preferences_for(subject, entity=entity),
                            ),
                        ),
                    )
                else:
                    log_warn(
                        "art_official_url_over_wire_budget",
                        context={
                            "subject": subject.full(),
                            "identity": official.facts["identity"],
                        },
                    )
                    faults.append(
                        _PortraitAttempt(
                            source_id, rank, fault=descriptors.REASON_CONFIGURATION_INVALID
                        )
                    )
            attempts.extend(faults)
            if candidate is not None:
                attempts.append(candidate)
    # The already-resolved entity rides along so the seam reads its sex,
    # apparent age, and registry provenance directly
    # (gallery-builtin-fallbacks). A resolution here IS the presented figure
    # exactly when no real candidate resolved, so that is the report.
    fallback = fallback_for(subject, entity=entity, report=(candidate is None))
    generation_subject, generation_state = _generation_facts(
        subject, record, chain.has_cards, chain.failed
    )
    return _PortraitEnumeration(
        descriptors.descriptor(
            subject_id=subject.full(),
            generation_subject=generation_subject,
            generation_state=generation_state,
            attempts=[
                descriptors.image_attempt(attempt.source_id, attempt.rank, attempt.resource)
                if attempt.resource is not None
                else descriptors.fault_attempt(attempt.source_id, attempt.rank, attempt.fault)
                for attempt in attempts
            ],
            terminal_payload=_alpha_terminal(fallback),
            # Portraits carry no retention authorization: their runtime sources
            # are presented only while they are reachable, and the atomic
            # portrait wire owner is the one that introduces authorization.
            retention_sources=[],
        ),
        record,
        candidate,
        _silhouette_from(fallback),
    )


def describe_portrait(subject: ArtSubject, entity=None) -> dict:
    """The canonical descriptor of one portrait subject's ordered source attempts.

    The canonical projection of the one production walk: the same selection
    the flat payload presents, with every position's stable source identity and
    rank, every reached fault at its own position, the subject's independent
    recorded generation truth, and the authoritative alpha terminal at its own
    rank. A scene subject resolves no person source and so contributes only its
    classic record — the scene wire itself stays the scene owner's.
    """
    return _enumerate_portrait(subject, entity).descriptor


def describe_entity(entity) -> dict | None:
    """The canonical portrait descriptor of one entity, or ``None``.

    Applies exactly the presentation eligibility (explicit named policy, both
    canonical integer age fields, registered visual species) and then
    enumerates that ONE subject. Nothing here enumerates, scans, or discovers
    any other subject: the caller supplies the entities it is already
    authorized to show.

    An entity that carries no eligible subject (a dialogue host with no named
    policy, a character whose canonical ages refuse it, a monster whose visual
    species is unregistered) still answers its own complete descriptor — the
    full fact set with no image attempt, no generated subject key and no
    prompt, plus the deterministic attribute-selected alpha terminal — because
    catalog admission is a membership decision the caller already made, not a
    real-image decision. Only a genuinely absent entity — ``None``, or a value
    carrying no runtime identity at all — answers ``None``, so no descriptor
    is ever built around a fabricated ``subject_id``.
    """
    if entity is None or getattr(entity, "pk", None) is None:
        return None
    subject, refusal = _portrait_subject(entity)
    if refusal is not None:
        return _refusal_descriptor(entity, subject)
    return describe_portrait(subject, entity)


def _refusal_descriptor(entity, subject: ArtSubject | None) -> dict:
    """The complete descriptor of an admitted entity with no eligible subject.

    Every fact here is a REFUSAL fact: no candidate, no reached fault and no
    recorded generation is claimed, so nothing is enqueued, created or read on
    the refused subject's behalf, and ``generation_subject`` stays null so the
    completion push can never match a subject the entity does not have. The
    alpha terminal is the deterministic attribute-selected built-in the
    presentation has always carried for such an entity — a fallback, never a
    real candidate.

    ``subject_id`` is the position's stable lifecycle identity and is
    deliberately the entity's own opaque decimal runtime identity — NEVER the
    refused subject's key, because a subject that failed eligibility must
    disclose no subject key at all (its ``portrait_policy.stable_key`` is
    operator content the refusal must not leak). It is likewise not a
    generation key — that is ``generation_subject``, which is null here — so a
    re-presentation of the same position keeps the same resolution epoch while
    claiming no generation.
    """
    identity = getattr(entity, "pk", None)
    if subject is not None:
        fallback = fallback_for(subject, entity=entity, report=True)
    else:
        fallback = _entity_fallback(entity)
    return descriptors.descriptor(
        subject_id=str(identity),
        generation_subject=None,
        generation_state=None,
        attempts=[],
        terminal_payload=_alpha_terminal(fallback),
        retention_sources=[],
    )


def _silhouette(key: object, identity: object, face_rect: object) -> dict | None:
    """The decorative reference for one resolved fallback key, or ``None``.

    The URL is built from the committed identity exactly like every other
    branch (the media route serves ``defaults/`` and nothing else). A missing
    or malformed rectangle defaults to the shared face rectangle without
    failing the payload.
    """
    if not isinstance(key, str) or not key:
        return None
    if not isinstance(identity, str) or not identity:
        return None
    rect: dict[str, float] | None = None
    try:
        rect = validate_face_rect(face_rect)
    except GalleryRecordError:  # observability: ignore R2: seam rectangle defaults per contract
        rect = None
    if rect is None:
        rect = dict(DEFAULT_FACE_RECT)
    return {"key": key, "url": media_url_for(identity), "face_rect": rect}


def _silhouette_from(fallback) -> dict | None:
    """The flat decorative reference for one resolved seam dict, or ``None``."""
    if not isinstance(fallback, dict):
        return None
    return _silhouette(
        fallback.get("key"), fallback.get("identity"), fallback.get("face_rect")
    )


def _entity_fallback(entity) -> dict | None:
    """The SEAM-shaped fallback facts of an entity carrying no named portrait subject.

    The deterministic attribute-selected resolution for a refused subject,
    kept in the seam's own ``{identity, key, face_rect}`` shape so it can build
    a canonical alpha terminal (which needs the committed identity's version)
    exactly like a subject's own resolution does. The one
    ``gallery_fallback_used`` event is reported with ``kind`` "entity" because
    no portrait subject exists.
    """
    identity = getattr(entity, "pk", None)
    if entity is None or identity is None:
        return None
    key = fallback_key_for_entity(entity, str(identity))
    from world.observability import log_info

    log_info(
        "gallery_fallback_used",
        context={"subject": str(identity), "kind": "entity", "key": key},
    )
    committed, rect = fallback_identity_and_rect(key)
    return {"key": key, "identity": committed, "face_rect": rect}


def _portrait_subject(entity) -> tuple[ArtSubject | None, str | None]:
    """The entity's eligible portrait subject, or the bounded reason it has none.

    ``(subject, None)`` for an eligible subject; ``(None, "unnamed")`` for a
    character whose named portrait policy is absent or malformed; and
    ``(subject, "ineligible")`` for a character whose canonical ages, or a
    monster whose registered visual species, refuse it. Eligibility stays
    exactly what presentation has always applied — the explicit named policy,
    both canonical integer age fields, and the registered visual species —
    and is never inferred from a display name, a quest role, or a key shape.
    A monster's provenance is resolved from ``species_key`` when present, else
    ``art_species_key``.
    """
    from typeclasses.monsters import Monster

    if isinstance(entity, Monster):
        visual_key = getattr(entity, "species_key", None)
        if visual_key is None:
            visual_key = getattr(entity, "art_species_key", None)
        if visual_key is None:
            return None, "ineligible"
        try:
            return monster_subject_for(visual_key), None
        except ArtSubjectError:  # observability: ignore R2: unregistered visual species -> specified refusal
            return None, "ineligible"
    try:
        subject = character_subject_for(entity)
    except ArtSubjectError:  # observability: ignore R2: unresolvable policy -> specified refusal
        return None, "unnamed"
    if subject is None:
        return None, "unnamed"
    try:
        character_ages(entity)
    except Exception:  # observability: ignore R2: age-eligibility failure -> specified refusal; diagnostics must never leak
        return subject, "ineligible"
    return subject, None


def _unique_attempts(attempts: list[dict]) -> list[dict]:
    """Keep one entry per position the canonical wire allows exactly once.

    A descriptor may carry at most one entry per ``(type, source_id, rank)``
    (the shared validators reject a duplicate), so a position that somehow
    contributes two facts of one kind keeps the FIRST — the one the chain's own
    order puts in front of the substitute that follows it — and the repeat is
    dropped. This is a contract guard, not a policy: each position's own
    attribution already gives its facts distinct source ids.
    """
    seen: set[tuple[str, str, int]] = set()
    unique: list[dict] = []
    for attempt in attempts:
        key = (attempt["type"], attempt["source_id"], attempt["rank"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(attempt)
    return unique


def _scene_bundled_resource(catalog, key: str) -> dict | None:
    """The admitted bundled illustration of one scene key as a canonical resource.

    ``None`` for a key the current bundled snapshot does not admit: a required
    image that is missing, unreadable or undecodable has no resource, so the
    chain can state the required-resource fact instead of inventing a URL.
    """
    image = catalog.entry(key)
    url = catalog.url_for(key)
    if image is None or url is None:
        return None
    return descriptors.resource(
        image.identity,
        image.fingerprint,
        url,
        descriptors.ORIGIN_BUNDLED_OFFICIAL,
        geometry_payload=descriptors.geometry(
            image_size=descriptors.image_size_payload(**image.image_size),
        ),
    )


def _scene_official_resource(official_catalog, identity: str) -> dict | None:
    """The admitted operator image of one identity as a canonical resource.

    ``None`` for an identity the current operator snapshot does not admit, so a
    URL is never built for unindexed artwork.
    """
    image = official_catalog.entry(identity)
    if image is None:
        return None
    url = official_catalog.url_for(image.identity)
    if url is None:
        return None
    return descriptors.resource(
        image.identity,
        image.fingerprint,
        url,
        descriptors.ORIGIN_OFFICIAL,
        geometry_payload=descriptors.geometry(
            image_size=descriptors.image_size_payload(**image.image_size),
        ),
    )


def _scene_official_position(
    kind: str, key: str, source_prefix: str, rank: int
) -> tuple[list[tuple[str, int, str]], dict | None]:
    """One operator scene position: its preceding faults and its default candidate.

    The retained startup facts of the content directory come FIRST — a
    directory that could not be enumerated, or a manifest-declared default a
    deterministic substitute replaced — followed by the metadata fact of the
    very image that resolved. A directory-scope fact keeps the position's own
    canonical ``<prefix>:<key>`` source id; a per-image fact is attributed to
    that exact image, exactly like the portrait chain's official slot, so two
    facts of one position never collide on one source id. An unconfigured
    directory contributes nothing at all: a never-mounted source is not a
    failure.
    """
    from world.art import official

    source_id = f"{source_prefix}:{key}"
    catalog = official.current_catalog()
    faults: list[tuple[str, int, str]] = []
    for fault in catalog.source_faults(kind, key):
        if fault.scope in (official.SOURCE_SCOPE_DEFAULT, official.SOURCE_SCOPE_SOURCE):
            faults.append((source_id, rank, fault.reason))
    content = catalog.content(kind, key)
    if content is None or content.default_identity is None:
        return faults, None
    resource = _scene_official_resource(catalog, content.default_identity)
    if resource is None:
        return faults, None
    metadata = catalog.fault_for(content.default_identity)
    if metadata is not None:
        faults.append(
            (f"{source_prefix}:{content.default_identity}", rank, metadata.reason)
        )
    return faults, resource


def _published_output_version(record: ArtAssetRecord, identity: str) -> str:
    """The resource version of one published output: its identity plus its
    PUBLISHING token.

    The claim token is cleared when the output is published, so the version
    reads the token that actually published the current bytes
    (``published_generation_token``): two successive successful publications of
    the same stored path therefore carry two different versions, which is what
    makes a regeneration a new resource for every consumer instead of a reused
    cached one. A record published before this fact existed contributes its
    empty token, which is a stable version of its own.
    """
    return descriptors.generated_version(identity, str(record.db.published_generation_token))


def _scene_generated_resource(
    subject: ArtSubject, record: ArtAssetRecord
) -> tuple[dict | None, str | None]:
    """The scene record's generated artwork as ``(resource, fault)``.

    Exactly one side is set for a ``done`` record: the resource of the output
    identity the store still holds, or the bounded generated-output-missing
    fact when the recorded output can no longer be presented. The URL carries
    the bounded ``?v=<digest>`` cache version the shared resource contract
    allows — a regeneration republishes the same stored path, so the version is
    what makes the browser fetch the new bytes; a path whose versioned form
    would exceed the runtime origin's own URL ceiling keeps its unversioned URL
    rather than failing the whole payload, and the version field still changes
    the resource identity for every consumer.
    """
    identity = _validated_output_identity(subject, record.db.output_identity)
    if identity is None:
        log_warn("art_asset_output_missing", context={"subject": subject.full()})
        return None, descriptors.REASON_GENERATED_OUTPUT_MISSING
    version = _published_output_version(record, identity)
    url = media_url_for(identity)
    versioned = f"{url}?{descriptors.VERSION_QUERY}={version}"
    if len(versioned) > descriptors.MEDIA_URL_LIMITS[descriptors.ORIGIN_RUNTIME]:
        versioned = url
    return (
        descriptors.resource(
            identity,
            version,
            versioned,
            descriptors.ORIGIN_RUNTIME,
            geometry_payload=descriptors.geometry(),
        ),
        None,
    )


def _scene_retained_output_identity(
    subject: ArtSubject, record: ArtAssetRecord | None
) -> str | None:
    """The applicable preserved output identity that authorizes scene retention.

    The record's CURRENT output when the store still holds it, else its
    PRESERVED prior output (a regeneration preserves the prior valid output
    across the requeue and a later failed attempt), so the authorization stays
    stable across a pending or failed regeneration and disappears the moment
    neither output can be presented. ``None`` when no output is readable —
    retention is never authorized by an unrelated healthy file.
    """
    if record is None:
        return None
    for identity in (record.db.output_identity, record.db.prior_output_identity):
        validated = _validated_output_identity(subject, identity)
        if validated is not None:
            return validated
    return None


def _scene_retention_sources(target, subject: ArtSubject, record) -> list[dict]:
    """The bounded retention authorizations of one logical scene.

    Only a scene whose logical identity came from the map owner's authored
    metadata authorizes retained content: a fallback identity cannot establish
    that two resolutions are the same logical place, so it authorizes nothing.
    A source is included only while its prior known-good output is still
    applicable and readable — the generated source for as long as its preserved
    output identity can be presented (which deliberately includes a pending or
    failed regeneration), and the room binding for as long as the binding still
    applies and the operator default it resolves is still admitted. Each token
    covers the exact applicable output, so a replaced room default or a
    vanished generated output stops authorizing the pixels it no longer
    describes.
    """
    if not target.trusted_identity:
        return []
    sources: list[dict] = []
    output = _scene_retained_output_identity(subject, record)
    if output is not None:
        sources.append(
            descriptors.retention_source(
                descriptors.scene_generated_source_id(subject.full()),
                descriptors.retention_token(
                    target.identity, subject.full(), "generated", output
                ),
            )
        )
    if target.room_art_key is not None and not target.room_binding_invalid:
        from world.art import official

        content = official.current_catalog().content("room", target.room_art_key)
        if content is not None and content.default_identity is not None:
            if _scene_official_resource(official.current_catalog(), content.default_identity):
                sources.append(
                    descriptors.retention_source(
                        descriptors.scene_room_source_id(target.room_art_key),
                        descriptors.retention_token(
                            target.identity,
                            "room",
                            target.room_art_key,
                            content.default_identity,
                        ),
                    )
                )
    return sources


def _malformed_scene_descriptor(identity: str) -> dict:
    """The explicit descriptor of a scene whose authored metadata is unusable.

    The one reached fact is the configuration failure, at the terminal
    position the town fallback occupies, followed by that town terminal itself
    when the bundled collection admits it: the malformed scene states WHICH
    configuration is wrong and still shows the permitted town image rather than
    an invented one. No generation is claimed here — an unusable archetype
    names no subject, so ``generation_subject`` and ``generation_state`` stay
    null instead of synthesizing a pending generation.
    """
    from world.art.scene_definitions import current_bundled_scenes

    source_id = descriptors.scene_terminal_source_id(TOWN_TERMINAL_KEY)
    resource = _scene_bundled_resource(current_bundled_scenes(), TOWN_TERMINAL_KEY)
    terminal_payload = (
        None
        if resource is None
        else descriptors.terminal(
            descriptors.TERMINAL_SCENE_IMAGE,
            source_id,
            descriptors.SCENE_RANK_TERMINAL,
            resource,
        )
    )
    return descriptors.descriptor(
        subject_id=identity,
        generation_subject=None,
        generation_state=None,
        attempts=[
            descriptors.fault_attempt(
                source_id,
                descriptors.SCENE_RANK_TERMINAL,
                descriptors.REASON_CONFIGURATION_INVALID,
            )
        ],
        terminal_payload=terminal_payload,
        retention_sources=[],
    )


def describe_scene(target) -> dict:
    """The canonical descriptor of one logical scene's ordered source chain.

    The scene wire's single resolution seam: it walks the authored room-art
    override, the scene archetype's own generated artwork, the optional
    operator scene default, the REQUIRED bundled type illustration and the
    scene's declared terminal image, keeping every reached fault at its own
    source position and rank. A healthy earlier candidate therefore prevents
    every later fact from being reached, while a broken override stays visible
    beside the substitute that follows it. An identical terminal — a scene
    whose declared terminal IS its own bundled type illustration — is never
    listed twice: the required position already covers that exact resource, so
    the terminal position carries nothing and the terminal is never retried.

    The walk is a pure read: nothing here creates a record, enqueues a job,
    repairs geometry, touches a file or contacts the network, and a frozen
    :class:`~world.rules.art_view.SceneTarget` is its whole input.
    An archetype-less target — the room's authored metadata reduced to nothing
    by ``world.rules.art_view.scene_target_for`` — is the malformed case stated
    explicitly; a
    registered archetype the art collection declares no terminal for simply has
    no terminal position, and its required bundled position still states
    whether that illustration is admitted.
    """
    from world.art.scene_definitions import current_bundled_scenes, scene_definition_for
    from world.art.subjects import scene_subject_for
    from world.rules.art_view import INVALID_ROOM_BINDING_KEY

    archetype = target.archetype
    if not isinstance(archetype, str):
        # An absent or unregistered archetype is authored metadata this
        # resolution cannot honor: the malformed case, stated explicitly. The
        # frozen target already reduces every unusable authored value to
        # ``None``, so nothing here re-reads a raw stored fact.
        return _malformed_scene_descriptor(target.identity)

    # A registered archetype's declared terminal is the art collection's own
    # declaration: a registered archetype without one simply has no terminal
    # position, and the required bundled position still states whether its
    # illustration is admitted.
    definition = scene_definition_for(archetype)
    terminal_key = definition.terminal_key if definition is not None else None
    try:
        subject = scene_subject_for(archetype)
    except ArtSubjectError:  # observability: ignore R2: an unusable authored archetype is the malformed case stated below
        # A registered room's archetype is always a registered scene subject;
        # one that is not cannot be honored, so it takes the same explicit
        # malformed-metadata path as an absent archetype instead of raising
        # into the art panel.
        return _malformed_scene_descriptor(target.identity)
    record = _record_for(subject)
    attempts: list[dict] = []

    # (1) The authored per-room operator override.
    if target.room_binding_invalid:
        attempts.append(
            descriptors.fault_attempt(
                descriptors.scene_room_source_id(
                    target.room_art_key or INVALID_ROOM_BINDING_KEY
                ),
                descriptors.SCENE_RANK_ROOM,
                descriptors.REASON_CONFIGURATION_INVALID,
            )
        )
    elif target.room_art_key is not None:
        faults, resource = _scene_official_position(
            "room",
            target.room_art_key,
            descriptors.SCENE_ROOM_SOURCE_PREFIX,
            descriptors.SCENE_RANK_ROOM,
        )
        for source_id, rank, reason in faults:
            attempts.append(descriptors.fault_attempt(source_id, rank, reason))
        if resource is not None:
            attempts.append(
                descriptors.image_attempt(
                    descriptors.scene_room_source_id(target.room_art_key),
                    descriptors.SCENE_RANK_ROOM,
                    resource,
                )
            )

    # (2) The scene archetype's own generated artwork.
    generated_source = descriptors.scene_generated_source_id(subject.full())
    if record is not None and record.db.status == ArtAssetStatus.DONE:
        resource, fault = _scene_generated_resource(subject, record)
        if fault is not None:
            attempts.append(
                descriptors.fault_attempt(
                    generated_source, descriptors.SCENE_RANK_GENERATED, fault
                )
            )
        else:
            attempts.append(
                descriptors.image_attempt(
                    generated_source, descriptors.SCENE_RANK_GENERATED, resource
                )
            )
    elif record is not None and record.db.status == ArtAssetStatus.FAILED:
        attempts.append(
            descriptors.fault_attempt(
                generated_source,
                descriptors.SCENE_RANK_GENERATED,
                descriptors.REASON_GENERATION_FAILED,
            )
        )

    # (3) The optional operator scene default.
    faults, resource = _scene_official_position(
        "scene",
        archetype,
        descriptors.SCENE_OPERATOR_SOURCE_PREFIX,
        descriptors.SCENE_RANK_OPERATOR,
    )
    for source_id, rank, reason in faults:
        attempts.append(descriptors.fault_attempt(source_id, rank, reason))
    if resource is not None:
        attempts.append(
            descriptors.image_attempt(
                descriptors.scene_operator_source_id(archetype),
                descriptors.SCENE_RANK_OPERATOR,
                resource,
            )
        )

    # (4) The REQUIRED bundled type illustration.
    catalog = current_bundled_scenes()
    bundled = _scene_bundled_resource(catalog, archetype)
    bundled_source = descriptors.scene_bundled_source_id(archetype)
    if bundled is None:
        attempts.append(
            descriptors.fault_attempt(
                bundled_source,
                descriptors.SCENE_RANK_BUNDLED,
                descriptors.REASON_REQUIRED_RESOURCE_MISSING,
            )
        )
    else:
        attempts.append(
            descriptors.image_attempt(
                bundled_source, descriptors.SCENE_RANK_BUNDLED, bundled
            )
        )

    # (5) The distinct declared terminal image.
    terminal_payload = None
    if terminal_key is not None and terminal_key != archetype:
        terminal_source = descriptors.scene_terminal_source_id(terminal_key)
        terminal_resource = _scene_bundled_resource(catalog, terminal_key)
        if terminal_resource is None:
            attempts.append(
                descriptors.fault_attempt(
                    terminal_source,
                    descriptors.SCENE_RANK_TERMINAL,
                    descriptors.REASON_REQUIRED_RESOURCE_MISSING,
                )
            )
        else:
            terminal_payload = descriptors.terminal(
                descriptors.TERMINAL_SCENE_IMAGE,
                terminal_source,
                descriptors.SCENE_RANK_TERMINAL,
                terminal_resource,
            )

    generation_subject, generation_state = _generation_facts(subject, record, False, False)
    return descriptors.descriptor(
        subject_id=target.identity,
        generation_subject=generation_subject,
        generation_state=generation_state,
        attempts=_unique_attempts(attempts),
        terminal_payload=terminal_payload,
        retention_sources=_scene_retention_sources(target, subject, record),
    )


def describe_dream_scene(subject_id: str) -> dict:
    """The canonical descriptor of the dream stage's OWN ordered source chain.

    The dream is not an explorable archetype: it has no authored room binding
    and no generated artwork of its own, so its chain is exactly the OPTIONAL
    operator-preferred official image — the exact identity
    ``world.art.scene_definitions.DREAM_PREFERRED_OFFICIAL_IDENTITY``, never a
    directory default or a manifest choice — the REQUIRED bundled
    ``dream_throne`` illustration and the distinct declared terminal image.
    ``generation_subject``/``generation_state`` stay null and no retention is
    authorized: the dream claims no generation, keeps no prior pixels across
    sessions and shows no inherited physical background. Nothing here reads the
    sleeper's location, enqueues a job, repairs geometry, touches a file or
    contacts the network.

    The preferred position states only the facts the startup snapshot retained
    about that EXACT identity: a root the load could not use at all or a
    content directory it could not enumerate (``source_unavailable``), an image
    of that name present but refused at admission (``source_rejected``) and the
    per-image metadata degradation of the very image that resolved. Plain
    absence is the normal no-art configuration and contributes nothing at all —
    never a reached failure — so an operator root without the dream image still
    shows the required bundled dream without error styling. The directory's own
    manifest-declared default is deliberately not consulted: it describes a
    different image's selection, not this identity's.
    """
    from world.art import official
    from world.art.scene_definitions import (
        DREAM_PREFERRED_OFFICIAL_IDENTITY,
        DREAM_PREFERRED_OFFICIAL_KEY,
        DREAM_SCENE_KEY,
        current_bundled_scenes,
        scene_definition_for,
    )

    source_id = descriptors.scene_operator_source_id(DREAM_SCENE_KEY)
    rank = descriptors.SCENE_RANK_OPERATOR
    catalog = official.current_catalog()
    identity_source_id = (
        f"{descriptors.SCENE_OPERATOR_SOURCE_PREFIX}:{DREAM_PREFERRED_OFFICIAL_IDENTITY}"
    )
    preferred_faults: list[tuple[str, str]] = []
    health = catalog.root_health()
    if health is not None and health.fault:
        preferred_faults.append((source_id, official.SOURCE_REASON_UNAVAILABLE))
    for fault in catalog.source_faults("npc", DREAM_PREFERRED_OFFICIAL_KEY):
        if fault.scope == official.SOURCE_SCOPE_SOURCE:
            preferred_faults.append((source_id, fault.reason))

    attempts: list[dict] = []
    resource = _scene_official_resource(catalog, DREAM_PREFERRED_OFFICIAL_IDENTITY)
    metadata = catalog.fault_for(DREAM_PREFERRED_OFFICIAL_IDENTITY)
    if metadata is not None:
        preferred_faults.append((identity_source_id, metadata.reason))
    if resource is None and catalog.refusal_reason(DREAM_PREFERRED_OFFICIAL_IDENTITY) is not None:
        preferred_faults.append((identity_source_id, descriptors.REASON_SOURCE_REJECTED))
    for failed_source, reason in preferred_faults:
        attempts.append(descriptors.fault_attempt(failed_source, rank, reason))
    if resource is not None:
        attempts.append(descriptors.image_attempt(source_id, rank, resource))

    bundled_catalog = current_bundled_scenes()
    bundled_source = descriptors.scene_bundled_source_id(DREAM_SCENE_KEY)
    bundled = _scene_bundled_resource(bundled_catalog, DREAM_SCENE_KEY)
    if bundled is None:
        attempts.append(
            descriptors.fault_attempt(
                bundled_source,
                descriptors.SCENE_RANK_BUNDLED,
                descriptors.REASON_REQUIRED_RESOURCE_MISSING,
            )
        )
    else:
        attempts.append(
            descriptors.image_attempt(
                bundled_source, descriptors.SCENE_RANK_BUNDLED, bundled
            )
        )

    definition = scene_definition_for(DREAM_SCENE_KEY)
    terminal_key = definition.terminal_key if definition is not None else None
    terminal_payload = None
    if terminal_key is not None and terminal_key != DREAM_SCENE_KEY:
        terminal_source = descriptors.scene_terminal_source_id(terminal_key)
        terminal_resource = _scene_bundled_resource(bundled_catalog, terminal_key)
        if terminal_resource is None:
            attempts.append(
                descriptors.fault_attempt(
                    terminal_source,
                    descriptors.SCENE_RANK_TERMINAL,
                    descriptors.REASON_REQUIRED_RESOURCE_MISSING,
                )
            )
        else:
            terminal_payload = descriptors.terminal(
                descriptors.TERMINAL_SCENE_IMAGE,
                terminal_source,
                descriptors.SCENE_RANK_TERMINAL,
                terminal_resource,
            )

    return descriptors.descriptor(
        subject_id=subject_id,
        generation_subject=None,
        generation_state=None,
        attempts=_unique_attempts(attempts),
        terminal_payload=terminal_payload,
        retention_sources=[],
    )
