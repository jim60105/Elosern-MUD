"""The coordinate-free instance/interior layer adapter (design D8).

Builds the room graph from real Exits: the current room, an instance origin
node, one-hop destinations (unvisited ones labelled 未探索 with the room name
withheld), and bounded remembered rooms whose objects still resolve (D4).
"""

from typing import Any

from web.webclient.presentation.local_map.builder import (
    _exit_ref,
    _GraphBuilder,
    _known_node_id,
    _traversable,
    _visited_map,
)
from web.webclient.presentation.local_map.validate import MAX_NODES
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.map_knowledge import NodeVisit, decode_node, encode_room


def _interior_graph(actor: Any, visits: list[NodeVisit], builder: _GraphBuilder, is_instance: bool) -> str:
    """Build the coordinate-free instance/interior graph from real Exits (D8)."""
    from typeclasses.rooms import InstanceRoom, Room

    location = actor.location
    if is_instance and not isinstance(location, InstanceRoom):
        raise PanelUnavailableError
    if not is_instance and not isinstance(location, Room):
        raise PanelUnavailableError
    visited = _visited_map(visits)
    current_id = encode_room(int(location.id))

    builder.add_node(
        current_id,
        location.key,
        0,
        0,
        visibility="current",
        current=True,
        anchor=False,
        landmark=False,
        action=None,
    )

    # Origin/return node for an instance.
    if is_instance:
        origin = location.origin_room
        if origin is not None and getattr(origin, "id", None):
            origin_id = encode_room(int(origin.id))
            builder.add_node(
                origin_id,
                origin.key,
                0,
                1,
                visibility=(
                    "visible_visited"
                    if _known_node_id(origin_id, visited)
                    else "visible_unvisited"
                ),
                anchor=False,
                landmark=False,
                action=None,
            )
            builder.add_edge(current_id, origin_id, "回程", True)

    # One-hop exits: visited adjacent rooms keep their names; unvisited
    # destinations are labelled 未探索 with the room name withheld.
    index = 1
    for exit_obj in sorted(location.exits, key=lambda e: (e.key or "")):
        destination = exit_obj.destination
        if destination is None or not getattr(destination, "id", None):
            continue
        dest_id = encode_room(int(destination.id))
        if dest_id == current_id:
            continue
        known = _known_node_id(dest_id, visited)
        if not known:
            label = "未探索"
        else:
            label = destination.key
        builder.add_node(
            dest_id,
            label,
            index,
            0,
            visibility="visible_visited" if known else "visible_unvisited",
            anchor=False,
            landmark=False,
            action=(
                {
                    "kind": "move",
                    "exit_ref": _exit_ref(exit_obj),
                    "destination": dest_id,
                }
                if _traversable(exit_obj, actor)
                else None
            ),
        )
        builder.add_edge(current_id, dest_id, exit_obj.key or "", True)
        index += 1

    # Remembered room nodes outside the current graph, bounded. A room node
    # whose object no longer resolves is treated as unavailable and omitted
    # (D4); the next reclamation prunes it idempotently.
    for visit in builder.remembered(MAX_NODES - len(builder.nodes)):
        if not visit.node_id.startswith("room:"):
            continue
        if visit.node_id == current_id or visit.node_id in {
            node["id"] for node in builder.nodes
        }:
            continue
        decoded = decode_node(visit.node_id)
        room = _room_by_id(decoded["dbref"])
        if room is None:
            continue
        builder.add_node(
            visit.node_id,
            room.key,
            index,
            0,
            visibility="remembered",
            anchor=False,
            landmark=False,
            action=None,
        )
        index += 1

    return "instance" if is_instance else "interior"


def _room_by_id(dbref: int):
    from evennia.objects.models import ObjectDB

    return ObjectDB.objects.filter(id=dbref).first()
