"""Placement working tool for Grandia's southern plains and south-east coast.

Throwaway helper for `grandia-south-village-placement` (design D1). It reads the
authored locations, the frozen road artifact and the terrain through
`elosern_map_core`, and prints gap reports and candidate lists. It never writes
a map source or a location row.

    uv run --locked python openspec/changes/grandia-south-village-placement/snippets/place.py survey
    uv run --locked python openspec/changes/grandia-south-village-placement/snippets/place.py gaps
    uv run --locked python openspec/changes/grandia-south-village-placement/snippets/place.py road "city_x -- town_y"
    uv run --locked python openspec/changes/grandia-south-village-placement/snippets/place.py villages
    uv run --locked python openspec/changes/grandia-south-village-placement/snippets/place.py off-trunk
    uv run --locked python openspec/changes/grandia-south-village-placement/snippets/place.py hamlets
    uv run --locked python openspec/changes/grandia-south-village-placement/snippets/place.py off-road
    uv run --locked python openspec/changes/grandia-south-village-placement/snippets/place.py check 2100,900 village
    uv run --locked python openspec/changes/grandia-south-village-placement/snippets/place.py plan PLAN.json

The scope is region `southeast_coast` in full and region `eastern_plains` at
y 1100 and below. Road coverage is checked over those cells plus the two areas
completed earlier, because a gap that crosses their boundary is checked once
both sides are complete (tiers design §6, resolution 6).
"""

from __future__ import annotations

import argparse
import bisect
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

REGION = "southeast_coast"
BOUNDED_REGION = "eastern_plains"
BOUNDED_Y_MAX = 1100
PRIOR_REGIONS = ("western_hills_valleys", "southwest_coast")
ROAD_GAP_KM = 75.0
VILLAGE_KM = 40.0
HAMLET_KM = 15.0
NATIONAL_KINDS = ("capital", "city", "town", "port")
SMALL_KINDS = ("village", "hamlet")
SETTLEMENT_KINDS = NATIONAL_KINDS + SMALL_KINDS
DIAGONAL = math.sqrt(2.0)
BUCKET = 10


# ---------------------------------------------------------------- loading


class World:
    """Everything one placement decision reads, loaded once."""

    def __init__(
        self,
        roads_path: Path | None = None,
        root: Path | None = None,
        without: Path | None = None,
        foreign: bool = False,
    ) -> None:
        self.root = root or ROOT
        self.view = load_workspace(self.root)
        self.world = self.view.world
        #: Whether the earlier completed areas may take a boundary hamlet
        #: under design D2.
        self.foreign = foreign
        self.hidden: set[str] = set()
        if without is not None:
            self.hidden = {
                row["id"]
                for row in json.loads(without.read_text(encoding="utf-8"))
            }
        self.definition = terrain_definition(self.world.continent)
        self.network = decode_road_network(
            (
                roads_path
                or self.root / "world" / "maps" / "data" / "road_network.json"
            )
            .read_text(encoding="utf-8")
        )
        self.water = rasterize_routes(self.definition.waterway_routes)
        self.places = {
            key: (row.kind, tuple(row.cell), row.display_name_zh)
            for key, row in sorted(self.world.locations.locations.items())
            if key not in self.hidden
        }
        self.occupied = self._occupied()
        self.habitat = self._habitat()
        self.road_segments = [
            (first, second, list(cells)) for first, second, cells in self.network.roads
        ]
        self._buckets: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for _, _, path in self.road_segments:
            for cell in path:
                self._buckets.setdefault(self._bucket(cell), []).append(cell)

    def _occupied(self) -> dict[tuple[int, int], str]:
        cells: dict[tuple[int, int], str] = {}
        for key, row in self.world.locations.locations.items():
            if key in self.hidden:
                continue
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

    # ------------------------------------------------------------ terrain

    def region(self, cell: tuple[int, int]) -> str:
        return region_for_coordinates(self.definition, *cell)

    def in_region(self, cell: tuple[int, int]) -> bool:
        """Whether the cell is in this change's area."""

        region = self.region(cell)
        if region == REGION:
            return True
        return region == BOUNDED_REGION and cell[1] <= BOUNDED_Y_MAX

    def in_completed(self, cell: tuple[int, int]) -> bool:
        """Whether a cell lies in a completed area, the earlier ones included."""

        return self.in_region(cell) or self.region(cell) in PRIOR_REGIONS

    def in_scope(self, cell: tuple[int, int]) -> bool:
        """Whether a settlement may stand on the cell."""

        return self.in_region(cell) or (
            self.foreign and self.region(cell) in PRIOR_REGIONS
        )

    def walkable(self, cell: tuple[int, int]) -> bool:
        return cell not in self.water and is_walkable_cell(self.definition, cell)

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
        """The band range over the walkable 3-cell neighbourhood."""

        window = self.view.terrain_window(cell, 3)
        bands = [
            window.band(other) for other in window.bands if window.walkable(other)
        ]
        bands.append(window.band(cell))
        return max(bands) - min(bands)

    def band(self, cell: tuple[int, int]) -> int:
        return self.view.terrain_window(cell, 0).band(cell)

    # ------------------------------------------------------------ roads

    @staticmethod
    def _bucket(cell: tuple[int, int]) -> tuple[int, int]:
        return (cell[0] // BUCKET, cell[1] // BUCKET)

    def trunk_distance(self, cell: tuple[int, int]) -> float:
        """Cells to the nearest road cell, searched outward in 10-cell rings."""

        centre = self._bucket(cell)
        best = float("inf")
        ring = 0
        while ring * BUCKET <= best:
            for bx in range(centre[0] - ring, centre[0] + ring + 1):
                for by in range(centre[1] - ring, centre[1] + ring + 1):
                    if max(abs(bx - centre[0]), abs(by - centre[1])) != ring:
                        continue
                    for other in self._buckets.get((bx, by), ()):
                        distance = math.hypot(cell[0] - other[0], cell[1] - other[1])
                        best = min(best, distance)
            ring += 1
        return best


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


def trunk_inner_cells(world: World) -> set[tuple[int, int]]:
    """Trunk cells that are neither the first nor the last cell of a trunk.

    A village stands on an inner trunk cell; its own spur also makes it the
    end of a new road, which the all-road rule would reject even though D2
    still holds. Hamlets keep the stricter all-road rule.
    """

    inner: set[tuple[int, int]] = set()
    ends: set[tuple[int, int]] = set()
    owners = world.network.spur_owners
    for first, second, path in world.road_segments:
        if owners.get((first, second)) is not None:
            continue
        ends.add(path[0])
        ends.add(path[-1])
        inner.update(path[1:-1])
    return inner - ends


def step_km(first: tuple[int, int], second: tuple[int, int]) -> float:
    diagonal = first[0] != second[0] and first[1] != second[1]
    return DIAGONAL if diagonal else 1.0


def marked_cells(world: World) -> set[tuple[int, int]]:
    """Settlement positions of the checker: road ends and every small kind."""

    marked = {cell for kind, cell, _ in world.places.values() if kind in SMALL_KINDS}
    for _, _, path in world.road_segments:
        marked.add(path[0])
        marked.add(path[-1])
    return marked


def gap_report(world: World) -> list[dict]:
    """Every road gap over the maximum whose cells all lie in the region."""

    marked = marked_cells(world)
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
            if not all(world.in_completed(cell) for cell in gap):
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
    for place_id, (place_kind, place_cell, _) in world.places.items():
        if place_kind not in SETTLEMENT_KINDS:
            continue
        distance = math.hypot(cell[0] - place_cell[0], cell[1] - place_cell[1])
        if kind == "village":
            if place_kind in (*NATIONAL_KINDS, "village") and distance < VILLAGE_KM:
                return False, f"{distance:.1f} km from {place_id} ({place_kind})"
            if place_kind == "hamlet" and distance < HAMLET_KM:
                return False, f"{distance:.1f} km from {place_id} (hamlet)"
        else:
            if place_kind in SETTLEMENT_KINDS and distance < HAMLET_KM:
                return False, f"{distance:.1f} km from {place_id} ({place_kind})"
    return True, ""


def neighbour_open(world: World, cell: tuple[int, int]) -> bool:
    """Whether one walkable, unoccupied neighbour exists for a gate.

    A single-cell map with no road contact takes its only gate from a walkable
    neighbour; the generator refuses the site with `no_gate` when none is open.
    """

    return any(
        world.walkable((cell[0] + dx, cell[1] + dy))
        and (cell[0] + dx, cell[1] + dy) not in world.occupied
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        if dx or dy
    )


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
        return False, "outside the scope"
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
        if not on and not neighbour_open(world, cell):
            return False, "no walkable neighbour for a gate"
    ok, reason = spacing_ok(world, cell, kind)
    if not ok:
        return False, reason
    return True, ""


# ------------------------------------------------------------ proposals


def gap_slices(world: World) -> list[tuple[dict, list[tuple[int, int]], list[float]]]:
    """Each reported gap with its cells and their cumulative road kilometres."""

    rows = []
    for gap in gap_report(world):
        for first, second, path in world.road_segments:
            if f"{first} -- {second}" != gap["road"]:
                continue
            slice_ = path[gap["from_index"] : gap["to_index"] + 1]
            cumulative = [0.0]
            for a, b in zip(slice_, slice_[1:]):
                cumulative.append(cumulative[-1] + step_km(a, b))
            rows.append((gap, slice_, cumulative))
            break
    return rows


def village_candidates(world: World, limit: int) -> list[dict]:
    """Rank village sites: gap coverage first, then off-trunk sites."""

    roads = road_cells(world)
    inner = trunk_inner_cells(world)
    rows = []
    for gap, slice_, cumulative in gap_slices(world):
        total = cumulative[-1]
        for index, cell in enumerate(slice_):
            if cell not in inner or cell not in roads:
                continue
            ok, _ = eligible(
                world, cell, "village", on_road=True, roads=roads, inner=inner
            )
            if not ok:
                continue
            rows.append(
                {
                    "cell": cell,
                    "road": gap["road"],
                    "km": round(cumulative[index], 1),
                    "longest_remaining_km": round(
                        max(cumulative[index], total - cumulative[index]), 1
                    ),
                    "relief": world.relief(cell),
                    "water": world.water_distance(cell),
                }
            )
    rows.sort(
        key=lambda row: (
            row["longest_remaining_km"],
            row["relief"],
            row["water"] if row["water"] is not None else 99,
        )
    )
    return rows[:limit]


def off_trunk_villages(
    world: World,
    limit: int,
    step: int = 5,
    max_node_km: float = 68.0,
    water_limit: int = 6,
) -> list[dict]:
    """Village sites 20 to 60 km from a road whose spur can reach a node.

    A village receives one spur from the nearest walking-cost node, so a site
    further than the road-gap maximum from every town or village would leave a
    gap the checker rejects.
    """

    roads = road_cells(world)
    nodes = [
        (place_id, place_cell)
        for place_id, (place_kind, place_cell, _) in world.places.items()
        if place_kind in SETTLEMENT_KINDS
    ]
    rows = []
    x_min, y_min, x_max, y_max = all_region_bounds(world)
    for x in range(x_min, x_max + 1, step):
        for y in range(y_min, y_max + 1, step):
            cell = (x, y)
            if not world.in_scope(cell):
                continue
            ok, _ = eligible(world, cell, "village", on_road=False, roads=roads)
            if not ok:
                continue
            trunk = world.trunk_distance(cell)
            if not 20.0 <= trunk <= 60.0:
                continue
            node_id, node_cell = min(
                nodes,
                key=lambda row: math.hypot(
                    cell[0] - row[1][0], cell[1] - row[1][1]
                ),
            )
            node_km = math.hypot(cell[0] - node_cell[0], cell[1] - node_cell[1])
            if node_km > max_node_km:
                continue
            water = (
                world.water_distance(cell, water_limit) if water_limit > 0 else None
            )
            if water_limit > 0 and water is None:
                continue
            rows.append(
                {
                    "cell": cell,
                    "road": "off-trunk",
                    "km": None,
                    "longest_remaining_km": None,
                    "relief": world.relief(cell),
                    "water": water,
                    "trunk_km": round(trunk, 1),
                    "node": node_id,
                    "node_km": round(node_km, 1),
                }
            )
    rows.sort(key=lambda row: (row["water"] or 99, -row["relief"], row["node_km"]))
    return rows[:limit]


def hamlet_candidates(world: World, limit: int) -> list[dict]:
    """Hamlet cells on the inner cells of every gap over 75 km."""

    roads = road_cells(world)
    inner = inner_cells(world)
    rows = []
    for gap, slice_, cumulative in gap_slices(world):
        for index, cell in enumerate(slice_):
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
                    "road": gap["road"],
                    "km": round(cumulative[index], 1),
                    "relief": world.relief(cell),
                    "water": world.water_distance(cell),
                }
            )
    rows.sort(key=lambda row: (row["relief"], row["water"] or 99))
    return rows[:limit]


def off_road_hamlets(world: World, limit: int, step: int = 5) -> list[dict]:
    """Hamlet sites with no road, 15 to 30 km from a village or town."""

    roads = road_cells(world)
    anchors = [
        (place_id, place_cell)
        for place_id, (place_kind, place_cell, _) in world.places.items()
        if place_kind in (*NATIONAL_KINDS, "village")
    ]
    rows = []
    x_min, y_min, x_max, y_max = all_region_bounds(world)
    for x in range(x_min, x_max + 1, step):
        for y in range(y_min, y_max + 1, step):
            cell = (x, y)
            if not world.in_scope(cell):
                continue
            ok, _ = eligible(world, cell, "hamlet", on_road=False, roads=roads)
            if not ok:
                continue
            nearest_id, nearest = min(
                anchors,
                key=lambda row: math.hypot(cell[0] - row[1][0], cell[1] - row[1][1]),
                default=("", (0, 0)),
            )
            distance = math.hypot(cell[0] - nearest[0], cell[1] - nearest[1])
            if not 15.0 <= distance <= 30.0:
                continue
            water = world.water_distance(cell, 6)
            rows.append(
                {
                    "cell": cell,
                    "road": "off-road",
                    "near": nearest_id,
                    "near_km": round(distance, 1),
                    "relief": world.relief(cell),
                    "water": water,
                }
            )
    rows.sort(key=lambda row: (row["relief"], row["water"] or 99))
    return rows[:limit]


def all_region_bounds(world: World, margin: int = 45) -> tuple[int, int, int, int]:
    """A scan window around everything the region already holds.

    The window is the road cells and the settlement cells, padded by ``margin``
    cells; every candidate is still checked against the real region predicate,
    so the window only bounds the scan.
    """

    cells = [
        cell
        for _, _, path in world.road_segments
        for cell in path
        if world.in_region(cell)
    ]
    cells.extend(
        cell
        for _, cell, _ in world.places.values()
        if world.in_region(cell)
    )
    x_min = min(cell[0] for cell in cells) - margin
    y_min = min(cell[1] for cell in cells) - margin
    x_max = max(cell[0] for cell in cells) + margin
    y_max = max(cell[1] for cell in cells) + margin
    limit = world.definition.frame_cells - 1
    return (max(x_min, 0), max(y_min, 0), min(x_max, limit), min(y_max, limit))


# --------------------------------------------------------------- commands


def command_cover(world: World, villages: int, hamlets: int) -> int:
    """The fewest on-road positions that cut every in-region gap to 75 km.

    One gap is repaired at a time: the longest one gets a stop at the first
    even division of its length, and the loop repeats on what is left. Every
    chosen cell is then given a tier — up to ``--villages`` of them become
    villages, the rest hamlets — and the run stops at ``--hamlets`` positions
    in total.
    """

    roads = road_cells(world)
    inner = inner_cells(world)
    road_index: dict[tuple[int, int], list[tuple[int, int]]] = {}
    cumulative: list[list[float]] = []
    outside: list[list[int]] = []
    positions: list[set[int]] = []
    marked = marked_cells(world)
    for order, (_, _, path) in enumerate(world.road_segments):
        steps = [0.0]
        for a, b in zip(path, path[1:]):
            steps.append(steps[-1] + step_km(a, b))
        cumulative.append(steps)
        row = [0]
        for cell in path:
            row.append(row[-1] + (0 if world.in_completed(cell) else 1))
        outside.append(row)
        positions.append({index for index, cell in enumerate(path) if cell in marked})
        for index, cell in enumerate(path):
            road_index.setdefault(cell, []).append((order, index))

    def excess(start: int, end: int, order: int) -> float:
        """Kilometres by which one gap exceeds the maximum; zero when it does not."""

        if end <= start:
            return 0.0
        if outside[order][end + 1] - outside[order][start]:
            return 0.0
        length = cumulative[order][end] - cumulative[order][start]
        return max(0.0, length - ROAD_GAP_KM)

    def gaps() -> list[tuple[int, int, int, float]]:
        rows = []
        for order in range(len(world.road_segments)):
            ordered = sorted(positions[order])
            for start, end in zip(ordered, ordered[1:]):
                value = excess(start, end, order)
                if value <= 0:
                    continue
                rows.append((value, order, start, end))
        rows.sort(reverse=True)
        return rows

    settlement_cells = [
        (place_cell, place_kind)
        for place_kind, place_cell, _ in world.places.values()
        if place_kind in SETTLEMENT_KINDS
    ]
    chosen: list[tuple[int, int]] = []

    def far_enough(cell: tuple[int, int], kind: str) -> bool:
        for other, other_kind in settlement_cells:
            if other == cell:
                continue
            distance = math.hypot(cell[0] - other[0], cell[1] - other[1])
            minimum = HAMLET_KM
            if kind == "village" and other_kind in (*NATIONAL_KINDS, "village"):
                minimum = VILLAGE_KM
            if distance < minimum:
                return False
        return True

    def usable(cell: tuple[int, int]) -> bool:
        return (
            cell in roads
            and cell in inner
            and world.in_scope(cell)
            and world.walkable(cell)
            and world.habitat_clear(cell)
            and cell not in world.occupied
        )

    def place(cell: tuple[int, int]) -> None:
        chosen.append(cell)
        settlement_cells.append((cell, "hamlet"))
        for order, index in road_index.get(cell, ()):
            positions[order].add(index)

    def repair() -> bool:
        """One stop on the longest gap; False when no gap can be repaired."""

        for _, order, start, end in gaps():
            if start + 1 >= end:
                continue
            path = world.road_segments[order][2]
            length = cumulative[order][end] - cumulative[order][start]
            divisions = math.ceil(length / ROAD_GAP_KM)
            target = cumulative[order][start] + length / divisions
            options = []
            for index in range(start + 1, end):
                cell = path[index]
                distance = abs(cumulative[order][index] - target)
                if distance > ROAD_GAP_KM * 0.4:
                    continue
                if not usable(cell) or not far_enough(cell, "hamlet"):
                    continue
                water = world.water_distance(cell)
                score = distance + (0.0 if water is not None and water <= 3 else 12.0)
                options.append(
                    (
                        round(score, 3),
                        -len(road_index[cell]),
                        -world.relief(cell),
                        round(distance, 3),
                        cell,
                    )
                )
            if not options:
                continue
            options.sort()
            place(options[0][-1])
            return True
        return False

    limit = max(hamlets, villages)
    while len(chosen) < limit and repair():
        pass

    stops = list(chosen)
    tiers: dict[tuple[int, int], str] = {}
    picked: list[tuple[int, int]] = []
    ranked = sorted(
        stops,
        key=lambda cell: (
            -len(road_index[cell]),
            -world.relief(cell),
            world.water_distance(cell) if world.water_distance(cell) is not None else 99,
            cell,
        ),
    )
    for cell in ranked:
        if len(picked) >= villages:
            break
        if not far_enough(cell, "village"):
            continue
        picked.append(cell)
        tiers[cell] = "village"
        settlement_cells.append((cell, "village"))
    for cell in stops:
        tiers.setdefault(cell, "hamlet")
    print(
        json.dumps(
            [{"cell": list(cell), "kind": tiers[cell]} for cell in stops],
            indent=0,
        )
    )
    for cell in stops:
        print(
            f"{tiers[cell]:<8} {cell} roads={len(road_index[cell])} "
            f"relief={world.relief(cell)} water={world.water_distance(cell)} "
            f"band={world.band(cell)}",
            file=sys.stderr,
        )
    remaining = sum(value for value, _, _, _ in gaps())
    print(
        f"{len(stops)} cells "
        f"({sum(1 for cell in stops if tiers[cell] == 'village')} villages); "
        f"{remaining:.0f} km of over-length left",
        file=sys.stderr,
    )
    for value, order, start, end in gaps():
        first, second, path = world.road_segments[order]
        print(
            f"uncovered {first} -- {second} {path[start]}..{path[end]} "
            f"{cumulative[order][end] - cumulative[order][start]:.1f} km",
            file=sys.stderr,
        )
    return 0


def command_spurs(world: World) -> int:
    """Every spur: its owner, its ends, its road kilometres, and its region."""

    owners = world.network.spur_owners
    if not owners:
        print("no spur in the artifact")
        return 0
    for first, second, path in world.road_segments:
        owner = owners.get((first, second))
        if owner is None:
            continue
        length = sum(step_km(a, b) for a, b in zip(path, path[1:]))
        inside = all(world.in_completed(cell) for cell in path)
        cells = len(path)
        print(
            f"{owner:<30} {first} -- {second:<28} {cells:>4} cells "
            f"{length:6.1f} km {'in region' if inside else 'leaves the region'}"
        )
    return 0


def command_survey(world: World) -> int:
    """One row per road: length in the region, settlements on it, longest gap."""

    marked = marked_cells(world)
    names = {
        cell: key
        for key, (kind, cell, _) in world.places.items()
        if kind in SETTLEMENT_KINDS
    }
    print(
        f"{'road':<52} {'cells':>6} {'km':>8} {'max_gap':>8} {'>75':>4}  settlements"
    )
    for first, second, path in world.road_segments:
        in_region = [cell for cell in path if world.in_region(cell)]
        if not in_region:
            continue
        positions = sorted(
            {0, len(path) - 1}
            | {index for index, cell in enumerate(path) if cell in marked}
        )
        longest = 0.0
        bad = 0
        for start, end in zip(positions, positions[1:]):
            gap = path[start : end + 1]
            length = sum(step_km(a, b) for a, b in zip(gap, gap[1:]))
            if not all(world.in_completed(cell) for cell in gap):
                continue
            longest = max(longest, length)
            bad += 1 if length > ROAD_GAP_KM else 0
        on_road = sorted((names[cell], cell) for cell in path if cell in names)
        print(
            f"{first + ' -- ' + second:<52} {len(in_region):>6} "
            f"{len(in_region) - 1:>8} {longest:>8.1f} {bad:>4}  "
            + ", ".join(f"{name}{cell}" for name, cell in on_road)
        )
    print()
    print(
        f"region bounds {all_region_bounds(world)}; "
        f"{len(gap_report(world))} gaps over {ROAD_GAP_KM:.0f} km"
    )
    return 0


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


def command_settlements(world: World) -> int:
    for place_id, (kind, cell, name) in world.places.items():
        if kind not in SETTLEMENT_KINDS:
            continue
        flags = []
        if world.in_region(cell):
            flags.append("scope")
        elif world.region(cell) in PRIOR_REGIONS:
            flags.append(world.region(cell))
        print(f"{place_id:<32} {kind:<10} {name:<8} {cell} {' '.join(flags)}")
    return 0


def command_villages(world: World, limit: int) -> int:
    rows = village_candidates(world, limit)
    for row in rows:
        print(json.dumps(row), file=sys.stderr)
    print(json.dumps([{"cell": row["cell"]} for row in rows], indent=0))
    return 0


def command_off_trunk(
    world: World, limit: int, step: int = 5, water: int = 6
) -> int:
    rows = off_trunk_villages(world, limit, step=step, water_limit=water)
    for row in rows:
        print(json.dumps(row), file=sys.stderr)
    print(json.dumps([{"cell": row["cell"]} for row in rows], indent=0))
    return 0


def command_hamlets(world: World, limit: int, step: int = 5, water: int = 6) -> int:
    rows = hamlet_candidates(world, limit)
    for row in rows:
        print(json.dumps(row), file=sys.stderr)
    print(json.dumps([{"cell": row["cell"]} for row in rows], indent=0))
    return 0


def command_off_road(world: World, limit: int, step: int = 5, water: int = 6) -> int:
    rows = off_road_hamlets(world, limit, step=step)
    for row in rows:
        print(json.dumps(row), file=sys.stderr)
    print(json.dumps([{"cell": row["cell"]} for row in rows], indent=0))
    return 0


def command_check(world: World, cell_text: str, kind: str) -> int:
    x, y = (int(part) for part in cell_text.split(","))
    cell = (x, y)
    ok, reason = eligible(world, cell, kind)
    print(
        json.dumps(
            {
                "cell": [x, y],
                "kind": kind,
                "ok": ok,
                "reason": reason,
                "band": world.band(cell),
                "relief": world.relief(cell),
                "water": world.water_distance(cell),
                "trunk": round(world.trunk_distance(cell), 1),
                "region": region_for_coordinates(world.definition, x, y),
            }
        )
    )
    return 0 if ok else 1


def command_plan(world: World, path: Path) -> int:
    """Validate a proposed plan and report the gaps it leaves."""

    plan = json.loads(path.read_text(encoding="utf-8"))
    roads = road_cells(world)
    all_inner = inner_cells(world)
    trunk_inner = trunk_inner_cells(world)
    proposed: dict[tuple[int, int], dict] = {}
    failed = False
    for row in plan:
        cell = tuple(row["cell"])
        kind = row["kind"]
        on_road = cell in roads
        inner = trunk_inner if kind == "village" else all_inner
        ok, reason = eligible(
            world, cell, kind, on_road=on_road, roads=roads, inner=inner
        )
        if on_road and cell not in inner:
            ok, reason = False, "a road end cell"
        print(
            f"{'ok ' if ok else 'BAD'} {row['id']:<34} {kind:<8} {cell} "
            f"{'road' if on_road else 'off-road'} {reason}"
        )
        failed |= not ok
        proposed[cell] = row
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
    marked = marked_cells(world) | set(proposed)
    for first, second, path_cells in world.road_segments:
        positions = sorted(
            {0, len(path_cells) - 1}
            | {index for index, cell in enumerate(path_cells) if cell in marked}
        )
        for start, end in zip(positions, positions[1:]):
            gap = path_cells[start : end + 1]
            length = sum(step_km(a, b) for a, b in zip(gap, gap[1:]))
            inside = all(world.in_completed(cell) for cell in gap)
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
        "command",
        choices=(
            "cover",
            "survey",
            "spurs",
            "gaps",
            "road",
            "settlements",
            "villages",
            "off-trunk",
            "hamlets",
            "off-road",
            "check",
            "plan",
        ),
    )
    parser.add_argument("argument", nargs="?")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--villages", type=int, default=0)
    parser.add_argument("--hamlets", type=int, default=200)
    parser.add_argument("--step", type=int, default=5, help="scan stride in cells")
    parser.add_argument(
        "--water",
        type=int,
        default=6,
        help="cells to the nearest waterway a candidate must have; 0 disables",
    )
    parser.add_argument(
        "--roads",
        type=Path,
        default=None,
        help="an explicit road artifact instead of the checkout's own",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="the checkout to read instead of this script's own",
    )
    parser.add_argument(
        "--without",
        type=Path,
        default=None,
        help="a plan file whose location ids are removed before the run",
    )
    parser.add_argument(
        "--foreign",
        action="store_true",
        help="also accept the earlier completed area of the boundary rule",
    )
    args = parser.parse_args(argv)
    world = World(
        args.roads, root=args.root, without=args.without, foreign=args.foreign
    )
    if args.command == "cover":
        return command_cover(world, args.villages, args.hamlets)
    if args.command == "spurs":
        return command_spurs(world)
    if args.command == "survey":
        return command_survey(world)
    if args.command == "gaps":
        return command_gaps(world)
    if args.command == "road":
        return command_road(world, args.argument)
    if args.command == "settlements":
        return command_settlements(world)
    if args.command == "villages":
        return command_villages(world, args.limit)
    if args.command == "off-trunk":
        return command_off_trunk(world, args.limit, step=args.step, water=args.water)
    if args.command == "hamlets":
        return command_hamlets(world, args.limit, step=args.step, water=args.water)
    if args.command == "off-road":
        return command_off_road(world, args.limit, step=args.step, water=args.water)
    if args.command == "plan":
        return command_plan(world, Path(args.argument))
    if args.command == "check":
        parts = (args.argument or "").split(",")
        return command_check(world, ",".join(parts[:2]), parts[2] if len(parts) > 2 else "hamlet")
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
