"""The eager ``rite`` panel (landmark-rite-panel).

The panel carries the committed facts the browser presents for a landmark rite:
the district and whether it is lit, the guardian, the authored options with
whether each admits a companion, the eligible performers, the experienced
option keys, and the delivery of the last rite committed at this node. Every
value is derived by the settlement rules from the record owner's canonical
node; this module freezes it into one bounded wire object and validates it
identically to the browser mirror
(``web/static/webclient/js/elosern/protocol/panels/rite.js``).

The panel is available exactly when the record owner stands on a rite
landmark's node, lit or unlit. Off it, the presenter asks for the registry's
registered unavailable form. ``options`` and ``performers`` are advisory
presentation data only: the action re-derives every admission itself.

``delivery`` is non-persistent ``ndb`` state bound to the node it was committed
on, so a snapshot replay on that node carries it and any other node does not.
It is lost on a server restart; the player may perform the rite again.
"""

from __future__ import annotations

import re
from typing import Any

from world.observability import log_warn
from web.webclient.presentation.artwork import validate_artwork
from web.webclient.presentation.protocol import (
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError

RITE_SCHEMA_VERSION = 1
RITE_UNAVAILABLE_REASON = ("rite_no_landmark", "這裡沒有可以進行儀式的地標")
#: The non-persistent attribute holding the last committed delivery and its node.
DELIVERY_NDB = "landmark_rite_delivery"
RITE_KIND = "rite"
RITE_DELIVERY_KIND = "formal"

RITE_MAX_BYTES = 32_768
RITE_MAX_DISTRICT_KEY = 64
RITE_MAX_DISTRICT_NAME = 256
RITE_MAX_LANDMARK_NAME = 256
RITE_MAX_GUARDIAN_NAME = 32
RITE_MAX_GUARDIAN_FORM = 200
RITE_MAX_OPTIONS = 3
RITE_MAX_OPTION_LABEL = 32
RITE_MAX_PERFORMERS = 16
RITE_MAX_PERFORMER_NAME = 128
RITE_MAX_SEEN = 3
RITE_MAX_DELIVERY_ID = 128
RITE_MAX_SCENE_ID = 96
RITE_MAX_SCENE_REVISION = 32
RITE_MAX_DELIVERY_NAME = 128
RITE_MAX_LINES = 32
RITE_MAX_LINE_TEXT = 2_000

#: An authored option key: a lowercase head then lowercase/digits/underscores.
_OPTION_KEY = re.compile(r"[a-z][a-z0-9_]{0,31}")
_SPEAKERS = ("actor", "host")

_PANEL_FIELDS = {
    "schema_version",
    "available",
    "kind",
    "district",
    "guardian",
    "art",
    "options",
    "performers",
    "delivery",
    "seen",
}
_DISTRICT_FIELDS = {"key", "name", "landmark", "lit"}
_GUARDIAN_FIELDS = {"name", "form"}
_OPTION_FIELDS = {"key", "label", "companion"}
_PERFORMER_FIELDS = {"member_id", "name", "owner"}
_DELIVERY_FIELDS = {
    "kind",
    "delivery_id",
    "scene_id",
    "scene_revision",
    "actor_name",
    "guardian_name",
    "lines",
}
_NARRATION_FIELDS = {"kind", "text"}
_SPEECH_FIELDS = {"kind", "speaker", "text"}


def _exact(value: Any, name: str, fields: set[str]) -> dict[str, Any]:
    _require_exact_fields(value, name, fields, {})
    return value


def _bounded_ascii(value: Any, field: str, maximum: int) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= maximum
        or not value.isascii()
    ):
        raise ProtocolValidationError(f"{field} must be 1..{maximum} ASCII characters")
    return value


def _nonblank(payload: dict[str, Any], field: str, maximum: int) -> str:
    value = _require_str(payload, field, maximum=maximum)
    if not value.strip():
        raise ProtocolValidationError(f"{field} must be non-blank")
    return value


def _bounded_text(payload: dict[str, Any], field: str, maximum: int) -> str:
    value = _require_str(payload, field, maximum=maximum)
    if not value:
        raise ProtocolValidationError(f"{field} must be 1..{maximum} code points")
    return value


def _validate_lines(lines: Any) -> None:
    if not isinstance(lines, list) or not 1 <= len(lines) <= RITE_MAX_LINES:
        raise ProtocolValidationError(
            f"delivery.lines must be 1..{RITE_MAX_LINES} entries"
        )
    for line in lines:
        if not isinstance(line, dict) or line.get("kind") not in ("narration", "speech"):
            raise ProtocolValidationError("delivery line kind is invalid")
        fields = _NARRATION_FIELDS if line["kind"] == "narration" else _SPEECH_FIELDS
        _require_exact_fields(line, "delivery line", set(fields), {})
        if line["kind"] == "speech" and line.get("speaker") not in _SPEAKERS:
            raise ProtocolValidationError("delivery speech speaker is invalid")
        _bounded_text(line, "text", RITE_MAX_LINE_TEXT)


def _validate_delivery(delivery: Any) -> None:
    _exact(delivery, "delivery", _DELIVERY_FIELDS)
    if delivery["kind"] != RITE_DELIVERY_KIND:
        raise ProtocolValidationError(f"delivery.kind must be {RITE_DELIVERY_KIND}")
    _bounded_ascii(delivery["delivery_id"], "delivery.delivery_id", RITE_MAX_DELIVERY_ID)
    _bounded_ascii(delivery["scene_id"], "delivery.scene_id", RITE_MAX_SCENE_ID)
    _bounded_ascii(
        delivery["scene_revision"], "delivery.scene_revision", RITE_MAX_SCENE_REVISION
    )
    _nonblank(delivery, "actor_name", RITE_MAX_DELIVERY_NAME)
    _nonblank(delivery, "guardian_name", RITE_MAX_DELIVERY_NAME)
    _validate_lines(delivery["lines"])


def _validate_options(options: Any) -> list[str]:
    if not isinstance(options, list) or not 1 <= len(options) <= RITE_MAX_OPTIONS:
        raise ProtocolValidationError(f"options must be 1..{RITE_MAX_OPTIONS} entries")
    keys: list[str] = []
    for option in options:
        row = _exact(option, "option", _OPTION_FIELDS)
        key = row["key"]
        if not isinstance(key, str) or _OPTION_KEY.fullmatch(key) is None:
            raise ProtocolValidationError("option key is invalid")
        if key in keys:
            raise ProtocolValidationError("option keys must be unique")
        keys.append(key)
        _nonblank(row, "label", RITE_MAX_OPTION_LABEL)
        _require_bool(row, "companion")
    return keys


def _validate_performers(performers: Any) -> None:
    if not isinstance(performers, list) or not 1 <= len(performers) <= RITE_MAX_PERFORMERS:
        raise ProtocolValidationError(
            f"performers must be 1..{RITE_MAX_PERFORMERS} entries"
        )
    member_ids: set[int] = set()
    owners = 0
    for index, performer in enumerate(performers):
        row = _exact(performer, "performer", _PERFORMER_FIELDS)
        member_id = row["member_id"]
        if index == 0:
            if member_id is not None:
                raise ProtocolValidationError(
                    "the first performer must have a null member_id"
                )
        else:
            if member_id is None:
                raise ProtocolValidationError(
                    "only the first performer may have a null member_id"
                )
            if (
                isinstance(member_id, bool)
                or not isinstance(member_id, int)
                or not 1 <= member_id <= MAX_SAFE_INTEGER
            ):
                raise ProtocolValidationError(
                    f"member_id must be an integer in 1..{MAX_SAFE_INTEGER}"
                )
            if member_id in member_ids:
                raise ProtocolValidationError("member_id values must be unique")
            member_ids.add(member_id)
        _nonblank(row, "name", RITE_MAX_PERFORMER_NAME)
        if _require_bool(row, "owner"):
            owners += 1
    if owners > 1:
        raise ProtocolValidationError("at most one performer may be the record owner")


def _validate_seen(seen: Any, option_keys: list[str]) -> None:
    if not isinstance(seen, list) or len(seen) > RITE_MAX_SEEN:
        raise ProtocolValidationError(f"seen must be 0..{RITE_MAX_SEEN} entries")
    recorded: list[str] = []
    for key in seen:
        if not isinstance(key, str) or key not in option_keys:
            raise ProtocolValidationError("seen keys must name an option")
        if key in recorded:
            raise ProtocolValidationError("seen keys must be unique")
        recorded.append(key)


def validate_rite(payload: Any) -> dict[str, Any]:
    """Validate the exact available version-1 ``rite`` payload."""
    if not isinstance(payload, dict):
        raise ProtocolValidationError("rite payload must be an object")
    _require_exact_fields(payload, "rite", _PANEL_FIELDS, {})
    version = _require_int(payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER)
    if version != RITE_SCHEMA_VERSION:
        raise ProtocolValidationError(f"schema_version must be {RITE_SCHEMA_VERSION}")
    if payload["available"] is not True:
        raise ProtocolValidationError("available must be True")
    if payload["kind"] != RITE_KIND:
        raise ProtocolValidationError(f"kind must be {RITE_KIND}")

    district = _exact(payload["district"], "district", _DISTRICT_FIELDS)
    _bounded_ascii(district["key"], "district.key", RITE_MAX_DISTRICT_KEY)
    _nonblank(district, "name", RITE_MAX_DISTRICT_NAME)
    _nonblank(district, "landmark", RITE_MAX_LANDMARK_NAME)
    _require_bool(district, "lit")

    guardian = _exact(payload["guardian"], "guardian", _GUARDIAN_FIELDS)
    _nonblank(guardian, "name", RITE_MAX_GUARDIAN_NAME)
    _nonblank(guardian, "form", RITE_MAX_GUARDIAN_FORM)

    if payload["art"] is not None:
        validate_artwork(payload["art"])

    option_keys = _validate_options(payload["options"])
    _validate_performers(payload["performers"])
    _validate_seen(payload["seen"], option_keys)
    if payload["delivery"] is not None:
        _validate_delivery(payload["delivery"])

    if json_byte_size(payload) > RITE_MAX_BYTES:
        raise ProtocolValidationError(f"rite exceeds {RITE_MAX_BYTES} canonical bytes")
    return payload


def _stored_delivery(owner: Any) -> dict[str, Any] | None:
    """The delivery committed at the owner's current node, or ``None``.

    ``owner.ndb`` reads an unset name as ``None`` (Evennia's ``DbHolder`` reads
    through ``AttributeHandler.get``), so a fresh character never raises here.
    """
    from world.rules.map_knowledge import node_id_for

    stored = getattr(owner.ndb, DELIVERY_NDB)
    if not isinstance(stored, dict):
        return None
    node = node_id_for(owner.location)
    if node is None or stored.get("node") != node:
        return None
    candidate = stored.get("delivery")
    return candidate if isinstance(candidate, dict) else None


def rite_presenter(context: Any) -> dict[str, Any]:
    """Render the committed rite site, or the registered unavailable form."""
    from world.rules.landmark_rite_record import (
        LandmarkRiteRecordError,
        seen_option_keys,
    )
    from world.rules.landmark_rites import (
        RiteRefused,
        eligible_performers,
        record_owner_for,
        rite_site_for,
    )
    from world.rules.map_district_lighting import lit_district_keys
    from world.rules.map_knowledge import KnowledgeError

    actor = context.actor
    try:
        owner = record_owner_for(actor)
    except RiteRefused as error:
        raise PanelUnavailableError(str(error)) from error
    site = rite_site_for(owner)
    if site is None:
        raise PanelUnavailableError()

    options = [
        {
            "key": option.key,
            "label": option.label_zh,
            "companion": option.watch_scene is not None,
        }
        for option in site.archetype.options
    ]
    performers = [{"member_id": None, "name": actor.key, "owner": actor is owner}]
    for body in eligible_performers(actor)[1:RITE_MAX_PERFORMERS]:
        performers.append(
            {
                "member_id": int(body.id),
                "name": body.key,
                "owner": body is owner,
            }
        )

    try:
        completed = seen_option_keys(owner, site.district_key)
    except LandmarkRiteRecordError as error:
        log_warn(
            "landmark_rite_record_corrupt",
            exc=error,
            context={"char": owner.pk, "district": site.district_key},
        )
        completed = ()
    seen = [row["key"] for row in options if row["key"] in completed]

    try:
        lit = site.district_key in lit_district_keys(owner)
    except KnowledgeError:  # observability: ignore R2: an unreadable knowledge record degrades to unlit without writing; the map presenters already report that fault
        lit = False

    payload = {
        "schema_version": RITE_SCHEMA_VERSION,
        "available": True,
        "kind": RITE_KIND,
        "district": {
            "key": site.district_key,
            "name": site.district_name,
            "landmark": site.landmark_name,
            "lit": lit,
        },
        "guardian": {
            "name": site.archetype.guardian_name_zh,
            "form": site.archetype.guardian_form_zh,
        },
        "art": None,
        "options": options,
        "performers": performers,
        "delivery": _stored_delivery(owner),
        "seen": seen,
    }
    return validate_rite(payload)


def store_rite_delivery(owner: Any, delivery: dict[str, Any]) -> None:
    """Bind one committed delivery to the owner's current canonical node."""
    from world.rules.map_knowledge import node_id_for

    setattr(
        owner.ndb,
        DELIVERY_NDB,
        {"node": node_id_for(owner.location), "delivery": delivery},
    )


__all__ = [
    "DELIVERY_NDB",
    "RITE_DELIVERY_KIND",
    "RITE_KIND",
    "RITE_MAX_BYTES",
    "RITE_MAX_DELIVERY_ID",
    "RITE_MAX_DELIVERY_NAME",
    "RITE_MAX_DISTRICT_KEY",
    "RITE_MAX_DISTRICT_NAME",
    "RITE_MAX_GUARDIAN_FORM",
    "RITE_MAX_GUARDIAN_NAME",
    "RITE_MAX_LANDMARK_NAME",
    "RITE_MAX_LINES",
    "RITE_MAX_LINE_TEXT",
    "RITE_MAX_OPTION_LABEL",
    "RITE_MAX_OPTIONS",
    "RITE_MAX_PERFORMER_NAME",
    "RITE_MAX_PERFORMERS",
    "RITE_MAX_SCENE_ID",
    "RITE_MAX_SCENE_REVISION",
    "RITE_MAX_SEEN",
    "RITE_SCHEMA_VERSION",
    "RITE_UNAVAILABLE_REASON",
    "rite_presenter",
    "store_rite_delivery",
    "validate_rite",
]