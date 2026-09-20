"""Immutable settlement-related identity registries (settlement-shops design §3).

This package holds registry-backed identity for settlements (the map
coordinate spaces), places (one authored record per service location) and
goods bundles (assortments). Shop identities are derived from places in
:mod:`world.lore.settlements.shops` — never authored here.
"""

from world.lore.settlements.places import PLACE_REGISTRY, PlaceDefinition, PlaceKind
from world.lore.settlements.settlements import (
    SETTLEMENT_REGISTRY,
    SettlementArchetype,
    SettlementDefinition,
)

__all__ = [
    "PLACE_REGISTRY",
    "PlaceDefinition",
    "PlaceKind",
    "SETTLEMENT_REGISTRY",
    "SettlementArchetype",
    "SettlementDefinition",
]