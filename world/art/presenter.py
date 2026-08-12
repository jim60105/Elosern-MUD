"""Read-only resolution primitives for the art store (design D8).

The presenter resolves a validated subject to its status, same-origin media
URL, aspect, and alternative text, or to a truthful placeholder kind/label.
It never exposes ``out_path``, the store root, or any absolute filesystem path.
Change 23f's browser panel consumes these primitives; this change owns them.
"""

from pathlib import Path

from django.conf import settings
from evennia import logger

from world.art.adult import portrait_eligibility
from world.art.queue import record_key
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import (
    ArtSubject,
    ArtSubjectError,
    ArtSubjectKind,
    character_subject_for,
    monster_subject_for,
)
from world.art.worker import expected_output_identity
from world.lore.monsters import MONSTER_TIER_REGISTRY

# Placeholder kinds, exactly what the browser must show when no asset exists.
PLACEHOLDER_MISSING = "missing"
PLACEHOLDER_UNAVAILABLE = "unavailable"
PLACEHOLDER_LABELS = {
    PLACEHOLDER_MISSING: "未生成",
    PLACEHOLDER_UNAVAILABLE: "無法提供",
}


def _record_for(subject: ArtSubject) -> ArtAssetRecord | None:
    return ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()


def media_url_for(identity: str) -> str:
    """Build the same-origin media URL for a validated stored identity."""
    return f"/art/{identity}"


def _validated_output_identity(subject: ArtSubject, identity: str | None) -> str | None:
    """Return a presentable identity only when its expected file still exists."""
    if not isinstance(identity, str) or identity != expected_output_identity(subject):
        return None
    target = Path(settings.ART_STORE_ROOT) / identity
    if target.is_symlink():
        return None
    try:
        resolved = target.resolve()
        root = Path(settings.ART_STORE_ROOT).resolve()
    except OSError:
        return None
    if resolved == root or root not in resolved.parents or not resolved.is_file():
        return None
    return identity


def resolve_subject(subject: ArtSubject) -> dict:
    """Resolve a validated subject to its presentation payload.

    Returns status, same-origin URL, aspect ratio, and alternative text for a
    ``done`` record; a truthful placeholder kind/label otherwise. Never leaks
    ``out_path`` or the store root. A claimed ``in_progress`` record is
    normalized to the wire-stable ``pending`` status so a snapshot taken while
    a worker holds the claim renders a placeholder instead of failing the wire
    schema (fix-art-pipeline-contracts D3); the persistent record status is
    never touched.
    """
    record = _record_for(subject)
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
        }
    identity = _validated_output_identity(subject, record.db.output_identity)
    if identity is None:
        logger.log_warn(
            f"art presenter found missing or invalid output for {subject.full()}"
        )
        return _placeholder_unavailable("無法提供")
    return {
        "kind": "asset",
        "label": "已生成",
        "status": ArtAssetStatus.DONE,
        "url": media_url_for(identity),
        "aspect_ratio": record.db.aspect_ratio,
        "alt": subject.full(),
        "subject_key": subject.full(),
    }


def resolve_character(entity) -> dict:
    """Resolve a character's portrait through the adult gate and named policy.

    A gate-rejected subject resolves only to the unavailable placeholder with
    its explanatory label; the payload never contains a rejected prompt or an
    underage identity.
    """
    try:
        subject = character_subject_for(entity)
    except ArtSubjectError:
        subject = None
    if subject is None:
        return _placeholder_unavailable("無肖像")
    try:
        portrait_eligibility(entity)
    except Exception:
        return _placeholder_unavailable("無法提供")
    return resolve_subject(subject)


def resolve_entity(entity) -> dict:
    """Resolve one present entity's portrait by kind (design D3).

    A generic monster (``threat_tier`` resolving in ``MONSTER_TIER_REGISTRY``)
    resolves ``portrait:monster:<threat_tier>`` through
    ``monster_subject_for`` + ``resolve_subject`` with no adult gate. A
    character resolves through :func:`resolve_character` (explicit named
    policy plus both adult age gates). Anything else yields the unavailable
    placeholder. A rejected subject never returns a prompt, a subject key, or
    a URL.
    """
    threat_tier = getattr(entity, "threat_tier", None)
    if threat_tier in MONSTER_TIER_REGISTRY:
        try:
            subject = monster_subject_for(threat_tier)
        except ArtSubjectError:
            return _placeholder_unavailable("無法提供")
        payload = resolve_subject(subject)
        payload["subject_key"] = subject.full()
        return payload
    return resolve_character(entity)


def resolve_scene(archetype: str) -> dict:
    """Resolve a validated scene archetype to its presentation payload."""
    from world.art.subjects import scene_subject_for

    try:
        subject = scene_subject_for(archetype)
    except ArtSubjectError:
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
    }
