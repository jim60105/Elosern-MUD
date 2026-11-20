"""The assembled resident registry and public-space declarations.

One slice per elven village owns its resident rows and names the settlement
node those residents visit. The slice order is fixed so the registry a consumer
reads is deterministic regardless of import history. This registry is
deliberately NOT mirrored into persistent lore records (like the NPC profile
registry): residents are materialized by the startup sync, never by the lore
mirror.
"""

from types import MappingProxyType

from world.lore.residents.ciaran import (
    PUBLIC_NODE as CIARAN_PUBLIC_NODE,
)
from world.lore.residents.ciaran import ROWS as CIARAN_ROWS
from world.lore.residents.ciaran import SETTLEMENT_KEY as CIARAN_SETTLEMENT
from world.lore.residents.eolas import (
    PUBLIC_NODE as EOLAS_PUBLIC_NODE,
)
from world.lore.residents.eolas import ROWS as EOLAS_ROWS
from world.lore.residents.eolas import SETTLEMENT_KEY as EOLAS_SETTLEMENT
from world.lore.residents.fionnen import (
    PUBLIC_NODE as FIONNEN_PUBLIC_NODE,
)
from world.lore.residents.fionnen import ROWS as FIONNEN_ROWS
from world.lore.residents.fionnen import SETTLEMENT_KEY as FIONNEN_SETTLEMENT
from world.lore.residents.shape import (
    Resident,
    ResidentRegistryError,
    assemble_public_nodes,
    assemble_resident_registry,
)

#: The owned slices, in fixed order: (slice label, settlement, public node, rows).
RESIDENT_SLICES: tuple[tuple[str, str, str | None, tuple[Resident, ...]], ...] = (
    ("eolas_residents", EOLAS_SETTLEMENT, EOLAS_PUBLIC_NODE, EOLAS_ROWS),
    ("ciaran_residents", CIARAN_SETTLEMENT, CIARAN_PUBLIC_NODE, CIARAN_ROWS),
    ("fionnen_residents", FIONNEN_SETTLEMENT, FIONNEN_PUBLIC_NODE, FIONNEN_ROWS),
)

RESIDENT_REGISTRY: MappingProxyType[str, Resident] = MappingProxyType(
    assemble_resident_registry(
        [(label, rows) for label, _, _, rows in RESIDENT_SLICES]
    )
)

#: Settlement key -> authored settlement node the village's residents visit.
RESIDENT_PUBLIC_NODES: MappingProxyType[str, str] = MappingProxyType(
    assemble_public_nodes(
        [(label, settlement, node) for label, settlement, node, _ in RESIDENT_SLICES]
    )
)

__all__ = [
    "CIARAN_ROWS",
    "EOLAS_ROWS",
    "FIONNEN_ROWS",
    "RESIDENT_PUBLIC_NODES",
    "RESIDENT_REGISTRY",
    "RESIDENT_SLICES",
    "Resident",
    "ResidentRegistryError",
]
