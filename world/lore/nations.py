"""Nation registry from design section 5.1 and lore-world-data.

Also owns the frozen demographic and territory contract of the known
continent. ``territory_share`` and ``territory_km2`` are area targets: they
describe neither terrain nor actual political control, and the national mean
density they produce is never a per-cell population raster.
"""

from dataclasses import dataclass
from enum import StrEnum

#: Land-area target of the known continent, square kilometres.
CONTINENT_AREA_KM2 = 5_000_000
#: Rounded continental population total.
CONTINENT_POPULATION = 30_000_000
#: Rounded elven population total: the three elven villages in ``anchors``.
ELVEN_POPULATION = 300
#: Neutral lands left outside the three national territory targets.
NEUTRAL_LANDS_AREA_KM2 = 500_000
#: The neutral lands have no separate regional population total.
NEUTRAL_LANDS_POPULATION: int | None = None
#: Combined share of the continental population living in the three capitals.
CAPITAL_POPULATION_SHARE = 0.06


class SupplyBasis(StrEnum):
    """One authored reason a capital's population can be sustained."""

    REGIONAL_FOOD = "regional_food"
    STORAGE = "storage"
    WATER = "water"
    PASTORAL_PRODUCTION = "pastoral_production"
    TRADE = "trade"


@dataclass(frozen=True)
class CapitalSupport:
    """Authored support facts for one capital's large fantasy population.

    These declare what sustains the population; they do not simulate regional
    supply or create runtime food, storage or water state. ``anchor_key`` names
    the capital in ``world.lore.anchors.ANCHOR_REGISTRY`` and supplies that
    entry's population.
    """

    anchor_key: str
    supply_bases: frozenset[SupplyBasis]
    notes: str


CAPITAL_SUPPORT_REGISTRY: dict[str, CapitalSupport] = {
    "capital_altoria": CapitalSupport(
        "capital_altoria",
        frozenset(
            {
                SupplyBasis.REGIONAL_FOOD,
                SupplyBasis.STORAGE,
                SupplyBasis.WATER,
                SupplyBasis.TRADE,
            }
        ),
        "River-valley terraces feed the city; granaries and river water serve the lower city.",
    ),
    "capital_grandia": CapitalSupport(
        "capital_grandia",
        frozenset(
            {
                SupplyBasis.REGIONAL_FOOD,
                SupplyBasis.STORAGE,
                SupplyBasis.WATER,
                SupplyBasis.TRADE,
            }
        ),
        "The eastern agricultural plain and its major river supply the imperial core.",
    ),
    "capital_valhalla": CapitalSupport(
        "capital_valhalla",
        frozenset(
            {
                SupplyBasis.REGIONAL_FOOD,
                SupplyBasis.STORAGE,
                SupplyBasis.WATER,
                SupplyBasis.PASTORAL_PRODUCTION,
                SupplyBasis.TRADE,
            }
        ),
        "Highland pastoral production and trade sustain the city; hunting alone cannot.",
    ),
}


@dataclass(frozen=True)
class Nation:
    key: str
    display_name_zh: str
    capital_anchor_key: str
    government: str
    dominant_race: str
    population: int
    territory_share: float
    territory_km2: int
    ruler_zh: str
    military_notes: str
    notes: str

    @property
    def mean_inhabitants_per_km2(self) -> float:
        """Mean continental density, not a per-cell population allocation."""
        return self.population / self.territory_km2

    @property
    def capital_name_zh(self) -> str:
        """The capital's player-facing name, resolved through the anchor registry.

        Read at call time so a swapped registry is honoured; the load-time
        nation check guarantees every shipped capital key resolves.
        """
        from world.lore import anchors

        anchor = anchors.anchors().get(self.capital_anchor_key)
        return anchor.display_name_zh if anchor is not None else self.capital_anchor_key


NATION_REGISTRY: dict[str, Nation] = {
    "grandia": Nation(
        "grandia", "格蘭迪亞帝國", "capital_grandia",
        "Absolute monarchy", "human", 12_000_000, 0.38, 1_900_000, "格蘭迪亞皇帝",
        "A standing army of about 150,000 plus 5,000 military mages.",
        "Agricultural and commercial power with the continent's largest royal magic academy.",
    ),
    "altoria": Nation(
        "altoria", "阿爾托利亞王國", "capital_altoria",
        "Constitutional monarchy with a noble council", "human", 9_000_000, 0.27, 1_350_000,
        "阿爾托利亞國王",
        "A standing army of about 100,000 supported by a developed knightly order.",
        "A craft and trading kingdom rich in mineral resources.",
    ),
    "valhalla": Nation(
        "valhalla", "瓦爾哈拉獸王國", "capital_valhalla",
        "Tribal federation", "beastfolk", 9_000_000, 0.25, 1_250_000, "雷克斯‧銀牙",
        "Universal military duty supports mobilization of about 500,000 warriors.",
        "A hunting, herding, and mining federation that values nature and strength.",
    ),
}
