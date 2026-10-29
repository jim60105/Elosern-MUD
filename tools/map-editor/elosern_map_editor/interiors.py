"""Named interior commands: documents, rooms, connections and layout arrangement.

Every source handler writes exactly one document,
``content/maps/interiors/<interior_id>.yaml``; the layout arrangement writes
exactly one layout document, ``content/map-editor-layouts/<interior_id>.yaml``.
Interiors are coordinate-free: no command reads or writes a position, a
distance or a physical length in a source document.

``create_interior`` ``{interior_id, room_id, fields}``
    A new standalone interior document (expected presence ``absent``) with
    its first room, no connections, no interior links and no exterior. No
    service, NPC, economy or layout record is written.
``create_room`` ``{interior_id, room_id, fields}``
    A new room with exactly ``name_zh``, ``desc_zh``, ``scene_archetype`` and
    ``art_key``.
``duplicate_room`` ``{interior_id, room_id, new_room_id}``
    A new room under a new stable ID copying the ordinary values (name,
    description, scene, art key). No connection, exterior, interior link or
    landmark is copied, and no incoming reference is retargeted.
``set_room_fields`` ``{interior_id, room_id, fields}``
    Any non-empty subset of the four room fields; the room ID (an existing
    service-room join included) is never renamed.
``delete_room`` ``{interior_id, room_id}``
    Refused while a connection, the exterior or an interior link of the
    document, another interior's link or a district landmark names the room
    (nothing cascades; layout positions are left for the separate cleanup),
    and, at execution time, unless the current external reference context
    proves that nothing external (a service place, a host) refers to it.
``delete_interior`` ``{interior_id}``
    Remove the whole document; every room it declares passes the same
    guards. Its layout document is left for ``remove_interior_layout``.
``create_connection`` ``{interior_id, source, destination, label, return_label}``
    One directed, named connection, or with ``return_label`` the reverse
    connection as well, both in one operation.
``set_connection`` ``{interior_id, source, destination, label, value: {source, destination, label}}``
    Retarget or relabel one connection.
``delete_connection`` ``{interior_id, source, destination, label}``
``arrange_interior_layout`` ``{interior_id, positions: [{room_id, x, y}, ...]}``
    Editor-only layout positions of several rooms in one operation (the
    browser's 自動排列). It never touches a world document.

A new room ID must not be declared by any interior: the game gives a
permanent room one identity across every interior, and the shared core
authoring gate reports ``duplicate_interior_room`` for the candidate, so the
editor refuses the write, undo and redo included.
"""

from __future__ import annotations

import re
from typing import Any

from elosern_map_core import AuthoringError, document_from_data, serialize_document
from elosern_map_core.schema import IDENTIFIER_PATTERN

from .commands import (
    MAX_LAYOUT_COORDINATE,
    CommandError,
    Current,
    DocumentCommand,
    Envelope,
    layout_document_id,
    layout_effect,
    refused_value,
)
from .writer import CREATE, REMOVE, Effect

#: Bound of one command's lists (arranged positions).
MAX_ITEMS = 1_000
#: Connection labels are short exit names.
MAX_LABEL = 200
ROOM_FIELDS = ("name_zh", "desc_zh", "scene_archetype", "art_key")

_IDENTIFIER = re.compile(IDENTIFIER_PATTERN)


def interior_document(interior_id: str) -> str:
    return f"content/maps/interiors/{interior_id}.yaml"


# -- argument typing ---------------------------------------------------------
def _invalid(message: str) -> CommandError:
    return CommandError(400, "invalid_command", message)


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value) or len(value) > 128:
        raise _invalid(f"{label} is an authored identifier")
    return value


def _label(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_LABEL:
        raise _invalid(f"{label} is a non-blank name of at most {MAX_LABEL} characters")
    if value != value.strip():
        raise _invalid(f"{label} has no leading or trailing whitespace")
    return value


def _fields(value: Any, *, exact: bool) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise _invalid("fields is a non-empty object")
    if set(value) - set(ROOM_FIELDS):
        raise _invalid(f"fields carries only {', '.join(ROOM_FIELDS)}")
    if exact and set(value) != set(ROOM_FIELDS):
        raise _invalid(f"fields carries exactly {', '.join(ROOM_FIELDS)}")
    return dict(value)


def _cross_document(owner: str) -> CommandError:
    return CommandError(
        400,
        "cross_document",
        "a command mutates exactly one owning document; this one names another",
        owner=owner,
    )


def _unknown(kind: str, identity: str, field_path: str) -> CommandError:
    return refused_value(f"unknown_{kind}", f"there is no {kind} {identity!r}", field_path)


def _duplicate(identity: str, field_path: str, code: str = "duplicate_identifier") -> CommandError:
    return refused_value(code, f"{identity!r} already exists", field_path)


def _projected(world: dict[str, Any], interior_id: str) -> dict[str, Any] | None:
    return next((row for row in world.get("interiors", []) if row["id"] == interior_id), None)


def _room_taken(world: dict[str, Any], room_id: str) -> str | None:
    """The interior that already declares ``room_id`` (published projection)."""

    for interior in world.get("interiors", []):
        if any(room["id"] == room_id for room in interior["rooms"]):
            return interior["id"]
    return None


def _refuse_taken_room(world: dict[str, Any], room_id: str, field_path: str) -> None:
    owner = _room_taken(world, room_id)
    if owner is not None:
        raise refused_value(
            "duplicate_room_identity",
            f"room {room_id!r} is already declared by interior {owner!r}; a new room needs a new ID",
            field_path,
        )


def _room(data: dict[str, Any], room_id: str, field_path: str) -> dict[str, Any]:
    room = data["rooms"].get(room_id)
    if room is None:
        raise _unknown("room", room_id, field_path)
    return room


def _gate(error: AuthoringError) -> CommandError:
    from .commands import _gate_failure

    return _gate_failure(error)


class _Interior(DocumentCommand):
    def owner(self, arguments: dict[str, Any]) -> str:
        return interior_document(arguments["interior_id"])

    def check(self, world, arguments):
        _identifier(arguments["interior_id"], "interior_id")
        self.check_arguments(world, arguments)

    def check_arguments(self, world, arguments) -> None:  # pragma: no cover - overridden
        """Type-check the command's own arguments."""


# -- documents -------------------------------------------------------------------
class CreateInterior:
    """Create one new standalone interior document (the only owner it writes)."""

    name = "create_interior"
    keys = frozenset({"interior_id", "room_id", "fields"})

    def target(self, world: dict[str, Any], envelope: Envelope) -> str:
        arguments = envelope.arguments
        if set(arguments) != set(self.keys):
            raise _invalid(f"arguments carry exactly {', '.join(sorted(self.keys))}")
        interior_id = _identifier(arguments["interior_id"], "interior_id")
        room_id = _identifier(arguments["room_id"], "room_id")
        _fields(arguments["fields"], exact=True)
        owner = interior_document(interior_id)
        if envelope.document_id != owner:
            raise _cross_document(owner)
        if _projected(world, interior_id) is not None:
            raise _duplicate(interior_id, "arguments.interior_id")
        _refuse_taken_room(world, room_id, "arguments.room_id")
        return owner

    def effect(self, envelope: Envelope, current: Current) -> Effect | None:
        if current.text is not None:
            raise CommandError(409, "stale_document", f"{envelope.document_id} already exists")
        arguments = envelope.arguments
        fields = arguments["fields"]
        data = {
            "version": 1,
            "kind": "interior",
            "id": arguments["interior_id"],
            "rooms": {arguments["room_id"]: {key: fields[key] for key in ROOM_FIELDS}},
            "connections": [],
            "interior_links": [],
            "exterior": None,
        }
        try:
            text = serialize_document(document_from_data(envelope.document_id, data), None)
        except AuthoringError as error:
            raise _gate(error) from error
        return Effect(CREATE, envelope.document_id, text)


class DeleteInterior:
    """Remove one interior document; its rooms pass every deletion guard."""

    name = "delete_interior"
    keys = frozenset({"interior_id"})

    def target(self, world: dict[str, Any], envelope: Envelope) -> str:
        if set(envelope.arguments) != set(self.keys):
            raise _invalid("arguments carry exactly interior_id")
        owner = interior_document(_identifier(envelope.arguments["interior_id"], "interior_id"))
        if envelope.document_id != owner:
            raise _cross_document(owner)
        return owner

    def effect(self, envelope: Envelope, current: Current) -> Effect | None:
        if current.text is None:
            raise CommandError(409, "stale_document", f"{envelope.document_id} does not exist")
        return Effect(REMOVE, envelope.document_id)


# -- rooms -----------------------------------------------------------------------
class CreateRoom(_Interior):
    name = "create_room"
    keys = frozenset({"interior_id", "room_id", "fields"})

    def check_arguments(self, world, arguments):
        room_id = _identifier(arguments["room_id"], "room_id")
        _fields(arguments["fields"], exact=True)
        _refuse_taken_room(world, room_id, "arguments.room_id")

    def mutate(self, data, arguments):
        room_id = arguments["room_id"]
        if room_id in data["rooms"]:
            raise _duplicate(room_id, "arguments.room_id", "duplicate_room_identity")
        fields = arguments["fields"]
        data["rooms"][room_id] = {key: fields[key] for key in ROOM_FIELDS}


class DuplicateRoom(_Interior):
    name = "duplicate_room"
    keys = frozenset({"interior_id", "room_id", "new_room_id"})

    def check_arguments(self, world, arguments):
        _identifier(arguments["room_id"], "room_id")
        new_id = _identifier(arguments["new_room_id"], "new_room_id")
        _refuse_taken_room(world, new_id, "arguments.new_room_id")

    def mutate(self, data, arguments):
        original = _room(data, arguments["room_id"], "arguments.room_id")
        new_id = arguments["new_room_id"]
        if new_id in data["rooms"]:
            raise _duplicate(new_id, "arguments.new_room_id", "duplicate_room_identity")
        data["rooms"][new_id] = {key: original.get(key) for key in ROOM_FIELDS}


class SetRoomFields(_Interior):
    name = "set_room_fields"
    keys = frozenset({"interior_id", "room_id", "fields"})

    def check_arguments(self, world, arguments):
        _identifier(arguments["room_id"], "room_id")
        _fields(arguments["fields"], exact=False)

    def mutate(self, data, arguments):
        _room(data, arguments["room_id"], "arguments.room_id").update(arguments["fields"])


def same_document_references(data: dict[str, Any], room_id: str, relative_path: str) -> list[dict[str, Any]]:
    """Connections, the exterior and interior links of one interior naming the room."""

    interior_id = data["id"]
    target = f"interior_room:{interior_id}:{room_id}"
    rows: list[dict[str, Any]] = []

    def row(kind: str, object_id: str, field_path: str) -> None:
        rows.append({"target": target, "kind": kind, "source": relative_path,
                     "object_id": object_id, "field_path": field_path})

    for index, connection in enumerate(data["connections"]):
        for end in ("source", "destination"):
            if connection[end] == room_id:
                row("connection", f"{connection['source']}>{connection['destination']}",
                    f"connections[{index}].{end}")
    exterior = data.get("exterior")
    if exterior and exterior.get("room") == room_id:
        row("exterior", interior_id, "exterior.room")
    for index, link in enumerate(data.get("interior_links") or []):
        if link["source_room"] == room_id:
            row("interior_link", interior_id, f"interior_links[{index}].source_room")
        elif link["target_interior"] == interior_id and link["target_room"] == room_id:
            row("interior_link", interior_id, f"interior_links[{index}].target_room")
    return rows


def other_document_references(world: dict[str, Any], interior_id: str, room_id: str) -> list[dict[str, Any]]:
    """Other interiors' links and district landmarks naming the room (projection)."""

    target = f"interior_room:{interior_id}:{room_id}"
    rows = []
    for other in world.get("interiors", []):
        if other["id"] == interior_id:
            continue
        for index, link in enumerate(other.get("interior_links") or []):
            if link["target_interior"] == interior_id and link["target_room"] == room_id:
                rows.append({"target": target, "kind": "interior_link", "source": other["relative_path"],
                             "object_id": other["id"], "field_path": f"interior_links[{index}].target_room"})
    for district in world.get("districts", []):
        landmark = district.get("landmark") or {}
        if (
            landmark.get("domain") == "interior_room"
            and landmark.get("map_id") == interior_id
            and landmark.get("object_id") == room_id
        ):
            rows.append({"target": target, "kind": "landmark", "source": district["relative_path"],
                         "object_id": district["id"], "field_path": f"districts.{district['id']}.landmark"})
    return rows


def _refuse(rows: list[dict[str, Any]], interior_id: str, room_id: str) -> CommandError:
    named = "; ".join(f"{row['source']} {row['field_path']}" for row in rows[:3])
    return CommandError(
        409,
        "deletion_refused",
        f"map references still name a room this operation removes; remove them first ({named})",
        guard="internal",
        internal_references=rows,
        removed=[f"interior_room:{interior_id}:{room_id}"],
    )


class DeleteRoom(_Interior):
    """Remove one room; never cascades.

    Same-document references refuse here; references in other documents
    refuse early from the published projection and, authoritatively, on the
    fresh disk baseline in :func:`~elosern_map_editor.commands.validate_candidate`,
    followed by the execution-time external reference context check.
    """

    name = "delete_room"
    keys = frozenset({"interior_id", "room_id"})

    def check_arguments(self, world, arguments):
        room_id = _identifier(arguments["room_id"], "room_id")
        rows = other_document_references(world, arguments["interior_id"], room_id)
        if rows:
            raise _refuse(rows, arguments["interior_id"], room_id)

    def mutate(self, data, arguments):
        room_id = arguments["room_id"]
        _room(data, room_id, "arguments.room_id")
        rows = same_document_references(data, room_id, interior_document(arguments["interior_id"]))
        if rows:
            raise _refuse(rows, arguments["interior_id"], room_id)
        del data["rooms"][room_id]


# -- connections -------------------------------------------------------------------
def _find_connection(data: dict[str, Any], source: str, destination: str, label: str) -> dict[str, Any] | None:
    return next(
        (
            connection
            for connection in data["connections"]
            if (connection["source"], connection["destination"], connection["label"]) == (source, destination, label)
        ),
        None,
    )


def _connection(data: dict[str, Any], source: str, destination: str, label: str) -> dict[str, Any]:
    found = _find_connection(data, source, destination, label)
    if found is None:
        raise _unknown("connection", f"{source}>{destination} {label!r}", "arguments.source")
    return found


def _check_endpoints(data: dict[str, Any], source: str, destination: str, prefix: str) -> None:
    _room(data, source, f"arguments.{prefix}source")
    _room(data, destination, f"arguments.{prefix}destination")
    if source == destination:
        raise refused_value(
            "self_loop", f"connection {source!r} -> {destination!r} returns to its own room",
            f"arguments.{prefix}destination",
        )


class _Connection(_Interior):
    #: ``label`` names a new connection (full name rules) or looks up an
    #: authored one, which may predate the editor's rules and must stay
    #: editable and removable.
    new_label = False

    def check_arguments(self, world, arguments):
        _identifier(arguments["source"], "source")
        _identifier(arguments["destination"], "destination")
        if self.new_label:
            _label(arguments["label"], "label")
        elif not isinstance(arguments["label"], str) or not arguments["label"] or len(arguments["label"]) > 4096:
            raise _invalid("label names an authored connection")
        self.check_connection(arguments)

    def check_connection(self, arguments) -> None:
        """Type-check the connection command's own arguments."""


class CreateConnection(_Connection):
    name = "create_connection"
    new_label = True
    keys = frozenset({"interior_id", "source", "destination", "label", "return_label"})

    def check_connection(self, arguments):
        if arguments["return_label"] is not None:
            _label(arguments["return_label"], "return_label")

    def mutate(self, data, arguments):
        source, destination, label = arguments["source"], arguments["destination"], arguments["label"]
        _check_endpoints(data, source, destination, "")
        entries = [{"source": source, "destination": destination, "label": label}]
        if arguments["return_label"] is not None:
            entries.append({"source": destination, "destination": source, "label": arguments["return_label"]})
        # Both triples are checked before anything changes: one operation or none.
        for entry in entries:
            if _find_connection(data, entry["source"], entry["destination"], entry["label"]) is not None:
                raise _duplicate(
                    f"{entry['source']}>{entry['destination']} {entry['label']!r}", "arguments.label",
                    "duplicate_connection",
                )
        data["connections"].extend(entries)


class SetConnection(_Connection):
    name = "set_connection"
    keys = frozenset({"interior_id", "source", "destination", "label", "value"})

    def _value(self, value: Any) -> dict[str, str]:
        if not isinstance(value, dict) or set(value) != {"source", "destination", "label"}:
            raise _invalid("value carries exactly source, destination and label")
        return {
            "source": _identifier(value["source"], "value.source"),
            "destination": _identifier(value["destination"], "value.destination"),
            "label": _label(value["label"], "value.label"),
        }

    def check_connection(self, arguments):
        self._value(arguments["value"])

    def mutate(self, data, arguments):
        connection = _connection(data, arguments["source"], arguments["destination"], arguments["label"])
        value = self._value(arguments["value"])
        _check_endpoints(data, value["source"], value["destination"], "value.")
        changed = (value["source"], value["destination"], value["label"]) != (
            connection["source"], connection["destination"], connection["label"],
        )
        if changed and _find_connection(data, value["source"], value["destination"], value["label"]) is not None:
            raise _duplicate(
                f"{value['source']}>{value['destination']} {value['label']!r}", "arguments.value",
                "duplicate_connection",
            )
        connection.update(value)


class DeleteConnection(_Connection):
    name = "delete_connection"
    keys = frozenset({"interior_id", "source", "destination", "label"})

    def mutate(self, data, arguments):
        data["connections"].remove(
            _connection(data, arguments["source"], arguments["destination"], arguments["label"])
        )


# -- layout ------------------------------------------------------------------------
class ArrangeInteriorLayout:
    """Several rooms' editor-only layout positions in one layout document."""

    name = "arrange_interior_layout"
    keys = frozenset({"interior_id", "positions"})

    def _positions(self, value: Any) -> dict[str, tuple[int, int]]:
        if not isinstance(value, list) or not value or len(value) > MAX_ITEMS:
            raise _invalid(f"positions is a non-empty list of at most {MAX_ITEMS} positions")
        positions: dict[str, tuple[int, int]] = {}
        for index, item in enumerate(value):
            if not isinstance(item, dict) or set(item) != {"room_id", "x", "y"}:
                raise _invalid(f"positions[{index}] carries exactly room_id, x and y")
            room_id = _identifier(item["room_id"], f"positions[{index}].room_id")
            for axis in ("x", "y"):
                number = item[axis]
                if not isinstance(number, int) or isinstance(number, bool) or abs(number) > MAX_LAYOUT_COORDINATE:
                    raise _invalid(f"positions[{index}].{axis} is an integer within ±{MAX_LAYOUT_COORDINATE}")
            if room_id in positions:
                raise _invalid("positions names a room twice")
            positions[room_id] = (item["x"], item["y"])
        return positions

    def target(self, world: dict[str, Any], envelope: Envelope) -> str:
        arguments = envelope.arguments
        if set(arguments) != set(self.keys):
            raise _invalid("arguments carry exactly interior_id and positions")
        interior_id = _identifier(arguments["interior_id"], "interior_id")
        positions = self._positions(arguments["positions"])
        owner = layout_document_id(interior_id)
        if envelope.document_id != owner:
            raise _cross_document(owner)
        interior = _projected(world, interior_id)
        if interior is None:
            raise _unknown("interior", interior_id, "arguments.interior_id")
        rooms = {room["id"] for room in interior["rooms"]}
        for room_id in positions:
            if room_id not in rooms:
                raise _unknown("room", room_id, "arguments.positions")
        return owner

    def effect(self, envelope: Envelope, current: Current) -> Effect | None:
        return layout_effect(
            envelope.document_id, current, envelope.arguments["interior_id"],
            self._positions(envelope.arguments["positions"]),
        )


INTERIOR_HANDLERS = (
    CreateInterior(),
    DeleteInterior(),
    CreateRoom(),
    DuplicateRoom(),
    SetRoomFields(),
    DeleteRoom(),
    CreateConnection(),
    SetConnection(),
    DeleteConnection(),
    ArrangeInteriorLayout(),
)

__all__ = [
    "INTERIOR_HANDLERS",
    "MAX_ITEMS",
    "ROOM_FIELDS",
    "interior_document",
    "other_document_references",
    "same_document_references",
]
