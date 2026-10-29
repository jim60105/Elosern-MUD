"""Explicitly loaded settlement local maps and their immutable game views.

The authored source is one discovered YAML document per settlement under
``content/maps/settlements/<map_id>.yaml``; ``elosern_map_core`` owns the schema,
the codec and the sparse-graph conversion. This module is the one game-side
adapter that

* discovers those documents in sorted order and reads the canonical
  ``content/maps/locations.yaml`` they bind to,
* composes the read-only game views (sparse graphs, anchor placements, local
  frame anchors, starting-room gates, wilderness entries and map-owned node
  scene associations) by joining authored values with the untouched Python
  non-map lore, and
* validates every settlement's own declaration and every cross-document join
  before it publishes a snapshot.

A location's local map is discovered from ``location_ref`` alone, so adding a
map for an existing location is a source edit: no Python registration, roster
or reverse location list exists.

Composition never publishes: a failed candidate raises :class:`SettlementError`
and leaves the adopted world exactly as it was. Nothing loads at import time;
the map composition root (``world.maps.runtime``) composes this domain and
installs it inside one adopted bundle, and every read-only consumer goes
through a registry view or :func:`current`.

Consumers must read through :func:`settlement_graph` (or
:data:`SETTLEMENT_GRAPHS`); never rebuild a graph from a single source file.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from elosern_map_core.authoring import build_settlement_graph
from elosern_map_core.codec import parse_document
from elosern_map_core.documents import LocationsDocument, SettlementDocument, QualifiedRef
from elosern_map_core.references import ReferenceIndex, settlement_node_ref
from elosern_map_core.sources import SourceDocument, fingerprint_text
from elosern_map_core.sparse import SparseGraphError, SparseSettlementGraph

from world.lore.anchor_placement import AnchorPlacement
from world.lore.anchors import LocalFrameAnchor
from world.lore.wilderness_entry import (
    WildernessEntryPoint,
    WildernessGate,
)
from elosern_map_core.authoring import diagnose_settlement_rules
from world.maps.city_gates import CityGateDef
from world.maps.published import PublishedKeySet, PublishedView

#: The repository root the shipped documents are read from.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

SETTLEMENTS_DIRECTORY = "content/maps/settlements"
LOCATIONS_PATH = "content/maps/locations.yaml"
CONTINENT_PATH = "content/maps/continent.yaml"


class SettlementError(ValueError):
    """A settlement candidate cannot be published.

    ``problems`` names every rejected declaration or join, in a deterministic
    order, so a caller can report the complete candidate failure at once.
    """

    def __init__(self, problems: tuple[str, ...] | list[str]) -> None:
        self.problems = tuple(problems)
        super().__init__(
            "invalid settlement candidate:\n" + "\n".join(f"- {item}" for item in self.problems)
        )


class SettlementNotLoaded(RuntimeError):
    """A consumer read the settlement domain before any candidate was published."""


@dataclass(frozen=True, slots=True)
class SettlementSnapshot:
    """One immutable, validated settlement world.

    The typed documents are retained because consumers (and the editor's
    external context) need authored identity and provenance; the composed
    mappings are the game-facing views. ``graphs`` and ``city_gates`` are keyed
    by the authored settlement (map) identity; ``anchor_placements``,
    ``local_frame_anchors`` and ``wilderness_entries`` are keyed by the
    ``location_ref`` that binds them, because that is the anchor identity a
    geographic location navigates by and the identity a gate exit persists in
    ``db.anchor_key``.
    """

    settlements: Mapping[str, SettlementDocument]
    graphs: Mapping[str, SparseSettlementGraph]
    anchor_placements: Mapping[str, AnchorPlacement]
    local_frame_anchors: Mapping[str, LocalFrameAnchor]
    city_gates: Mapping[str, CityGateDef]
    wilderness_entries: Mapping[str, WildernessEntryPoint]
    grid_node_scene_archetypes: Mapping[QualifiedRef, str]
    fingerprints: Mapping[str, str] = field(default_factory=dict)

    @property
    def identity(self) -> str:
        """A stable digest of the authored source set this snapshot came from."""

        digest = hashlib.sha256()
        for path in sorted(self.fingerprints):
            digest.update(path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(self.fingerprints[path].encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()

    @property
    def reference_index(self) -> ReferenceIndex:
        """The settlement-node bindings every qualified target resolves against."""

        return ReferenceIndex.build(
            settlement_nodes=[
                (settlement_id, node_id, node.coordinate)
                for settlement_id, graph in self.graphs.items()
                for node_id, node in graph.nodes.items()
            ]
        )

    @property
    def node_extents(self) -> Mapping[str, frozenset[tuple[int, int]]]:
        """The authored node coordinates of every map in this world."""

        return MappingProxyType(
            {
                settlement_id: frozenset(node.coordinate for node in graph.nodes.values())
                for settlement_id, graph in self.graphs.items()
            }
        )


def parse_settlement_documents(
    sources: Iterable[SourceDocument], locations_text: str
) -> tuple[
    Mapping[str, SettlementDocument],
    LocationsDocument,
    dict[str, str],
]:
    """Parse one candidate source set from explicit text (no file access).

    The candidate set is rejected as a whole when a path is supplied twice, when
    a document is not a settlement document, or when two documents claim one
    identity (the ``id`` must equal the file stem, which the codec enforces).
    """

    problems: list[str] = []
    seen_paths: set[str] = set()
    documents: dict[str, SettlementDocument] = {}
    paths: dict[str, str] = {}
    fingerprints: dict[str, str] = {}
    for source in sorted(sources, key=lambda item: item.relative_path):
        path = source.relative_path.replace("\\", "/")
        if path in seen_paths:
            problems.append(f"{path} is supplied more than once")
            continue
        seen_paths.add(path)
        parsed = parse_document(path, source.text)
        if parsed.kind != "settlement":
            problems.append(f"{path} is a {parsed.kind!r} document, not a settlement")
            continue
        previous = paths.get(parsed.identity)
        if previous is not None:
            problems.append(
                f"settlement identity {parsed.identity!r} is declared by "
                f"{previous} and {path}"
            )
            continue
        paths[parsed.identity] = path
        documents[parsed.identity] = parsed.document
        fingerprints[path] = source.fingerprint
    locations = parse_document(LOCATIONS_PATH, locations_text)
    fingerprints[LOCATIONS_PATH] = fingerprint_text(locations_text)
    if not documents and not problems:
        problems.append(f"no {SETTLEMENTS_DIRECTORY}/*.yaml document is present")
    if problems:
        raise SettlementError(problems)
    return MappingProxyType(documents), locations.document, fingerprints


def _compose_document(
    document: SettlementDocument,
    locations: LocationsDocument,
    problems: list[str],
) -> tuple[
    SparseSettlementGraph | None,
    AnchorPlacement | None,
    LocalFrameAnchor | None,
    CityGateDef | None,
    WildernessEntryPoint | None,
    dict[QualifiedRef, str],
]:
    """Validate one settlement's declaration and compose its derived views."""

    from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY

    settlement_id = document.identity
    defects: list[str] = []

    def fail(message: str) -> None:
        defects.append(f"settlement {settlement_id!r}: {message}")

    try:
        graph = build_settlement_graph(settlement_id, document)
    except SparseGraphError as error:
        fail(f"does not form a sparse graph: {error}")
        graph = None

    location = locations.locations.get(document.location_ref)
    if location is None:
        fail(f"location_ref {document.location_ref!r} is not an authored location")

    anchor_nodes = [
        node
        for node in document.nodes.values()
        if node.prototype_parent == "anchor_room"
    ]
    anchor = None
    if len(anchor_nodes) != 1:
        fail(f"declares {len(anchor_nodes)} anchor_room nodes, expected exactly one")
    else:
        anchor = anchor_nodes[0]
        if anchor.anchor_key != document.location_ref:
            fail(
                f"anchor node {anchor.node_id!r} declares anchor_key "
                f"{anchor.anchor_key!r}, expected the location_ref "
                f"{document.location_ref!r}"
            )
        if document.binding.local_anchor_m != (anchor.x_m, anchor.y_m):
            fail(
                f"binding local_anchor_m {document.binding.local_anchor_m} disagrees "
                f"with anchor node {anchor.node_id!r} at "
                f"{(anchor.x_m, anchor.y_m)}"
            )
    if location is not None and document.binding.anchor_cell != location.cell:
        fail(
            f"binding anchor_cell {document.binding.anchor_cell} disagrees with "
            f"location {document.location_ref!r} cell {location.cell}"
        )

    scene_archetypes: dict[QualifiedRef, str] = {}
    for node in document.nodes.values():
        if node.scene_archetype is None:
            continue
        if node.scene_archetype not in SCENE_ARCHETYPE_REGISTRY:
            fail(
                f"node {node.node_id!r} names unregistered scene archetype "
                f"{node.scene_archetype!r}"
            )
            continue
        scene_archetypes[settlement_node_ref(settlement_id, node.node_id)] = (
            node.scene_archetype
        )

    city_gate = None
    if document.city_gate is not None:
        if document.city_gate.node not in document.nodes:
            fail(f"city_gate.node {document.city_gate.node!r} is not an authored node")
        else:
            city_gate = CityGateDef(
                gate=settlement_node_ref(settlement_id, document.city_gate.node),
                exit_key=document.city_gate.exit_key,
                exit_aliases=document.city_gate.exit_aliases,
            )

    wilderness_entry = None
    if document.wilderness_entry is not None:
        entry = document.wilderness_entry
        unknown = [
            gate.destination_node
            for gate in entry.gates
            if gate.destination_node not in document.nodes
        ]
        for node_id in unknown:
            fail(f"wilderness gate destination {node_id!r} is not an authored node")
        if not unknown:
            wilderness_entry = WildernessEntryPoint(
                anchor_key=document.location_ref,
                shape=entry.shape,
                origin_xy=entry.origin,
                gates=tuple(
                    WildernessGate(
                        gate.return_direction,
                        settlement_node_ref(settlement_id, gate.destination_node),
                    )
                    for gate in entry.gates
                ),
            )

    problems.extend(defects)
    if defects:
        return None, None, None, None, None, {}

    assert anchor is not None and location is not None
    placement = AnchorPlacement(
        anchor_key=document.location_ref,
        node=settlement_node_ref(settlement_id, anchor.node_id),
    )
    frame = LocalFrameAnchor(document.location_ref, document.binding.local_anchor_m)
    return graph, placement, frame, city_gate, wilderness_entry, scene_archetypes


def build_settlements(
    settlements: Mapping[str, SettlementDocument],
    locations: LocationsDocument,
    *,
    frame_cells: int,
    fingerprints: Mapping[str, str] | None = None,
) -> SettlementSnapshot:
    """Validate one candidate and compose its immutable game views.

    Every rejection a published consumer could later trip over (duplicate
    location binding, a binding that disagrees with its anchor node or
    location, an unknown gate destination, an unregistered scene archetype and
    the terrain-independent wilderness footprint/gate rules) is completed here.
    Terrain-dependent wilderness checks belong to the geography candidate,
    which re-runs the same validator against its own frame and walkability.
    ``frame_cells`` is the authored continental frame the wilderness cells are
    measured against; it bounds the footprint cells and gate-approach walks.
    """

    problems: list[str] = []
    graphs: dict[str, SparseSettlementGraph] = {}
    placements: dict[str, AnchorPlacement] = {}
    frames: dict[str, LocalFrameAnchor] = {}
    city_gates: dict[str, CityGateDef] = {}
    entries: dict[str, WildernessEntryPoint] = {}
    scene_archetypes: dict[QualifiedRef, str] = {}

    for settlement_id in sorted(settlements):
        document = settlements[settlement_id]
        graph, placement, frame, city_gate, entry, scenes = _compose_document(
            document, locations, problems
        )
        if graph is None or placement is None or frame is None:
            continue
        if document.location_ref in placements:
            problems.append(
                f"location {document.location_ref!r} is bound by more than one "
                f"settlement document"
            )
            continue
        graphs[settlement_id] = graph
        placements[document.location_ref] = placement
        frames[document.location_ref] = frame
        if city_gate is not None:
            city_gates[settlement_id] = city_gate
        if entry is not None:
            # Keyed by the anchor identity the gate exits persist
            # (``db.anchor_key``), so traversal and the local-map presenter
            # resolve the entry without an alias table.
            entries[entry.anchor_key] = entry
        scene_archetypes.update(scenes)

    for diag in diagnose_settlement_rules(
        settlements,
        locations=locations,
        frame_cells=frame_cells,
        terrain=None,
    ):
        if diag.message not in problems:
            problems.append(diag.message)

    if problems:
        raise SettlementError(problems)
    return SettlementSnapshot(
        settlements=MappingProxyType(dict(settlements)),
        graphs=MappingProxyType(graphs),
        anchor_placements=MappingProxyType(placements),
        local_frame_anchors=MappingProxyType(frames),
        city_gates=MappingProxyType(city_gates),
        wilderness_entries=MappingProxyType(entries),
        grid_node_scene_archetypes=MappingProxyType(scene_archetypes),
        fingerprints=MappingProxyType(dict(fingerprints or {})),
    )


_PUBLISHED: SettlementSnapshot | None = None


def _install(snapshot: SettlementSnapshot) -> SettlementSnapshot:
    """Bind one validated snapshot as this process's settlement world.

    The map composition root (``world.maps.runtime``) owns publication: it
    installs the four domain views of one bundle together, so no domain can be
    replaced on its own and no partial world can be observed.
    """

    global _PUBLISHED
    if not isinstance(snapshot, SettlementSnapshot):
        raise TypeError("_install() requires a SettlementSnapshot")
    _PUBLISHED = snapshot
    return snapshot


def current() -> SettlementSnapshot:
    """The published settlement world.

    Raises :class:`SettlementNotLoaded` instead of loading implicitly: every
    process entry point adopts the complete map world before any read-only
    consumer runs.
    """

    snapshot = _PUBLISHED
    if snapshot is None:
        raise SettlementNotLoaded(
            "settlement maps are not loaded; adopt the map world with "
            "world.maps.runtime before using map consumers"
        )
    return snapshot


def is_published() -> bool:
    """Whether a settlement snapshot has been published in this process."""

    return _PUBLISHED is not None


#: The composed sparse graphs of the published settlements, keyed by map id.
SETTLEMENT_GRAPHS: Mapping[str, SparseSettlementGraph] = PublishedView("graphs")

#: The declared map identities (``z`` coordinates) of the published settlements.
KNOWN_GRID_MAP_KEYS = PublishedKeySet("graphs")


def settlement_graph(map_id: str) -> SparseSettlementGraph | None:
    """Return the declared sparse graph for ``map_id``, or ``None``."""

    return SETTLEMENT_GRAPHS.get(map_id)


__all__ = [
    "KNOWN_GRID_MAP_KEYS",
    "LOCATIONS_PATH",
    "REPOSITORY_ROOT",
    "SETTLEMENTS_DIRECTORY",
    "SETTLEMENT_GRAPHS",
    "SettlementError",
    "SettlementNotLoaded",
    "SettlementSnapshot",
    "build_settlements",
    "current",
    "is_published",
    "parse_settlement_documents",
    "settlement_graph",
]
