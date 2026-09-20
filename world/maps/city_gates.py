"""The sole authored source of 虛境 city gates (limbo-one-way-gates D1).

Every bridge from the starting room (Limbo) into a city is declared here and
only here: one ``CityGateDef`` row per city, keyed by map id. ``sync_grid()``
(``world/maps/bootstrap.py``) converges exactly these rows — one forward exit
each — and prunes anything leading back into 虛境, so the one-way threshold
holds for however many rows the registry grows to. Adding a city means adding
one row plus that city's map data; no bootstrap code change (design doc §4,
D7). Race-based selection of which gate a new character takes is explicitly
out of scope (design doc §2, YAGNI).

The registry slot expresses "the authored way in from 虛境", and a row SHALL
NOT be assumed to describe a walled settlement: elven villages have no walls
and no gates, so ``village_ciaran``'s row is a concealed path (隱密小徑)
through the forest even though it occupies the slot a city gate would
(settlement-shops design §6.2).

Frozen dataclass + ``MappingProxyType`` is the repo's immutable-registry
convention (mirrors ``WILDERNESS_ENTRY_REGISTRY``); consumers must read these
values instead of duplicating gate keys, aliases, or coordinates.
"""

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class CityGateDef:
    """One authored city gate: where it lands and how the exit is named."""

    map_id: str
    gate_xyz: tuple[int, int, str]
    exit_key: str
    exit_aliases: tuple[str, ...]


CITY_GATE_REGISTRY: MappingProxyType = MappingProxyType(
    {
        "capital_altoria": CityGateDef(
            map_id="capital_altoria",
            gate_xyz=(3, 0, "capital_altoria"),
            exit_key="南門",
            exit_aliases=("王都", "城門"),
        ),
        "village_ciaran": CityGateDef(
            map_id="village_ciaran",
            gate_xyz=(0, 1, "village_ciaran"),
            exit_key="隱密小徑",
            exit_aliases=("祕徑", "幽徑"),
        ),
    }
)
