"""Geographic anchor registry from design section 5.1 and lore-world-data."""

from dataclasses import dataclass
from enum import StrEnum


class AnchorKind(StrEnum):
    CAPITAL = "capital"
    ELVEN_VILLAGE = "elven_village"
    DUNGEON = "dungeon"


@dataclass(frozen=True)
class Anchor:
    key: str
    kind: AnchorKind
    display_name_zh: str
    nation_key: str | None
    population: int | None
    floors: int | None
    description: str


ANCHOR_REGISTRY: dict[str, Anchor] = {
    "capital_grandia": Anchor(
        "capital_grandia", AnchorKind.CAPITAL, "輝煌帝都", "grandia", 800_000, None,
        "Capital of the Grandia Empire.",
    ),
    "capital_altoria": Anchor(
        "capital_altoria", AnchorKind.CAPITAL, "聖潔王都", "altoria", 600_000, None,
        "Capital of the Altoria Kingdom.",
    ),
    "capital_valhalla": Anchor(
        "capital_valhalla", AnchorKind.CAPITAL, "咆哮王城", "valhalla", 400_000, None,
        "Capital of the Valhalla Beast Kingdom.",
    ),
    "village_fionnen": Anchor(
        "village_fionnen", AnchorKind.ELVEN_VILLAGE, "翠綠森林村", None, 120, None,
        "Fionnen village on the eastern side of the neutral central range.",
    ),
    "village_ciaran": Anchor(
        "village_ciaran", AnchorKind.ELVEN_VILLAGE, "暗影谷村", None, 100, None,
        "Ciaran village underground on the western side of the neutral central range.",
    ),
    "village_eolas": Anchor(
        "village_eolas", AnchorKind.ELVEN_VILLAGE, "幽月谷村", None, 80, None,
        "Hidden Eolas village in a northern valley of the neutral central range.",
    ),
    "dungeon_eternal_night": Anchor(
        "dungeon_eternal_night", AnchorKind.DUNGEON, "永夜迷宮", "valhalla", None, 80,
        "A northern deep-forest dungeon under Valhalla's nominal but unenforced claim.",
    ),
    "dungeon_dragon_nest": Anchor(
        "dungeon_dragon_nest", AnchorKind.DUNGEON, "龍之巢穴", "grandia", None, 50,
        "A known dungeon in the eastern Grandia Empire.",
    ),
    "dungeon_arcane_ruins": Anchor(
        "dungeon_arcane_ruins", AnchorKind.DUNGEON, "魔導遺跡", "altoria", None, 60,
        "A known dungeon in the western Altoria Kingdom.",
    ),
}
