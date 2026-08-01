"""Terrain region registry for the wilderness/Virtual map layer (map-wilderness)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WildernessRegion:
    """One terrain region covering part of the continent's wilderness.

    ``nation_key`` is ``None`` for neutral/contested territory; otherwise it
    names a key in ``world.lore.nations.NATION_REGISTRY`` (asserted by a test,
    not enforced by the dataclass).
    """

    key: str
    display_name_zh: str
    nation_key: str | None
    terrain_flavor_zh: tuple[str, ...]


WILDERNESS_REGION_REGISTRY: dict[str, WildernessRegion] = {
    "central_mountains": WildernessRegion(
        "central_mountains", "中央山脈", None, (
            "陡峭的山壁直插雲霄，寒風中隱約傳來難以辨明來源的歌聲。",
            "林木稀疏的山徑蜿蜒而上，碎石在腳下滑動，四周異常寂靜。",
            "雲霧終年繚繞山腰，據說深處藏著人族從未涉足之地。",
        ),
    ),
    "eastern_plains": WildernessRegion(
        "eastern_plains", "東部大平原", "grandia", (
            "一望無際的麥田隨風起伏，遠方農莊的炊煙筆直升起。",
            "平整的官道兩側是修剪整齊的果園，牛車緩緩碾過塵土。",
            "肥沃的黑土地上阡陌縱橫，灌溉渠道映著天光。",
        ),
    ),
    "southeast_coast": WildernessRegion(
        "southeast_coast", "東南海岸", "grandia", (
            "鹹濕的海風夾雜著魚市的喧鬧，遠方帆影點點。",
            "石砌的碼頭邊堆滿待運的貨箱，海鳥在桅杆間盤旋。",
            "潮水拍打著防波堤，港區小巷瀰漫著海產與香料的氣味。",
        ),
    ),
    "western_hills_valleys": WildernessRegion(
        "western_hills_valleys", "西部丘陵與谷地", "altoria", (
            "起伏的丘陵間點綴著石砌梯田，遠處傳來礦坑鑿擊的回聲。",
            "谷地間河流蜿蜒，兩岸散落著手工業者的作坊與磨坊。",
            "低緩的丘陵覆滿灌木與野花，羊群在坡地上安靜地啃食。",
        ),
    ),
    "southwest_coast": WildernessRegion(
        "southwest_coast", "西南海岸", "altoria", (
            "精工打磨的木船停靠在小巧的港灣，工匠的敲打聲不絕於耳。",
            "海崖下的漁村炊煙裊裊，曬鹽場在陽光下泛著白光。",
            "商船的旗幟在海風中獵獵作響，岸邊堆滿待售的精工器物。",
        ),
    ),
    "northwest_highland_forest": WildernessRegion(
        "northwest_highland_forest", "西北高地森林", "valhalla", (
            "高聳的針葉林間，獸群的足跡清晰可辨，空氣中帶著松脂的氣味。",
            "起伏的高地覆蓋著濃密的森林，獵人的營火痕跡散落其間。",
            "礦脈裸露的岩壁旁，成群的野獸在林間空地遊蕩。",
        ),
    ),
    "north_deep_forest": WildernessRegion(
        "north_deep_forest", "北部深林", "valhalla", (  # nominal claim only, see below
            "巨木遮蔽天日，林間彌漫著潮濕腐葉的氣息，寂靜得令人不安。",
            "糾結的藤蔓封鎖了視野，遠處似乎有什麼龐然大物正在移動。",
            "無人踏足的密林深處，偶爾傳來不知名生物的低吼。",
        ),
    ),
}
