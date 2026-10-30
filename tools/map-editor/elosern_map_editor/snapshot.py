"""One complete read of the workspace: sources, diagnostics and statuses.

``read_workspace`` performs a fresh confined disk read, loads the candidate
with ``elosern_map_core`` and returns a :class:`WorkspaceRead`. Every domain
value in the projection is computed by the core (world positions, road
lengths, schema, diagnostics, partition and reference-context freshness); the
service and the browser never re-derive map rules. Nothing here writes.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from elosern_map_core import (
    AuthoringError,
    Diagnostic,
    ReferenceContextError,
    ReferenceContextFreshness,
    PartitionDocumentError,
    cell_center_m,
    check_reference_context_freshness,
    decode_reference_context,
    diagnose_world,
    discover_external_sources,
    gate_approach_cell,
    load_authoring_world,
    local_to_world_m,
    make_source_document,
    parse_document,
    partition_freshness,
    read_partition_metadata,
    road_lengths,
    terrain_definition,
    terrain_preview,
)
from elosern_map_core.terrain import PREVIEW_SURFACES
from elosern_map_core.diagnostics import STRUCTURE, sorted_diagnostics
from elosern_map_core.reference_context import ReferenceContextDocument

from .config import Limits
from .confinement import (
    PARTITION_ARTIFACT,
    REFERENCE_CONTEXT_ARTIFACT,
    ConfinedWorkspace,
    ConfinementError,
    split_relative,
)

_REFUSAL_CODES = {
    "symlink_rejected": "unsafe_source_path",
    "not_regular_file": "unsafe_source_path",
    "not_directory": "unsafe_source_path",
    "too_large": "invalid_document_size",
    "missing": "missing_source",
    "unreadable": "unreadable_source",
}


def thaw(value: Any) -> Any:
    """A frozen core value tree as plain JSON-ready data."""

    if isinstance(value, Mapping):
        return {str(key): thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [thaw(item) for item in value]
    return value


def _refusal(relative_path: str, code: str, message: str) -> Diagnostic:
    return Diagnostic(
        code=_REFUSAL_CODES.get(code, "unsafe_source_path"),
        category=STRUCTURE,
        message=message,
        relative_path=relative_path,
        field_path="",
    )


@dataclass(frozen=True, slots=True)
class WorkspaceRead:
    """The outcome of one disk read (loaded or structurally rejected)."""

    loaded: bool
    documents: tuple[dict[str, Any], ...]
    world: dict[str, Any] | None
    diagnostics: tuple[dict[str, Any], ...]
    external_context_status: dict[str, Any]
    partition_status: dict[str, Any]
    #: ``(relative_path, presence)`` for every discovered world source and
    #: layout document: the raw-byte content fingerprint, or ``unreadable:<code>``
    #: for an entry that was refused. Generated artifacts are not included.
    fingerprints: tuple[tuple[str, str], ...] = ()
    #: ``{qualified_ref: [incoming reference, ...]}`` from the reference
    #: context for every projected map object that has one, looked up through
    #: the core's own ``incoming_references_for``. Informative only: it is
    #: present whenever the index decoded, even when it is not current, and an
    #: index that is not current can never prove that a target is unreferenced.
    external_incoming_references: tuple[tuple[str, tuple[dict[str, Any], ...]], ...] = ()
    #: External identifier sets the editor offers as options (only the
    #: ``scene_archetypes`` family), present only while the index is current.
    external_identifiers: tuple[tuple[str, tuple[str, ...]], ...] = ()
    #: The loaded immutable authoring world behind ``world`` (read-only
    #: previews such as the route endpoint). Not part of the observable
    #: digest: it is derived from the same documents.
    authoring: Any = field(default=None, compare=False, repr=False)

    @property
    def fingerprint_map(self) -> dict[str, str]:
        return dict(self.fingerprints)

    @property
    def digest(self) -> str:
        """Identity of the observable outcome (used to skip no-op publishes)."""

        payload = json.dumps(
            [self.loaded, self.documents, self.world, self.diagnostics,
             self.external_context_status, self.partition_status, self.fingerprints,
             self.external_incoming_references, self.external_identifiers],
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# -- source reads ----------------------------------------------------------
def read_sources(workspace: ConfinedWorkspace, limits: Limits, rows):
    """``(sources, refusal diagnostics, presence fingerprints)`` for discovered rows."""

    sources = []
    diagnostics: list[Diagnostic] = []
    fingerprints: dict[str, str] = {}
    if len(rows) > limits.max_documents:
        diagnostics.append(
            Diagnostic(
                code="too_many_documents",
                category=STRUCTURE,
                message=f"{len(rows)} documents exceed the {limits.max_documents}-document limit",
            )
        )
        return sources, diagnostics, fingerprints
    for relative_path, refusal in rows:
        if refusal is not None:
            fingerprints[relative_path] = f"unreadable:{refusal}"
            diagnostics.append(
                _refusal(relative_path, refusal, f"{relative_path} was refused ({refusal})")
            )
            continue
        try:
            raw = workspace.read_document(relative_path, limits.max_document_bytes)
        except ConfinementError as error:
            fingerprints[relative_path] = f"unreadable:{error.code}"
            diagnostics.append(_refusal(relative_path, error.code, str(error)))
            continue
        fingerprints[relative_path] = hashlib.sha256(raw).hexdigest()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            diagnostics.append(
                Diagnostic(
                    code="invalid_encoding",
                    category=STRUCTURE,
                    message=f"{relative_path} is not valid UTF-8: {error}",
                    relative_path=relative_path,
                )
            )
            continue
        sources.append(make_source_document(relative_path, text))
    return sources, diagnostics, fingerprints


def _read_layout_sources(workspace: ConfinedWorkspace, limits: Limits):
    return read_sources(workspace, limits, workspace.discover_layouts())


def _parse_layouts(sources, refused):
    layouts: dict[str, dict[str, Any]] = {}
    diagnostics: list[Diagnostic] = list(refused)
    for source in sources:
        try:
            parsed = parse_document(source.relative_path, source.text)
        except AuthoringError as error:
            diagnostics.extend(error.diagnostics)
            continue
        document = parsed.document
        layouts[document.identity] = {
            "id": document.identity,
            "relative_path": source.relative_path,
            "fingerprint": source.fingerprint,
            "positions": {
                key: [position.x, position.y]
                for key, position in sorted(document.positions.items())
            },
        }
    return layouts, diagnostics


# -- generated artifact statuses ------------------------------------------
def _partition_status(workspace: ConfinedWorkspace, limits: Limits, world) -> tuple[dict, Any]:
    base = {"relative_path": PARTITION_ARTIFACT}
    try:
        raw = workspace.read_document(PARTITION_ARTIFACT, limits.max_artifact_bytes)
        metadata = read_partition_metadata(raw.decode("utf-8"))
    except ConfinementError as error:
        return {**base, "status": "unavailable", "current": False, "reasons": [f"{error.code}: {error}"]}, None
    except (PartitionDocumentError, UnicodeDecodeError, ValueError) as error:
        return {**base, "status": "unavailable", "current": False, "reasons": [f"malformed: {error}"]}, None
    expected = world.partition_signature if world is not None else None
    freshness = partition_freshness(metadata, expected)
    return (
        {
            **base,
            # The artifact bytes' identity: a client keys its outline fetch on it.
            "artifact_fingerprint": hashlib.sha256(raw).hexdigest(),
            "status": "current" if freshness.current else "stale",
            "current": freshness.current,
            "algorithm_version": metadata.algorithm_version,
            "input_signature": metadata.source_signature,
            "expected_signature": expected,
            "reasons": [] if freshness.current else ["the artifact does not describe the current map inputs"],
        },
        freshness,
    )


@dataclass(frozen=True, slots=True)
class ExternalContext:
    """One execution-time read of the reference context and its freshness.

    ``document``/``freshness`` are ``None`` when the context could not be read
    or checked; such a context can never prove that a target is unreferenced.
    """

    status: dict[str, Any]
    document: ReferenceContextDocument | None = None
    freshness: ReferenceContextFreshness | None = None


def read_external_context(
    workspace: ConfinedWorkspace,
    limits: Limits,
    *,
    known_hashes: Mapping[str, str] | None = None,
    unread: Iterable[str] = (),
) -> ExternalContext:
    """Fresh confined read of the reference context, re-hashing every source.

    ``known_hashes`` supplies digests of documents the caller already read, so
    an index that lists them costs no second read. ``unread`` names candidate
    paths the caller deliberately did not read: an index depending on them
    cannot be shown current, so it is reported unavailable instead.
    """

    base = {"relative_path": REFERENCE_CONTEXT_ARTIFACT}

    def unavailable(status: str, reason: str) -> ExternalContext:
        return ExternalContext({**base, "status": status, "current": False, "reasons": [reason]})

    try:
        raw = workspace.read_document(REFERENCE_CONTEXT_ARTIFACT, limits.max_artifact_bytes)
        context = decode_reference_context(raw.decode("utf-8"))
    except ConfinementError as error:
        return unavailable("missing" if error.code == "missing" else "unavailable", f"{error.code}: {error}")
    except (ReferenceContextError, UnicodeDecodeError) as error:
        return unavailable("incompatible", f"malformed: {error}")
    try:
        for rule in context.discovery_rules:
            # Rules come from a file: confine them before any glob runs.
            split_relative(rule)
        for path in context.source_manifest:
            split_relative(path)
    except ConfinementError as error:
        return unavailable("unavailable", f"unsafe discovery rule or manifest path: {error.relative_path}")
    discovered = discover_external_sources(workspace.root, context.discovery_rules)
    known = {path: digest for path, digest in (known_hashes or {}).items()}
    skipped = {path.replace("\\", "/") for path in unread}
    candidates = sorted(set(discovered) | set(context.source_manifest))
    if len(candidates) > limits.max_external_files:
        return unavailable("unavailable", f"{len(candidates)} external sources exceed the limit")
    hashes: dict[str, str] = {}
    total = 0
    unresolved: list[str] = []
    for relative_path in candidates:
        if relative_path in known:
            hashes[relative_path] = known[relative_path]
            continue
        if relative_path in skipped:
            unresolved.append(relative_path)
            continue
        try:
            data = workspace.read_external(relative_path, limits.max_external_file_bytes)
        except ConfinementError as error:
            if error.code == "missing":
                continue
            return unavailable("unavailable", f"{relative_path}: {error.code}")
        total += len(data)
        if total > limits.max_external_total_bytes:
            return unavailable("unavailable", "external sources exceed the total byte limit")
        hashes[relative_path] = hashlib.sha256(data).hexdigest()
    if unresolved:
        return unavailable(
            "unavailable",
            f"not read for this capture: {', '.join(sorted(unresolved))}",
        )
    freshness = check_reference_context_freshness(context, hashes, discovered_files=discovered)
    return ExternalContext(
        {
            **base,
            "status": freshness.status,
            "current": freshness.current,
            "reasons": list(freshness.reasons),
            "fingerprint": context.fingerprint,
        },
        context,
        freshness,
    )


# -- projection ------------------------------------------------------------
def _cell(cell) -> list[int]:
    return [int(cell[0]), int(cell[1])]


def _terrain_preview(continent) -> dict[str, Any]:
    """The core's derived terrain preview of the current inputs (cell units).

    Recomputed on every read from the authored inputs alone; nothing here
    classifies a cell. Inconsistent inputs (a saveable semantic diagnostic)
    have no preview, with the core's reason.
    """

    try:
        preview = terrain_preview(terrain_definition(continent))
    except (ValueError, TypeError) as error:
        return {"status": "unavailable", "reason": str(error)}
    return {
        "status": "current",
        "step": preview.step,
        "columns": preview.columns,
        "rows": preview.rows,
        "regions": list(preview.regions),
        "surfaces": list(PREVIEW_SURFACES),
        "samples": list(preview.samples),
        "ridge_walls": [[_cell(point) for point in wall] for wall in preview.ridge_walls],
        "passes": [
            {"index": index, "y_min": low, "y_max": high, "centre": _cell(centre)}
            for index, (low, high, centre) in enumerate(preview.passes)
        ],
        "national_borders": [
            {"nation_keys": list(border.nation_keys), "points": [_cell(point) for point in border.points]}
            for border in preview.national_borders
        ],
        "borders_reason": preview.borders_reason,
    }


def _footprint(settlement, location_cell) -> dict[str, Any] | None:
    """The authored mask with its derived absolute origin and cells.

    The document owns only the offset from its location cell; ``origin`` and
    ``cells`` are projected for the read-only grid so the editor never has to
    add a cell itself.
    """

    entry = settlement.wilderness_entry
    if entry is None:
        return None
    geometry = None if location_cell is None else entry.geometry(location_cell)
    return {
        "shape": list(entry.shape),
        "offset": [int(entry.offset[0]), int(entry.offset[1])],
        "origin": None if geometry is None else _cell(geometry.origin),
        "cells": [] if geometry is None else sorted(_cell(cell) for cell in geometry.mask_cells),
    }


def _wilderness_entry(settlement, location_cell) -> dict[str, Any] | None:
    """The authored entry, each gate with its core-computed approach cell."""

    data = thaw(settlement.data.get("wilderness_entry"))
    geometry = settlement.wilderness_geometry(location_cell) if location_cell is not None else None
    if data is None or geometry is None:
        return data
    for gate in data["gates"]:
        cell = gate_approach_cell(geometry, gate["return_direction"])
        gate["approach_cell"] = None if cell is None else _cell(cell)
    return data


def _project(world, layouts: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
    continent = world.continent
    terrain = continent.terrain
    local_maps: dict[str, list[str]] = {}
    for settlement_id, settlement in sorted(world.settlements.items()):
        local_maps.setdefault(settlement.location_ref, []).append(settlement_id)
    interiors_by_settlement: dict[str, list[str]] = {}
    for interior_id, interior in sorted(world.interiors.items()):
        if interior.exterior is not None:
            interiors_by_settlement.setdefault(interior.exterior.settlement, []).append(interior_id)

    settlements = []
    for settlement_id, settlement in sorted(world.settlements.items()):
        lengths = road_lengths(settlement)
        location = world.locations.locations.get(settlement.location_ref)
        location_cell = None if location is None else location.cell
        local_anchor = settlement.local_anchor_m
        world_frame = (
            None
            if location_cell is None or local_anchor is None
            else {
                "anchor_cell": _cell(location_cell),
                "local_anchor_m": [int(local_anchor[0]), int(local_anchor[1])],
            }
        )
        nodes = []
        for node_id, node in settlement.nodes.items():
            world_m = (
                None
                if world_frame is None
                else local_to_world_m(location_cell, local_anchor, node.coordinate)
            )
            nodes.append(
                {
                    "id": node_id,
                    "qualified_ref": f"settlement_node:{settlement_id}:{node_id}",
                    "key": node.key,
                    "desc": node.desc,
                    "prototype_parent": node.prototype_parent,
                    "scene_archetype": node.scene_archetype,
                    "anchor_key": node.anchor_key,
                    "typeclass": node.typeclass,
                    "local_m": [node.x_m, node.y_m],
                    "world_m": None if world_m is None else [int(world_m[0]), int(world_m[1])],
                }
            )
        roads = []
        for road in settlement.roads:
            length = lengths.get((road.source, road.destination))
            roads.append(
                {
                    "id": f"{road.source}>{road.destination}",
                    "source": road.source,
                    "destination": road.destination,
                    "direction": road.direction,
                    "bends": [[bend.x_m, bend.y_m] for bend in road.bends],
                    "length_m": round(length, 3) if length is not None else None,
                }
            )
        settlements.append(
            {
                "id": settlement_id,
                "relative_path": settlement.relative_path,
                "location_ref": settlement.location_ref,
                "world_frame": world_frame,
                "nodes": nodes,
                "roads": roads,
                "wilderness_entry": _wilderness_entry(settlement, location_cell),
                "footprint": _footprint(settlement, location_cell),
                "city_gate": thaw(settlement.data.get("city_gate")),
                "options": thaw(settlement.data.get("options")),
                "exit_prototype": thaw(settlement.data.get("exit_prototype")),
                "interiors": interiors_by_settlement.get(settlement_id, []),
            }
        )

    interiors = []
    for interior_id, interior in sorted(world.interiors.items()):
        layout = layouts.get(interior_id)
        positions = layout["positions"] if layout else {}
        interiors.append(
            {
                "id": interior_id,
                "relative_path": interior.relative_path,
                "layout_relative_path": layout["relative_path"] if layout else None,
                "rooms": [
                    {
                        "id": room_id,
                        "qualified_ref": f"interior_room:{interior_id}:{room_id}",
                        "name_zh": room.name_zh,
                        "desc_zh": room.desc_zh,
                        "scene_archetype": room.scene_archetype,
                        "art_key": room.art_key,
                        "layout_position": positions.get(room_id),
                    }
                    for room_id, room in interior.rooms.items()
                ],
                "connections": thaw(interior.data.get("connections", ())),
                "interior_links": thaw(interior.data.get("interior_links", ())),
                "exterior": thaw(interior.data.get("exterior")),
            }
        )

    return {
        "fingerprint": world.fingerprint,
        "continent": {
            "relative_path": continent.relative_path,
            "frame_cells": terrain.frame_cells,
            "cell_size_km": terrain.cell_size_km,
            "mainland_boundary_km": [list(point) for point in terrain.mainland_boundary_km],
            "forest_edge": [_cell(cell) for cell in terrain.forest_edge],
            "forest_edge_m": [list(cell_center_m(cell)) for cell in terrain.forest_edge],
            "waterways": [
                {
                    "id": waterway_id,
                    "route": [_cell(cell) for cell in waterway.route],
                    "route_m": [list(cell_center_m(cell)) for cell in waterway.route],
                    "fords": [_cell(cell) for cell in waterway.fords],
                    "fords_m": [list(cell_center_m(cell)) for cell in waterway.fords],
                }
                for waterway_id, waterway in sorted(terrain.waterways.items())
            ],
            "harbor_sites": [
                {
                    "id": site.site_id,
                    "display_name": site.display_name,
                    "cell": _cell(site.cell),
                    "centre_m": list(cell_center_m(site.cell)),
                    "role": site.role,
                }
                for site in continent.harbor_sites.values()
            ],
            "regions": [
                {"id": region_id, **thaw(region)}
                for region_id, region in sorted(continent.data["regions"].items())
            ],
            "ridge": thaw(continent.data["terrain"]["ridge"]),
            "coastal_y_max": continent.data["terrain"]["coastal_y_max"],
            "border_river_key": continent.data["terrain"]["border_river_key"],
            "terrain_preview": _terrain_preview(continent),
        },
        "locations": [
            {
                "id": location_id,
                "qualified_ref": f"location:{location_id}",
                "relative_path": world.locations.relative_path,
                "kind": location.kind,
                "display_name_zh": location.display_name_zh,
                "description": location.description,
                "scene_archetype": location.scene_archetype,
                "cell": _cell(location.cell),
                "centre_m": list(cell_center_m(location.cell)),
                "local_maps": local_maps.get(location_id, []),
            }
            for location_id, location in world.locations.locations.items()
        ],
        "districts": [
            {
                "id": district_id,
                "relative_path": world.districts.relative_path,
                "district_name_zh": district.district_name_zh,
                "landmark_name_zh": district.landmark_name_zh,
                "landmark": thaw(world.districts.data["districts"][district_id]["landmark"]),
                "kind": district.kind,
                "region_key": district.region_key,
                # Optional distant-sighting authoring; absent values stay
                # absent so the editor never invents a range or a silhouette.
                "vantage": district.vantage,
                "sight_km": district.sight_km,
                "light_km": district.light_km,
                "silhouette_zh": district.silhouette_zh,
            }
            for district_id, district in world.districts.districts.items()
        ],
        "settlements": settlements,
        "interiors": interiors,
        "layouts": [
            {key: value for key, value in layout.items() if key != "positions"}
            for _, layout in sorted(layouts.items())
        ],
    }


# -- shared load and projection --------------------------------------------
@dataclass(frozen=True, slots=True)
class SourceLoad:
    """One confined source/layout/core load and its projection (never writes).

    ``read_workspace`` and the capture adapter consume this operation and apply
    their own policy to :attr:`structure`: the interactive editor keeps a
    partial layout projection and reports the diagnostics, while capture
    refuses it.
    """

    #: The loaded immutable authoring world, or ``None`` when the source set
    #: could not be loaded at all.
    world: Any | None
    #: The JSON-ready projection of :attr:`world` (``None`` without a world).
    projection: dict[str, Any] | None
    #: Every diagnostic the layout documents produced.
    layout_diagnostics: tuple[Diagnostic, ...]
    #: The structure-category diagnostics of this read: a non-empty value means
    #: the sources or layouts cannot be admitted by a caller that requires a
    #: structurally sound workspace.
    structure: tuple[Diagnostic, ...]
    #: ``(relative_path, presence)`` for the world sources and layouts.
    fingerprints: tuple[tuple[str, str], ...]
    #: ``{relative_path, fingerprint}`` of the readable world sources.
    source_rows: tuple[dict[str, str], ...]


def load_sources(workspace: ConfinedWorkspace, limits: Limits) -> SourceLoad:
    """Discover the workspace sources once, read each once, load and project it."""

    sources, refused, fingerprints = read_sources(workspace, limits, workspace.discover_world())
    layout_sources, layout_refused, layout_fingerprints = _read_layout_sources(workspace, limits)
    presence = tuple(sorted({**fingerprints, **layout_fingerprints}.items()))
    source_rows = tuple(
        {"relative_path": source.relative_path, "fingerprint": source.fingerprint}
        for source in sorted(sources, key=lambda item: item.relative_path)
    )
    if refused:
        return SourceLoad(
            world=None,
            projection=None,
            layout_diagnostics=(),
            structure=tuple(sorted_diagnostics(refused)),
            fingerprints=presence,
            source_rows=source_rows,
        )
    try:
        world = load_authoring_world(sources)
    except AuthoringError as error:
        return SourceLoad(
            world=None,
            projection=None,
            layout_diagnostics=(),
            structure=error.diagnostics,
            fingerprints=presence,
            source_rows=source_rows,
        )
    layouts, layout_diagnostics = _parse_layouts(layout_sources, layout_refused)
    return SourceLoad(
        world=world,
        projection=_project(world, layouts),
        layout_diagnostics=sorted_diagnostics(layout_diagnostics),
        structure=tuple(item for item in layout_diagnostics if item.category == STRUCTURE),
        fingerprints=presence,
        source_rows=source_rows,
    )


def read_workspace(workspace: ConfinedWorkspace, limits: Limits) -> WorkspaceRead:
    """One fresh confined read of the complete workspace."""

    load = load_sources(workspace, limits)
    context = read_external_context(workspace, limits)
    external = context.status
    if load.world is None:
        partition, _ = _partition_status(workspace, limits, None)
        return WorkspaceRead(
            loaded=False,
            documents=load.source_rows,
            world=None,
            diagnostics=tuple(item.as_dict() for item in load.structure),
            external_context_status=external,
            partition_status=partition,
            fingerprints=load.fingerprints,
        )
    world = load.world
    partition, freshness = _partition_status(workspace, limits, world)
    diagnostics = sorted_diagnostics(
        (*diagnose_world(world, partition_freshness=freshness), *load.layout_diagnostics)
    )
    projection = load.projection
    incoming = _incoming_references(context, projection)
    identifiers = _scene_statuses(context, projection)
    documents = tuple(
        {
            "relative_path": document.relative_path,
            "kind": document.kind,
            "id": document.identity,
            "fingerprint": document.fingerprint,
            "data": thaw(document.data),
        }
        for document in world.documents
    )
    return WorkspaceRead(
        loaded=True,
        documents=documents,
        world=projection,
        diagnostics=tuple(item.as_dict() for item in diagnostics),
        external_context_status=external,
        partition_status=partition,
        fingerprints=load.fingerprints,
        external_incoming_references=incoming,
        external_identifiers=identifiers,
        authoring=world,
    )


def _projected_refs(projection: Mapping[str, Any]):
    for location in projection["locations"]:
        yield location["qualified_ref"]
    for settlement in projection["settlements"]:
        for node in settlement["nodes"]:
            yield node["qualified_ref"]
    for interior in projection["interiors"]:
        for room in interior["rooms"]:
            yield room["qualified_ref"]


#: The external identifier family that names scene references.
SCENE_FAMILY = "scene_archetypes"


def _scene_statuses(context: ExternalContext, projection: dict[str, Any]):
    """Mark every settlement node's and interior room's scene reference, return the offered set.

    ``scene_status`` is ``none`` (no scene), ``valid`` or ``invalid`` against
    the current index's scene identifiers, or ``unavailable`` when the index
    is missing, incompatible or not current (it can then prove nothing).
    """

    current = context.document is not None and context.freshness is not None and context.freshness.current
    scenes = context.document.identifier_set(SCENE_FAMILY) if current else None
    marked = [node for settlement in projection["settlements"] for node in settlement["nodes"]]
    marked += [room for interior in projection["interiors"] for room in interior["rooms"]]
    for item in marked:
        scene = item["scene_archetype"]
        if scene is None:
            item["scene_status"] = "none"
        elif scenes is None:
            item["scene_status"] = "unavailable"
        else:
            item["scene_status"] = "valid" if scene in scenes else "invalid"
    return ((SCENE_FAMILY, tuple(sorted(scenes))),) if scenes is not None else ()


def _incoming_references(context: ExternalContext, projection: Mapping[str, Any]):
    """Incoming external references of the projected objects only (bounded)."""

    if context.document is None:
        return ()
    rows = []
    for ref in _projected_refs(projection):
        found = context.document.incoming_references_for(ref)
        if found:
            rows.append((ref, tuple(item.to_dict() for item in found)))
    return tuple(sorted(rows))


__all__ = [
    "ExternalContext",
    "SourceLoad",
    "WorkspaceRead",
    "load_sources",
    "read_external_context",
    "read_sources",
    "read_workspace",
    "thaw",
]
