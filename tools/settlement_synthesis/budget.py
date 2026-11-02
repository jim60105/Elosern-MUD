"""The research-based size budget: population to area, cells and tier targets.

Built-up area follows the Cesaretti et al. (2016) population-area relation,
``area = reference_area * (population / reference_population) ** exponent``,
anchored at the configured reference density. The constants live in one
``BudgetConfig`` so a review can change the assumption once; the shipped
``DEFAULT_BUDGET`` is an assumption, not a measured constant.

Two scales stay separate and both come from that one area: the wilderness
footprint in whole 1 km cells, and the metre envelope radius of the street
graph. The footprint floor of two cells keeps every settlement multi-gate, so a
concealed one-cell entry is an authored exception and never a budget result.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.settlement_synthesis.site import SettlementRef

#: The kinds that receive a population-based budget.
NATIONAL_KINDS = ("capital", "city", "town", "port")


@dataclass(frozen=True)
class Tier:
    """One gameplay size tier, selected by inclusive lower population."""

    min_population: int
    nodes: int
    gates: int
    loop_ratio: float


@dataclass(frozen=True)
class BudgetConfig:
    """Every constant the size budget reads."""

    reference_population: int
    reference_density_per_ha: float
    area_exponent: float
    min_footprint_cells: int
    tiers: tuple[Tier, ...]
    capital_tier: Tier

    def __post_init__(self) -> None:
        if self.reference_population <= 0:
            raise ValueError("reference_population must be positive")
        if self.reference_density_per_ha <= 0:
            raise ValueError("reference_density_per_ha must be positive")
        if self.area_exponent <= 0:
            raise ValueError("area_exponent must be positive")
        if self.min_footprint_cells < 2:
            raise ValueError(
                "min_footprint_cells must be at least 2 so no settlement is a "
                "single concealed cell"
            )
        if not self.tiers:
            raise ValueError("at least one population tier is required")
        for tier in (*self.tiers, self.capital_tier):
            _validate_tier(tier)


def _validate_tier(tier: Tier) -> None:
    if tier.min_population < 0:
        raise ValueError("a tier's min_population cannot be negative")
    if tier.nodes <= 0 or tier.gates <= 0 or tier.loop_ratio <= 0:
        raise ValueError("a tier's nodes, gates and loop_ratio must be positive")


DEFAULT_BUDGET = BudgetConfig(
    reference_population=10_000,
    reference_density_per_ha=150.0,
    area_exponent=0.714,
    min_footprint_cells=2,
    tiers=(
        Tier(100_000, 18, 3, 0.30),
        Tier(50_000, 12, 2, 0.25),
        Tier(25_000, 10, 2, 0.20),
        Tier(10_000, 8, 2, 0.15),
        Tier(0, 6, 2, 0.15),
    ),
    capital_tier=Tier(0, 28, 4, 0.35),
)


@dataclass(frozen=True)
class SizeBudget:
    """One settlement's derived size, in both scales plus its tier targets."""

    location_id: str
    population: int
    built_area_km2: float
    footprint_cells: int
    envelope_radius_m: int
    node_count: int
    gate_count: int
    loop_ratio: float


class BudgetError(ValueError):
    """A location has no size budget: wrong kind, or no positive population."""


def size_budget(
    location: SettlementRef, config: BudgetConfig = DEFAULT_BUDGET
) -> SizeBudget:
    """The derived size budget for one settlement location."""

    if location.kind not in NATIONAL_KINDS:
        raise BudgetError(
            f"{location.location_id}: kind {location.kind!r} has no size budget"
        )
    if location.population is None or location.population < 1:
        raise BudgetError(
            f"{location.location_id}: population {location.population!r} is not a "
            "positive count"
        )

    population = location.population
    reference_area_km2 = (
        config.reference_population / config.reference_density_per_ha / 100
    )
    area_km2 = reference_area_km2 * (
        population / config.reference_population
    ) ** config.area_exponent
    footprint_cells = max(
        config.min_footprint_cells, math.ceil(area_km2 - 1e-9)
    )
    envelope_radius_m = round(1000 * math.sqrt(area_km2 / math.pi))

    if location.kind == "capital":
        tier = config.capital_tier
    else:
        qualifying = [
            tier for tier in config.tiers if tier.min_population <= population
        ]
        if not qualifying:
            raise BudgetError(
                f"{location.location_id}: no tier covers population {population}"
            )
        tier = max(qualifying, key=lambda candidate: candidate.min_population)

    return SizeBudget(
        location_id=location.location_id,
        population=population,
        built_area_km2=area_km2,
        footprint_cells=footprint_cells,
        envelope_radius_m=envelope_radius_m,
        node_count=tier.nodes,
        gate_count=tier.gates,
        loop_ratio=tier.loop_ratio,
    )
