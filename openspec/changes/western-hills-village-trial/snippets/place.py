"""Placement working tool for the western-hills trial rectangle.

Throwaway helper for `western-hills-village-trial` (design D1). It reads the
authored locations, the frozen road artifact and the terrain through
`elosern_map_core`, and prints candidates and gap reports. It never writes a
map source or a location row.

    uv run --locked python openspec/changes/western-hills-village-trial/snippets/place.py gaps
    uv run --locked python openspec/changes/western-hills-village-trial/snippets/place.py road "town_honey_vale -- town_scarp"
    uv run --locked python openspec/changes/western-hills-village-trial/snippets/place.py villages
    uv run --locked python openspec/changes/western-hills-village-trial/snippets/place.py hamlets
    uv run --locked python openspec/changes/western-hills-village-trial/snippets/place.py check CELL CANDIDATES.json

`gaps` lists every road gap over 75 km that lies wholly inside the trial
rectangle. `road` dumps one road's cells with the facts a site decision needs.
`villages` and `hamlets` print a JSON candidate list that
`.agents/skills/map-data-authoring/scripts/place_sites.py` accepts, plus a
ranking comment on stderr.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from elosern_map_core.authoring import gate_approach_cell, terrain_definition
from elosern_map_core.roads_codec import decode_road_network
from elosern_map_core.terrain import (
    is_walkable_cell,
    rasterize_routes,
    region_for_coordinates,
)

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.settlement_synthesis.workspace import load_workspace  # noqa: E402

REGION = "western_hills_valleys"
SCOPE = (1000, 501, 1340, 950)  # x_min, y_min, x_max, y_max inclusive
ROAD_GAP_KM = 75.0
VILLAGE_KM = 40.0
HAMLET_KM = 15.0
NATIONAL_KINDS = ("capital", "city", "town", "port")
SMALL_KINDS = ("village", "hamlet")
DIAGONAL = math.sqrt(2.0)


# ---------------------------------------------------------------- loading


class World:
    """Everything one placement decision reads, loaded once."""

    def __init__(self, roads_path: Path | None = None) -> None:
        self.view = load_workspace(ROOT)
        self.world = self.view.world
        self.definition = terrain_definition(self.world.continent)
        self.network = decode_road_network(
            (
                roads_path
                or ROOT / "world" / "maps" / "data" / "road_network.json"
            ).read_text(encoding="utf-8")
        )
        self.water = rasterize_routes(self.definition.waterway_routes)
        self.places = {
            key: (row.kind, tuple(row.cell))
            for key, row in sorted(self.world.locations.locations.items())
        }
        self.occupied = self._occupied()
        self.habitat = self._habitat()
        self.road_segments = self._road_segments()

    def _occupied(self) -> dict[tuple[int, int], str]:
        cells: dict[tuple[int, int], str] = {}
        for key, row in self.world.locations.locations.items():
            cells[tuple(row.cell)] = f"location:{key}"
        for key, row in self.world.continent.harbor_sites.items():
            cells[tuple(row.cell)] = f"harbour:{key}"
        for key, row in self.world.districts.districts.items():
            landmark = row.landmark
            if landmark.domain == "wilderness_cell" and landmark.cell is not None:
                cells[tuple(landmark.cell)] = f"landmark:{key}"
        for key in sorted(self.world.settlements):
            document = self.world.settlements[key]
            location = self.world.locations.locations.get(document.location_ref)
            if location is None:
                continue
            geometry = document.wilderness_geometry(tuple(location.cell))
            if geometry is None:
                continue
            for cell in geometry.footprint_cells:
                cells[cell] = f"footprint:{key}"
            for gate in document.wilderness_entry.gates:
                approach = gate_approach_cell(geometry, gate.return_direction)
                if approach is not None:
                    cells[approach] = f"gate:{key}"
        return cells

    @staticmethod
    def _habitat() -> set[tuple[int, int]]:
        from world.lore.monster_placement import (
            ECOLOGY_ZONE_REGISTRY,
            MONSTER_SITE_REGISTRY,
        )

        blocked: set[tuple[int, int]] = set()
        for zone in ECOLOGY_ZONE_REGISTRY.values():
            for x_min, x_max, y_min, y_max in zone.rectangles:
                for x in range(x_min, x_max + 1):
                    for y in range(y_min, y_max + 1):
                        blocked.add((x, y))
        for site in MONSTER_SITE_REGISTRY.values():
            blocked.add(tuple(site.coordinates))
        return blocked

    def _road_segments(self) -> list[tuple[str, str, list[tuple[int, int]]]]:
        return [(first, second, list(cells)) for first, second, cells in self.network.roads]

    # ------------------------------------------------------------ terrain

    def in_scope(self, cell: tuple[int, int]) -> bool:
        x_min, y_min, x_max, y_max = SCOPE
        return (
            x_min <= cell[0] <= x_max
            and y_min <= cell[1] <= y_max
            and region_for_coordinates(self.definition, *cell) == REGION
        )

    def walkable(self, cell: tuple[int, int]) -> bool:
        return (
            cell not in self.water
            and is_walkable_cell(self.definition, cell)
        )

    def habitat_clear(self, cell: tuple[int, int]) -> bool:
        return all(
            (cell[0] + dx, cell[1] + dy) not in self.habitat
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
        )

    def water_distance(self, cell: tuple[int, int], limit: int = 6) -> int | None:
        for radius in range(limit + 1):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if max(abs(dx), abs(dy)) == radius:
                        if (cell[0] + dx, cell[1] + dy) in self.water:
                            return radius
        return None

    def relief(self, cell: tuple[int, int]) -> int:
        """The band range over the walkable 3-cell neighbourhood (design `site`)."""

        window = self.view.terrain_window(cell, 3)
        bands = [
            window.band(other)
            for other in window.bands
            if window.walkable(other)
        ]
        bands.append(window.band(cell))
        return max(bands) - min(bands)

    def band(self, cell: tuple[int, int]) -> int:
        return self.view.terrain_window(cell, 0).band(cell)


# ------------------------------------------------------------ road facts


def road_cells(world: World) -> dict[tuple[int, int], list[str]]:
    """Every road cell with the names of the roads that carry it."""

    cells: dict[tuple[int, int], list[str]] = {}
    for first, second, path in world.road_segments:
        for cell in path:
            cells.setdefault(cell, []).append(f"{first} -- {second}")
    return cells


def inner_cells(world: World) -> set[tuple[int, int]]:
    """Cells of a road that are neither its first nor its last cell."""

    inner: set[tuple[int, int]] = set()
    ends: set[tuple[int, int]] = set()
    for _, _, path in world.road_segments:
        ends.add(path[0])
        ends.add(path[-1])
        inner.update(path[1:-1])
    return inner - ends


def step_km(first: tuple[int, int], second: tuple[int, int]) -> float:
    diagonal = first[0] != second[0] and first[1] != second[1]
    return DIAGONAL if diagonal else 1.0


def gap_report(world: World) -> list[dict]:
    """Every gap over the maximum that lies wholly inside the trial rectangle."""

    marked = {
        place_cell
        for kind, place_cell in world.places.values()
        if kind in SMALL_KINDS
    }
    reports = []
    for first, second, path in world.road_segments:
        positions = sorted(
            {0, len(path) - 1}
            | {index for index, cell in enumerate(path) if cell in marked}
        )
        for start, end in zip(positions, positions[1:]):
            gap = path[start : end + 1]
            length = sum(step_km(a, b) for a, b in zip(gap, gap[1:]))
            if length <= ROAD_GAP_KM:
                continue
            if not all(world.in_scope(cell) for cell in gap):
                continue
            reports.append(
                {
                    "road": f"{first} -- {second}",
                    "from": list(gap[0]),
                    "to": list(gap[-1]),
                    "from_index": start,
                    "to_index": end,
                    "cells": len(gap),
                    "km": round(length, 1),
                }
            )
    return reports


# ------------------------------------------------------------ eligibility


def spacing_ok(world: World, cell: tuple[int, int], kind: str) -> tuple[bool, str]:
    for place_id, (place_kind, place_cell) in world.places.items():
        distance = math.hypot(cell[0] - place_cell[0], cell[1] - place_cell[1])
        if kind == "village":
            if place_kind in (*NATIONAL_KINDS, "village") and distance < VILLAGE_KM:
                return False, f"{distance:.1f} km from {place_id} ({place_kind})"
        else:
            if place_kind in (*NATIONAL_KINDS, *SMALL_KINDS) and distance < HAMLET_KM:
                return False, f"{distance:.1f} km from {place_id} ({place_kind})"
    return True, ""


def eligible(
    world: World,
    cell: tuple[int, int],
    kind: str,
    *,
    on_road: bool | None = None,
    roads: dict[tuple[int, int], list[str]] | None = None,
    inner: set[tuple[int, int]] | None = None,
) -> tuple[bool, str]:
    if not world.in_scope(cell):
        return False, "outside the trial rectangle"
    if not world.walkable(cell):
        return False, "not walkable or water"
    if cell in world.occupied:
        return False, f"occupied by {world.occupied[cell]}"
    if not world.habitat_clear(cell):
        return False, "inside a monster habitat"
    if on_road is not None:
        on = bool(roads and cell in roads)
        if on != on_road:
            return False, "on a road" if on else "off every road"
        if on and inner is not None and cell not in inner:
            return False, "a road end cell"
    ok, reason = spacing_ok(world, cell, kind)
    if not ok:
        return False, reason
    return True, ""


def trunk_distance(world: World, cell: tuple[int, int]) -> float:
    """Cells from the nearest road cell other than a village spur."""

    road = set()
    for _, _, path in world.road_segments:
        road.update(path)
    return min(
        (math.hypot(cell[0] - other[0], cell[1] - other[1]) for other in road),
        default=float("inf"),
    )


# ------------------------------------------------------------ proposals


def village_candidates(world: World, limit: int) -> list[dict]:
    """Rank village sites: gap coverage first, then terrain quality."""

    roads = road_cells(world)
    inner = inner_cells(world)
    gaps = gap_report(world)
    rows = []
    if gaps:
        for gap in gaps:
            first, second, path = next(
                (f, s, p) for f, s, p in world.road_segments if f"{f} -- {s}" == gap["road"]
            )
            slice_ = path[gap["from_index"] : gap["to_index"] + 1]
            cumulative = [0.0]
            for a, b in zip(slice_, slice_[1:]):
                cumulative.append(cumulative[-1] + step_km(a, b))
            total = cumulative[-1]
            for index, cell in enumerate(slice_):
                if cell not in inner or cell not in roads:
                    continue
                ok, _ = eligible(
                    world, cell, "village", on_road=True, roads=roads, inner=inner
                )
                if not ok:
                    continue
                split = max(
                    cumulative[index],
                    total - cumulative[index],
                )
                rows.append(
                    {
                        "cell": cell,
                        "road": f"{first} -- {second}",
                        "km": round(cumulative[index], 1),
                        "longest_remaining_km": round(split, 1),
                        "relief": world.relief(cell),
                        "water": world.water_distance(cell),
                    }
                )
    # An off-trunk village: 20 to 60 km from a trunk, with a geographic reason.
    seen: set[tuple[int, int]] = set()
    for x in range(SCOPE[0], SCOPE[2] + 1, 5):
        for y in range(SCOPE[1], SCOPE[3] + 1, 5):
            cell = (x, y)
            if cell in seen:
                continue
            seen.add(cell)
            ok, _ = eligible(world, cell, "village", on_road=False, roads=roads)
            if not ok:
                continue
            distance = trunk_distance(world, cell)
            if not 20.0 <= distance <= 60.0:
                continue
            water = world.water_distance(cell, 6)
            if water is None:
                continue
            rows.append(
                {
                    "cell": cell,
                    "road": "off-trunk",
                    "km": None,
                    "longest_remaining_km": None,
                    "relief": world.relief(cell),
                    "water": water,
                    "trunk_km": round(distance, 1),
                }
            )
    rows.sort(
        key=lambda row: (
            0 if row["road"] != "off-trunk" else 1,
            row["longest_remaining_km"] if row["longest_remaining_km"] is not None else 999,
            row["relief"],
            row["water"] if row["water"] is not None else 99,
        )
    )
    return rows[:limit]


def hamlet_candidates(world: World, limit: int) -> list[dict]:
    roads = road_cells(world)
    inner = inner_cells(world)
    gaps = gap_report(world)
    rows = []
    for gap in gaps:
        first, second, path = next(
            (f, s, p) for f, s, p in world.road_segments if f"{f} -- {s}" == gap["road"]
        )
        slice_ = path[gap["from_index"] : gap["to_index"] + 1]
        for cell in slice_:
            if cell not in inner or cell not in roads:
                continue
            ok, _ = eligible(
                world, cell, "hamlet", on_road=True, roads=roads, inner=inner
            )
            if not ok:
                continue
            rows.append(
                {
                    "cell": cell,
                    "road": f"{first} -- {second}",
                    "relief": world.relief(cell),
                    "water": world.water_distance(cell),
                }
            )
    rows.sort(key=lambda row: (row["relief"], row["water"] or 99))
    return rows[:limit]


# --------------------------------------------------------------- commands


def command_gaps(world: World) -> int:
    report = gap_report(world)
    print(json.dumps(report, indent=1))
    for gap in report:
        print(
            f"{gap['road']}: {tuple(gap['from'])} to {tuple(gap['to'])} "
            f"is {gap['km']} km ({gap['cells']} cells)",
            file=sys.stderr,
        )
    return 0


def command_road(world: World, name: str) -> int:
    roads = road_cells(world)
    inner = inner_cells(world)
    for first, second, path in world.road_segments:
        label = f"{first} -- {second}"
        if label != name:
            continue
        cumulative = 0.0
        for index, cell in enumerate(path):
            if index:
                cumulative += step_km(path[index - 1], cell)
            if not world.in_scope(cell):
                continue
            ok, reason = eligible(
                world, cell, "hamlet", on_road=True, roads=roads, inner=inner
            )
            band = world.band(cell)
            water = world.water_distance(cell)
            print(
                f"[{index:3d}] {cell} cum={cumulative:6.1f} "
                f"band={band:2d} relief={world.relief(cell)} water={water} "
                f"{'OK' if ok else '-- ' + reason}"
            )
        return 0
    print(f"unknown road {name!r}", file=sys.stderr)
    return 2


def command_villages(world: World, limit: int) -> int:
    rows = village_candidates(world, limit)
    for row in rows:
        print(json.dumps(row), file=sys.stderr)
    print(json.dumps([{"cell": row["cell"]} for row in rows], indent=0))
    return 0


def command_hamlets(world: World, limit: int) -> int:
    rows = hamlet_candidates(world, limit)
    for row in rows:
        print(json.dumps(row), file=sys.stderr)
    print(json.dumps([{"cell": row["cell"]} for row in rows], indent=0))
    return 0


def command_check(world: World, cell_text: str, kind: str) -> int:
    x, y = (int(part) for part in cell_text.split(","))
    ok, reason = eligible(world, (x, y), kind)
    print(
        json.dumps(
            {
                "cell": [x, y],
                "kind": kind,
                "ok": ok,
                "reason": reason,
                "band": world.band((x, y)),
                "relief": world.relief((x, y)),
                "water": world.water_distance((x, y)),
                "trunk": round(trunk_distance(world, (x, y)), 1),
            }
        )
    )
    return 0 if ok else 1


def command_plan(world: World, path: Path) -> int:
    """Validate a proposed plan and report the gaps it leaves."""

    import json as _json

    plan = _json.loads(path.read_text(encoding="utf-8"))
    roads = road_cells(world)
    inner = inner_cells(world)
    proposed: dict[tuple[int, int], dict] = {}
    failed = False
    for row in plan:
        cell = tuple(row["cell"])
        kind = row["kind"]
        on_road = cell in roads
        ok, reason = eligible(
            world, cell, kind, on_road=on_road, roads=roads, inner=inner
        )
        if on_road and cell not in inner:
            ok, reason = False, "a road end cell"
        print(
            f"{'ok ' if ok else 'BAD'} {row['id']:<36} {kind:<8} {cell} "
            f"{'road' if on_road else 'off-road'} {reason}"
        )
        failed |= not ok
        proposed[cell] = row
    # Spacing among the proposed rows themselves.
    rows = list(proposed.values())
    for index, first in enumerate(rows):
        for second in rows[index + 1 :]:
            distance = math.hypot(
                first["cell"][0] - second["cell"][0],
                first["cell"][1] - second["cell"][1],
            )
            minimum = (
                VILLAGE_KM
                if first["kind"] == "village" and second["kind"] == "village"
                else HAMLET_KM
            )
            if distance < minimum:
                failed = True
                print(
                    f"BAD {first['id']} - {second['id']}: {distance:.1f} km "
                    f"< {minimum:.0f} km"
                )
    # The gaps the plan leaves, under the completed-area rule.
    marked = set(proposed) | {
        cell for kind, cell in world.places.values() if kind in SMALL_KINDS
    }
    for first, second, path_cells in world.road_segments:
        positions = sorted(
            {0, len(path_cells) - 1}
            | {
                index
                for index, cell in enumerate(path_cells)
                if cell in marked
            }
        )
        for start, end in zip(positions, positions[1:]):
            gap = path_cells[start : end + 1]
            length = sum(step_km(a, b) for a, b in zip(gap, gap[1:]))
            inside = all(world.in_scope(cell) for cell in gap)
            flag = "checked" if inside else "outside"
            bad = "BAD " if inside and length > ROAD_GAP_KM else "ok  "
            print(
                f"{bad}gap {first} -- {second} {gap[0]}..{gap[-1]} "
                f"{length:6.1f} km [{flag}]"
            )
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "command", choices=("gaps", "road", "villages", "hamlets", "check", "plan")
    )
    parser.add_argument("argument", nargs="?")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument(
        "--roads",
        type=Path,
        default=None,
        help="an explicit road artifact instead of the checkout's own",
    )
    args = parser.parse_args(argv)
    world = World(args.roads)
    if args.command == "gaps":
        return command_gaps(world)
    if args.command == "road":
        return command_road(world, args.argument)
    if args.command == "villages":
        return command_villages(world, args.limit)
    if args.command == "hamlets":
        return command_hamlets(world, args.limit)
    if args.command == "plan":
        return command_plan(world, Path(args.argument))
    return command_check(world, args.argument, "hamlet")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
