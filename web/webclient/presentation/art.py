"""Exact schema-version-4 ``art`` panel and presenter (webclient-art-panel).

The presenter composes the frozen art view owned by
``world.rules.art_view`` with the read-only resolution primitives in
``world.art.presenter`` (``describe_scene`` for the scene,
``describe_entity`` for every catalog member) and validates its own output
against the exact bounded schema before returning it to the presentation
registry. The panel is available in ``exploration`` and ``combat`` modes; a
creation-pending shell raises :class:`PanelUnavailableError` so the registry
emits the common unavailable form.

The payload contains exactly ``schema_version``, ``available``, ``kind``, the
current scene and a bounded ``portrait_catalog`` keyed by the opaque IDs of
currently present focusable entities. The scene is exactly ``archetype``,
``label``, ``alt`` and ``artwork``: the canonical descriptor the scene
resolution produced (``world.art.descriptors`` — the logical place identity,
its revision, the independent recorded generation truth, the ordered
candidate/fault facts of the room-aware source chain, the permitted scene
terminal and the retention authorizations), with the archetype the room
renders from and the two bounded display strings the stage needs. Each catalog
entry carries the same canonical descriptor vocabulary plus its bounded display
``context``. Both artwork vocabularies are canonical in this version — the
retired flat scene fields (``url``/``subject_key``/``status``/``aspect_ratio``/
``placeholder``/``stage``) fail the exact-key check instead of being adapted.
It never exposes ``out_path``, the store root, or rejected prompt content.

Catalog admission and real-image eligibility are different facts: membership
is ``world.rules.art_view``'s decision (a currently present focusable entity),
while an entry's own attempts state whether any real image resolves. An
admitted entity with no eligible portrait subject still carries its complete
descriptor — no real candidate, no generated subject key, and the
deterministic attribute-selected alpha terminal — so no surface ever has to
guess imagery from the absence of a field.
"""

from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.artwork import validate_artwork
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
from world.art import descriptors
from world.art.presenter import (
    describe_entity,
    describe_scene,
)
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

ART_SCHEMA_VERSION = 4

# Stable panel-level bounds equal to or below the global protocol table.
MAX_ARCHETYPE = 64
MAX_LABEL = 128
MAX_MEDIA_URL = 256
MAX_ALT = 512
MAX_CONTEXT_NAME = 64
MAX_CONTEXT_ROLE = 16

ROLES = frozenset({ROLE_ALLY, ROLE_DIALOGUE, ROLE_FOE, ROLE_PERSON})

# The bounded display strings of a room whose authored scene metadata cannot be
# honored. The scene's own descriptor states the configuration failure and
# carries the permitted town terminal, so this is a caption fact only — never a
# claim about imagery.
SCENE_UNAVAILABLE_LABEL = "場景"


class ArtPanelError(ProtocolValidationError):
    """The available art payload violates its exact bounded schema."""


def _validate_scene(value: Any) -> dict[str, Any]:
    """Validate one exact scene wrapper: archetype, label, alt and descriptor.

    The scene is exactly ``{archetype, label, alt, artwork}`` — the archetype
    the room renders from (null when the room's authored metadata cannot be
    honored), the two bounded display strings the stage renders outside the
    bitmap, and the complete canonical descriptor the scene resolution
    produced. Every retired flat scene field fails the exact-key check, so no
    old-shape payload can be silently adapted.
    """
    _require_exact_fields(
        value,
        "art scene",
        {"archetype", "label", "alt", "artwork"},
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
    alt = _require_str(value, "alt", maximum=MAX_ALT)
    if not alt.strip():
        raise ProtocolValidationError("scene alt must be non-empty")
    return {
        "archetype": archetype,
        "label": label,
        "alt": alt,
        "artwork": validate_artwork(value["artwork"]),
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
    """Validate one catalog entry: exactly the canonical descriptor plus its context.

    The entry is ``{artwork, context}`` and nothing else. ``artwork`` is the
    complete canonical descriptor validated by the one shared wire validator
    (``web.webclient.presentation.artwork.validate_artwork``), so the art
    catalog and every other descriptor consumer accept byte-identical fact
    shapes; an entry that still carries the retired flat image fields
    (``url``/``face_rect``/``stage``/``origin``/``fallback``/``placeholder``)
    fails the exact-key check rather than being adapted.
    """
    _require_exact_fields(value, "art catalog entry", {"artwork", "context"}, {})
    return {
        "artwork": validate_artwork(value["artwork"]),
        "context": _validate_context(value["context"]),
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


def _serialize_scene(target: Any) -> dict[str, Any]:
    """Serialize one logical scene target as the exact v4 scene wrapper.

    The descriptor is the one the scene resolution produced for the target's
    own logical place identity, archetype and room-art binding; the two display
    strings come from the registered archetype's authored name, so the stage's
    caption is authored content rather than a media fact. A room whose authored
    metadata cannot be honored keeps its explicit archetype-less wrapper: the
    descriptor itself carries the configuration failure and the permitted town
    terminal, so nothing here invents an image or hides the malformed state.
    """
    archetype = target.archetype
    registry_entry = (
        SCENE_ARCHETYPE_REGISTRY.get(archetype) if archetype is not None else None
    )
    label = (
        registry_entry.display_name_zh
        if registry_entry is not None
        else SCENE_UNAVAILABLE_LABEL
    )
    return {
        "archetype": archetype,
        "label": label,
        "alt": label,
        "artwork": describe_scene(target),
    }


def _missing_entity_descriptor(identity: Any) -> dict[str, Any]:
    """The complete descriptor of an admitted identity with no live entity row.

    A catalog member whose database row no longer resolves still occupies its
    admitted key in the committed snapshot, so the position states the truth
    instead of failing the whole panel: its stable lifecycle identity, no
    candidate, no reached fault and no generation claim.
    """
    return descriptors.descriptor(
        subject_id=str(int(identity)),
        generation_subject=None,
        generation_state=None,
        attempts=[],
        terminal_payload=None,
        retention_sources=[],
    )


def _serialize_catalog_entry(entity_view: Any) -> dict[str, Any]:
    """Serialize one admitted entity as its complete descriptor plus display context.

    Admission is ``world.rules.art_view``'s decision and is already made: this
    builder never drops a member for lacking real imagery, never consults an
    eligibility rule of its own, and never enqueues or creates art state. An
    admitted entity with no eligible portrait subject still resolves its own
    complete refusal descriptor (no candidate, no generated subject key, the
    attribute-selected alpha terminal).
    """
    from evennia.objects.models import ObjectDB

    entity = ObjectDB.objects.filter(id=int(entity_view.identity)).first()
    artwork = (
        _missing_entity_descriptor(entity_view.identity)
        if entity is None
        else describe_entity(entity)
    )
    return {
        "artwork": artwork,
        "context": {
            "name": entity_view.display_name,
            "role": entity_view.role,
        },
    }


def _serialize(view: Any) -> dict[str, Any]:
    scene = _serialize_scene(view.scene)
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
    "MAX_MEDIA_URL",
    "ROLES",
    "SCENE_UNAVAILABLE_LABEL",
    "_missing_entity_descriptor",
    "art_presenter",
    "validate_art",
]
