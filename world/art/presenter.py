"""Read-only resolution primitives for the art store (design D8).

The presenter resolves a validated subject to its status, same-origin media
URL, aspect, and alternative text, or to a truthful placeholder kind/label.
ONE canonical enumerator owns the portrait source policy: the ordered chain of
the equipment-bound card, the personal official selection, the record's
default card, the classic ``done`` asset record, the mounted catalog's
official default for the entity's content reference, and the authoritative
alpha terminal. ``_enumerate_portrait`` walks that chain exactly once and
projects it twice — as the canonical artwork descriptor
(``describe_portrait``/``describe_entity``, using the frozen
``world.art.descriptors`` vocabulary with each position's stable source id and
rank and every reached fault at its own position) and as the current
registered flat payload ``resolve_subject`` still returns. Scenes keep their
own path through the same classic record and truthful placeholder.

Every flat payload carries ``face_rect`` — the resolved card's or official
image's rectangle, the shared default for a classic asset or a fallback image,
or ``null`` for every placeholder — and ``origin``, the closed
portrait-origin discriminator vocabulary: ``runtime`` for the payload's own
card or classic image, ``official`` for the catalog's read-only default,
``silhouette`` when only the built-in fallback resolved, and ``placeholder``
when nothing did.
Every payload also carries the decorative ``fallback`` silhouette reference:
the resolved built-in key, its committed ``/art/defaults/`` URL, and that
key's rectangle, carried on stage-eligible payloads whether or not a real
image resolved, so a browser whose real image later fails to load renders the
already-resolved silhouette without a new request. The field is presentation
data only: it never becomes a payload's own media URL, never reports the
portrait as generated, and never changes the subject's true status.
An official default is presented only when the catalog's URL fits
``MAX_PORTRAIT_MEDIA_URL``, the shared wire ceiling: an official identity
embeds an operator-chosen filename, so an over-budget URL falls through
exactly like an absent reference instead of failing the whole panel, and an
official payload never claims a ``done``/generated status.
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

# Placeholder kinds, exactly what the browser must show when no asset exists.
PLACEHOLDER_MISSING = "missing"
PLACEHOLDER_UNAVAILABLE = "unavailable"
PLACEHOLDER_LABELS = {
    PLACEHOLDER_MISSING: "未生成",
    PLACEHOLDER_UNAVAILABLE: "無法提供",
}

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

# The payload kind of a resolved official default: a real image the subject
# presents, but not a generated asset, so it is never a ``done`` status.
PAYLOAD_OFFICIAL = "official"

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
                descriptors.generated_version(identity, str(record.db.generation_token)),
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


def _attempt_payload(subject: ArtSubject, attempt: _PortraitAttempt) -> dict:
    """The current flat payload of one resolved canonical candidate.

    The projection the registered portrait contract keeps until its atomic
    canonical wire cutover: the resource's own URL, its validated geometry and
    its authored origin, with the catalog's read-only image labelled as exactly
    that and never as a generated asset. Selection, geometry validation and
    diagnostics all already happened once, in the enumerator.
    """
    resource = attempt.resource
    geometry = resource["geometry"]
    official = resource["origin"] == descriptors.ORIGIN_OFFICIAL
    return {
        "kind": PAYLOAD_OFFICIAL if official else "asset",
        "label": "官方圖片" if official else "已生成",
        "status": None if official else ArtAssetStatus.DONE,
        "url": resource["url"],
        "aspect_ratio": geometry["aspect_ratio"],
        "alt": subject.full(),
        "subject_key": subject.full(),
        "face_rect": geometry["face_rect"],
        "stage": geometry["stage"],
    }


def _placeholder_payload(
    subject: ArtSubject, record: ArtAssetRecord | None, silhouette: dict | None
) -> dict:
    """The truthful placeholder closing a chain that resolved no real image.

    A missing or unfinished record reads ``missing`` with its own true status
    (a claimed ``in_progress`` record is normalized to the wire-stable
    ``pending`` status so a snapshot taken while a worker holds the claim
    renders a placeholder instead of failing the wire schema; the persistent
    record status is never touched), and a ``done`` record whose output cannot
    be presented reads ``unavailable``. Never leaks ``out_path`` or the store
    root.
    """
    if record is None or record.db.status != ArtAssetStatus.DONE:
        kind = PLACEHOLDER_MISSING
        status = record.db.status if record else ArtAssetStatus.MISSING
        if status == ArtAssetStatus.IN_PROGRESS:
            status = ArtAssetStatus.PENDING
        return _carried(
            {
                "kind": kind,
                "label": PLACEHOLDER_LABELS[kind],
                "status": status,
                "url": None,
                "aspect_ratio": record.db.aspect_ratio if record else None,
                "alt": PLACEHOLDER_LABELS[kind],
                "subject_key": subject.full(),
                "face_rect": None,
                "stage": None,
            },
            silhouette,
        )
    return _carried(_placeholder_unavailable("無法提供"), silhouette)


def resolve_subject(subject: ArtSubject, *, entity=None) -> dict:
    """Resolve a validated subject to its current registered presentation payload.

    The flat projection of the one canonical portrait enumeration: the first
    resolving candidate of the ordered chain (the equipment-bound card, the
    personal official selection, the record's default card, the classic
    ``done`` asset, the mounted catalog's official default for the entity's
    content reference) becomes the payload's own image, and the truthful
    placeholder closes the chain when none resolved. A URL outside the shared
    wire budget falls through exactly like an absent reference, and a
    selection presentation performs the chain's step-4 read plus this
    payload's override read.

    A resolved fallback is NEVER the payload's own image: it rides the
    decorative ``fallback`` field (key, committed ``/art/defaults/`` URL and
    rectangle) beside the subject's true status, so a silhouette-only
    resolution stays the truthful placeholder row it is — no ``done`` status,
    no generated label, and the same persisted record. Payloads whose real
    image resolved carry the same reference (without reporting a use) so the
    browser can fall back locally when that image fails to load.
    """
    enumeration = _enumerate_portrait(subject, entity)
    if enumeration.attempt is not None:
        return _carried(
            _attempt_payload(subject, enumeration.attempt),
            enumeration.silhouette,
            origin=enumeration.attempt.resource["origin"],
        )
    return _placeholder_payload(subject, enumeration.record, enumeration.silhouette)


def _carried(payload: dict, silhouette: dict | None, *, origin: str | None = None) -> dict:
    """Attach the origin discriminator and the decorative silhouette.

    ``origin`` states the branch that produced the payload's OWN media (a
    resolved card or classic asset: ``runtime``; an official default:
    ``official``). Every other payload derives it from what actually
    resolved: ``silhouette`` when the built-in fallback did, ``placeholder``
    when nothing did.
    """
    payload["fallback"] = silhouette
    payload["origin"] = (
        origin
        if origin is not None
        else ORIGIN_SILHOUETTE if silhouette is not None else ORIGIN_PLACEHOLDER
    )
    return payload


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


def _silhouette_field(subject: ArtSubject, entity=None, *, report: bool = True) -> dict | None:
    """The silhouette a subject's payload carries, via the terminal seam.

    ``report`` marks whether the resolution is the payload's presented figure
    (the chain fell all the way through) or a decorative reference carried
    beside a real image; it rides through to the seam, which owns the
    ``gallery_fallback_used`` event.
    """
    return _silhouette_from(fallback_for(subject, entity=entity, report=report))


def _entity_silhouette(entity) -> dict | None:
    """The decorative silhouette for an entity with no named portrait subject.

    A rejected subject (no policy, malformed policy, no age pair) has no
    subject key to hand the seam, so selection runs ``fallback_key_for_entity``
    over the entity's validated attributes with its stable runtime identity as
    the sole hash input; the resolved key's committed identity and rectangle
    come from the same map. The one ``gallery_fallback_used`` event is
    reported with ``kind`` "entity" because no portrait subject exists, and
    nothing is installed, created, or enqueued.
    """
    return _silhouette_from(_entity_fallback(entity))


def _entity_fallback(entity) -> dict | None:
    """The SEAM-shaped fallback facts of an entity carrying no named portrait subject.

    The canonical counterpart of :func:`_entity_silhouette`: the same
    deterministic attribute-selected resolution, kept in the seam's own
    ``{identity, key, face_rect}`` shape so it can build a canonical alpha
    terminal (which needs the committed identity's version) exactly like a
    subject's own resolution does. The one ``gallery_fallback_used`` event is
    reported with ``kind`` "entity" because no portrait subject exists.
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


def resolve_character(entity) -> dict:
    """Resolve a character's portrait through the canonical-age check and named policy.

    A subject with missing or malformed canonical ages resolves only to the
    unavailable placeholder with its explanatory label; the payload never
    contains a rejected prompt or the offending age values.
    """
    subject, refusal = _portrait_subject(entity)
    if refusal == "unnamed":
        return _placeholder_unavailable("無肖像", silhouette=_entity_silhouette(entity))
    if refusal == "ineligible":
        return _placeholder_unavailable(
            "無法提供", silhouette=_silhouette_field(subject, entity)
        )
    return resolve_subject(subject, entity=entity)


def resolve_entity(entity) -> dict:
    """Resolve one present entity's portrait by kind (design D3).

    A monster (entity of typeclass ``Monster``) resolves
    ``portrait:monster:<visual_key>`` through ``monster_subject_for`` +
    ``resolve_subject`` with no canonical-age check. Provenance is resolved
    from ``species_key`` if present, else ``art_species_key``.
    A character resolves through :func:`resolve_character` (explicit named
    policy plus both canonical age fields). Anything else yields the
    unavailable placeholder. A rejected subject never returns a prompt, a
    subject key, or a URL.
    """
    from typeclasses.monsters import Monster

    if not isinstance(entity, Monster):
        return resolve_character(entity)
    subject, refusal = _portrait_subject(entity)
    if refusal is not None:
        return _placeholder_unavailable("無法提供", silhouette=_entity_silhouette(entity))
    payload = resolve_subject(subject, entity=entity)
    return dict(payload, subject_key=subject.full())


def resolve_scene(archetype: str) -> dict:
    """Resolve a validated scene archetype to its presentation payload."""
    from world.art.subjects import scene_subject_for

    try:
        subject = scene_subject_for(archetype)
    except ArtSubjectError:  # observability: ignore R2: unregistered archetype -> specified unavailable placeholder
        return _placeholder_unavailable("無法提供")
    return resolve_subject(subject)


def _placeholder_unavailable(label: str, *, silhouette: dict | None = None) -> dict:
    """The unavailable placeholder row, with the decorative silhouette.

    The real fields stay null (no URL, no subject key, no rectangle, no
    stage); the silhouette the entity's validated attributes select is carried
    beside them, so a placeholder row still shows the attribute-selected
    figure instead of one shared shape for every missing actor.
    """
    return _carried(
        {
            "kind": PLACEHOLDER_UNAVAILABLE,
            "label": label,
            "status": None,
            "url": None,
            "aspect_ratio": None,
            "alt": label,
            "subject_key": None,
            "face_rect": None,
            "stage": None,
        },
        silhouette,
    )
