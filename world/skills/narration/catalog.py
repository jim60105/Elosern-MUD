"""The frozen narration catalog aggregate.

The per-skill rows of the elemental-magic and non-elemental families land
here: the eight element slices, then martial arts, holy rites, divine
mysteries and enhancement. The sexual-act family is still carried by its
family tier until its own change authors the rows. Keeping one aggregate
means the lookup chain, the validator, and the selector stay exercised by the
shipped import, and each follow-up change only adds data modules.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from .data_dark import ROWS as DARK_ROWS
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
from .validation import build_catalog, validate_catalog
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
        )
    )
)

# Fail closed at import: a bad row, a broken bound, or a missing row for a
# non-pending active skill stops the server rather than silently rendering a
# generic line.
validate_catalog(NARRATION_CATALOG)


__all__ = ["FAMILY_ROWS", "NARRATION_CATALOG"]
