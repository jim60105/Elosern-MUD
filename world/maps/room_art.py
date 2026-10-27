"""Authored room-art metadata owned by the map layer (unified-room-art-metadata).

The map owner is the single writer of a room's scene facts. This module is the
one explicit authored mapping that declares, for every supported room family:

* the registered **scene archetype** the room renders its background from
  (``world.lore.scene_archetypes``), and
* the optional **registered room-art key** a per-room operator override may
  address (``world.art.scene_definitions``' authored room vocabulary), and
* a bounded **logical scene identity** that distinguishes the logical place
  even when one pooled room object serves many coordinates.

Keys are never inferred from a room name, an ObjectDB id, a threat tier or a
neighbouring room: each family below is an authored table, and import fails
closed if a mapped scene archetype is unregistered or an authored place is
left without a declaration. The art resolver only reads this metadata; it never
writes or repairs it.

Families and their identity sources:

* **authored grid rooms** — the authored ``(map key, x, y)`` coordinate;
* **permanent interiors** — the authored place key (which IS the room-art key);
* **pooled wilderness** — the wilderness name plus the current coordinates;
* **instances** — the stable non-pooled room identity, carried explicitly into
  supported instance construction.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from elosern_map_core.documents import QualifiedRef
from elosern_map_core.references import settlement_node_ref

from world.art.scene_definitions import is_registered_room_art_key
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.lore.settlements.places import PLACE_REGISTRY

# The bound that keeps a logical scene identity within the descriptor's subject
# ceiling. Every identity this module produces is an authored short key plus at
# most two small integers, so the bound is a contract guard, not a truncation.
MAX_SCENE_IDENTITY_CODE_POINTS = 128


def _scene_identity(prefix: str, *parts: object) -> str:
    """One bounded logical scene identity from an authored prefix and parts."""
    identity = ":".join((prefix, *(_text(part) for part in parts)))
    if len(identity) > MAX_SCENE_IDENTITY_CODE_POINTS:
        raise ValueError(
            f"scene identity {identity!r} exceeds {MAX_SCENE_IDENTITY_CODE_POINTS} code points"
        )
    return identity


def _text(part: object) -> str:
    return str(part)


def grid_scene_identity(map_key: str, x: int, y: int) -> str:
    """The authored grid node's logical identity (its map/z coordinate)."""
    return _scene_identity("grid", map_key, f"{x},{y}")


def place_scene_identity(place_key: str) -> str:
    """A permanent interior's logical identity (its authored place key)."""
    return _scene_identity("place", place_key)


def wilderness_scene_identity(name: str, x: int, y: int) -> str:
    """A pooled wilderness room's logical identity (name plus coordinates)."""
    return _scene_identity("wilderness", name, f"{x},{y}")


def instance_scene_identity(identity: object) -> str:
    """A non-pooled instance's logical identity (its stable room identity)."""
    return _scene_identity("instance", identity)


# --------------------------------------------------------------------------- authored tables

# Wilderness region scene associations are map-owned fields of the continent
# source (``scene_archetype`` per region), published by
# ``world.maps.geography`` after validating them against the scene catalog.
# They are deliberately not duplicated here.
#
# Authored grid node identity -> registered scene archetype. Every walkable
# node of every declared settlement graph is listed so the art panel resolves
# a real registered archetype on a fresh boot; the node's current coordinate is
# derived at the consumer boundary, never stored here.
_GRID_NODE_SCENE_ARCHETYPES: dict[QualifiedRef, str] = {
    # 聖潔王都 (capital_altoria): the river town's streets, plazas, gates and
    # quays are all the town street.
    settlement_node_ref("capital_altoria", "south_gate"): "city_street",
    settlement_node_ref("capital_altoria", "quay"): "city_street",
    settlement_node_ref("capital_altoria", "riverbank_road"): "city_street",
    settlement_node_ref("capital_altoria", "south_avenue"): "city_street",
    settlement_node_ref("capital_altoria", "inn_lane"): "city_street",
    settlement_node_ref("capital_altoria", "bath_forecourt"): "city_street",
    settlement_node_ref("capital_altoria", "old_wall_ruins"): "city_street",
    settlement_node_ref("capital_altoria", "north_avenue"): "city_street",
    settlement_node_ref("capital_altoria", "craft_alley"): "city_street",
    settlement_node_ref("capital_altoria", "market_street"): "city_street",
    settlement_node_ref("capital_altoria", "central_plaza"): "city_street",
    settlement_node_ref("capital_altoria", "guild_forecourt"): "city_street",
    settlement_node_ref("capital_altoria", "east_market"): "city_street",
    settlement_node_ref("capital_altoria", "east_gate"): "city_street",
    settlement_node_ref("capital_altoria", "training_ground"): "city_street",
    settlement_node_ref("capital_altoria", "holy_steps"): "city_street",
    settlement_node_ref("capital_altoria", "great_temple"): "city_street",
    settlement_node_ref("capital_altoria", "noble_quarter"): "city_street",
    settlement_node_ref("capital_altoria", "upper_gate"): "city_street",
    settlement_node_ref("capital_altoria", "academy"): "city_street",
    settlement_node_ref("capital_altoria", "palace_forecourt"): "city_street",
    # 暗影谷村 (village_ciaran): the forest village's paths and groves are the
    # forest path, the cleared plaza and drill ground the town street, and the
    # stream approaches the wilderness path.
    settlement_node_ref("village_ciaran", "hidden_path"): "forest_path",
    settlement_node_ref("village_ciaran", "village_plaza"): "city_street",
    settlement_node_ref("village_ciaran", "training_clearing"): "city_street",
    settlement_node_ref("village_ciaran", "stream_path"): "wilderness_path",
    settlement_node_ref("village_ciaran", "old_tree_north"): "forest_path",
    settlement_node_ref("village_ciaran", "weaving_slope"): "forest_path",
    settlement_node_ref("village_ciaran", "elder_tree"): "forest_path",
    settlement_node_ref("village_ciaran", "silver_leaf_slope"): "forest_path",
    settlement_node_ref("village_ciaran", "herb_garden"): "forest_path",
    settlement_node_ref("village_ciaran", "stream_bend"): "wilderness_path",
}

GRID_NODE_SCENE_ARCHETYPES: Mapping[QualifiedRef, str] = MappingProxyType(
    _GRID_NODE_SCENE_ARCHETYPES
)

# Authored permanent interior place -> registered scene archetype. Keys are the
# authored place keys of ``world.lore.settlements.places``; a place key IS the
# interior's registered room-art key, so this table needs no separate key field.
# The temple, its sanctum shop and the palace render the shrine interior; every
# other interior (dwellings, halls, shops, taverns, commons, courier stations)
# renders the tavern interior.
_SANCTUARY_SCENE_ARCHETYPE = "shrine_interior"
_INTERIOR_SCENE_ARCHETYPE = "tavern_interior"

_PLACE_SCENE_ARCHETYPES: dict[str, str] = {
    place_key: (
        _SANCTUARY_SCENE_ARCHETYPE
        if place_key in {"altoria_temple", "altoria_sanctum", "altoria_palace"}
        else _INTERIOR_SCENE_ARCHETYPE
    )
    for place_key in PLACE_REGISTRY
}

PLACE_SCENE_ARCHETYPES: Mapping[str, str] = MappingProxyType(_PLACE_SCENE_ARCHETYPES)


# --------------------------------------------------------------------------- validation


def validate_room_art_registries() -> None:
    """Fail closed on any mapped key this contract requires to be registered.

    Called at import: a mapped scene archetype must be a registered scene
    archetype, every authored place key must be a registered room-art key, and
    every authored place must be declared here. A defect names the offending
    key so a bad edit cannot silently degrade a room to no scene art.
    """
    for node, scene in GRID_NODE_SCENE_ARCHETYPES.items():
        if not isinstance(node, QualifiedRef) or node.domain != "settlement_node":
            raise ValueError(f"grid art key {node!r} is not a settlement_node reference")
        if scene not in SCENE_ARCHETYPE_REGISTRY:
            raise ValueError(
                f"grid node {node!r} maps to unregistered scene archetype {scene!r}"
            )
    for place_key, scene in PLACE_SCENE_ARCHETYPES.items():
        if place_key not in PLACE_REGISTRY:
            raise ValueError(f"place {place_key!r} is not an authored place")
        if not is_registered_room_art_key(place_key):
            raise ValueError(f"place {place_key!r} is not a registered room-art key")
        if scene not in SCENE_ARCHETYPE_REGISTRY:
            raise ValueError(
                f"place {place_key!r} maps to unregistered scene archetype {scene!r}"
            )
    missing = sorted(set(PLACE_REGISTRY) - set(PLACE_SCENE_ARCHETYPES))
    if missing:
        raise ValueError(
            "authored places without a declared scene archetype: " + ", ".join(missing)
        )


validate_room_art_registries()


__all__ = [
    "GRID_NODE_SCENE_ARCHETYPES",
    "MAX_SCENE_IDENTITY_CODE_POINTS",
    "PLACE_SCENE_ARCHETYPES",
    "grid_scene_identity",
    "instance_scene_identity",
    "place_scene_identity",
    "validate_room_art_registries",
    "wilderness_scene_identity",
]
