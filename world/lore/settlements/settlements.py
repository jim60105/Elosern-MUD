"""Settlement identity registry (settlement-shops design §3.3).

A settlement is the map coordinate space its places sit in: its key equals
the geographic anchor key, its archetype comes from the closed vocabulary of
the six settlement types the world defines, and its coordinate space is the
map the published anchor placement binds it to — never an authored copy. ``AnchorKind`` is deliberately left alone — it classifies
geography (and includes non-settlements, e.g. dungeons), while archetypes
classify how a settlement is built.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

class SettlementArchetype(StrEnum):
    CAPITAL = "capital"
    TOWN = "town"
    PORT = "port"
    BEAST_CITY = "beast_city"
    ELVEN_VILLAGE = "elven_village"
    FRONTIER = "frontier"


@dataclass(frozen=True)
class SettlementDefinition:
    """One settlement's non-map identity: anchor key and archetype.

    The map coordinate space is not authored here: it is the map identity the
    published anchor placement binds to this settlement's location, so a
    candidate that changes the binding changes what every consumer reads.
    """

    key: str
    archetype: SettlementArchetype

    @property
    def zcoord(self) -> str:
        """The map coordinate space this settlement's places sit in."""

        from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY

        placement = ANCHOR_PLACEMENT_REGISTRY.get(self.key)
        if placement is None:
            raise ValueError(
                f"settlement {self.key!r} has no published anchor placement; "
                "its map association comes from the adopted map world"
            )
        return placement.zcoord


def validate_settlement_registry(
    registry: Mapping[str, SettlementDefinition],
) -> None:
    """Fail closed on a malformed settlement record, naming the row.

    A settlement key MUST resolve in the composed geographic locations. That
    join is checked when the geography candidate is published
    (``world.maps.geography``), because the locations are loaded map sources
    rather than import-time lore tables.
    """
    for key, settlement in registry.items():
        if key != settlement.key:
            raise ValueError(
                f"settlement {key!r} key mismatch (declared {settlement.key!r})"
            )


SETTLEMENT_REGISTRY: dict[str, SettlementDefinition] = {
    "capital_altoria": SettlementDefinition(
        key="capital_altoria",
        archetype=SettlementArchetype.CAPITAL,
    ),
    "village_ciaran": SettlementDefinition(
        key="village_ciaran",
        archetype=SettlementArchetype.ELVEN_VILLAGE,
    ),
}

validate_settlement_registry(SETTLEMENT_REGISTRY)