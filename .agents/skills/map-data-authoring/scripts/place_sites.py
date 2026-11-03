"""Snap and validate candidate continental cells before you author them.

Run from the repository root, inside the map-core environment (no Evennia,
Django or database is needed):

    uv run --locked --project packages/map-core python \
        .agents/skills/map-data-authoring/scripts/place_sites.py CANDIDATES.json \
        [--output SNAPPED.json] [--min-km 60] [--jobs N]

    uv run --locked --project packages/map-core python \
        .agents/skills/map-data-authoring/scripts/place_sites.py --locations

    uv run --locked --project packages/map-core python \
        .agents/skills/map-data-authoring/scripts/place_sites.py --landmarks --min-km 100

    uv run --locked --project packages/map-core python \
        .agents/skills/map-data-authoring/scripts/place_sites.py --rivers

CANDIDATES.json is a list of objects:

    [{"id": "my_port", "cell": [2073, 247], "snap": "sea", "pop": 180000}]

``snap`` is optional: ``river`` (within 2 cells of a waterway), ``sea``
(within 2 cells of the coast) or ``both``. A snapped site moves to the
nearest walkable, non-water cell that satisfies the condition, searched up to
``--snap-radius`` cells away. Every other key is passed through untouched.
``--locations`` validates the authored ``locations.yaml`` cells and harbour
sites instead of a candidate file. ``--landmarks`` does the same for every
authored ``wilderness_cell`` district landmark in ``districts.yaml`` (for
example after a landmark drag in the editor); landmarks that reference a
location or a settlement node follow their referent and are not listed. ``--rivers`` checks every waterway's
mouth (its last route vertex) instead: a river must end in the sea or join
another waterway, within 2 cells. A mouth that stops inland is easy to miss on
the editor canvas and leaves its "river mouth" ports with no water.

For each site it reports: walkable, whether the cell is waterway, terrain
region, nominal nation, distance (cells) to the nearest waterway and to the
sea, and every pair closer than ``--min-km``. The terrain checks are pure
Python and CPU-bound, so the sites are spread over a process pool (one
worker per CPU by default) rather than threads, which the GIL would
serialise.

Exit status: 0 when every site is walkable and off the water (or, with
``--rivers``, every mouth reaches the sea or another waterway), 1 otherwise,
2 when the sources do not load. The script never writes map sources; only
``--output`` writes the snapped candidate list.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

SNAP_MODES = ("river", "sea", "both")
NEAR_CELLS = 2

_TERRAIN = None
_WATER: frozenset = frozenset()


def _load_world(root: Path):
    from elosern_map_core import discover_source_documents, load_authoring_world

    return load_authoring_world(discover_source_documents(root))


def _init_worker(root: str) -> None:
    global _TERRAIN, _WATER
    from elosern_map_core import terrain
    from elosern_map_core.authoring import terrain_definition

    _TERRAIN = terrain_definition(_load_world(Path(root)).continent)
    _WATER = terrain.rasterize_routes(_TERRAIN.waterway_routes)


@lru_cache(maxsize=None)
def _land(cell: tuple[int, int]) -> bool:
    from elosern_map_core.terrain import is_land_cell

    return is_land_cell(_TERRAIN, cell)


@lru_cache(maxsize=None)
def _walkable(cell: tuple[int, int]) -> bool:
    from elosern_map_core.terrain import is_walkable_cell

    return is_walkable_cell(_TERRAIN, cell)


def _ring(centre: tuple[int, int], k: int):
    """Cells on the Chebyshev ring of radius ``k`` around ``centre``."""

    x, y = centre
    if k == 0:
        yield centre
        return
    for dx in range(-k, k + 1):
        yield (x + dx, y - k)
        yield (x + dx, y + k)
    for dy in range(-k + 1, k):
        yield (x - k, y + dy)
        yield (x + k, y + dy)


def _ring_distance(centre, predicate, limit: int) -> int | None:
    for k in range(limit + 1):
        if any(predicate(cell) for cell in _ring(centre, k)):
            return k
    return None


def _near_water(cell) -> bool:
    return _ring_distance(cell, lambda c: c in _WATER, NEAR_CELLS) is not None


def _near_sea(cell) -> bool:
    return _ring_distance(cell, lambda c: not _land(c), NEAR_CELLS) is not None


def _snap(centre, mode: str, limit: int):
    wanted = {
        "river": _near_water,
        "sea": _near_sea,
        "both": lambda c: _near_water(c) and _near_sea(c),
    }[mode]
    best = None
    for k in range(limit + 1):
        for cell in _ring(centre, k):
            if cell in _WATER or not _walkable(cell) or not wanted(cell):
                continue
            distance = math.hypot(cell[0] - centre[0], cell[1] - centre[1])
            if best is None or distance < best[0]:
                best = (distance, cell)
        # Euclidean distance never exceeds the ring radius times sqrt(2) and
        # never falls below it, so once a hit is no farther than the current
        # ring radius no outer ring can beat it.
        if best is not None and best[0] <= k:
            break
    return best


def _evaluate(job: tuple[dict, int, int]) -> dict:
    from elosern_map_core import terrain

    site, snap_radius, measure_radius = job
    cell = tuple(site["cell"])
    moved = None
    unsnapped = False
    mode = site.get("snap")
    if mode:
        hit = _snap(cell, mode, snap_radius)
        if hit is None:
            unsnapped = True
        else:
            moved, cell = round(hit[0], 1), hit[1]
    return {
        **site,
        "cell": list(cell),
        "_moved": moved,
        "_unsnapped": unsnapped,
        "_walkable": _walkable(cell),
        "_on_water": cell in _WATER,
        "_region": terrain.region_for_coordinates(_TERRAIN, *cell),
        "_nation": terrain.nominal_nation_for_coordinates(_TERRAIN, *cell),
        "_river": _ring_distance(cell, lambda c: c in _WATER, measure_radius),
        "_coast": _ring_distance(cell, lambda c: not _land(c), measure_radius),
    }


def _mouth(job: tuple[str, int]) -> dict:
    from elosern_map_core.terrain import rasterize_routes

    name, limit = job
    route = _TERRAIN.waterway_routes[name]
    mouth = tuple(route[-1])
    others = rasterize_routes(
        {key: points for key, points in _TERRAIN.waterway_routes.items() if key != name}
    )
    return {
        "id": name,
        "mouth": list(mouth),
        "sea": _ring_distance(mouth, lambda c: not _land(c), limit),
        "joins": _ring_distance(mouth, lambda c: c in others, limit),
    }


def _check_rivers(root: Path, jobs: int, limit: int) -> int:
    world = _load_world(root)
    names = sorted(world.continent.terrain.waterways)
    with ProcessPoolExecutor(
        max_workers=max(1, min(jobs, len(names))), initializer=_init_worker, initargs=(str(root),)
    ) as pool:
        rows = list(pool.map(_mouth, [(name, limit) for name in names]))
    failed = 0
    for row in rows:
        reached = [d for d in (row["sea"], row["joins"]) if d is not None]
        bad = not reached or min(reached) > NEAR_CELLS
        failed += bad
        print(
            f"{'!!' if bad else 'ok'} {row['id']} mouth=({row['mouth'][0]},{row['mouth'][1]}) "
            f"sea={row['sea']} joins_waterway={row['joins']}"
        )
    print(f"{len(rows) - failed}/{len(rows)} waterways reach the sea or another waterway")
    return 1 if failed else 0


def _authored_sites(root: Path) -> list[dict]:
    world = _load_world(root)
    sites = [
        {"id": f"location:{key}", "cell": list(row.cell)}
        for key, row in sorted(world.locations.locations.items())
    ]
    sites += [
        {"id": f"harbor_site:{key}", "cell": list(row.cell)}
        for key, row in sorted(world.continent.harbor_sites.items())
    ]
    return sites


def _authored_landmarks(root: Path) -> list[dict]:
    world = _load_world(root)
    return [
        {"id": f"district:{key}", "cell": list(row.landmark.cell)}
        for key, row in sorted(world.districts.districts.items())
        if row.landmark.domain == "wilderness_cell" and row.landmark.cell is not None
    ]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("candidates", nargs="?", type=Path)
    source.add_argument("--locations", action="store_true")
    source.add_argument("--landmarks", action="store_true")
    source.add_argument("--rivers", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--min-km", type=float, default=60.0)
    parser.add_argument("--snap-radius", type=int, default=40)
    parser.add_argument("--measure-radius", type=int, default=40)
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    if args.rivers:
        try:
            return _check_rivers(root, args.jobs, args.measure_radius)
        except Exception as error:  # noqa: BLE001 - a source failure surfaces here
            print(f"cannot check waterways: {error}", file=sys.stderr)
            return 2
    try:
        if args.locations:
            sites = _authored_sites(root)
        elif args.landmarks:
            sites = _authored_landmarks(root)
        else:
            sites = json.loads(args.candidates.read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001 - report any load failure plainly
        print(f"cannot load sites: {error}", file=sys.stderr)
        return 2
    for site in sites:
        if site.get("snap") not in (None, *SNAP_MODES):
            print(f"{site.get('id')}: unknown snap mode {site['snap']!r}", file=sys.stderr)
            return 2

    jobs = [(site, args.snap_radius, args.measure_radius) for site in sites]
    try:
        with ProcessPoolExecutor(
            max_workers=max(1, args.jobs), initializer=_init_worker, initargs=(str(root),)
        ) as pool:
            results = list(pool.map(_evaluate, jobs, chunksize=1))
    except Exception as error:  # noqa: BLE001 - a source failure surfaces here
        print(f"cannot evaluate sites: {error}", file=sys.stderr)
        return 2

    failed = 0
    width = max((len(str(row["id"])) for row in results), default=4)
    for row in results:
        bad = not row["_walkable"] or row["_on_water"] or row["_unsnapped"]
        failed += bad
        moved = "unsnapped" if row["_unsnapped"] else row["_moved"]
        print(
            f"{'!!' if bad else 'ok'} {row['id']:<{width}} "
            f"cell=({row['cell'][0]},{row['cell'][1]}) moved={moved} "
            f"walkable={row['_walkable']} water_cell={row['_on_water']} "
            f"region={row['_region']} nation={row['_nation']} "
            f"river={row['_river']} coast={row['_coast']}"
        )
    print(f"--- pairs closer than {args.min_km:g} km")
    for i, first in enumerate(results):
        for second in results[i + 1:]:
            a, b = first["cell"], second["cell"]
            distance = math.hypot(a[0] - b[0], a[1] - b[1])
            if distance < args.min_km:
                print(f"  {first['id']} - {second['id']}: {distance:.0f} km")

    if args.output:
        clean = [{k: v for k, v in row.items() if not k.startswith("_")} for row in results]
        for row in clean:
            row.pop("snap", None)
        args.output.write_text(json.dumps(clean, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {args.output}")
    print(f"{len(results) - failed}/{len(results)} sites valid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
