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
has a media URL, ``null`` for every placeholder). It never exposes
``out_path``, the store root, or rejected prompt content.
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
from world.art.presenter import resolve_entity, resolve_scene
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
MAX_ALT = 512
MAX_STATUS = 16
MAX_PLACEHOLDER_KIND = 16
MAX_PLACEHOLDER_LABEL = 128
MAX_CONTEXT_NAME = 64
MAX_CONTEXT_ROLE = 16

PLACEHOLDER_KINDS = frozenset({"missing", "unavailable"})
ROLES = frozenset({ROLE_ALLY, ROLE_DIALOGUE, ROLE_FOE, ROLE_PERSON})


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


def _validate_scene(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "art scene",
        {
            "archetype",
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
        url = _require_str(value, "url", maximum=MAX_SUBJECT_KEY)
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
    if placeholder is None and status != "done":
        # An unavailable scene without a placeholder is not truthful.
        raise ProtocolValidationError("scene placeholder must be present unless done")
    if placeholder is not None and status == "done":
        raise ProtocolValidationError("a done scene must not carry a placeholder")
    return {
        "archetype": archetype,
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
            "context",
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
        url = _require_str(value, "url", maximum=MAX_SUBJECT_KEY)
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
    # A client never offsets a frame it has no image for: the rectangle is
    # present exactly when the entry carries a media URL.
    if url is not None and face_rect is None:
        raise ProtocolValidationError("a catalog entry with a url carries a face_rect")
    if url is None and face_rect is not None:
        raise ProtocolValidationError("a catalog placeholder carries no face_rect")
    return {
        "subject_key": subject_key,
        "status": status,
        "url": url,
        "aspect_ratio": aspect_ratio,
        "alt": alt,
        "placeholder": placeholder,
        "face_rect": face_rect,
        "context": context,
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
    if value.get("kind") == "asset":
        return None
    return {"kind": value["kind"], "label": value["label"]}


def _serialize_scene(archetype: str | None) -> dict[str, Any]:
    if archetype is None:
        return {
            "archetype": None,
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
    "MAX_ARCHETYPE",
    "MAX_ALT",
    "MAX_CONTEXT_NAME",
    "MAX_CONTEXT_ROLE",
    "MAX_LABEL",
    "MAX_PLACEHOLDER_KIND",
    "MAX_PLACEHOLDER_LABEL",
    "MAX_STATUS",
    "MAX_SUBJECT_KEY",
    "PLACEHOLDER_KINDS",
    "ROLES",
    "_validate_face_rect",
    "_placeholder_for",
    "art_presenter",
    "validate_art",
]
