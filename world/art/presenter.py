"""Read-only resolution primitives for the art store (design D8).

The presenter resolves a validated subject to its status, same-origin media
URL, aspect, and alternative text, or to a truthful placeholder kind/label.
Gallery-bearing subjects (characters, monsters) first attempt the
deterministic gallery display chain in ``world.art.gallery_match``; every
payload it produces carries ``face_rect`` — the resolved card's rectangle,
the shared default for a classic asset or a fallback image, or ``null`` for
every placeholder.
It never exposes ``out_path``, the store root, or any absolute filesystem path.
Change 23f's browser panel consumes these primitives; this change owns them.
"""

from world.observability import log_warn

from world.art.formats import STORE_EXTENSIONS
from world.art.gallery import (
    DEFAULT_FACE_RECT,
    GalleryRecordError,
    validate_face_rect,
)
from world.art.gallery_match import fallback_for, resolve_card
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
    chain (``resolve_card``); a resolved card yields an ``asset`` payload
    whose URL is built only from its validated stored identity. When nothing
    in the gallery resolves, the classic ``done`` asset record is resolved
    exactly as before, the terminal fallback seam is consulted when that
    record's identity is unusable, and the truthful placeholder closes the
    chain. Every payload carries ``face_rect``: the card's rectangle, the
    shared default for a classic asset or fallback image, or ``None`` for a
    placeholder.

    Returns status, same-origin URL, aspect ratio, and alternative text for a
    ``done`` record; a truthful placeholder kind/label otherwise. Never leaks
    ``out_path`` or the store root. A claimed ``in_progress`` record is
    normalized to the wire-stable ``pending`` status so a snapshot taken while
    a worker holds the claim renders a placeholder instead of failing the wire
    schema (fix-art-pipeline-contracts D3); the persistent record status is
    never touched.
    """
    card = resolve_card(subject, entity)
    if card is not None:
        return _card_payload(subject, card)
    record = _record_for(subject)
    identity = None
    if record is not None and record.db.status == ArtAssetStatus.DONE:
        identity = _validated_output_identity(subject, record.db.output_identity)
        if identity is None:
            log_warn("art_asset_output_missing", context={"subject": subject.full()})
    if identity is not None:
        return {
            "kind": "asset",
            "label": "已生成",
            "status": ArtAssetStatus.DONE,
            "url": media_url_for(identity),
            "aspect_ratio": record.db.aspect_ratio,
            "alt": subject.full(),
            "subject_key": subject.full(),
            "face_rect": dict(DEFAULT_FACE_RECT),
        }
    # Steps 1-5 resolved nothing: consult the terminal seam (step 6) on
    # EVERY fall-through path — no record, an unfinished record, and an
    # unusable done identity alike — before the placeholder closes the chain.
    # The already-resolved entity rides along so the resolver reads its sex,
    # apparent age, and registry provenance directly (gallery-builtin-fallbacks).
    fallback = fallback_for(subject, entity=entity)
    if fallback is not None:
        return _fallback_payload(subject, fallback)
    if record is None or record.db.status != ArtAssetStatus.DONE:
        kind = PLACEHOLDER_MISSING
        status = record.db.status if record else ArtAssetStatus.MISSING
        if status == ArtAssetStatus.IN_PROGRESS:
            status = ArtAssetStatus.PENDING
        return {
            "kind": kind,
            "label": PLACEHOLDER_LABELS[kind],
            "status": status,
            "url": None,
            "aspect_ratio": record.db.aspect_ratio if record else None,
            "alt": PLACEHOLDER_LABELS[kind],
            "subject_key": subject.full(),
            "face_rect": None,
        }
    return _placeholder_unavailable("無法提供")


def _card_payload(subject: ArtSubject, card: dict) -> dict:
    """The asset payload for one validated gallery card.

    The URL is built only from the card's validated stored identity (the
    chain checked prefix, extension, confinement, and existence). A stored
    rectangle that fails validation degrades to the shared default with one
    bounded diagnostic — never a failed payload.
    """
    try:
        face_rect = validate_face_rect(card["face_rect"])
    except GalleryRecordError:  # observability: ignore R2: malformed rect degrades per contract; payload must never fail
        log_warn("art_face_rect_invalid", context={"subject": subject.full()})
        face_rect = dict(DEFAULT_FACE_RECT)
    return {
        "kind": "asset",
        "label": "已生成",
        "status": ArtAssetStatus.DONE,
        "url": media_url_for(card["stored_identity"]),
        "aspect_ratio": GALLERY_ASPECT_RATIO,
        "alt": subject.full(),
        "subject_key": subject.full(),
        "face_rect": face_rect,
    }


def _fallback_payload(subject: ArtSubject, fallback: dict) -> dict:
    """The asset payload for a fallback image supplied by the terminal seam.

    Filled by ``gallery-builtin-fallbacks``: the seam hands back the resolved
    built-in default's ``defaults/<key>.webp`` identity plus its per-key face
    rectangle, and the URL is built from the identity exactly like every
    other branch (the media route serves it from the in-repo defaults
    directory). An unusable seam result stays the truthful placeholder, and a
    missing or malformed seam rectangle defaults to the shared face rectangle
    without failing the payload.
    """
    identity = fallback.get("identity") if isinstance(fallback, dict) else None
    if not isinstance(identity, str) or not identity:
        return _placeholder_unavailable("無法提供")
    try:
        face_rect = validate_face_rect(fallback.get("face_rect"))
    except GalleryRecordError:  # observability: ignore R2: seam rectangle defaults per contract
        face_rect = dict(DEFAULT_FACE_RECT)
    return {
        "kind": "asset",
        "label": "已生成",
        "status": ArtAssetStatus.DONE,
        "url": media_url_for(identity),
        "aspect_ratio": GALLERY_ASPECT_RATIO,
        "alt": subject.full(),
        "subject_key": subject.full(),
        "face_rect": face_rect,
    }


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
        return _placeholder_unavailable("無肖像")
    try:
        character_ages(entity)
    except Exception:  # observability: ignore R2: age-eligibility failure -> specified unavailable placeholder; diagnostics must never leak
        return _placeholder_unavailable("無法提供")
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
            return _placeholder_unavailable("無法提供")
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


def _placeholder_unavailable(label: str) -> dict:
    return {
        "kind": PLACEHOLDER_UNAVAILABLE,
        "label": label,
        "status": None,
        "url": None,
        "aspect_ratio": None,
        "alt": label,
        "subject_key": None,
        "face_rect": None,
    }
