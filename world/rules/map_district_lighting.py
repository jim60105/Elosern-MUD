"""Read-only district lighting derived from the landmark rite record (map-districts).

A map district is lit if and only if the player character's rite record
(:mod:`world.rules.landmark_rite_record`) holds at least one completed rite for
it and the district registry declares it (landmark rites design §8). Visiting
a landmark lights nothing: map knowledge stays a record of visits only.

Lighting is a pure derivation: it reads the rite record through
:func:`world.rules.landmark_rite_record.completed_district_keys`, never reads
map knowledge, and never writes or creates an attribute. ``record_arrival``
stays the sole knowledge writer and the rite settlement the sole record writer.

Two reads share one rule. :func:`lit_district_keys` is strict and raises on a
corrupt record; :func:`readable_lit_district_keys` is the read presentation and
travel use, which degrades an unreadable record to no lit district with one
warning, so a corrupt record can never fabricate a lit district.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from elosern_map_core.documents import DistrictDeclaration
from world.observability import log_warn
from world.rules.landmark_rite_record import (
    LandmarkRiteRecordError,
    completed_district_keys,
)


def lit_district_keys(
    character: Any,
    registry: Mapping[str, DistrictDeclaration] | None = None,
) -> frozenset[str]:
    """The districts whose rite this character has completed at least once.

    ``character`` is the rite record owner (the player character, or the
    commander behind a possessed body). A completed key the registry (default:
    the published district world) does not declare is not lit. A character who
    never completed a rite lights nothing and the registry is not read. A
    corrupt record raises :class:`LandmarkRiteRecordError` and is left as is.
    """
    completed = completed_district_keys(character)
    if not completed:
        return frozenset()
    if registry is None:
        # Resolved at call time so a substituted district world is honoured.
        from world.lore.map_districts import current

        registry = current().districts
    return frozenset(key for key in completed if key in registry)


def readable_lit_district_keys(
    character: Any,
    registry: Mapping[str, DistrictDeclaration] | None = None,
) -> frozenset[str]:
    """As :func:`lit_district_keys`, degrading to no lit district when unreadable."""
    try:
        return lit_district_keys(character, registry)
    except LandmarkRiteRecordError as error:
        log_warn(
            "landmark_rite_record_corrupt",
            exc=error,
            context={"char": getattr(character, "pk", None), "district": ""},
        )
        return frozenset()
