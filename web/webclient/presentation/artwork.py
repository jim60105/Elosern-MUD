"""The canonical artwork descriptor wire serializer/validator.

Change ``unified-gallery-image-contract`` (design §"Canonical interface owned
by this change"). Exactly one bounded validator owns the descriptor's wire
shape: the container's exact key sets, the identity/version/rank/retention
bounds, the same-origin media URL rule with its per-origin ceiling and its one
closed cache-version query form, and the applicable geometry. Every panel that
carries a descriptor calls :func:`validate_artwork`; the browser mirror is
``web/static/webclient/js/elosern/protocol/artwork.js``.

The shape mirrors ``world.art.descriptors`` exactly, and both sides read the
same constants rather than re-declaring a bound. This module is a validator,
not a resolver: it never selects a source, never reads game state, and never
writes.

Origin-SPECIFIC route checks (an official fingerprint vocabulary, a gallery
route bound to the selected subject and image) stay with the panel that owns
that route, because only that panel knows which subject the descriptor
describes.
"""

from __future__ import annotations

import math
import re

from world.art import descriptors

from .protocol import (
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_exact_fields,
)

DESCRIPTOR_FIELDS = (
    "subject_id",
    "revision",
    "generation_subject",
    "generation_state",
    "attempts",
    "terminal",
    "retention_sources",
)
RESOURCE_FIELDS = ("resource_id", "version", "url", "origin", "geometry")
GEOMETRY_FIELDS = ("image_size", "face_rect", "stage", "aspect_ratio")
IMAGE_ATTEMPT_FIELDS = ("type", "source_id", "rank", "resource")
FAULT_ATTEMPT_FIELDS = ("type", "source_id", "rank", "reason")
TERMINAL_FIELDS = ("kind", "source_id", "rank", "resource")
RETENTION_FIELDS = ("source_id", "token")
IMAGE_SIZE_FIELDS = ("width", "height")
FACE_RECT_FIELDS = ("x", "y", "w", "h")
STAGE_FIELDS = ("scale", "x", "y")
ATTEMPT_TYPES = ("image", "fault")

# The art media route prefix every canonical URL lives under, and the one
# closed query form a republishable generated path may carry.
MEDIA_URL_PREFIX = "/art/"
_FINGERPRINT = re.compile(r"[0-9a-f]{64}")
_ASPECT_RATIO = re.compile(r"[0-9]{1,4}:[0-9]{1,4}")
# The stage triple's closed bounds, mirroring world.art.gallery.validate_stage.
_STAGE_BOUNDS = (("scale", 0.2, 2.0), ("x", -0.5, 0.5), ("y", -0.5, 0.5))


def _exact(value, keys, name):
    _require_exact_fields(value, name, set(keys), {})


def _text(value, maximum, name):
    if (
        not isinstance(value, str)
        or not value
        or len(value) > maximum
        or any(0xD800 <= ord(char) <= 0xDFFF for char in value)
    ):
        raise ProtocolValidationError(f"invalid {name}")
    return value


def _fingerprint(value, name):
    if not isinstance(value, str) or _FINGERPRINT.fullmatch(value) is None:
        raise ProtocolValidationError(f"invalid {name}")
    return value


def _number(value, name):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or abs(value) > MAX_SAFE_INTEGER
        or not math.isfinite(value)
    ):
        raise ProtocolValidationError(f"invalid {name}")
    return value


def _positive_integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ProtocolValidationError(f"invalid {name}")
    return value


def media_url(value, origin):
    """Return one bounded same-origin media URL for ``origin``.

    Exactly the art route prefix, no fragment, printable text only (the same
    ``isprintable`` discipline the server's own URL builder satisfies, so no
    control character or exotic separator can slip through while a
    non-ASCII subject key still produces its own real URL), no ``..`` segment,
    at most the origin's own URL ceiling, and an OPTIONAL cache version that
    must be the single closed ``?v=<sha256>`` form — never a second query key,
    a list, or an absolute URL to another origin.
    """
    limit = descriptors.MEDIA_URL_LIMITS.get(origin)
    if limit is None:
        raise ProtocolValidationError("invalid origin")
    if not isinstance(value, str) or not value or len(value) > limit:
        raise ProtocolValidationError("invalid media url")
    path, marker, query = value.partition("?")
    if marker:
        key, separator, digest = query.partition("=")
        if separator != "=" or key != descriptors.VERSION_QUERY or _FINGERPRINT.fullmatch(digest) is None:
            raise ProtocolValidationError("invalid media url version")
    if not path.startswith(MEDIA_URL_PREFIX) or not path.isprintable():
        raise ProtocolValidationError("media url must name the same-origin art route")
    if ".." in path.split("/"):
        raise ProtocolValidationError("media url must not traverse")
    return value


def validate_geometry(value):
    """Validate one geometry: exactly four keys, each null or an exact domain value."""
    if value is None:
        return None
    _exact(value, GEOMETRY_FIELDS, "geometry")
    size = value["image_size"]
    if size is not None:
        _exact(size, IMAGE_SIZE_FIELDS, "image_size")
        width = _positive_integer(size["width"], "image_size width")
        height = _positive_integer(size["height"], "image_size height")
        if (
            width > descriptors.MAX_IMAGE_DIMENSION
            or height > descriptors.MAX_IMAGE_DIMENSION
            or width * height > descriptors.MAX_IMAGE_PIXELS
        ):
            raise ProtocolValidationError("image_size exceeds the decoded-size ceiling")
    rect = value["face_rect"]
    if rect is not None:
        validate_face_rect(rect)
    stage = value["stage"]
    if stage is not None:
        validate_stage(stage)
    ratio = value["aspect_ratio"]
    if ratio is not None and (
        not isinstance(ratio, str) or _ASPECT_RATIO.fullmatch(ratio) is None
    ):
        raise ProtocolValidationError("invalid aspect_ratio")
    return {
        "image_size": None if size is None else {"width": size["width"], "height": size["height"]},
        "face_rect": rect,
        "stage": stage,
        "aspect_ratio": ratio,
    }


def validate_face_rect(rect):
    """Exactly x, y, w, h as real numbers in ``[0, 1]`` forming a positive unit-square fit."""
    _exact(rect, FACE_RECT_FIELDS, "face_rect")
    for name in FACE_RECT_FIELDS:
        number = _number(rect[name], f"face_rect {name}")
        if not 0.0 <= number <= 1.0:
            raise ProtocolValidationError("face_rect must lie in the unit square")
    if rect["x"] + rect["w"] > 1 or rect["y"] + rect["h"] > 1:
        raise ProtocolValidationError("face_rect must lie inside the unit square")
    if rect["w"] <= 0 or rect["h"] <= 0:
        raise ProtocolValidationError("face_rect w and h must be positive")
    return rect


def validate_stage(stage):
    """Exactly scale, x, y as real numbers inside the shared finite placement bounds."""
    _exact(stage, STAGE_FIELDS, "stage")
    for name, lower, upper in _STAGE_BOUNDS:
        number = _number(stage[name], f"stage {name}")
        if not lower <= number <= upper:
            raise ProtocolValidationError("stage value out of bounds")
    return stage


def validate_resource(value):
    """Validate one candidate/terminal resource and return it verbatim."""
    _exact(value, RESOURCE_FIELDS, "resource")
    _text(value["resource_id"], descriptors.MAX_RESOURCE_ID, "resource_id")
    _fingerprint(value["version"], "resource version")
    origin = value["origin"]
    if origin not in descriptors.ORIGINS:
        raise ProtocolValidationError("invalid resource origin")
    media_url(value["url"], origin)
    validate_geometry(value["geometry"])
    return value


def validate_artwork(payload):
    """Validate one canonical descriptor and return it verbatim.

    Exactly the seven descriptor keys, in the canonical fact vocabulary. A
    fault entry carries no resource (and so no URL), a terminal names a
    permitted kind, and a terminal whose bytes already appear among the
    attempts is rejected: the terminal is a FALLBACK, not a second copy of a
    candidate the caller already listed.
    """
    _exact(payload, DESCRIPTOR_FIELDS, "artwork")
    _text(payload["subject_id"], descriptors.MAX_SUBJECT_ID, "subject_id")
    _fingerprint(payload["revision"], "revision")
    generation_subject = payload["generation_subject"]
    if generation_subject is not None:
        _text(generation_subject, descriptors.MAX_SUBJECT_ID, "generation_subject")
    generation_state = payload["generation_state"]
    if generation_state is not None and generation_state not in descriptors.GENERATION_STATES:
        raise ProtocolValidationError("invalid generation state")
    attempts = payload["attempts"]
    if not isinstance(attempts, list) or len(attempts) > descriptors.MAX_ATTEMPTS:
        raise ProtocolValidationError("invalid attempts")
    seen = set()
    resource_keys = set()
    for attempt in attempts:
        if not isinstance(attempt, dict) or attempt.get("type") not in ATTEMPT_TYPES:
            raise ProtocolValidationError("invalid attempt")
        image = attempt["type"] == "image"
        _exact(attempt, IMAGE_ATTEMPT_FIELDS if image else FAULT_ATTEMPT_FIELDS, "attempt")
        source_id = _text(attempt["source_id"], descriptors.MAX_SOURCE_ID, "source_id")
        rank = _number(attempt["rank"], "attempt rank")
        if rank < 0:
            raise ProtocolValidationError("attempt rank must be nonnegative")
        if (attempt["type"], source_id, rank) in seen:
            raise ProtocolValidationError("duplicate attempt")
        seen.add((attempt["type"], source_id, rank))
        if image:
            resource = validate_resource(attempt["resource"])
            resource_keys.add((resource["resource_id"], resource["version"]))
        elif attempt["reason"] not in descriptors.FAULT_REASONS:
            raise ProtocolValidationError("invalid fault reason")
    terminal = payload["terminal"]
    if terminal is not None:
        _exact(terminal, TERMINAL_FIELDS, "terminal")
        if terminal["kind"] not in descriptors.TERMINAL_KINDS:
            raise ProtocolValidationError("invalid terminal kind")
        _text(terminal["source_id"], descriptors.MAX_SOURCE_ID, "terminal source_id")
        if _number(terminal["rank"], "terminal rank") < 0:
            raise ProtocolValidationError("terminal rank must be nonnegative")
        resource = validate_resource(terminal["resource"])
        if (resource["resource_id"], resource["version"]) in resource_keys:
            raise ProtocolValidationError("terminal duplicates an attempt resource")
    retention = payload["retention_sources"]
    if not isinstance(retention, list) or len(retention) > descriptors.MAX_RETENTION_SOURCES:
        raise ProtocolValidationError("invalid retention sources")
    retained = set()
    for entry in retention:
        _exact(entry, RETENTION_FIELDS, "retention entry")
        source_id = _text(entry["source_id"], descriptors.MAX_SOURCE_ID, "retention source_id")
        _fingerprint(entry["token"], "retention token")
        if source_id in retained:
            raise ProtocolValidationError("duplicate retention source")
        retained.add(source_id)
    return payload
