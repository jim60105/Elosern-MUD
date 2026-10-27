"""Terrain region and reserved-site views for the wilderness/Virtual map layer.

The authored declarations (frame, cell size, mainland boundary, terrain regions
and reserved harbor sites) live in ``content/maps/continent.yaml`` and are
loaded and validated by :mod:`world.maps.geography`. This module owns only the
read-only view types and the thin helpers every consumer shares; it holds no
authored values, so a reload can never leave a second copy behind.

The polygon and frame arithmetic these helpers feed lives in
``elosern_map_core.geometry``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from elosern_map_core import geometry as core_geometry


@dataclass(frozen=True)
class HarborSite:
    """One reserved land-side harbor cell.

    A functional site is not a named anchor: it declares no city, quest,
    anchor key or population, and it is not mirrored into room lifecycle.
    """

    key: str
    display_name: str
    cell: tuple[int, int]
    role: str


@dataclass(frozen=True)
class WildernessRegion:
    """One terrain region covering part of the continent's wilderness.

    ``nation_key`` names the single nation that nominally claims the whole
    region, or is ``None`` when the region straddles a nominal border (the
    central mountains and the northern deep forest). ``nominal_nation_keys``
    lists every nation that claims some of the region's cells, sorted; the
    per-cell claim is ``world.maps.wilderness_provider.
    nominal_nation_for_coordinates``. Both name keys in
    ``world.lore.nations.NATION_REGISTRY``.

    ``scene_archetype`` is the map-owned region scene association, validated
    against the game scene catalog when the geography is published.
    """

    key: str
    display_name_zh: str
    nation_key: str | None
    terrain_flavor_zh: tuple[str, ...]
    nominal_nation_keys: tuple[str, ...] = ()
    scene_archetype: str | None = None


def _geography():
    from world.maps.geography import current

    return current()


def regions() -> Mapping[str, WildernessRegion]:
    """The published terrain region views, keyed by classifier region key."""

    return _geography().regions


def harbor_sites() -> Mapping[str, HarborSite]:
    """The published reserved harbor-site views."""

    return _geography().harbor_sites


def frame_cells() -> int:
    """The enclosing wilderness frame's cell count per axis."""

    return _geography().frame_cells


def cell_size_km() -> int:
    """Logical size of one wilderness cell, kilometres per axis."""

    return _geography().cell_size_km


def mainland_boundary_km() -> tuple[tuple[int, int], ...]:
    """Ordered mainland boundary vertices as absolute ``(east, north)`` km."""

    return _geography().mainland_boundary_km


def is_wilderness_cell(cell: tuple[int, int]) -> bool:
    """Whether ``(x, y)`` is inside the declared enclosing frame."""

    return core_geometry.is_within_frame(frame_cells(), cell)


def mainland_area_km2() -> float:
    """Shoelace area of the closed mainland boundary, square kilometres."""

    return core_geometry.polygon_area_km2(mainland_boundary_km())


def is_on_mainland(east_km: float, north_km: float) -> bool:
    """Whether an absolute ``(east, north)`` kilometre point is on land.

    Boundary points count as land; sea and the ocean margin do not.
    """

    return core_geometry.is_on_mainland(mainland_boundary_km(), east_km, north_km)


__all__ = [
    "HarborSite",
    "WildernessRegion",
    "cell_size_km",
    "frame_cells",
    "harbor_sites",
    "is_on_mainland",
    "is_wilderness_cell",
    "mainland_area_km2",
    "mainland_boundary_km",
    "regions",
]
