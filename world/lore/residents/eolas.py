"""幽月谷村 resident slice (elven-resident-npcs-content fills this row set).

``PUBLIC_NODE`` is the settlement node the village's residents walk to on the
shared ``resident`` schedule; leave it ``None`` while ``ROWS`` is empty.
"""

from world.lore.residents.shape import Resident

SETTLEMENT_KEY = "elven_village_eolas"
PUBLIC_NODE: str | None = None
ROWS: tuple[Resident, ...] = ()
