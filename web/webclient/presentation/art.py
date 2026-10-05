"""Exact schema-version-2 ``art`` panel and presenter (webclient-art-panel).

The presenter composes the frozen art view owned by
``world.rules.art_view`` with the read-only resolution primitives in
``world.art.presenter`` (``resolve_scene`` / ``resolve_entity``) and validates
its own output against the exact bounded schema before returning it to the
presentation registry. The panel is available in ``exploration`` and ``combat``
modes; a creation-pending shell raises :class:`PanelUnavailableError` so the
registry emits the common unavailable form.

The payload contains exactly ``schema_version``, ``available``, ``kind``, the
current scene (validated archetype, label, subject key, status, same-origin
URL, aspect, alternative text, and a nullable placeholder) and a bounded
``portrait_catalog`` keyed by the opaque IDs of currently present focusable
entities, each entry additionally carrying the resolved normalized face
rectangle (exactly ``x``, ``y``, ``w``, ``h`` in ``[0, 1]`` whenever the entry
has a media URL, ``null`` for every placeholder), the server-authored origin
discriminator (the closed vocabulary ``runtime``/``official``/
``silhouette``/``placeholder``, see ``official-art-resolution``), and the
decorative built-in silhouette the fallback seam resolved (``key``, committed
``/art/defaults/`` URL and rectangle, see ``art-gallery-fallback``). It never
exposes ``out_path``, the store root, or rejected prompt content. The origin
rules — including that an ``official`` entry always carries its own media URL
and never a generated status — are shared with the roster row portrait
(``_validate_portrait_origin``), so the two vocabularies cannot drift.
"""

from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    _validate_identifier,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.art.presenter import (
    ORIGIN_OFFICIAL,
    ORIGIN_PLACEHOLDER,
    ORIGIN_RUNTIME,
    ORIGIN_SILHOUETTE,
    resolve_entity,
    resolve_scene,
)
from world.art.gallery import GalleryRecordError, validate_stage
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.rules.art_view import (
    MAX_PORTRAIT_CATALOG,
    ROLE_ALLY,
    ROLE_DIALOGUE,
    ROLE_FOE,
    ROLE_PERSON,
    ArtViewError,
    build_art_view,
)

ART_SCHEMA_VERSION = 2

# Stable panel-level bounds equal to or below the global protocol table.
MAX_ARCHETYPE = 64
MAX_LABEL = 128
MAX_SUBJECT_KEY = 128
MAX_MEDIA_URL = 256
MAX_ALT = 512
MAX_STATUS = 16
MAX_PLACEHOLDER_KIND = 16
MAX_PLACEHOLDER_LABEL = 128
MAX_CONTEXT_NAME = 64
MAX_CONTEXT_ROLE = 16
MAX_FALLBACK_KEY = 32
MAX_ORIGIN = 16

PLACEHOLDER_KINDS = frozenset({"missing", "unavailable"})
ROLES = frozenset({ROLE_ALLY, ROLE_DIALOGUE, ROLE_FOE, ROLE_PERSON})
# The closed portrait-origin vocabulary (owned by ``world.art.presenter``;
# `official-art-resolution-contracts` extends both sides with ``official``).
PORTRAIT_ORIGINS = frozenset(
    {ORIGIN_OFFICIAL, ORIGIN_PLACEHOLDER, ORIGIN_RUNTIME, ORIGIN_SILHOUETTE}
)
# The committed built-in identities the decorative fallback may name.
FALLBACK_URL_PREFIX = "/art/defaults/"


class ArtPanelError(ProtocolValidationError):
    """The available art payload violates its exact bounded schema."""


def _validate_face_rect(value: Any) -> dict[str, float] | None:
    """Validate the wire face rectangle: ``None`` or exactly x, y, w, h reals.

    Shared by the art catalog entry and the roster row portrait (the same
    portrait field vocabulary on both wires). Every coordinate is a real
    number in ``[0, 1]``; booleans are not numbers here. The server ships
    placement metadata only — no crop, no second image.
    """
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"x", "y", "w", "h"}:
        raise ProtocolValidationError(
            "face_rect must be a mapping of exactly x, y, w, h"
        )
    rect: dict[str, float] = {}
    for name in ("x", "y", "w", "h"):
        coordinate = value[name]
        if not isinstance(coordinate, (int, float)) or isinstance(coordinate, bool):
            raise ProtocolValidationError(f"face_rect.{name} must be a real number")
        if not 0.0 <= coordinate <= 1.0:
            raise ProtocolValidationError(f"face_rect.{name} must lie in [0, 1]")
        rect[name] = coordinate
    return rect


def _validate_stage(value: Any, url: str | None) -> dict | None:
    """Enforce asset placement and truthful placeholder nullability."""
    if url is None:
        if value is not None:
            raise ProtocolValidationError("a placeholder carries no stage")
        return None
    try:
        return validate_stage(value)
    except GalleryRecordError as exc:  # observability: ignore R2: wire validation returns a typed refusal
        raise ProtocolValidationError("invalid asset stage") from exc


def _validate_placeholder(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    _require_exact_fields(value, "art placeholder", {"kind", "label"}, {})
    kind = value["kind"]
    if kind not in PLACEHOLDER_KINDS:
        raise ProtocolValidationError("placeholder kind is not a stable value")
    label = _require_str(value, "label", maximum=MAX_PLACEHOLDER_LABEL)
    if not label.strip():
        raise ProtocolValidationError("placeholder label must be non-empty")
    return {"kind": kind, "label": label}


def _validate_portrait_fallback(value: Any) -> dict[str, Any] | None:
    """Validate the decorative built-in silhouette reference.

    ``None``, or exactly ``key``, ``url``, and ``face_rect``: the committed
    fallback key, its ``/art/defaults/`` identity, and that key's normalized
    rectangle. The field is presentation data for a still-absent portrait —
    the caller keeps it out of the entry's own fields — so it carries a URL
    only under that closed prefix and never a second portrait.
    """
    if value is None:
        return None
    _require_exact_fields(value, "art fallback", {"key", "url", "face_rect"}, {})
    key = _require_str(value, "key", maximum=MAX_FALLBACK_KEY)
    if not key.strip():
        raise ProtocolValidationError("fallback key must be non-empty")
    url = _require_str(value, "url", maximum=MAX_MEDIA_URL)
    if not url.startswith(FALLBACK_URL_PREFIX):
        raise ProtocolValidationError(
            "fallback url must name a committed built-in identity"
        )
    face_rect = _validate_face_rect(value["face_rect"])
    if face_rect is None:
        raise ProtocolValidationError("a fallback carries a face_rect")
    return {"key": key, "url": url, "face_rect": face_rect}


def _validate_portrait_origin(
    field: str, noun: str, portrait: Any, url: str | None, status: str | None
) -> str:
    """The server-authored origin discriminator, coherent with its own media.

    Shared by the art catalog entry and the roster row portrait — the same
    portrait field vocabulary on both wires — so the two can never drift: the
    value is inside the closed vocabulary
    ``runtime | official | silhouette | placeholder`` and it names the branch
    that produced the payload's OWN media, never a URL shape. A ``silhouette``
    or ``placeholder`` origin therefore never carries that media URL, a
    ``runtime`` or ``official`` origin always does, and an ``official`` image
    is never reported with a generated-portrait status, because a read-only
    catalog default is not a generated asset (``official-art-resolution``).
    ``field`` and ``noun`` only name the surface in the refusal messages
    ("catalog origin"/"catalog entry" or "portrait origin"/"portrait"); the
    wire key itself is always ``origin``.
    """
    origin = _require_str(portrait, "origin", maximum=MAX_ORIGIN)
    if origin not in PORTRAIT_ORIGINS:
        raise ProtocolValidationError(f"{field} is not a stable value")
    if url is not None and origin in (ORIGIN_SILHOUETTE, ORIGIN_PLACEHOLDER):
        raise ProtocolValidationError(
            f"a {noun} carrying a media URL is not a silhouette or a placeholder"
        )
    if url is None and origin in (ORIGIN_RUNTIME, ORIGIN_OFFICIAL):
        raise ProtocolValidationError(
            f"an {origin} origin carries the {noun}'s media URL"
        )
    if origin == ORIGIN_OFFICIAL and status is not None:
        raise ProtocolValidationError(
            "an official image is not a generated portrait"
        )
    return origin


def _validate_scene(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "art scene",
        {
            "archetype",
            "stage",
            "label",
            "subject_key",
            "status",
            "url",
            "aspect_ratio",
            "alt",
            "placeholder",
        },
        {},
    )
    archetype = value["archetype"]
    if archetype is not None:
        archetype = _require_str(value, "archetype", maximum=MAX_ARCHETYPE)
        if not archetype.strip():
            raise ProtocolValidationError("scene archetype must be non-empty")
    label = _require_str(value, "label", maximum=MAX_LABEL)
    if not label.strip():
        raise ProtocolValidationError("scene label must be non-empty")
    subject_key = value["subject_key"]
    if subject_key is not None:
        subject_key = _require_str(value, "subject_key", maximum=MAX_SUBJECT_KEY)
        if not subject_key.strip():
            raise ProtocolValidationError("scene subject_key must be non-empty")
    status = value["status"]
    if status is not None:
        status = _require_str(value, "status", maximum=MAX_STATUS)
        if status not in ("missing", "pending", "failed", "done"):
            raise ProtocolValidationError("scene status is not a stable value")
    url = value["url"]
    if url is not None:
        url = _require_str(value, "url", maximum=MAX_MEDIA_URL)
        if not url.startswith("/art/"):
            raise ProtocolValidationError("scene url must be a same-origin media URL")
    aspect_ratio = value["aspect_ratio"]
    if aspect_ratio is not None:
        aspect_ratio = _require_str(value, "aspect_ratio", maximum=16)
        if aspect_ratio != "16:9":
            raise ProtocolValidationError("scene aspect_ratio must be 16:9")
    alt = _require_str(value, "alt", maximum=MAX_ALT)
    if not alt.strip():
        raise ProtocolValidationError("scene alt must be non-empty")
    placeholder = _validate_placeholder(value["placeholder"])
    stage = _validate_stage(value["stage"], url)
    if placeholder is None and status != "done":
        # An unavailable scene without a placeholder is not truthful.
        raise ProtocolValidationError("scene placeholder must be present unless done")
    if placeholder is not None and status == "done":
        raise ProtocolValidationError("a done scene must not carry a placeholder")
    return {
        "archetype": archetype,
        "stage": stage,
        "label": label,
        "subject_key": subject_key,
        "status": status,
        "url": url,
        "aspect_ratio": aspect_ratio,
        "alt": alt,
        "placeholder": placeholder,
    }


def _validate_context(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "art context", {"name", "role"}, {})
    name = _require_str(value, "name", maximum=MAX_CONTEXT_NAME)
    if not name.strip():
        raise ProtocolValidationError("context name must be non-empty")
    role = _require_str(value, "role", maximum=MAX_CONTEXT_ROLE)
    if role not in ROLES:
        raise ProtocolValidationError("context role is not a stable value")
    return {"name": name, "role": role}


def _validate_catalog_entry(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "art catalog entry",
        {
            "subject_key",
            "status",
            "url",
            "aspect_ratio",
            "alt",
            "placeholder",
            "face_rect",
            "stage",
            "context",
            "origin",
            "fallback",
        },
        {},
    )
    subject_key = value["subject_key"]
    if subject_key is not None:
        subject_key = _require_str(value, "subject_key", maximum=MAX_SUBJECT_KEY)
        if not subject_key.strip():
            raise ProtocolValidationError("catalog subject_key must be non-empty")
    status = value["status"]
    if status is not None:
        status = _require_str(value, "status", maximum=MAX_STATUS)
        if status not in ("missing", "pending", "failed", "done"):
            raise ProtocolValidationError("catalog status is not a stable value")
    url = value["url"]
    if url is not None:
        url = _require_str(value, "url", maximum=MAX_MEDIA_URL)
        if not url.startswith("/art/"):
            raise ProtocolValidationError("catalog url must be a same-origin media URL")
    aspect_ratio = value["aspect_ratio"]
    if aspect_ratio is not None:
        aspect_ratio = _require_str(value, "aspect_ratio", maximum=16)
        if aspect_ratio != "3:4":
            raise ProtocolValidationError("catalog aspect_ratio must be 3:4")
    alt = _require_str(value, "alt", maximum=MAX_ALT)
    if not alt.strip():
        raise ProtocolValidationError("catalog alt must be non-empty")
    placeholder = _validate_placeholder(value["placeholder"])
    context = _validate_context(value["context"])
    face_rect = _validate_face_rect(value["face_rect"])
    stage = _validate_stage(value["stage"], url)
    origin = _validate_portrait_origin(
        "catalog origin", "catalog entry", value, url, status
    )
    fallback = _validate_portrait_fallback(value["fallback"])
    # A client never offsets a frame it has no image for: the rectangle is
    # present exactly when the entry carries a media URL.
    if url is not None and face_rect is None:
        raise ProtocolValidationError("a catalog entry with a url carries a face_rect")
    if url is None and face_rect is not None:
        raise ProtocolValidationError("a catalog placeholder carries no face_rect")
    # The decorative reference has no meaning on an entry whose own media is
    # already absent for a different reason, so it is required exactly by the
    # silhouette origin and refused by the placeholder origin.
    if origin == ORIGIN_SILHOUETTE:
        if fallback is None:
            raise ProtocolValidationError(
                "a silhouette origin carries its fallback identity"
            )
        if status == "done":
            raise ProtocolValidationError("a silhouette origin is not a done portrait")
    elif origin == ORIGIN_PLACEHOLDER and fallback is not None:
        raise ProtocolValidationError("a placeholder origin carries no fallback identity")
    return {
        "subject_key": subject_key,
        "status": status,
        "url": url,
        "aspect_ratio": aspect_ratio,
        "alt": alt,
        "placeholder": placeholder,
        "face_rect": face_rect,
        "stage": stage,
        "context": context,
        "origin": origin,
        "fallback": fallback,
    }


def validate_art(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``art`` payload.

    Returns a normalized payload or raises :class:`ArtPanelError`. The common
    unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "art panel",
        {
            "schema_version",
            "available",
            "kind",
            "scene",
            "portrait_catalog",
        },
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != ART_SCHEMA_VERSION:
        raise ArtPanelError("unsupported art schema_version")
    if not _require_bool(payload, "available"):
        raise ArtPanelError("available must be true for the art form")
    if payload["kind"] != "scene":
        raise ArtPanelError("art panel kind must be scene")

    scene = _validate_scene(payload["scene"])
    catalog = payload["portrait_catalog"]
    if not isinstance(catalog, dict) or len(catalog) > MAX_PORTRAIT_CATALOG:
        raise ArtPanelError("portrait_catalog must be a bounded object")
    entries: dict[str, Any] = {}
    for key, value in catalog.items():
        if not isinstance(key, str) or not key or not key.isdecimal():
            raise ArtPanelError("catalog keys must be opaque decimal strings")
        entries[key] = _validate_catalog_entry(value)

    result = {
        "schema_version": ART_SCHEMA_VERSION,
        "available": True,
        "kind": "scene",
        "scene": scene,
        "portrait_catalog": entries,
    }
    # Envelope guarantee: per-field bounds are ceilings, not a guarantee that
    # any combination of them fits, so the validator enforces the serialized
    # size directly -- an all-ceilings payload fails closed.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise ArtPanelError("art payload exceeds the OOB envelope limit")
    return result


# ---------------------------------------------------------------------------
# Serialization from the frozen art view.
# ---------------------------------------------------------------------------


def _placeholder_for(value: dict[str, Any]) -> dict[str, Any] | None:
    """The placeholder descriptor a payload carries when no image did.

    ``None`` whenever the payload carries its own media URL — a runtime card,
    a classic asset, or an official default — and the payload's own kind/label
    otherwise. Keying on the URL rather than on the ``asset`` kind keeps the
    official branch (a real image, but not a generated asset, so not ``done``)
    on the same rule: the descriptor exists exactly when no image does, which
    is also what keeps the roster row's url-XOR-placeholder rule intact.
    """
    if value.get("url") is not None:
        return None
    return {"kind": value["kind"], "label": value["label"]}


def _serialize_scene(archetype: str | None) -> dict[str, Any]:
    if archetype is None:
        return {
            "archetype": None,
            "stage": None,
            "label": "無法提供",
            "subject_key": None,
            "status": None,
            "url": None,
            "aspect_ratio": None,
            "alt": "無法提供",
            "placeholder": {"kind": "unavailable", "label": "無法提供"},
        }
    registry_entry = SCENE_ARCHETYPE_REGISTRY.get(archetype)
    label = registry_entry.display_name_zh if registry_entry is not None else "場景"
    resolved = resolve_scene(archetype)
    return {
        "archetype": archetype,
        "stage": resolved.get("stage"),
        "label": label,
        "subject_key": resolved.get("subject_key"),
        "status": resolved.get("status"),
        "url": resolved.get("url"),
        "aspect_ratio": resolved.get("aspect_ratio"),
        "alt": resolved.get("alt") or label,
        "placeholder": _placeholder_for(resolved),
    }


def _serialize_catalog_entry(entity_view: Any) -> dict[str, Any]:
    from evennia.objects.models import ObjectDB

    entity = ObjectDB.objects.filter(id=int(entity_view.identity)).first()
    if entity is None:
        resolved = {
            "kind": "unavailable",
            "label": "無法提供",
            "status": None,
            "url": None,
            "aspect_ratio": None,
            "alt": "無法提供",
            "subject_key": None,
            "face_rect": None,
            "stage": None,
            "origin": ORIGIN_PLACEHOLDER,
            "fallback": None,
        }
    else:
        resolved = resolve_entity(entity)
    return {
        "subject_key": resolved.get("subject_key"),
        "status": resolved.get("status"),
        "url": resolved.get("url"),
        "aspect_ratio": resolved.get("aspect_ratio"),
        "alt": resolved.get("alt") or "無法提供",
        "placeholder": _placeholder_for(resolved),
        "face_rect": resolved.get("face_rect"),
        "stage": resolved.get("stage"),
        "origin": resolved.get("origin"),
        "fallback": resolved.get("fallback"),
        "context": {
            "name": entity_view.display_name,
            "role": entity_view.role,
        },
    }


def _serialize(view: Any) -> dict[str, Any]:
    scene = _serialize_scene(view.scene_archetype)
    catalog: dict[str, Any] = {}
    for entity_view in view.entities:
        catalog[str(int(entity_view.identity))] = _serialize_catalog_entry(entity_view)
    return {
        "schema_version": ART_SCHEMA_VERSION,
        "available": True,
        "kind": "scene",
        "scene": scene,
        "portrait_catalog": catalog,
    }


def _in_supported_mode(actor: Any) -> bool:
    # Available in exploration and combat; creation-pending shells use the
    # common unavailable form.
    return not bool(getattr(actor, "creation_pending", False))


def art_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``art`` panel for the authenticated puppet."""
    actor = context.actor
    if not _in_supported_mode(actor):
        raise PanelUnavailableError
    try:
        view = build_art_view(actor)
    except ArtViewError:
        raise PanelUnavailableError
    return validate_art(_serialize(view))


__all__ = [
    "ART_SCHEMA_VERSION",
    "ArtPanelError",
    "FALLBACK_URL_PREFIX",
    "MAX_ARCHETYPE",
    "MAX_ALT",
    "MAX_CONTEXT_NAME",
    "MAX_CONTEXT_ROLE",
    "MAX_FALLBACK_KEY",
    "MAX_LABEL",
    "MAX_ORIGIN",
    "MAX_PLACEHOLDER_KIND",
    "MAX_PLACEHOLDER_LABEL",
    "MAX_STATUS",
    "MAX_SUBJECT_KEY",
    "MAX_MEDIA_URL",
    "PLACEHOLDER_KINDS",
    "PORTRAIT_ORIGINS",
    "ROLES",
    "_validate_face_rect",
    "_validate_portrait_fallback",
    "_validate_portrait_origin",
    "_placeholder_for",
    "art_presenter",
    "validate_art",
]
