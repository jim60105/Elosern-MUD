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
      scene/<scene-key>/<image-file>
      room/<room-art-key>/<image-file>

The INDEX content kind is exactly ``monster``, ``preset``, ``npc``, ``scene``,
or ``room`` (``unified-scene-catalog`` added the last two); a content
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
shared stable-key contract (or outside the kind's authored registry, for the
registry-backed ``preset``, ``scene`` and ``room`` kinds) are skipped the same
way. The ``npc`` and ``monster`` kinds have no registry membership check yet —
the authored npc/profile provenance and the monster species catalog land with
their own changes — so those kinds index any structurally valid key.

**The bundled scene collection is admitted alongside.** ``load_catalog``
publishes ``world.art.scene_definitions``' bundled snapshot FIRST and
unconditionally, on every exit path: the eleven committed scene illustrations
must serve in the no-operator-art configuration that absence is exactly for.
The two publishes are independent (neither can zero the other), and the
bundled collection has its own event id, so this catalog's contract of exactly
one ``official_art_catalog_loaded`` boundary event per load is untouched. This
module references ``world.art.scene_definitions`` only INSIDE function bodies
— that module imports this one's shared bounded decoder at import time.

**One fingerprint per image, computed here.** :func:`_content_fingerprint` is
the sole hashing site and catalog load is its only caller: the digest is the
cache token in an official media URL, never re-derived per resolution or
request, never read from or written to a metadata file, and never a package
version. A request naming a fingerprint the current snapshot does not hold is
refused by the media route (a 404, no historical artwork retention).

Admission validates the image HEADER only (dimensions from ``Image.open``
under the bounded limits, never a pixel decode) so a hostile file cannot make
startup allocate a giant buffer; a file whose header is valid but whose pixel
stream is truncated is therefore admitted and served as-is, exactly like the
seed mirror's accepted images, and the browser falls back to the built-in
silhouette when the download fails to render.

**Observability.** Load emits exactly one ``official_art_catalog_loaded`` info
event carrying the indexed content-directory, image, and refused-entry counts
plus the empty/absent condition, and every per-entry refusal emits a bounded
diagnostic within a per-load budget (the suppressed count rides the boundary
event). No event context carries the configured absolute root — only
root-relative paths, kinds, and keys.

**Bounded startup facts are RETAINED on the snapshot.**
``art-source-fault-facts``: the load keeps three bounded fact families beside
the admitted images, so an empty index can never erase why a source is absent
or broken and resolution can tell the normal no-art configuration from an
actual failure:

* the root's :class:`RootHealth` — a deliberately absent DEFAULT optional root,
  an available-but-empty root, an indexed root, or a retained availability
  failure (an explicitly configured root that is missing, and every
  refused/unreadable/unusable root in any configuration);
* the per-content :class:`SourceFault` tuple — a manifest-declared default that
  was missing or refused, recorded BEFORE the deterministic substitute, and the
  metadata fault of each image whose declared geometry was replaced by the
  fitted one (a fault of an unselected rejected sibling is never promoted: it
  stays an operational diagnostic);
* the per-entry refusal reason of every refused image candidate, keyed by the
  root-relative identity the caller already knows.

Every retained value is bounded — a closed reason token, or a root-relative
identity built from a validated single-segment filename, never an echoed raw
manifest string, an absolute root, or exception text. The facts are recorded
independently of the diagnostic emission budget, and reading one is a single
in-memory lookup for a supplied identity: never an enumeration and never a
filesystem probe. The refusal map is the one fact whose SIZE follows the tree
(one small entry per refused candidate, for the restart's lifetime) rather than
the per-load diagnostic budget: silently capping it would make a lookup for a
supplied identity claim "healthy" about an entry the load actually refused. Its
peak footprint stays the order of the listing the walk already materializes.

Imports stay on the deterministic-path side of the package: stdlib, Django
settings, Pillow, the gallery geometry validators, the shared confinement and
no-follow helpers, the shared stable-key contract, the authored lore/art
registries, and the observability facade — never the worker, the sd-webui
client, or any connectivity surface.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import io
import json
import os
from pathlib import Path
from stat import S_ISDIR, S_ISLNK, S_ISREG
from urllib.parse import quote

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
from world.art.subjects import is_valid_subject_key
from world.observability import log_info, log_warn

# The one boundary/diagnostic event id (design §11): the load boundary and the
# bounded per-entry refusals share it and carry a "phase" discriminator.
OFFICIAL_CATALOG_EVENT = "official_art_catalog_loaded"

# The manifest filename inside a content folder, and nothing else in the tree
# is ever parsed as one (the seed-metadata convention).
OFFICIAL_MANIFEST_FILENAME = "manifest.json"

# The closed ENTITY-REFERENCE content-kind vocabulary, in the documented
# layout order. It is the vocabulary ``world.art.official_refs`` mirrors for
# entity-carried official references (``official-content-provenance``): a kind
# here must have a provenance attribute that resolver can map, so extending it
# is a data-owner change, never an indexing change.
OFFICIAL_CONTENT_KINDS = ("monster", "preset", "npc")

# The closed INDEX layout vocabulary, in the documented layout order. This is
# the vocabulary the startup walk accepts: the reference vocabulary above plus
# the two operator-only content kinds ``unified-scene-catalog`` adds, whose
# entity metadata is owned by the map owner and the scene renderer.
OFFICIAL_LAYOUT_KINDS = OFFICIAL_CONTENT_KINDS + ("scene", "room")

# The exact manifest key contract: anything else makes the manifest invalid.
_MANIFEST_KEYS = frozenset({"default", "face_rect", "stage"})

# Kinds whose directory key is checked against a registry that exists today.
# ``npc``/``monster`` membership arrives with the authored npc/profile
# provenance and the separate monster species catalog respectively; until then
# those kinds admit any structurally valid key (never a tier or display name).
_REGISTRY_BACKED_KINDS = ("preset", "scene", "room")


# Per-load budget for bounded leaf diagnostics. Beyond it the walk still
# continues; only the event emission is capped and the suppressed count is
# reported in the boundary event.
_MAX_DIAGNOSTICS = 32

# The closed reason vocabulary of the RETAINED source facts. These are the
# batch's canonical closed reasons (the unified-image design's "closed reasons"
# list), so a fact is always one bounded token — never a raw path, an echoed
# manifest string, or exception text. The same tokens are what the descriptor
# owners consume at each selected chain slot.
SOURCE_REASON_UNAVAILABLE = "source_unavailable"
SOURCE_REASON_REJECTED = "source_rejected"
SOURCE_REASON_REFERENCE_MISSING = "explicit_reference_missing"
SOURCE_REASON_METADATA_INVALID = "metadata_invalid"

# The closed fact scopes: a fault attributable to a content directory's
# manifest-declared default (it precedes every deterministic substitute) or to
# one admitted image whose declared metadata was replaced by the fitted one,
# plus the availability failure of one authorized content directory the walk
# could not enumerate at all.
SOURCE_SCOPE_DEFAULT = "default"
SOURCE_SCOPE_METADATA = "metadata"
SOURCE_SCOPE_SOURCE = "source"

# The closed root-health vocabulary of one load. ``absent_default`` is the
# normal no-art configuration (a deliberately unbound or deliberately empty
# optional root, or an absent DEFAULT root); ``unavailable`` is a retained
# availability failure in every configuration.
ROOT_STATE_ABSENT = "absent_default"
ROOT_STATE_EMPTY = "empty"
ROOT_STATE_INDEXED = "indexed"
ROOT_STATE_UNAVAILABLE = "unavailable"

# The boundary reasons whose condition is an availability failure REGARDLESS of
# provenance: a refused symlinked root and any I/O or usability failure are
# never the deliberate "no official artwork" absence.
_ROOT_FAULT_REASONS = frozenset(
    {
        "official_root_symlink",
        "official_root_unreadable",
        "official_root_not_a_directory",
        "catalog_load_failed",
    }
)

# The bound of a manifest-declared default filename retained as a source
# identity (the filesystem's own single-name bound). A longer value is never
# echoed; the manifest simply degrades whole as an inadmissible default.
_MAX_DECLARED_DEFAULT_LENGTH = 255

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
    # The manifest-DECLARED default identity of this directory (the request),
    # retained beside the EFFECTIVE ``default_identity`` (the selection) so a
    # consumer can see that a declared default was accepted without re-reading
    # anything. ``None`` when the directory's manifest declared no default.
    requested_default: str | None = None


@dataclass(frozen=True)
class _ContentManifest:
    """One content folder's parsed manifest (all three fields optional).

    ``declared_default`` and ``invalid_reason`` are the retained FACTS of the
    parse, kept BESIDE the degraded fields rather than instead of them: the
    bounded single-file name the manifest asked for (``None`` when it declared
    none, or declared a value that is not a bounded filename and is therefore
    never echoed as an identity), and the bounded token of the one violation
    that degraded the manifest whole (``None`` when the manifest was absent or
    fully applied).
    """

    default: str | None
    face_rect: dict | None
    stage: dict | None
    declared_default: str | None = None
    invalid_reason: str | None = None


@dataclass(frozen=True)
class RootHealth:
    """One load's bounded root availability fact, retained on the snapshot.

    ``state`` is one of the closed ``ROOT_STATE_*`` tokens, ``configured``
    records whether the environment explicitly bound ``ART_OFFICIAL_ROOT`` at
    settings import, ``fault`` is True only for a retained availability failure
    (a deliberately absent default optional root is normal, never a fault), and
    ``reason`` is the boundary reason token of the same load.
    """

    state: str
    configured: bool
    fault: bool
    reason: str


@dataclass(frozen=True)
class SourceFault:
    """One bounded startup fault attributed to one requested art source.

    ``scope`` is ``default`` for a fault attributable to a content directory's
    manifest-declared default — recorded BEFORE any deterministic substitute —
    and ``metadata`` for rejected/inapplicable manifest metadata that forced
    safe fitted geometry for one admitted image. ``identity`` is the
    root-relative identity the fault belongs to (the declared default, or the
    admitted image), and ``reason`` is one closed ``SOURCE_REASON_*`` token.
    """

    scope: str
    identity: str
    reason: str


@dataclass
class _LoadFacts:
    """The mutable per-load fact accumulators (published immutably on the snapshot).

    Never read on the wire: :meth:`_record` hands these to the frozen
    :class:`OfficialCatalog`, which is the only reader.
    """

    configured: bool = False
    source_faults: dict[tuple[str, str], tuple[SourceFault, ...]] = field(
        default_factory=dict
    )
    refusals: dict[str, str] = field(default_factory=dict)


class OfficialCatalog:
    """The immutable official-artwork snapshot a restart produced.

    Every lookup is an in-memory read: the media route admits a request only
    when :meth:`admits` finds the exact root-relative path at the exact current
    fingerprint, and presenters read identities/geometry/fingerprints from
    here instead of touching the filesystem. The snapshot also retains the
    bounded startup facts of the load that produced it — its
    :class:`RootHealth`, the per-content :class:`SourceFault` tuples and the
    per-entry refusal reasons — so an empty index can never erase why a source
    is absent or broken.
    """

    def __init__(
        self,
        contents: Mapping[tuple[str, str], OfficialContent],
        images: Mapping[str, OfficialImage],
        root_health: RootHealth | None = None,
        source_faults: Mapping[tuple[str, str], tuple[SourceFault, ...]] | None = None,
        refusals: Mapping[str, str] | None = None,
    ) -> None:
        self._contents = dict(contents)
        self._images = dict(images)
        self._root_health = root_health
        self._source_faults = dict(source_faults or {})
        self._refusals = dict(refusals or {})
        # The identity-scoped view of the metadata faults: one lookup for the
        # exact image a chain selected, so a consumer never has to treat every
        # fault of a content directory as applicable to that image.
        self._identity_faults = {
            fault.identity: fault
            for faults in self._source_faults.values()
            for fault in faults
            if fault.scope == SOURCE_SCOPE_METADATA
        }

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

    def root_health(self) -> RootHealth | None:
        """The retained root availability fact of the last load.

        ``None`` only before the first load (an empty pre-load snapshot): a load
        always retains one, including when its index is empty.
        """
        return self._root_health

    def source_faults(self, kind: str, key: str) -> tuple[SourceFault, ...]:
        """The bounded faults attributed to one content source, in chain order.

        A manifest-declared-default fault comes FIRST (it precedes every
        deterministic substitute), then the metadata faults of the admitted
        images in deterministic identity order. Empty for an unknown source and
        for a source with no retained fault: an unselected refused sibling
        stays an operational diagnostic and never taints a healthy source.
        """
        return self._source_faults.get((kind, key), ())

    def fault_for(self, identity: str) -> SourceFault | None:
        """The bounded metadata fault attributed to one exact admitted image.

        ``None`` for an image whose declared metadata was applied as written —
        including an image whose sibling was refused (a refusal is an
        operational diagnostic, never a fault of this identity). An image whose
        directory degraded its manifest WHOLE has its declared metadata replaced
        by the fitted one, so it carries ``metadata_invalid``; that is a
        separate fact from the directory's declared-default fault, which
        :meth:`source_faults` reports under the declared identity instead.
        """
        return self._identity_faults.get(identity)

    def refusal_reason(self, identity: str) -> str | None:
        """The bounded admission-refusal reason recorded for one identity.

        ``None`` when the identity was admitted (or was never a candidate this
        load saw). The reason is the bounded diagnostic token of one per-entry
        refusal, keyed by the identity the caller already knows: a refused
        identity keeps its reason even after the diagnostic emission budget is
        exhausted, and this read is never an enumeration or a filesystem probe.
        """
        return self._refusals.get(identity)

    def url_for(self, identity: str) -> str | None:
        """The same-origin official media URL for an admitted identity.

        ``None`` for an identity this snapshot does not admit, so a URL can
        never be built for unindexed artwork. The identity is
        percent-encoded segment-wise (slashes kept), because a content key or
        filename may legally contain a space, ``#``, ``?``, or ``%`` — an
        unencoded reserved character would make the URL unfetchable. The
        server decodes the path before routing, so the served identity is the
        admitted one exactly.
        """
        fingerprint = self.fingerprint_for(identity)
        if fingerprint is None:
            return None
        return f"/art/official/{fingerprint}/{quote(identity, safe='/')}"


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


def _registered_preset_keys() -> frozenset[str]:
    """The player-preset registry's keys — the ``preset`` kind's registry.

    Read per call from the immutable lore registry, so a directory keyed to a
    name no registry declares is skipped with a bounded diagnostic instead of
    indexing artwork nothing can ever reference.
    """
    from world.lore.player_presets import PLAYER_PRESET_REGISTRY

    return frozenset(PLAYER_PRESET_REGISTRY)


def _registered_scene_keys() -> frozenset[str]:
    """The authored scene-art keys — the ``scene`` kind's registry.

    The closed eleven-key vocabulary (every registered archetype plus the
    explicit dream type) the bundled collection and the media boundary use, so
    an operator ``scene/<key>/`` directory can only name a scene that actually
    exists in the game. Imported per call (this module may not import the art
    definitions at module level; see the module docstring).
    """
    from world.art.scene_definitions import SCENE_ART_DEFINITIONS

    return frozenset(SCENE_ART_DEFINITIONS)


def _registered_room_art_keys() -> frozenset[str]:
    """The authored room-art keys — the ``room`` kind's registry.

    The closed vocabulary of authored room content the map owner declares
    ``room_art_key`` metadata from; a ``room/<key>/`` directory keyed to a
    room no authored place declares is skipped like any other unregistered
    reference (never inferred from a room name or a database row).
    """
    from world.art.scene_definitions import ROOM_ART_KEY_SET

    return ROOM_ART_KEY_SET


def _registered_kind_keys(kind: str) -> frozenset[str]:
    """The authored keys one registry-backed kind accepts (empty when none).

    The three loaders are resolved through their module globals at call time,
    so a test patches one kind's lookup without disturbing the others (the
    long-standing preset seam) and a new kind adds one arm here.
    """
    if kind == "preset":
        return _registered_preset_keys()
    if kind == "scene":
        return _registered_scene_keys()
    if kind == "room":
        return _registered_room_art_keys()
    return frozenset()


def admit_image_header(payload: bytes) -> tuple[dict | None, str | None]:
    """Return ``(image_size, refusal_reason)`` with exactly one of them ``None``.

    Decoding reads the HEADER only (``Image.open`` + ``size``, never a pixel
    decode): a file declaring hostile dimensions is refused from its header
    under the same bounded limits the sd-webui client applies, so admission can
    never allocate a giant pixel buffer. This is the ONE bounded header decoder
    of the art domain: the operator catalog and ``world.art.scene_definitions``'
    bundled scene admission both call it, so the two roots cannot drift into
    two definitions of "an admissible image". (A full pixel decode belongs to
    the scene collection's data contract, which must also reject a truncated
    file that a header read cannot see.)
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


def _bounded_declared_default(value: object) -> str | None:
    """The manifest's declared default as a bounded single-file name, or ``None``.

    A declared default names a file INSIDE its own content directory, so the
    only value this snapshot ever retains as a source identity is a plain
    single-segment filename within the filesystem's own name bound. An absolute
    path, a sub-path, a traversal component, a control character, an empty name,
    or an over-long name is refused here and never echoed into any fault,
    refusal, or event value — such a manifest degrades whole through the usual
    inadmissible-default violation instead.
    """
    if (
        not isinstance(value, str)
        or not value
        or len(value) > _MAX_DECLARED_DEFAULT_LENGTH
    ):
        return None
    if value in (".", "..") or "/" in value or "\\" in value:
        return None
    if any(character < " " or character == "\x7f" for character in value):
        return None
    return value


def _declared_default_fault(
    kind: str,
    key: str,
    declared_default: str | None,
    admitted_names: set[str],
    refused_names: Mapping[str, str],
) -> SourceFault | None:
    """The pre-substitute fault of a manifest's declared default, or ``None``.

    A declared default that IS admitted carries no fault: it is the effective
    default, not a request that failed (even when an unrelated metadata
    violation degraded the manifest whole). One that was refused at admission
    is a ``source_rejected`` fact; one that no listing entry carries is an
    ``explicit_reference_missing`` fact. Either way the fault is attributed to
    the declared identity and precedes the deterministic substitute.
    """
    if declared_default is None or declared_default in admitted_names:
        return None
    reason = (
        SOURCE_REASON_REJECTED
        if declared_default in refused_names
        else SOURCE_REASON_REFERENCE_MISSING
    )
    return SourceFault(
        SOURCE_SCOPE_DEFAULT, f"{kind}/{key}/{declared_default}", reason
    )


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

    The violation's bounded token and the manifest's bounded declared default
    ride BESIDE the degraded fields (``invalid_reason``/``declared_default``),
    so the snapshot keeps an attributable source fact while the file behaviour
    is byte-for-byte unchanged.
    """
    try:
        raw_bytes = open_file_bytes(
            OFFICIAL_MANIFEST_FILENAME, dir_fd=content_fd, max_bytes=_MAX_FILE_BYTES
        )
    except FileNotFoundError:  # observability: ignore R2: an absent manifest is the documented silent fallback
        return _ContentManifest(None, None, None)
    except OSError:  # observability: ignore R2: an unreadable manifest degrades whole via the diagnostic below
        diagnostics.emit("manifest_unreadable", kind=kind, key=key)
        return _ContentManifest(None, None, None, None, "manifest_unreadable")
    except RejectedFile:  # observability: ignore R2: degradation is the bounded diagnostic below
        diagnostics.emit("manifest_unreadable", kind=kind, key=key)
        return _ContentManifest(None, None, None, None, "manifest_unreadable")
    try:
        raw = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):  # observability: ignore R2: malformed JSON degrades whole via the diagnostic below
        diagnostics.emit("manifest_unreadable", kind=kind, key=key)
        return _ContentManifest(None, None, None, None, "manifest_unreadable")
    if not isinstance(raw, dict):
        diagnostics.emit("manifest_not_a_valid_object", kind=kind, key=key)
        return _ContentManifest(None, None, None, None, "manifest_not_a_valid_object")
    # The declared default is extracted BEFORE the key contract is checked, so a
    # manifest that is rejected for an unrelated unknown key still keeps its
    # bounded requested-default fact instead of silently losing it.
    declared_default = _bounded_declared_default(raw.get("default"))
    if not set(raw) <= _MANIFEST_KEYS:
        diagnostics.emit("manifest_not_a_valid_object", kind=kind, key=key)
        return _ContentManifest(
            None, None, None, declared_default, "manifest_not_a_valid_object"
        )
    face_rect = None
    if "face_rect" in raw:
        try:
            face_rect = validate_face_rect(raw["face_rect"])
        except GalleryRecordError:  # observability: ignore R2: an invalid rectangle degrades whole via the diagnostic below
            diagnostics.emit("manifest_invalid_face_rect", kind=kind, key=key)
            return _ContentManifest(
                None, None, None, declared_default, "manifest_invalid_face_rect"
            )
    stage = None
    if "stage" in raw:
        try:
            stage = validate_stage(raw["stage"])
        except GalleryRecordError:  # observability: ignore R2: an invalid stage degrades whole via the diagnostic below
            diagnostics.emit("manifest_invalid_stage", kind=kind, key=key)
            return _ContentManifest(
                None, None, None, declared_default, "manifest_invalid_stage"
            )
    # A JSON ``null`` default is "no default declared" exactly as an absent key
    # is (the long-standing seed-metadata convention): the declared metadata
    # still applies and the deterministic first filename is the selection.
    if raw.get("default") is None:
        return _ContentManifest(None, face_rect, stage, None, None)
    if declared_default is None or declared_default not in admitted_names:
        diagnostics.emit("manifest_default_not_an_admitted_file", kind=kind, key=key)
        return _ContentManifest(
            None,
            None,
            None,
            declared_default,
            "manifest_default_not_an_admitted_file",
        )
    return _ContentManifest(declared_default, face_rect, stage, declared_default, None)


def _admitted_entries(
    kind: str,
    key: str,
    content_fd: int,
    diagnostics: _Diagnostics,
    counters: dict[str, int],
    refused: dict[str, str],
) -> list[tuple[str, bytes, dict]] | None:
    """Admit one content folder's images: ``(filename, payload, image_size)``.

    Listing order is sorted filename order (the deterministic order the default
    rule and the snapshot rely on). Every refusal is per-entry: one bounded
    diagnostic, the entry's bounded reason retained in ``refused`` keyed by its
    filename (the caller turns those into root-relative identities, so a
    refused identity keeps its reason even when the diagnostic budget is
    exhausted), and the walk continues — so the remaining valid images in this
    folder and every other folder still index.

    ``None`` (rather than an empty list) when the listing itself failed: nothing
    was enumerated, so no caller may infer that a declared filename is absent.
    """
    try:
        names = sorted(os.listdir(content_fd))
    except OSError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
        diagnostics.emit("content_directory_unreadable", kind=kind, key=key)
        return None
    admitted: list[tuple[str, bytes, dict]] = []
    for name in names:
        if name == OFFICIAL_MANIFEST_FILENAME:
            continue
        try:
            stat_result = os.lstat(name, dir_fd=content_fd)
        except OSError:  # observability: ignore R2: a vanished listing entry is a silent no-op
            continue
        reason: str | None = None
        if S_ISLNK(stat_result.st_mode):
            reason = "symlink_skipped"
        elif S_ISDIR(stat_result.st_mode):
            reason = "nested_directory_skipped"
        elif not S_ISREG(stat_result.st_mode):
            reason = "non_regular_entry_skipped"
        elif Path(name).suffix not in STORE_EXTENSIONS:
            reason = "unsupported_extension_skipped"
        if reason is not None:
            counters["refused"] += 1
            refused[name] = reason
            diagnostics.emit(reason, kind=kind, key=key, entry=name)
            continue
        try:
            payload = open_file_bytes(name, dir_fd=content_fd, max_bytes=_MAX_FILE_BYTES)
        except OSError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
            counters["refused"] += 1
            refused[name] = "source_unreadable"
            diagnostics.emit("source_unreadable", kind=kind, key=key, entry=name)
            continue
        except RejectedFile:  # observability: ignore R2: reported through the bounded diagnostic emitter below
            counters["refused"] += 1
            refused[name] = "source_rejected"
            diagnostics.emit("source_rejected", kind=kind, key=key, entry=name)
            continue
        image_size, refusal = admit_image_header(payload)
        if image_size is None:
            counters["refused"] += 1
            refused[name] = refusal or "image_undecodable"
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
    facts: _LoadFacts,
) -> None:
    """Index one ``<kind>/<key>/`` folder; never raises.

    The folder's bounded source facts are retained whether or not any image is
    admitted: a directory whose every candidate was refused (or whose manifest
    declares a default that no listing entry carries) still keeps its
    attributable declared-default fault and its per-entry refusal reasons, even
    though no ``OfficialContent`` is published for it. A directory the walk
    cannot open or enumerate at all retains the coarse source-availability
    fault instead, and nothing is classified from an enumeration that failed.
    """
    try:
        content_fd = open_dir_fd(key, dir_fd=kind_fd)
    except OSError:  # observability: ignore R2: reported through the bounded diagnostic emitter below
        counters["refused"] += 1
        diagnostics.emit("content_directory_unreadable", kind=kind, key=key)
        facts.source_faults[(kind, key)] = (
            SourceFault(
                SOURCE_SCOPE_SOURCE, f"{kind}/{key}", SOURCE_REASON_UNAVAILABLE
            ),
        )
        return
    refused: dict[str, str] = {}
    try:
        entries = _admitted_entries(
            kind, key, content_fd, diagnostics, counters, refused
        )
        admitted = entries or []
        admitted_names = {name for name, _, _ in admitted}
        # A failed enumeration made no reference knowable, so no manifest is
        # consulted: the directory keeps only its availability fact.
        manifest = (
            None
            if entries is None
            else _parse_manifest(
                content_fd, admitted_names, diagnostics, kind, key
            )
        )
    finally:
        os.close(content_fd)
    facts.refusals.update(
        {f"{kind}/{key}/{name}": reason for name, reason in refused.items()}
    )
    if manifest is None:
        facts.source_faults[(kind, key)] = (
            SourceFault(
                SOURCE_SCOPE_SOURCE, f"{kind}/{key}", SOURCE_REASON_UNAVAILABLE
            ),
        )
        return
    identities: list[str] = []
    metadata_faults: list[SourceFault] = []
    for name, payload, image_size in admitted:
        identity = f"{kind}/{key}/{name}"
        face_rect = default_face_rect(image_size)
        inapplicable = False
        if manifest.face_rect is not None:
            try:
                face_rect = validate_face_rect(manifest.face_rect, image_size=image_size)
            except GalleryRecordError:  # observability: ignore R2: the fitted per-image rectangle already applies
                diagnostics.emit(
                    "manifest_face_rect_inapplicable", kind=kind, key=key, entry=name
                )
                inapplicable = True
        if inapplicable or manifest.invalid_reason is not None:
            # This image's declared geometry was replaced by the fitted one, so
            # a metadata fault accompanies its safe geometry (and never the
            # image's valid bytes).
            metadata_faults.append(
                SourceFault(SOURCE_SCOPE_METADATA, identity, SOURCE_REASON_METADATA_INVALID)
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
    default_fault = _declared_default_fault(
        kind,
        key,
        manifest.declared_default,
        admitted_names,
        refused,
    )
    faults = ([default_fault] if default_fault is not None else []) + metadata_faults
    if faults:
        facts.source_faults[(kind, key)] = tuple(faults)
    if not admitted:
        return
    default_name = manifest.default or admitted[0][0]
    contents[(kind, key)] = OfficialContent(
        kind=kind,
        key=key,
        default_identity=f"{kind}/{key}/{default_name}",
        images=tuple(identities),
        requested_default=(
            f"{kind}/{key}/{manifest.declared_default}"
            if manifest.declared_default is not None
            else None
        ),
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
    facts: _LoadFacts,
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
            if not is_valid_subject_key(content_name):
                counters["refused"] += 1
                diagnostics.emit(
                    "invalid_content_key_skipped", kind=kind, key=content_name
                )
                continue
            if kind in _REGISTRY_BACKED_KINDS and content_name not in _registered_kind_keys(kind):
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
                facts,
            )
    finally:
        os.close(kind_fd)


def _root_health(reason: str, configured: bool) -> RootHealth:
    """The bounded root-health fact of one load's boundary reason.

    A deliberately absent DEFAULT optional root (an unbound or deliberately
    empty ``ART_OFFICIAL_ROOT``) is the normal no-art configuration and never a
    fault. An explicitly configured root that is MISSING, and every
    refused/unreadable/unusable root in any configuration, retain an
    availability failure — absence without an explicit binding is the only
    absence that carries no fault.
    """
    if reason in _ROOT_FAULT_REASONS:
        return RootHealth(ROOT_STATE_UNAVAILABLE, configured, True, reason)
    if reason == "official_root_absent":
        if configured:
            return RootHealth(ROOT_STATE_UNAVAILABLE, True, True, reason)
        return RootHealth(ROOT_STATE_ABSENT, False, False, reason)
    if reason == "official_root_unset":
        return RootHealth(ROOT_STATE_ABSENT, configured, False, reason)
    if reason == "official_root_empty":
        return RootHealth(ROOT_STATE_EMPTY, configured, False, reason)
    return RootHealth(ROOT_STATE_INDEXED, configured, False, reason)


def _record(
    contents: dict[tuple[str, str], OfficialContent],
    images: dict[str, OfficialImage],
    counters: dict[str, int],
    diagnostics: _Diagnostics,
    facts: _LoadFacts,
    reason: str,
) -> dict:
    """Publish the snapshot and emit the single boundary event.

    The retained facts are published on the snapshot BEFORE the event, and the
    boundary event carries the root state and fault flag beside the counts. A
    retained availability failure emits exactly ONE further bounded
    ``source_unavailable`` diagnostic — deliberately outside the budgeted
    :class:`_Diagnostics` counter, because a retained fact must never depend on
    the diagnostic emission budget.
    """
    global _CATALOG
    health = _root_health(reason, facts.configured)
    _CATALOG = OfficialCatalog(
        contents, images, health, facts.source_faults, facts.refusals
    )
    summary = {
        "skipped": not images,
        **counters,
        "diagnostics": diagnostics.emitted,
        "suppressed_diagnostics": diagnostics.suppressed,
        "root_state": health.state,
        "root_fault": health.fault,
    }
    log_info(
        OFFICIAL_CATALOG_EVENT,
        context={"phase": "loaded", "reason": reason, **summary},
    )
    if health.fault:
        log_warn(
            OFFICIAL_CATALOG_EVENT,
            context={
                "phase": "diagnostic",
                "reason": SOURCE_REASON_UNAVAILABLE,
                "root_state": health.state,
                "configured": health.configured,
            },
        )
    return summary


def _publish_bundled_scenes() -> None:
    """Publish the committed bundled scene collection beside this catalog.

    The bundled load owns its snapshot, counters and event id, and carries its
    own outermost guard, so a broken scene collection never disturbs the
    operator snapshot (or the reverse). The try/except here is the last-resort
    isolation of the two publishes: an unforeseen fault in the bundled pass is
    reported as one bounded diagnostic on the bundled event and the operator
    walk continues. Both the art definitions import and the load itself are
    inside the guard, so even an import-time fault in the bundled module (whose
    module-level imports include this one's shared bounded decoder) can never
    escape ``load_catalog``.
    """
    try:
        # The definitions module is imported inside the body because it imports
        # this module's shared bounded decoder at import time.
        from world.art.scene_definitions import (
            BUNDLED_SCENE_CATALOG_EVENT,
            load_bundled_scene_catalog,
        )

        load_bundled_scene_catalog()
    except Exception as error:  # pragma: no cover - last-resort isolation
        # The bundled collection's own boundary event id, spelled literally
        # because this guard must report even when that module cannot import.
        log_warn(
            "bundled_scene_catalog_loaded",
            context={"phase": "bundled_scenes_failed", "reason": "bundled_scenes_failed"},
            exc=error,
        )


def load_catalog() -> dict:
    """Index the official-artwork root once (startup step); never raises.

    Returns a non-empty summary dict (also emitted as the single
    ``official_art_catalog_loaded`` boundary event): the indexed
    content-directory, image, and refused-entry counts plus the diagnostic
    budget counters, and the retained root state/fault flag. An unset, absent,
    symlinked, unreadable, or empty root is a supported no-art configuration:
    the snapshot is empty, one bounded info event names the condition, and
    startup proceeds with the existing runtime-art and fallback behavior
    unchanged. The snapshot retains the load's bounded health and source facts
    on EVERY exit path, so an empty index never erases why a root was absent or
    broken: a deliberately absent DEFAULT optional root is normal, an
    explicitly configured missing root and any refused/unreadable/unusable root
    retain an availability failure (one bounded ``source_unavailable``
    diagnostic beside the fact). The outermost catch exists only for unforeseen
    faults — a broken artwork tree is never a startup failure, and it too
    publishes a fault-bearing snapshot rather than erasing the health fact.
    Nothing is acquired here: the walk is the only I/O.

    The committed bundled scene collection is published FIRST and on every exit
    path, under its own guard and its own event id: a missing operator mount is
    exactly the configuration the bundled art has to serve, and neither publish
    may zero the other. This catalog's own counts, snapshot and single boundary
    event are unaffected by the bundled pass.
    """
    global _CATALOG
    _publish_bundled_scenes()
    counters: dict[str, int] = {"contents": 0, "images": 0, "refused": 0}
    diagnostics = _Diagnostics()
    # The explicit-configuration provenance the settings captured at import: an
    # operator who BOUND the root is never silently treated as if the default
    # optional root had merely been absent.
    facts = _LoadFacts(
        configured=bool(getattr(settings, "ART_OFFICIAL_ROOT_EXPLICIT", False))
    )
    try:
        configured_root = str(getattr(settings, "ART_OFFICIAL_ROOT", "") or "")
        if not configured_root.strip():
            return _record({}, {}, counters, diagnostics, facts, "official_root_unset")
        root = Path(configured_root)
        # ``lstat`` (never the swallowing pathlib predicates) so an unreadable
        # parent is a retained I/O failure rather than a silent "absent".
        try:
            root_stat = os.lstat(root)
        except FileNotFoundError:  # observability: ignore R2: absence is the supported no-art configuration recorded below
            return _record({}, {}, counters, diagnostics, facts, "official_root_absent")
        except OSError:  # observability: ignore R2: the unreadable-root reason below is the one bounded event
            return _record({}, {}, counters, diagnostics, facts, "official_root_unreadable")
        if S_ISLNK(root_stat.st_mode):
            return _record({}, {}, counters, diagnostics, facts, "official_root_symlink")
        if not S_ISDIR(root_stat.st_mode):
            # An existing non-directory entry can never be walked: it is a
            # configured root the catalog cannot read, not a normal absence.
            return _record(
                {}, {}, counters, diagnostics, facts, "official_root_not_a_directory"
            )
        try:
            root_fd = open_dir_fd(str(root))
        except OSError:  # observability: ignore R2: the unreadable-root reason below is the one bounded event
            return _record({}, {}, counters, diagnostics, facts, "official_root_unreadable")
        contents: dict[tuple[str, str], OfficialContent] = {}
        images: dict[str, OfficialImage] = {}
        try:
            try:
                top_level = sorted(os.listdir(root_fd))
            except OSError:  # observability: ignore R2: the unreadable-root reason below is the one bounded event
                return _record(
                    {}, {}, counters, diagnostics, facts, "official_root_unreadable"
                )
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
                if entry_name not in OFFICIAL_LAYOUT_KINDS:
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
                    facts,
                )
        finally:
            os.close(root_fd)
        return _record(
            contents,
            images,
            counters,
            diagnostics,
            facts,
            "official_root_indexed" if images else "official_root_empty",
        )
    except Exception as error:
        # A broken artwork tree is never a startup failure, and the unforeseen
        # fault must not erase the health or source facts collected so far: the
        # snapshot is republished fault-bearing — with every fact already
        # retained — instead of reset to an empty one. Only the partially walked
        # admitted images are dropped, because a partial index is not a snapshot
        # this catalog can serve from.
        health = _root_health("catalog_load_failed", facts.configured)
        log_warn(
            OFFICIAL_CATALOG_EVENT,
            context={
                "phase": "loaded",
                "reason": "catalog_load_failed",
                **counters,
                "root_state": health.state,
                "root_fault": health.fault,
            },
            exc=error,
        )
        _CATALOG = OfficialCatalog(
            {}, {}, health, facts.source_faults, facts.refusals
        )
        return {
            "skipped": True,
            **counters,
            "root_state": health.state,
            "root_fault": health.fault,
        }
