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
    EXTERNAL,
    FRESHNESS,
    SEMANTIC,
    STRUCTURE,
    AuthoringError,
    Diagnostic,
    RuntimeRejection,
    sorted_diagnostics,
)
from .documents import (
    AuthoringDocument,
    ContinentDocument,
    DistrictsDocument,
    InteriorDocument,
    LocationsDocument,
    SettlementDocument,
)
from .sources import SourceDocument, fingerprint_text, is_world_source
from .sparse import SparseGraphError, SparseNode, SparseRoad, SparseSettlementGraph
from .terrain import (
    REGION_KEYS,
    TerrainDefinition,
    is_valid_wilderness_cell,
    is_walkable_cell,
)

EXTERNAL_RESULT_VERSION = 1
PARTITION_ALGORITHM_VERSION = 1
PARTITION_SOURCE_KINDS = frozenset({"continent", "locations", "districts", "settlement"})
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
class PartitionFreshness:
    """The generated partition artifact's freshness for one input signature."""

    algorithm_version: int
    input_signature: str
    current: bool


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
    def fingerprint(self) -> str:
        return _combined_fingerprint(self.documents)

    @property
    def partition_signature(self) -> str:
        return _combined_fingerprint(
            document
            for document in self.documents
            if document.kind in PARTITION_SOURCE_KINDS
        )


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
        if settlement.location_ref not in locations.locations:
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
                if _approach_cell(entry, gate.return_direction) is None:
                    diagnostics.append(
                        _diagnostic(
                            "invalid_gate",
                            STRUCTURE,
                            f"gate {gate.return_direction!r} never leaves the footprint",
                            document=settlement,
                            field_path="wilderness_entry.gates",
                            object_id=settlement_id,
                        )
                    )

    for district_id, district in districts.districts.items():
        landmark = district.landmark
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
        if landmark.domain == "settlement_node":
            settlement = settlements.get(landmark.map_id or "")
            if settlement is None:
                diagnostics.append(
                    _diagnostic(
                        "unknown_reference",
                        STRUCTURE,
                        f"landmark map {landmark.map_id!r} is not an authored settlement",
                        document=districts,
                        field_path=f"districts.{district_id}.landmark.map_id",
                        object_id=district_id,
                    )
                )
            elif landmark.object_id not in settlement.nodes:
                diagnostics.append(
                    _diagnostic(
                        "unknown_reference",
                        STRUCTURE,
                        f"landmark node {landmark.object_id!r} is not in {landmark.map_id!r}",
                        document=districts,
                        field_path=f"districts.{district_id}.landmark.object_id",
                        object_id=district_id,
                    )
                )
        elif landmark.domain == "interior_room":
            interior = interiors.get(landmark.map_id or "")
            if interior is None or landmark.object_id not in interior.rooms:
                diagnostics.append(
                    _diagnostic(
                        "unknown_reference",
                        STRUCTURE,
                        f"landmark room {landmark.object_id!r} is not authored in "
                        f"{landmark.map_id!r}",
                        document=districts,
                        field_path=f"districts.{district_id}.landmark",
                        object_id=district_id,
                    )
                )
        elif landmark.domain == "location":
            if landmark.object_id not in locations.locations:
                diagnostics.append(
                    _diagnostic(
                        "unknown_reference",
                        STRUCTURE,
                        f"landmark location {landmark.object_id!r} is not authored",
                        document=districts,
                        field_path=f"districts.{district_id}.landmark.object_id",
                        object_id=district_id,
                    )
                )
        elif landmark.domain == "wilderness_cell":
            cell = landmark.cell
            frame = continent.terrain.frame_cells
            if cell is None or not (0 <= cell[0] < frame and 0 <= cell[1] < frame):
                diagnostics.append(
                    _diagnostic(
                        "unknown_reference",
                        STRUCTURE,
                        f"landmark cell {cell!r} is outside the {frame}-cell frame",
                        document=districts,
                        field_path=f"districts.{district_id}.landmark.cell",
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


def _approach_cell(
    entry: Any,
    return_direction: str,
) -> tuple[int, int] | None:
    """The exterior cell a traveller stands on to take one authored gate.

    Point-shape entries (exactly one ``#``) use the anchor cell itself. A
    footprint entry walks from the footprint's bounding-box midpoint along the
    face opposite the gate's return direction while inside the footprint; the
    first cell outside is the approach, exactly the authored mask rule.
    """

    anchor = entry.anchor_cell
    if anchor is None:
        return None
    if entry.is_point_shape:
        return anchor
    footprint = entry.footprint_cells
    direction = _OPPOSITE_DIRECTION[return_direction]
    delta_x, delta_y = _DIRECTION_DELTAS[direction]
    cell = anchor
    for _ in range(len(entry.shape) * max(len(entry.shape[0]), 1) + 1):
        cell = (cell[0] + delta_x, cell[1] + delta_y)
        if cell not in footprint:
            return cell
    return None


def _terrain_definition(continent: ContinentDocument) -> TerrainDefinition:
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
        terrain = _terrain_definition(world.continent)
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
    for settlement in world.settlements.values():
        if settlement.wilderness_entry is not None:
            footprints.update(settlement.wilderness_entry.footprint_cells)

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
        if settlement.wilderness_entry is not None:
            for gate in settlement.wilderness_entry.gates:
                approach = _approach_cell(
                    settlement.wilderness_entry,
                    gate.return_direction,
                )
                if terrain is not None and approach is not None:
                    if not is_valid_wilderness_cell(terrain, footprints, approach):
                        diagnostics.append(
                            _diagnostic(
                                "blocked_approach",
                                SEMANTIC,
                                f"gate {gate.return_direction!r} approach "
                                f"{approach!r} is not walkable wilderness",
                                document=settlement,
                                field_path="wilderness_entry.gates",
                                object_id=settlement_id,
                            )
                        )

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

    diagnostics: list[Diagnostic] = list(world.diagnostics)
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
            graphs[settlement_id] = _settlement_graph(settlement_id, settlement)
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


def _settlement_graph(
    settlement_id: str,
    settlement: SettlementDocument,
) -> SparseSettlementGraph:
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
            f"{road.source}->{road.destination}",
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


__all__ = [
    "AuthoritativeExternalResult",
    "AuthoringWorld",
    "PARTITION_ALGORITHM_VERSION",
    "PartitionFreshness",
    "RuntimeMapSnapshot",
    "compile_runtime",
    "diagnose_world",
    "load_authoring_world",
]
