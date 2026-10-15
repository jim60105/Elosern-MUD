"""The canonical artwork descriptor vocabulary: one closed fact set, no I/O.

Change ``unified-gallery-image-contract`` (design §"Canonical interface owned
by this change"). This module owns the ONE frozen vocabulary every artwork
descriptor shares — the container and identity bounds, the closed origin /
generation-state / fault-reason / terminal-kind sets, the per-origin media URL
ceilings, the stable source-layer ranks with their canonical source-identity
builders, and the single revision digest.

Builders return fresh plain dictionaries (JSON-safe, never shared mutables).
The wire serializer/validator is
``web.webclient.presentation.artwork``; the browser mirror is
``web/static/webclient/js/elosern/protocol/artwork.js``. Neither side invents
a bound: both read the constants below.

Read-only by construction: nothing here touches Evennia state, a queue, a
record, a file, or the network, and nothing here writes. Resolution stays
elsewhere; this module only names what resolution produced.
"""

from __future__ import annotations

import hashlib
import json

# --- Container and identity bounds ---------------------------------------

#: Longest stable subject identity a descriptor may carry.
MAX_SUBJECT_ID = 128
#: Longest canonical source identity (``<layer>.<owner>:<key>``) an attempt may carry.
MAX_SOURCE_ID = 256
#: Longest canonical resource identity an attempt or terminal may carry.
MAX_RESOURCE_ID = 256
#: The exact length of a version / revision / retention-token digest.
FINGERPRINT_LENGTH = 64
#: Most attempts one descriptor may carry, faults included.
MAX_ATTEMPTS = 16
#: Most retention authorizations one descriptor may carry.
MAX_RETENTION_SOURCES = 16
#: Longest aspect-ratio token (``<w>:<h>``) a geometry may carry.
MAX_ASPECT_RATIO = 16

# The decoded-size ceiling of the shared image resource contract, mirrored from
# the shipped ``ART_SD_MAX_IMAGE_DIMENSIONS`` / ``ART_SD_MAX_IMAGE_PIXELS``
# defaults. It is a WIRE ceiling: a decoded size past it is not something any
# active panel may present, so the canonical validators reject it rather than
# let one surface accept a dimension another cannot.
MAX_IMAGE_DIMENSION = 4096
MAX_IMAGE_PIXELS = 16_777_216

# --- Origins --------------------------------------------------------------

ORIGIN_RUNTIME = "runtime"
ORIGIN_OFFICIAL = "official"
ORIGIN_BUNDLED_OFFICIAL = "bundled_official"
ORIGIN_SILHOUETTE = "silhouette"
ORIGINS = (
    ORIGIN_RUNTIME,
    ORIGIN_OFFICIAL,
    ORIGIN_BUNDLED_OFFICIAL,
    ORIGIN_SILHOUETTE,
)

# The same-origin media URL ceiling each origin's own route can reach. A
# generated gallery resource names one stored card inside its subject's
# directory; an official or bundled resource embeds an operator-chosen
# filename, so it carries the shared portrait media ceiling instead.
GENERAL_MEDIA_URL_LIMIT = 256
GALLERY_MEDIA_URL_LIMIT = 129
MEDIA_URL_LIMITS = {
    ORIGIN_RUNTIME: GALLERY_MEDIA_URL_LIMIT,
    ORIGIN_OFFICIAL: GENERAL_MEDIA_URL_LIMIT,
    ORIGIN_BUNDLED_OFFICIAL: GENERAL_MEDIA_URL_LIMIT,
    ORIGIN_SILHOUETTE: GALLERY_MEDIA_URL_LIMIT,
}

# The one closed query form a republishable generated path may carry: a cache
# version, never a second selector.
VERSION_QUERY = "v"

# --- Recorded generation truth -------------------------------------------

GENERATION_MISSING = "missing"
GENERATION_PENDING = "pending"
GENERATION_DONE = "done"
GENERATION_FAILED = "failed"
GENERATION_STATES = (
    GENERATION_MISSING,
    GENERATION_PENDING,
    GENERATION_DONE,
    GENERATION_FAILED,
)

# The one normalization from a recorded asset status onto the canonical
# vocabulary. A CLAIMED (``in_progress``) generation is the same player-visible
# fact as a queued one, so it is reported as pending — exactly as the art
# panel's own wire normalizes it — while termination stays truthful.
RECORDED_STATE_NORMALIZATION = {
    "missing": GENERATION_MISSING,
    "pending": GENERATION_PENDING,
    "in_progress": GENERATION_PENDING,
    "done": GENERATION_DONE,
    "failed": GENERATION_FAILED,
}


def normalize_generation_state(status: object) -> str | None:
    """The canonical generation state for one recorded asset status, or ``None``.

    ``None`` is the honest answer for an absent status: a subject with no
    recorded generation carries no claim at all rather than a synthesized
    ``missing``.
    """
    if status is None:
        return None
    return RECORDED_STATE_NORMALIZATION.get(str(status))

# --- Closed fault reasons -------------------------------------------------

REASON_GENERATION_FAILED = "generation_failed"
REASON_GENERATED_OUTPUT_MISSING = "generated_output_missing"
REASON_SOURCE_UNAVAILABLE = "source_unavailable"
REASON_SOURCE_REJECTED = "source_rejected"
REASON_EXPLICIT_REFERENCE_MISSING = "explicit_reference_missing"
REASON_METADATA_INVALID = "metadata_invalid"
REASON_REQUIRED_RESOURCE_MISSING = "required_resource_missing"
REASON_CONFIGURATION_INVALID = "configuration_invalid"
REASON_PANEL_UNAVAILABLE = "panel_unavailable"
REASON_IMAGE_LOAD_FAILED = "image_load_failed"
REASON_IMAGE_DECODE_FAILED = "image_decode_failed"
FAULT_REASONS = (
    REASON_GENERATION_FAILED,
    REASON_GENERATED_OUTPUT_MISSING,
    REASON_SOURCE_UNAVAILABLE,
    REASON_SOURCE_REJECTED,
    REASON_EXPLICIT_REFERENCE_MISSING,
    REASON_METADATA_INVALID,
    REASON_REQUIRED_RESOURCE_MISSING,
    REASON_CONFIGURATION_INVALID,
    REASON_PANEL_UNAVAILABLE,
    REASON_IMAGE_LOAD_FAILED,
    REASON_IMAGE_DECODE_FAILED,
)

# --- Terminal kinds -------------------------------------------------------

TERMINAL_ALPHA_MASK = "alpha_mask"
TERMINAL_SCENE_IMAGE = "scene_image"
TERMINAL_KINDS = (TERMINAL_ALPHA_MASK, TERMINAL_SCENE_IMAGE)

# --- Stable source layers -------------------------------------------------

#: The classic-artwork request ceiling: one exact original is the whole layer.
MAX_SOURCE_LAYERS_PER_SUBJECT = 2
# The exact-gallery ranks. The requested original is the subject's own image;
# the alpha silhouette is a terminal fallback, never a competing original.
GALLERY_RANK_ORIGINAL = 10
GALLERY_RANK_ALPHA = 100
# The exact-portrait-layer ranks (design §"Stable ranks and authorized
# retention"): the selected equipment-bound card, the player's explicit
# personal official choice, the record's default card, the classic generated
# asset and the optional official default, in that precedence — before the
# same authoritative alpha terminal the gallery preview uses. Positions are
# independent of attempt-array order, and a fault keeps the rank of the source
# it belongs to.
PORTRAIT_RANK_BOUND = 10
PORTRAIT_RANK_PERSONAL = 20
PORTRAIT_RANK_DEFAULT = 30
PORTRAIT_RANK_CLASSIC = 40
PORTRAIT_RANK_OFFICIAL = 50
PORTRAIT_RANK_ALPHA = GALLERY_RANK_ALPHA
# The exact scene-layer ranks (design §"Stable ranks and authorized
# retention", change unified-scene-rendering): the authored room-art override,
# the scene's own generated archetype artwork, the optional operator scene
# default, the required bundled type illustration and the distinct declared
# town/forest terminal image, in that precedence. Like the portrait ranks these
# are positions, never attempt-array indexes, and a fault keeps the rank of the
# source it belongs to.
SCENE_RANK_ROOM = 10
SCENE_RANK_GENERATED = 20
SCENE_RANK_OPERATOR = 30
SCENE_RANK_BUNDLED = 40
SCENE_RANK_TERMINAL = 100

# The scene source-layer prefixes. A position's canonical source id is
# ``<prefix>:<identity>`` — the authored room-art key, the scene subject's own
# generation key, the scene key, or the terminal key. A FACT of a position
# names the exact thing it belongs to after the colon (the content directory
# identity, or one admitted image's identity), exactly like the portrait
# chain's own official faults, so two facts of one position never collide.
SCENE_ROOM_SOURCE_PREFIX = "scene.room"
SCENE_GENERATED_SOURCE_PREFIX = "scene.generated"
SCENE_OPERATOR_SOURCE_PREFIX = "scene.operator"
SCENE_BUNDLED_SOURCE_PREFIX = "scene.bundled"
SCENE_TERMINAL_SOURCE_PREFIX = "scene.terminal"


def scene_room_source_id(room_art_key: str) -> str:
    """The canonical source id of one authored per-room operator override."""
    return f"{SCENE_ROOM_SOURCE_PREFIX}:{room_art_key}"


def scene_generated_source_id(generation_subject: str) -> str:
    """The canonical source id of one scene archetype's generated artwork."""
    return f"{SCENE_GENERATED_SOURCE_PREFIX}:{generation_subject}"


def scene_operator_source_id(scene_key: str) -> str:
    """The canonical source id of one optional operator scene default."""
    return f"{SCENE_OPERATOR_SOURCE_PREFIX}:{scene_key}"


def scene_bundled_source_id(scene_key: str) -> str:
    """The canonical source id of one required bundled scene illustration."""
    return f"{SCENE_BUNDLED_SOURCE_PREFIX}:{scene_key}"


def scene_terminal_source_id(terminal_key: str) -> str:
    """The canonical source id of one scene's declared terminal image."""
    return f"{SCENE_TERMINAL_SOURCE_PREFIX}:{terminal_key}"


def gallery_original_source_id(image_id: str) -> str:
    """The canonical source id of one exact requested gallery original."""
    return f"gallery.original:{image_id}"


def gallery_official_source_id(identity: str) -> str:
    """The canonical source id of one exact catalog-admitted official image."""
    return f"gallery.official:{identity}"


def gallery_alpha_source_id(key: str) -> str:
    """The canonical source id of one committed silhouette alpha mask."""
    return f"gallery.alpha:{key}"


def portrait_bound_source_id(image_id: str) -> str:
    """The canonical source id of one equipment-bound portrait card."""
    return f"portrait.bound:{image_id}"


def portrait_personal_source_id(identity: str) -> str:
    """The canonical source id of one person's explicit official selection."""
    return f"portrait.personal:{identity}"


def portrait_default_source_id(image_id: str) -> str:
    """The canonical source id of one record's named default card."""
    return f"portrait.default:{image_id}"


def portrait_classic_source_id(generation_subject: str) -> str:
    """The canonical source id of one subject's classic generated asset."""
    return f"portrait.classic:{generation_subject}"


def portrait_official_source_id(reference: str) -> str:
    """The canonical source id of one entity's official content reference.

    ``reference`` is the catalog's own ``<content-kind>/<content-key>`` text:
    one entity's reference is ONE source position, so its candidate and every
    fault at that position share this id.
    """
    return f"portrait.official:{reference}"


def portrait_alpha_source_id(key: str) -> str:
    """The canonical source id of one committed silhouette alpha mask."""
    return f"portrait.alpha:{key}"


def identity_version(identity: str) -> str:
    """The stable version of one immutable admitted identity.

    A stored card, a catalog-admitted official image and a committed built-in
    silhouette are all immutable: their identity IS their version input, so a
    replacement is a new identity rather than a mutation of old bytes. Whole
    image bytes are never hashed here. It uses the one digest convention of
    this module, so a lone surrogate in a fact is escaped rather than fatal.
    """
    return _digest(identity)


def generated_version(identity: str, generation_token: str) -> str:
    """The stable version of one generated resource at a republishable identity.

    Whole image bytes are never hashed and neither is the pending/failed
    regeneration state: a validated output identity plus the successful
    generation token that published it distinguish a regenerated file at the
    same path, so the version changes exactly when the bytes a completed
    generation produced change.
    """
    return _digest((identity, generation_token))


# --- Builders -------------------------------------------------------------


def image_size_payload(width: int, height: int) -> dict:
    """The exact decoded-size mapping one geometry carries."""
    return {"width": width, "height": height}


def geometry(
    *,
    image_size: dict | None = None,
    face_rect: dict | None = None,
    stage: dict | None = None,
    aspect_ratio: str | None = None,
) -> dict:
    """A geometry with exactly its four keys, each nullable as applicable.

    A scene resource carries null face/stage; a silhouette alpha mask carries
    its own rectangle with no decoded size; a runtime original carries all of
    the facts its card stored plus the subject's aspect ratio. The returned
    container is always fresh; the nested facts are the caller's own
    already-fresh mappings (a reader hands over the dicts it just validated,
    never shared mutable state).
    """
    return {
        "image_size": image_size,
        "face_rect": face_rect,
        "stage": stage,
        "aspect_ratio": aspect_ratio,
    }


def resource(
    resource_id: str, version: str, url: str, origin: str, *, geometry_payload: dict | None = None
) -> dict:
    """One candidate/terminal resource: canonical identity, version, URL, origin, geometry."""
    return {
        "resource_id": resource_id,
        "version": version,
        "url": url,
        "origin": origin,
        "geometry": geometry_payload,
    }


def image_attempt(source_id: str, rank: int, resource_payload: dict) -> dict:
    """One real, loadable candidate at its stable source-layer rank."""
    return {"type": "image", "source_id": source_id, "rank": rank, "resource": resource_payload}


def fault_attempt(source_id: str, rank: int, reason: str) -> dict:
    """One REACHED known fault at the exact position its source occupies.

    A fault names its failed source and a bounded reason and NEVER a URL, so a
    broken preference can never be presented as an image.
    """
    return {"type": "fault", "source_id": source_id, "rank": rank, "reason": reason}


def terminal(kind: str, source_id: str, rank: int, resource_payload: dict) -> dict:
    """One permitted terminal fallback (the alpha silhouette) with its own source and rank."""
    return {
        "kind": kind,
        "source_id": source_id,
        "rank": rank,
        "resource": resource_payload,
    }


def retention_source(source_id: str, token: str) -> dict:
    """One backend-authorized retention entry: an exact source and its token."""
    return {"source_id": source_id, "token": token}


def retention_token(*facts: object) -> str:
    """The 64-character token of one retention authorization.

    The token covers exactly what makes old pixels still applicable — the
    subject and generation subject, the current authorized binding/source
    applicability and the access policy — and deliberately excludes geometry
    and pending/failed regeneration state, so a re-render or an in-flight
    regeneration never revokes a still-valid known-good output.
    """
    return _digest(facts)


def revision_for(
    *,
    subject_id: str,
    generation_subject: str | None,
    generation_state: str | None,
    attempts: list,
    terminal_payload: dict | None,
    retention_sources: list,
) -> str:
    """The 64-character revision digest of one descriptor's ordered facts.

    Ordered source/fault facts, source versions, geometry, binding/access
    applicability (the retention tokens) and generation facts all enter; the
    revision itself never does.
    """
    return _digest(
        (
            subject_id,
            generation_subject,
            generation_state,
            attempts,
            terminal_payload,
            retention_sources,
        )
    )


def descriptor(
    *,
    subject_id: str,
    generation_subject: str | None,
    generation_state: str | None,
    attempts: list,
    terminal_payload: dict | None,
    retention_sources: list,
) -> dict:
    """One canonical descriptor with exactly its seven keys and its own revision."""
    return {
        "subject_id": subject_id,
        "revision": revision_for(
            subject_id=subject_id,
            generation_subject=generation_subject,
            generation_state=generation_state,
            attempts=attempts,
            terminal_payload=terminal_payload,
            retention_sources=retention_sources,
        ),
        "generation_subject": generation_subject,
        "generation_state": generation_state,
        "attempts": attempts,
        "terminal": terminal_payload,
        "retention_sources": retention_sources,
    }


def _digest(facts: object) -> str:
    """The one digest convention: sha256 over the canonical JSON of the facts.

    The canonical form is ASCII-escaped: it is byte-stable for every input a
    validated fact can carry (including a lone surrogate, which the active
    validators reject at the wire but which must never turn a digest into a
    UnicodeEncodeError).
    """
    encoded = json.dumps(facts, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
