"""The frozen narration catalog aggregate.

Per-skill rows are empty in this change: the family tier carries every active
skill until the three follow-up changes author their rows. Keeping the empty
aggregate here means the lookup chain, the validator, and the selector are
exercised by the shipped import from day one, and each follow-up change only
adds data modules.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

from .families import FAMILY_ROWS
from .validation import validate_catalog
from .vocab import NarrationRow

#: Authored per-skill narration rows, keyed by the skill registry's own keys.
#: The follow-up changes fill this mapping from ``data_*.py`` modules.
NARRATION_CATALOG: Mapping[str, NarrationRow] = MappingProxyType({})

# Fail closed at import: a bad row, a broken bound, or a missing row for a
# non-pending active skill stops the server rather than silently rendering a
# generic line.
validate_catalog(NARRATION_CATALOG)


__all__ = ["FAMILY_ROWS", "NARRATION_CATALOG"]
