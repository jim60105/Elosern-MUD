"""Authored scene-art definitions, the bundled scene collection, and its media identity.

``unified-scene-catalog`` (approved design §6.2/§6.3): every registered scene
archetype plus the explicit dream scene has ONE required bundled official WebP
under the fixed repository directory ``web/static/art/scenes/``, and every one
of them declares a terminal scene key. The definitions are immutable authored
records in the art domain, keyed by ``world.lore.scene_archetypes``' registry
plus the dream type — the lore archetype records themselves stay untouched
(the ``art-assets`` amendment: ``SceneArchetype`` carries no image field).

Three things live here, in this order:

* **The authored declarations** — :data:`SCENE_ART_DEFINITIONS` and the closed
  terminal vocabulary. Their completeness against the lore registry and the
  real files is what :func:`scene_art_collection_problems` checks.
* **The authored room-art keys** — :data:`ROOM_ART_KEYS`, the closed vocabulary
  of authored room content an operator ``room/<room-art-key>/`` directory may
  name. Keys identify authored room content (never a database row, never a
  translated name) and are projected from the authored place registry, so a
  directory keyed to an unregistered room cannot exist. The map owner that
  declares ``room_art_key`` metadata consumes this vocabulary; a room family
  outside today's authored places extends it in its own change, here.
* **The bundled collection snapshot** — :func:`load_bundled_scene_catalog`
  admits the fixed directory once per startup, under the same bounded decoder,
  no-follow opening discipline and content fingerprint the operator catalog
  uses, and publishes an immutable snapshot that the media route authorizes
  against. Identities are ``bundled-scene/<key>/<sha256>.webp`` and URLs are
  ``/art/bundled-scene/<key>/<sha256>.webp``: a closed allowlist of the
  declared keys under a root that NEVER overlaps the operator roots, so an
  operator file can neither replace a bundled identity nor a terminal image.

**Contract versus runtime.** :func:`scene_art_collection_problems` is the
contract: it names the affected scene key for a missing declaration, an
unregistered definition key, an invalid or unregistered terminal reference, a
key outside the shared stable-key contract, and a missing, empty, oversized,
undecodable or non-16:9 required image. It decodes the shipped bytes FULLY (a
truncated file must fail the contract), while startup admission reads the
image HEADER only — the operator catalog's documented discipline — so a
deployment that loses or corrupts one of these validated files still starts,
logs a bounded failure and degrades visibly instead of blocking gameplay.

**Observability.** One ``bundled_scene_catalog_loaded`` info event per load
carries the declaration, published-image, refused-entry and diagnostic counts
plus the absent/unreadable condition; every refusal emits a bounded diagnostic
within a per-load budget. No event context carries an absolute root or an
image payload — only scene keys, reasons and counts.

**Import direction.** This module imports ``world.art.official``'s shared
bounded header decoder at import time; ``world.art.official`` therefore
references this module only INSIDE function bodies (the same lazy discipline
it already uses for the lore registries). Keep that direction one-way.
"""

from __future__ import annotations

import hashlib
import io
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from stat import S_ISDIR, S_ISLNK
from types import MappingProxyType
from urllib.parse import quote

from django.conf import settings
from PIL import Image

from world.art.no_follow import RejectedFile, open_dir_fd, open_file_bytes
from world.art.official import admit_image_header
from world.art.subjects import is_valid_subject_key
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.lore.settlements.places import PLACE_REGISTRY
from world.observability import log_info, log_warn

# The one boundary/diagnostic event id of the bundled collection: the load
# boundary and the bounded per-entry refusals share it and carry a "phase"
# discriminator. It is deliberately NOT the operator catalog's event id —
# that catalog's contract is exactly one boundary event per load.
BUNDLED_SCENE_CATALOG_EVENT = "bundled_scene_catalog_loaded"

# The one committed extension of a bundled scene illustration, and the fixed
# repository directory that holds the collection (the first staticfiles
# directory, i.e. ``web/static/``). Neither is a setting: the bundled root is
# in-repo, never operator-mountable, and never overridden by the environment.
BUNDLED_SCENE_EXTENSION = ".webp"
BUNDLED_SCENE_DIRECTORY = ("art", "scenes")

# The declared bound for one committed scene illustration (the artwork packs'
# repository media bound). The admission limits that bound the HEADER decode
# are the shared ART_SD_MAX_IMAGE_* settings, read through the shared decoder
# rather than re-declared here.
BUNDLED_SCENE_MAX_FILE_BYTES = 524_288

# The exact identity/URL shapes of the closed bundled namespace.
BUNDLED_SCENE_IDENTITY_PREFIX = "bundled-scene/"
BUNDLED_SCENE_MEDIA_PREFIX = "/art/bundled-scene/"

# The explicit dream definition: the dream scene is not an explorable
# archetype, so it is declared here rather than in the lore registry.
DREAM_SCENE_KEY = "dream_throne"

# The dream stage's OPTIONAL operator-preferred source: the exact official
# identity the dream chain resolves first, in the operator catalog's
# ``npc/<key>/<file>`` layout. It is an exact filename, never a directory
# default (the operator resolves that path or nothing), and it lives here
# because it is art-domain authored content: the narrative read model reads the
# dream's descriptor from :func:`world.art.presenter.describe_dream_scene` and
# never names an artwork identity itself.
DREAM_PREFERRED_OFFICIAL_KIND = "npc"
DREAM_PREFERRED_OFFICIAL_KEY = "dream_goddess"
DREAM_PREFERRED_OFFICIAL_IDENTITY = (
    f"{DREAM_PREFERRED_OFFICIAL_KIND}/{DREAM_PREFERRED_OFFICIAL_KEY}/dream-throne.webp"
)

# The closed terminal vocabulary: a scene's declared terminal image is always
# one of the two terminal members, and every terminal key is itself a required
# bundled definition.
TERMINAL_SCENE_KEYS = ("city_street", "forest_path")

# The desktop stage's full-bleed landscape aspect (approved design §6.2): a
# required image that is not exactly this would silently lose composition the
# packs' visual review signed off on when the stage cover-crops it.
_SCENE_ASPECT_WIDTH = 16
_SCENE_ASPECT_HEIGHT = 9

# Per-load budget for bounded leaf diagnostics. Beyond it the walk still
# continues; only the event emission is capped and the suppressed count is
# reported in the boundary event.
_MAX_DIAGNOSTICS = 32

# The human-readable form of every image-level contract refusal, so a failure
# names the affected scene key AND what is wrong with its required image.
_IMAGE_REFUSAL_MESSAGES = {
    "image_missing": "the required bundled image is missing",
    "image_rejected": "the required bundled image is not a plain bounded regular file",
    "image_unreadable": "the required bundled image is unreadable",
    "image_empty": "the required bundled image is empty",
    "image_undecodable": "the required bundled image does not decode",
    "image_too_large": "the required bundled image exceeds the image admission limits",
    "image_not_full_bleed_landscape": "the required bundled image is not a full-bleed 16:9 landscape",
}


@dataclass(frozen=True)
class SceneArtDefinition:
    """One authored scene-art declaration: its key and its declared terminal.

    ``key`` is the scene-art key (a registered archetype key or the explicit
    dream key) and is also the bundled image's filename stem and the media
    identity's scene segment. ``terminal_key`` names the required bundled
    definition the scene falls back to as its terminal image; it is always a
    member of :data:`TERMINAL_SCENE_KEYS` and of this registry.
    """

    key: str
    terminal_key: str


# The authored declarations, in the lore registry's order plus the explicit
# dream type. The terminal map is the approved design's §6.2 table verbatim.
_SCENE_ART_DEFINITIONS = (
    SceneArtDefinition("forest_path", "forest_path"),
    SceneArtDefinition("tavern_interior", "city_street"),
    SceneArtDefinition("dungeon_interior", "forest_path"),
    SceneArtDefinition("city_street", "city_street"),
    SceneArtDefinition("wilderness_path", "forest_path"),
    SceneArtDefinition("mountain_path", "forest_path"),
    SceneArtDefinition("ruin_interior", "forest_path"),
    SceneArtDefinition("coastal_path", "forest_path"),
    SceneArtDefinition("cave_interior", "forest_path"),
    SceneArtDefinition("shrine_interior", "city_street"),
    SceneArtDefinition(DREAM_SCENE_KEY, "city_street"),
)

# Frozen: consumers may read declarations but never extend or replace them. A
# new normal archetype adds its declaration and its real artwork together (the
# collection contract below fails otherwise).
SCENE_ART_DEFINITIONS: MappingProxyType[str, SceneArtDefinition] = MappingProxyType(
    {definition.key: definition for definition in _SCENE_ART_DEFINITIONS}
)

# The declared keys in authored order (the deterministic enumeration the
# admission pass and the contract walk).
SCENE_ART_KEYS: tuple[str, ...] = tuple(
    definition.key for definition in _SCENE_ART_DEFINITIONS
)

# The authored room-art-key vocabulary. A place key IS the permanent
# interior's room tag (``world.lore.settlements.places``), so projecting the
# authored place registry keeps one source of truth: a ``room/<key>/``
# directory that no authored place declares cannot be characterized, and no
# key is ever a runtime row id or a translated display name. A future room
# family (authored grid rooms, declared instances) extends this projection in
# the change that declares its metadata.
ROOM_ART_KEYS: tuple[str, ...] = tuple(sorted(PLACE_REGISTRY))
ROOM_ART_KEY_SET: frozenset[str] = frozenset(ROOM_ART_KEYS)


def is_registered_scene_key(key: object) -> bool:
    """True when ``key`` names one of the authored scene-art declarations."""
    return isinstance(key, str) and key in SCENE_ART_DEFINITIONS


def is_registered_room_art_key(key: object) -> bool:
    """True when ``key`` names one of the authored room-art keys."""
    return isinstance(key, str) and key in ROOM_ART_KEY_SET


def scene_definition_for(key: str) -> SceneArtDefinition | None:
    """The authored declaration for a scene-art key, or ``None``."""
    return SCENE_ART_DEFINITIONS.get(key)


def bundled_scene_root() -> Path:
    """The fixed in-repo directory holding the committed scene collection.

    Pinned to the first staticfiles directory (``web/static``), i.e. the
    design's ``web/static/art/scenes/``; settings-derived, never
    env-configurable, and read per call so tests can redirect it. The root is
    deliberately NOT ``ART_OFFICIAL_ROOT`` or ``ART_STORE_ROOT``: the bundled
    namespace and the operator namespaces never share a directory.
    """
    return Path(settings.STATICFILES_DIRS[0]).joinpath(*BUNDLED_SCENE_DIRECTORY)


def bundled_asset_filename(key: str) -> str:
    """The committed filename of one scene-art key's bundled illustration."""
    return f"{key}{BUNDLED_SCENE_EXTENSION}"


def bundled_identity(key: str, fingerprint: str) -> str:
    """The media identity of one admitted bundled image."""
    return f"{BUNDLED_SCENE_IDENTITY_PREFIX}{key}/{fingerprint}{BUNDLED_SCENE_EXTENSION}"


# --------------------------------------------------------------------------- contract


def _decode_required_image(key: str, payload: bytes) -> tuple[dict | None, str | None]:
    """Fully decode one required image under the bounded limits, or a reason.

    A full ``load()`` (not a header read) is deliberate: the contract's job is
    to reject a truncated or corrupted committed payload, which a header read
    would admit. The returned ``image_size`` is the decoded pixel size.
    """
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.load()
            width, height = image.size
    except Exception:  # noqa: BLE001
        # observability: ignore R2: the returned reason is this helper's contract signal
        return None, "image_undecodable"
    if width <= 0 or height <= 0:
        return None, "image_undecodable"
    max_dimension = int(settings.ART_SD_MAX_IMAGE_DIMENSIONS)
    max_pixels = int(settings.ART_SD_MAX_IMAGE_PIXELS)
    if width > max_dimension or height > max_dimension or width * height > max_pixels:
        return None, "image_too_large"
    if width * _SCENE_ASPECT_HEIGHT != height * _SCENE_ASPECT_WIDTH:
        return None, "image_not_full_bleed_landscape"
    return {"width": width, "height": height}, None


def _read_required_image(
    key: str, filename: str, directory_fd: int
) -> tuple[bytes | None, str | None]:
    """Read one required image bounded no-follow, or a reason."""
    try:
        payload = open_file_bytes(
            filename, dir_fd=directory_fd, max_bytes=BUNDLED_SCENE_MAX_FILE_BYTES
        )
    except FileNotFoundError:  # observability: ignore R2: the returned reason is the refusal signal
        return None, "image_missing"
    except RejectedFile:  # observability: ignore R2: the returned reason is the refusal signal
        return None, "image_rejected"
    except OSError:  # observability: ignore R2: the reason below is the refusal signal
        return None, "image_unreadable"
    if not payload:
        return None, "image_empty"
    return payload, None


def scene_art_collection_problems(
    *,
    definitions: Mapping[str, SceneArtDefinition] = SCENE_ART_DEFINITIONS,
    archetype_keys: Mapping[str, object] = SCENE_ARCHETYPE_REGISTRY,
    root: Path | str | None = None,
) -> tuple[str, ...]:
    """Every defect of the authored scene-art collection, each naming its key.

    Returns a deterministically ordered tuple of problem strings; an empty
    tuple means the collection is complete and valid. Every problem caused by
    a declaration or an image begins with the affected scene key, so a failure
    names its source (the delta spec's ``Broken coverage names its source``).

    ``definitions``, ``archetype_keys`` and ``root`` are injection points:
    production callers use the authored defaults, while the contract test
    plants a missing declaration, an unregistered definition key, an invalid
    or unregistered terminal reference and a missing/corrupt/oversized image
    and asserts each one is reported by key.
    """
    problems: list[str] = list(
        scene_art_registry_problems(
            definitions=definitions, archetype_keys=archetype_keys
        )
    )

    directory = Path(root) if root is not None else bundled_scene_root()
    if directory.is_symlink():
        problems.append(f"{directory.name}: the scene-art directory is a symlink")
        return tuple(problems)
    try:
        directory_fd = open_dir_fd(str(directory))
    except OSError:  # observability: ignore R2: the problem below is the contract failure
        problems.append(f"{directory.name}: the scene-art directory is missing or unreadable")
        return tuple(problems)
    try:
        for key in sorted(definitions):
            payload, refusal = _read_required_image(
                key, bundled_asset_filename(key), directory_fd
            )
            if payload is None:
                problems.append(
                    f"{key}: {_IMAGE_REFUSAL_MESSAGES.get(refusal or '', 'the required bundled image is unreadable')}"
                )
                continue
            image_size, refusal = _decode_required_image(key, payload)
            if image_size is None:
                problems.append(
                    f"{key}: {_IMAGE_REFUSAL_MESSAGES.get(refusal or '', 'the required bundled image does not decode')}"
                )
    finally:
        os.close(directory_fd)
    return tuple(problems)


def scene_art_registry_problems(
    *,
    definitions: Mapping[str, SceneArtDefinition] = SCENE_ART_DEFINITIONS,
    archetype_keys: Mapping[str, object] = SCENE_ARCHETYPE_REGISTRY,
) -> tuple[str, ...]:
    """The declaration-level defects of the collection, each naming its key.

    Pure structure only (no filesystem access), so the runtime admission can
    report a registry hole or a bad terminal reference without reading a
    single image: a registered archetype with no declaration, a declaration
    key that is neither a registered archetype nor the explicit dream key, a
    scene key outside the shared stable-key contract, a terminal outside the
    closed terminal vocabulary, and a terminal naming no declared definition.
    """
    problems: list[str] = []
    expected_keys = tuple(archetype_keys) + (DREAM_SCENE_KEY,)
    for key in expected_keys:
        if key not in definitions:
            problems.append(f"{key}: no scene-art definition")
    terminals = set(TERMINAL_SCENE_KEYS)
    for key, definition in definitions.items():
        if key not in expected_keys:
            problems.append(f"{key}: unregistered scene-art key")
        elif not is_valid_subject_key(key):
            problems.append(f"{key}: the scene-art key breaks the stable-key contract")
        if definition.terminal_key not in terminals:
            problems.append(
                f"{key}: terminal {definition.terminal_key!r} is not a declared terminal scene key"
            )
        elif definition.terminal_key not in definitions:
            problems.append(
                f"{key}: terminal {definition.terminal_key!r} has no required image"
            )
    return tuple(problems)


# --------------------------------------------------------------------------- snapshot


@dataclass(frozen=True)
class BundledSceneImage:
    """One admitted bundled scene illustration and its load-time facts."""

    key: str
    identity: str
    filename: str
    fingerprint: str
    image_size: dict


class BundledSceneCatalog:
    """The immutable bundled-scene snapshot a restart produced.

    Every lookup is an in-memory read: the media route admits a request only
    when :meth:`admits` finds the exact scene key at the exact current
    fingerprint, so an unregistered key, an outdated fingerprint or a request
    that never named a declaration is refused without touching the filesystem
    (and without a scan).
    """

    def __init__(self, images: Mapping[str, BundledSceneImage]) -> None:
        self._images = dict(images)

    def __len__(self) -> int:
        """The number of admitted bundled images (an empty snapshot is falsy)."""
        return len(self._images)

    def identities(self) -> tuple[str, ...]:
        """Every admitted media identity, deterministically ordered."""
        return tuple(sorted(image.identity for image in self._images.values()))

    def entry(self, key: str) -> BundledSceneImage | None:
        """The admitted image for a scene key, or ``None``."""
        return self._images.get(key)

    def fingerprint_for(self, key: str) -> str | None:
        """The current content fingerprint for a scene key, or ``None``."""
        image = self._images.get(key)
        return image.fingerprint if image is not None else None

    def admits(self, key: str, fingerprint: str) -> bool:
        """True when the snapshot admits ``key`` at exactly ``fingerprint``."""
        image = self._images.get(key)
        return image is not None and image.fingerprint == fingerprint

    def url_for(self, key: str) -> str | None:
        """The same-origin bundled media URL for an admitted key.

        ``None`` for a key this snapshot does not admit, so a URL can never be
        built for unadmitted artwork. The key is percent-encoded (the shared
        stable-key contract forbids ``/`` but permits a space, ``#`` or ``?``),
        and the server decodes the path before routing, so the served identity
        is the admitted one exactly.
        """
        image = self._images.get(key)
        if image is None:
            return None
        return f"{BUNDLED_SCENE_MEDIA_PREFIX}{quote(key, safe='')}/{image.fingerprint}{BUNDLED_SCENE_EXTENSION}"


# The current snapshot: empty until the startup step loads it, empty again
# after a reset. A module global (not a settings read) because the snapshot IS
# the restart-scoped state this module owns.
_BUNDLED = BundledSceneCatalog({})


def current_bundled_scenes() -> BundledSceneCatalog:
    """The snapshot the last bundled load produced (empty before the first)."""
    return _BUNDLED


def reset_bundled_scenes() -> None:
    """Drop the snapshot; the next load rebuilds it from the repository."""
    global _BUNDLED
    _BUNDLED = BundledSceneCatalog({})


class _Diagnostics:
    """Bounded diagnostic counter emitting capped facade events."""

    def __init__(self) -> None:
        self.emitted = 0
        self.suppressed = 0

    def emit(self, reason: str, **context: object) -> None:
        if self.emitted < _MAX_DIAGNOSTICS:
            self.emitted += 1
            log_warn(
                BUNDLED_SCENE_CATALOG_EVENT,
                context={"phase": "diagnostic", "reason": reason, **context},
            )
        else:
            self.suppressed += 1


def _publish(images: dict[str, BundledSceneImage], counters: dict[str, int], diagnostics: _Diagnostics, reason: str) -> dict:
    """Publish the snapshot and emit the single boundary event."""
    global _BUNDLED
    _BUNDLED = BundledSceneCatalog(images)
    summary = {
        "skipped": not images,
        "reason": reason,
        **counters,
        "diagnostics": diagnostics.emitted,
        "suppressed_diagnostics": diagnostics.suppressed,
    }
    log_info(
        BUNDLED_SCENE_CATALOG_EVENT,
        context={"phase": "loaded", **summary},
    )
    return summary


def _admit_required_images(
    directory_fd: int, counters: dict[str, int], diagnostics: _Diagnostics
) -> dict[str, BundledSceneImage]:
    """Admit every declaration's required image; per-entry refusals only."""
    images: dict[str, BundledSceneImage] = {}
    for key in SCENE_ART_KEYS:
        filename = bundled_asset_filename(key)
        payload, refusal = _read_required_image(key, filename, directory_fd)
        if payload is None:
            counters["refused"] += 1
            diagnostics.emit(refusal or "image_unreadable", key=key)
            continue
        image_size, refusal = admit_image_header(payload)
        if image_size is None:
            counters["refused"] += 1
            diagnostics.emit(refusal or "image_undecodable", key=key)
            continue
        fingerprint = hashlib.sha256(payload).hexdigest()
        images[key] = BundledSceneImage(
            key=key,
            identity=bundled_identity(key, fingerprint),
            filename=filename,
            fingerprint=fingerprint,
            image_size=dict(image_size),
        )
    counters["images"] = len(images)
    return images


def _registry_problems(
    counters: dict[str, int], diagnostics: _Diagnostics
) -> None:
    """Report the registry-structure defects the admission pass cannot see.

    The image-level defects are reported by the admission pass itself; these
    are the declaration-level ones (a registered archetype without a
    declaration, an unregistered declaration key, an invalid or unregistered
    terminal reference), each as one bounded diagnostic naming its key.
    """
    for problem in scene_art_registry_problems():
        key, _, detail = problem.partition(":")
        counters["refused"] += 1
        diagnostics.emit("registry_invalid", key=key, detail=detail.strip())


def load_bundled_scene_catalog() -> dict:
    """Admit the committed bundled scene collection once (startup step).

    Returns a non-empty summary dict (also emitted as the single
    ``bundled_scene_catalog_loaded`` boundary event): declaration, admitted
    image, refused-entry and diagnostic counts plus the reason. A missing,
    symlinked or unreadable directory is a supported no-bundled-art
    configuration: the snapshot stays empty, one bounded info event names the
    condition, and startup proceeds. Every refusal is per entry, so the
    remaining declarations still admit; nothing is acquired, written, copied
    or moved here — the walk is the only I/O. The outermost catch exists only
    for unforeseen faults: a broken collection is never a startup failure.
    """
    counters: dict[str, int] = {"definitions": len(SCENE_ART_KEYS), "images": 0, "refused": 0}
    diagnostics = _Diagnostics()
    try:
        directory = bundled_scene_root()
        if directory.is_symlink():
            return _publish({}, counters, diagnostics, "bundled_root_symlink")
        if not directory.is_dir():
            return _publish({}, counters, diagnostics, "bundled_root_absent")
        try:
            directory_fd = open_dir_fd(str(directory))
        except OSError:  # observability: ignore R2: the unreadable-root reason below is the one bounded event
            return _publish({}, counters, diagnostics, "bundled_root_unreadable")
        try:
            images = _admit_required_images(directory_fd, counters, diagnostics)
        finally:
            os.close(directory_fd)
        _registry_problems(counters, diagnostics)
        return _publish(
            images,
            counters,
            diagnostics,
            "bundled_root_indexed" if images else "bundled_root_empty",
        )
    except Exception as error:
        log_warn(
            BUNDLED_SCENE_CATALOG_EVENT,
            context={"phase": "loaded", "reason": "bundled_load_failed", **counters},
            exc=error,
        )
        reset_bundled_scenes()
        return {"skipped": True, **counters}
