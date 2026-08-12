"""MP cost tiers for spell skills (skill-system-redesign design doc §4.3, D9).

The five tiers are keyed by the world-lore rank titles; later spell-catalog
proposals pick a range from here instead of inventing ad hoc costs. The level
band is descriptive (the design doc's rank-title table and this cost table
share the 90 boundary); nothing in this module gates on it.
"""

from typing import NamedTuple


class CostTier(NamedTuple):
    """One MP cost tier: a level band plus single- and area-effect ranges."""

    min_level: int
    max_level: int | None
    single_mp: tuple[int, int]
    area_mp: tuple[int, int]


MP_COST_TIERS: dict[str, CostTier] = {
    "學徒": CostTier(0, 15, (10, 16), (14, 20)),
    "術師": CostTier(16, 30, (20, 28), (26, 34)),
    "大師": CostTier(31, 70, (35, 48), (45, 60)),
    "賢者": CostTier(71, 90, (65, 85), (80, 110)),
    "主宰": CostTier(90, None, (120, 150), (140, 180)),
}
