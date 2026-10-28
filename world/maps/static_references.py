"""Current bindings every authored static map reference resolves against.

Authored declarations (city gates, anchor placements, wilderness entry gates,
place room joins, district landmarks and grid art associations) hold a
qualified identity, never a coordinate. This module is the one game-side
boundary that turns those identities into the coordinate, room or wire form a
consumer needs.

Two shapes live here:

* :class:`StaticWorld` — every authored declaration family *together with* the
  bindings it resolves against, as one explicit value. A candidate bundle is
  checked against its own ``StaticWorld`` before publication, so an empty
  binding in one family can never be masked by an older published world.
* the read helpers (:func:`resolve_static`, :func:`settlement_node_xy`,
  :func:`place_exterior_xyz`, ...) — they read the currently published bundle
  and are deliberately uncached: a binding read reflects the bundle the process
  holds, so a moved node is visible to every consumer without a second alias
  table. Presenters that cache geometry key it by :func:`binding_signature`
  instead of invalidating a process-global cache.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from elosern_map_core.documents import QualifiedRef
from elosern_map_core.references import (
    ReferenceError,
    ReferenceIndex,
    ResolvedReference,
    interior_room_ref,
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


def _interior_rooms(interiors) -> tuple[tuple[str, str], ...]:
    """``(interior_id, room_id)`` pairs of one interior snapshot."""

    return tuple(
        (room.interior_id, room.room_id) for room in interiors.rooms.values()
    )


def reference_index() -> ReferenceIndex:
    """The complete index for every authored static target family."""

    from world.lore.anchors import anchor_geography
    from world.maps.interiors import current as current_interiors
    from world.maps.map_data import SETTLEMENT_GRAPHS

    return ReferenceIndex.build(
        settlement_nodes=(
            (map_id, node_id, node.coordinate)
            for map_id, graph in SETTLEMENT_GRAPHS.items()
            for node_id, node in graph.nodes.items()
        ),
        # A permanent interior room is identified by its authored room id (the
        # room's own tag); the interior document that authors it scopes the
        # reference.
        interior_rooms=_interior_rooms(current_interiors()),
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
    if map_id is None:
        raise ReferenceError("invalid_reference", f"{source}: no map scope")
    return (position[0], position[1], map_id)


def place_exterior_xyz(
    place: Any, *, index: ReferenceIndex | None = None
) -> tuple[int, int, str]:
    """The current exterior room address of one authored place.

    The exterior belongs to the interior document the place joins, so the
    address is resolved through that room's authored entrance.
    """

    from world.maps.interiors import exterior_for

    exterior = exterior_for(place.room.object_id)
    if exterior is None:
        raise ReferenceError(
            "invalid_reference",
            f"place {place.key!r}: its interior room declares no exterior entrance",
        )
    from elosern_map_core.references import settlement_node_ref

    return settlement_node_xyz(
        settlement_node_ref(exterior.settlement, exterior.node),
        index=index,
        source=f"place {place.key!r}",
    )


def anchor_entrance_xyz(
    placement: Any, *, index: ReferenceIndex | None = None
) -> tuple[int, int, str]:
    """The current entrance room address of one anchor placement."""

    return settlement_node_xyz(
        placement.node, index=index, source=f"anchor placement {placement.anchor_key}"
    )


#: The reference domains a district landmark may project.
LANDMARK_DOMAINS: tuple[str, ...] = (
    "settlement_node",
    "wilderness_cell",
    "location",
    "interior_room",
)


@dataclass(frozen=True, slots=True)
class StaticWorld:
    """Every authored static declaration family with its own bindings.

    One value carries both sides of every static join, so a candidate is
    checked against the candidate's bindings: no family can silently borrow
    the previously published world's index.
    """

    index: ReferenceIndex
    city_gates: Mapping[str, Any]
    anchor_placements: Mapping[str, Any]
    wilderness_entries: Mapping[str, Any]
    district_landmarks: Mapping[str, QualifiedRef]
    grid_art: Mapping[QualifiedRef, str]
    place_rooms: Mapping[str, QualifiedRef]
    interior_rooms: Mapping[str, str]
    interior_scenes: Mapping[str, str | None]
    scene_archetypes: frozenset[str]

    @property
    def fingerprint(self) -> str:
        """A stable digest of the checked declaration set."""

        digest = hashlib.sha256()
        parts: list[Any] = [
            tuple(
                (key, _ref(row.gate)) for key, row in sorted(self.city_gates.items())
            ),
            tuple(
                (key, _ref(placement.node))
                for key, placement in sorted(self.anchor_placements.items())
            ),
            tuple(
                (
                    key,
                    tuple(
                        (gate.return_direction, _ref(gate.destination))
                        for gate in entry.gates
                    ),
                )
                for key, entry in sorted(self.wilderness_entries.items())
            ),
            tuple(
                (key, _ref(landmark))
                for key, landmark in sorted(self.district_landmarks.items())
            ),
            tuple(
                (_ref(reference), scene)
                for reference, scene in sorted(
                    self.grid_art.items(), key=lambda item: (_ref(item[0]), item[1])
                )
            ),
            tuple(
                (key, _ref(room)) for key, room in sorted(self.place_rooms.items())
            ),
            tuple(sorted(self.interior_rooms.items())),
            tuple(
                (room_id, scene)
                for room_id, scene in sorted(self.interior_scenes.items())
            ),
            tuple(sorted(self.scene_archetypes)),
        ]
        for part in parts:
            digest.update(repr(part).encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()

    def problems(self) -> tuple[str, ...]:
        """Every declaration that does not resolve against these bindings."""

        problems: list[str] = []

        def check_node(source: str, reference: QualifiedRef) -> None:
            try:
                settlement_position(self.index, reference, source=source)
            except ReferenceError as error:
                problems.append(str(error))

        def check_landmark(source: str, reference: QualifiedRef) -> None:
            if reference.domain not in LANDMARK_DOMAINS:
                problems.append(
                    f"{source}: {reference.domain!r} is not one of "
                    f"{LANDMARK_DOMAINS}"
                )
                return
            try:
                resolve_reference(self.index, reference, source=source)
            except ReferenceError as error:
                problems.append(str(error))

        for key, row in self.city_gates.items():
            check_node(f"city gate {key}", row.gate)
        for key, placement in self.anchor_placements.items():
            check_node(f"anchor placement {key}", placement.node)
        for key, entry in self.wilderness_entries.items():
            for gate in entry.gates:
                check_node(
                    f"wilderness entry {key} gate {gate.return_direction}",
                    gate.destination,
                )
        for key, landmark in self.district_landmarks.items():
            check_landmark(f"district {key} landmark", landmark)
        for reference in self.grid_art:
            check_node(f"grid art {reference.map_id}:{reference.object_id}", reference)
        for key, reference in self.place_rooms.items():
            if reference.domain != "interior_room":
                problems.append(
                    f"place {key}: room join must be an interior_room reference, "
                    f"got {reference!r}"
                )
                continue
            if reference.object_id != key:
                problems.append(
                    f"place {key}: joins interior room {reference.object_id!r}; a "
                    "place key IS the permanent room identity"
                )
                continue
            authored = self.interior_rooms.get(key)
            if authored is None:
                problems.append(
                    f"place {key}: interior room {key!r} is not authored by any "
                    "interior document"
                )
                continue
            if reference.map_id is not None and reference.map_id != authored:
                problems.append(
                    f"place {key}: room is authored by interior {authored!r}, not "
                    f"{reference.map_id!r}"
                )
        for room_id, scene in self.interior_scenes.items():
            if scene is None:
                continue
            if scene not in self.scene_archetypes:
                problems.append(
                    f"interior room {room_id}: unregistered scene archetype "
                    f"{scene!r}"
                )
        return tuple(problems)


def _ref(value: QualifiedRef) -> tuple[Any, ...]:
    return (value.domain, value.map_id, value.object_id, value.cell)


def published_static_world() -> StaticWorld:
    """The static declaration families of the currently published bundle."""

    from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
    from world.lore.map_districts import current as current_districts
    from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
    from world.lore.settlements.places import PLACE_REGISTRY
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
    from world.maps.city_gates import CITY_GATE_REGISTRY
    from world.maps.interiors import current as current_interiors
    from world.maps.room_art import GRID_NODE_SCENE_ARCHETYPES

    interiors = current_interiors()
    return StaticWorld(
        index=reference_index(),
        city_gates=MappingProxyType(dict(CITY_GATE_REGISTRY)),
        anchor_placements=MappingProxyType(dict(ANCHOR_PLACEMENT_REGISTRY)),
        wilderness_entries=MappingProxyType(dict(WILDERNESS_ENTRY_REGISTRY)),
        district_landmarks=MappingProxyType(
            {
                key: district.landmark
                for key, district in current_districts().districts.items()
            }
        ),
        grid_art=MappingProxyType(dict(GRID_NODE_SCENE_ARCHETYPES)),
        place_rooms=MappingProxyType(
            {key: place.room for key, place in PLACE_REGISTRY.items()}
        ),
        interior_rooms=MappingProxyType(
            {room.room_id: room.interior_id for room in interiors.rooms.values()}
        ),
        interior_scenes=MappingProxyType(
            {room.room_id: room.scene_archetype for room in interiors.rooms.values()}
        ),
        scene_archetypes=frozenset(SCENE_ARCHETYPE_REGISTRY),
    )


def static_world_for_candidate(
    *,
    world,
    settlements,
    interiors,
    districts,
) -> StaticWorld:
    """The static declaration families of one *candidate* world.

    ``world`` is the core authoring world (its reference index binds the
    candidate's own settlement nodes, interior rooms and locations),
    ``settlements``/``interiors``/``districts`` are the composed candidate
    views. Nothing here reads a published snapshot, so an approval cannot be
    inherited from a world that is being replaced.
    """

    from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
    from world.lore.settlements.places import PLACE_REGISTRY

    return StaticWorld(
        index=world.reference_index,
        city_gates=MappingProxyType(dict(settlements.city_gates)),
        anchor_placements=MappingProxyType(dict(settlements.anchor_placements)),
        wilderness_entries=MappingProxyType(dict(settlements.wilderness_entries)),
        district_landmarks=MappingProxyType(
            {
                key: district.landmark
                for key, district in districts.districts.items()
            }
        ),
        grid_art=MappingProxyType(dict(settlements.grid_node_scene_archetypes)),
        place_rooms=MappingProxyType(
            {key: place.room for key, place in PLACE_REGISTRY.items()}
        ),
        interior_rooms=MappingProxyType(
            {room.room_id: room.interior_id for room in interiors.rooms.values()}
        ),
        interior_scenes=MappingProxyType(
            {room.room_id: room.scene_archetype for room in interiors.rooms.values()}
        ),
        scene_archetypes=frozenset(SCENE_ARCHETYPE_REGISTRY),
    )


def validate_static_world(world: StaticWorld) -> None:
    """Reject one static world whose declarations do not resolve."""

    problems = world.problems()
    if problems:
        raise StaticReferenceError(problems)


def validate_static_references(*, index: ReferenceIndex | None = None) -> None:
    """Reject a non-resolving static declaration before any persistent write.

    Every family is checked against one binding snapshot, so a valid
    declaration followed by an invalid one cannot persist the first half. A
    target that is authored but has no materialized room is a different,
    existing condition: convergence warns and skips it, and this preflight does
    not turn that into an adoption failure.
    """

    published = published_static_world()
    if index is None:
        validate_static_world(published)
        return
    from dataclasses import replace

    validate_static_world(replace(published, index=index))


def binding_signature() -> str:
    """A stable digest of every binding a cached map presenter depends on.

    The digest covers the settlement graphs (a moved node changes it), the
    placements, the interior identities and their exteriors, the district
    landmarks, the grid art associations, the city gates and the wilderness
    gate destinations, so a presenter cache keyed by it can never serve
    geometry or visit ids from a previous binding.
    """

    from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
    from world.lore.anchors import LOCAL_FRAME_ANCHOR_REGISTRY, anchor_geography
    from world.lore.map_districts import current as current_districts
    from world.lore.settlements.places import PLACE_REGISTRY
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
    from world.maps.city_gates import CITY_GATE_REGISTRY
    from world.maps.geography import current as current_geography
    from world.maps.interiors import current as current_interiors
    from world.maps.map_data import SETTLEMENT_GRAPHS
    from world.maps.room_art import GRID_NODE_SCENE_ARCHETYPES

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
    parts.append(current_geography().identity)
    parts.append(
        tuple(
            (key, frame.local_anchor_m)
            for key, frame in sorted(LOCAL_FRAME_ANCHOR_REGISTRY.items())
        )
    )
    parts.append(
        tuple(
            (key, _ref(placement.node))
            for key, placement in sorted(ANCHOR_PLACEMENT_REGISTRY.items())
        )
    )
    # A place joins an interior room; the room's own exterior and authored
    # prose live in the interior document, so the interior world's identity is
    # part of the signature rather than a place exterior field.
    interiors = current_interiors()
    parts.append(interiors.identity)
    parts.append(
        tuple(
            (key, place.room.object_id) for key, place in sorted(PLACE_REGISTRY.items())
        )
    )
    districts = current_districts()
    parts.append(
        tuple(
            (key, _ref(district.landmark))
            for key, district in sorted(districts.districts.items())
        )
    )
    # A name-only authored edit changes no landmark reference, so the district
    # source digest is part of the signature: cached presentation never serves
    # a retired district or landmark name.
    parts.append(districts.identity)
    parts.append(
        tuple(
            (_ref(reference), scene)
            for reference, scene in sorted(
                GRID_NODE_SCENE_ARCHETYPES.items(),
                key=lambda item: (_ref(item[0]), item[1]),
            )
        )
    )
    parts.append(
        tuple((key, _ref(row.gate)) for key, row in sorted(CITY_GATE_REGISTRY.items()))
    )
    parts.append(
        tuple(
            (key, tuple((gate.return_direction, _ref(gate.destination)) for gate in entry.gates))
            for key, entry in sorted(WILDERNESS_ENTRY_REGISTRY.items())
        )
    )
    digest = hashlib.sha1(repr(parts).encode("utf-8"))
    return digest.hexdigest()


__all__ = [
    "LANDMARK_DOMAINS",
    "StaticReferenceError",
    "StaticWorld",
    "anchor_entrance_xyz",
    "binding_signature",
    "map_reference_index",
    "place_exterior_xyz",
    "published_static_world",
    "reference_index",
    "resolve_static",
    "settlement_node_xy",
    "settlement_node_xyz",
    "settlement_reference_index",
    "static_world_for_candidate",
    "validate_static_references",
    "validate_static_world",
]
