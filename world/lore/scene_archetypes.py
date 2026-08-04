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
        "鋪著石板的主要街道上人來人往，攤販的叫賣聲與馬車的輪聲此起彼落。",
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
        "莊嚴的神殿內燭光搖曳，香氣裊繞，虔誠的信徒在神像前低聲祈禱。",
    ),
)

# Frozen: consumers may read registry values but never extend or replace them.
SCENE_ARCHETYPE_REGISTRY: MappingProxyType[str, SceneArchetype] = MappingProxyType(
    {archetype.key: archetype for archetype in _SCENE_ARCHETYPES}
)
