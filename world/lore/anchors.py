"""Geographic location identity and the non-map lore joined to it.

Map-facing identity (kind, name, description, cell, geographic constraint) is
authored in ``content/maps/locations.yaml`` and composed by
:mod:`world.maps.geography`. This module owns the view types plus
:data:`ANCHOR_LORE`: the political affiliation, population and dungeon floor
counts that stay with their existing lore owner and are joined by the same
stable identity.

``LOCAL_FRAME_ANCHOR_REGISTRY`` binds authored settlement frames; it is a
settlement-domain declaration (not map-facing geography) and stays here until
the settlement cutover. It is neither the grid-placement registry nor a room
spawner.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from elosern_map_core.geometry import local_to_world_m


class AnchorKind(StrEnum):
    CAPITAL = "capital"
    ELVEN_VILLAGE = "elven_village"
    DUNGEON = "dungeon"


@dataclass(frozen=True)
class AnchorLore:
    """The non-map lore one location identity carries.

    These values are joined to the authored geographic location by identity;
    none of them is derived from geometry, and an absent nation stays absent.
    """

    nation_key: str | None
    population: int | None
    floors: int | None


@dataclass(frozen=True)
class Anchor:
    """One composed geographic location (map-facing fields + joined lore)."""

    key: str
    kind: AnchorKind
    display_name_zh: str
    nation_key: str | None
    population: int | None
    floors: int | None
    description: str


@dataclass(frozen=True)
class GeographicAnchor:
    """The canonical wilderness cell of one geographic location.

    Declaring a cell creates no room and reveals nothing to players; map
    knowledge and visibility rules remain authoritative.
    """

    anchor_key: str
    cell: tuple[int, int]
    geographic_constraint: str


@dataclass(frozen=True)
class LocalFrameAnchor:
    """The authored integer-metre point that binds a settlement frame.

    ``local_anchor_m`` is the ``(east, north)`` metre position inside the
    settlement that sits at the center of its wilderness anchor cell.
    """

    anchor_key: str
    local_anchor_m: tuple[int, int]


#: Non-map lore keyed by the authored location identity. Political affiliation,
#: rounded population and dungeon floor counts are lore facts, never values
#: inferred from the geographic cell.
ANCHOR_LORE: dict[str, AnchorLore] = {
    "capital_grandia": AnchorLore("grandia", 800_000, None),
    "capital_altoria": AnchorLore("altoria", 600_000, None),
    "capital_valhalla": AnchorLore("valhalla", 400_000, None),
    "village_fionnen": AnchorLore(None, 120, None),
    "village_ciaran": AnchorLore(None, 100, None),
    "village_eolas": AnchorLore(None, 80, None),
    "dungeon_eternal_night": AnchorLore("valhalla", None, 80),
    "dungeon_dragon_nest": AnchorLore("grandia", None, 50),
    "dungeon_arcane_ruins": AnchorLore("altoria", None, 60),
}


LOCAL_FRAME_ANCHOR_REGISTRY: dict[str, LocalFrameAnchor] = {
    "capital_altoria": LocalFrameAnchor("capital_altoria", (3500, 2850)),
    "village_ciaran": LocalFrameAnchor("village_ciaran", (220, 305)),
}


def _geography():
    from world.maps.geography import current

    return current()


def anchors() -> Mapping[str, Anchor]:
    """The published composed geographic-location views."""

    return _geography().anchors


def anchor_geography() -> Mapping[str, GeographicAnchor]:
    """The published location cells and geographic constraints."""

    return _geography().anchor_geography


def world_position_m(
    anchor_key: str, local_position_m: tuple[int, int]
) -> tuple[int, int]:
    """Absolute ``(east, north)`` metres of a settlement-local metre position.

    ``world_m = wilderness_anchor_cell_center + local_m - local_anchor_m``.
    The settlement's ``z`` remains a logical layer and is never elevation;
    this transform returns horizontal metres only.
    """

    geography = anchor_geography()[anchor_key]
    frame = LOCAL_FRAME_ANCHOR_REGISTRY[anchor_key]
    return local_to_world_m(geography.cell, frame.local_anchor_m, local_position_m)


__all__ = [
    "ANCHOR_LORE",
    "Anchor",
    "AnchorKind",
    "AnchorLore",
    "GeographicAnchor",
    "LOCAL_FRAME_ANCHOR_REGISTRY",
    "LocalFrameAnchor",
    "anchor_geography",
    "anchors",
    "world_position_m",
]
