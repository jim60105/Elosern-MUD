"""The sole authored source of 虛境 city gates (limbo-one-way-gates D1).

Every bridge from the starting room (Limbo) into a city is declared once, by
that settlement's own document: its ``city_gate`` row. This module exposes the
composed ``CityGateDef`` view of the published settlement world — one row per
settlement that declares an entry — and ``sync_grid()``
(``world/maps/bootstrap.py``) converges exactly those rows, one forward exit
each, pruning anything leading back into 虛境. Adding a city means adding a
settlement document; no bootstrap code change (design doc §4, D7). Race-based
selection of which gate a new character takes is explicitly out of scope
(design doc §2, YAGNI).

The gate is a qualified settlement-node identity, never a coordinate: the
current gate room address is derived from the settlement graph at the consumer
boundary (``world/maps/static_references.py``). Moving the authored node moves
the gate with it.

The slot expresses "the authored way in from 虛境", and a row SHALL NOT be
assumed to describe a walled settlement: elven villages have no walls and no
gates, so 暗影谷村's row is a concealed path (隱密小徑) through the forest even
though it occupies the slot a city gate would (settlement-shops design §6.2).

Frozen dataclass + an immutable published view is the repo's registry
convention (mirrors ``WILDERNESS_ENTRY_REGISTRY``); consumers must read these
values instead of duplicating gate keys, aliases, or coordinates.
"""

from dataclasses import dataclass
from typing import Mapping

from elosern_map_core.documents import QualifiedRef

from world.maps.published import PublishedView


@dataclass(frozen=True, slots=True)
class CityGateDef:
    """One authored city gate: which node it lands on and how the exit is named."""

    gate: QualifiedRef
    exit_key: str
    exit_aliases: tuple[str, ...]


#: One composed row per published settlement that declares a starting-room entry.
CITY_GATE_REGISTRY: Mapping[str, CityGateDef] = PublishedView("city_gates")


__all__ = ["CITY_GATE_REGISTRY", "CityGateDef"]
