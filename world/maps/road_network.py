"""Frozen wilderness road network: runtime read view and road-cell lookup.

``tools/road_network.py`` writes ``data/road_network.json``; this module reads
it, decodes it once per process and answers the one question the runtime asks:
is this wilderness cell on a road? Nothing here computes a road, and no
generator (NumPy, SciPy or ``tools``) is imported, so the read view loads in a
runtime without the generation extra.

The published network belongs to the :class:`world.maps.runtime.MapWorld`
bundle: adoption installs the decoded network with :func:`_install` and clears
it with the bundle. An unpublished network answers no road cell instead of
raising, because offline bundles and consumer tests carry no network and truly
have no adopted road.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import TYPE_CHECKING

from elosern_map_core.roads_codec import (
    RoadMetadata,
    RoadNetwork,
    decode_road_network,
    read_road_metadata,
    road_source_signature,
)

if TYPE_CHECKING:
    from elosern_map_core.authoring import AuthoringWorld

#: The repository root the shipped documents are discovered from.
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
#: Standard on-disk location of the generated road artifact.
DATA_PATH = Path(__file__).resolve().parent / "data" / "road_network.json"

_CURRENT: RoadNetwork | None = None


def _install(network: RoadNetwork | None) -> None:
    """Point the global road lookup at one published network (or none)."""
    global _CURRENT
    _CURRENT = network


def current() -> RoadNetwork | None:
    """The published road network, or ``None`` when the bundle carries none."""
    return _CURRENT


def is_road_cell(cell: tuple[int, int]) -> bool:
    """Whether ``cell`` is on a road in the published network."""
    network = _CURRENT
    return network is not None and tuple(cell) in network.cells


def road_cells() -> frozenset[tuple[int, int]]:
    """Every road cell of the published network; empty when none is published."""
    network = _CURRENT
    return network.cells if network is not None else frozenset()


def artifact_metadata() -> RoadMetadata:
    """The committed artifact's version and signatures, without expanding it."""
    return read_road_metadata(DATA_PATH.read_text(encoding="utf-8"))


@functools.cache
def frozen_network() -> RoadNetwork:
    """The committed artifact, decoded once per process."""
    return decode_road_network(DATA_PATH.read_text(encoding="utf-8"))


def source_signature(
    world: AuthoringWorld, elevation_fingerprint: str
) -> str | None:
    """The signature of this candidate's road inputs, or ``None`` without one.

    A candidate that carries no road parameter document cannot certify any
    artifact, so it has no current signature; adoption then rejects it.
    """
    if world.road_network is None:
        return None
    from world.rules import travel_cost

    return road_source_signature(
        world.fingerprints,
        elevation_fingerprint=elevation_fingerprint,
        region_speeds=travel_cost.region_speeds_m_per_hour(),
    )


__all__ = [
    "DATA_PATH",
    "REPOSITORY_ROOT",
    "artifact_metadata",
    "current",
    "frozen_network",
    "is_road_cell",
    "road_cells",
    "source_signature",
]
