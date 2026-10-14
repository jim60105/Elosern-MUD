"""Same-origin media serving for validated art-store identities.

The route serves five closed identity vocabularies and nothing else:

* classic identities (``scene/``, ``portrait/monster/``, ``portrait/character/``)
  — served only when a ``done`` asset record references them (unchanged);
* gallery identities (``gallery/<kind>/<subject-key>/<image-id>.<ext>``) —
  served only when the gallery record addressed by the identity's OWN
  kind/subject-key segments holds a card whose stored identity equals the
  request exactly (a direct record lookup, never a scan of every record);
* built-in fallback identities (``defaults/<fallback-key>.<ext>``) — served
  from one fixed in-repo defaults directory (never the store root).
* official identities (``official/<fingerprint>/<root-relative-image-path>``) —
  served only when the startup official-artwork catalog's current snapshot
  indexes that exact root-relative path at that exact content fingerprint, so
  the request is answered from the catalog lookup alone: a caller-supplied
  filesystem path is never accepted, no historical artwork is retained for an
  outdated fingerprint, and nothing is ever copied into the store.
* bundled scene identities (``bundled-scene/<scene-key>/<sha256>.webp``) —
  served only when the startup bundled-scene snapshot admits that scene key at
  that exact fingerprint. The key is a closed allowlist of declared scene-art
  keys and the root is the FIXED in-repo ``web/static/art/scenes`` directory,
  which never overlaps ``ART_OFFICIAL_ROOT`` or ``ART_STORE_ROOT``: an operator
  file cannot replace a bundled identity or a terminal scene image, and a
  bundled request can never be answered from an operator root.

Every branch applies the same confinement discipline: path traversal,
symlinks, unexpected directories or extensions, absolute paths, and missing
or out-of-root identities all return 404 without exposing the store root
(design D8). The shared :func:`_serve_confined` helper is the one place that
turns a root plus a root-relative name into a response, so the five families
cannot drift into five definitions of "a confined, existing file".

**Admission versus serving, deliberately asymmetric.** Startup admission reads
each file through the no-follow primitives, which refuse a hard-linked or
oversized file; a served request resolves through
:func:`world.art.paths.resolved_under_root`, which rejects traversal and every
symlinked component but does not re-check the link count. That asymmetry is
accepted: the bytes are identical, the identity is fingerprint-authorized, and
the trusted bundled root is in-repo and git-tracked, so it is never
player-writable. As in the other four families, a component swapped for a
symlink between the confinement check and ``FileResponse``'s open could be
followed — the operator and bundled roots are read-only mounts/repository
paths, and the fingerprint admission is what bounds which paths are reachable
at all.
"""

from pathlib import Path
import re

from django.conf import settings
from django.http import FileResponse, Http404

from world.art import official
from world.art.gallery import cards_for
from world.art.paths import resolved_under_root, resolved_under_store_root
from world.art.fallback_keys import FALLBACK_EXTENSION, FALLBACK_KEYS
from world.art.scene_definitions import (
    BUNDLED_SCENE_EXTENSION,
    bundled_asset_filename,
    bundled_scene_root,
    current_bundled_scenes,
)
from world.art.store import ArtAssetRecord, ArtAssetStatus
from world.art.subjects import ArtSubject, ArtSubjectError, ArtSubjectKind
from world.lore.monster_visuals import is_registered_monster_visual_key

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
# `defaults/` (an unexpected sub-path never matches). The stem is then
# checked against the closed key vocabulary in ``_serve_defaults`` — a
# filename outside the six committed keys can never be served whatever the
# directory holds (gallery-builtin-fallbacks).
_DEFAULTS_IDENTITY = re.compile(r"^defaults/[^/]+\.(png|webp|jpg|avif)$")

# The exact official identity shape: `official/<fingerprint>/<root-relative
# path>`, each segment non-empty (so `..` or an empty segment can never match)
# and the extension from the same closed four store extensions. Matching the
# shape is only the cheap pre-gate: `_serve_official` then requires the
# catalog's snapshot to index that path at that fingerprint.
_OFFICIAL_IDENTITY = re.compile(
    r"^official/([^/]+)/((?:[^/]+/)*[^/]+\.(png|webp|jpg|avif))$"
)

# The exact bundled-scene identity shape: `bundled-scene/<scene-key>/<sha256>
# .webp`, the key one clean segment (never a sub-path) and the fingerprint
# exactly 64 lowercase hex digits. Matching the shape is only the cheap
# pre-gate: `_serve_bundled_scene` then requires the bundled snapshot to admit
# that key at that fingerprint.
_BUNDLED_SCENE_IDENTITY = re.compile(
    rf"^bundled-scene/([^/]+)/([0-9a-f]{{64}})\{BUNDLED_SCENE_EXTENSION}$"
)

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


def _referenced_by_done_record(identity: str) -> bool:
    if identity.startswith("portrait/monster/") and not any(identity.startswith(f"portrait/monster/{k}.") for k in [k for k in (identity.split("/")[2].split(".")[0],) if is_registered_monster_visual_key(k)]):
        return False
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
    if subject.kind is ArtSubjectKind.MONSTER and not is_registered_monster_visual_key(subject.key):
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


def _serve_confined(root: Path, relative_name: str) -> FileResponse:
    """Serve one root-relative file strictly confined to ``root``, or 404.

    The one shared open/response primitive of this boundary: the name is
    resolved through :func:`world.art.paths.resolved_under_root` (no traversal,
    no absolute path, no symlinked component, strictly inside the root) and
    must be an existing regular file, so a missing or escaping identity is an
    actual 404 — never a substitute image and never a successful status with
    no bytes.
    """
    resolved = resolved_under_root(root, relative_name)
    if resolved is None or not resolved.is_file():
        raise Http404
    return _serve(resolved)


def _serve_stored(identity: str) -> FileResponse:
    """The store-root pin of :func:`_serve_confined`, or 404."""
    resolved = resolved_under_store_root(identity)
    if resolved is None or not resolved.is_file():
        raise Http404
    return _serve(resolved)


def _serve_gallery(identity: str, match: re.Match) -> FileResponse:
    if not _referenced_by_gallery_card(identity, match.group(1), match.group(2)):
        raise Http404
    return _serve_stored(identity)


def _serve_defaults(identity: str) -> FileResponse:
    """Serve one committed fallback from the fixed in-repo defaults directory.

    The defaults directory is a separate, FIXED root — never the store root —
    resolved from the STATICFILES app dirs (overridable in tests). The shape
    gate is the closed key vocabulary: the flat ``<stem>.<ext>`` stem must be
    exactly one of the six committed fallback keys before the file is even
    looked up. Then the closed extension map (via the regex) and the same
    containment check as the other branches (resolves inside the defaults
    root, exists as a real file, no symlink). Anything else returns 404.
    Serving fallbacks through this one route keeps ``/art/`` the single media
    URL surface.
    """
    filename = identity[len("defaults/"):]
    if not filename.endswith(FALLBACK_EXTENSION):
        # The committed set is exactly ``<key>.webp`` — an alternate
        # extension for a valid stem is not a committed identity.
        raise Http404
    if filename[: -len(FALLBACK_EXTENSION)] not in FALLBACK_KEYS:
        raise Http404
    return _serve_confined(_defaults_root(), identity[len("defaults/"):])


def _serve_bundled_scene(match: re.Match) -> FileResponse:
    """Serve one snapshot-admitted bundled scene image under root confinement.

    The bundled snapshot lookup is the authorization: only a DECLARED scene-art
    key the current startup snapshot admits at exactly the requested
    fingerprint is served, so an unregistered key, an outdated fingerprint (the
    committed bytes were replaced and the server restarted) or a key no
    declaration names returns 404 — the closed scene-key allowlist is the
    snapshot itself, and no request ever reaches an operator root. The recorded
    filename is then re-resolved strictly inside the fixed in-repo scene
    directory through the shared confinement helper (no symlinked component,
    which also refuses a file swapped for a symlink after load).
    """
    key, fingerprint = match.group(1), match.group(2)
    if not current_bundled_scenes().admits(key, fingerprint):
        raise Http404
    return _serve_confined(bundled_scene_root(), bundled_asset_filename(key))


def _serve_official(match: re.Match) -> FileResponse:
    """Serve one catalog-admitted official image under root confinement.

    The catalog lookup is the authorization: only a root-relative path the
    current startup snapshot indexes at exactly the requested fingerprint is
    served, so an unindexed path, a stale fingerprint (the bytes were replaced
    and the server restarted), or a bogus fingerprint returns 404 — never
    another file and never a re-scan. The catalog's recorded identity is then
    re-resolved strictly inside ``ART_OFFICIAL_ROOT`` through the shared
    confinement helper (no symlinked component, no traversal), which also
    refuses a file swapped for a symlink after load.

    Like the gallery and defaults branches, the last step is a pathname open:
    a component swapped for a symlink between the confinement check and
    ``FileResponse``'s open could be followed. That residual race is accepted
    here for the same reason the other branches accept it — the official root
    is an operator-owned read-only mount, never a player-writable path — and
    the catalog contract (admission + fingerprint) is what bounds which paths
    can be reached at all.
    """
    fingerprint, relative_path = match.group(1), match.group(2)
    if not official.current_catalog().admits(relative_path, fingerprint):
        raise Http404
    return _serve_confined(Path(settings.ART_OFFICIAL_ROOT), relative_path)


def art_media(request, identity: str):
    """Serve one validated identity from the store, gallery, defaults, official, or bundled root."""
    if not identity:
        raise Http404
    bundled_match = _BUNDLED_SCENE_IDENTITY.fullmatch(identity)
    if bundled_match is not None:
        return _serve_bundled_scene(bundled_match)
    gallery_match = _GALLERY_IDENTITY.fullmatch(identity)
    if gallery_match is not None:
        return _serve_gallery(identity, gallery_match)
    if _DEFAULTS_IDENTITY.fullmatch(identity) is not None:
        return _serve_defaults(identity)
    official_match = _OFFICIAL_IDENTITY.fullmatch(identity)
    if official_match is not None:
        return _serve_official(official_match)
    if not _ALLOWED_IDENTITY.fullmatch(identity):
        raise Http404
    if not _referenced_by_done_record(identity):
        raise Http404
    return _serve_stored(identity)
