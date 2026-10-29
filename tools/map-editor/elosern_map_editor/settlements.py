"""Named settlement commands: local maps, nodes, prototypes, roads and bends.

Every handler writes exactly one document,
``content/maps/settlements/<settlement_id>.yaml``:

``create_settlement`` ``{settlement_id, location_id, options}``
    Create a new local map for an existing location (expected presence
    ``absent``). The document starts with no nodes and no roads: the core
    diagnoses it as an unfinished (``empty_graph``) map, never a playable
    one. Nothing is written to the location document; a location's local
    maps are derived from ``location_ref``, and the world frame comes from
    that location's cell plus the ``anchor_room`` node the map later declares,
    so creation authors no coordinate at all.
``set_settlement_field`` ``{settlement_id, field, value}``
    ``options`` (``{map_visual_range, map_mode}``) or ``exit_prototype``
    (``{prototype_parent, typeclass}``); ``null`` removes the optional mapping.
``create_node`` ``{settlement_id, node_id, fields}``
    A new stable node ID with every node field given explicitly. The first
    node of an empty map becomes the ``anchor_room`` of its location
    (``anchor_key`` equal to ``location_ref``), keeping the entered ID,
    position and other fields; later nodes keep their authored prototypes.
``duplicate_node`` ``{settlement_id, node_id, new_node_id, x_m, y_m}``
    A new node with a new stable ID copying the ordinary values (name,
    description, typeclass, scene and prototype). No relationship is copied:
    no road, gate, city gate, interior exterior or district landmark, and an
    ``anchor_room`` copy becomes a ``grid_room`` because the anchor key binds
    the one room of its location.
``set_node_fields`` ``{settlement_id, node_id, fields}``
    Any node field except the position (``prototype_parent`` and
    ``anchor_key`` change together); the core schema decides validity.
``move_nodes`` ``{settlement_id, moves: [{node_id, x_m, y_m}, ...]}``
    One or several nodes of the one document in one operation. IDs, road
    directions and every relationship stay as authored.
``delete_nodes`` ``{settlement_id, node_ids}``
    Refused while a road, gate or city gate of the document, an interior's
    exterior or a district landmark still names a node (nothing cascades),
    and, at execution time, unless the current external reference context
    proves that nothing external refers to it.
``create_road`` ``{settlement_id, source, destination, direction, bends, return}``
    One directed road, or with ``return`` (``{direction, bends}``) the
    reverse road as well: both entries in one operation.
``set_road`` ``{settlement_id, source, destination, value: {source, destination, direction}}``
    Change a road's endpoints or authored direction; bends are kept.
``delete_road`` ``{settlement_id, source, destination}``
``insert_bend`` / ``move_bend`` ``{settlement_id, source, destination, index, point}`` and
``remove_bend`` ``{settlement_id, source, destination, index}``
    Bend points of one road, integer metres ``[x_m, y_m]`` in the local frame.

Positions are integer metres in the settlement's local east/north frame.
Directions are always authored values: no command infers or recomputes a
direction from positions. Lengths are the core's (``road_lengths``).
"""

from __future__ import annotations

import re
from typing import Any

from elosern_map_core import document_from_data, serialize_document, AuthoringError
from elosern_map_core.schema import COMPASS_DIRECTIONS, IDENTIFIER_PATTERN

from .commands import Current, CommandError, DocumentCommand, Envelope, refused_value
from .geography import settlement_document
from .writer import CREATE, Effect

#: Argument sanity bound for integer metres.
MAX_METRES = 10_000_000
#: Bounds of one command's lists (moves, deleted nodes, bends).
MAX_ITEMS = 1_000

_IDENTIFIER = re.compile(IDENTIFIER_PATTERN)
#: Node fields set by ``set_node_fields`` (the position moves separately).
NODE_FIELDS = ("prototype_parent", "key", "desc", "anchor_key", "typeclass", "scene_archetype")
CREATE_NODE_FIELDS = ("x_m", "y_m", *NODE_FIELDS)


# -- argument typing ---------------------------------------------------------
def _invalid(message: str) -> CommandError:
    return CommandError(400, "invalid_command", message)


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value) or len(value) > 128:
        raise _invalid(f"{label} is an authored identifier")
    return value


def _metres(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise _invalid(f"{label} is an integer number of metres")
    if abs(value) > MAX_METRES:
        raise _invalid(f"{label} is outside ±{MAX_METRES} m")
    return value


def _point(value: Any, label: str) -> dict[str, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise _invalid(f"{label} is [x_m, y_m]")
    return {"x_m": _metres(value[0], f"{label}[0]"), "y_m": _metres(value[1], f"{label}[1]")}


def _bends(value: Any, label: str) -> list[dict[str, int]]:
    if not isinstance(value, list) or len(value) > MAX_ITEMS:
        raise _invalid(f"{label} is a list of at most {MAX_ITEMS} [x_m, y_m] points")
    return [_point(item, f"{label}[{index}]") for index, item in enumerate(value)]


def _direction(value: Any, label: str) -> str:
    if value not in COMPASS_DIRECTIONS:
        raise _invalid(f"{label} is one of {', '.join(COMPASS_DIRECTIONS)}")
    return value


def _ids(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > MAX_ITEMS:
        raise _invalid(f"{label} is a non-empty list of at most {MAX_ITEMS} identifiers")
    ids = [_identifier(item, f"{label}[{index}]") for index, item in enumerate(value)]
    if len(set(ids)) != len(ids):
        raise _invalid(f"{label} names a node twice")
    return ids


def _fields(value: Any, allowed: tuple[str, ...], label: str, *, exact: bool = False) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise _invalid(f"{label} is a non-empty object")
    unknown = set(value) - set(allowed)
    if unknown:
        raise _invalid(f"{label} carries only {', '.join(allowed)}")
    if exact and set(value) != set(allowed):
        raise _invalid(f"{label} carries exactly {', '.join(allowed)}")
    for key in ("x_m", "y_m"):
        if key in value:
            _metres(value[key], f"{label}.{key}")
    return dict(value)


def _unknown(kind: str, identity: str, field_path: str) -> CommandError:
    return refused_value(f"unknown_{kind}", f"there is no {kind} {identity!r}", field_path)


def _duplicate(identity: str, field_path: str, code: str = "duplicate_identifier") -> CommandError:
    return refused_value(code, f"{identity!r} already exists", field_path)


def _node(data: dict[str, Any], node_id: str, field_path: str) -> dict[str, Any]:
    node = data["nodes"].get(node_id)
    if node is None:
        raise _unknown("node", node_id, field_path)
    return node


def _road(data: dict[str, Any], source: str, destination: str) -> dict[str, Any]:
    for road in data["roads"]:
        if road["source"] == source and road["destination"] == destination:
            return road
    raise _unknown("road", f"{source}>{destination}", "arguments.source")


def _index(value: Any, length: int, label: str, *, insert: bool = False) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise _invalid(f"{label} is a non-negative integer")
    limit = length if insert else length - 1
    if value > limit:
        raise refused_value("index_out_of_range", f"{label} {value} is outside 0..{limit}", label)
    return value


def _settlement(world: dict[str, Any], settlement_id: str) -> dict[str, Any] | None:
    return next((row for row in world.get("settlements", []) if row["id"] == settlement_id), None)


class _Settlement(DocumentCommand):
    def owner(self, arguments: dict[str, Any]) -> str:
        return settlement_document(arguments["settlement_id"])

    def check(self, world, arguments):
        _identifier(arguments["settlement_id"], "settlement_id")
        self.check_arguments(world, arguments)

    def check_arguments(self, world, arguments) -> None:  # pragma: no cover - overridden
        """Type-check the command's own arguments."""


# -- local maps ----------------------------------------------------------------
def _options(value: Any, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"map_visual_range", "map_mode"}:
        raise _invalid(f"{label} carries exactly map_visual_range and map_mode, or is null")
    return dict(value)


def _exit_prototype(value: Any, label: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"prototype_parent", "typeclass"}:
        raise _invalid(f"{label} carries exactly prototype_parent and typeclass, or is null")
    return dict(value)


class CreateSettlement:
    """Create one new settlement document (the only owner it writes)."""

    name = "create_settlement"
    keys = frozenset({"settlement_id", "location_id", "options"})

    def target(self, world: dict[str, Any], envelope: Envelope) -> str:
        arguments = envelope.arguments
        if set(arguments) != set(self.keys):
            raise _invalid(f"arguments carry exactly {', '.join(sorted(self.keys))}")
        settlement_id = _identifier(arguments["settlement_id"], "settlement_id")
        location_id = _identifier(arguments["location_id"], "location_id")
        _options(arguments["options"], "options")
        owner = settlement_document(settlement_id)
        if envelope.document_id != owner:
            raise CommandError(
                400,
                "cross_document",
                "a command mutates exactly one owning document; this one names another",
                owner=owner,
            )
        if _settlement(world, settlement_id) is not None:
            raise _duplicate(settlement_id, "arguments.settlement_id")
        if not any(row["id"] == location_id for row in world.get("locations", [])):
            raise _unknown("location", location_id, "arguments.location_id")
        return owner

    def effect(
        self, envelope: Envelope, current: Current, world: dict[str, Any]
    ) -> Effect | None:
        if current.text is not None:
            raise CommandError(409, "stale_document", f"{envelope.document_id} already exists")
        arguments = envelope.arguments
        data: dict[str, Any] = {
            "version": 1,
            "kind": "settlement",
            "id": arguments["settlement_id"],
            "location_ref": arguments["location_id"],
        }
        options = _options(arguments["options"], "options")
        if options is not None:
            data["options"] = options
        data.update({"nodes": {}, "roads": [], "wilderness_entry": None, "city_gate": None})
        try:
            text = serialize_document(document_from_data(envelope.document_id, data), None)
        except AuthoringError as error:
            from .commands import _gate_failure  # defined after the handler registry

            raise _gate_failure(error) from error
        return Effect(CREATE, envelope.document_id, text)


class SetSettlementField(_Settlement):
    name = "set_settlement_field"
    keys = frozenset({"settlement_id", "field", "value"})
    _FIELDS = {"options": _options, "exit_prototype": _exit_prototype}

    def check_arguments(self, world, arguments):
        if arguments["field"] not in self._FIELDS:
            raise _invalid(f"field is one of {', '.join(self._FIELDS)}")
        self._FIELDS[arguments["field"]](arguments["value"], "value")

    def mutate(self, data, arguments):
        value = self._FIELDS[arguments["field"]](arguments["value"], "value")
        if value is None:
            data.pop(arguments["field"], None)
            return
        # Keep the document's key order readable: optional mappings sit
        # before the nodes, as the core's own documents declare them.
        if arguments["field"] in data:
            data[arguments["field"]] = value
            return
        reordered: dict[str, Any] = {}
        for key, item in data.items():
            if key == "nodes":
                reordered[arguments["field"]] = value
            reordered[key] = item
        data.clear()
        data.update(reordered)


# -- nodes -----------------------------------------------------------------------
class CreateNode(_Settlement):
    name = "create_node"
    keys = frozenset({"settlement_id", "node_id", "fields"})

    def check_arguments(self, world, arguments):
        _identifier(arguments["node_id"], "node_id")
        _fields(arguments["fields"], CREATE_NODE_FIELDS, "fields", exact=True)

    def mutate(self, data, arguments):
        node_id = arguments["node_id"]
        if node_id in data["nodes"]:
            raise _duplicate(node_id, "arguments.node_id")
        fields = arguments["fields"]
        node = {key: fields[key] for key in CREATE_NODE_FIELDS}
        if not data["nodes"]:
            # The map's first node is its anchor: it is the local metre point
            # that sits on the location cell's centre, so a location drag moves
            # the whole graph without any authored coordinate.
            node["prototype_parent"] = "anchor_room"
            node["anchor_key"] = data["location_ref"]
        data["nodes"][node_id] = node


class DuplicateNode(_Settlement):
    name = "duplicate_node"
    keys = frozenset({"settlement_id", "node_id", "new_node_id", "x_m", "y_m"})

    def check_arguments(self, world, arguments):
        _identifier(arguments["node_id"], "node_id")
        _identifier(arguments["new_node_id"], "new_node_id")
        _metres(arguments["x_m"], "x_m")
        _metres(arguments["y_m"], "y_m")

    def mutate(self, data, arguments):
        original = _node(data, arguments["node_id"], "arguments.node_id")
        new_id = arguments["new_node_id"]
        if new_id in data["nodes"]:
            raise _duplicate(new_id, "arguments.new_node_id")
        anchor = original["prototype_parent"] == "anchor_room"
        data["nodes"][new_id] = {
            "x_m": arguments["x_m"],
            "y_m": arguments["y_m"],
            "prototype_parent": "grid_room" if anchor else original["prototype_parent"],
            "key": original["key"],
            "desc": original["desc"],
            "anchor_key": None,
            "typeclass": original.get("typeclass"),
            "scene_archetype": original.get("scene_archetype"),
        }


class SetNodeFields(_Settlement):
    name = "set_node_fields"
    keys = frozenset({"settlement_id", "node_id", "fields"})

    def check_arguments(self, world, arguments):
        _identifier(arguments["node_id"], "node_id")
        _fields(arguments["fields"], NODE_FIELDS, "fields")

    def mutate(self, data, arguments):
        node = _node(data, arguments["node_id"], "arguments.node_id")
        node.update(arguments["fields"])


class MoveNodes(_Settlement):
    name = "move_nodes"
    keys = frozenset({"settlement_id", "moves"})

    def _moves(self, value: Any) -> list[tuple[str, int, int]]:
        if not isinstance(value, list) or not value or len(value) > MAX_ITEMS:
            raise _invalid(f"moves is a non-empty list of at most {MAX_ITEMS} moves")
        moves = []
        for index, move in enumerate(value):
            if not isinstance(move, dict) or set(move) != {"node_id", "x_m", "y_m"}:
                raise _invalid(f"moves[{index}] carries exactly node_id, x_m and y_m")
            moves.append(
                (
                    _identifier(move["node_id"], f"moves[{index}].node_id"),
                    _metres(move["x_m"], f"moves[{index}].x_m"),
                    _metres(move["y_m"], f"moves[{index}].y_m"),
                )
            )
        if len({node_id for node_id, _, _ in moves}) != len(moves):
            raise _invalid("moves names a node twice")
        return moves

    def check_arguments(self, world, arguments):
        self._moves(arguments["moves"])

    def mutate(self, data, arguments):
        for node_id, x, y in self._moves(arguments["moves"]):
            node = _node(data, node_id, "arguments.moves")
            node["x_m"], node["y_m"] = x, y


def same_document_references(data: dict[str, Any], node_ids: set[str], relative_path: str) -> list[dict[str, Any]]:
    """Roads, gates and the city gate of one settlement that name the nodes."""

    settlement_id = data["id"]
    rows: list[dict[str, Any]] = []

    def row(node_id: str, kind: str, object_id: str, field_path: str) -> None:
        rows.append(
            {
                "target": f"settlement_node:{settlement_id}:{node_id}",
                "kind": kind,
                "source": relative_path,
                "object_id": object_id,
                "field_path": field_path,
            }
        )

    for index, road in enumerate(data["roads"]):
        for end in ("source", "destination"):
            if road[end] in node_ids:
                row(road[end], "road", f"{road['source']}>{road['destination']}", f"roads[{index}].{end}")
    entry = data.get("wilderness_entry") or {}
    for index, gate in enumerate(entry.get("gates", [])):
        if gate["destination_node"] in node_ids:
            row(gate["destination_node"], "wilderness_gate", gate["return_direction"],
                f"wilderness_entry.gates[{index}].destination_node")
    city_gate = data.get("city_gate")
    if city_gate and city_gate["node"] in node_ids:
        row(city_gate["node"], "city_gate", city_gate["node"], "city_gate.node")
    return rows


def other_document_references(world: dict[str, Any], settlement_id: str, node_ids: set[str]) -> list[dict[str, Any]]:
    """Interior exteriors and district landmarks (published projection)."""

    rows = []
    for interior in world.get("interiors", []):
        exterior = interior.get("exterior") or {}
        if exterior.get("settlement") == settlement_id and exterior.get("node") in node_ids:
            rows.append({"target": f"settlement_node:{settlement_id}:{exterior['node']}", "kind": "exterior",
                         "source": interior["relative_path"], "object_id": interior["id"], "field_path": "exterior.node"})
    for district in world.get("districts", []):
        landmark = district.get("landmark") or {}
        if (
            landmark.get("domain") == "settlement_node"
            and landmark.get("map_id") == settlement_id
            and landmark.get("object_id") in node_ids
        ):
            rows.append({"target": f"settlement_node:{settlement_id}:{landmark['object_id']}", "kind": "landmark",
                         "source": district["relative_path"], "object_id": district["id"],
                         "field_path": f"districts.{district['id']}.landmark"})
    return rows


def _refuse(rows: list[dict[str, Any]], settlement_id: str, node_ids: list[str]) -> CommandError:
    named = "; ".join(f"{row['source']} {row['field_path']}" for row in rows[:3])
    return CommandError(
        409,
        "deletion_refused",
        f"map references still name a node this operation removes; remove them first ({named})",
        guard="internal",
        internal_references=rows,
        removed=[f"settlement_node:{settlement_id}:{node_id}" for node_id in node_ids],
    )


class DeleteNodes(_Settlement):
    """Remove nodes of one settlement; never cascades.

    Same-document references (roads, gates, the city gate) refuse here,
    before serialization; references in other documents refuse early from
    the published projection and, authoritatively, on the fresh disk
    baseline in :func:`~elosern_map_editor.commands.validate_candidate`,
    followed by the execution-time external reference context check.
    """

    name = "delete_nodes"
    keys = frozenset({"settlement_id", "node_ids"})

    def check_arguments(self, world, arguments):
        node_ids = _ids(arguments["node_ids"], "node_ids")
        rows = other_document_references(world, arguments["settlement_id"], set(node_ids))
        if rows:
            raise _refuse(rows, arguments["settlement_id"], node_ids)

    def mutate(self, data, arguments):
        node_ids = _ids(arguments["node_ids"], "node_ids")
        for node_id in node_ids:
            _node(data, node_id, "arguments.node_ids")
        rows = same_document_references(data, set(node_ids), settlement_document(arguments["settlement_id"]))
        if rows:
            raise _refuse(rows, arguments["settlement_id"], node_ids)
        for node_id in node_ids:
            del data["nodes"][node_id]


# -- roads and bends ---------------------------------------------------------------
def _check_endpoints(data: dict[str, Any], source: str, destination: str, label: str) -> None:
    _node(data, source, f"arguments.{label}source")
    _node(data, destination, f"arguments.{label}destination")
    if source == destination:
        raise refused_value("self_loop", f"road {source!r} -> {destination!r} is a self-loop", f"arguments.{label}destination")


def _road_entry(source: str, destination: str, direction: str, bends: list[dict[str, int]]) -> dict[str, Any]:
    return {"source": source, "destination": destination, "direction": direction, "bends": bends}


def _has_road(data: dict[str, Any], source: str, destination: str) -> bool:
    return any(road["source"] == source and road["destination"] == destination for road in data["roads"])


class _Road(_Settlement):
    def check_arguments(self, world, arguments):
        _identifier(arguments["source"], "source")
        _identifier(arguments["destination"], "destination")
        self.check_road(arguments)

    def check_road(self, arguments) -> None:
        """Type-check the road command's own arguments."""


def _return(value: Any) -> tuple[str, list[dict[str, int]]] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"direction", "bends"}:
        raise _invalid("return carries exactly direction and bends, or is null")
    return _direction(value["direction"], "return.direction"), _bends(value["bends"], "return.bends")


class CreateRoad(_Road):
    name = "create_road"
    keys = frozenset({"settlement_id", "source", "destination", "direction", "bends", "return"})

    def check_road(self, arguments):
        _direction(arguments["direction"], "direction")
        _bends(arguments["bends"], "bends")
        _return(arguments["return"])

    def mutate(self, data, arguments):
        source, destination = arguments["source"], arguments["destination"]
        _check_endpoints(data, source, destination, "")
        reverse = _return(arguments["return"])
        pairs = [(source, destination)] + ([(destination, source)] if reverse else [])
        for pair in pairs:
            if _has_road(data, *pair):
                raise _duplicate(f"{pair[0]}>{pair[1]}", "arguments.destination", "duplicate_road")
        data["roads"].append(
            _road_entry(source, destination, arguments["direction"], _bends(arguments["bends"], "bends"))
        )
        if reverse:
            data["roads"].append(_road_entry(destination, source, reverse[0], reverse[1]))


class SetRoad(_Road):
    name = "set_road"
    keys = frozenset({"settlement_id", "source", "destination", "value"})

    def _value(self, value: Any) -> dict[str, str]:
        if not isinstance(value, dict) or set(value) != {"source", "destination", "direction"}:
            raise _invalid("value carries exactly source, destination and direction")
        return {
            "source": _identifier(value["source"], "value.source"),
            "destination": _identifier(value["destination"], "value.destination"),
            "direction": _direction(value["direction"], "value.direction"),
        }

    def check_road(self, arguments):
        self._value(arguments["value"])

    def mutate(self, data, arguments):
        road = _road(data, arguments["source"], arguments["destination"])
        value = self._value(arguments["value"])
        _check_endpoints(data, value["source"], value["destination"], "value.")
        moved = (value["source"], value["destination"]) != (road["source"], road["destination"])
        if moved and _has_road(data, value["source"], value["destination"]):
            raise _duplicate(f"{value['source']}>{value['destination']}", "arguments.value", "duplicate_road")
        road.update(value)


class DeleteRoad(_Road):
    name = "delete_road"
    keys = frozenset({"settlement_id", "source", "destination"})

    def mutate(self, data, arguments):
        road = _road(data, arguments["source"], arguments["destination"])
        data["roads"].remove(road)


class InsertBend(_Road):
    name = "insert_bend"
    keys = frozenset({"settlement_id", "source", "destination", "index", "point"})

    def check_road(self, arguments):
        _point(arguments["point"], "point")

    def mutate(self, data, arguments):
        bends = _road(data, arguments["source"], arguments["destination"]).setdefault("bends", [])
        if len(bends) >= MAX_ITEMS:
            raise refused_value("too_many_bends", f"a road holds at most {MAX_ITEMS} bends", "arguments.index")
        bends.insert(_index(arguments["index"], len(bends), "index", insert=True), _point(arguments["point"], "point"))


class MoveBend(_Road):
    name = "move_bend"
    keys = frozenset({"settlement_id", "source", "destination", "index", "point"})

    def check_road(self, arguments):
        _point(arguments["point"], "point")

    def mutate(self, data, arguments):
        bends = _road(data, arguments["source"], arguments["destination"]).setdefault("bends", [])
        bends[_index(arguments["index"], len(bends), "index")] = _point(arguments["point"], "point")


class RemoveBend(_Road):
    name = "remove_bend"
    keys = frozenset({"settlement_id", "source", "destination", "index"})

    def mutate(self, data, arguments):
        bends = _road(data, arguments["source"], arguments["destination"]).setdefault("bends", [])
        del bends[_index(arguments["index"], len(bends), "index")]


SETTLEMENT_HANDLERS = (
    CreateSettlement(),
    SetSettlementField(),
    CreateNode(),
    DuplicateNode(),
    SetNodeFields(),
    MoveNodes(),
    DeleteNodes(),
    CreateRoad(),
    SetRoad(),
    DeleteRoad(),
    InsertBend(),
    MoveBend(),
    RemoveBend(),
)

__all__ = [
    "MAX_ITEMS",
    "NODE_FIELDS",
    "SETTLEMENT_HANDLERS",
    "other_document_references",
    "same_document_references",
]
