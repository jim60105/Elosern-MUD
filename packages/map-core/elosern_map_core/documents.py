"""Typed, immutable authoring documents.

Each supported kind has a frozen document wrapper that exposes the validated
values as typed declarations. The wrappers hold plain immutable mappings for
arbitrary field access (``data``) and typed tuples/mappings for the domain
values consumers read (nodes, roads, regions, rooms, ...). Nothing here reads
the filesystem, a clock, a database or a game module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from .diagnostics import SourceLocation

Cell = tuple[int, int]
PointM = tuple[int, int]


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _cell(value: Mapping[str, Any]) -> Cell:
    return (int(value["cell_x"]), int(value["cell_y"]))


def _point_m(value: Mapping[str, Any]) -> PointM:
    return (int(value["east_m"]), int(value["north_m"]))


@dataclass(frozen=True, slots=True)
class QualifiedRef:
    """A tagged, domain-qualified authored reference."""

    domain: str
    map_id: str | None = None
    object_id: str | None = None
    cell: Cell | None = None


@dataclass(frozen=True, slots=True)
class Bend:
    x_m: int
    y_m: int


@dataclass(frozen=True, slots=True)
class NodeDeclaration:
    node_id: str
    x_m: int
    y_m: int
    key: str
    desc: str
    prototype_parent: str
    anchor_key: str | None = None
    typeclass: str | None = None
    scene_archetype: str | None = None

    @property
    def coordinate(self) -> PointM:
        return (self.x_m, self.y_m)


@dataclass(frozen=True, slots=True)
class RoadDeclaration:
    source: str
    destination: str
    direction: str
    bends: tuple[Bend, ...] = ()


@dataclass(frozen=True, slots=True)
class GateDeclaration:
    return_direction: str
    destination_node: str


@dataclass(frozen=True, slots=True)
class WildernessEntryDeclaration:
    shape: tuple[str, ...]
    origin: Cell
    gates: tuple[GateDeclaration, ...]

    @property
    def hash_cell_count(self) -> int:
        return sum(row.count("#") for row in self.shape)

    @property
    def is_point_shape(self) -> bool:
        return self.hash_cell_count == 1

    @property
    def footprint_cells(self) -> frozenset[Cell]:
        if self.is_point_shape:
            return frozenset()
        origin_x, origin_y = self.origin
        return frozenset(
            (origin_x + column, origin_y + row)
            for row, line in enumerate(self.shape)
            for column, character in enumerate(line)
            if character == "#"
        )

    @property
    def anchor_cell(self) -> Cell | None:
        cells = [
            (column, row)
            for row, line in enumerate(self.shape)
            for column, character in enumerate(line)
            if character == "#"
        ]
        if not cells:
            return None
        min_x = min(column for column, _ in cells)
        max_x = max(column for column, _ in cells)
        min_y = min(row for _, row in cells)
        max_y = max(row for _, row in cells)
        origin_x, origin_y = self.origin
        return (origin_x + (min_x + max_x) // 2, origin_y + (min_y + max_y) // 2)


@dataclass(frozen=True, slots=True)
class CityGateDeclaration:
    node: str
    exit_key: str
    exit_aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BindingDeclaration:
    anchor_cell: Cell
    local_anchor_m: PointM


@dataclass(frozen=True, slots=True)
class RegionDeclaration:
    region_id: str
    display_name_zh: str
    nation_key: str | None
    terrain_flavor_zh: tuple[str, ...]
    nominal_nation_keys: tuple[str, ...]
    scene_archetype: str | None


@dataclass(frozen=True, slots=True)
class HarborSiteDeclaration:
    site_id: str
    display_name: str
    cell: Cell
    role: str


@dataclass(frozen=True, slots=True)
class WaterwayDeclaration:
    waterway_id: str
    route: tuple[Cell, ...]
    fords: tuple[Cell, ...]


@dataclass(frozen=True, slots=True)
class TerrainDeclaration:
    frame_cells: int
    cell_size_km: int
    mainland_boundary_km: tuple[tuple[int, int], ...]
    forest_edge: tuple[Cell, ...]
    ridge_base_x: int
    ridge_period: int
    ridge_step: int
    ridge_min_x: int
    ridge_max_x: int
    ridge_north_limit_y: int
    ridge_corridor_half_width: int
    ridge_passes: tuple[tuple[int, int], ...]
    coastal_y_max: int
    waterways: Mapping[str, WaterwayDeclaration]
    border_river_key: str


@dataclass(frozen=True, slots=True)
class LocationDeclaration:
    location_id: str
    kind: str
    display_name_zh: str
    description: str
    cell: Cell
    geographic_constraint: str
    scene_archetype: str | None


@dataclass(frozen=True, slots=True)
class DistrictDeclaration:
    district_id: str
    district_name_zh: str
    landmark_name_zh: str
    landmark: QualifiedRef
    kind: str
    region_key: str | None


@dataclass(frozen=True, slots=True)
class InteriorRoomDeclaration:
    room_id: str
    name_zh: str
    desc_zh: str
    scene_archetype: str | None


@dataclass(frozen=True, slots=True)
class ConnectionDeclaration:
    source: str
    destination: str
    label: str


@dataclass(frozen=True, slots=True)
class InteriorLinkDeclaration:
    source_room: str
    target_interior: str
    target_room: str
    label: str
    return_label: str | None


@dataclass(frozen=True, slots=True)
class ExteriorDeclaration:
    settlement: str
    node: str
    doorway_key: str
    doorway_aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LayoutPosition:
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class AuthoringDocument:
    """Base of every typed document."""

    relative_path: str
    kind: str
    version: int
    identity: str
    fingerprint: str
    data: Mapping[str, Any]
    provenance: Mapping[str, SourceLocation]

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _freeze(self.data))
        object.__setattr__(
            self,
            "provenance",
            MappingProxyType(dict(self.provenance)),
        )


def _node(node_id: str, value: Mapping[str, Any]) -> NodeDeclaration:
    return NodeDeclaration(
        node_id=node_id,
        x_m=int(value["x_m"]),
        y_m=int(value["y_m"]),
        key=str(value["key"]),
        desc=str(value["desc"]),
        prototype_parent=str(value["prototype_parent"]),
        anchor_key=value.get("anchor_key"),
        typeclass=value.get("typeclass"),
        scene_archetype=value.get("scene_archetype"),
    )


def _road(value: Mapping[str, Any]) -> RoadDeclaration:
    return RoadDeclaration(
        source=str(value["source"]),
        destination=str(value["destination"]),
        direction=str(value["direction"]),
        bends=tuple(
            Bend(x_m=int(bend["x_m"]), y_m=int(bend["y_m"]))
            for bend in value.get("bends", ())
        ),
    )


def _qualified_ref(value: Mapping[str, Any]) -> QualifiedRef:
    cell = value.get("cell")
    return QualifiedRef(
        domain=str(value["domain"]),
        map_id=value.get("map_id"),
        object_id=value.get("object_id"),
        cell=_cell(cell) if cell is not None else None,
    )


@dataclass(frozen=True, slots=True)
class ContinentDocument(AuthoringDocument):
    regions: Mapping[str, RegionDeclaration] = field(init=False, repr=False)
    harbor_sites: Mapping[str, HarborSiteDeclaration] = field(init=False, repr=False)
    terrain: TerrainDeclaration = field(init=False, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        data = self.data
        regions = {
            key: RegionDeclaration(
                region_id=key,
                display_name_zh=str(value["display_name_zh"]),
                nation_key=value.get("nation_key"),
                terrain_flavor_zh=tuple(str(item) for item in value["terrain_flavor_zh"]),
                nominal_nation_keys=tuple(
                    str(item) for item in value.get("nominal_nation_keys", ())
                ),
                scene_archetype=value.get("scene_archetype"),
            )
            for key, value in data["regions"].items()
        }
        harbor_sites = {
            key: HarborSiteDeclaration(
                site_id=key,
                display_name=str(value["display_name"]),
                cell=_cell(value["cell"]),
                role=str(value["role"]),
            )
            for key, value in data["harbor_sites"].items()
        }
        terrain_data = data["terrain"]
        ridge = terrain_data["ridge"]
        waterways = {
            key: WaterwayDeclaration(
                waterway_id=key,
                route=tuple(_cell(cell) for cell in value["route"]),
                fords=tuple(_cell(cell) for cell in value.get("fords", ())),
            )
            for key, value in terrain_data["waterways"].items()
        }
        terrain = TerrainDeclaration(
            frame_cells=int(data["frame_cells"]),
            cell_size_km=int(data["cell_size_km"]),
            mainland_boundary_km=tuple(
                (int(vertex["east_km"]), int(vertex["north_km"]))
                for vertex in data["mainland_boundary_km"]
            ),
            forest_edge=tuple(_cell(cell) for cell in terrain_data["forest_edge"]),
            ridge_base_x=int(ridge["base_x"]),
            ridge_period=int(ridge["period"]),
            ridge_step=int(ridge["step"]),
            ridge_min_x=int(ridge["min_x"]),
            ridge_max_x=int(ridge["max_x"]),
            ridge_north_limit_y=int(ridge["north_limit_y"]),
            ridge_corridor_half_width=int(ridge["mountain_corridor_half_width"]),
            ridge_passes=tuple(
                (int(window["y_min"]), int(window["y_max"]))
                for window in ridge["passes"]
            ),
            coastal_y_max=int(terrain_data["coastal_y_max"]),
            waterways=MappingProxyType(waterways),
            border_river_key=str(terrain_data["border_river_key"]),
        )
        object.__setattr__(self, "regions", MappingProxyType(regions))
        object.__setattr__(self, "harbor_sites", MappingProxyType(harbor_sites))
        object.__setattr__(self, "terrain", terrain)


@dataclass(frozen=True, slots=True)
class LocationsDocument(AuthoringDocument):
    locations: Mapping[str, LocationDeclaration] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        locations = {
            key: LocationDeclaration(
                location_id=key,
                kind=str(value["kind"]),
                display_name_zh=str(value["display_name_zh"]),
                description=str(value["description"]),
                cell=_cell(value["cell"]),
                geographic_constraint=str(value["geographic_constraint"]),
                scene_archetype=value.get("scene_archetype"),
            )
            for key, value in self.data["locations"].items()
        }
        object.__setattr__(self, "locations", MappingProxyType(locations))


@dataclass(frozen=True, slots=True)
class DistrictsDocument(AuthoringDocument):
    districts: Mapping[str, DistrictDeclaration] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        districts = {
            key: DistrictDeclaration(
                district_id=key,
                district_name_zh=str(value["district_name_zh"]),
                landmark_name_zh=str(value["landmark_name_zh"]),
                landmark=_qualified_ref(value["landmark"]),
                kind=str(value["kind"]),
                region_key=value.get("region_key"),
            )
            for key, value in self.data["districts"].items()
        }
        object.__setattr__(self, "districts", MappingProxyType(districts))


@dataclass(frozen=True, slots=True)
class SettlementDocument(AuthoringDocument):
    location_ref: str = field(init=False, repr=False)
    binding: BindingDeclaration = field(init=False, repr=False)
    nodes: Mapping[str, NodeDeclaration] = field(init=False, repr=False)
    roads: tuple[RoadDeclaration, ...] = field(init=False, repr=False)
    wilderness_entry: WildernessEntryDeclaration | None = field(
        init=False, repr=False
    )
    city_gate: CityGateDeclaration | None = field(init=False, repr=False)
    options: Mapping[str, Any] = field(init=False, repr=False)
    exit_prototype: Mapping[str, Any] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        data = self.data
        entry_data = data.get("wilderness_entry")
        entry = None
        if entry_data is not None:
            entry = WildernessEntryDeclaration(
                shape=tuple(str(row) for row in entry_data["shape"]),
                origin=_cell(entry_data["origin"]),
                gates=tuple(
                    GateDeclaration(
                        return_direction=str(gate["return_direction"]),
                        destination_node=str(gate["destination_node"]),
                    )
                    for gate in entry_data["gates"]
                ),
            )
        gate_data = data.get("city_gate")
        city_gate = None
        if gate_data is not None:
            city_gate = CityGateDeclaration(
                node=str(gate_data["node"]),
                exit_key=str(gate_data["exit_key"]),
                exit_aliases=tuple(
                    str(alias) for alias in gate_data.get("exit_aliases", ())
                ),
            )
        object.__setattr__(self, "location_ref", str(data["location_ref"]))
        object.__setattr__(
            self,
            "binding",
            BindingDeclaration(
                anchor_cell=_cell(data["binding"]["anchor_cell"]),
                local_anchor_m=_point_m(data["binding"]["local_anchor_m"]),
            ),
        )
        object.__setattr__(
            self,
            "nodes",
            MappingProxyType(
                {key: _node(key, value) for key, value in data["nodes"].items()}
            ),
        )
        object.__setattr__(
            self,
            "roads",
            tuple(_road(value) for value in data["roads"]),
        )
        object.__setattr__(self, "wilderness_entry", entry)
        object.__setattr__(self, "city_gate", city_gate)
        object.__setattr__(
            self,
            "options",
            MappingProxyType(dict(data.get("options", {}))),
        )
        object.__setattr__(
            self,
            "exit_prototype",
            MappingProxyType(dict(data.get("exit_prototype", {}))),
        )

    @property
    def entry_nodes(self) -> frozenset[str]:
        """The authored nodes through which a traveller can enter the map."""

        nodes: set[str] = set()
        if self.wilderness_entry is not None:
            nodes.update(gate.destination_node for gate in self.wilderness_entry.gates)
        if self.city_gate is not None:
            nodes.add(self.city_gate.node)
        return frozenset(nodes)


@dataclass(frozen=True, slots=True)
class InteriorDocument(AuthoringDocument):
    rooms: Mapping[str, InteriorRoomDeclaration] = field(init=False, repr=False)
    connections: tuple[ConnectionDeclaration, ...] = field(init=False, repr=False)
    interior_links: tuple[InteriorLinkDeclaration, ...] = field(
        init=False, repr=False
    )
    exterior: ExteriorDeclaration | None = field(init=False, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        data = self.data
        exterior_data = data.get("exterior")
        exterior = None
        if exterior_data is not None:
            exterior = ExteriorDeclaration(
                settlement=str(exterior_data["settlement"]),
                node=str(exterior_data["node"]),
                doorway_key=str(exterior_data["doorway_key"]),
                doorway_aliases=tuple(
                    str(alias) for alias in exterior_data.get("doorway_aliases", ())
                ),
            )
        object.__setattr__(
            self,
            "rooms",
            MappingProxyType(
                {
                    key: InteriorRoomDeclaration(
                        room_id=key,
                        name_zh=str(value["name_zh"]),
                        desc_zh=str(value["desc_zh"]),
                        scene_archetype=value.get("scene_archetype"),
                    )
                    for key, value in data["rooms"].items()
                }
            ),
        )
        object.__setattr__(
            self,
            "connections",
            tuple(
                ConnectionDeclaration(
                    source=str(value["source"]),
                    destination=str(value["destination"]),
                    label=str(value["label"]),
                )
                for value in data["connections"]
            ),
        )
        object.__setattr__(
            self,
            "interior_links",
            tuple(
                InteriorLinkDeclaration(
                    source_room=str(value["source_room"]),
                    target_interior=str(value["target_interior"]),
                    target_room=str(value["target_room"]),
                    label=str(value["label"]),
                    return_label=value.get("return_label"),
                )
                for value in data.get("interior_links", ())
            ),
        )
        object.__setattr__(self, "exterior", exterior)


@dataclass(frozen=True, slots=True)
class LayoutDocument(AuthoringDocument):
    positions: Mapping[str, LayoutPosition] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(
            self,
            "positions",
            MappingProxyType(
                {
                    key: LayoutPosition(x=int(value["x"]), y=int(value["y"]))
                    for key, value in self.data["positions"].items()
                }
            ),
        )


DOCUMENT_CLASSES: dict[str, type[AuthoringDocument]] = {
    "continent": ContinentDocument,
    "locations": LocationsDocument,
    "districts": DistrictsDocument,
    "settlement": SettlementDocument,
    "interior": InteriorDocument,
    "layout": LayoutDocument,
}


def build_document(
    kind: str,
    *,
    relative_path: str,
    identity: str,
    version: int,
    fingerprint: str,
    data: Mapping[str, Any],
    provenance: Mapping[str, SourceLocation],
) -> AuthoringDocument:
    """Build the typed wrapper for one already-validated document value."""

    try:
        document_class = DOCUMENT_CLASSES[kind]
    except KeyError as error:  # pragma: no cover - schema validates the kind
        raise ValueError(f"unsupported document kind {kind!r}") from error
    document = document_class(
        relative_path=relative_path,
        kind=kind,
        version=version,
        identity=identity,
        fingerprint=fingerprint,
        data=data,
        provenance=provenance,
    )
    return document


__all__ = [
    "AuthoringDocument",
    "Bend",
    "BindingDeclaration",
    "CityGateDeclaration",
    "ConnectionDeclaration",
    "ContinentDocument",
    "DistrictDeclaration",
    "DistrictsDocument",
    "ExteriorDeclaration",
    "GateDeclaration",
    "HarborSiteDeclaration",
    "InteriorDocument",
    "InteriorLinkDeclaration",
    "InteriorRoomDeclaration",
    "LayoutDocument",
    "LayoutPosition",
    "LocationDeclaration",
    "LocationsDocument",
    "NodeDeclaration",
    "QualifiedRef",
    "RegionDeclaration",
    "RoadDeclaration",
    "SettlementDocument",
    "TerrainDeclaration",
    "WaterwayDeclaration",
    "WildernessEntryDeclaration",
    "build_document",
]
