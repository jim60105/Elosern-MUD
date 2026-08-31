"""Same-origin media serving for validated art-store identities.

The route serves only an output identity referenced by a ``done`` asset record
-- never an arbitrary path under the store root -- after applying the same
confinement check the worker uses. Path traversal, symlinks, unexpected
directories or extensions, absolute paths, and missing or out-of-root
identities all return 404 without exposing the store root (design D8).
"""

from pathlib import Path
import re

from django.conf import settings
from django.http import FileResponse, Http404

from world.art.store import ArtAssetRecord, ArtAssetStatus

# Only these exact store layouts are servable: the scene and portrait
# directories with ANY of the four store extensions — the closed set of all
# formats the engine can produce, never the currently configured format
# alone, so a store mid-way through a format switch stays servable. Each
# extension maps to exactly one media type; there is no sniffing.
_ALLOWED_IDENTITY = re.compile(
    r"^(scene|portrait/monster|portrait/character)/[^/]+\.(png|webp|jpg|avif)$"
)

_MIME_BY_EXTENSION = {
    ".png": "image/png",
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".avif": "image/avif",
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


def art_media(request, identity: str):
    """Serve one stored asset identity referenced by a done record."""
    if not identity or not _ALLOWED_IDENTITY.fullmatch(identity):
        raise Http404
    if not _referenced_by_done_record(identity):
        raise Http404
    target = _store_root() / identity
    if target.is_symlink():
        raise Http404
    resolved = _resolved_under_root(target)
    if resolved is None or not resolved.is_file():
        raise Http404
    return FileResponse(
        resolved.open("rb"),
        content_type=_MIME_BY_EXTENSION[resolved.suffix.lower()],
    )
