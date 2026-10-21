"""The frozen narration catalog aggregate.

The per-skill rows of every ACTIVE family land here: the eight element
slices, martial arts, holy rites, divine mysteries and enhancement, then the
six sexual-act lines. Keeping one aggregate means the lookup chain, the
validator, and the selector stay exercised by the shipped import.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from world.skills.sexual_acts import SHIPPED_ACT_SKILLS, SEXUAL_ACT_REGISTRY

from .data_dark import ROWS as DARK_ROWS
from .data_sexual_combat import ROWS as SEXUAL_COMBAT_ROWS
from .data_sexual_divine import ROWS as SEXUAL_DIVINE_ROWS
from .data_sexual_interspecies import ROWS as SEXUAL_INTERSPECIES_ROWS
from .data_sexual_partner import ROWS as SEXUAL_PARTNER_ROWS
from .data_sexual_shame import ROWS as SEXUAL_SHAME_ROWS
from .data_sexual_solo import ROWS as SEXUAL_SOLO_ROWS
from .data_divine_mystery import ROWS as DIVINE_MYSTERY_ROWS
from .data_earth import ROWS as EARTH_ROWS
from .data_enhancement import ROWS as ENHANCEMENT_ROWS
from .data_fire import ROWS as FIRE_ROWS
from .data_holy_rite import ROWS as HOLY_RITE_ROWS
from .data_ice import ROWS as ICE_ROWS
from .data_light import ROWS as LIGHT_ROWS
from .data_lightning import ROWS as LIGHTNING_ROWS
from .data_martial import ROWS as MARTIAL_ROWS
from .data_water import ROWS as WATER_ROWS
from .data_wind import ROWS as WIND_ROWS
from .families import FAMILY_ROWS
from .validation import build_catalog, validate_catalog, validate_sexual_pools
from .vocab import NarrationRow

#: Authored per-skill narration rows, keyed by the skill registry's own keys.
NARRATION_CATALOG: Mapping[str, NarrationRow] = MappingProxyType(
    build_catalog(
        (
            *FIRE_ROWS,
            *WATER_ROWS,
            *WIND_ROWS,
            *EARTH_ROWS,
            *LIGHTNING_ROWS,
            *ICE_ROWS,
            *LIGHT_ROWS,
            *DARK_ROWS,
            *MARTIAL_ROWS,
            *HOLY_RITE_ROWS,
            *DIVINE_MYSTERY_ROWS,
            *ENHANCEMENT_ROWS,
            *SEXUAL_SOLO_ROWS,
            *SEXUAL_SHAME_ROWS,
            *SEXUAL_PARTNER_ROWS,
            *SEXUAL_COMBAT_ROWS,
            *SEXUAL_INTERSPECIES_ROWS,
            *SEXUAL_DIVINE_ROWS,
        )
    )
)

# Fail closed at import: a bad row, a broken bound, or a missing row for a
# non-pending active skill stops the server rather than silently rendering a
# generic line.
validate_catalog(NARRATION_CATALOG)
# The transition and counter pools are keyed by what the act catalogue can
# emit, so a new event or counter without prose stops the import too.
validate_sexual_pools(SEXUAL_ACT_REGISTRY, SHIPPED_ACT_SKILLS)


__all__ = ["FAMILY_ROWS", "NARRATION_CATALOG"]
