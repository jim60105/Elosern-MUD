"""Same-origin media serving for validated art-store identities.

The route serves three closed identity vocabularies and nothing else:

* classic identities (``scene/``, ``portrait/monster/``, ``portrait/character/``)
  — served only when a ``done`` asset record references them (unchanged);
* gallery identities (``gallery/<kind>/<subject-key>/<image-id>.<ext>``) —
  served only when the gallery record addressed by the identity's OWN
  kind/subject-key segments holds a card whose stored identity equals the
  request exactly (a direct record lookup, never a scan of every record);
* built-in fallback identities (``defaults/<fallback-key>.<ext>``) — served
  from one fixed in-repo defaults directory (never the store root).

Every branch applies the same confinement discipline: path traversal,
symlinks, unexpected directories or extensions, absolute paths, and missing
or out-of-root identities all return 404 without exposing the store root
(design D8).
"""

from pathlib import Path
import re

from django.conf import settings
from django.http import FileResponse, Http404

from world.art.gallery import cards_for
from world.art.paths import resolved_under_root, resolved_under_store_root
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectError, ArtSubjectKind

# Only these exact store layouts are servable: the scene and portrait
# directories with ANY of the four store extensions — the closed set of all
# formats the engine can produce, never the currently configured format
# alone, so a store mid-way through a format switch stays servable. Each
# extension maps to exactly one media type; there is no sniffing.
_ALLOWED_IDENTITY = re.compile(
    r"^(scene|portrait/monster|portrait/character)/[^/]+\.(png|webp|jpg|avif)$"
)

# The exact gallery identity shape: kind is exactly `character` or `monster`,
# the subject key and image id are single clean segments, and the extension
# is one of the same closed four store extensions.
_GALLERY_IDENTITY = re.compile(
    r"^gallery/(character|monster)/([^/]+)/[^/]+\.(png|webp|jpg|avif)$"
)

# The exact built-in fallback identity shape: one flat segment under
# `defaults/` (an unexpected sub-path never matches).
_DEFAULTS_IDENTITY = re.compile(r"^defaults/[^/]+\.(png|webp|jpg|avif)$")

_MIME_BY_EXTENSION = {
    ".png": "image/png",
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".avif": "image/avif",
}

_GALLERY_KINDS = {
    "character": ArtSubjectKind.CHARACTER,
    "monster": ArtSubjectKind.MONSTER,
}


def _store_root() -> Path:
    return Path(settings.ART_STORE_ROOT)


def _resolved_under_root(path: Path) -> Path | None:
    try:
        resolved = path.resolve()
    except OSError:
        return None
    root = _store_root().resolve()
    if resolved == root or root not in resolved.parents:
        return None
    return resolved


def _referenced_by_done_record(identity: str) -> bool:
    for record in ArtAssetRecord.objects.all():
        if (
            record.db.status == ArtAssetStatus.DONE
            and record.db.output_identity == identity
        ):
            return True
    return False


def _referenced_by_gallery_card(identity: str, kind_text: str, subject_key: str) -> bool:
    """True when the addressed subject's gallery record references ``identity``.

    The subject comes from the identity's own segments, so this is a direct
    record lookup (``cards_for`` reads exactly one record by key) — never a
    scan over every record. A subject the segments cannot name references
    nothing; a card of ANOTHER subject never admits this identity.
    """
    try:
        subject = ArtSubject(_GALLERY_KINDS[kind_text], subject_key)
    except (ArtSubjectError, KeyError):
        return False
    return any(card["stored_identity"] == identity for card in cards_for(subject))


def _defaults_root() -> Path:
    """The fixed in-repo defaults directory (never the store root).

    Pinned to the first staticfiles directory (``web/static``), i.e. the
    design's ``web/static/art/defaults/``; settings-derived, not
    env-configurable, and read per call so tests can redirect it.
    """
    return Path(settings.STATICFILES_DIRS[0]) / "art" / "defaults"


def _serve(resolved: Path) -> FileResponse:
    return FileResponse(
        resolved.open("rb"),
        content_type=_MIME_BY_EXTENSION[resolved.suffix.lower()],
    )


def _serve_gallery(identity: str, match: re.Match) -> FileResponse:
    if not _referenced_by_gallery_card(identity, match.group(1), match.group(2)):
        raise Http404
    resolved = resolved_under_store_root(identity)
    if resolved is None or not resolved.is_file():
        raise Http404
    return _serve(resolved)


def _serve_defaults(identity: str) -> FileResponse:
    resolved = resolved_under_root(_defaults_root(), identity[len("defaults/"):])
    if resolved is None or not resolved.is_file():
        raise Http404
    return _serve(resolved)


def art_media(request, identity: str):
    """Serve one validated identity from the store, gallery, or defaults dir."""
    if not identity:
        raise Http404
    gallery_match = _GALLERY_IDENTITY.fullmatch(identity)
    if gallery_match is not None:
        return _serve_gallery(identity, gallery_match)
    if _DEFAULTS_IDENTITY.fullmatch(identity) is not None:
        return _serve_defaults(identity)
    if not _ALLOWED_IDENTITY.fullmatch(identity):
        raise Http404
    if not _referenced_by_done_record(identity):
        raise Http404
    target = _store_root() / identity
    if target.is_symlink():
        raise Http404
    resolved = _resolved_under_root(target)
    if resolved is None or not resolved.is_file():
        raise Http404
    return _serve(resolved)
