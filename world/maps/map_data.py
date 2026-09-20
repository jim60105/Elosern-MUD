"""Shared grid-map assembly: every settlement's ``XYMAP_DATA`` in one list.

``XYMAP_DATA_LIST`` has two independent readers with separate imports —
``world/maps/bootstrap.py`` and ``world/lore/wilderness_entry.py``'s
``_iter_map_extents()`` (whose import stays deferred: lore must not import
``world.maps`` at module scope) — plus ``world.quests.definitions.py``, which
derives ``KNOWN_GRID_MAP_KEYS`` from it. The name used to live in
``world/maps/altoria_capital.py``; moving the definition here (settlement-shops
design §6.2 / §10 "one trap worth naming") makes "add a settlement's map" an
assembly edit instead of an append at one import site. Consumers must read the
list from this module, never from a single settlement's module.
"""

from world.maps.altoria_capital import XYMAP_DATA as _CAPITAL_XYMAP_DATA
from world.maps.village_ciaran import XYMAP_DATA as _VILLAGE_XYMAP_DATA

XYMAP_DATA_LIST = [_CAPITAL_XYMAP_DATA, _VILLAGE_XYMAP_DATA]