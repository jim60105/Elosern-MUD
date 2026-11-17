"""Immutable scene-kind registry for quest proposals (design section 8).

Design section 8 keys scene art by archetype, not by room: one ``SceneArchetype``
carries a stable key plus a one-sentence natural-language scene description.
This change supplies the key vocabulary and the ``scene_sentence``-ready shape
as immutable lore data so every side of the single-writer boundary -- the
``world/ai`` proposal validators, change 21's SceneBuilder, and the
``world/quests`` compiler -- reads the same registry values instead of
duplicating constants. Change 22 adds the image field surface it owns.
"""

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class SceneArchetype:
    """One immutable scene-kind identity referenced by quest proposals."""

    key: str
    display_name_zh: str
    scene_sentence: str


_SCENE_ARCHETYPES = (
    SceneArchetype(
        "forest_path",
        "林間小徑",
        "陽光穿過層疊的枝葉，灑在一條蜿蜒的林間小徑上，四周寂靜得只剩下風聲。",
    ),
    SceneArchetype(
        "tavern_interior",
        "酒館內部",
        "爐火映照的木造酒館內，酒客的低語與杯盤碰撞聲交織成喧鬧的背景。",
    ),
    SceneArchetype(
        "dungeon_interior",
        "地牢內部",
        "潮濕的石砌地牢裡，燭火在牆上投下搖曳的影子，隱約傳來的聲響令人不安。",
    ),
    SceneArchetype(
        "city_street",
        "城市街道",
        "鋪著石板的主要街道上人來人往，攤販的叫賣聲與馬車的車輪聲此起彼落。",
    ),
    SceneArchetype(
        "wilderness_path",
        "荒野小徑",
        "荒草叢生的鄉間小徑通往遠方的地平線，曠野的風掠過乾燥的土壤。",
    ),
    SceneArchetype(
        "mountain_path",
        "山道",
        "陡峭的山道沿著岩壁盤旋而上，碎石在腳下滾落，空氣中帶著岩石與松脂的氣味。",
    ),
    SceneArchetype(
        "ruin_interior",
        "遺跡內部",
        "殘破的古代遺跡內，斷裂的立柱與斑駁的壁畫訴說著失落時代的過往。",
    ),
    SceneArchetype(
        "coastal_path",
        "海岸小徑",
        "海風挾著鹹味迎面吹來，浪濤拍打著岸邊的礁石，海平線延伸到視線盡頭。",
    ),
    SceneArchetype(
        "cave_interior",
        "洞穴內部",
        "深邃的洞穴內滴水聲迴盪，岩壁上覆滿苔蘚，陰暗處似乎有目光凝視。",
    ),
    SceneArchetype(
        "shrine_interior",
        "神殿內部",
        "莊嚴的神殿內燭光搖曳，香煙繚繞，虔誠的信徒在神像前低聲祈禱。",
    ),
    SceneArchetype(
        "rite_spring",
        "泉之石龕",
        "苔蘚覆滿的泉池上緣有一座低矮石龕，墨黑的水面映著林隙間垂落的冷光。",
    ),
    SceneArchetype(
        "rite_statue",
        "鹿影石雕",
        "風掃過的草原上立著白色鹿形石雕，斷角與苔痕在斜陽下拖出細長的影子。",
    ),
    SceneArchetype(
        "rite_megalith",
        "符文巨石",
        "光裸的山頂環立著蝕痕斑駁的巨石，低垂的日光把石影拉過短草與碎石。",
    ),
    SceneArchetype(
        "rite_tower",
        "霧鐘石塔",
        "海崖上的圓石塔只剩殘拱，霧中垂著一口青綠的鐘，腳下是一片空蕩的石台。",
    ),
    SceneArchetype(
        "rite_tree",
        "古樹之心",
        "巨樹的樹心被根鬚拱成一片凹陷的泥土空地，琥珀色的光柱自樹冠缺口斜落。",
    ),
    SceneArchetype(
        "rite_grave",
        "騎士墓群",
        "緩坡上一片無人憑弔的墓園，低矮的墓碑歪斜而立，斷裂的石十字與雜草野花一同沉寂在灰霧裡。",
    ),
    SceneArchetype(
        "rite_mine",
        "紫晶坑道",
        "廢棄的紫晶坑口撐著塌斜的木架，一道冷光自頂隙落下，照亮成堆的碎石地面。",
    ),
    SceneArchetype(
        "rite_gate",
        "赤岩拱門",
        "赤色砂岩的巨大拱門橫跨乾燥隘口，正午的強光把門內的通道照得發白。",
    ),
    SceneArchetype(
        "rite_cliff",
        "冰泉崖壁",
        "野溪自深色花崗岩崖壁直落入乳藍色的天然岩池，水霧與冷冽的飛沫在濕黑的石面上浮動。",
    ),
    SceneArchetype(
        "rite_plaza",
        "中央廣場",
        "王都中心的石鋪廣場上立著雕花噴泉，拱廊與垂下的旗幟圍著一片空蕩的鋪面。",
    ),
)

# Frozen: consumers may read registry values but never extend or replace them.
SCENE_ARCHETYPE_REGISTRY: MappingProxyType[str, SceneArchetype] = MappingProxyType(
    {archetype.key: archetype for archetype in _SCENE_ARCHETYPES}
)
