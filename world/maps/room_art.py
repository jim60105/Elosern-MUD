"""Authored room-art metadata owned by the map layer (unified-room-art-metadata).

A room's scene facts are authored, never inferred:

* ``scene_archetype`` — the registered archetype the room's background
  resolves from. Grid nodes declare it in their settlement document, permanent
  interiors in their interior document, and incidental/wilderness rooms get it
  from the terrain rules.
* ``room_art_key`` — the optional registered per-room artwork key a room
  addresses. It is authored in the same map documents (an interior room's
  ``art_key``) and never derived from a room name, a database row or a
  neighbouring room.
* ``scene_identity`` — the bounded logical identity that distinguishes the
  logical place even when one pooled room object serves many coordinates.

The authored key vocabulary is :data:`world.maps.interiors`' published
``room_art_keys``: a ``room/<key>/`` directory that no authored interior room
declares cannot be characterized, and no key is ever a runtime row id or a
translated display name. This module owns only the identity derivations; it
authors no table, so no second authority over a room's scene facts exists.
"""

from __future__ import annotations

from typing import Mapping

from elosern_map_core.documents import QualifiedRef

from world.maps.published import PublishedView

# The bound that keeps a logical scene identity within the descriptor's subject
# ceiling. Every identity this module produces is an authored short key plus at
# most two small integers, so the bound is a contract guard, not a truncation.
MAX_SCENE_IDENTITY_CODE_POINTS = 128


def _scene_identity(prefix: str, *parts: object) -> str:
    """One bounded logical scene identity from an authored prefix and parts."""

    identity = ":".join((prefix, *(_text(part) for part in parts)))
    if len(identity) > MAX_SCENE_IDENTITY_CODE_POINTS:
        raise ValueError(
            f"scene identity {identity!r} exceeds "
            f"{MAX_SCENE_IDENTITY_CODE_POINTS} code points"
        )
    return identity


def _text(part: object) -> str:
    return str(part)


def grid_scene_identity(map_key: str, x: int, y: int) -> str:
    """The authored grid node's logical identity (its map/z coordinate)."""
    return _scene_identity("grid", map_key, f"{x},{y}")


def place_scene_identity(place_key: str) -> str:
    """A permanent interior room's logical identity (its authored room id)."""
    return _scene_identity("place", place_key)


def wilderness_scene_identity(name: str, x: int, y: int) -> str:
    """A pooled wilderness room's logical identity (name plus coordinates)."""
    return _scene_identity("wilderness", name, f"{x},{y}")


def instance_scene_identity(identity: object) -> str:
    """A non-pooled instance's logical identity (its stable room identity)."""
    return _scene_identity("instance", identity)


#: Authored grid node identity -> registered scene archetype, composed from each
#: settlement document's per-node ``scene_archetype`` field. A node's current
#: coordinate is derived at the consumer boundary, never stored here.
GRID_NODE_SCENE_ARCHETYPES: Mapping[QualifiedRef, str] = PublishedView(
    "grid_node_scene_archetypes"
)


__all__ = [
    "GRID_NODE_SCENE_ARCHETYPES",
    "MAX_SCENE_IDENTITY_CODE_POINTS",
    "grid_scene_identity",
    "instance_scene_identity",
    "place_scene_identity",
    "wilderness_scene_identity",
]
