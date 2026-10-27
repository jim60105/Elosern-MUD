"""Terrain region registry for the wilderness/Virtual map layer (map-wilderness).

Also owns the frozen continental coordinate-frame and mainland declarations of
the known continent. These are authoring contracts only: they create no rooms,
do not activate the runtime wilderness scale, and describe one continent (no
planet size or further continent is inferred).

The polygon and frame arithmetic these declarations feed lives in
``elosern_map_core.geometry``; the helpers below only bind this module's
authored values into it.
"""

from dataclasses import dataclass

from elosern_map_core import geometry as core_geometry

#: The enclosing wilderness frame spans this many one-kilometre cells per axis.
CONTINENT_FRAME_CELLS = 2700
#: Logical size of one wilderness cell, kilometres per axis.
CONTINENT_CELL_SIZE_KM = 1

#: Ordered mainland boundary vertices as absolute ``(east, north)`` kilometres.
#: The boundary is implicitly closed from the last vertex back to the first;
#: the shoelace area is exactly 5,000,000 km².
MAINLAND_BOUNDARY_KM: tuple[tuple[int, int], ...] = (
    (450, 100),
    (1850, 100),
    (2400, 450),
    (2600, 1350),
    (1930, 2250),
    (1800, 2600),
    (750, 2550),
    (200, 2050),
    (100, 1050),
    (300, 350),
)


def is_wilderness_cell(cell: tuple[int, int]) -> bool:
    """Whether ``(x, y)`` is inside the 2700 by 2700 enclosing frame."""

    return core_geometry.is_within_frame(CONTINENT_FRAME_CELLS, cell)


def mainland_area_km2() -> float:
    """Shoelace area of the closed mainland boundary, square kilometres."""

    return core_geometry.polygon_area_km2(MAINLAND_BOUNDARY_KM)


def is_on_mainland(east_km: float, north_km: float) -> bool:
    """Whether an absolute ``(east, north)`` kilometre point is on land.

    Boundary points count as land; sea and the ocean margin do not.
    """

    return core_geometry.is_on_mainland(MAINLAND_BOUNDARY_KM, east_km, north_km)


@dataclass(frozen=True)
class HarborSite:
    """One reserved land-side harbor cell.

    A functional site is not a named anchor: it declares no city, quest,
    anchor key or population, and it is not mirrored into room lifecycle.
    """

    key: str
    display_name: str
    cell: tuple[int, int]
    role: str


HARBOR_SITE_REGISTRY: dict[str, HarborSite] = {
    "kingdom_southwest_main_port": HarborSite(
        "kingdom_southwest_main_port",
        "Kingdom southwestern main port",
        (301, 350),
        "River/sea transfer and foreign trade",
    ),
    "kingdom_western_secondary_port": HarborSite(
        "kingdom_western_secondary_port",
        "Kingdom western secondary port",
        (201, 700),
        "Western mining and craft exports",
    ),
    "kingdom_southern_secondary_port": HarborSite(
        "kingdom_southern_secondary_port",
        "Kingdom southern secondary port",
        (600, 101),
        "Southern coastal supply",
    ),
    "imperial_southeast_main_port": HarborSite(
        "imperial_southeast_main_port",
        "Imperial southeastern main port",
        (2070, 241),
        "Agricultural and magical-goods exports",
    ),
    "imperial_southeast_secondary_port": HarborSite(
        "imperial_southeast_secondary_port",
        "Imperial southeastern secondary port",
        (2400, 454),
        "Eastern coastal collection",
    ),
    "imperial_southern_secondary_port": HarborSite(
        "imperial_southern_secondary_port",
        "Imperial southern secondary port",
        (1700, 101),
        "Southern coastal transfer",
    ),
}


@dataclass(frozen=True)
class WildernessRegion:
    """One terrain region covering part of the continent's wilderness.

    ``nation_key`` names the single nation that nominally claims the whole
    region, or is ``None`` when the region straddles a nominal border (the
    central mountains and the northern deep forest). ``nominal_nation_keys``
    lists every nation that claims some of the region's cells, sorted; the
    per-cell claim is ``world.maps.wilderness_provider.
    nominal_nation_for_coordinates``. Both name keys in
    ``world.lore.nations.NATION_REGISTRY`` (asserted by a test, not enforced
    by the dataclass).
    """

    key: str
    display_name_zh: str
    nation_key: str | None
    terrain_flavor_zh: tuple[str, ...]
    nominal_nation_keys: tuple[str, ...] = ()


WILDERNESS_REGION_REGISTRY: dict[str, WildernessRegion] = {
    "central_mountains": WildernessRegion(
        "central_mountains", "中央山脈", None, (  # split by ridge and river
            "陡峭的山壁直插雲霄，寒風中隱約傳來難以辨明來源的歌聲。",
            "林木稀疏的山徑蜿蜒而上，碎石在腳下滑動，四周異常寂靜。",
            "雲霧終年繚繞山腰，據說深處藏著人族從未涉足之地。",
        ),
        ("altoria", "grandia", "valhalla"),
    ),
    "eastern_plains": WildernessRegion(
        "eastern_plains", "東部大平原", "grandia", (
            "一望無際的麥田隨風起伏，遠方農莊的炊煙筆直升起。",
            "平整的官道兩側是修剪整齊的果園，牛車緩緩碾過塵土。",
            "肥沃的黑土地上阡陌縱橫，灌溉渠道映著天光。",
        ),
        ("grandia",),
    ),
    "southeast_coast": WildernessRegion(
        "southeast_coast", "東南海岸", "grandia", (
            "鹹濕的海風夾雜著魚市的喧鬧，遠方帆影點點。",
            "石砌的碼頭邊堆滿待運的貨箱，海鳥在桅杆間盤旋。",
            "潮水拍打著防波堤，港區小巷瀰漫著海產與香料的氣味。",
        ),
        ("grandia",),
    ),
    "western_hills_valleys": WildernessRegion(
        "western_hills_valleys", "西部丘陵與谷地", "altoria", (
            "起伏的丘陵間點綴著石砌梯田，遠處傳來礦坑鑿擊的回聲。",
            "谷地間河流蜿蜒，兩岸散落著手工業者的作坊與磨坊。",
            "低緩的丘陵覆滿灌木與野花，羊群在坡地上安靜地啃食。",
        ),
        ("altoria",),
    ),
    "southwest_coast": WildernessRegion(
        "southwest_coast", "西南海岸", "altoria", (
            "精工打磨的木船停靠在小巧的港灣，工匠的敲打聲不絕於耳。",
            "海崖下的漁村炊煙裊裊，曬鹽場在陽光下泛著白光。",
            "商船的旗幟在海風中獵獵作響，岸邊堆滿待售的精工器物。",
        ),
        ("altoria",),
    ),
    "northwest_highland_forest": WildernessRegion(
        "northwest_highland_forest", "西北高地森林", "valhalla", (
            "高聳的針葉林間，獸群的足跡清晰可辨，空氣中帶著松脂的氣味。",
            "起伏的高地覆蓋著濃密的森林，獵人的營火痕跡散落其間。",
            "礦脈裸露的岩壁旁，成群的野獸在林間空地遊蕩。",
        ),
        ("valhalla",),
    ),
    "north_deep_forest": WildernessRegion(
        "north_deep_forest", "北部深林", None, (  # west Valhalla, east Grandia
            "巨木遮蔽天日，林間彌漫著潮濕腐葉的氣息，寂靜得令人不安。",
            "糾結的藤蔓封鎖了視野，遠處似乎有什麼龐然大物正在移動。",
            "無人踏足的密林深處，偶爾傳來不知名生物的低吼。",
        ),
        ("grandia", "valhalla"),
    ),
}
