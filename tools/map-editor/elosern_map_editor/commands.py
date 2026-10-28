"""Named document commands: envelope, handlers and candidate validation.

``POST /api/commands/<name>`` carries exactly::

    {"session_generation": str, "snapshot_revision": int, "segment": str,
     "document_id": str, "expected_document_fingerprint": str | "absent",
     "arguments": {...}}

A named handler validates its typed arguments, derives the one canonical
document it owns (the client's ``document_id`` must equal it) and returns one
internal create/replace/remove :class:`~elosern_map_editor.writer.Effect`.
Clients can never name a file operation. Before any effect reaches the writer,
:func:`validate_candidate` builds the complete candidate world from a fresh
disk read and runs its authoring gate, and every object-removing effect
rechecks the current external reference context at execution time.

Handlers in this slice:

``move_interior_layout`` ``{interior_id, room_id, x, y}``
    Set one room's editor-only layout position in
    ``content/map-editor-layouts/<interior_id>.yaml``; the first move creates
    that document (only the moved room is written; the others keep their list
    fallback). Comments of an existing document are retained. World
    coordinates, distance and the game snapshot are never touched.
``remove_interior_layout`` ``{interior_id}``
    The explicit layout-cleanup command (service-only in this slice). It never
    cascades from, or into, a world document.

World-document handlers derive from :class:`DocumentCommand` (or, for a
document creation, implement ``target``/``effect`` directly): continent
geometry, locations, districts and the settlement-owned footprint and
binding live in :mod:`elosern_map_editor.geography`; local maps, nodes,
prototypes, roads and bends in :mod:`elosern_map_editor.settlements`;
interior documents, rooms, connections and the multi-room layout
arrangement in :mod:`elosern_map_editor.interiors`; the entrance
relationships (wilderness gates, the starting-room entry, interior exteriors
and interior links) in :mod:`elosern_map_editor.relationships`.

``undo`` and ``redo`` (``arguments: {}``) apply the inverse/forward effect of
the current segment's top history entry through the same path.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from elosern_map_core import (
    AuthoringError,
    canonical_target_key,
    document_from_data,
    interior_room_ref,
    load_authoring_world,
    location_ref,
    make_source_document,
    parse_document,
    serialize_document,
    settlement_node_ref,
)
from elosern_map_core.schema import IDENTIFIER_PATTERN
from elosern_map_core.sources import LAYOUT_DIRECTORY, is_world_source

from .config import Limits
from .confinement import ConfinedWorkspace
from .snapshot import read_external_context, read_sources, thaw
from .writer import ABSENT, CREATE, REMOVE, REPLACE, Effect

ENVELOPE_KEYS = frozenset(
    {
        "session_generation",
        "snapshot_revision",
        "segment",
        "document_id",
        "expected_document_fingerprint",
        "arguments",
    }
)
HISTORY_COMMANDS = ("undo", "redo")
#: Editor-only layout grid bound (positions are grid steps, not metres).
MAX_LAYOUT_COORDINATE = 100_000
_HEX = frozenset("0123456789abcdef")
_IDENTIFIER = re.compile(IDENTIFIER_PATTERN)


class CommandError(Exception):
    """A rejected command; nothing was written and history is unchanged."""

    def __init__(self, status: int, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.details = details

    def body(self) -> bytes:
        return json.dumps(
            {"error": {"code": self.code, "message": str(self), **self.details}}, ensure_ascii=False
        ).encode("utf-8")


def _invalid(message: str) -> CommandError:
    return CommandError(400, "invalid_command", message)


@dataclass(frozen=True, slots=True)
class Envelope:
    session_generation: str
    snapshot_revision: int
    segment: str
    document_id: str
    expected: str
    arguments: dict[str, Any]


def _is_fingerprint(value: object) -> bool:
    return value == ABSENT or (
        isinstance(value, str) and len(value) == 64 and set(value) <= _HEX
    )


def parse_envelope(raw: bytes) -> Envelope:
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise CommandError(400, "invalid_body", "the body is not JSON") from None
    if not isinstance(body, dict) or set(body) != ENVELOPE_KEYS:
        raise CommandError(
            400, "invalid_body", f"the body carries exactly {', '.join(sorted(ENVELOPE_KEYS))}"
        )
    revision = body["snapshot_revision"]
    if not isinstance(revision, int) or isinstance(revision, bool):
        raise CommandError(400, "invalid_body", "snapshot_revision is an integer")
    for key in ("session_generation", "segment", "document_id"):
        if not isinstance(body[key], str) or not body[key] or len(body[key]) > 256:
            raise CommandError(400, "invalid_body", f"{key} is a non-empty string")
    if not _is_fingerprint(body["expected_document_fingerprint"]):
        raise CommandError(
            400, "invalid_body", "expected_document_fingerprint is a content hash or 'absent'"
        )
    if not isinstance(body["arguments"], dict):
        raise CommandError(400, "invalid_body", "arguments is an object")
    return Envelope(
        session_generation=body["session_generation"],
        snapshot_revision=revision,
        segment=body["segment"],
        document_id=body["document_id"],
        expected=body["expected_document_fingerprint"],
        arguments=body["arguments"],
    )


# -- argument helpers ------------------------------------------------------
def _exact_keys(arguments: dict[str, Any], keys: set[str]) -> None:
    if set(arguments) != keys:
        raise _invalid(f"arguments carry exactly {', '.join(sorted(keys))}")


def _string(arguments: dict[str, Any], key: str) -> str:
    value = arguments[key]
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise _invalid(f"{key} is an authored identifier")
    return value


def _integer(arguments: dict[str, Any], key: str) -> int:
    value = arguments[key]
    # bool is an int subclass and 1.0 is not an integer value here.
    if not isinstance(value, int) or isinstance(value, bool):
        raise _invalid(f"{key} is an integer")
    if abs(value) > MAX_LAYOUT_COORDINATE:
        raise _invalid(f"{key} is outside ±{MAX_LAYOUT_COORDINATE}")
    return value


def layout_document_id(interior_id: str) -> str:
    return f"{LAYOUT_DIRECTORY}/{interior_id}.yaml"


def _interior(world: dict[str, Any], interior_id: str) -> dict[str, Any]:
    for interior in world["interiors"]:
        if interior["id"] == interior_id:
            return interior
    raise CommandError(
        422,
        "validation_failed",
        f"interior {interior_id!r} does not exist",
        diagnostics=[{"code": "unknown_interior", "field_path": "arguments.interior_id"}],
    )


def _owner_of_room(world: dict[str, Any], room_id: str) -> list[str]:
    return [
        interior["id"]
        for interior in world["interiors"]
        if any(room["id"] == room_id for room in interior["rooms"])
    ]


def _check_owner(document_id: str, interior_id: str) -> str:
    owner = layout_document_id(interior_id)
    if document_id != owner:
        raise CommandError(
            400,
            "cross_document",
            "a command mutates exactly one owning document; this one names another",
            owner=owner,
        )
    return owner


# -- handlers --------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Current:
    """The target's disk state the handler builds on (already guard-checked)."""

    fingerprint: str
    text: str | None


class MoveInteriorLayout:
    name = "move_interior_layout"

    def target(self, world: dict[str, Any], envelope: Envelope) -> str:
        arguments = envelope.arguments
        _exact_keys(arguments, {"interior_id", "room_id", "x", "y"})
        interior_id = _string(arguments, "interior_id")
        room_id = _string(arguments, "room_id")
        _integer(arguments, "x")
        _integer(arguments, "y")
        owner = _check_owner(envelope.document_id, interior_id)
        interior = _interior(world, interior_id)
        if not any(room["id"] == room_id for room in interior["rooms"]):
            others = [other for other in _owner_of_room(world, room_id) if other != interior_id]
            if others:
                raise CommandError(
                    400,
                    "cross_document",
                    f"room {room_id!r} belongs to another interior's layout",
                    owner=layout_document_id(others[0]),
                )
            raise CommandError(
                422,
                "validation_failed",
                f"room {room_id!r} is not a room of {interior_id!r}",
                diagnostics=[{"code": "unknown_room", "field_path": "arguments.room_id"}],
            )
        return owner

    def effect(self, envelope: Envelope, current: Current) -> Effect | None:
        arguments = envelope.arguments
        return layout_effect(
            envelope.document_id, current, arguments["interior_id"],
            {arguments["room_id"]: (arguments["x"], arguments["y"])},
        )


def layout_effect(
    document_id: str, current: Current, interior_id: str, positions: dict[str, tuple[int, int]]
) -> Effect | None:
    """Set editor-only positions of rooms in one layout document.

    Creates the absent document with only these rooms, or merges them into
    the existing one keeping its comments and every other position. ``None``
    when every position is already stored.
    """

    wanted = {room_id: {"x": x, "y": y} for room_id, (x, y) in positions.items()}
    if current.text is None:
        data = {"version": 1, "kind": "layout", "id": interior_id, "positions": wanted}
        retained = None
    else:
        try:
            parsed = parse_document(document_id, current.text)
        except AuthoringError as error:
            raise _gate_failure(error) from error
        data = thaw(parsed.document.data)
        if all(data["positions"].get(room_id) == position for room_id, position in wanted.items()):
            return None
        data["positions"].update(wanted)
        retained = parsed.round_trip
    try:
        text = serialize_document(document_from_data(document_id, data), retained)
    except AuthoringError as error:
        raise _gate_failure(error) from error
    return Effect(REPLACE if current.text is not None else CREATE, document_id, text)


class RemoveInteriorLayout:
    name = "remove_interior_layout"

    def target(self, world: dict[str, Any], envelope: Envelope) -> str:
        _exact_keys(envelope.arguments, {"interior_id"})
        interior_id = _string(envelope.arguments, "interior_id")
        # The interior need not exist: cleaning up an orphaned layout is allowed.
        return _check_owner(envelope.document_id, interior_id)

    def effect(self, envelope: Envelope, current: Current) -> Effect | None:
        if current.text is None:
            raise CommandError(409, "stale_document", "there is no layout document to remove")
        return Effect(REMOVE, envelope.document_id)


class DocumentCommand:
    """One named command that replaces one existing world document.

    Subclasses name ``keys`` (the exact argument keys), derive their ``owner``
    document from the arguments, type-check the arguments in ``check`` (a
    friendly early refusal may consult the published projection) and change
    the thawed document data in ``mutate``. The complete candidate document
    is then validated by the core schema while serializing (comments of
    retained objects are kept), and the complete candidate world by the
    authoring gate in :func:`validate_candidate`.
    """

    name = ""
    keys: frozenset[str] = frozenset()

    def owner(self, arguments: dict[str, Any]) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    def check(self, world: dict[str, Any], arguments: dict[str, Any]) -> None:
        """Type-check the arguments (raise :class:`CommandError`)."""

    def mutate(self, data: dict[str, Any], arguments: dict[str, Any]) -> None:  # pragma: no cover
        raise NotImplementedError

    def target(self, world: dict[str, Any], envelope: Envelope) -> str:
        _exact_keys(envelope.arguments, set(self.keys))
        self.check(world, envelope.arguments)
        owner = self.owner(envelope.arguments)
        if envelope.document_id != owner:
            raise CommandError(
                400,
                "cross_document",
                "a command mutates exactly one owning document; this one names another",
                owner=owner,
            )
        return owner

    def effect(self, envelope: Envelope, current: Current) -> Effect | None:
        if current.text is None:
            raise CommandError(409, "stale_document", f"{envelope.document_id} does not exist")
        try:
            parsed = parse_document(envelope.document_id, current.text)
        except AuthoringError as error:
            raise _gate_failure(error) from error
        data = thaw(parsed.document.data)
        baseline = deepcopy(data)
        self.mutate(data, envelope.arguments)
        if data == baseline:
            return None
        try:
            text = serialize_document(document_from_data(envelope.document_id, data), parsed.round_trip)
        except AuthoringError as error:
            raise _gate_failure(error) from error
        return Effect(REPLACE, envelope.document_id, text)


def refused_value(code: str, message: str, field_path: str) -> CommandError:
    """A domain refusal of one command value; nothing is written."""

    return CommandError(
        422,
        "validation_failed",
        message,
        diagnostics=[{"code": code, "category": "structure", "message": message, "field_path": field_path}],
    )


def _registry():
    from .geography import GEOGRAPHY_HANDLERS
    from .interiors import INTERIOR_HANDLERS
    from .relationships import RELATIONSHIP_HANDLERS
    from .settlements import SETTLEMENT_HANDLERS

    handlers = (
        MoveInteriorLayout(),
        RemoveInteriorLayout(),
        *GEOGRAPHY_HANDLERS,
        *SETTLEMENT_HANDLERS,
        *INTERIOR_HANDLERS,
        *RELATIONSHIP_HANDLERS,
    )
    return {handler.name: handler for handler in handlers}


HANDLERS = _registry()
COMMANDS = frozenset(HANDLERS) | frozenset(HISTORY_COMMANDS)


# -- candidate validation --------------------------------------------------
#: Authored fields that hold one entrance relationship, and its kind.
_RELATIONSHIP_FIELDS = (
    ("wilderness_entry.gates", "wilderness_gate"),
    ("city_gate", "city_gate"),
    ("exterior", "exterior"),
    ("interior_links", "interior_link"),
)


def relationship_of(field_path: str) -> str | None:
    """The entrance relationship kind an authored field path belongs to."""

    for prefix, kind in _RELATIONSHIP_FIELDS:
        if field_path == prefix or field_path.startswith((f"{prefix}.", f"{prefix}[")):
            return kind
    return None


def _gate_failure(error: AuthoringError) -> CommandError:
    rows = []
    for item in error.diagnostics:
        row = item.as_dict()
        # A gate failure on an entrance field names its relationship and
        # owning document, exactly like the handlers' own endpoint refusals.
        kind = relationship_of(row.get("field_path") or "")
        if kind is not None:
            row.update(relationship=kind, owner=row.get("relative_path"))
        rows.append(row)
    return CommandError(
        422,
        "validation_failed",
        "the candidate does not pass the authoring gate",
        diagnostics=rows,
    )


def _object_keys(world) -> set[str]:
    index = world.reference_index
    keys: set[str] = set()
    for map_id, nodes in index.settlement_nodes.items():
        keys.update(canonical_target_key(settlement_node_ref(map_id, node)) for node in nodes)
    for interior_id, rooms in index.interior_rooms.items():
        keys.update(canonical_target_key(interior_room_ref(interior_id, room)) for room in rooms)
    keys.update(canonical_target_key(location_ref(location)) for location in index.locations)
    return keys


def removed_objects(workspace: ConfinedWorkspace, limits: Limits, effect: Effect) -> tuple[str, ...]:
    """Validate the complete candidate world; return the map objects it removes.

    Raises :class:`CommandError` when the current workspace or the candidate
    does not pass the authoring gate.
    """

    sources, refused, _ = read_sources(workspace, limits, workspace.discover_world())
    if refused:
        raise CommandError(
            422,
            "validation_failed",
            "the current workspace cannot be read; reread before writing",
            diagnostics=[item.as_dict() for item in refused],
        )
    try:
        baseline = load_authoring_world(sources)
    except AuthoringError as error:
        raise _gate_failure(error) from error
    path = effect.relative_path
    if not is_world_source(path):
        # A layout document is editor-only: parse it and require its interior.
        if effect.text is not None:
            try:
                parsed = parse_document(path, effect.text)
            except AuthoringError as error:
                raise _gate_failure(error) from error
            if parsed.identity not in baseline.interiors:
                raise CommandError(
                    422,
                    "validation_failed",
                    f"interior {parsed.identity!r} does not exist",
                    diagnostics=[{"code": "unknown_interior", "relative_path": path}],
                )
        return ()
    check_internal_references(baseline, _document_removals(baseline, path, effect.text))
    candidate_sources = [source for source in sources if source.relative_path != path]
    if effect.text is not None:
        candidate_sources.append(make_source_document(path, effect.text))
    try:
        candidate = load_authoring_world(candidate_sources)
    except AuthoringError as error:
        raise _gate_failure(error) from error
    check_room_identities(baseline, candidate)
    check_doorways(baseline, candidate)
    return tuple(sorted(_object_keys(baseline) - _object_keys(candidate)))


def _room_owners(world) -> dict[str, list[str]]:
    owners: dict[str, list[str]] = {}
    for interior_id, interior in sorted(world.interiors.items()):
        for room_id in interior.rooms:
            owners.setdefault(room_id, []).append(interior_id)
    return owners


def check_room_identities(baseline, candidate) -> None:
    """Refuse a candidate that newly declares one room ID in two interiors.

    The game's interior snapshot gives a permanent room one identity across
    every interior; the core authoring gate does not check it, so the editor
    mirrors that rule for every world-source effect (commands, undo and redo)
    on the fresh disk baseline. A duplicate the baseline already holds does
    not block unrelated edits; only one this candidate introduces refuses.
    """

    before = _room_owners(baseline)
    rows = [
        {"code": "duplicate_room_identity", "category": "structure", "object_id": room_id,
         "message": f"room {room_id!r} would be declared by interiors {', '.join(owners)}",
         "field_path": f"rooms.{room_id}"}
        for room_id, owners in sorted(_room_owners(candidate).items())
        # A duplicate is new when the room gains an owner beyond a baseline
        # that already shared it (or had one owner, or none).
        if len(owners) > 1 and not set(owners) <= set(before.get(room_id, ()))
    ]
    if rows:
        raise CommandError(
            422,
            "validation_failed",
            "a permanent room has one identity across every interior",
            diagnostics=rows,
        )


def _doorway_owners(world) -> dict[tuple[str, str, str], list[str]]:
    owners: dict[tuple[str, str, str], list[str]] = {}
    for interior_id, interior in sorted(world.interiors.items()):
        exterior = interior.exterior
        if exterior is not None:
            owners.setdefault((exterior.settlement, exterior.node, exterior.doorway_key), []).append(interior_id)
    return owners


def check_doorways(baseline, candidate) -> None:
    """Refuse a candidate that newly gives two interiors one doorway.

    The game refuses two interiors that open onto the same settlement node
    under the same doorway name (the exact (settlement, node, doorway_key)
    tuple, as the game compares it; aliases are not compared); the core gate does
    not check it, so the editor mirrors that rule for every world-source
    effect on the fresh disk baseline. A duplicate the baseline already holds
    does not block unrelated edits; only one this candidate introduces
    refuses.
    """

    before = _doorway_owners(baseline)
    rows = [
        {"code": "duplicate_doorway", "category": "structure", "relationship": "exterior",
         "object_id": ",".join(owners), "field_path": "exterior.doorway_key",
         "message": f"interiors {', '.join(owners)} would open onto {settlement}:{node} "
                    f"under the same doorway {doorway!r}"}
        for (settlement, node, doorway), owners in sorted(_doorway_owners(candidate).items())
        if len(owners) > 1 and not set(owners) <= set(before.get((settlement, node, doorway), ()))
    ]
    if rows:
        raise CommandError(
            422,
            "validation_failed",
            "two interiors on one settlement node need different doorway names",
            diagnostics=rows,
        )


# Keep _document_keys and internal_references in step: every reference kind
# scanned below must name an object kind this function can report removed.
def _document_keys(document) -> set[str]:
    kind = getattr(document, "kind", None)
    if kind == "locations":
        return {canonical_target_key(location_ref(key)) for key in document.locations}
    if kind == "settlement":
        return {canonical_target_key(settlement_node_ref(document.identity, key)) for key in document.nodes}
    if kind == "interior":
        return {canonical_target_key(interior_room_ref(document.identity, key)) for key in document.rooms}
    return set()


def _document_removals(baseline, path: str, text: str | None) -> set[str]:
    """Map objects of ``path`` that the candidate text no longer declares.

    Computed from that one document, so it is known even when the candidate
    world would not load because something still refers to a removed object.
    """

    before = next((document for document in baseline.documents if document.relative_path == path), None)
    if before is None:
        return set()
    if text is None:
        return _document_keys(before)
    try:
        after = parse_document(path, text).document
    except AuthoringError as error:
        raise _gate_failure(error) from error
    return _document_keys(before) - _document_keys(after)


def _landmark_key(landmark) -> str | None:
    if landmark.domain == "location" and landmark.object_id:
        return canonical_target_key(location_ref(landmark.object_id))
    if landmark.domain == "settlement_node" and landmark.map_id and landmark.object_id:
        return canonical_target_key(settlement_node_ref(landmark.map_id, landmark.object_id))
    if landmark.domain == "interior_room" and landmark.map_id and landmark.object_id:
        return canonical_target_key(interior_room_ref(landmark.map_id, landmark.object_id))
    return None


def internal_references(world, removed: set[str]) -> list[dict[str, Any]]:
    """Map-internal references in other documents to the removed objects."""

    rows: list[dict[str, Any]] = []
    if not removed:
        return rows
    for settlement_id, settlement in sorted(world.settlements.items()):
        key = canonical_target_key(location_ref(settlement.location_ref))
        if key in removed:
            rows.append({"target": key, "kind": "location_ref", "source": settlement.relative_path,
                         "object_id": settlement_id, "field_path": "location_ref"})
        for node_id, node in settlement.nodes.items():
            if node.anchor_key is None:
                continue
            key = canonical_target_key(location_ref(node.anchor_key))
            if key in removed:
                rows.append({"target": key, "kind": "anchor_key", "source": settlement.relative_path,
                             "object_id": node_id, "field_path": f"nodes.{node_id}.anchor_key"})
    for interior_id, interior in sorted(world.interiors.items()):
        exterior = interior.exterior
        if exterior is None:
            continue
        key = canonical_target_key(settlement_node_ref(exterior.settlement, exterior.node))
        if key in removed:
            rows.append({"target": key, "kind": "exterior", "source": interior.relative_path,
                         "object_id": interior_id, "field_path": "exterior.node"})
    for interior_id, interior in sorted(world.interiors.items()):
        for index, link in enumerate(interior.interior_links):
            if link.target_interior == interior_id:
                continue  # a same-document link is the removing handler's concern
            key = canonical_target_key(interior_room_ref(link.target_interior, link.target_room))
            if key in removed:
                rows.append({"target": key, "kind": "interior_link", "source": interior.relative_path,
                             "object_id": interior_id, "field_path": f"interior_links[{index}].target_room"})
    for district_id, district in world.districts.districts.items():
        key = _landmark_key(district.landmark)
        if key in removed:
            rows.append({"target": key, "kind": "landmark", "source": world.districts.relative_path,
                         "object_id": district_id, "field_path": f"districts.{district_id}.landmark"})
    return rows


def check_internal_references(world, removed: set[str]) -> None:
    """Refuse a removal that would leave a map reference dangling (no cascade)."""

    rows = internal_references(world, removed)
    if rows:
        named = "; ".join(f"{row['source']} {row['field_path']}" for row in rows[:3])
        raise CommandError(
            409,
            "deletion_refused",
            f"other map documents still refer to an object this operation removes ({named})",
            guard="internal",
            internal_references=rows,
            removed=sorted(removed),
        )


def check_removal(workspace: ConfinedWorkspace, limits: Limits, removed: tuple[str, ...]) -> None:
    """Execution-time external-reference guard for every removed map object."""

    if not removed:
        return
    context = read_external_context(workspace, limits)
    if context.document is None or context.freshness is None:
        raise CommandError(
            409,
            "deletion_refused",
            "the external reference index is unavailable, so references cannot be checked",
            guard="unavailable",
            reasons=list(context.status.get("reasons", [])),
            removed=list(removed),
        )
    refusals = []
    for target in removed:
        decision = context.document.check_deletion_safety(target, context.freshness)
        if not decision.allowed:
            refusals.append(
                {
                    "target": target,
                    "status": decision.status,
                    "reasons": list(decision.reasons),
                    "incoming_references": [ref.to_dict() for ref in decision.incoming_references],
                }
            )
    if refusals:
        raise CommandError(
            409,
            "deletion_refused",
            "an object this operation removes cannot be removed now",
            refusals=refusals,
            removed=list(removed),
        )


def validate_candidate(workspace: ConfinedWorkspace, limits: Limits, effect: Effect) -> None:
    check_removal(workspace, limits, removed_objects(workspace, limits, effect))


__all__ = [
    "COMMANDS",
    "CommandError",
    "Current",
    "DocumentCommand",
    "Envelope",
    "HANDLERS",
    "HISTORY_COMMANDS",
    "MAX_LAYOUT_COORDINATE",
    "check_doorways",
    "check_room_identities",
    "layout_document_id",
    "internal_references",
    "parse_envelope",
    "refused_value",
    "relationship_of",
    "removed_objects",
    "validate_candidate",
]
