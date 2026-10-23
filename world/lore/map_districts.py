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
        # Players leave settlements through gateway approaches, so a cell is
        # reachable when it shares a component with any of them. The shipped
        # approaches all lie in one component (pinned by
        # test_map_district_content), so no isolated pocket counts.
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


#: The authored roster: the deep forest region district plus 119 Voronoi
#: districts of roughly 200 km, grouped by nominal nation and listed north to
#: south. Placement and naming rationale live in
#: docs/development/continental-geography.md; after any change, regenerate the
#: frozen partition with ``uv run --locked python -m tools.map_district_partition``.
MAP_DISTRICT_REGISTRY: dict[str, MapDistrict] = {
    # The single region district: the whole northern deep forest, across the
    # Valhalla and Grandia nominal claims, lit only at its heart near the
    # north coast, about 500 km beyond the forest edge.
    "north_deep_forest": MapDistrict(
        "north_deep_forest", "北部深林", "古樹之心",
        "wild:elosern:1250:2420", "region", "north_deep_forest",
    ),
    # Altoria: the western hills and river valleys south of the border
    # river, the southwest coast and the western flank of the central range.
    "border_source_highlands": MapDistrict(
        "border_source_highlands", "界源高地", "源泉石龕",
        "wild:elosern:1302:1318", "voronoi",
    ),
    "march_watch_hills": MapDistrict(
        "march_watch_hills", "守界丘陵", "古哨塔遺址",
        "wild:elosern:1065:1303", "voronoi",
    ),
    "north_road_uplands": MapDistrict(
        "north_road_uplands", "北道高原", "白石里程碑",
        "wild:elosern:854:1282", "voronoi",
    ),
    "rune_stone_hills": MapDistrict(
        "rune_stone_hills", "古符丘陵", "符文巨石",
        "wild:elosern:442:1258", "voronoi",
    ),
    "maple_vale": MapDistrict(
        "maple_vale", "楓紅谷地", "紅葉瀑布",
        "wild:elosern:655:1225", "voronoi",
    ),
    "mistbell_heights": MapDistrict(
        "mistbell_heights", "霧角高原", "霧鐘石塔",
        "wild:elosern:232:1199", "voronoi",
    ),
    "vineyard_slopes": MapDistrict(
        "vineyard_slopes", "葡萄坡地", "老橡木酒窖",
        "wild:elosern:996:1161", "voronoi",
    ),
    "white_ram_foothills": MapDistrict(
        "white_ram_foothills", "白羊山麓", "牧羊人石屋",
        "wild:elosern:1177:1150", "voronoi",
    ),
    "eyrie_cliffs": MapDistrict(
        "eyrie_cliffs", "鷹巢峭壁", "蒼鷹岩",
        "wild:elosern:1345:1133", "voronoi",
    ),
    "amethyst_mine_vale": MapDistrict(
        "amethyst_mine_vale", "紫晶礦谷", "廢棄紫晶坑",
        "wild:elosern:491:1090", "voronoi",
    ),
    # The royal valley's landmark is the capital's central plaza, a
    # settlement grid node placed on the continent through its local frame.
    "royal_river_valley": MapDistrict(
        "royal_river_valley", "王都河谷", "王都中央廣場",
        "grid:capital_altoria:3500:2850", "voronoi",
    ),
    "royal_hunting_park": MapDistrict(
        "royal_hunting_park", "王家獵苑", "白鹿石雕",
        "wild:elosern:677:1029", "voronoi",
    ),
    "westwind_downs": MapDistrict(
        "westwind_downs", "西風丘原", "風琴石林",
        "wild:elosern:182:1013", "voronoi",
    ),
    "western_ore_hills": MapDistrict(
        "western_ore_hills", "西陲礦丘", "灰岩礦塔",
        "wild:elosern:330:1000", "voronoi",
    ),
    "east_river_fields": MapDistrict(
        "east_river_fields", "東河沃野", "古水車",
        "wild:elosern:1054:997", "voronoi",
    ),
    "westpass_uplands": MapDistrict(
        "westpass_uplands", "隘西高地", "西隘道標石",
        "wild:elosern:1281:972", "voronoi",
    ),
    "ironpine_woods": MapDistrict(
        "ironpine_woods", "鐵杉林地", "千年鐵杉",
        "wild:elosern:496:890", "voronoi",
    ),
    "bell_vale": MapDistrict(
        "bell_vale", "鐘聲谷", "荒廢修道院",
        "wild:elosern:887:886", "voronoi",
    ),
    "mill_reach": MapDistrict(
        "mill_reach", "磨坊河灣", "河畔舊磨坊",
        "wild:elosern:680:871", "voronoi",
    ),
    "oak_knolls": MapDistrict(
        "oak_knolls", "古橡丘陵", "巨橡樹",
        "wild:elosern:1122:850", "voronoi",
    ),
    "limestone_terrace": MapDistrict(
        "limestone_terrace", "石灰岩台地", "白灰窯遺址",
        "wild:elosern:265:805", "voronoi",
    ),
    "icespring_gorge": MapDistrict(
        "icespring_gorge", "冰泉峽谷", "冰泉瀑布",
        "wild:elosern:1334:801", "voronoi",
    ),
    "bramble_moor": MapDistrict(
        "bramble_moor", "荊棘荒原", "荊棘石環",
        "wild:elosern:433:713", "voronoi",
    ),
    "honey_vale": MapDistrict(
        "honey_vale", "蜜蜂谷地", "千巢岩壁",
        "wild:elosern:991:711", "voronoi",
    ),
    "silverbrook_vale": MapDistrict(
        "silverbrook_vale", "銀溪谷地", "銀溪石橋",
        "wild:elosern:800:696", "voronoi",
    ),
    "red_earth_hills": MapDistrict(
        "red_earth_hills", "赤土丘陵", "赤岩拱門",
        "wild:elosern:1181:688", "voronoi",
    ),
    "bluebell_meadows": MapDistrict(
        "bluebell_meadows", "藍鈴草原", "藍鈴石井",
        "wild:elosern:606:685", "voronoi",
    ),
    "rift_scarp_plateau": MapDistrict(
        "rift_scarp_plateau", "斷崖高原", "裂岩斷崖",
        "wild:elosern:1326:586", "voronoi",
    ),
    "gullcry_hills": MapDistrict(
        "gullcry_hills", "灰鷗丘陵", "鷗鳴石塔",
        "wild:elosern:319:581", "voronoi",
    ),
    "chalk_giant_downs": MapDistrict(
        "chalk_giant_downs", "白堊丘陵", "白堊巨人像",
        "wild:elosern:908:539", "voronoi",
    ),
    "old_battlefield": MapDistrict(
        "old_battlefield", "古戰場原", "騎士墓碑群",
        "wild:elosern:1114:525", "voronoi",
    ),
    "olive_slopes": MapDistrict(
        "olive_slopes", "橄欖坡地", "古榨油石臼",
        "wild:elosern:702:515", "voronoi",
    ),
    "anvil_vale": MapDistrict(
        "anvil_vale", "鐵砧谷地", "巨鐵砧岩",
        "wild:elosern:518:503", "voronoi",
    ),
    "south_pass_west_slopes": MapDistrict(
        "south_pass_west_slopes", "南隘西麓", "南隘古道碑",
        "wild:elosern:1314:414", "voronoi",
    ),
    "estuary_flats": MapDistrict(
        "estuary_flats", "河口平原", "潮汐石閘",
        "wild:elosern:389:381", "voronoi",
    ),
    "salt_road_hills": MapDistrict(
        "salt_road_hills", "鹽道丘陵", "鹽商界石",
        "wild:elosern:980:370", "voronoi",
    ),
    "seabreeze_pasture": MapDistrict(
        "seabreeze_pasture", "海風牧原", "風鈴石柱",
        "wild:elosern:797:367", "voronoi",
    ),
    "amber_slopes": MapDistrict(
        "amber_slopes", "琥珀坡地", "琥珀泉",
        "wild:elosern:1158:343", "voronoi",
    ),
    "salt_cliff_coast": MapDistrict(
        "salt_cliff_coast", "鹽崖海岸", "白鹽崖",
        "wild:elosern:620:300", "voronoi",
    ),
    "thunder_peak_range": MapDistrict(
        "thunder_peak_range", "雷鳴山嶺", "雷鳴峰",
        "wild:elosern:1338:211", "voronoi",
    ),
    "fishers_cove_coast": MapDistrict(
        "fishers_cove_coast", "漁灣海岸", "漁人守望塔",
        "wild:elosern:478:206", "voronoi",
    ),
    "keelwood_forest": MapDistrict(
        "keelwood_forest", "船木林地", "龍骨巨杉",
        "wild:elosern:836:192", "voronoi",
    ),
    "tidesong_dunes": MapDistrict(
        "tidesong_dunes", "潮音沙原", "潮音洞窟",
        "wild:elosern:1006:190", "voronoi",
    ),
    "pearl_bay_coast": MapDistrict(
        "pearl_bay_coast", "珍珠灣岸", "珍珠貝塚",
        "wild:elosern:1177:176", "voronoi",
    ),
    "white_sand_coast": MapDistrict(
        "white_sand_coast", "白沙海岸", "海蝕拱門",
        "wild:elosern:662:167", "voronoi",
    ),
    # Grandia: the eastern plains, the southeast coast and the eastern
    # flank of the central range, north to the deep forest edge.
    "forest_rim_heath": MapDistrict(
        "forest_rim_heath", "林緣荒原", "守林人石標",
        "wild:elosern:1625:1845", "voronoi",
    ),
    "moonlit_fields": MapDistrict(
        "moonlit_fields", "月光原野", "月光石圈",
        "wild:elosern:1941:1836", "voronoi",
    ),
    "whalebone_heath": MapDistrict(
        "whalebone_heath", "鯨骨荒原", "鯨骨拱門",
        "wild:elosern:2110:1834", "voronoi",
    ),
    "reed_marsh": MapDistrict(
        "reed_marsh", "蘆風沼澤", "沼中石塔",
        "wild:elosern:1782:1809", "voronoi",
    ),
    "north_pass_east_slopes": MapDistrict(
        "north_pass_east_slopes", "北隘東麓", "北隘風蝕岩",
        "wild:elosern:1486:1784", "voronoi",
    ),
    "sunken_bell_lake": MapDistrict(
        "sunken_bell_lake", "沉鐘湖區", "沉鐘湖",
        "wild:elosern:2224:1723", "voronoi",
    ),
    "stag_plateau": MapDistrict(
        "stag_plateau", "狩鹿高原", "獵鹿石陣",
        "wild:elosern:1669:1633", "voronoi",
    ),
    "crystal_plains": MapDistrict(
        "crystal_plains", "魔晶平原", "魔晶尖塔",
        "wild:elosern:1871:1633", "voronoi",
    ),
    "starfall_plain": MapDistrict(
        "starfall_plain", "星落原", "隕星坑",
        "wild:elosern:2069:1633", "voronoi",
    ),
    "bluemaple_hills": MapDistrict(
        "bluemaple_hills", "藍楓丘陵", "藍楓古樹",
        "wild:elosern:2286:1581", "voronoi",
    ),
    "spruce_foothills": MapDistrict(
        "spruce_foothills", "雲杉山麓", "雲杉石階",
        "wild:elosern:1487:1564", "voronoi",
    ),
    "harvest_north_plain": MapDistrict(
        "harvest_north_plain", "金麥北原", "豐收女神像",
        "wild:elosern:1987:1468", "voronoi",
    ),
    "sunrise_downs": MapDistrict(
        "sunrise_downs", "日出丘原", "日出岩",
        "wild:elosern:2394:1464", "voronoi",
    ),
    "orchard_plain": MapDistrict(
        "orchard_plain", "果園平原", "千年蘋果樹",
        "wild:elosern:1805:1437", "voronoi",
    ),
    "black_soil_plain": MapDistrict(
        "black_soil_plain", "黑土平原", "豐饒石壇",
        "wild:elosern:1623:1428", "voronoi",
    ),
    "poplar_plain": MapDistrict(
        "poplar_plain", "白楊平原", "白楊林蔭道",
        "wild:elosern:2164:1418", "voronoi",
    ),
    "hawkwing_heath": MapDistrict(
        "hawkwing_heath", "鷹翼荒原", "鷹翼石",
        "wild:elosern:2502:1330", "voronoi",
    ),
    "echo_canyon": MapDistrict(
        "echo_canyon", "回音峽谷", "回音石門",
        "wild:elosern:1490:1308", "voronoi",
    ),
    "scorched_hills": MapDistrict(
        "scorched_hills", "焦岩丘陵", "焦黑石林",
        "wild:elosern:2303:1287", "voronoi",
    ),
    "imperial_capital_plain": MapDistrict(
        "imperial_capital_plain", "帝都平原", "帝都凱旋門",
        "wild:elosern:1970:1280", "voronoi",
    ),
    "canal_plain": MapDistrict(
        "canal_plain", "運河平原", "古運河閘門",
        "wild:elosern:1738:1246", "voronoi",
    ),
    "rose_plain": MapDistrict(
        "rose_plain", "玫瑰平原", "玫瑰石園",
        "wild:elosern:2124:1196", "voronoi",
    ),
    "tide_wind_downs": MapDistrict(
        "tide_wind_downs", "潮風丘地", "海神祭壇",
        "wild:elosern:2460:1163", "voronoi",
    ),
    "gargoyle_plateau": MapDistrict(
        "gargoyle_plateau", "石像鬼高原", "石像鬼岩",
        "wild:elosern:1549:1132", "voronoi",
    ),
    "imperial_river_reach": MapDistrict(
        "imperial_river_reach", "帝河流域", "七拱石橋",
        "wild:elosern:1939:1103", "voronoi",
    ),
    "sundial_plain": MapDistrict(
        "sundial_plain", "金陽平原", "日晷石",
        "wild:elosern:2269:1088", "voronoi",
    ),
    "imperial_wheatlands": MapDistrict(
        "imperial_wheatlands", "帝國麥原", "風車古道",
        "wild:elosern:1760:1050", "voronoi",
    ),
    "stormrock_heath": MapDistrict(
        "stormrock_heath", "東岬荒原", "風暴岩",
        "wild:elosern:2439:991", "voronoi",
    ),
    "wizard_tower_plain": MapDistrict(
        "wizard_tower_plain", "法師平原", "傾斜法師塔",
        "wild:elosern:2097:968", "voronoi",
    ),
    "great_pass_east": MapDistrict(
        "great_pass_east", "大隘東原", "大隘道標",
        "wild:elosern:1502:962", "voronoi",
    ),
    "emerald_lake_plain": MapDistrict(
        "emerald_lake_plain", "翡翠湖原", "翡翠湖",
        "wild:elosern:1896:906", "voronoi",
    ),
    "eastern_pasture": MapDistrict(
        "eastern_pasture", "東陲牧野", "孤石望台",
        "wild:elosern:2300:900", "voronoi",
    ),
    "horse_plain": MapDistrict(
        "horse_plain", "駿馬原野", "奔馬石雕",
        "wild:elosern:1687:864", "voronoi",
    ),
    "golden_dune_downs": MapDistrict(
        "golden_dune_downs", "金沙丘原", "沙中古塔",
        "wild:elosern:2402:797", "voronoi",
    ),
    "flax_plain": MapDistrict(
        "flax_plain", "亞麻平原", "藍花石橋",
        "wild:elosern:2191:777", "voronoi",
    ),
    "mithril_foothills": MapDistrict(
        "mithril_foothills", "銀礦山麓", "秘銀礦坑",
        "wild:elosern:1504:761", "voronoi",
    ),
    "river_isle_flats": MapDistrict(
        "river_isle_flats", "河洲平原", "白鷺沙洲",
        "wild:elosern:2015:751", "voronoi",
    ),
    "herbal_plain": MapDistrict(
        "herbal_plain", "藥草原野", "賢者石圃",
        "wild:elosern:1842:711", "voronoi",
    ),
    "griffin_plateau": MapDistrict(
        "griffin_plateau", "獅鷲高原", "獅鷲巢岩",
        "wild:elosern:1667:651", "voronoi",
    ),
    "bluewave_downs": MapDistrict(
        "bluewave_downs", "藍浪丘原", "浪花石",
        "wild:elosern:2343:642", "voronoi",
    ),
    "confluence_vale": MapDistrict(
        "confluence_vale", "雙河谷地", "匯流巨石",
        "wild:elosern:2144:598", "voronoi",
    ),
    "cloudsea_foothills": MapDistrict(
        "cloudsea_foothills", "雲海山麓", "雲海觀星台",
        "wild:elosern:1503:569", "voronoi",
    ),
    "east_branch_ford": MapDistrict(
        "east_branch_ford", "渡口原野", "東支流古渡",
        "wild:elosern:2300:526", "voronoi",
    ),
    "spice_road_plain": MapDistrict(
        "spice_road_plain", "香料原野", "香料古道碑",
        "wild:elosern:1976:522", "voronoi",
    ),
    "orange_blossom_plain": MapDistrict(
        "orange_blossom_plain", "橙花平原", "橙花古泉",
        "wild:elosern:1805:518", "voronoi",
    ),
    "giants_stair_highlands": MapDistrict(
        "giants_stair_highlands", "南嶺高地", "巨人階梯",
        "wild:elosern:1660:419", "voronoi",
    ),
    "caravan_hills": MapDistrict(
        "caravan_hills", "商隊丘陵", "商隊泉",
        "wild:elosern:2147:402", "voronoi",
    ),
    "south_pass_east_slopes": MapDistrict(
        "south_pass_east_slopes", "南隘東麓", "南隘石門",
        "wild:elosern:1490:371", "voronoi",
    ),
    "imperial_south_shore": MapDistrict(
        "imperial_south_shore", "帝國南岸", "燈塔岬",
        "wild:elosern:1850:320", "voronoi",
    ),
    "imperial_delta": MapDistrict(
        "imperial_delta", "帝河三角洲", "三角洲古碑",
        "wild:elosern:2007:303", "voronoi",
    ),
    "sea_serpent_slopes": MapDistrict(
        "sea_serpent_slopes", "海蛇坡地", "海蛇化石",
        "wild:elosern:1668:211", "voronoi",
    ),
    "obsidian_ridge": MapDistrict(
        "obsidian_ridge", "火山岩嶺", "黑曜石峰",
        "wild:elosern:1503:184", "voronoi",
    ),
    "mermaid_cove_coast": MapDistrict(
        "mermaid_cove_coast", "人魚灣岸", "人魚雕像",
        "wild:elosern:1840:177", "voronoi",
    ),
    # Valhalla: the northwest highland forest between the border river and
    # the deep forest edge, and the range's western flank north of the river.
    "howling_capital_woods": MapDistrict(
        "howling_capital_woods", "王城森林", "萬獸圖騰柱",
        "wild:elosern:780:1910", "voronoi",
    ),
    "bear_claw_woods": MapDistrict(
        "bear_claw_woods", "熊爪林地", "熊王岩",
        "wild:elosern:992:1851", "voronoi",
    ),
    "stag_call_highlands": MapDistrict(
        "stag_call_highlands", "鹿鳴高地", "鹿角聖樹",
        "wild:elosern:469:1850", "voronoi",
    ),
    "north_pass_west_slopes": MapDistrict(
        "north_pass_west_slopes", "北隘西麓", "雪豹岩",
        "wild:elosern:1326:1837", "voronoi",
    ),
    "shaman_cave_woods": MapDistrict(
        "shaman_cave_woods", "巫醫林地", "巫醫石窟",
        "wild:elosern:1168:1816", "voronoi",
    ),
    "frost_heath": MapDistrict(
        "frost_heath", "霜風荒原", "冰河巨石",
        "wild:elosern:262:1814", "voronoi",
    ),
    "war_drum_highlands": MapDistrict(
        "war_drum_highlands", "戰鼓高地", "戰鼓岩",
        "wild:elosern:648:1808", "voronoi",
    ),
    "beast_trail_woods": MapDistrict(
        "beast_trail_woods", "獸徑林地", "飲獸泉",
        "wild:elosern:857:1713", "voronoi",
    ),
    "pine_hunting_grounds": MapDistrict(
        "pine_hunting_grounds", "松濤獵場", "獵人祭壇",
        "wild:elosern:1050:1700", "voronoi",
    ),
    "hot_spring_foothills": MapDistrict(
        "hot_spring_foothills", "溫泉山麓", "赤霧溫泉",
        "wild:elosern:1331:1670", "voronoi",
    ),
    "bison_plateau": MapDistrict(
        "bison_plateau", "野牛高原", "野牛頭骨塚",
        "wild:elosern:391:1661", "voronoi",
    ),
    "howling_highlands": MapDistrict(
        "howling_highlands", "狼嚎高地", "灰狼石柱",
        "wild:elosern:560:1640", "voronoi",
    ),
    "iron_vein_highlands": MapDistrict(
        "iron_vein_highlands", "鐵脈高地", "赤鐵岩壁",
        "wild:elosern:1175:1605", "voronoi",
    ),
    "ancestor_cairn_hills": MapDistrict(
        "ancestor_cairn_hills", "先祖丘陵", "先祖石冢",
        "wild:elosern:729:1595", "voronoi",
    ),
    "mossy_coast_woods": MapDistrict(
        "mossy_coast_woods", "苔林海岸", "苔蘚巨木",
        "wild:elosern:240:1583", "voronoi",
    ),
    "grizzly_vale": MapDistrict(
        "grizzly_vale", "灰熊谷", "灰熊洞穴",
        "wild:elosern:896:1489", "voronoi",
    ),
    "giant_rockfall_slopes": MapDistrict(
        "giant_rockfall_slopes", "落石坡地", "巨人落石",
        "wild:elosern:1310:1480", "voronoi",
    ),
    "falcon_rise": MapDistrict(
        "falcon_rise", "獵鷹高原", "獵鷹台",
        "wild:elosern:1093:1455", "voronoi",
    ),
    "blood_moon_vale": MapDistrict(
        "blood_moon_vale", "血月谷", "血月石",
        "wild:elosern:447:1450", "voronoi",
    ),
    "rivers_watch_woods": MapDistrict(
        "rivers_watch_woods", "界北林地", "望河岩",
        "wild:elosern:670:1416", "voronoi",
    ),
    "wolf_fang_coast": MapDistrict(
        "wolf_fang_coast", "狼牙海岸林", "狼牙巨石",
        "wild:elosern:238:1388", "voronoi",
    ),
}
