"""Offline road network adapter: the published world in, the frozen artifact out.

The algorithm, its input assembly and the artifact encoding live in
``elosern_map_core.roads`` (the ``generation`` extra of the pure map core).
This module is only the game-side adapter. It composes and previews the
candidate world, reads the committed elevation bands and the authored region
speeds, and writes ``world/maps/data/road_network.json``, the sole committed,
read-only generated output.

Regenerate after any change to a settlement's location or gates, the terrain,
the elevation tiles, the region speeds or ``content/maps/road_network.yaml``,
after the partition and the elevation tiles are current::

    uv run --locked python -m tools.road_network

``--check`` regenerates in memory and exits non-zero when the committed file
differs byte for byte. ``--preview PATH`` also writes an image of the network
for human review; keep that path outside the repository.
"""

from __future__ import annotations

import argparse
import os
import resource
import sys
import time
from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np

from elosern_map_core.roads import (
    Road,
    RoadGenerationError,
    RoadInput,
    generate_road_network,
    road_input,
)
from elosern_map_core.roads_codec import decode_road_network

#: The repository root the shipped sources are read from.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPOSITORY_ROOT / "world" / "maps" / "data" / "road_network.json"
COMMAND = "uv run --locked python -m tools.road_network"
ELEVATION_COMMAND = (
    "uv run --locked --project tools/map-editor python "
    ".agents/skills/map-data-authoring/scripts/regenerate_elevation.py"
)

#: Preview colours (RGB).
_SEA = (32, 60, 110)
_LAND = (214, 204, 168)
_FORBIDDEN = (150, 168, 120)
_UNWALKABLE = (96, 92, 88)
_FORD = (90, 170, 230)
_ROAD = (176, 32, 32)
_NODE = (250, 210, 40)


def band_raster(runtime) -> np.ndarray:
    """Every frame cell's elevation band, ``[y, x]``, from the tile bundle.

    A tile is ``tile_cells`` squared bytes, row-major, each ``(band << 4) |
    tier``; cells beyond the frame are sliced away.
    """
    frame = int(runtime.frame_cells)
    tile = int(runtime.tile_cells)
    count = -(-frame // tile)
    bands = np.zeros((count * tile, count * tile), dtype=np.int16)
    for ty in range(count):
        for tx in range(count):
            raw = np.frombuffer(runtime.get_tile(tx, ty), dtype=np.uint8)
            bands[ty * tile : (ty + 1) * tile, tx * tile : (tx + 1) * tile] = (
                raw.reshape(tile, tile) >> 4
            )
    return bands[:frame, :frame]


def build_input() -> RoadInput:
    """The road input of the current candidate world and committed elevation."""
    from world.maps import elevation, runtime
    from world.rules import travel_cost

    composed = runtime.compose()
    runtime.preview(composed)
    world = composed.world
    elevation_runtime = elevation.load_elevation(
        None, expected_frame_cells=world.continent.terrain.frame_cells
    )
    freshness = elevation.freshness(
        elevation_runtime.metadata, world.fingerprints["content/maps/continent.yaml"]
    )
    if not freshness.current:
        raise SystemExit(
            "the elevation artifact is stale, so roads would be built on old bands; "
            f"regenerate it first: {ELEVATION_COMMAND}"
        )
    return road_input(
        world,
        band_raster(elevation_runtime),
        travel_cost.region_speeds_m_per_hour(),
        elevation_runtime.fingerprint,
    )


def artifact_text(inp: RoadInput | None = None) -> str:
    """The complete committed artifact text for the current sources."""
    return generate_road_network(inp if inp is not None else build_input())


def _ford_cells() -> frozenset[tuple[int, int]]:
    """Every authored ford of the published terrain, for the preview only."""
    from world.maps.wilderness_provider import terrain_definition

    fords = terrain_definition().waterway_fords
    return frozenset(tuple(cell) for cells in fords.values() for cell in cells)


def write_preview(
    inp: RoadInput,
    roads: Sequence[Road],
    path: Path,
    fords: Iterable[tuple[int, int]] = (),
) -> None:
    """Draw land, sea, unwalkable cells, fords, roads and nodes, north up."""
    from PIL import Image

    size = inp.size
    image = np.zeros((size, size, 3), dtype=np.uint8)
    land = inp.region != 0
    forbidden_codes = [
        index + 1
        for index, name in enumerate(inp.region_names)
        if name in set(inp.forbidden_regions)
    ]
    image[~land] = _SEA
    image[land & ~inp.walkable] = _UNWALKABLE
    image[inp.walkable] = _LAND
    image[inp.walkable & np.isin(inp.region, forbidden_codes)] = _FORBIDDEN

    def paint(cells: Iterable[tuple[int, int]], colour: tuple[int, int, int]) -> None:
        for x, y in cells:
            if 0 <= x < size and 0 <= y < size:
                image[y, x] = colour

    paint(fords, _FORD)
    for road in roads:
        paint(road.cells, _ROAD)
    for node in inp.nodes:
        for x, y in node.approaches:
            paint(
                ((x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)), _NODE
            )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image[::-1]).save(path)


def _bootstrap() -> None:
    root = REPOSITORY_ROOT
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    import django

    django.setup()
    import evennia

    # portal_mode=True initializes the Evennia API without the server session
    # handler or any database listener, as the reference-context exporter does.
    evennia._init(portal_mode=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the frozen wilderness road network.")
    parser.add_argument("--check", action="store_true", help="fail when the committed file is stale")
    parser.add_argument("--output", type=Path, default=DATA_PATH)
    parser.add_argument(
        "--preview", type=Path, default=None, help="also write a preview image to this path"
    )
    args = parser.parse_args(argv)
    started = time.monotonic()
    _bootstrap()
    inp = build_input()
    try:
        text = artifact_text(inp)
    except RoadGenerationError as error:
        print("road network generation failed:")
        for problem in error.problems:
            print(f"  {problem}")
        return 1
    # Informational only: never a pass/fail criterion. ru_maxrss is KiB on Linux.
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(
        f"generated {len(inp.nodes)} nodes in {time.monotonic() - started:.1f} s "
        f"(peak resident {peak / 1024:.0f} MiB on Linux)"
    )
    if args.preview is not None:
        network = decode_road_network(text)
        roads = [Road(first, second, cells) for first, second, cells in network.roads]
        write_preview(inp, roads, args.preview, fords=_ford_cells())
        print(f"wrote preview {args.preview.resolve()}")
    current = args.output.read_text(encoding="utf-8") if args.output.exists() else None
    if args.check:
        if current != text:
            print(f"{args.output} is stale; run: {COMMAND}")
            return 1
        print(f"{args.output} is up to date")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"wrote {args.output} ({len(text.encode())} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
