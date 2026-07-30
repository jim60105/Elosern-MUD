"""Currency and price registries from design section 5.1 and lore-world-data."""

from dataclasses import dataclass


COPPER_PER_SILVER = 100
COPPER_PER_GOLD = 10_000


def to_copper(gold: int = 0, silver: int = 0, copper: int = 0) -> int:
    """Convert integral denominations to the canonical copper count."""

    return gold * COPPER_PER_GOLD + silver * COPPER_PER_SILVER + copper


@dataclass(frozen=True)
class PriceEntry:
    key: str
    display_name_zh: str
    min_copper: int
    max_copper: int | None
    notes: str


PRICE_TABLE: dict[str, PriceEntry] = {
    "inn_stay": PriceEntry("inn_stay", "普通旅館一晚", 20, 20, "One ordinary inn night."),
    "meal": PriceEntry("meal", "普通餐食", 5, 10, "One ordinary meal."),
    "potion": PriceEntry("potion", "魔法藥劑", 50, 500, "A common magical potion."),
    "plain_sword": PriceEntry("plain_sword", "普通劍", 100, 500, "An ordinary sword."),
    "magic_weapon": PriceEntry(
        "magic_weapon", "魔法武器", 100_000, None, "Open-ended price starting at ten gold."
    ),
    "commoner_annual_income": PriceEntry(
        "commoner_annual_income", "平民年收入", 50_000, 100_000, "Approximate annual income."
    ),
    "adventurer_annual_income": PriceEntry(
        "adventurer_annual_income", "冒險者年收入", 100_000, 1_000_000,
        "Annual income depending on guild rank.",
    ),
}
