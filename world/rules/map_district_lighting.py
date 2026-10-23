"""Read-only district lighting derived from map knowledge (map-districts).

A map district is lit if and only if its exact canonical landmark node is in
the player's visited record (world-map drawer design §4.3). Lighting is a pure
derivation: it reads the record through :func:`world.rules.map_knowledge.
parse_knowledge`, compares node IDs by exact string identity, and never writes
the record, adds a discovery attribute, or attaches district names or geometry
to persisted knowledge. ``record_arrival`` stays the sole knowledge writer.

The first-arrival ``已探明`` narrative belongs to the world-map panel change,
not to this module.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from world.lore.map_districts import MAP_DISTRICT_REGISTRY, MapDistrict
from world.rules.map_knowledge import KNOWLEDGE_ATTR, NodeVisit, parse_knowledge


def lit_district_keys_from_visits(
    visits: Iterable[NodeVisit],
    registry: Mapping[str, MapDistrict] | None = None,
) -> frozenset[str]:
    """The keys of the districts whose exact landmark node was visited."""
    districts = MAP_DISTRICT_REGISTRY if registry is None else registry
    visited = {visit.node_id for visit in visits}
    return frozenset(
        key for key, district in districts.items() if district.landmark_node in visited
    )


def lit_district_keys(
    character: Any,
    registry: Mapping[str, MapDistrict] | None = None,
) -> frozenset[str]:
    """The keys of the districts the character has lit.

    A character with no record yet has visited nothing, so nothing is lit. A
    corrupt record raises :class:`world.rules.map_knowledge.KnowledgeError`
    exactly as ``parse_knowledge`` does (it is never reset here); the caller
    decides how an unreadable record is presented, as the local-map presenter
    does.
    """
    if character.attributes.get(KNOWLEDGE_ATTR) is None:
        return frozenset()
    return lit_district_keys_from_visits(parse_knowledge(character), registry)
