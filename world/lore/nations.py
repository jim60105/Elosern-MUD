"""Nation registry from design section 5.1 and lore-world-data."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Nation:
    key: str
    display_name_zh: str
    capital_anchor_key: str
    government: str
    dominant_race: str
    population: int
    territory_share: float
    ruler_zh: str
    military_notes: str
    notes: str


NATION_REGISTRY: dict[str, Nation] = {
    "grandia": Nation(
        "grandia", "格蘭迪亞帝國", "capital_grandia",
        "Absolute monarchy", "human", 12_000_000, 0.38, "格蘭迪亞皇帝",
        "A standing army of about 150,000 plus 5,000 military mages.",
        "Agricultural and commercial power with the continent's largest royal magic academy.",
    ),
    "altoria": Nation(
        "altoria", "阿爾托利亞王國", "capital_altoria",
        "Constitutional monarchy with a noble council", "human", 9_000_000, 0.27,
        "阿爾托利亞國王",
        "A standing army of about 100,000 supported by a developed knightly order.",
        "A craft and trading kingdom rich in mineral resources.",
    ),
    "valhalla": Nation(
        "valhalla", "瓦爾哈拉獸王國", "capital_valhalla",
        "Tribal federation", "beastfolk", 9_000_000, 0.25, "雷克斯·銀牙",
        "Universal military duty supports mobilization of about 500,000 warriors.",
        "A hunting, herding, and mining federation that values nature and strength.",
    ),
}
