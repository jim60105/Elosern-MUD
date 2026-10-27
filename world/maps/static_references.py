"""Current bindings every authored static map reference resolves against.

Authored declarations (city gates, anchor placements, wilderness entry gates,
place exteriors, district landmarks and grid art associations) hold a
qualified identity, never a coordinate. This module is the one game-side
boundary that reads the *current* settlement graphs, place registry and anchor
geography and turns those identities into the coordinate, room or wire form a
consumer needs.

It is deliberately uncached: a binding read must reflect the graphs and
registries the process currently holds, so a moved node is visible to every
consumer without a second alias table. Presenters that cache geometry key it
by :func:`binding_signature` instead of invalidating a process-global cache.
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable

from elosern_map_core.documents import QualifiedRef
from elosern_map_core.references import (
    ReferenceError,
    ReferenceIndex,
    ResolvedReference,
    resolve_reference,
    settlement_position,
)


class StaticReferenceError(ValueError):
    """One or more authored static references do not resolve.

    ``problems`` names every declaration and its target, in registry order, so
    a caller can reject the complete declaration closure before it mutates
    persistent state.
    """

    def __init__(self, problems: Iterable[str]) -> None:
        self.problems = tuple(problems)
        super().__init__(
            "invalid static map references:\n" + "\n".join(self.problems)
        )


def settlement_reference_index() -> ReferenceIndex:
    """The index a settlement-only consumer (a gate, place or gate destination) needs."""

    from world.maps.map_data import SETTLEMENT_GRAPHS

    return ReferenceIndex.build(
        settlement_nodes=(
            (map_id, node_id, node.coordinate)
            for map_id, graph in SETTLEMENT_GRAPHS.items()
            for node_id, node in graph.nodes.items()
        )
    )


def reference_index() -> ReferenceIndex:
    """The complete index for every authored static target family."""

    from world.lore.anchors import anchor_geography
    from world.lore.settlements.places import PLACE_REGISTRY

    from world.maps.map_data import SETTLEMENT_GRAPHS

    return ReferenceIndex.build(
        settlement_nodes=(
            (map_id, node_id, node.coordinate)
            for map_id, graph in SETTLEMENT_GRAPHS.items()
            for node_id, node in graph.nodes.items()
        ),
        # A permanent interior room is identified by its place key (the room's
        # own tag); a place is its own single authored room until the interior
        # cutover adds per-room declarations.
        interior_rooms=((place.key, place.key) for place in PLACE_REGISTRY.values()),
        locations=(
            (key, tuple(geography.cell))
            for key, geography in anchor_geography().items()
        ),
    )


def map_reference_index() -> ReferenceIndex:
    """The settlement/location bindings a district landmark can project."""

    from world.lore.anchors import anchor_geography
    from world.maps.map_data import SETTLEMENT_GRAPHS

    return ReferenceIndex.build(
        settlement_nodes=(
            (map_id, node_id, node.coordinate)
            for map_id, graph in SETTLEMENT_GRAPHS.items()
            for node_id, node in graph.nodes.items()
        ),
        locations=(
            (key, tuple(geography.cell))
            for key, geography in anchor_geography().items()
        ),
    )


def resolve_static(
    reference: QualifiedRef,
    *,
    index: ReferenceIndex | None = None,
    source: str = "",
) -> ResolvedReference:
    """Resolve one authored reference against the current bindings."""

    return resolve_reference(
        index if index is not None else reference_index(),
        reference,
        source=source,
    )


def settlement_node_xy(
    reference: QualifiedRef,
    *,
    index: ReferenceIndex | None = None,
    source: str = "",
) -> tuple[int, int]:
    """The current settlement-local metre coordinate of one node identity."""

    return settlement_position(
        index if index is not None else settlement_reference_index(),
        reference,
        source=source,
    )


def settlement_node_xyz(
    reference: QualifiedRef,
    *,
    index: ReferenceIndex | None = None,
    source: str = "",
) -> tuple[int, int, str]:
    """The current ``(x, y, map_id)`` address of one node identity."""

    position = settlement_node_xy(reference, index=index, source=source)
    map_id = reference.map_id
    assert map_id is not None  # settlement_position requires the domain
    return (position[0], position[1], map_id)


def place_exterior_xyz(
    place: Any, *, index: ReferenceIndex | None = None
) -> tuple[int, int, str]:
    """The current exterior room address of one authored place."""

    return settlement_node_xyz(place.exterior, index=index, source=f"place {place.key}")


def anchor_entrance_xyz(
    placement: Any, *, index: ReferenceIndex | None = None
) -> tuple[int, int, str]:
    """The current entrance room address of one anchor placement."""

    return settlement_node_xyz(
        placement.node, index=index, source=f"anchor placement {placement.anchor_key}"
    )


def binding_signature() -> str:
    """A stable digest of every binding a cached map presenter depends on.

    The digest covers the settlement graphs (a moved node changes it), the
    placements and place exteriors, the district landmarks, the grid art
    associations, the city gates and the wilderness gate destinations, so a
    presenter cache keyed by it can never serve geometry or visit ids from a
    previous binding.
    """

    from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
    from world.lore.anchors import LOCAL_FRAME_ANCHOR_REGISTRY, anchor_geography
    from world.maps.geography import current
    from world.lore.map_districts import MAP_DISTRICT_REGISTRY
    from world.lore.settlements.places import PLACE_REGISTRY
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
    from world.maps.city_gates import CITY_GATE_REGISTRY
    from world.maps.map_data import SETTLEMENT_GRAPHS
    from world.maps.room_art import GRID_NODE_SCENE_ARCHETYPES

    def ref(value: QualifiedRef) -> tuple[Any, ...]:
        return (value.domain, value.map_id, value.object_id, value.cell)

    parts: list[Any] = []
    for map_id, graph in sorted(SETTLEMENT_GRAPHS.items()):
        parts.append(
            (
                map_id,
                tuple(
                    (node_id, node.x, node.y, node.physical)
                    for node_id, node in sorted(graph.nodes.items())
                ),
                tuple(
                    (
                        road.road_id,
                        road.source_id,
                        road.destination_id,
                        road.direction_hint,
                        road.bend_points,
                    )
                    for road in sorted(graph.roads, key=lambda item: item.road_id)
                ),
            )
        )
    parts.append(
        tuple(
            (key, tuple(geography.cell))
            for key, geography in sorted(anchor_geography().items())
        )
    )
    # The authored continent and location sources themselves: a reload that
    # changes terrain, prose or a scene association must invalidate every
    # presenter cache keyed by this digest.
    parts.append(current().identity)
    parts.append(
        tuple(
            (key, frame.local_anchor_m)
            for key, frame in sorted(LOCAL_FRAME_ANCHOR_REGISTRY.items())
        )
    )
    parts.append(
        tuple(
            (key, ref(placement.node))
            for key, placement in sorted(ANCHOR_PLACEMENT_REGISTRY.items())
        )
    )
    parts.append(
        tuple(
            (key, ref(place.exterior))
            for key, place in sorted(PLACE_REGISTRY.items())
        )
    )
    parts.append(
        tuple(
            (key, ref(district.landmark))
            for key, district in sorted(MAP_DISTRICT_REGISTRY.items())
        )
    )
    parts.append(
        tuple(
            (ref(reference), scene)
            for reference, scene in sorted(
                GRID_NODE_SCENE_ARCHETYPES.items(),
                key=lambda item: (ref(item[0]), item[1]),
            )
        )
    )
    parts.append(
        tuple((key, ref(row.gate)) for key, row in sorted(CITY_GATE_REGISTRY.items()))
    )
    parts.append(
        tuple(
            (key, tuple((gate.return_direction, ref(gate.destination)) for gate in entry.gates))
            for key, entry in sorted(WILDERNESS_ENTRY_REGISTRY.items())
        )
    )
    digest = hashlib.sha1(repr(parts).encode("utf-8"))
    return digest.hexdigest()


def validate_static_references(*, index: ReferenceIndex | None = None) -> None:
    """Reject a non-resolving static declaration before any persistent write.

    Every family is checked against one binding snapshot, so a valid
    declaration followed by an invalid one cannot persist the first half. A
    target that is authored but has no materialized room is a different,
    existing condition: convergence warns and skips it, and this preflight does
    not turn that into an adoption failure.
    """

    from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
    from world.lore.map_districts import MAP_DISTRICT_REGISTRY
    from world.lore.settlements.places import PLACE_REGISTRY
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
    from world.maps.city_gates import CITY_GATE_REGISTRY
    from world.maps.room_art import GRID_NODE_SCENE_ARCHETYPES

    current = index if index is not None else reference_index()
    problems: list[str] = []

    def check_node(source: str, reference: QualifiedRef) -> None:
        """One settlement-node consumer: domain policy plus existence."""

        try:
            settlement_position(current, reference, source=source)
        except ReferenceError as error:
            problems.append(str(error))

    def check_landmark(source: str, reference: QualifiedRef) -> None:
        """A district landmark may use any domain that projects a map position."""

        allowed = ("settlement_node", "wilderness_cell", "location")
        if reference.domain not in allowed:
            problems.append(
                f"{source}: {reference.domain!r} is not one of {allowed}"
            )
            return
        try:
            resolve_static(reference, index=current, source=source)
        except ReferenceError as error:
            problems.append(str(error))

    for key, row in CITY_GATE_REGISTRY.items():
        check_node(f"city gate {key}", row.gate)
    for key, placement in ANCHOR_PLACEMENT_REGISTRY.items():
        check_node(f"anchor placement {key}", placement.node)
    for key, entry in WILDERNESS_ENTRY_REGISTRY.items():
        for gate in entry.gates:
            check_node(
                f"wilderness entry {key} gate {gate.return_direction}",
                gate.destination,
            )
    for key, place in PLACE_REGISTRY.items():
        check_node(f"place {key} exterior", place.exterior)
    for key, district in MAP_DISTRICT_REGISTRY.items():
        check_landmark(f"district {key} landmark", district.landmark)
    for reference in GRID_NODE_SCENE_ARCHETYPES:
        check_node(
            f"grid art {reference.map_id}:{reference.object_id}",
            reference,
        )
    if problems:
        raise StaticReferenceError(problems)


__all__ = [
    "StaticReferenceError",
    "anchor_entrance_xyz",
    "binding_signature",
    "place_exterior_xyz",
    "map_reference_index",
    "reference_index",
    "resolve_static",
    "settlement_node_xy",
    "settlement_node_xyz",
    "settlement_reference_index",
    "validate_static_references",
]
