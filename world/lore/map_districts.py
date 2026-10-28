"""Explicitly loaded map districts and their runtime validation (map-districts).

``content/maps/districts.yaml`` is the sole authority for the districts of the
world map: each district's identity, Traditional Chinese names, kind, terrain
region membership and its one stable discovery landmark (world-map drawer
design §4.1). A landmark is a qualified authored identity (a settlement node,
an authored location or an explicitly typed wilderness cell), never a
coordinate: its canonical ``grid:``/``wild:`` node is derived from the current
binding by :func:`landmark_node_ids`. A district is lit for a player only when
that canonical node is in the player's visited map knowledge; the read-only
lighting rule lives in ``world.rules.map_district_lighting``.

Two kinds exist:

* ``voronoi`` districts are seeds of the walking-distance partition that the
  offline generator computes. Their landmarks keep at least
  :data:`MIN_VORONOI_SPACING_KM` apart.
* ``region`` districts take every cell of one terrain region. The northern
  deep forest is the single region district: one landmark deep inside covers
  the whole forest across both nominal claims, so it is deliberately hard to
  light.

Nothing here loads at import time. The game composition root (and tests) call
:func:`load_and_publish`, and every read-only consumer goes through
:func:`current`. :func:`load_districts` returns a candidate snapshot even when
the terrain rules report saveable work-in-progress diagnostics;
:func:`publish` rejects a candidate carrying any diagnostic, so runtime
adoption never precedes a rejection and a failed candidate leaves the
previously published snapshot untouched.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Protocol

from elosern_map_core.codec import parse_document
from elosern_map_core.diagnostics import (
    SEMANTIC,
    STRUCTURE,
    AuthoringError,
    Diagnostic,
    sorted_diagnostics,
)
from elosern_map_core.documents import DistrictDeclaration, DistrictsDocument
from elosern_map_core.geometry import cell_center_m
from elosern_map_core.references import (
    ReferenceError,
    resolve_reference,
)
from elosern_map_core.sources import read_source_document

#: The repository root the shipped document is read from.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

DISTRICTS_PATH = "content/maps/districts.yaml"

#: The single spacing rule: two Voronoi landmarks are never closer than this
#: straight-line distance (world-map drawer design §4.1). It sits well below
#: the roughly 200 km district target, so authored seeds may cluster where the
#: land is narrow without producing slivers.
MIN_VORONOI_SPACING_KM = 100

#: The landmark domains a continental district may project. The one vocabulary
#: lives with the static-reference boundary, because a landmark is exactly a
#: qualified static target that must resolve there.
from world.maps.static_references import LANDMARK_DOMAINS  # noqa: E402

#: Landmark diagnostics that describe a real authored identity but no usable
#: continental projection yet; they stay loadable as saveable work in progress.
_UNBOUND = "unbound_landmark"


class DistrictError(ValueError):
    """A district candidate was rejected; ``diagnostics`` names every fault."""

    def __init__(self, diagnostics: tuple[Diagnostic, ...]) -> None:
        self.diagnostics = sorted_diagnostics(diagnostics)
        super().__init__(
            "invalid map districts:\n"
            + "\n".join(
                f"{item.relative_path or DISTRICTS_PATH}:"
                f"{item.field_path or '<document>'}: "
                f"{item.code}: {item.message}"
                for item in self.diagnostics
            )
        )


class DistrictNotLoaded(RuntimeError):
    """A consumer read the district domain before any candidate was published."""


@dataclass(frozen=True, slots=True)
class DistrictSnapshot:
    """One immutable, validated district world.

    The typed document is retained because consumers (and the editor's external
    context) need authored identity and provenance; ``districts`` is the
    game-facing view. ``diagnostics`` holds the terrain-dependent semantic
    findings of this candidate: a snapshot may load with unfinished geographic
    work, but :func:`publish` refuses it.
    """

    document: DistrictsDocument
    districts: Mapping[str, DistrictDeclaration]
    diagnostics: tuple[Diagnostic, ...] = ()
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


@dataclass(frozen=True)
class GridSite:
    """A grid landmark resolved into the continental frame."""

    position_m: tuple[int, int]
    reachable: bool


class DistrictTerrain(Protocol):
    """The terrain and settlement facts validation reads.

    The production implementation is :class:`_ProductionTerrain`; tests pass
    a synthetic one so the rules are exercised without shipped geography.
    """

    wilderness_name: str
    max_cell: tuple[int, int]
    region_keys: frozenset[str]

    def is_land(self, cell: tuple[int, int]) -> bool: ...

    def is_walkable(self, cell: tuple[int, int]) -> bool: ...

    def is_reachable(self, cell: tuple[int, int]) -> bool: ...

    def region_of(self, cell: tuple[int, int]) -> str: ...

    def grid_site(self, map_key: str, xy: tuple[int, int]) -> GridSite | None: ...


def cell_of_position(position_m: tuple[int, int]) -> tuple[int, int]:
    """The one-kilometre wilderness cell containing an absolute metre point."""
    return (position_m[0] // 1000, position_m[1] // 1000)


class _ProductionTerrain:
    """One geography snapshot's terrain, settlement graphs and gateway registry.

    Every geography-dependent operation is bound to the snapshot this adapter
    was built from (including the reachability index), so a retained adapter
    never mixes an older world's components with a newly published classifier.
    """

    def __init__(self, snapshot=None, settlements=None) -> None:
        from world.maps.geography import current
        from world.maps.wilderness_provider import WILDERNESS_NAME
        from world.maps.wilderness_reachability import walkable_components

        self._geography = snapshot if snapshot is not None else current()
        if settlements is None:
            from world.maps.map_data import current as current_settlements

            settlements = current_settlements()
        self._settlements = settlements
        self._terrain = self._geography.terrain
        self.wilderness_name = WILDERNESS_NAME
        self.max_cell = (self._geography.max_x, self._geography.max_y)
        self.region_keys = frozenset(self._geography.regions)
        self._components = walkable_components(
            self._geography, entries=self._settlements.wilderness_entries
        )
        self._entries = tuple(self._gateway_entries())
        # Players leave settlements through gateway approaches, so a cell is
        # reachable when it shares a component with any of them. The shipped
        # approaches all lie in one component, so no isolated pocket counts.
        self._reachable_components = frozenset(
            component
            for _, _, approach in self._entries
            if (component := self._components.component(approach)) is not None
        )

    def _gateway_entries(self):
        """``(z_map_key, gate grid_xy, approach cell)`` of every registered gate.

        Approaches are derived against this adapter's own frame bounds, so a
        retained adapter never borrows another world's rectangle.
        """
        from elosern_map_core.references import settlement_position

        bounds = (self._geography.max_x, self._geography.max_y)
        index = self._settlements.reference_index
        for entry in self._settlements.wilderness_entries.values():
            for gate in entry.gates:
                approach = entry.approach_cell(gate, bounds=bounds)
                if approach is not None:
                    yield (
                        gate.z_map_key,
                        settlement_position(
                            index, gate.destination, source="wilderness gate"
                        ),
                        approach,
                    )

    def is_land(self, cell):
        from elosern_map_core import terrain as core_terrain

        return core_terrain.is_land_cell(self._terrain, cell)

    def is_walkable(self, cell):
        from elosern_map_core import terrain as core_terrain

        return core_terrain.is_valid_wilderness_cell(
            self._terrain, self._components.footprints, cell
        )

    def is_reachable(self, cell):
        component = self._components.component(cell)
        return component is not None and component in self._reachable_components

    def region_of(self, cell):
        from elosern_map_core import terrain as core_terrain

        return core_terrain.region_for_coordinates(self._terrain, *cell)

    def grid_site(self, map_key, xy):
        from elosern_map_core.geometry import local_to_world_m

        graph = self._settlements.graphs.get(map_key)
        node = graph.node_at(xy) if graph is not None else None
        if node is None:
            return None
        anchor_key = next(
            (
                placement.anchor_key
                for placement in self._settlements.anchor_placements.values()
                if placement.zcoord == map_key
                and placement.anchor_key in self._settlements.local_frame_anchors
            ),
            None,
        )
        if anchor_key is None:
            return None
        position = local_to_world_m(
            self._geography.anchor_geography[anchor_key].cell,
            self._settlements.local_frame_anchors[anchor_key].local_anchor_m,
            node.physical_coordinate,
        )
        reachable = False
        for gate_map, gate_xy, approach in self._entries:
            gate_node = graph.node_at(gate_xy) if gate_map == map_key else None
            if gate_node is None or not self.is_reachable(approach):
                continue
            if graph.route(gate_node.node_id, node.node_id) is not None:
                reachable = True
                break
        return GridSite(position_m=position, reachable=reachable)


def production_terrain() -> DistrictTerrain:
    """The live terrain the shipped document is validated against."""
    return _ProductionTerrain()


def candidate_terrain(geography_snapshot, settlements) -> DistrictTerrain:
    """One candidate world's terrain, for validating that candidate's districts.

    The adapter is bound to the candidate geography *and* the candidate
    settlements, so a district is never projected through the previously
    published graphs or anchor placements.
    """

    return _ProductionTerrain(geography_snapshot, settlements)


def landmark_node_ids(
    districts: Mapping[str, DistrictDeclaration] | None = None,
    *,
    index=None,
) -> dict[str, str]:
    """Every district's canonical map-knowledge node ID at its current binding.

    The wire form stays exactly the existing grammar (``wild:<name>:<x>:<y>``
    or ``grid:<map>:<x>:<y>``); only its source changes from a stored string to
    the landmark's resolved identity. A landmark that cannot produce a
    canonical visited node (an invalid or interior-room reference in a patched
    registry) is omitted here -- validation is the gate that rejects it.
    """

    from world.maps.static_references import map_reference_index, resolve_static
    from world.maps.wilderness_provider import WILDERNESS_NAME
    from world.rules.map_knowledge import encode_grid, encode_wild

    registry = current().districts if districts is None else districts
    bindings = index if index is not None else map_reference_index()
    result: dict[str, str] = {}
    for key, district in registry.items():
        try:
            resolved = resolve_static(
                district.landmark, index=bindings, source=f"district {key}"
            )
        except ReferenceError:  # observability: ignore R2: validation owns rejection; a presenter never invents a node id
            continue
        landmark = district.landmark
        if landmark.domain == "settlement_node" and resolved.position_m is not None:
            result[key] = encode_grid(
                landmark.map_id, resolved.position_m[0], resolved.position_m[1]
            )
        elif landmark.domain in ("wilderness_cell", "location") and resolved.cell is not None:
            result[key] = encode_wild(
                WILDERNESS_NAME, resolved.cell[0], resolved.cell[1]
            )
    return result


def landmark_node_id(district: DistrictDeclaration) -> str | None:
    """One district's canonical map-knowledge node ID, or ``None``."""

    resolved = landmark_node_ids({district.district_id: district})
    return resolved.get(district.district_id)


def _diagnostic(
    code: str,
    category: str,
    message: str,
    *,
    relative_path: str,
    field_path: str,
    object_id: str,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        category=category,
        message=message,
        relative_path=relative_path,
        field_path=field_path,
        object_id=object_id,
    )


def _landmark_projection(
    district: DistrictDeclaration,
    terrain: DistrictTerrain,
    bindings,
    *,
    relative_path: str,
    problems: list[Diagnostic],
) -> tuple[int, int] | None:
    """Resolve one qualified landmark to its absolute continental position."""

    key = district.district_id
    landmark = district.landmark
    field_path = f"districts.{key}.landmark"

    def fail(code: str, category: str, message: str) -> None:
        problems.append(
            _diagnostic(
                code,
                category,
                message,
                relative_path=relative_path,
                field_path=field_path,
                object_id=key,
            )
        )

    # An interior room has no continental position. This is the game's
    # projection policy, not a core authoring restriction: the authoring model
    # accepts a reachable interior-room landmark.
    if landmark.domain not in LANDMARK_DOMAINS:
        fail(
            "unsupported_landmark_domain",
            STRUCTURE,
            f"landmark {landmark.object_id!r} is a {landmark.domain!r} reference "
            f"with no continental map position; one of {LANDMARK_DOMAINS} is required",
        )
        return None
    try:
        resolved = resolve_reference(bindings, landmark, source=f"district {key}")
    except ReferenceError as error:
        fail(error.code, STRUCTURE, str(error))
        return None
    if resolved.cell is not None:
        cell = resolved.cell
        max_x, max_y = terrain.max_cell
        if cell[0] > max_x or cell[1] > max_y:
            fail(
                "invalid_reference",
                STRUCTURE,
                f"landmark {landmark.object_id or cell!r} is outside the "
                "wilderness frame",
            )
            return None
        if not terrain.is_land(cell):
            fail(
                "landmark_in_sea",
                SEMANTIC,
                f"landmark {landmark.object_id or cell!r} lies in the sea",
            )
            return None
        if not terrain.is_walkable(cell):
            fail(
                "landmark_blocked",
                SEMANTIC,
                f"landmark {landmark.object_id or cell!r} lies on blocked terrain",
            )
            return None
        if not terrain.is_reachable(cell):
            fail(
                "unreachable_landmark",
                SEMANTIC,
                f"landmark {landmark.object_id or cell!r} is unreachable",
            )
            return None
        return cell_center_m(cell)
    position = resolved.position_m
    if position is None:
        fail(
            _UNBOUND,
            SEMANTIC,
            f"landmark {landmark.object_id!r} has no map position",
        )
        return None
    site = terrain.grid_site(landmark.map_id, position)
    if site is None:
        fail(
            _UNBOUND,
            SEMANTIC,
            f"landmark {landmark.map_id}:{landmark.object_id} has no continental "
            "binding yet",
        )
        return None
    if not terrain.is_land(cell_of_position(site.position_m)):
        fail(
            "landmark_in_sea",
            SEMANTIC,
            f"landmark {landmark.map_id}:{landmark.object_id} lies in the sea",
        )
        return None
    if not site.reachable:
        fail(
            "unreachable_landmark",
            SEMANTIC,
            f"landmark {landmark.map_id}:{landmark.object_id} is unreachable",
        )
        return None
    return site.position_m


def diagnose_districts(
    districts: Mapping[str, DistrictDeclaration],
    *,
    terrain: DistrictTerrain | None = None,
    index=None,
    relative_path: str = DISTRICTS_PATH,
) -> tuple[Diagnostic, ...]:
    """Report every district fault as a typed diagnostic (never raises).

    Structure diagnostics (unknown region membership, an unsupported landmark
    domain, an unresolvable reference, duplicate identities) block authoring and
    are raised by :func:`build_districts`. Semantic diagnostics (sea, blocked
    or unreachable ground, an unbound grid projection, landmark/region
    disagreement and the Voronoi spacing rule) are saveable work in progress:
    the candidate loads, and runtime adoption rejects it.
    """

    land = production_terrain() if terrain is None else terrain
    if index is None:
        from world.maps.static_references import map_reference_index

        index = map_reference_index()
    problems: list[Diagnostic] = []

    def fail(key: str, code: str, category: str, rule: str, field_path: str) -> None:
        problems.append(
            _diagnostic(
                code,
                category,
                rule,
                relative_path=relative_path,
                field_path=field_path,
                object_id=key,
            )
        )

    seen: dict[str, dict[object, str]] = {
        "landmark": {},
        "district_name_zh": {},
        "landmark_name_zh": {},
        "region_key": {},
    }
    positions: list[tuple[DistrictDeclaration, tuple[int, int]]] = []
    region_claims: set[str] = set()
    for key, district in districts.items():
        if not isinstance(district, DistrictDeclaration):
            fail(
                str(key),
                "invalid_declaration",
                STRUCTURE,
                "entry is not a district declaration",
                f"districts.{key}",
            )
            continue
        if district.district_id != key:
            fail(
                str(key),
                "identity_mismatch",
                STRUCTURE,
                f"registered under a different key than {district.district_id!r}",
                f"districts.{key}",
            )
        for field in ("district_name_zh", "landmark_name_zh", "kind"):
            value = getattr(district, field)
            if not isinstance(value, str) or not value.strip():
                fail(
                    district.district_id,
                    "invalid_field",
                    STRUCTURE,
                    f"{field} is empty",
                    f"districts.{key}.{field}",
                )
        if district.kind == "region":
            if district.region_key not in land.region_keys:
                fail(
                    district.district_id,
                    "unknown_region",
                    STRUCTURE,
                    f"region_key {district.region_key!r} is not a terrain region",
                    f"districts.{key}.region_key",
                )
            else:
                region_claims.add(district.region_key)
        elif district.region_key is not None:
            fail(
                district.district_id,
                "invalid_region_membership",
                STRUCTURE,
                "a voronoi district declares no region_key",
                f"districts.{key}.region_key",
            )
        for field, owners in seen.items():
            value = getattr(district, field)
            if value is None or (field == "region_key" and district.kind != "region"):
                continue
            if value in owners:
                fail(
                    district.district_id,
                    f"duplicate_{field}",
                    STRUCTURE,
                    f"duplicate {field} {value!r} (also {owners[value]!r})",
                    f"districts.{key}.{field}",
                )
            else:
                owners[value] = district.district_id
        position = _landmark_projection(
            district,
            land,
            index,
            relative_path=relative_path,
            problems=problems,
        )
        if position is not None:
            positions.append((district, position))

    voronoi: list[tuple[str, tuple[int, int]]] = []
    for district, position in positions:
        key = district.district_id
        region = land.region_of(cell_of_position(position))
        if (
            district.kind == "region"
            and district.region_key in land.region_keys
            and region != district.region_key
        ):
            fail(
                key,
                "region_mismatch",
                SEMANTIC,
                f"landmark lies in region {region!r}, not {district.region_key!r}",
                f"districts.{key}.landmark",
            )
        elif district.kind == "voronoi":
            if region in region_claims:
                fail(
                    key,
                    "region_territory_overlap",
                    SEMANTIC,
                    f"landmark lies inside region district territory {region!r}",
                    f"districts.{key}.landmark",
                )
            voronoi.append((key, position))

    minimum_m = MIN_VORONOI_SPACING_KM * 1000
    for position_index, (key, position) in enumerate(voronoi):
        for other_key, other in voronoi[position_index + 1 :]:
            distance = math.hypot(position[0] - other[0], position[1] - other[1])
            if distance < minimum_m:
                fail(
                    key,
                    "invalid_spacing",
                    SEMANTIC,
                    f"landmark is {distance / 1000:.1f} km from {other_key!r}, "
                    f"below the {MIN_VORONOI_SPACING_KM} km minimum spacing",
                    f"districts.{key}.landmark",
                )
    return sorted_diagnostics(problems)


def build_districts(
    document: DistrictsDocument,
    *,
    terrain: DistrictTerrain | None = None,
    index=None,
    fingerprints: Mapping[str, str] | None = None,
) -> DistrictSnapshot:
    """Validate one candidate document and compose its immutable snapshot.

    Structure faults raise :class:`DistrictError`; semantic faults are retained
    on the returned snapshot and reject publication in :func:`publish`.
    """

    problems = diagnose_districts(
        document.districts,
        terrain=terrain,
        index=index,
        relative_path=document.relative_path,
    )
    blocking = tuple(item for item in problems if item.category == STRUCTURE)
    if blocking:
        raise DistrictError(blocking)
    supplied = (
        {document.relative_path: document.fingerprint}
        if fingerprints is None
        else dict(fingerprints)
    )
    return DistrictSnapshot(
        document=document,
        districts=MappingProxyType(dict(document.districts)),
        diagnostics=tuple(item for item in problems if item.category == SEMANTIC),
        fingerprints=MappingProxyType(supplied),
    )


def parse_districts_document(text: str) -> DistrictsDocument:
    """Parse the canonical document from explicit text (no file access)."""

    return parse_document(DISTRICTS_PATH, text).document


_PUBLISHED: DistrictSnapshot | None = None


def _install(snapshot: DistrictSnapshot) -> DistrictSnapshot:
    """Bind one validated snapshot as this process's district world.

    The map composition root (``world.maps.runtime``) owns publication: it
    installs the four domain views of one bundle together, so no domain can be
    replaced on its own and no partial world can be observed.
    """

    global _PUBLISHED
    if not isinstance(snapshot, DistrictSnapshot):
        raise TypeError("_install() requires a DistrictSnapshot")
    _PUBLISHED = snapshot
    return snapshot


def current() -> DistrictSnapshot:
    """The published district world.

    Raises :class:`DistrictNotLoaded` instead of loading implicitly: every
    process entry point adopts the complete map world before any read-only
    consumer runs.
    """

    snapshot = _PUBLISHED
    if snapshot is None:
        raise DistrictNotLoaded(
            "map districts are not loaded; adopt the map world with "
            "world.maps.runtime before using map consumers"
        )
    return snapshot


def is_published() -> bool:
    """Whether a district snapshot has been published in this process."""

    return _PUBLISHED is not None


__all__ = [
    "DISTRICTS_PATH",
    "LANDMARK_DOMAINS",
    "MIN_VORONOI_SPACING_KM",
    "DistrictError",
    "DistrictNotLoaded",
    "DistrictSnapshot",
    "DistrictTerrain",
    "GridSite",
    "build_districts",
    "cell_of_position",
    "current",
    "diagnose_districts",
    "is_published",
    "landmark_node_id",
    "landmark_node_ids",
    "parse_districts_document",
    "production_terrain",
    "candidate_terrain",
]
