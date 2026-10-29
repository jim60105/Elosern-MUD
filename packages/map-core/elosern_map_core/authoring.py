"""Authoring load, work-in-progress diagnostics and runtime acceptance.

Two gates are deliberately distinct:

* :func:`load_authoring_world` accepts a structurally complete candidate even
  when the map is unfinished, and records semantic work-in-progress
  diagnostics (empty graph, unreachable landmark, blocked approach).
* :func:`compile_runtime` builds the route/provider-facing snapshot only after
  the authored world has no diagnostics, the caller supplied an authoritative
  game-side external result for *this* world, and the required partition
  artifact is current for *this* input.

The module reads only explicit inputs: source documents, an external result
value and a freshness value. It never imports a game module, watches files or
writes anything.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .codec import parse_document
from .diagnostics import (
    ERROR,
    EXTERNAL,
    FRESHNESS,
    SEMANTIC,
    STRUCTURE,
    WARNING,
    AuthoringError,
    Diagnostic,
    RuntimeRejection,
    blocking,
    sorted_diagnostics,
)
from .documents import (
    AuthoringDocument,
    ContinentDocument,
    DistrictsDocument,
    InteriorDocument,
    LocationsDocument,
    SettlementDocument,
    WildernessEntryGeometry,
)
from .geometry import is_within_frame
from .sources import SourceDocument, fingerprint_text, is_world_source
from .sparse import (
    SparseGraphError,
    SparseNode,
    SparseRoad,
    SparseSettlementGraph,
    polyline_length,
)
from .partition_codec import (
    PARTITION_ALGORITHM_VERSION,
    PARTITION_SOURCE_KINDS,
    PartitionFreshness,
    partition_source_signature,
)
from .references import (
    ReferenceError,
    ReferenceIndex,
    resolve_reference,
)
from .terrain import (
    REGION_KEYS,
    TerrainDefinition,
    is_walkable_cell,
)

EXTERNAL_RESULT_VERSION = 1
WORLD_SOURCE_KINDS = frozenset({"continent", "locations", "districts", "settlement", "interior"})
_OPPOSITE_DIRECTION = {
    "n": "s",
    "s": "n",
    "e": "w",
    "w": "e",
    "ne": "sw",
    "sw": "ne",
    "nw": "se",
    "se": "nw",
}
_DIRECTION_DELTAS = {
    "n": (0, 1),
    "ne": (1, 1),
    "e": (1, 0),
    "se": (1, -1),
    "s": (0, -1),
    "sw": (-1, -1),
    "w": (-1, 0),
    "nw": (-1, 1),
}


def location_cells_of(
    locations: LocationsDocument | Mapping[str, Any] | None,
) -> dict[str, tuple[int, int]]:
    """Every authored location's cell, from a document or a raw mapping.

    A settlement owns no geographic coordinate: its frame and its wilderness
    entry resolve against the cell this returns for its ``location_ref``.
    Only a real integer pair is accepted -- nothing is coerced -- and a row
    without one is left out here so that :func:`diagnose_settlement_structure`
    can report it instead of geometry silently disappearing.
    """

    if locations is None:
        return {}
    rows = getattr(locations, "locations", locations)
    cells: dict[str, tuple[int, int]] = {}
    for key, value in rows.items():
        cell = getattr(value, "cell", None)
        if cell is None and isinstance(value, Mapping):
            raw = value.get("cell")
            if isinstance(raw, Mapping):
                cell = (raw.get("cell_x"), raw.get("cell_y"))
        if cell is None or len(cell) != 2:
            continue
        if not all(isinstance(item, int) and not isinstance(item, bool) for item in cell):
            continue
        cells[str(key)] = (cell[0], cell[1])
    return cells


def _entry_geometries(
    settlements: Mapping[str, SettlementDocument],
    location_cells: Mapping[str, tuple[int, int]],
) -> dict[str, WildernessEntryGeometry]:
    """Each settlement's absolute entry geometry, for the locations it names."""

    geometries: dict[str, WildernessEntryGeometry] = {}
    for settlement_id, settlement in settlements.items():
        entry = settlement.wilderness_entry
        location_cell = location_cells.get(settlement.location_ref)
        if entry is None or location_cell is None:
            continue
        geometries[settlement_id] = entry.geometry(location_cell)
    return geometries


def diagnose_settlement_structure(
    settlements: Mapping[str, SettlementDocument],
    locations: LocationsDocument | Mapping[str, Any] | None = None,
) -> list[Diagnostic]:
    """Structure diagnostics for settlement documents (rejection on load/mutation)."""
    diagnostics: list[Diagnostic] = []
    bound_locations: dict[str, str] = {}
    seen_destinations: dict[tuple[str, str], tuple[str, str]] = {}
    cells = location_cells_of(locations)

    for settlement_id, settlement in sorted(settlements.items()):
        if locations is not None:
            loc_keys = set(locations.locations) if hasattr(locations, "locations") else set(locations)
            if settlement.location_ref not in loc_keys:
                diagnostics.append(
                    _diagnostic(
                        "unknown_reference",
                        STRUCTURE,
                        f"location_ref {settlement.location_ref!r} is not an authored location",
                        document=settlement,
                        field_path="location_ref",
                        object_id=settlement_id,
                    )
                )
            elif settlement.location_ref not in cells:
                # A location without a usable integer cell cannot place the
                # settlement; say so instead of silently dropping its geometry.
                diagnostics.append(
                    _diagnostic(
                        "invalid_field_value",
                        STRUCTURE,
                        f"location {settlement.location_ref!r} declares no integer cell, "
                        "so the settlement cannot be placed",
                        document=settlement,
                        field_path="location_ref",
                        object_id=settlement_id,
                    )
                )
        if settlement.location_ref in bound_locations:
            first_id = bound_locations[settlement.location_ref]
            diagnostics.append(
                _diagnostic(
                    "duplicate_location_binding",
                    STRUCTURE,
                    f"settlement {settlement_id!r} binds location {settlement.location_ref!r} "
                    f"already bound by {first_id!r}",
                    document=settlement,
                    field_path="location_ref",
                    object_id=settlement_id,
                )
            )
        else:
            bound_locations[settlement.location_ref] = settlement_id

        anchor_nodes = [
            n for n in settlement.nodes.values()
            if n.prototype_parent == "anchor_room"
        ]
        if len(anchor_nodes) > 1:
            diagnostics.append(
                _diagnostic(
                    "multiple_anchor_rooms",
                    STRUCTURE,
                    f"settlement {settlement_id!r} declares {len(anchor_nodes)} anchor_room nodes, "
                    "expected at most one",
                    document=settlement,
                    field_path="nodes",
                    object_id=settlement_id,
                )
            )
        elif len(anchor_nodes) == 1:
            anchor = anchor_nodes[0]
            if anchor.anchor_key != settlement.location_ref:
                diagnostics.append(
                    _diagnostic(
                        "anchor_location_mismatch",
                        STRUCTURE,
                        f"settlement {settlement_id!r} anchor node {anchor.node_id!r} "
                        f"declares anchor_key {anchor.anchor_key!r}, expected location_ref {settlement.location_ref!r}",
                        document=settlement,
                        field_path="nodes",
                        object_id=settlement_id,
                    )
                )

        entry = settlement.wilderness_entry
        if entry is not None:
            for gate in entry.gates:
                target_room = (settlement_id, gate.destination_node)
                if target_room in seen_destinations:
                    first_id, first_dir = seen_destinations[target_room]
                    diagnostics.append(
                        _diagnostic(
                            "duplicate_gate_destination",
                            STRUCTURE,
                            f"settlement {settlement_id!r} gate {gate.return_direction!r} "
                            f"shares destination room {target_room!r} with {first_id!r} gate {first_dir!r}",
                            document=settlement,
                            field_path="wilderness_entry.gates",
                            object_id=settlement_id,
                        )
                    )
                else:
                    seen_destinations[target_room] = (settlement_id, gate.return_direction)

    return diagnostics


def diagnose_interior_structure(
    interiors: Mapping[str, InteriorDocument],
) -> list[Diagnostic]:
    """Structure diagnostics for interior documents (rejection on load/mutation)."""
    diagnostics: list[Diagnostic] = []
    seen_rooms: dict[str, str] = {}
    doorway_owners: dict[tuple[str, str, str], str] = {}

    for interior_id, interior in sorted(interiors.items()):
        for room_id in sorted(interior.rooms):
            if room_id in seen_rooms:
                first_id = seen_rooms[room_id]
                diagnostics.append(
                    _diagnostic(
                        "duplicate_interior_room",
                        STRUCTURE,
                        f"room {room_id!r} is declared by interior {first_id!r} and interior {interior_id!r}; "
                        "a persistent room has one identity",
                        document=interior,
                        field_path="rooms",
                        object_id=interior_id,
                    )
                )
            else:
                seen_rooms[room_id] = interior_id

        exterior = interior.exterior
        if exterior is not None:
            key = (exterior.settlement, exterior.node, exterior.doorway_key)
            if key in doorway_owners:
                first_id = doorway_owners[key]
                diagnostics.append(
                    _diagnostic(
                        "duplicate_doorway",
                        STRUCTURE,
                        f"interiors {first_id!r} and {interior_id!r} both declare doorway {exterior.doorway_key!r} "
                        f"on exterior {exterior.node!r} of {exterior.settlement!r}; two interiors on one exterior "
                        "must name their doorways differently",
                        document=interior,
                        field_path="exterior.doorway_key",
                        object_id=interior_id,
                    )
                )
            else:
                doorway_owners[key] = interior_id

    return diagnostics


def diagnose_settlement_semantics(
    settlements: Mapping[str, SettlementDocument],
    *,
    locations: LocationsDocument | Mapping[str, Any] | None = None,
    frame_cells: int | None = None,
    terrain: TerrainDefinition | None = None,
) -> list[Diagnostic]:
    """Semantic diagnostics for settlement documents (saveable WIP, rejected by runtime/game)."""
    diagnostics: list[Diagnostic] = []
    location_cells = location_cells_of(locations)
    geometries = _entry_geometries(settlements, location_cells)

    for settlement_id, settlement in sorted(settlements.items()):
        anchor_nodes = [
            n for n in settlement.nodes.values()
            if n.prototype_parent == "anchor_room"
        ]
        if not anchor_nodes:
            diagnostics.append(
                _diagnostic(
                    "missing_anchor_room",
                    SEMANTIC,
                    f"settlement {settlement_id!r} declares no anchor_room node",
                    document=settlement,
                    field_path="nodes",
                    object_id=settlement_id,
                )
            )

    all_footprints: dict[str, frozenset[tuple[int, int]]] = {}
    point_anchors: dict[str, tuple[int, int]] = {}

    for settlement_id, settlement in sorted(settlements.items()):
        geometry = geometries.get(settlement_id)
        if geometry is None:
            continue

        all_footprints[settlement_id] = geometry.footprint_cells
        if geometry.is_point_shape and geometry.anchor_cell is not None:
            point_anchors[settlement_id] = geometry.anchor_cell

        if geometry.is_point_shape:
            if len(geometry.gates) > 1:
                diagnostics.append(
                    _diagnostic(
                        "point_gate_count",
                        SEMANTIC,
                        f"settlement {settlement_id!r} point-shape entry must have exactly one gate, "
                        f"found {len(geometry.gates)}",
                        document=settlement,
                        field_path="wilderness_entry.gates",
                        object_id=settlement_id,
                    )
                )
        else:
            cells = geometry.footprint_cells
            if cells:
                start = next(iter(cells))
                seen = {start}
                queue = [start]
                while queue:
                    cx, cy = queue.pop()
                    for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                        nxt = (cx + dx, cy + dy)
                        if nxt in cells and nxt not in seen:
                            seen.add(nxt)
                            queue.append(nxt)
                if seen != set(cells):
                    diagnostics.append(
                        _diagnostic(
                            "disconnected_footprint",
                            SEMANTIC,
                            f"settlement {settlement_id!r} footprint '#' cells are not 4-connected",
                            document=settlement,
                            field_path="wilderness_entry.shape",
                            object_id=settlement_id,
                        )
                    )

            anchor_cell = geometry.anchor_cell
            if anchor_cell is not None and anchor_cell not in cells:
                diagnostics.append(
                    _diagnostic(
                        "invalid_footprint_anchor",
                        SEMANTIC,
                        f"settlement {settlement_id!r} anchor_cell {anchor_cell} is not a '#' footprint cell",
                        document=settlement,
                        field_path="wilderness_entry.shape",
                        object_id=settlement_id,
                    )
                )

        for cell in sorted(geometry.mask_cells):
            if frame_cells is not None and not is_within_frame(frame_cells, cell):
                diagnostics.append(
                    _diagnostic(
                        "invalid_footprint_cell",
                        SEMANTIC,
                        f"settlement {settlement_id!r} footprint cell {cell} is outside the frame",
                        document=settlement,
                        field_path="wilderness_entry.shape",
                        object_id=settlement_id,
                    )
                )
            elif terrain is not None and not is_walkable_cell(terrain, cell):
                diagnostics.append(
                    _diagnostic(
                        "invalid_footprint_cell",
                        SEMANTIC,
                        f"settlement {settlement_id!r} footprint cell {cell} is not walkable terrain",
                        document=settlement,
                        field_path="wilderness_entry.shape",
                        object_id=settlement_id,
                    )
                )

    for sid, fp in sorted(all_footprints.items()):
        if not fp:
            continue
        for other_sid, other_fp in sorted(all_footprints.items()):
            if other_sid > sid and fp & other_fp:
                diagnostics.append(
                    _diagnostic(
                        "overlapping_footprint",
                        SEMANTIC,
                        f"settlement {sid!r} footprint overlaps {other_sid!r}",
                        document=settlements[sid],
                        field_path="wilderness_entry.shape",
                        object_id=sid,
                    )
                )
        for other_sid, point_cell in sorted(point_anchors.items()):
            if other_sid != sid and point_cell in fp:
                diagnostics.append(
                    _diagnostic(
                        "overlapping_footprint",
                        SEMANTIC,
                        f"settlement {sid!r} footprint contains point anchor of {other_sid!r}",
                        document=settlements[sid],
                        field_path="wilderness_entry.shape",
                        object_id=sid,
                    )
                )

    for settlement_id, geometry in sorted(geometries.items()):
        anchor_cell = geometry.anchor_cell
        location_cell = location_cells.get(settlements[settlement_id].location_ref)
        if anchor_cell is None or location_cell is None or anchor_cell == location_cell:
            continue
        if not geometry.is_point_shape and anchor_cell not in geometry.footprint_cells:
            # The mask is already diagnosed; an advisory about its midpoint
            # would name a disagreement the reader cannot act on yet.
            continue
        diagnostics.append(
            _diagnostic(
                "footprint_location_offset",
                SEMANTIC,
                f"settlement {settlement_id!r} footprint midpoint {anchor_cell} is not "
                f"its location cell {location_cell}; the world-map marker and the "
                "wilderness entrance are in different places (advisory)",
                document=settlements[settlement_id],
                field_path="wilderness_entry.offset",
                object_id=settlement_id,
                severity=WARNING,
            )
        )

    seen_gate_keys: dict[tuple[tuple[int, int], str], str] = {}
    for sid, settlement in sorted(settlements.items()):
        geometry = geometries.get(sid)
        if geometry is None:
            continue
        for gate in geometry.gates:
            approach = gate_approach_cell(geometry, gate.return_direction, frame_cells=frame_cells)
            if approach is None:
                diagnostics.append(
                    _diagnostic(
                        "invalid_gate_approach",
                        SEMANTIC,
                        f"settlement {sid!r} gate {gate.return_direction!r} approach cell is undefined: "
                        "its face ray crosses no footprint cell or never lands inside the frame",
                        document=settlement,
                        field_path="wilderness_entry.gates",
                        object_id=sid,
                    )
                )
                continue

            gate_key = (approach, gate.return_direction)
            if gate_key in seen_gate_keys:
                first_sid = seen_gate_keys[gate_key]
                diagnostics.append(
                    _diagnostic(
                        "duplicate_gate_approach",
                        SEMANTIC,
                        f"settlement {sid!r} gate {gate.return_direction!r} collides on "
                        f"(approach_cell, return_direction) {gate_key} with {first_sid!r}",
                        document=settlement,
                        field_path="wilderness_entry.gates",
                        object_id=sid,
                    )
                )
            else:
                seen_gate_keys[gate_key] = sid

            if not geometry.is_point_shape:
                for other_sid, other_fp in sorted(all_footprints.items()):
                    if other_sid != sid and approach in other_fp:
                        diagnostics.append(
                            _diagnostic(
                                "gate_approach_collision",
                                SEMANTIC,
                                f"settlement {sid!r} gate {gate.return_direction!r} approach cell {approach} "
                                f"lies inside footprint of {other_sid!r}",
                                document=settlement,
                                field_path="wilderness_entry.gates",
                                object_id=sid,
                            )
                        )
                if terrain is not None and not is_walkable_cell(terrain, approach):
                    diagnostics.append(
                        _diagnostic(
                            "blocked_approach",
                            SEMANTIC,
                            f"settlement {sid!r} gate {gate.return_direction!r} approach "
                            f"{approach!r} is not walkable wilderness",
                            document=settlement,
                            field_path="wilderness_entry.gates",
                            object_id=sid,
                        )
                    )

            for other_sid, point_cell in sorted(point_anchors.items()):
                if other_sid != sid and approach == point_cell:
                    diagnostics.append(
                        _diagnostic(
                            "gate_approach_collision",
                            SEMANTIC,
                            f"settlement {sid!r} gate {gate.return_direction!r} approach {approach} "
                            f"is the point anchor of {other_sid!r}",
                            document=settlement,
                            field_path="wilderness_entry.gates",
                            object_id=sid,
                        )
                    )

            if geometry.is_point_shape and geometry.anchor_cell is not None:
                delta = _DIRECTION_DELTAS.get(gate.return_direction)
                if delta is None:
                    continue
                dx, dy = delta
                neighbor = (geometry.anchor_cell[0] + dx, geometry.anchor_cell[1] + dy)
                neighbor_invalid = False
                reason = ""
                if frame_cells is not None and not is_within_frame(frame_cells, neighbor):
                    neighbor_invalid = True
                    reason = "outside frame"
                elif terrain is not None and not is_walkable_cell(terrain, neighbor):
                    neighbor_invalid = True
                    reason = "not walkable terrain"
                elif any(neighbor in other_fp for other_fp in all_footprints.values()):
                    neighbor_invalid = True
                    reason = "inside a footprint"

                if neighbor_invalid:
                    diagnostics.append(
                        _diagnostic(
                            "blocked_point_neighbor",
                            SEMANTIC,
                            f"settlement {sid!r} point anchor {geometry.anchor_cell} has invalid neighbor "
                            f"{neighbor} ({reason}) in its entry direction {gate.return_direction!r}",
                            document=settlement,
                            field_path="wilderness_entry.gates",
                            object_id=sid,
                        )
                    )

    return diagnostics


def diagnose_settlement_rules(
    settlements: Mapping[str, SettlementDocument],
    *,
    locations: LocationsDocument | Mapping[str, Any] | None = None,
    frame_cells: int | None = None,
    terrain: TerrainDefinition | None = None,
) -> list[Diagnostic]:
    """All shared structure and semantic diagnostics for settlement documents."""
    return (
        diagnose_settlement_structure(settlements, locations=locations)
        + diagnose_settlement_semantics(
            settlements,
            locations=locations,
            frame_cells=frame_cells,
            terrain=terrain,
        )
    )


def diagnose_interior_rules(
    interiors: Mapping[str, InteriorDocument],
) -> list[Diagnostic]:
    """All shared structure diagnostics for interior documents."""
    return diagnose_interior_structure(interiors)


@dataclass(frozen=True, slots=True)
class AuthoritativeExternalResult:
    """The game-side authoritative static-reference check for one world.

    ``fingerprint`` is opaque game-side evidence; ``world_fingerprint`` binds
    that evidence to the exact authored source set it was produced against.
    """

    version: int
    fingerprint: str
    world_fingerprint: str
    valid: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class AuthoringWorld:
    """A structurally complete, loadable authored world (may be unfinished)."""

    continent: ContinentDocument
    locations: LocationsDocument
    districts: DistrictsDocument
    settlements: Mapping[str, SettlementDocument]
    interiors: Mapping[str, InteriorDocument]
    documents: tuple[AuthoringDocument, ...]
    fingerprints: Mapping[str, str]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def reference_index(self) -> ReferenceIndex:
        """The current bindings every authored static target resolves against."""

        return ReferenceIndex.from_documents(
            settlements=self.settlements,
            interiors=self.interiors,
            locations=self.locations,
            frame_cells=self.continent.terrain.frame_cells,
        )

    @property
    def fingerprint(self) -> str:
        return _combined_fingerprint(self.documents)

    @property
    def partition_signature(self) -> str:
        return partition_source_signature(self.documents)


@dataclass(frozen=True, slots=True)
class RuntimeMapSnapshot:
    """The immutable runtime surface; only a fully accepted world reaches it."""

    fingerprint: str
    external_fingerprint: str
    partition_signature: str
    partition_algorithm_version: int
    continent: ContinentDocument
    locations: LocationsDocument
    districts: DistrictsDocument
    settlements: Mapping[str, SparseSettlementGraph]
    interiors: Mapping[str, InteriorDocument]


def _combined_fingerprint(documents: Iterable[AuthoringDocument]) -> str:
    digest = hashlib.sha256()
    for document in sorted(documents, key=lambda item: item.relative_path):
        digest.update(document.relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(document.fingerprint.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _diagnostic(
    code: str,
    category: str,
    message: str,
    *,
    document: AuthoringDocument | None = None,
    field_path: str = "",
    relative_path: str | None = None,
    object_id: str | None = None,
    severity: str = ERROR,
) -> Diagnostic:
    location = None
    if document is not None:
        relative_path = document.relative_path
        location = document.provenance.get(field_path)
    return Diagnostic(
        code=code,
        category=category,
        message=message,
        relative_path=relative_path,
        field_path=field_path,
        line=location.line if location else None,
        column=location.column if location else None,
        object_id=object_id,
        severity=severity,
    )


def _check_envelope(
    source: SourceDocument,
) -> tuple[tuple[Diagnostic, ...], Any | None]:
    """Validate a source's path and fingerprint, then parse it."""

    if not is_world_source(source.relative_path):
        return (
            (
                _diagnostic(
                    "unsupported_source_path",
                    STRUCTURE,
                    f"{source.relative_path!r} is not a supported world source",
                    relative_path=source.relative_path,
                ),
            ),
            None,
        )
    if source.fingerprint and source.fingerprint != fingerprint_text(source.text):
        return (
            (
                _diagnostic(
                    "fingerprint_mismatch",
                    STRUCTURE,
                    f"{source.relative_path} does not match its supplied fingerprint",
                    relative_path=source.relative_path,
                ),
            ),
            None,
        )
    try:
        return (), parse_document(source.relative_path, source.text)
    except AuthoringError as error:
        return tuple(error.diagnostics), None


def load_authoring_world(source_documents: Iterable[SourceDocument]) -> AuthoringWorld:
    """Load and validate one complete authored world candidate."""

    sources = tuple(source_documents)
    diagnostics: list[Diagnostic] = []
    seen_paths: set[str] = set()
    parsed_by_kind: dict[str, list[Any]] = {}
    documents: list[AuthoringDocument] = []
    source_fingerprints: dict[str, str] = {}

    for source in sorted(sources, key=lambda item: item.relative_path):
        normalised = source.relative_path.replace("\\", "/")
        if normalised in seen_paths:
            diagnostics.append(
                _diagnostic(
                    "duplicate_source_path",
                    STRUCTURE,
                    f"{normalised} is supplied more than once",
                    relative_path=normalised,
                )
            )
            continue
        seen_paths.add(normalised)
        source_diagnostics, parsed = _check_envelope(source)
        diagnostics.extend(source_diagnostics)
        if parsed is None:
            continue
        parsed_by_kind.setdefault(parsed.kind, []).append(parsed)
        documents.append(parsed.document)
        source_fingerprints[normalised] = source.fingerprint or fingerprint_text(
            source.text
        )

    for kind in ("continent", "locations", "districts"):
        entries = parsed_by_kind.get(kind, [])
        if not entries:
            diagnostics.append(
                _diagnostic(
                    "missing_document",
                    STRUCTURE,
                    f"the required {kind} document is absent",
                    relative_path=None,
                )
            )
        elif len(entries) > 1:
            diagnostics.append(
                _diagnostic(
                    "duplicate_document_identity",
                    STRUCTURE,
                    f"more than one {kind} document is present",
                    relative_path=entries[1].relative_path,
                )
            )
    for kind in ("settlement", "interior"):
        identifiers: dict[str, str] = {}
        for parsed in parsed_by_kind.get(kind, []):
            previous = identifiers.get(parsed.identity)
            if previous is not None:
                diagnostics.append(
                    _diagnostic(
                        "duplicate_document_identity",
                        STRUCTURE,
                        f"{kind} identity {parsed.identity!r} is declared by "
                        f"{previous} and {parsed.relative_path}",
                        relative_path=parsed.relative_path,
                        field_path="id",
                        object_id=parsed.identity,
                    )
                )
            else:
                identifiers[parsed.identity] = parsed.relative_path

    if diagnostics:
        raise AuthoringError(sorted_diagnostics(diagnostics))

    continent: ContinentDocument = parsed_by_kind["continent"][0].document
    locations: LocationsDocument = parsed_by_kind["locations"][0].document
    districts: DistrictsDocument = parsed_by_kind["districts"][0].document
    settlements = MappingProxyType(
        {
            parsed.identity: parsed.document
            for parsed in parsed_by_kind.get("settlement", [])
        }
    )
    interiors = MappingProxyType(
        {
            parsed.identity: parsed.document
            for parsed in parsed_by_kind.get("interior", [])
        }
    )

    diagnostics.extend(_structural_diagnostics(continent, locations, districts, settlements, interiors))
    if diagnostics:
        raise AuthoringError(sorted_diagnostics(diagnostics))

    fingerprints = MappingProxyType(dict(source_fingerprints))
    world = AuthoringWorld(
        continent=continent,
        locations=locations,
        districts=districts,
        settlements=settlements,
        interiors=interiors,
        documents=tuple(sorted(documents, key=lambda item: item.relative_path)),
        fingerprints=fingerprints,
        diagnostics=(),
    )
    diagnostics.extend(_semantic_diagnostics(world))
    return AuthoringWorld(
        continent=continent,
        locations=locations,
        districts=districts,
        settlements=settlements,
        interiors=interiors,
        documents=world.documents,
        fingerprints=fingerprints,
        diagnostics=sorted_diagnostics(diagnostics),
    )


def _structural_diagnostics(
    continent: ContinentDocument,
    locations: LocationsDocument,
    districts: DistrictsDocument,
    settlements: Mapping[str, SettlementDocument],
    interiors: Mapping[str, InteriorDocument],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    missing_regions = sorted(REGION_KEYS - set(continent.regions))
    if missing_regions:
        diagnostics.append(
            _diagnostic(
                "missing_region",
                STRUCTURE,
                f"the continent declares no terrain region for {missing_regions}",
                document=continent,
                field_path="regions",
            )
        )

    for settlement_id, settlement in settlements.items():
        node_ids = set(settlement.nodes)
        for road in settlement.roads:
            for field, endpoint in (
                ("source", road.source),
                ("destination", road.destination),
            ):
                if endpoint not in node_ids:
                    diagnostics.append(
                        _diagnostic(
                            "unknown_node",
                            STRUCTURE,
                            f"road endpoint {endpoint!r} is not an authored node",
                            document=settlement,
                            field_path=f"roads[{field}]",
                            object_id=settlement_id,
                        )
                    )
            if road.source == road.destination:
                diagnostics.append(
                    _diagnostic(
                        "self_loop",
                        STRUCTURE,
                        f"road {road.source!r} -> {road.destination!r} is a self-loop",
                        document=settlement,
                        field_path="roads",
                        object_id=settlement_id,
                    )
                )
        if settlement.city_gate is not None and settlement.city_gate.node not in node_ids:
            diagnostics.append(
                _diagnostic(
                    "unknown_node",
                    STRUCTURE,
                    f"city_gate.node {settlement.city_gate.node!r} is not an authored node",
                    document=settlement,
                    field_path="city_gate.node",
                    object_id=settlement_id,
                )
            )
        entry = settlement.wilderness_entry
        if entry is not None:
            seen_directions: set[str] = set()
            for gate in entry.gates:
                if gate.destination_node not in node_ids:
                    diagnostics.append(
                        _diagnostic(
                            "unknown_node",
                            STRUCTURE,
                            f"gate destination {gate.destination_node!r} is not an authored node",
                            document=settlement,
                            field_path="wilderness_entry.gates.destination_node",
                            object_id=settlement_id,
                        )
                    )
                if gate.return_direction in seen_directions:
                    diagnostics.append(
                        _diagnostic(
                            "duplicate_gate_direction",
                            STRUCTURE,
                            f"gate direction {gate.return_direction!r} is declared twice",
                            document=settlement,
                            field_path="wilderness_entry.gates",
                            object_id=settlement_id,
                        )
                    )
                seen_directions.add(gate.return_direction)

    diagnostics.extend(diagnose_settlement_structure(settlements, locations))
    diagnostics.extend(diagnose_interior_structure(interiors))

    reference_index = ReferenceIndex.from_documents(
        settlements=settlements,
        interiors=interiors,
        locations=locations,
        frame_cells=continent.terrain.frame_cells,
    )
    for district_id, district in districts.districts.items():
        if district.kind == "region" and district.region_key not in continent.regions:
            diagnostics.append(
                _diagnostic(
                    "unknown_reference",
                    STRUCTURE,
                    f"region_key {district.region_key!r} is not an authored region",
                    document=districts,
                    field_path=f"districts.{district_id}.region_key",
                    object_id=district_id,
                )
            )
        try:
            resolve_reference(
                reference_index,
                district.landmark,
                source=f"district {district_id}",
            )
        except ReferenceError as error:
            diagnostics.append(
                _diagnostic(
                    error.code,
                    STRUCTURE,
                    str(error),
                    document=districts,
                    field_path=f"districts.{district_id}.landmark",
                    object_id=district_id,
                )
            )

    for interior_id, interior in interiors.items():
        room_ids = set(interior.rooms)
        for connection in interior.connections:
            for endpoint in (connection.source, connection.destination):
                if endpoint not in room_ids:
                    diagnostics.append(
                        _diagnostic(
                            "unknown_reference",
                            STRUCTURE,
                            f"connection endpoint {endpoint!r} is not an authored room",
                            document=interior,
                            field_path="connections",
                            object_id=interior_id,
                        )
                    )
        for link in interior.interior_links:
            if link.source_room not in room_ids:
                diagnostics.append(
                    _diagnostic(
                        "unknown_reference",
                        STRUCTURE,
                        f"link source {link.source_room!r} is not an authored room",
                        document=interior,
                        field_path="interior_links",
                        object_id=interior_id,
                    )
                )
            target = interiors.get(link.target_interior)
            if target is None:
                diagnostics.append(
                    _diagnostic(
                        "unknown_reference",
                        STRUCTURE,
                        f"link target interior {link.target_interior!r} is not authored",
                        document=interior,
                        field_path="interior_links",
                        object_id=interior_id,
                    )
                )
            elif link.target_room not in target.rooms:
                diagnostics.append(
                    _diagnostic(
                        "unknown_reference",
                        STRUCTURE,
                        f"link target room {link.target_room!r} is not authored in "
                        f"{link.target_interior!r}",
                        document=interior,
                        field_path="interior_links",
                        object_id=interior_id,
                    )
                )
        if interior.exterior is not None:
            if interior.exterior.room not in room_ids:
                diagnostics.append(
                    _diagnostic(
                        "unknown_reference",
                        STRUCTURE,
                        f"exterior room {interior.exterior.room!r} is not an "
                        f"authored room of {interior_id!r}",
                        document=interior,
                        field_path="exterior.room",
                        object_id=interior_id,
                    )
                )
            settlement = settlements.get(interior.exterior.settlement)
            if settlement is None:
                diagnostics.append(
                    _diagnostic(
                        "unknown_reference",
                        STRUCTURE,
                        f"exterior settlement {interior.exterior.settlement!r} is not authored",
                        document=interior,
                        field_path="exterior.settlement",
                        object_id=interior_id,
                    )
                )
            elif interior.exterior.node not in settlement.nodes:
                diagnostics.append(
                    _diagnostic(
                        "unknown_reference",
                        STRUCTURE,
                        f"exterior node {interior.exterior.node!r} is not authored in "
                        f"{interior.exterior.settlement!r}",
                        document=interior,
                        field_path="exterior.node",
                        object_id=interior_id,
                    )
                )
    return diagnostics


def gate_approach_cell(
    geometry: Any,
    return_direction: str,
    *,
    frame_cells: int | None = None,
) -> tuple[int, int] | None:
    """The exterior cell a traveller stands on to take one authored gate.

    ``geometry`` is an entry's absolute geometry, resolved against an explicit
    location cell; an authored offset is never an origin here.
    Point-shape entries (exactly one ``#``) use the anchor cell itself. A
    footprint entry walks from the footprint's bounding-box midpoint along the
    face opposite the gate's return direction while inside the footprint; the
    first cell outside is the approach, exactly the authored mask rule.
    Returns None if:
    - anchor_cell is None
    - for non-point shapes, anchor_cell is not in footprint_cells (ray does not start in footprint)
    - the return direction is unknown
    - ray never leaves the footprint or leaves the frame
    - frame_cells is given and the approach cell is outside frame_cells.
    """

    anchor = geometry.anchor_cell
    if anchor is None:
        return None
    if geometry.is_point_shape:
        if frame_cells is not None and not is_within_frame(frame_cells, anchor):
            return None
        return anchor
    footprint = geometry.footprint_cells
    if anchor not in footprint:
        return None
    direction = _OPPOSITE_DIRECTION.get(return_direction)
    if direction is None:
        return None
    delta_x, delta_y = _DIRECTION_DELTAS[direction]
    cell = anchor
    max_steps = len(geometry.shape) * max(len(geometry.shape[0]), 1) + 2
    for _ in range(max_steps):
        if frame_cells is not None and not is_within_frame(frame_cells, cell):
            return None
        cell = (cell[0] + delta_x, cell[1] + delta_y)
        if cell not in footprint:
            if frame_cells is not None and not is_within_frame(frame_cells, cell):
                return None
            return cell
    return None


def terrain_definition(continent: ContinentDocument) -> TerrainDefinition:
    """The deterministic terrain rules' explicit inputs for one continent document."""

    terrain = continent.terrain
    return TerrainDefinition(
        frame_cells=terrain.frame_cells,
        mainland_boundary_km=terrain.mainland_boundary_km,
        forest_edge=terrain.forest_edge,
        waterway_routes={
            key: value.route for key, value in terrain.waterways.items()
        },
        waterway_fords={
            key: value.fords for key, value in terrain.waterways.items()
        },
        border_river_key=terrain.border_river_key,
        ridge_base_x=terrain.ridge_base_x,
        ridge_period=terrain.ridge_period,
        ridge_step=terrain.ridge_step,
        ridge_min_x=terrain.ridge_min_x,
        ridge_max_x=terrain.ridge_max_x,
        ridge_north_limit=terrain.ridge_north_limit_y,
        ridge_passes=terrain.ridge_passes,
        coastal_y_max=terrain.coastal_y_max,
        mountain_corridor_half_width=terrain.ridge_corridor_half_width,
        region_flavors={
            key: value.terrain_flavor_zh for key, value in continent.regions.items()
        },
    )


def _semantic_diagnostics(world: AuthoringWorld) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    terrain: TerrainDefinition | None
    try:
        terrain = terrain_definition(world.continent)
    except (ValueError, TypeError) as error:
        terrain = None
        diagnostics.append(
            _diagnostic(
                "terrain_inconsistent",
                SEMANTIC,
                f"the authored terrain inputs are inconsistent: {error}",
                document=world.continent,
                field_path="terrain",
            )
        )
    footprints: set[tuple[int, int]] = set()
    for geometry in _entry_geometries(
        world.settlements, location_cells_of(world.locations)
    ).values():
        footprints.update(geometry.footprint_cells)

    reachable_cache: dict[str, frozenset[str]] = {}
    for settlement_id, settlement in world.settlements.items():
        if not settlement.nodes:
            diagnostics.append(
                _diagnostic(
                    "empty_graph",
                    SEMANTIC,
                    f"settlement {settlement_id!r} declares no nodes",
                    document=settlement,
                    field_path="nodes",
                    object_id=settlement_id,
                )
            )
            reachable_cache[settlement_id] = frozenset()
            continue
        reachable_cache[settlement_id] = _reachable_nodes(settlement)

    diagnostics.extend(
        diagnose_settlement_semantics(
            world.settlements,
            locations=world.locations,
            frame_cells=world.continent.terrain.frame_cells,
            terrain=terrain,
        )
    )

    interior_reachable = _reachable_interior_rooms(world, reachable_cache)

    for district_id, district in world.districts.districts.items():
        landmark = district.landmark
        if landmark.domain == "settlement_node" and landmark.map_id is not None:
            reachable = reachable_cache.get(landmark.map_id, frozenset())
            if landmark.object_id not in reachable:
                diagnostics.append(
                    _diagnostic(
                        "unreachable_landmark",
                        SEMANTIC,
                        f"landmark node {landmark.object_id!r} is not reachable from "
                        f"an authored entrance of {landmark.map_id!r}",
                        document=world.districts,
                        field_path=f"districts.{district_id}.landmark",
                        object_id=district_id,
                    )
                )
        elif landmark.domain == "wilderness_cell" and landmark.cell is not None:
            cell = landmark.cell
            if cell in footprints:
                continue
            if terrain is None or not is_walkable_cell(terrain, cell):
                diagnostics.append(
                    _diagnostic(
                        "unreachable_landmark",
                        SEMANTIC,
                        f"landmark cell {cell!r} is not walkable wilderness",
                        document=world.districts,
                        field_path=f"districts.{district_id}.landmark.cell",
                        object_id=district_id,
                    )
                )
        elif landmark.domain == "interior_room" and landmark.map_id is not None:
            reachable = interior_reachable.get(landmark.map_id, frozenset())
            if landmark.object_id not in reachable:
                diagnostics.append(
                    _diagnostic(
                        "unreachable_landmark",
                        SEMANTIC,
                        f"landmark room {landmark.object_id!r} is not reachable "
                        f"from an authored entrance of {landmark.map_id!r}",
                        document=world.districts,
                        field_path=f"districts.{district_id}.landmark",
                        object_id=district_id,
                    )
                )
    return diagnostics


def _reachable_nodes(settlement: SettlementDocument) -> frozenset[str]:
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in settlement.nodes}
    for road in settlement.roads:
        adjacency.setdefault(road.source, set()).add(road.destination)
    reachable: set[str] = set()
    pending = list(settlement.entry_nodes)
    while pending:
        node_id = pending.pop()
        if node_id in reachable or node_id not in settlement.nodes:
            continue
        reachable.add(node_id)
        pending.extend(adjacency.get(node_id, ()))
    return frozenset(reachable)


def _reachable_interior_rooms(
    world: AuthoringWorld,
    settlement_reachable: Mapping[str, frozenset[str]],
) -> dict[str, frozenset[str]]:
    """Rooms reachable from a settlement entrance or a reachable interior link."""

    reachable: dict[str, set[str]] = {
        interior_id: set() for interior_id in world.interiors
    }
    changed = True
    while changed:
        changed = False
        for interior_id, interior in world.interiors.items():
            pending: list[str] = []
            exterior = interior.exterior
            if (
                exterior is not None
                and exterior.node
                in settlement_reachable.get(exterior.settlement, frozenset())
            ):
                pending.append(exterior.room)
            for source_id, source in world.interiors.items():
                for link in source.interior_links:
                    if (
                        link.source_room in reachable[source_id]
                        and link.target_interior == interior_id
                    ):
                        pending.append(link.target_room)
            while pending:
                room_id = pending.pop()
                if room_id in reachable[interior_id]:
                    continue
                if room_id not in interior.rooms:
                    continue
                reachable[interior_id].add(room_id)
                changed = True
                pending.extend(
                    connection.destination
                    for connection in interior.connections
                    if connection.source == room_id
                )
    return {
        interior_id: frozenset(rooms) for interior_id, rooms in reachable.items()
    }


def diagnose_world(
    world: AuthoringWorld,
    *,
    partition_freshness: PartitionFreshness | None = None,
) -> tuple[Diagnostic, ...]:
    """Return the world's saveable semantic diagnostics.

    Passing a freshness value also reports a stale required artifact as a
    saveable work-in-progress diagnostic; without it the core cannot know the
    artifact's state and makes no claim.
    """

    diagnostics = list(world.diagnostics)
    if partition_freshness is not None and not _partition_current(
        world,
        partition_freshness,
    ):
        diagnostics.append(
            _diagnostic(
                "stale_partition",
                SEMANTIC,
                "the generated partition does not describe the current map inputs",
                relative_path=None,
            )
        )
    return sorted_diagnostics(diagnostics)


def _partition_current(
    world: AuthoringWorld,
    freshness: PartitionFreshness,
) -> bool:
    return (
        freshness.current is True
        and freshness.input_signature == world.partition_signature
        and freshness.algorithm_version == PARTITION_ALGORITHM_VERSION
    )


def compile_runtime(
    world: AuthoringWorld,
    authoritative_external_result: AuthoritativeExternalResult | None,
    partition_freshness: PartitionFreshness | None,
) -> RuntimeMapSnapshot:
    """Build the immutable runtime snapshot, or reject the candidate."""

    # Advisory warnings describe the map; they never refuse publication, so
    # the rejection accumulator starts with the blocking diagnostics only and
    # every later check appends its own errors to that same list.
    diagnostics: list[Diagnostic] = list(blocking(world.diagnostics))
    if diagnostics:
        raise RuntimeRejection(sorted_diagnostics(diagnostics))

    external = authoritative_external_result
    if not isinstance(external, AuthoritativeExternalResult):
        diagnostics.append(
            _diagnostic(
                "external_reference_unavailable",
                EXTERNAL,
                "no authoritative external result was supplied",
            )
        )
    else:
        if external.version != EXTERNAL_RESULT_VERSION:
            diagnostics.append(
                _diagnostic(
                    "external_version_unsupported",
                    EXTERNAL,
                    f"external result version {external.version!r} is not supported",
                )
            )
        if external.valid is not True:
            diagnostics.append(
                _diagnostic(
                    "external_reference_invalid",
                    EXTERNAL,
                    "the authoritative external result reports invalid references"
                    + (f": {external.reason}" if external.reason else ""),
                )
            )
        if not external.fingerprint:
            diagnostics.append(
                _diagnostic(
                    "external_reference_unavailable",
                    EXTERNAL,
                    "the authoritative external result carries no fingerprint",
                )
            )
        if external.world_fingerprint != world.fingerprint:
            diagnostics.append(
                _diagnostic(
                    "external_result_stale",
                    EXTERNAL,
                    "the authoritative external result was produced for a different world",
                )
            )

    freshness = partition_freshness
    if not isinstance(freshness, PartitionFreshness):
        diagnostics.append(
            _diagnostic(
                "partition_missing",
                FRESHNESS,
                "no partition freshness value was supplied",
            )
        )
    else:
        if freshness.algorithm_version != PARTITION_ALGORITHM_VERSION:
            diagnostics.append(
                _diagnostic(
                    "partition_algorithm_unsupported",
                    FRESHNESS,
                    f"partition algorithm version {freshness.algorithm_version!r} "
                    "is not supported",
                )
            )
        if not freshness.input_signature:
            diagnostics.append(
                _diagnostic(
                    "partition_signature_missing",
                    FRESHNESS,
                    "the partition artifact carries no input signature",
                )
            )
        elif freshness.input_signature != world.partition_signature:
            diagnostics.append(
                _diagnostic(
                    "stale_partition",
                    FRESHNESS,
                    "the partition artifact was generated from different map inputs",
                )
            )
        elif freshness.current is not True:
            diagnostics.append(
                _diagnostic(
                    "stale_partition",
                    FRESHNESS,
                    "the partition artifact is not current",
                )
            )

    if diagnostics:
        raise RuntimeRejection(sorted_diagnostics(diagnostics))

    graphs: dict[str, SparseSettlementGraph] = {}
    for settlement_id, settlement in world.settlements.items():
        try:
            graphs[settlement_id] = build_settlement_graph(settlement_id, settlement)
        except SparseGraphError as error:
            diagnostics.append(
                _diagnostic(
                    "invalid_settlement_graph",
                    STRUCTURE,
                    f"settlement {settlement_id!r} cannot form a runtime graph: {error}",
                    document=settlement,
                    field_path="nodes",
                    object_id=settlement_id,
                )
            )
    if diagnostics:
        raise RuntimeRejection(sorted_diagnostics(diagnostics))

    assert external is not None and freshness is not None
    return RuntimeMapSnapshot(
        fingerprint=world.fingerprint,
        external_fingerprint=external.fingerprint,
        partition_signature=freshness.input_signature,
        partition_algorithm_version=freshness.algorithm_version,
        continent=world.continent,
        locations=world.locations,
        districts=world.districts,
        settlements=MappingProxyType(graphs),
        interiors=world.interiors,
    )


def build_settlement_graph(
    settlement_id: str,
    settlement: SettlementDocument,
) -> SparseSettlementGraph:
    """Assemble one settlement document's validated sparse graph.

    This is the single conversion from authored node/road declarations to the
    spawn, identity and route graph every consumer reads: node prototypes carry
    the authored room fields, roads keep the authored compass octant (never a
    direction inferred from the metre deltas) and the road identity is the
    ``source>destination`` pair the game adapter persists on each exit.
    """

    nodes = []
    for node in settlement.nodes.values():
        prototype: dict[str, Any] = {
            "prototype_parent": node.prototype_parent,
            "key": node.key,
            "desc": node.desc,
        }
        if node.anchor_key is not None:
            prototype["anchor_key"] = node.anchor_key
        if node.typeclass is not None:
            prototype["typeclass"] = node.typeclass
        nodes.append(
            SparseNode(node.node_id, node.x_m, node.y_m, prototype)
        )
    roads = [
        SparseRoad(
            f"{road.source}>{road.destination}",
            road.source,
            road.destination,
            bend_points=tuple((bend.x_m, bend.y_m) for bend in road.bends),
            direction_hint=road.direction,
        )
        for road in settlement.roads
    ]
    return SparseSettlementGraph(
        settlement_id,
        nodes,
        roads,
        options=dict(settlement.options) or None,
        exit_prototype=dict(settlement.exit_prototype) or None,
    )


def road_lengths(settlement: SettlementDocument) -> Mapping[tuple[str, str], float]:
    """Physical polyline length in metres of every declared road.

    Keyed by the road's ordered ``(source, destination)`` identity. The
    length runs from the source node through the authored bend points to the
    destination node in the settlement's local metre frame. It is computed
    per road, so it exists even when the whole graph cannot be built (an
    empty or unfinished map); a road naming an unknown node has no length.
    """

    lengths: dict[tuple[str, str], float] = {}
    for road in settlement.roads:
        source = settlement.nodes.get(road.source)
        destination = settlement.nodes.get(road.destination)
        if source is None or destination is None:
            continue
        points = (
            source.coordinate,
            *((bend.x_m, bend.y_m) for bend in road.bends),
            destination.coordinate,
        )
        lengths[(road.source, road.destination)] = polyline_length(points)
    return MappingProxyType(lengths)


@dataclass(frozen=True, slots=True)
class RouteStepPreview:
    """One directed road of a route preview, with its physical length."""

    source: str
    destination: str
    direction: str
    length_m: float


ROUTE_FOUND = "route"
ROUTE_NONE = "no_route"
ROUTE_UNKNOWN_NODE = "unknown_node"
ROUTE_UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class RoutePreview:
    """The shortest authored route between two nodes of one settlement.

    ``status`` is ``route`` (``steps`` and the total ``length_m``),
    ``no_route`` (the directed roads do not connect them), ``unknown_node``
    or ``unavailable`` (the graph cannot be built; ``reason`` says why).
    """

    status: str
    source: str
    destination: str
    steps: tuple[RouteStepPreview, ...] = ()
    length_m: float | None = None
    reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "destination": self.destination,
            "steps": [
                {
                    "source": step.source,
                    "destination": step.destination,
                    "direction": step.direction,
                    "length_m": step.length_m,
                }
                for step in self.steps
            ],
            "length_m": self.length_m,
            "reason": self.reason,
        }


def settlement_route(
    settlement_id: str,
    settlement: SettlementDocument,
    source: str,
    destination: str,
) -> RoutePreview:
    """Preview the route the game's planner would take (read-only)."""

    if source not in settlement.nodes or destination not in settlement.nodes:
        return RoutePreview(ROUTE_UNKNOWN_NODE, source, destination)
    try:
        graph = build_settlement_graph(settlement_id, settlement)
    except SparseGraphError as error:
        return RoutePreview(ROUTE_UNAVAILABLE, source, destination, reason=str(error))
    edges = graph.route(source, destination)
    if edges is None:
        return RoutePreview(ROUTE_NONE, source, destination)
    steps = tuple(
        RouteStepPreview(
            edge.source.node_id,
            edge.destination.node_id,
            edge.direction,
            edge.length,
        )
        for edge in edges
    )
    return RoutePreview(
        ROUTE_FOUND,
        source,
        destination,
        steps,
        sum(step.length_m for step in steps),
    )


__all__ = [
    "AuthoritativeExternalResult",
    "AuthoringWorld",
    "PARTITION_ALGORITHM_VERSION",
    "PartitionFreshness",
    "RoutePreview",
    "RouteStepPreview",
    "RuntimeMapSnapshot",
    "build_settlement_graph",
    "compile_runtime",
    "diagnose_interior_rules",
    "diagnose_interior_structure",
    "diagnose_settlement_rules",
    "diagnose_settlement_semantics",
    "diagnose_settlement_structure",
    "diagnose_world",
    "gate_approach_cell",
    "load_authoring_world",
    "road_lengths",
    "settlement_route",
    "terrain_definition",
]
