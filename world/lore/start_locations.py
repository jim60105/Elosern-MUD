"""Per-subrace start settlements (subrace-start-locations).

Every subrace names exactly one start settlement by its anchor (location)
identity. The start room is that settlement's anchor room: it is derived from
the anchor placement at the consumer boundary
(``world.rules.start_location.resolve_start_room``), never stored here as a
coordinate, node id or object id.

Coverage of the subrace registry is checked when this module is imported.
Whether each anchor has a settlement placement depends on the published map
world, so that check runs at map-world adoption instead
(``world/maps/static_references.py``).
"""

from collections.abc import Mapping
from dataclasses import dataclass

from world.lore.races import SUBRACE_REGISTRY


@dataclass(frozen=True)
class SubraceStartLocation:
    """One subrace's start settlement, named by its anchor (location) identity."""

    subrace_key: str
    anchor_key: str


SUBRACE_START_LOCATION_REGISTRY: dict[str, SubraceStartLocation] = {
    row.subrace_key: row
    for row in (
        SubraceStartLocation("human_royal", "town_olive_ferry"),
        SubraceStartLocation("human_noble", "town_steed_plain"),
        SubraceStartLocation("human_coastal", "port_fishers_cove"),
        SubraceStartLocation("human_plains", "town_orange_blossom"),
        SubraceStartLocation("human_highland", "town_silver_ridge"),
        SubraceStartLocation("fionnen", "elven_village_fionnen"),
        SubraceStartLocation("ciaran", "elven_village_ciaran"),
        SubraceStartLocation("eolas", "elven_village_eolas"),
        SubraceStartLocation("wolfkin", "city_moon_howl"),
        SubraceStartLocation("catkin", "city_shadow_wood"),
        SubraceStartLocation("bearkin", "city_iron_claw"),
        SubraceStartLocation("rabbitkin", "city_swift_wind"),
        SubraceStartLocation("bovinekin", "city_horn_plain"),
        SubraceStartLocation("tigerkin", "city_tiger_roar"),
        SubraceStartLocation("foxkin", "city_fox_fire"),
    )
}


def validate_start_locations(
    registry: Mapping[str, object], subraces: Mapping[str, object]
) -> None:
    """Reject a start registry that does not cover ``subraces`` exactly once."""

    for key, row in registry.items():
        if not isinstance(row, SubraceStartLocation):
            raise ValueError(f"start location {key!r} must be a SubraceStartLocation")
        if row.subrace_key != key:
            raise ValueError(
                f"start location {key!r} declares mismatched subrace "
                f"{row.subrace_key!r}"
            )
        if key not in subraces:
            raise ValueError(f"start location {key!r} names an unknown subrace")
        if not isinstance(row.anchor_key, str) or not row.anchor_key:
            raise ValueError(
                f"start location {key!r} must name a non-empty anchor key"
            )
    missing = sorted(set(subraces) - set(registry))
    if missing:
        raise ValueError(f"subraces without a start location: {missing}")


validate_start_locations(SUBRACE_START_LOCATION_REGISTRY, SUBRACE_REGISTRY)


__all__ = [
    "SUBRACE_START_LOCATION_REGISTRY",
    "SubraceStartLocation",
    "validate_start_locations",
]
