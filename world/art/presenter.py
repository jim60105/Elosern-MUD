"""Read-only resolution primitives for the art store (design D8).

The presenter resolves a validated subject to its status, same-origin media
URL, aspect, and alternative text, or to a truthful placeholder kind/label.
Gallery-bearing subjects (characters, monsters) resolve through the
deterministic gallery display chain in ``world.art.gallery_match``: the
equipment-bound/default card, the classic ``done`` asset record, the mounted
catalog's official default for the entity's content reference
(``official_default_for``, resolved from the startup snapshot alone), the
terminal fallback seam, and the truthful placeholder. Every payload it
produces carries ``face_rect`` — the resolved card's or official image's
rectangle, the shared default for a classic asset or a fallback image, or
``null`` for every placeholder — and ``origin``, the closed portrait-origin
discriminator vocabulary this change completes: ``runtime`` for the payload's
own card or classic image, ``official`` for the catalog's read-only default,
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

from world.observability import log_warn

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
from world.art.gallery_match import fallback_for, official_default_for, resolve_display
from world.art.paths import resolved_under_store_root
from world.art.queue import record_key
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import (
    ArtSubject,
    ArtSubjectError,
    ArtSubjectKind,
    character_ages,
    character_subject_for,
    monster_subject_for,
)
from world.lore.monsters import MONSTER_TIER_REGISTRY

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


def resolve_subject(subject: ArtSubject, *, entity=None) -> dict:
    """Resolve a validated subject to its presentation payload.

    Characters and monsters first attempt the deterministic gallery display
    chain's steps 1-4 (``resolve_display``): a resolved card yields an
    ``asset`` payload whose URL is built only from its validated stored
    identity, and a resolving personal official selection yields an
    ``official`` payload (the player's explicit choice replaces the gallery
    default while every equipment-bound card still outranks it). Only when no
    personal official selection resolved is the classic ``done`` asset record
    consulted, exactly as before; then the entity's official content
    reference resolves its default image from the startup catalog snapshot
    when one is indexed (an absent, unregistered, or removed reference — and
    a URL outside the wire budget — falls through like the classic record's
    unusable identity), the terminal fallback seam is consulted, and the
    truthful placeholder closes the chain. Every payload carries
    ``face_rect``: the card's or official image's rectangle (a personal
    geometry override taking precedence for an official image), the shared
    default for a classic asset or fallback image, or ``None`` for a
    placeholder.

    A resolved fallback is NEVER the payload's own image: it rides the
    decorative ``fallback`` field (key, committed ``/art/defaults/`` URL and
    rectangle) beside the subject's true status, so a silhouette-only
    resolution stays the truthful placeholder row it is — no ``done`` status,
    no generated label, and the same persisted record. Payloads whose real
    image resolved carry the same reference (without reporting a use) so the
    browser can fall back locally when that image fails to load.

    Returns status, same-origin URL, aspect ratio, and alternative text for a
    ``done`` record; a truthful placeholder kind/label otherwise. Never leaks
    ``out_path`` or the store root. A claimed ``in_progress`` record is
    normalized to the wire-stable ``pending`` status so a snapshot taken while
    a worker holds the claim renders a placeholder instead of failing the wire
    schema (fix-art-pipeline-contracts D3); the persistent record status is
    never touched.
    """
    outcome, resolved = resolve_display(subject, entity)
    if outcome == "card":
        return _carried(
            _card_payload(subject, resolved),
            _silhouette_field(subject, entity, report=False),
            origin=ORIGIN_RUNTIME,
        )
    if outcome == "official":
        # Step 4's personal selection is the player's own explicit choice, so
        # it replaces the gallery default and presents behind every
        # equipment-bound card — still inside the shared wire budget, because
        # an official identity embeds an operator-chosen filename.
        if len(resolved["url"]) <= MAX_PORTRAIT_MEDIA_URL:
            return _carried(
                # A selection presentation performs two tolerant preference
                # reads — the chain's step-4 read and this payload's override
                # read — so corrupt stored state is reported once per read,
                # the same discipline the tolerant card read follows.
                _official_payload(subject, resolved, official_preferences_for(subject)),
                _silhouette_field(subject, entity, report=False),
                origin=ORIGIN_OFFICIAL,
            )
        log_warn(
            "art_official_url_over_wire_budget",
            context={"subject": subject.full(), "identity": resolved["identity"]},
        )
    record = _record_for(subject)
    identity = None
    if record is not None and record.db.status == ArtAssetStatus.DONE:
        identity = _validated_output_identity(subject, record.db.output_identity)
        if identity is None:
            log_warn("art_asset_output_missing", context={"subject": subject.full()})
    if identity is not None:
        return _carried(
            {
                "kind": "asset",
                "label": "已生成",
                "status": ArtAssetStatus.DONE,
                "url": media_url_for(identity),
                "aspect_ratio": record.db.aspect_ratio,
                "alt": subject.full(),
                "subject_key": subject.full(),
                "face_rect": dict(DEFAULT_FACE_RECT),
                "stage": identity_stage(),
            },
            _silhouette_field(subject, entity, report=False),
            origin=ORIGIN_RUNTIME,
        )
    # Step 6: the mounted catalog's official default for the entity's content
    # reference, presented as the payload's own read-only image (origin
    # ``official``) with the decorative silhouette carried beside it — the
    # official image is the presented figure, so the fallback reports no use.
    # ``official_default_for`` answers from the startup snapshot alone, and a
    # URL outside the wire budget falls through exactly like an absent
    # reference: one oversized operator filename must never fail the panel.
    official = official_default_for(subject, entity)
    if official is not None:
        if len(official["url"]) <= MAX_PORTRAIT_MEDIA_URL:
            return _carried(
                _official_payload(subject, official, official_preferences_for(subject)),
                _silhouette_field(subject, entity, report=False),
                origin=ORIGIN_OFFICIAL,
            )
        log_warn(
            "art_official_url_over_wire_budget",
            context={"subject": subject.full(), "identity": official["identity"]},
        )
    # Steps 1-6 resolved nothing: consult the terminal seam (step 7) on
    # EVERY fall-through path — no record, an unfinished record, an unusable
    # done identity, and an absent/over-budget official reference alike —
    # before the placeholder closes the chain.
    # The already-resolved entity rides along so the resolver reads its sex,
    # apparent age, and registry provenance directly (gallery-builtin-fallbacks).
    # A resolution here IS the presented figure, so it reports its use exactly
    # once and is carried decoratively — never as the payload's own media URL.
    silhouette = _silhouette_field(subject, entity)
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


def _card_payload(subject: ArtSubject, card: dict) -> dict:
    """The asset payload for one validated gallery card.

    The URL is built only from the card's validated stored identity (the
    chain checked prefix, extension, confinement, and existence). A stored
    rectangle that fails validation degrades to the shared default with one
    bounded diagnostic — never a failed payload.
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
    return {
        "kind": "asset",
        "label": "已生成",
        "status": ArtAssetStatus.DONE,
        "url": media_url_for(card["stored_identity"]),
        "aspect_ratio": GALLERY_ASPECT_RATIO,
        "alt": subject.full(),
        "subject_key": subject.full(),
        "face_rect": face_rect,
        "stage": stage,
    }


def _official_payload(
    subject: ArtSubject, official: dict, preferences: OfficialPreferences
) -> dict:
    """The asset payload for one resolved official default (chain step 6).

    The URL is the catalog's admitted same-origin identity (fingerprinted; the
    media route re-admits the exact path at the exact fingerprint), and the
    geometry is the catalog's load-time rectangle/stage re-validated here
    against the decoded image size exactly as a stored card's is: a rectangle
    that fails validation (including one that is not pixel-square on its own
    image) degrades to the fitted default for that image, and a malformed
    stage to identity placement, each with one bounded diagnostic — never a
    failed payload.

    The subject's own geometry override for this identity takes precedence,
    component by component, read from the caller's single tolerant preference
    snapshot. A stored rectangle the CURRENT bytes invalidate
    (an artwork update replaced them at other dimensions) degrades to the
    catalog's metadata-or-fitted rectangle with ONE bounded
    ``art_official_override_invalid`` diagnostic naming the subject, the
    identity, and the component; the stored preference itself is retained,
    because this builder only ever reads it. A stored stage needs no such
    guard: the tolerant preference read already validated it (and drops a
    malformed one) before this payload is built.

    No status is claimed: an official image is not a generated asset, so the
    payload reports no ``done``/generated portrait state, and it carries no
    filesystem root, deployment source, license/manifest text, or prompt.
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
    return {
        "kind": PAYLOAD_OFFICIAL,
        "label": "官方圖片",
        "status": None,
        "url": official["url"],
        "aspect_ratio": GALLERY_ASPECT_RATIO,
        "alt": subject.full(),
        "subject_key": subject.full(),
        "face_rect": face_rect,
        "stage": stage,
    }


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


def _silhouette_field(subject: ArtSubject, entity=None, *, report: bool = True) -> dict | None:
    """The silhouette a subject's payload carries, via the terminal seam.

    ``report`` marks whether the resolution is the payload's presented figure
    (the chain fell all the way through) or a decorative reference carried
    beside a real image; it rides through to the seam, which owns the
    ``gallery_fallback_used`` event.
    """
    fallback = fallback_for(subject, entity=entity, report=report)
    if not isinstance(fallback, dict):
        return None
    return _silhouette(
        fallback.get("key"), fallback.get("identity"), fallback.get("face_rect")
    )


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
    identity = getattr(entity, "pk", None)
    if entity is None or identity is None:
        return None
    key = fallback_key_for_entity(entity, str(identity))
    from world.observability import log_info

    log_info(
        "gallery_fallback_used",
        context={"subject": str(identity), "kind": "entity", "key": key},
    )
    return _silhouette(key, *fallback_identity_and_rect(key))


def resolve_character(entity) -> dict:
    """Resolve a character's portrait through the canonical-age check and named policy.

    A subject with missing or malformed canonical ages resolves only to the
    unavailable placeholder with its explanatory label; the payload never
    contains a rejected prompt or the offending age values.
    """
    try:
        subject = character_subject_for(entity)
    except ArtSubjectError:  # observability: ignore R2: unresolvable subject -> specified unavailable placeholder payload
        subject = None
    if subject is None:
        return _placeholder_unavailable("無肖像", silhouette=_entity_silhouette(entity))
    try:
        character_ages(entity)
    except Exception:  # observability: ignore R2: age-eligibility failure -> specified unavailable placeholder; diagnostics must never leak
        return _placeholder_unavailable(
            "無法提供", silhouette=_silhouette_field(subject, entity)
        )
    return resolve_subject(subject, entity=entity)


def resolve_entity(entity) -> dict:
    """Resolve one present entity's portrait by kind (design D3).

    A generic monster (``threat_tier`` resolving in ``MONSTER_TIER_REGISTRY``)
    resolves ``portrait:monster:<threat_tier>`` through
    ``monster_subject_for`` + ``resolve_subject`` with no canonical-age check.
    A character resolves through :func:`resolve_character` (explicit named
    policy plus both canonical age fields). Anything else yields the
    unavailable placeholder. A rejected subject never returns a prompt, a
    subject key, or a URL.
    """
    threat_tier = getattr(entity, "threat_tier", None)
    if threat_tier in MONSTER_TIER_REGISTRY:
        try:
            subject = monster_subject_for(threat_tier)
        except ArtSubjectError:  # observability: ignore R2: unregistered tier -> specified unavailable placeholder
            return _placeholder_unavailable(
                "無法提供", silhouette=_entity_silhouette(entity)
            )
        payload = resolve_subject(subject, entity=entity)
        payload["subject_key"] = subject.full()
        return payload
    return resolve_character(entity)


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
