"""Geographic location identity and the non-map lore joined to it.

Map-facing identity (kind, name, description, cell, geographic constraint) is
authored in ``content/maps/locations.yaml`` and composed by
:mod:`world.maps.geography`. This module owns the view types plus
:data:`ANCHOR_LORE`: the political affiliation, population and dungeon floor
counts that stay with their existing lore owner and are joined by the same
stable identity.

``LOCAL_FRAME_ANCHOR_REGISTRY`` binds authored settlement frames. Its values are
the published settlement documents' anchor bindings, keyed by ``location_ref``;
it is neither the grid-placement registry nor a room spawner.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from elosern_map_core.geometry import local_to_world_m

from world.maps.published import PublishedView


class AnchorKind(StrEnum):
    CAPITAL = "capital"
    CITY = "city"
    TOWN = "town"
    PORT = "port"
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
    # National cities, towns and ports, largest first. Their populations count
    # settlements of at least 5,000; the rural majority lives in unnamed villages.
    # Grandia Empire: 21 settlements, 757,000 people.
    "port_golden_sheaf": AnchorLore("grandia", 180_000, None),
    "city_twin_currents": AnchorLore("grandia", 90_000, None),
    "port_south_cape": AnchorLore("grandia", 60_000, None),
    "port_east_bay": AnchorLore("grandia", 55_000, None),
    "city_starglow": AnchorLore("grandia", 50_000, None),
    "city_wheatwave": AnchorLore("grandia", 45_000, None),
    "city_imperial_ferry": AnchorLore("grandia", 40_000, None),
    "port_dawnlight": AnchorLore("grandia", 35_000, None),
    "city_spice_road": AnchorLore("grandia", 30_000, None),
    "town_east_pasture": AnchorLore("grandia", 20_000, None),
    "town_emerald_lake": AnchorLore("grandia", 20_000, None),
    "town_crystal": AnchorLore("grandia", 18_000, None),
    "town_steed_plain": AnchorLore("grandia", 15_000, None),
    "town_silver_ridge": AnchorLore("grandia", 15_000, None),
    "town_black_soil": AnchorLore("grandia", 15_000, None),
    "port_tide_wind": AnchorLore("grandia", 15_000, None),
    "town_maple_foot": AnchorLore("grandia", 12_000, None),
    "town_orange_blossom": AnchorLore("grandia", 12_000, None),
    "town_north_wood_keep": AnchorLore("grandia", 10_000, None),
    "town_sunrise": AnchorLore("grandia", 10_000, None),
    "town_sunken_bell": AnchorLore("grandia", 10_000, None),
    # Altoria Kingdom: 19 settlements, 578,000 people.
    "port_white_sail": AnchorLore("altoria", 160_000, None),
    "city_confluence": AnchorLore("altoria", 80_000, None),
    "port_south_tide": AnchorLore("altoria", 55_000, None),
    "port_west_ore": AnchorLore("altoria", 40_000, None),
    "city_greyrock": AnchorLore("altoria", 35_000, None),
    "city_east_river": AnchorLore("altoria", 25_000, None),
    "city_salt_ferry": AnchorLore("altoria", 25_000, None),
    "city_salt_road": AnchorLore("altoria", 25_000, None),
    "city_border_bridge": AnchorLore("altoria", 25_000, None),
    "town_olive_ferry": AnchorLore("altoria", 15_000, None),
    "town_ruins_gate": AnchorLore("altoria", 15_000, None),
    "port_fishers_cove": AnchorLore("altoria", 12_000, None),
    "town_honey_vale": AnchorLore("altoria", 12_000, None),
    "port_hills_mouth": AnchorLore("altoria", 10_000, None),
    "town_west_ferry": AnchorLore("altoria", 10_000, None),
    "town_vineyard": AnchorLore("altoria", 10_000, None),
    "town_scarp": AnchorLore("altoria", 8_000, None),
    "town_east_ferry": AnchorLore("altoria", 8_000, None),
    "port_westwind": AnchorLore("altoria", 8_000, None),
    # Valhalla Beast Kingdom: 17 settlements, 339,000 people.
    "city_mutual_market": AnchorLore("valhalla", 40_000, None),
    "city_iron_claw": AnchorLore("valhalla", 40_000, None),
    "city_horn_plain": AnchorLore("valhalla", 35_000, None),
    "city_shadow_wood": AnchorLore("valhalla", 30_000, None),
    "city_moon_howl": AnchorLore("valhalla", 30_000, None),
    "city_swift_wind": AnchorLore("valhalla", 25_000, None),
    "city_tiger_roar": AnchorLore("valhalla", 25_000, None),
    "city_fox_fire": AnchorLore("valhalla", 25_000, None),
    "town_pine_ferry": AnchorLore("valhalla", 15_000, None),
    "town_stag_ferry": AnchorLore("valhalla", 12_000, None),
    "town_ancestor_shrine": AnchorLore("valhalla", 10_000, None),
    "town_falcon": AnchorLore("valhalla", 10_000, None),
    "town_west_ford_camp": AnchorLore("valhalla", 10_000, None),
    "town_grizzly": AnchorLore("valhalla", 10_000, None),
    "town_frost_wind": AnchorLore("valhalla", 8_000, None),
    "town_shaman_cave": AnchorLore("valhalla", 8_000, None),
    "town_east_ford_camp": AnchorLore("valhalla", 6_000, None),
}


#: One frame per discovered settlement document, keyed by its ``location_ref``.
#: The authored metre point is the document's anchor binding; no reverse
#: location list or second coordinate table exists.
LOCAL_FRAME_ANCHOR_REGISTRY: Mapping[str, LocalFrameAnchor] = PublishedView(
    "local_frame_anchors"
)


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
