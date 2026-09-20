"""Settlement identity registry (settlement-shops design §3.3).

A settlement is the map coordinate space its places sit in: its key equals
the geographic anchor key, its archetype comes from the closed vocabulary of
the six settlement types the world defines, and its zcoord names the map's
coordinate space. ``AnchorKind`` is deliberately left alone — it classifies
geography (and includes non-settlements, e.g. dungeons), while archetypes
classify how a settlement is built.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from world.lore.anchors import ANCHOR_REGISTRY


class SettlementArchetype(StrEnum):
    CAPITAL = "capital"
    TOWN = "town"
    PORT = "port"
    BEAST_CITY = "beast_city"
    ELVEN_VILLAGE = "elven_village"
    FRONTIER = "frontier"


@dataclass(frozen=True)
class SettlementDefinition:
    """One settlement's identity: anchor key, archetype and coordinate space."""

    key: str
    archetype: SettlementArchetype
    zcoord: str


def validate_settlement_registry(
    registry: Mapping[str, SettlementDefinition],
) -> None:
    """Fail closed on a malformed settlement record, naming the row.

    A settlement key MUST resolve in the geographic anchor registry: places
    resolve their exterior coordinate space through the settlement, and the
    anchor registry is the single naming authority for geography.
    """
    for key, settlement in registry.items():
        if key != settlement.key:
            raise ValueError(
                f"settlement {key!r} key mismatch (declared {settlement.key!r})"
            )
        if settlement.key not in ANCHOR_REGISTRY:
            raise ValueError(
                f"settlement {settlement.key!r} has no matching ANCHOR_REGISTRY key"
            )
        if not isinstance(settlement.zcoord, str) or not settlement.zcoord.strip():
            raise ValueError(
                f"settlement {settlement.key!r} zcoord must be a non-empty string"
            )


SETTLEMENT_REGISTRY: dict[str, SettlementDefinition] = {
    "capital_altoria": SettlementDefinition(
        key="capital_altoria",
        archetype=SettlementArchetype.CAPITAL,
        zcoord="capital_altoria",
    ),
    "village_ciaran": SettlementDefinition(
        key="village_ciaran",
        archetype=SettlementArchetype.ELVEN_VILLAGE,
        zcoord="village_ciaran",
    ),
}

validate_settlement_registry(SETTLEMENT_REGISTRY)