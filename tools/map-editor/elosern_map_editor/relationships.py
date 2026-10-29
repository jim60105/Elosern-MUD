"""Named entrance-relationship commands: gates, the start entry, exteriors and links.

Every relationship is stored once, in its owning document, with both of its
endpoints and every directional label it has; no command writes a mirrored
reverse record, and a two-way meaning is never a second file operation.

Settlement-owned (``content/maps/settlements/<settlement_id>.yaml``):

``create_wilderness_gate`` ``{settlement_id, return_direction, node}``
    One wilderness gate onto a node of this settlement. A settlement without
    a wilderness entry gets a one-cell point entry at offset ``(0,0)`` from its
    location cell, which the continent footprint tool can then grow.
``set_wilderness_gate`` ``{settlement_id, return_direction, value: {return_direction, node}}``
``delete_wilderness_gate`` ``{settlement_id, return_direction}``
    The last gate is refused: an entry keeps at least one gate.
``remove_wilderness_entry`` ``{settlement_id}``
    The explicit removal of the whole entry, its footprint mask included.
``set_city_gate`` ``{settlement_id, value: null | {node, exit_key, exit_aliases}}``
    The one-way entry from the starting room. It has no return field: a
    value naming one is refused, so it can never become two-way.

Interior-owned (``content/maps/interiors/<interior_id>.yaml``):

``set_exterior`` ``{interior_id, value: null | {room, node, doorway_key, doorway_aliases}}``
    The two-way doorway between a room of this interior and a settlement
    node (the game provides the fixed way back out).
``create_interior_link`` ``{interior_id, source, target, label, return_label}``
    A special link from a room of this interior to a room of any interior;
    a ``return_label`` makes it two-way in the same record.
``set_interior_link`` ``{interior_id, source, target, label, value: {source, target, label, return_label}}``
``delete_interior_link`` ``{interior_id, source, target, label}``

Endpoints are always qualified references (``settlement_node:<map>:<node>``,
``interior_room:<map>:<room>``), never a display name or a coordinate. An
endpoint that is malformed, of another domain, on another map than required
or absent is refused with nothing written; the diagnostic names the
relationship, its owning document and the argument field. None of these
commands removes a qualified map object, so none needs the reference index.
"""

from __future__ import annotations

import re
from typing import Any

from elosern_map_core.schema import IDENTIFIER_PATTERN

from .commands import CommandError, refused_value
from .interiors import _Interior, _label, interior_document
from .settlements import _Settlement, _direction, _identifier
from .geography import settlement_document

#: Bound of an alias list.
MAX_ALIASES = 20

_ID = IDENTIFIER_PATTERN.strip("^$")
_PATTERNS = {
    "settlement_node": re.compile(rf"settlement_node:({_ID}):({_ID})"),
    "interior_room": re.compile(rf"interior_room:({_ID}):({_ID})"),
}
_PREFIX = re.compile(r"[a-z_]+:")

WILDERNESS_GATE = "wilderness_gate"
CITY_GATE = "city_gate"
EXTERIOR = "exterior"
INTERIOR_LINK = "interior_link"


def _invalid(message: str) -> CommandError:
    return CommandError(400, "invalid_command", message)


def refuse(code: str, message: str, relationship: str, owner: str, field_path: str) -> CommandError:
    """An endpoint or value refusal that names its relationship; nothing is written."""

    error = refused_value(code, message, field_path)
    for row in error.details["diagnostics"]:
        row.update(relationship=relationship, owner=owner)
    return error


def endpoint(value: Any, domain: str, relationship: str, owner: str, field_path: str) -> tuple[str, str]:
    """``(map_id, object_id)`` of a qualified endpoint of ``domain``."""

    if not isinstance(value, str) or len(value) > 300:
        raise _invalid(f"{field_path} is a qualified reference string")
    match = _PATTERNS[domain].fullmatch(value)
    if match:
        return match.group(1), match.group(2)
    if _PREFIX.match(value) and not value.startswith(f"{domain}:"):
        raise refuse("wrong_domain", f"{value!r} is not a {domain} reference", relationship, owner, field_path)
    raise refuse(
        "invalid_endpoint",
        f"{value!r} is not a qualified {domain} reference ({domain}:<map>:<id>)",
        relationship, owner, field_path,
    )


def _aliases(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_ALIASES:
        raise _invalid(f"{label} is a list of at most {MAX_ALIASES} names")
    names = [_label(item, f"{label}[{index}]") for index, item in enumerate(value)]
    if len(set(names)) != len(names):
        raise _invalid(f"{label} names an alias twice")
    return names


def _exact(value: Any, keys: set[str], label: str, note: str = "") -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        extra = sorted(set(value) - keys) if isinstance(value, dict) else []
        named = f" (unexpected: {', '.join(extra)})" if extra else ""
        raise _invalid(f"{label} carries exactly {', '.join(sorted(keys))}{note}{named}")
    return value


def _projected_nodes(world: dict[str, Any], settlement_id: str) -> set[str] | None:
    row = next((item for item in world.get("settlements", []) if item["id"] == settlement_id), None)
    return None if row is None else {node["id"] for node in row["nodes"]}


def _projected_rooms(world: dict[str, Any], interior_id: str) -> set[str] | None:
    row = next((item for item in world.get("interiors", []) if item["id"] == interior_id), None)
    return None if row is None else {room["id"] for room in row["rooms"]}


# -- settlement-owned ------------------------------------------------------------
class _SettlementEntrance(_Settlement):
    relationship = WILDERNESS_GATE

    def own_node(self, world, arguments, value, field_path) -> str:
        """A node of this settlement, refused when it is elsewhere or absent."""

        settlement_id = arguments["settlement_id"]
        owner = settlement_document(settlement_id)
        map_id, node_id = endpoint(value, "settlement_node", self.relationship, owner, field_path)
        if map_id != settlement_id:
            raise refuse(
                "wrong_map", f"{value!r} is a node of another settlement; this entrance lands in {settlement_id!r}",
                self.relationship, owner, field_path,
            )
        nodes = _projected_nodes(world, settlement_id) if world is not None else None
        if nodes is not None and node_id not in nodes:
            raise refuse("unknown_target", f"there is no node {value!r}", self.relationship, owner, field_path)
        return node_id

    def node_in(self, data, arguments, node_id, field_path) -> str:
        if node_id not in data["nodes"]:
            raise refuse(
                "unknown_target", f"there is no node {node_id!r} in {data['id']!r}",
                self.relationship, settlement_document(arguments["settlement_id"]), field_path,
            )
        return node_id

    def gates(self, data, arguments) -> list[dict[str, Any]]:
        entry = data.get("wilderness_entry")
        if entry is None:
            raise refuse(
                "no_wilderness_entry", "this settlement declares no wilderness entry",
                self.relationship, settlement_document(arguments["settlement_id"]), "arguments.return_direction",
            )
        return entry["gates"]

    def gate(self, data, arguments) -> dict[str, Any]:
        direction = arguments["return_direction"]
        for gate in self.gates(data, arguments):
            if gate["return_direction"] == direction:
                return gate
        raise refuse(
            "unknown_gate", f"there is no wilderness gate {direction!r}",
            self.relationship, settlement_document(arguments["settlement_id"]), "arguments.return_direction",
        )

    def duplicate(self, arguments, direction, field_path) -> CommandError:
        return refuse(
            "duplicate_gate_direction", f"a wilderness gate {direction!r} already exists",
            self.relationship, settlement_document(arguments["settlement_id"]), field_path,
        )


class CreateWildernessGate(_SettlementEntrance):
    name = "create_wilderness_gate"
    keys = frozenset({"settlement_id", "return_direction", "node"})

    def check_arguments(self, world, arguments):
        _direction(arguments["return_direction"], "return_direction")
        self.own_node(world, arguments, arguments["node"], "arguments.node")

    def mutate(self, data, arguments):
        node_id = self.node_in(data, arguments, self.own_node(None, arguments, arguments["node"], "arguments.node"),
                               "arguments.node")
        gate = {"return_direction": arguments["return_direction"], "destination_node": node_id}
        entry = data.get("wilderness_entry")
        if entry is None:
            # A point entry at the settlement's location cell: offset (0,0)
            # means the single hash sits on that cell, so no document authors
            # a geographic coordinate and a later location move carries it.
            data["wilderness_entry"] = {
                "shape": ["#"],
                "offset": {"dx": 0, "dy": 0},
                "gates": [gate],
            }
            return
        if any(row["return_direction"] == gate["return_direction"] for row in entry["gates"]):
            raise self.duplicate(arguments, gate["return_direction"], "arguments.return_direction")
        entry["gates"].append(gate)


class SetWildernessGate(_SettlementEntrance):
    name = "set_wilderness_gate"
    keys = frozenset({"settlement_id", "return_direction", "value"})

    def _value(self, value):
        value = _exact(value, {"return_direction", "node"}, "value")
        _direction(value["return_direction"], "value.return_direction")
        return value

    def check_arguments(self, world, arguments):
        _direction(arguments["return_direction"], "return_direction")
        value = self._value(arguments["value"])
        self.own_node(world, arguments, value["node"], "arguments.value.node")

    def mutate(self, data, arguments):
        gate = self.gate(data, arguments)
        value = self._value(arguments["value"])
        node_id = self.node_in(
            data, arguments, self.own_node(None, arguments, value["node"], "arguments.value.node"),
            "arguments.value.node",
        )
        direction = value["return_direction"]
        if direction != gate["return_direction"] and any(
            row["return_direction"] == direction for row in self.gates(data, arguments)
        ):
            raise self.duplicate(arguments, direction, "arguments.value.return_direction")
        gate.update(return_direction=direction, destination_node=node_id)


class DeleteWildernessGate(_SettlementEntrance):
    name = "delete_wilderness_gate"
    keys = frozenset({"settlement_id", "return_direction"})

    def check_arguments(self, world, arguments):
        _direction(arguments["return_direction"], "return_direction")

    def mutate(self, data, arguments):
        gate = self.gate(data, arguments)
        gates = self.gates(data, arguments)
        if len(gates) == 1:
            raise refuse(
                "last_gate",
                "a wilderness entry keeps at least one gate; retarget this gate or remove the whole "
                "wilderness entry (remove_wilderness_entry)",
                self.relationship, settlement_document(arguments["settlement_id"]), "arguments.return_direction",
            )
        gates.remove(gate)


class RemoveWildernessEntry(_SettlementEntrance):
    name = "remove_wilderness_entry"
    keys = frozenset({"settlement_id"})

    def check_arguments(self, world, arguments):
        return None

    def mutate(self, data, arguments):
        self.gates(data, arguments)
        data["wilderness_entry"] = None


class SetCityGate(_SettlementEntrance):
    name = "set_city_gate"
    keys = frozenset({"settlement_id", "value"})
    relationship = CITY_GATE

    def _value(self, value):
        if value is None:
            return None
        value = _exact(
            value, {"node", "exit_key", "exit_aliases"}, "value",
            "; the starting-room entry is one-way and has no return field",
        )
        _label(value["exit_key"], "value.exit_key")
        _aliases(value["exit_aliases"], "value.exit_aliases")
        return value

    def check_arguments(self, world, arguments):
        value = self._value(arguments["value"])
        if value is not None:
            self.own_node(world, arguments, value["node"], "arguments.value.node")

    def mutate(self, data, arguments):
        value = self._value(arguments["value"])
        if value is None:
            data["city_gate"] = None
            return
        node_id = self.node_in(
            data, arguments, self.own_node(None, arguments, value["node"], "arguments.value.node"),
            "arguments.value.node",
        )
        data["city_gate"] = {
            "node": node_id,
            "exit_key": value["exit_key"],
            "exit_aliases": list(value["exit_aliases"]),
        }


# -- interior-owned --------------------------------------------------------------
class _InteriorEntrance(_Interior):
    relationship = EXTERIOR

    def owner_path(self, arguments) -> str:
        return interior_document(arguments["interior_id"])

    def own_room(self, world, arguments, value, field_path) -> str:
        interior_id = arguments["interior_id"]
        map_id, room_id = endpoint(value, "interior_room", self.relationship, self.owner_path(arguments), field_path)
        if map_id != interior_id:
            raise refuse(
                "wrong_map", f"{value!r} is a room of another interior; this end is in {interior_id!r}",
                self.relationship, self.owner_path(arguments), field_path,
            )
        rooms = _projected_rooms(world, interior_id) if world is not None else None
        if rooms is not None and room_id not in rooms:
            raise refuse("unknown_target", f"there is no room {value!r}", self.relationship,
                         self.owner_path(arguments), field_path)
        return room_id

    def room_in(self, data, arguments, room_id, field_path) -> str:
        if room_id not in data["rooms"]:
            raise refuse("unknown_target", f"there is no room {room_id!r} in {data['id']!r}", self.relationship,
                         self.owner_path(arguments), field_path)
        return room_id


class SetExterior(_InteriorEntrance):
    name = "set_exterior"
    keys = frozenset({"interior_id", "value"})

    def _value(self, value):
        if value is None:
            return None
        value = _exact(value, {"room", "node", "doorway_key", "doorway_aliases"}, "value")
        _label(value["doorway_key"], "value.doorway_key")
        _aliases(value["doorway_aliases"], "value.doorway_aliases")
        return value

    def _node(self, world, arguments, value):
        settlement_id, node_id = endpoint(
            value["node"], "settlement_node", self.relationship, self.owner_path(arguments), "arguments.value.node"
        )
        if world is not None:
            nodes = _projected_nodes(world, settlement_id)
            if nodes is None or node_id not in nodes:
                raise refuse("unknown_target", f"there is no node {value['node']!r}", self.relationship,
                             self.owner_path(arguments), "arguments.value.node")
        return settlement_id, node_id

    def check_arguments(self, world, arguments):
        value = self._value(arguments["value"])
        if value is not None:
            self.own_room(world, arguments, value["room"], "arguments.value.room")
            self._node(world, arguments, value)

    def mutate(self, data, arguments):
        value = self._value(arguments["value"])
        if value is None:
            data["exterior"] = None
            return
        room_id = self.room_in(
            data, arguments, self.own_room(None, arguments, value["room"], "arguments.value.room"),
            "arguments.value.room",
        )
        # The node's existence on the fresh disk is the candidate gate's.
        settlement_id, node_id = self._node(None, arguments, value)
        data["exterior"] = {
            "settlement": settlement_id,
            "node": node_id,
            "room": room_id,
            "doorway_key": value["doorway_key"],
            "doorway_aliases": list(value["doorway_aliases"]),
        }


class _Link(_InteriorEntrance):
    relationship = INTERIOR_LINK

    def target_of(self, world, arguments, value, field_path) -> tuple[str, str]:
        interior_id, room_id = endpoint(value, "interior_room", self.relationship, self.owner_path(arguments),
                                        field_path)
        if world is not None:
            rooms = _projected_rooms(world, interior_id)
            if rooms is None or room_id not in rooms:
                raise refuse("unknown_target", f"there is no room {value!r}", self.relationship,
                             self.owner_path(arguments), field_path)
        return interior_id, room_id

    def link_value(self, world, data, arguments, value, prefix) -> dict[str, Any]:
        """The stored record of a link value (both ends checked)."""

        source = self.own_room(world, arguments, value["source"], f"arguments.{prefix}source")
        target_interior, target_room = self.target_of(world, arguments, value["target"], f"arguments.{prefix}target")
        if data is not None:
            self.room_in(data, arguments, source, f"arguments.{prefix}source")
            if target_interior == data["id"]:
                self.room_in(data, arguments, target_room, f"arguments.{prefix}target")
        if (target_interior, target_room) == (arguments["interior_id"], source):
            raise refuse("self_loop", "a link returns to its own room", self.relationship,
                         self.owner_path(arguments), f"arguments.{prefix}target")
        return {"source_room": source, "target_interior": target_interior, "target_room": target_room}

    def find(self, data, record, label):
        for link in data.get("interior_links") or []:
            if (
                link["source_room"], link["target_interior"], link["target_room"], link["label"]
            ) == (record["source_room"], record["target_interior"], record["target_room"], label):
                return link
        return None

    def duplicate(self, arguments, field_path) -> CommandError:
        return refuse("duplicate_interior_link", "this link already exists", self.relationship,
                      self.owner_path(arguments), field_path)

    def existing_label(self, value) -> str:
        if not isinstance(value, str) or not value or len(value) > 4096:
            raise _invalid("label names an authored link")
        return value


def _return_label(value):
    return None if value is None else _label(value, "return_label")


class CreateInteriorLink(_Link):
    name = "create_interior_link"
    keys = frozenset({"interior_id", "source", "target", "label", "return_label"})

    def check_arguments(self, world, arguments):
        _label(arguments["label"], "label")
        _return_label(arguments["return_label"])
        self.link_value(world, None, arguments, arguments, "")

    def mutate(self, data, arguments):
        record = self.link_value(None, data, arguments, arguments, "")
        if self.find(data, record, arguments["label"]) is not None:
            raise self.duplicate(arguments, "arguments.label")
        record.update(label=arguments["label"], return_label=arguments["return_label"])
        if data.get("interior_links") is None:
            data["interior_links"] = []
        data["interior_links"].append(record)


class SetInteriorLink(_Link):
    name = "set_interior_link"
    keys = frozenset({"interior_id", "source", "target", "label", "value"})

    def _value(self, value):
        value = _exact(value, {"source", "target", "label", "return_label"}, "value")
        _label(value["label"], "value.label")
        if value["return_label"] is not None:
            _label(value["return_label"], "value.return_label")
        return value

    def check_arguments(self, world, arguments):
        self.existing_label(arguments["label"])
        endpoint(arguments["source"], "interior_room", self.relationship, self.owner_path(arguments), "arguments.source")
        endpoint(arguments["target"], "interior_room", self.relationship, self.owner_path(arguments), "arguments.target")
        self.link_value(world, None, arguments, self._value(arguments["value"]), "value.")

    def mutate(self, data, arguments):
        current = self.link_value(None, None, arguments, arguments, "")
        link = self.find(data, current, arguments["label"])
        if link is None:
            raise refuse("unknown_interior_link", "there is no such link", self.relationship,
                         self.owner_path(arguments), "arguments.label")
        value = self._value(arguments["value"])
        record = self.link_value(None, data, arguments, value, "value.")
        found = self.find(data, record, value["label"])
        if found is not None and found is not link:
            raise self.duplicate(arguments, "arguments.value")
        link.update(record, label=value["label"], return_label=value["return_label"])


class DeleteInteriorLink(_Link):
    name = "delete_interior_link"
    keys = frozenset({"interior_id", "source", "target", "label"})

    def check_arguments(self, world, arguments):
        self.existing_label(arguments["label"])
        endpoint(arguments["source"], "interior_room", self.relationship, self.owner_path(arguments), "arguments.source")
        endpoint(arguments["target"], "interior_room", self.relationship, self.owner_path(arguments), "arguments.target")

    def mutate(self, data, arguments):
        current = self.link_value(None, None, arguments, arguments, "")
        link = self.find(data, current, arguments["label"])
        if link is None:
            raise refuse("unknown_interior_link", "there is no such link", self.relationship,
                         self.owner_path(arguments), "arguments.label")
        data["interior_links"].remove(link)


RELATIONSHIP_HANDLERS = (
    CreateWildernessGate(),
    SetWildernessGate(),
    DeleteWildernessGate(),
    RemoveWildernessEntry(),
    SetCityGate(),
    SetExterior(),
    CreateInteriorLink(),
    SetInteriorLink(),
    DeleteInteriorLink(),
)

__all__ = [
    "CITY_GATE",
    "EXTERIOR",
    "INTERIOR_LINK",
    "MAX_ALIASES",
    "RELATIONSHIP_HANDLERS",
    "WILDERNESS_GATE",
    "endpoint",
    "refuse",
]
