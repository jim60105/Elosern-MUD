"""Frozen map-district registry and its authoring validation (map-districts).

Each district of the world map has exactly one landmark (world-map drawer
design §4.1). A district is lit for a player only when that landmark's exact
canonical node is in the player's visited map knowledge; the read-only
lighting rule lives in ``world.rules.map_district_lighting``. The world map
starts nearly empty and grows as landmarks are reached.

Two kinds exist:

* ``voronoi`` districts are seeds of the walking-distance partition that the
  later partition change computes. Their landmarks keep at least
  :data:`MIN_VORONOI_SPACING_KM` apart.
* ``region`` districts take every cell of one terrain region. The northern
  deep forest is the single region district: one landmark deep inside covers
  the whole forest across both nominal claims, so it is deliberately hard to
  light.

Declaring a district creates no room and reveals nothing. The registry is
validated by :func:`validate_map_districts` (pure, database-free); it is not a
startup synchronization step. Lore stays read-only: the terrain and settlement
lookups the validator needs are imported lazily from ``world.maps``, as
``world.lore.wilderness_entry`` does.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

#: The two district kinds.
DISTRICT_KINDS: tuple[str, ...] = ("voronoi", "region")

#: The single spacing rule: two Voronoi landmarks are never closer than this
#: straight-line distance (world-map drawer design §4.1). It sits well below
#: the roughly 200 km district target, so authored seeds may cluster where the
#: land is narrow without producing slivers.
MIN_VORONOI_SPACING_KM = 100

_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_NUMBER = r"(0|[1-9][0-9]*)"
_WILD_RE = re.compile(rf"^wild:([^:]+):{_NUMBER}:{_NUMBER}$")
_GRID_RE = re.compile(rf"^grid:([^:]+):{_NUMBER}:{_NUMBER}$")


@dataclass(frozen=True)
class MapDistrict:
    """One map district and its single discovery landmark.

    ``landmark_node`` is a canonical map-knowledge node ID:
    ``wild:elosern:<x>:<y>`` or an existing ``grid:<map>:<x>:<y>``.
    ``region_key`` names the terrain region a ``region`` district covers and
    is ``None`` for a ``voronoi`` district.
    """

    key: str
    district_name_zh: str
    landmark_name_zh: str
    landmark_node: str
    kind: str
    region_key: str | None = None


class MapDistrictError(ValueError):
    """A district registry failed validation; ``problems`` names every fault."""

    def __init__(self, problems: tuple[str, ...]) -> None:
        self.problems = problems
        super().__init__("invalid map districts:\n" + "\n".join(problems))


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


def _cell_center_m(cell: tuple[int, int]) -> tuple[int, int]:
    from world.lore.wilderness_regions import cell_center_m

    return cell_center_m(cell)


class _ProductionTerrain:
    """The live terrain model, settlement graphs and gateway registry."""

    def __init__(self) -> None:
        from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY
        from world.maps import wilderness_provider as provider
        from world.maps.wilderness_reachability import walkable_components

        self._provider = provider
        self.wilderness_name = provider.WILDERNESS_NAME
        self.max_cell = (provider.WILDERNESS_MAX_X, provider.WILDERNESS_MAX_Y)
        self.region_keys = frozenset(WILDERNESS_REGION_REGISTRY)
        self._components = walkable_components()
        self._entries = tuple(self._gateway_entries())
        self._reachable_components = frozenset(
            component
            for _, _, approach in self._entries
            if (component := self._components.component(approach)) is not None
        )

    @staticmethod
    def _gateway_entries():
        """``(z_map_key, gate grid_xy, approach cell)`` of every registered gate."""
        from world.lore import wilderness_entry

        for entry in wilderness_entry.WILDERNESS_ENTRY_REGISTRY.values():
            for gate in entry.gates:
                approach = entry.approach_cell(gate)
                if approach is not None:
                    yield gate.z_map_key, gate.grid_xy, approach

    def is_land(self, cell):
        return self._provider.is_land_cell(cell)

    def is_walkable(self, cell):
        return self._provider.is_valid_wilderness_cell(cell)

    def is_reachable(self, cell):
        component = self._components.component(cell)
        return component is not None and component in self._reachable_components

    def region_of(self, cell):
        return self._provider.region_for_coordinates(*cell)

    def grid_site(self, map_key, xy):
        from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
        from world.lore.anchors import LOCAL_FRAME_ANCHOR_REGISTRY, world_position_m
        from world.maps.map_data import settlement_graph

        graph = settlement_graph(map_key)
        node = graph.node_at(xy) if graph is not None else None
        if node is None:
            return None
        anchor_key = next(
            (
                placement.anchor_key
                for placement in ANCHOR_PLACEMENT_REGISTRY.values()
                if placement.zcoord == map_key
                and placement.anchor_key in LOCAL_FRAME_ANCHOR_REGISTRY
            ),
            None,
        )
        if anchor_key is None:
            return None
        position = world_position_m(anchor_key, node.physical_coordinate)
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
    """The live terrain the shipped registry is validated against."""
    return _ProductionTerrain()


def _landmark_position(
    district: MapDistrict, terrain: DistrictTerrain, fail
) -> tuple[int, int] | None:
    """Check one landmark node and return its absolute metre position."""
    node = district.landmark_node
    if not isinstance(node, str):
        fail(district.key, f"landmark_node {node!r} is not a string")
        return None
    wild = _WILD_RE.match(node)
    if wild is not None:
        name, x, y = wild.group(1), int(wild.group(2)), int(wild.group(3))
        max_x, max_y = terrain.max_cell
        if name != terrain.wilderness_name or x > max_x or y > max_y:
            fail(district.key, f"landmark_node {node!r} is not a canonical wilderness node")
            return None
        cell = (x, y)
        if not terrain.is_land(cell):
            fail(district.key, f"landmark {node!r} lies in the sea")
            return None
        if not terrain.is_walkable(cell):
            fail(district.key, f"landmark {node!r} lies on blocked terrain")
            return None
        if not terrain.is_reachable(cell):
            fail(district.key, f"landmark {node!r} is unreachable")
            return None
        return _cell_center_m(cell)
    grid = _GRID_RE.match(node)
    if grid is not None:
        map_key, x, y = grid.group(1), int(grid.group(2)), int(grid.group(3))
        site = terrain.grid_site(map_key, (x, y))
        if site is None:
            fail(district.key, f"landmark {node!r} is not an existing grid node")
            return None
        if not terrain.is_land(cell_of_position(site.position_m)):
            fail(district.key, f"landmark {node!r} lies in the sea")
            return None
        if not site.reachable:
            fail(district.key, f"landmark {node!r} is unreachable")
            return None
        return site.position_m
    fail(district.key, f"landmark_node {node!r} is not a canonical wild: or grid: node")
    return None


def validate_map_districts(
    registry: Mapping[str, MapDistrict] | None = None,
    terrain: DistrictTerrain | None = None,
) -> None:
    """Validate a district registry, raising :class:`MapDistrictError`.

    Every fault is collected and reported with its district key: identity and
    field shape, kind/region pairing, duplicate keys, landmark nodes and names,
    canonical landmark grammar, sea, blocked terrain, absent grid nodes,
    unreachable landmarks, region membership and the Voronoi spacing rule.
    """
    districts = MAP_DISTRICT_REGISTRY if registry is None else registry
    land = production_terrain() if terrain is None else terrain
    problems: list[str] = []

    def fail(key: str, rule: str) -> None:
        problems.append(f"{key}: {rule}")

    seen: dict[str, dict[object, str]] = {
        "landmark_node": {},
        "district_name_zh": {},
        "landmark_name_zh": {},
        "region_key": {},
    }
    positions: list[tuple[MapDistrict, tuple[int, int]]] = []
    region_claims: set[str] = set()
    for registry_key, district in districts.items():
        if not isinstance(district, MapDistrict):
            fail(str(registry_key), "entry is not a MapDistrict")
            continue
        if district.key != registry_key:
            fail(str(registry_key), f"registered under a different key than {district.key!r}")
        if not isinstance(district.key, str) or not _KEY_RE.match(district.key):
            fail(str(registry_key), "key is not a snake_case identifier")
        for field in ("district_name_zh", "landmark_name_zh"):
            value = getattr(district, field)
            if not isinstance(value, str) or not value.strip():
                fail(district.key, f"{field} is empty")
        if district.kind not in DISTRICT_KINDS:
            fail(district.key, f"kind {district.kind!r} is not one of {DISTRICT_KINDS}")
        elif district.kind == "region":
            if district.region_key not in land.region_keys:
                fail(district.key, f"region_key {district.region_key!r} is not a terrain region")
            else:
                region_claims.add(district.region_key)
        elif district.region_key is not None:
            fail(district.key, "a voronoi district declares no region_key")
        for field, owners in seen.items():
            value = getattr(district, field)
            if value is None or (field == "region_key" and district.kind != "region"):
                continue
            if value in owners:
                fail(district.key, f"duplicate {field} {value!r} (also {owners[value]!r})")
            else:
                owners[value] = district.key
        position = _landmark_position(district, land, fail)
        if position is not None:
            positions.append((district, position))

    voronoi: list[tuple[str, tuple[int, int]]] = []
    for district, position in positions:
        key = district.key
        region = land.region_of(cell_of_position(position))
        if district.kind == "region" and region != district.region_key:
            fail(key, f"landmark lies in region {region!r}, not {district.region_key!r}")
        elif district.kind == "voronoi":
            if region in region_claims:
                fail(key, f"landmark lies inside region district territory {region!r}")
            voronoi.append((key, position))

    minimum_m = MIN_VORONOI_SPACING_KM * 1000
    for index, (key, position) in enumerate(voronoi):
        for other_key, other in voronoi[index + 1 :]:
            distance = math.hypot(position[0] - other[0], position[1] - other[1])
            if distance < minimum_m:
                fail(
                    key,
                    f"landmark is {distance / 1000:.1f} km from {other_key!r}, "
                    f"below the {MIN_VORONOI_SPACING_KM} km minimum spacing",
                )
    if problems:
        raise MapDistrictError(tuple(problems))


MAP_DISTRICT_REGISTRY: dict[str, MapDistrict] = {
    # The single region district: the whole northern deep forest, across the
    # Valhalla and Grandia nominal claims, lit only at its heart near the
    # north coast, about 500 km beyond the forest edge.
    "north_deep_forest": MapDistrict(
        "north_deep_forest", "北部深林", "古樹之心",
        "wild:elosern:1250:2420", "region", "north_deep_forest",
    ),
    # Altoria. The royal valley's landmark is the capital's central plaza, a
    # settlement grid node placed on the continent through its local frame.
    "royal_river_valley": MapDistrict(
        "royal_river_valley", "王都河谷", "王都中央廣場",
        "grid:capital_altoria:3500:2850", "voronoi",
    ),
    "salt_cliff_coast": MapDistrict(
        "salt_cliff_coast", "鹽崖海岸", "白鹽崖",
        "wild:elosern:620:300", "voronoi",
    ),
    "western_ore_hills": MapDistrict(
        "western_ore_hills", "西陲礦丘", "灰岩礦塔",
        "wild:elosern:330:1000", "voronoi",
    ),
    # Grandia.
    "imperial_wheatlands": MapDistrict(
        "imperial_wheatlands", "帝國麥原", "風車古道",
        "wild:elosern:1760:1050", "voronoi",
    ),
    "eastern_pasture": MapDistrict(
        "eastern_pasture", "東陲牧野", "孤石望台",
        "wild:elosern:2300:900", "voronoi",
    ),
    "imperial_south_shore": MapDistrict(
        "imperial_south_shore", "帝國南岸", "燈塔岬",
        "wild:elosern:1850:320", "voronoi",
    ),
    # Valhalla, south of the deep forest.
    "howling_highlands": MapDistrict(
        "howling_highlands", "狼嚎高地", "灰狼石柱",
        "wild:elosern:560:1640", "voronoi",
    ),
    "pine_hunting_grounds": MapDistrict(
        "pine_hunting_grounds", "松濤獵場", "獵人祭壇",
        "wild:elosern:1050:1700", "voronoi",
    ),
}
