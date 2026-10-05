"""Read-only startup snapshot of the external official-artwork directory.

``official-artwork-catalog`` (source design §3, §4, §10): the game reads one
operator-prepared directory (``ART_OFFICIAL_ROOT``, the
``ART_SEED_ROOT``/``PROMPT_ROOT`` directory-root precedent) and indexes it ONCE
per boot into an in-memory snapshot. The layout is::

    <official root>/
      LICENSE
      monster/<species-key>/<image-file>
      preset/<preset-key>/<image-file>
      npc/<npc-or-profile-key>/<image-file>

The content kind is exactly ``monster``, ``preset``, or ``npc``; a content
directory's key identifies registered authored content (never a runtime
database row or a translated display name), and an image's root-relative path
is its stable official asset identity. A content directory may hold several
images plus an optional ``manifest.json`` (``default``, ``face_rect``,
``stage``, the seed-metadata convention) and MAY declare a default by filename.

**Snapshot-only, restart-only.** Ordinary resolution reads the snapshot; there
is no file watcher, hot activation, or refresh path, and this module never
calls Git, S3, an archive extractor, or an external host. Bytes replaced inside
the live root keep serving under the previously indexed identity and
fingerprint until the next restart (the documented maintenance-window
semantics).

**Nothing is written.** No code path here creates, renames, replaces, or
deletes any file under the root; the walker opens directories and files
``O_NOFOLLOW`` relative to verified parent fds through
:mod:`world.art.no_follow` (the same discipline the seed sync uses, defined
once there) and keeps everything in memory.

**Per-entry admission, never whole-root rejection.** A symlinked, out-of-root,
non-regular, unsupported-format, unreadable, undecodable, or oversized entry is
refused with one bounded diagnostic while every unrelated valid entry still
indexes; an unsupported top-level directory and a content key outside the
shared stable-key contract (or, for ``preset``, outside the player-preset
registry) are skipped the same way. The ``npc`` and ``monster`` kinds have no
registry membership check yet — the authored npc/profile provenance and the
monster species catalog land with their own changes — so those kinds index any
structurally valid key.

**One fingerprint per image, computed here.** :func:`_content_fingerprint` is
the sole hashing site and catalog load is its only caller: the digest is the
cache token in an official media URL, never re-derived per resolution or
request, never read from or written to a metadata file, and never a package
version. A request naming a fingerprint the current snapshot does not hold is
refused by the media route (a 404, no historical artwork retention).

**Observability.** Load emits exactly one ``official_art_catalog_loaded`` info
event carrying the indexed content-directory, image, and refused-entry counts
plus the empty/absent condition, and every per-entry refusal emits a bounded
diagnostic within a per-load budget (the suppressed count rides the boundary
event). No event context carries the configured absolute root — only
root-relative paths, kinds, and keys.

Imports stay on the deterministic-path side of the package: stdlib, Django
settings, Pillow, the gallery geometry validators, the shared confinement and
no-follow helpers, the shared stable-key contract, the player-preset registry,
and the observability facade — never the worker, the sd-webui client, or any
connectivity surface.
"""

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path
from stat import S_ISDIR, S_ISLNK, S_ISREG

from django.conf import settings
from PIL import Image

from world.art.formats import STORE_EXTENSIONS
from world.art.gallery import (
    GalleryRecordError,
    default_face_rect,
    identity_stage,
    validate_face_rect,
    validate_stage,
)
from world.art.no_follow import RejectedFile, open_dir_fd, open_file_bytes
from world.art.subjects import (
    FORBIDDEN_SUBJECT_KEY_CHARACTERS,
    MAX_SUBJECT_KEY_BYTES,
    MAX_SUBJECT_KEY_LENGTH,
)
from world.observability import log_info, log_warn

# The one boundary/diagnostic event id (design §11): the load boundary and the
# bounded per-entry refusals share it and carry a "phase" discriminator.
OFFICIAL_CATALOG_EVENT = "official_art_catalog_loaded"

# The manifest filename inside a content folder, and nothing else in the tree
# is ever parsed as one (the seed-metadata convention).
OFFICIAL_MANIFEST_FILENAME = "manifest.json"

# The closed content-kind vocabulary, in the documented layout order.
OFFICIAL_CONTENT_KINDS = ("monster", "preset", "npc")

# The exact manifest key contract: anything else makes the manifest invalid.
_MANIFEST_KEYS = frozenset({"default", "face_rect", "stage"})

# Kinds whose directory key is checked against a registry that exists today.
# ``npc``/``monster`` membership arrives with the authored npc/profile
# provenance and the separate monster species catalog respectively; until then
# those kinds admit any structurally valid key (never a tier or display name).
_REGISTRY_BACKED_KINDS = ("preset",)

# Per-load budget for bounded leaf diagnostics. Beyond it the walk still
# continues; only the event emission is capped and the suppressed count is
# reported in the boundary event.
_MAX_DIAGNOSTICS = 32

# Hard cap on any single file read from the (hostile-capable) official tree.
# Official images are kilobyte-to-megabyte media; anything past the cap is
# refused without being buffered into memory.
_MAX_FILE_BYTES = 32 * 1024 * 1024


@dataclass(frozen=True)
class OfficialImage:
    """One admitted official image and its load-time geometry."""

    identity: str
    kind: str
    key: str
    fingerprint: str
    image_size: dict
    face_rect: dict
    stage: dict


@dataclass(frozen=True)
class OfficialContent:
    """One indexed content directory: its kind/key and admitted images."""

    kind: str
    key: str
    default_identity: str | None
    images: tuple[str, ...]


@dataclass(frozen=True)
class _ContentManifest:
    """One content folder's parsed manifest (all three fields optional)."""

    default: str | None
    face_rect: dict | None
    stage: dict | None


class OfficialCatalog:
    """The immutable official-artwork snapshot a restart produced.

    Every lookup is an in-memory read: the media route admits a request only
    when :meth:`admits` finds the exact root-relative path at the exact current
    fingerprint, and presenters read identities/geometry/fingerprints from
    here instead of touching the filesystem.
    """

    def __init__(
        self,
        contents: Mapping[tuple[str, str], OfficialContent],
        images: Mapping[str, OfficialImage],
    ) -> None:
        self._contents = dict(contents)
        self._images = dict(images)

    def __len__(self) -> int:
        """The number of admitted images (an empty snapshot is falsy)."""
        return len(self._images)

    def identities(self) -> tuple[str, ...]:
        """Every admitted root-relative identity, deterministically ordered."""
        return tuple(sorted(self._images))

    def entry(self, identity: str) -> OfficialImage | None:
        """The admitted image for a root-relative identity, or ``None``."""
        return self._images.get(identity)

    def fingerprint_for(self, identity: str) -> str | None:
        """The current content fingerprint for an identity, or ``None``."""
        entry = self._images.get(identity)
        return entry.fingerprint if entry is not None else None

    def admits(self, identity: str, fingerprint: str) -> bool:
        """True when the snapshot indexes ``identity`` at exactly ``fingerprint``."""
        entry = self._images.get(identity)
        return entry is not None and entry.fingerprint == fingerprint

    def content(self, kind: str, key: str) -> OfficialContent | None:
        """The indexed content directory for a kind/key pair, or ``None``."""
        return self._contents.get((kind, key))

    def url_for(self, identity: str) -> str | None:
        """The same-origin official media URL for an admitted identity.

        ``None`` for an identity this snapshot does not admit, so a URL can
        never be built for unindexed artwork.
        """
        fingerprint = self.fingerprint_for(identity)
        if fingerprint is None:
            return None
        return f"/art/official/{fingerprint}/{identity}"


# The current snapshot: empty until the startup step loads it, empty again
# after a reset. A module global (not a settings read) because the snapshot IS
# the restart-scoped state this module owns.
_CATALOG = OfficialCatalog({}, {})


def current_catalog() -> OfficialCatalog:
    """The snapshot the last catalog load produced (empty before the first)."""
    return _CATALOG


def reset_catalog() -> None:
    """Drop the snapshot; the next load rebuilds it from the filesystem."""
    global _CATALOG
    _CATALOG = OfficialCatalog({}, {})


def fingerprint_for(identity: str) -> str | None:
    """The current snapshot's fingerprint for a root-relative identity."""
    return _CATALOG.fingerprint_for(identity)


class _Diagnostics:
    """Bounded diagnostic counter emitting capped facade events."""

    def __init__(self) -> None:
        self.emitted = 0
        self.suppressed = 0

    def emit(self, reason: str, **context: object) -> None:
        if self.emitted < _MAX_DIAGNOSTICS:
            self.emitted += 1
            log_warn(
                OFFICIAL_CATALOG_EVENT,
                context={"phase": "diagnostic", "reason": reason, **context},
            )
        else:
            self.suppressed += 1


def _content_fingerprint(payload: bytes) -> str:
    """The one content fingerprint of an image (sha256, the queue's convention)."""
    return hashlib.sha256(payload).hexdigest()


def _content_key_is_valid(key: str) -> bool:
    """True when ``key`` satisfies the shared stable-key contract.

    The rule set is the one every portrait/scene stable-key producer applies
    (no ``|``, ``/``, ``:``, ``{``, ``}``, or control character, at most 64
    characters and 200 UTF-8 bytes), read from its published constants so the
    two contracts cannot drift. A key outside it can never name registered
    authored content and is skipped with a bounded diagnostic.
    """
    if not key or len(key) > MAX_SUBJECT_KEY_LENGTH:
        return False
    if any(character in FORBIDDEN_SUBJECT_KEY_CHARACTERS for character in key):
        return False
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in key):
        return False
    return len(key.encode("utf-8")) <= MAX_SUBJECT_KEY_BYTES


def _registered_preset_keys() -> frozenset[str]:
    """The player-preset registry's keys — the ``preset`` kind's registry.

    Read per call from the immutable lore registry, so a directory keyed to a
    name no registry declares is skipped with a bounded diagnostic instead of
    indexing artwork nothing can ever reference.
    """
    from world.lore.player_presets import PLAYER_PRESET_REGISTRY

    return frozenset(PLAYER_PRESET_REGISTRY)


def _admit_image(payload: bytes) -> tuple[dict | None, str | None]:
    """Return ``(image_size, refusal_reason)`` with exactly one of them ``None``.

    Decoding reads the HEADER only (``Image.open`` + ``size``, never a pixel
    decode): a file declaring hostile dimensions is refused from its header
    under the same bounded limits the sd-webui client applies, so admission can
    never allocate a giant pixel buffer.
    """
    try:
        with Image.open(io.BytesIO(payload)) as image:
            width, height = image.size
    except Image.DecompressionBombError:  # observability: ignore R2: a bounded per-entry refusal is returned below
        return None, "image_too_large"
    except Exception:  # observability: ignore R2: a bounded per-entry refusal is returned below
        return None, "image_undecodable"
    if width <= 0 or height <= 0:
        return None, "image_undecodable"
    max_dimension = int(settings.ART_SD_MAX_IMAGE_DIMENSIONS)
    max_pixels = int(settings.ART_SD_MAX_IMAGE_PIXELS)
    if width > max_dimension or height > max_dimension or width * height > max_pixels:
        return None, "image_too_large"
    return {"width": width, "height": height}, None


def _parse_manifest(
    content_fd: int,
    admitted_names: set[str],
    diagnostics: _Diagnostics,
    kind: str,
    key: str,
) -> _ContentManifest:
    """Return one content folder's manifest, degrading WHOLE on any violation.

    An absent manifest is the documented silent fallback (an all-``None``
    manifest). Every violation — unreadable, symlinked, oversized, non-UTF-8,
    non-JSON, not an object, an unexpected key, an invalid ``face_rect`` or
    ``stage`` shape, or a ``default`` naming anything outside the ADMITTED
    images — yields the all-``None`` manifest after EXACTLY ONE diagnostic, so
    the directory's valid images still load with the fitted default rectangle
    and identity stage placement.
    """
    try:
        raw_bytes = open_file_bytes(
            OFFICIAL_MANIFEST_FILENAME, dir_fd=content_fd, max_bytes=_MAX_FILE_BYTES
        )
    except FileNotFoundError:  # observability: ignore R2: an absent manifest is the documented silent fallback
        return _ContentManifest(None, None, None)
    except OSError:  # observability: ignore R2: an unreadable manifest degrades whole via the diagnostic below
        diagnostics.emit("manifest_unreadable", kind=kind, key=key)
        return _ContentManifest(None, None, None)
    except RejectedFile:  # observability: ignore R2: degradation is the bounded diagnostic below
        diagnostics.emit("manifest_unreadable", kind=kind, key=key)
        return _ContentManifest(None, None, None)
    try:
        raw = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):  # observability: ignore R2: malformed JSON degrades whole via the diagnostic below
        diagnostics.emit("manifest_unreadable", kind=kind, key=key)
        return _ContentManifest(None, None, None)
    if not isinstance(raw, dict) or not set(raw) <= _MANIFEST_KEYS:
        diagnostics.emit("manifest_not_a_valid_object", kind=kind, key=key)
        return _ContentManifest(None, None, None)
    face_rect = None
    if "face_rect" in raw:
        try:
            face_rect = validate_face_rect(raw["face_rect"])
        except GalleryRecordError:  # observability: ignore R2: an invalid rectangle degrades whole via the diagnostic below
            diagnostics.emit("manifest_invalid_face_rect", kind=kind, key=key)
            return _ContentManifest(None, None, None)
    stage = None
    if "stage" in raw:
        try:
            stage = validate_stage(raw["stage"])
        except GalleryRecordError:  # observability: ignore R2: an invalid stage degrades whole via the diagnostic below
            diagnostics.emit("manifest_invalid_stage", kind=kind, key=key)
            return _ContentManifest(None, None, None)
    default_name = raw.get("default")
    if default_name is None:
        return _ContentManifest(None, face_rect, stage)
    if not isinstance(default_name, str) or default_name not in admitted_names:
        diagnostics.emit("manifest_default_not_an_admitted_file", kind=kind, key=key)
        return _ContentManifest(None, None, None)
    return _ContentManifest(default_name, face_rect, stage)


def _admitted_entries(
    kind: str,
    key: str,
    content_fd: int,
    diagnostics: _Diagnostics,
    counters: dict[str, int],
) -> list[tuple[str, bytes, dict]]:
    """Admit one content folder's images: ``(filename, payload, image_size)``.

    Listing order is sorted filename order (the deterministic order the default
    rule and the snapshot rely on). Every refusal is per-entry: one bounded
    diagnostic and the walk continues, so the remaining valid images in this
    folder and every other folder still index.
    """
    try:
        names = sorted(os.listdir(content_fd))
    except OSError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
        diagnostics.emit("content_directory_unreadable", kind=kind, key=key)
        return []
    admitted: list[tuple[str, bytes, dict]] = []
    for name in names:
        if name == OFFICIAL_MANIFEST_FILENAME:
            continue
        try:
            stat_result = os.lstat(name, dir_fd=content_fd)
        except OSError:  # observability: ignore R2: a vanished listing entry is a silent no-op
            continue
        if S_ISLNK(stat_result.st_mode):
            counters["refused"] += 1
            diagnostics.emit("symlink_skipped", kind=kind, key=key, entry=name)
            continue
        if S_ISDIR(stat_result.st_mode):
            counters["refused"] += 1
            diagnostics.emit("nested_directory_skipped", kind=kind, key=key, entry=name)
            continue
        if not S_ISREG(stat_result.st_mode):
            counters["refused"] += 1
            diagnostics.emit("non_regular_entry_skipped", kind=kind, key=key, entry=name)
            continue
        if Path(name).suffix not in STORE_EXTENSIONS:
            counters["refused"] += 1
            diagnostics.emit(
                "unsupported_extension_skipped", kind=kind, key=key, entry=name
            )
            continue
        try:
            payload = open_file_bytes(name, dir_fd=content_fd, max_bytes=_MAX_FILE_BYTES)
        except OSError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
            counters["refused"] += 1
            diagnostics.emit("source_unreadable", kind=kind, key=key, entry=name)
            continue
        except RejectedFile:  # observability: ignore R2: reported through the bounded diagnostic emitter below
            counters["refused"] += 1
            diagnostics.emit("source_rejected", kind=kind, key=key, entry=name)
            continue
        image_size, refusal = _admit_image(payload)
        if image_size is None:
            counters["refused"] += 1
            diagnostics.emit(refusal or "image_undecodable", kind=kind, key=key, entry=name)
            continue
        admitted.append((name, payload, image_size))
    return admitted


def _index_content(
    kind: str,
    key: str,
    kind_fd: int,
    contents: dict[tuple[str, str], OfficialContent],
    images: dict[str, OfficialImage],
    diagnostics: _Diagnostics,
    counters: dict[str, int],
) -> None:
    """Index one ``<kind>/<key>/`` folder; never raises."""
    try:
        content_fd = open_dir_fd(key, dir_fd=kind_fd)
    except OSError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
        counters["refused"] += 1
        diagnostics.emit("content_directory_unreadable", kind=kind, key=key)
        return
    try:
        admitted = _admitted_entries(kind, key, content_fd, diagnostics, counters)
        if not admitted:
            return
        manifest = _parse_manifest(
            content_fd, {name for name, _, _ in admitted}, diagnostics, kind, key
        )
    finally:
        os.close(content_fd)
    identities: list[str] = []
    for name, payload, image_size in admitted:
        identity = f"{kind}/{key}/{name}"
        face_rect = default_face_rect(image_size)
        if manifest.face_rect is not None:
            try:
                face_rect = validate_face_rect(manifest.face_rect, image_size=image_size)
            except GalleryRecordError:  # observability: ignore R2: the fitted per-image rectangle already applies
                diagnostics.emit(
                    "manifest_face_rect_inapplicable", kind=kind, key=key, entry=name
                )
        stage = manifest.stage if manifest.stage is not None else identity_stage()
        images[identity] = OfficialImage(
            identity=identity,
            kind=kind,
            key=key,
            fingerprint=_content_fingerprint(payload),
            image_size=dict(image_size),
            face_rect=dict(face_rect),
            stage=dict(stage),
        )
        identities.append(identity)
    default_name = manifest.default or admitted[0][0]
    contents[(kind, key)] = OfficialContent(
        kind=kind,
        key=key,
        default_identity=f"{kind}/{key}/{default_name}",
        images=tuple(identities),
    )
    counters["contents"] += 1
    counters["images"] += len(identities)


def _index_kind(
    kind: str,
    kind_name: str,
    root_fd: int,
    contents: dict[tuple[str, str], OfficialContent],
    images: dict[str, OfficialImage],
    diagnostics: _Diagnostics,
    counters: dict[str, int],
) -> None:
    """Index one known content-kind directory; never raises."""
    try:
        kind_fd = open_dir_fd(kind_name, dir_fd=root_fd)
    except OSError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
        counters["refused"] += 1
        diagnostics.emit("kind_directory_unreadable", kind=kind)
        return
    try:
        try:
            content_names = sorted(os.listdir(kind_fd))
        except OSError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
            counters["refused"] += 1
            diagnostics.emit("kind_directory_unreadable", kind=kind)
            return
        for content_name in content_names:
            try:
                stat_result = os.lstat(content_name, dir_fd=kind_fd)
            except OSError:  # observability: ignore R2: a vanished listing entry is a silent no-op
                continue
            if S_ISLNK(stat_result.st_mode):
                counters["refused"] += 1
                diagnostics.emit(
                    "symlinked_content_directory_skipped", kind=kind, entry=content_name
                )
                continue
            if not S_ISDIR(stat_result.st_mode):
                # A stray file at kind level (README, license copy, ...) is not
                # a content directory and carries no identity to report.
                continue
            if not _content_key_is_valid(content_name):
                counters["refused"] += 1
                diagnostics.emit(
                    "invalid_content_key_skipped", kind=kind, key=content_name
                )
                continue
            if kind in _REGISTRY_BACKED_KINDS and content_name not in _registered_preset_keys():
                counters["refused"] += 1
                diagnostics.emit(
                    "unknown_registry_reference", kind=kind, key=content_name
                )
                continue
            _index_content(
                kind,
                content_name,
                kind_fd,
                contents,
                images,
                diagnostics,
                counters,
            )
    finally:
        os.close(kind_fd)


def _record(
    contents: dict[tuple[str, str], OfficialContent],
    images: dict[str, OfficialImage],
    counters: dict[str, int],
    diagnostics: _Diagnostics,
    reason: str,
) -> dict:
    """Publish the snapshot and emit the single boundary event."""
    global _CATALOG
    _CATALOG = OfficialCatalog(contents, images)
    summary = {
        "skipped": not images,
        **counters,
        "diagnostics": diagnostics.emitted,
        "suppressed_diagnostics": diagnostics.suppressed,
    }
    log_info(
        OFFICIAL_CATALOG_EVENT,
        context={"phase": "loaded", "reason": reason, **summary},
    )
    return summary


def load_catalog() -> dict:
    """Index the official-artwork root once (startup step); never raises.

    Returns a non-empty summary dict (also emitted as the single
    ``official_art_catalog_loaded`` boundary event): the indexed
    content-directory, image, and refused-entry counts plus the diagnostic
    budget counters. An unset, absent, symlinked, unreadable, or empty root is
    a supported no-art configuration: the snapshot is empty, one bounded info
    event names the condition, and startup proceeds with the existing
    runtime-art and fallback behavior unchanged. The outermost catch exists
    only for unforeseen faults — a broken artwork tree is never a startup
    failure. Nothing is acquired here: the walk is the only I/O.
    """
    counters: dict[str, int] = {"contents": 0, "images": 0, "refused": 0}
    diagnostics = _Diagnostics()
    try:
        configured = str(getattr(settings, "ART_OFFICIAL_ROOT", "") or "")
        root = Path(configured)
        if not configured.strip():
            return _record({}, {}, counters, diagnostics, "official_root_unset")
        if root.is_symlink():
            return _record({}, {}, counters, diagnostics, "official_root_symlink")
        if not root.is_dir():
            return _record({}, {}, counters, diagnostics, "official_root_absent")
        try:
            root_fd = open_dir_fd(str(root))
        except OSError:  # observability: ignore R2: the unreadable-root reason below is the one bounded event
            return _record({}, {}, counters, diagnostics, "official_root_unreadable")
        contents: dict[tuple[str, str], OfficialContent] = {}
        images: dict[str, OfficialImage] = {}
        try:
            try:
                top_level = sorted(os.listdir(root_fd))
            except OSError:  # observability: ignore R2: the unreadable-root reason below is the one bounded event
                return _record({}, {}, counters, diagnostics, "official_root_unreadable")
            for entry_name in top_level:
                try:
                    stat_result = os.lstat(entry_name, dir_fd=root_fd)
                except OSError:  # observability: ignore R2: a vanished listing entry is a silent no-op
                    continue
                if S_ISLNK(stat_result.st_mode):
                    counters["refused"] += 1
                    diagnostics.emit("symlinked_root_entry_skipped", entry=entry_name)
                    continue
                if not S_ISDIR(stat_result.st_mode):
                    # The root's ``LICENSE`` and other plain files carry no
                    # content identity; only directories can hold artwork.
                    continue
                if entry_name not in OFFICIAL_CONTENT_KINDS:
                    counters["refused"] += 1
                    diagnostics.emit("unknown_kind_directory_skipped", entry=entry_name)
                    continue
                _index_kind(
                    entry_name,
                    entry_name,
                    root_fd,
                    contents,
                    images,
                    diagnostics,
                    counters,
                )
        finally:
            os.close(root_fd)
        return _record(
            contents,
            images,
            counters,
            diagnostics,
            "official_root_indexed" if images else "official_root_empty",
        )
    except Exception as error:
        log_warn(
            OFFICIAL_CATALOG_EVENT,
            context={"phase": "loaded", "reason": "catalog_load_failed", **counters},
            exc=error,
        )
        reset_catalog()
        return {"skipped": True, **counters}
