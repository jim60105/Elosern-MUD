"""Qualified static-reference resolution over an explicit authored index.

Every authored static map target is a :class:`QualifiedRef`: a tagged domain
plus, where the domain is map-scoped, its map and object identity, or an
explicitly typed wilderness cell. Static declarations never store coordinates;
a consumer resolves the reference against the *current* binding and derives the
coordinate, wire identity or locator form it needs at that boundary.

Resolution is one pure function over an explicit :class:`ReferenceIndex`, so
the game adapter and the YAML authoring world share the same implementation and
the same named diagnostics. The index is immutable and never a process cache:
callers build it from the declarations they are about to use.

Diagnostic codes are stable and machine-readable:

``invalid_reference``    the reference shape is not valid for its domain.
``unknown_domain``       the tagged domain is not in the closed vocabulary.
``unknown_reference``    the domain has no authored object with that identity.
``wrong_domain``         the identity is authored, but under another domain.
``duplicate_reference``  one identity is declared twice in the index input.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Protocol

from .documents import Cell, QualifiedRef
from .geometry import is_within_frame
from .schema import QUALIFIED_REF_DOMAINS

INVALID_REFERENCE = "invalid_reference"
UNKNOWN_DOMAIN = "unknown_domain"
UNKNOWN_REFERENCE = "unknown_reference"
WRONG_DOMAIN = "wrong_domain"
DUPLICATE_REFERENCE = "duplicate_reference"

#: Per-domain presence rules, mirroring the machine-readable schema.
_DOMAIN_FIELDS: dict[str, tuple[bool, bool, bool]] = {
    # domain: (map_id required, object_id required, cell required)
    "settlement_node": (True, True, False),
    "interior_room": (True, True, False),
    "location": (False, True, False),
    "wilderness_cell": (False, False, True),
}


class ReferenceError(ValueError):
    """A static reference cannot be resolved; ``code`` names the defect."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class ResolvedReference:
    """One reference resolved against the current authored bindings.

    ``position_m`` is the settlement-local metre coordinate of a
    ``settlement_node``. ``cell`` is the wilderness cell of a
    ``wilderness_cell`` reference or of a ``location``. An ``interior_room``
    has neither: its room is coordinate-free and identified by the interior
    and room ids alone.
    """

    reference: QualifiedRef
    position_m: Cell | None = None
    cell: Cell | None = None

    @property
    def domain(self) -> str:
        return self.reference.domain

    @property
    def map_id(self) -> str | None:
        return self.reference.map_id

    @property
    def object_id(self) -> str | None:
        return self.reference.object_id


def _freeze_bindings(
    bindings: Mapping[str, Mapping[str, Cell]],
) -> Mapping[str, Mapping[str, Cell]]:
    return MappingProxyType(
        {map_id: MappingProxyType(dict(nodes)) for map_id, nodes in bindings.items()}
    )


@dataclass(frozen=True, slots=True)
class ReferenceIndex:
    """The current authored bindings every static reference resolves against."""

    settlement_nodes: Mapping[str, Mapping[str, Cell]]
    interior_rooms: Mapping[str, frozenset[str]]
    locations: Mapping[str, Cell]
    frame_cells: int | None = None

    @property
    def reference_index(self) -> "ReferenceIndex":
        """This value is already a reference world (the public seam's input)."""

        return self

    @classmethod
    def build(
        cls,
        *,
        settlement_nodes: Iterable[tuple[str, str, Cell]] = (),
        interior_rooms: Iterable[tuple[str, str]] = (),
        locations: Iterable[tuple[str, Cell]] = (),
        frame_cells: int | None = None,
    ) -> "ReferenceIndex":
        """Assemble an index, rejecting one identity declared twice."""

        nodes: dict[str, dict[str, Cell]] = {}
        seen_nodes: set[tuple[str, str]] = set()
        for map_id, node_id, position in settlement_nodes:
            _require_text(map_id, "settlement_node map id")
            _require_text(node_id, "settlement_node object id")
            _require_cell(position, f"settlement_node {map_id}:{node_id} position")
            key = (map_id, node_id)
            if key in seen_nodes:
                raise ReferenceError(
                    DUPLICATE_REFERENCE,
                    f"settlement_node {map_id}:{node_id} is declared twice",
                )
            seen_nodes.add(key)
            nodes.setdefault(map_id, {})[node_id] = tuple(position)

        rooms: dict[str, set[str]] = {}
        seen_rooms: set[tuple[str, str]] = set()
        for interior_id, room_id in interior_rooms:
            _require_text(interior_id, "interior_room interior id")
            _require_text(room_id, "interior_room object id")
            key = (interior_id, room_id)
            if key in seen_rooms:
                raise ReferenceError(
                    DUPLICATE_REFERENCE,
                    f"interior_room {interior_id}:{room_id} is declared twice",
                )
            seen_rooms.add(key)
            rooms.setdefault(interior_id, set()).add(room_id)

        location_cells: dict[str, Cell] = {}
        for location_id, cell in locations:
            _require_text(location_id, "location object id")
            _require_cell(cell, f"location {location_id} cell")
            if location_id in location_cells:
                raise ReferenceError(
                    DUPLICATE_REFERENCE,
                    f"location {location_id} is declared twice",
                )
            location_cells[location_id] = tuple(cell)

        return cls(
            settlement_nodes=_freeze_bindings(nodes),
            interior_rooms=MappingProxyType(
                {interior_id: frozenset(values) for interior_id, values in rooms.items()}
            ),
            locations=MappingProxyType(location_cells),
            frame_cells=frame_cells,
        )

    @classmethod
    def from_documents(
        cls,
        *,
        settlements: Mapping[str, Any],
        interiors: Mapping[str, Any],
        locations: Any,
        frame_cells: int | None = None,
    ) -> "ReferenceIndex":
        """Build the index from typed authoring documents.

        The parameter names follow the authoring documents they read
        (``settlements``, ``interiors``, ``locations``); a document exposes
        ``nodes``, ``rooms`` and ``locations`` mappings respectively. This keeps
        the game adapter and the authoring world on one construction shape
        without importing either package into the other.
        """

        return cls.build(
            settlement_nodes=(
                (map_id, node_id, node.coordinate)
                for map_id, settlement in settlements.items()
                for node_id, node in settlement.nodes.items()
            ),
            interior_rooms=(
                (interior_id, room_id)
                for interior_id, interior in interiors.items()
                for room_id in interior.rooms
            ),
            locations=(
                (location_id, location.cell)
                for location_id, location in locations.locations.items()
            ),
            frame_cells=frame_cells,
        )


class ReferenceWorld(Protocol):
    """Anything that exposes exactly one current :class:`ReferenceIndex`."""

    @property
    def reference_index(self) -> ReferenceIndex: ...


def _require_text(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value:
        raise ReferenceError(INVALID_REFERENCE, f"{label} must be a non-empty string")


def _require_cell(value: Any, label: str) -> None:
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or any(type(axis) is not int for axis in value)
    ):
        raise ReferenceError(INVALID_REFERENCE, f"{label} must be an integer pair")


def _describe(reference: QualifiedRef) -> str:
    parts = [reference.domain]
    if reference.map_id is not None:
        parts.append(reference.map_id)
    if reference.object_id is not None:
        parts.append(reference.object_id)
    if reference.cell is not None:
        parts.append(f"{reference.cell[0]},{reference.cell[1]}")
    return ":".join(parts)


def _with_source(message: str, source: str) -> str:
    return f"{source}: {message}" if source else message


def _other_domain(index: ReferenceIndex, reference: QualifiedRef) -> str | None:
    object_id = reference.object_id
    if object_id is None:
        return None
    if reference.domain != "location" and object_id in index.locations:
        return "location"
    if reference.domain != "settlement_node" and any(
        object_id in nodes for nodes in index.settlement_nodes.values()
    ):
        return "settlement_node"
    if reference.domain != "interior_room" and any(
        object_id in rooms for rooms in index.interior_rooms.values()
    ):
        return "interior_room"
    return None


def _missing(
    index: ReferenceIndex, reference: QualifiedRef, source: str, reason: str
) -> ReferenceError:
    other = _other_domain(index, reference)
    if other is not None:
        return ReferenceError(
            WRONG_DOMAIN,
            _with_source(
                f"{_describe(reference)} is not an authored {reference.domain}; "
                f"the identity is an authored {other}",
                source,
            ),
        )
    return ReferenceError(UNKNOWN_REFERENCE, _with_source(reason, source))


def resolve_reference(
    world: ReferenceWorld,
    reference: QualifiedRef,
    *,
    source: str = "",
) -> ResolvedReference:
    """Resolve one qualified reference against ``world``'s current bindings.

    ``source`` names the declaring object (a gate row, place, district, ...)
    so a rejection identifies both target and source. Domain eligibility is the
    caller's policy: a consumer that needs a settlement node calls
    :func:`settlement_position` (or checks ``domain`` itself) instead of
    accepting whatever domain happens to resolve.
    """

    index = world.reference_index
    if not isinstance(reference, QualifiedRef):
        raise ReferenceError(
            INVALID_REFERENCE,
            _with_source(
                f"{reference!r} is not a qualified reference",
                source,
            ),
        )

    domain = reference.domain
    if domain not in QUALIFIED_REF_DOMAINS or domain not in _DOMAIN_FIELDS:
        raise ReferenceError(
            UNKNOWN_DOMAIN,
            _with_source(
                f"{_describe(reference)}: domain {domain!r} is not one of "
                f"{QUALIFIED_REF_DOMAINS}",
                source,
            ),
        )

    needs_map, needs_object, needs_cell = _DOMAIN_FIELDS[domain]
    if needs_map and reference.map_id is None:
        raise ReferenceError(
            INVALID_REFERENCE,
            _with_source(f"{domain} requires a map scope", source),
        )
    if not needs_map and reference.map_id is not None:
        raise ReferenceError(
            INVALID_REFERENCE,
            _with_source(f"{domain} takes no map scope", source),
        )
    if needs_object and reference.object_id is None:
        raise ReferenceError(
            INVALID_REFERENCE,
            _with_source(f"{domain} requires an object id", source),
        )
    if not needs_object and reference.object_id is not None:
        raise ReferenceError(
            INVALID_REFERENCE,
            _with_source(f"{domain} takes no object id", source),
        )
    if needs_cell and reference.cell is None:
        raise ReferenceError(
            INVALID_REFERENCE,
            _with_source(f"{domain} requires an explicit cell", source),
        )
    if not needs_cell and reference.cell is not None:
        raise ReferenceError(
            INVALID_REFERENCE,
            _with_source(f"{domain} takes no explicit cell", source),
        )

    if domain == "settlement_node":
        map_id = reference.map_id or ""
        object_id = reference.object_id or ""
        nodes = index.settlement_nodes.get(map_id)
        if nodes is None:
            raise _missing(
                index,
                reference,
                source,
                f"{_describe(reference)}: no authored settlement {map_id!r}",
            )
        position = nodes.get(object_id)
        if position is None:
            raise _missing(
                index,
                reference,
                source,
                f"{_describe(reference)}: no authored node {object_id!r} "
                f"in settlement {map_id!r}",
            )
        return ResolvedReference(reference, position_m=tuple(position))

    if domain == "interior_room":
        map_id = reference.map_id or ""
        object_id = reference.object_id or ""
        rooms = index.interior_rooms.get(map_id)
        if rooms is None:
            raise _missing(
                index,
                reference,
                source,
                f"{_describe(reference)}: no authored interior {map_id!r}",
            )
        if object_id not in rooms:
            raise _missing(
                index,
                reference,
                source,
                f"{_describe(reference)}: no authored room {object_id!r} "
                f"in interior {map_id!r}",
            )
        return ResolvedReference(reference)

    if domain == "location":
        object_id = reference.object_id or ""
        cell = index.locations.get(object_id)
        if cell is None:
            raise _missing(
                index,
                reference,
                source,
                f"{_describe(reference)}: no authored location {object_id!r}",
            )
        return ResolvedReference(reference, cell=tuple(cell))

    cell = reference.cell
    assert cell is not None  # shape checked above
    if index.frame_cells is not None and not is_within_frame(index.frame_cells, cell):
        raise ReferenceError(
            INVALID_REFERENCE,
            _with_source(
                f"{_describe(reference)}: cell is outside the "
                f"{index.frame_cells}-cell frame",
                source,
            ),
        )
    return ResolvedReference(reference, cell=tuple(cell))


def settlement_position(
    world: ReferenceWorld, reference: QualifiedRef, *, source: str = ""
) -> Cell:
    """Resolve a reference that a consumer requires to be a settlement node."""

    if not isinstance(reference, QualifiedRef) or reference.domain != "settlement_node":
        raise ReferenceError(
            WRONG_DOMAIN,
            _with_source(
                f"{reference!r} is not a settlement_node reference",
                source,
            ),
        )
    resolved = resolve_reference(world, reference, source=source)
    assert resolved.position_m is not None
    return resolved.position_m


def settlement_node_ref(map_id: str, object_id: str) -> QualifiedRef:
    return QualifiedRef(domain="settlement_node", map_id=map_id, object_id=object_id)


def interior_room_ref(interior_id: str, object_id: str) -> QualifiedRef:
    return QualifiedRef(domain="interior_room", map_id=interior_id, object_id=object_id)


def location_ref(object_id: str) -> QualifiedRef:
    return QualifiedRef(domain="location", object_id=object_id)


def wilderness_cell_ref(cell: Cell) -> QualifiedRef:
    return QualifiedRef(domain="wilderness_cell", cell=(cell[0], cell[1]))


__all__ = [
    "DUPLICATE_REFERENCE",
    "INVALID_REFERENCE",
    "ReferenceError",
    "ReferenceIndex",
    "ReferenceWorld",
    "ResolvedReference",
    "UNKNOWN_DOMAIN",
    "UNKNOWN_REFERENCE",
    "WRONG_DOMAIN",
    "interior_room_ref",
    "location_ref",
    "resolve_reference",
    "settlement_node_ref",
    "settlement_position",
    "wilderness_cell_ref",
]
