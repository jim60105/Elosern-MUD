"""Deterministic street-graph generation from a site, a budget and a catalogue.

The generator is a pure function of its explicit inputs: the same map identity,
terrain, roster, budget, catalogue and forced gates always produce the same
document bytes. Randomness comes from one ``random.Random`` seeded by the map
identity, and only ``random()`` is drawn, whose sequence is stable for a given
seed across interpreter versions.

The output is the coarse fit only. Bridges, district shape and appearance are
finished by a person in the map editor, and the prose pass fills ``key`` and
``desc`` (``settlement-rework-and-prose``). The generator never overwrites an
existing settlement: that refusal lives in the command line, next to the size
budget and the site analysis it reads.
"""

from __future__ import annotations

import hashlib
import itertools
import math
import random
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from elosern_map_core.codec import document_from_data
from elosern_map_core.diagnostics import AuthoringError

from tools.settlement_synthesis.budget import SizeBudget
from tools.settlement_synthesis.fit_lint import (
    CROSSING_WORDS,
    lint_settlement,
    words,
)
from tools.settlement_synthesis.geometry import (
    Cell,
    OCTANT_VECTORS,
    OCTANTS,
    OPPOSITE,
    cell_of,
    point_to_cell_distance,
)
from tools.settlement_synthesis.roles import RoleEntry
from tools.settlement_synthesis.site import (
    PointFeature,
    SettlementRef,
    SiteContext,
    WaterContact,
)
from tools.settlement_synthesis.terrain_view import GridTerrain

SETTLEMENT_CLASSES = ("human_capital", "human_town", "port", "beast_capital", "beast_town")
MORPHOLOGIES = ("tribal_ring", "harbour_crescent", "river_crossing", "waterside_linear", "hill_terraces", "crossroads")
OCTANT_WORDS = {"n": "north", "ne": "northeast", "e": "east", "se": "southeast",
                "s": "south", "sw": "southwest", "w": "west", "nw": "northwest"}
OCTANT_ZH = {"n": "北", "ne": "東北", "e": "東", "se": "東南", "s": "南", "sw": "西南", "w": "西", "nw": "西北"}
FALLBACK_BEARINGS = ("s", "n", "e", "w", "se", "sw", "ne", "nw")

#: The eight 4-neighbour offsets, in the design's BFS order.
_STEPS = ((1, 0), (0, 1), (-1, 0), (0, -1))

#: The eight 8-neighbour offsets, ordered south rows first then west to east.
_KING_STEPS = tuple(
    (dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dx, dy) != (0, 0)
)


@dataclass(frozen=True)
class GenerationConfig:
    beast_nations: frozenset[str] = frozenset({"valhalla"})
    water_edge_max_m: int = 600          # must equal fit_lint.LintConfig().water_edge_max_m
    margin_m: int = 100
    max_degree: int = 6

    def __post_init__(self) -> None:
        if not 1 <= self.max_degree <= 6:
            raise ValueError(
                "max_degree must be between 1 and 6: the settlement schema allows "
                "at most six roads at one node"
            )


@dataclass(frozen=True)
class GenerationInput:
    map_id: str
    location: SettlementRef
    site: SiteContext
    budget: SizeBudget
    terrain: GridTerrain
    blocked: frozenset[Cell]             # never part of this footprint, never an approach cell
    catalogue: tuple[RoleEntry, ...]
    forced_gates: tuple[str, ...] = ()   # octants, highest priority first
    config: GenerationConfig = GenerationConfig()


@dataclass(frozen=True)
class Slot:
    slot_id: str
    role: str          # "anchor" | "gate" | "crossing" | "approach" | "filler" | catalogue slot_id
    key_zh: str
    rel_m: tuple[float, float]   # metres relative to the location cell centre (east, north)


@dataclass(frozen=True)
class GenerationResult:
    map_id: str
    settlement_class: str
    morphology: str
    footprint: frozenset[Cell]
    slots: tuple[Slot, ...]      # document node order
    data: Mapping[str, Any]      # complete settlement document data (D8)
    warnings: tuple[str, ...]    # sorted


class GenerationError(ValueError):
    """A settlement cannot be generated from these inputs."""


def seed_for(map_id: str) -> int:
    return int.from_bytes(hashlib.sha256(f"settlement:{map_id}:v1".encode("utf-8")).digest()[:8], "big")


# -- small geometry helpers -------------------------------------------------------


def _unit(vec: tuple[float, float]) -> tuple[float, float] | None:
    length = math.hypot(vec[0], vec[1])
    if length == 0:
        return None
    return (vec[0] / length, vec[1] / length)


def _octant_unit(octant: str) -> tuple[float, float]:
    return _unit(OCTANT_VECTORS[octant]) or (1.0, 0.0)


def _cheb(a: Cell, b: Cell) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _midpoint(cells: frozenset[Cell] | set[Cell]) -> Cell:
    return (
        (min(cell[0] for cell in cells) + max(cell[0] for cell in cells)) // 2,
        (min(cell[1] for cell in cells) + max(cell[1] for cell in cells)) // 2,
    )


def _window_cells(terrain: GridTerrain) -> list[Cell]:
    min_x, min_y, max_x, max_y = terrain.window
    return [
        (x, y) for y in range(min_y, max_y + 1) for x in range(min_x, max_x + 1)
    ]


def _cell_of_rel(location_cell: Cell, point: tuple[float, float]) -> Cell:
    return cell_of(
        (
            1000 * location_cell[0] + 500 + point[0],
            1000 * location_cell[1] + 500 + point[1],
        )
    )


def _world_of_rel(location_cell: Cell, point: tuple[float, float]) -> tuple[float, float]:
    return (
        1000 * location_cell[0] + 500 + point[0],
        1000 * location_cell[1] + 500 + point[1],
    )


def _rel_of_cell(location_cell: Cell, cell: Cell) -> tuple[float, float]:
    return (
        float((cell[0] - location_cell[0]) * 1000),
        float((cell[1] - location_cell[1]) * 1000),
    )


def _neighbours8(cell: Cell) -> tuple[Cell, ...]:
    return tuple((cell[0] + dx, cell[1] + dy) for dx, dy in _KING_STEPS)


# -- class, reach and morphology (D3) ---------------------------------------------


def _settlement_class(inp: GenerationInput) -> str:
    location = inp.location
    if location.nation in inp.config.beast_nations:
        return "beast_capital" if location.kind == "capital" else "beast_town"
    if location.kind == "capital":
        return "human_capital"
    if location.kind == "port":
        return "port"
    if location.kind in ("city", "town"):
        return "human_town"
    raise GenerationError(f"{inp.map_id}: kind {location.kind!r} has no settlement class")


def _morphology(inp: GenerationInput, reach: int) -> tuple[str, Any]:
    centre = inp.location.cell
    river = next(
        (
            contact
            for contact in inp.site.rivers
            if _cheb(centre, contact.nearest_cell) <= reach
        ),
        None,
    )
    sea = inp.site.sea
    if sea is not None and _cheb(centre, sea.nearest_cell) > reach:
        sea = None
    ford = None
    if river is not None:
        ford = next(
            (
                feature
                for feature in inp.site.fords
                if feature.feature_id == river.name
                and _cheb(centre, feature.cell) <= reach
            ),
            None,
        )

    settlement_class = _settlement_class(inp)
    if settlement_class in ("beast_capital", "beast_town"):
        return "tribal_ring", river
    if settlement_class == "port":
        if sea is not None:
            return "harbour_crescent", sea
        if river is not None:
            return "waterside_linear", river
        raise GenerationError(
            f"{inp.map_id}: water_gap: no sea or river within {reach} cells"
        )
    if river is not None and ford is not None:
        return "river_crossing", ford
    if river is not None:
        return "waterside_linear", river
    if inp.site.relief >= 2:
        return "hill_terraces", None
    return "crossroads", None


def settlement_class_of(inp: GenerationInput) -> str:
    """The settlement class the generator derives from one input."""

    return _settlement_class(inp)


def morphology_of(inp: GenerationInput) -> str:
    """The morphology the generator derives from one input and its reach."""

    reach = math.ceil(math.sqrt(inp.budget.footprint_cells) / 2) + 1
    return _morphology(inp, reach)[0]


def _water_vector(morphology: str, target: Any) -> tuple[float, float] | None:
    """The unit vector toward the water a morphology leans on, if it has one."""

    if target is None:
        return None
    direction = getattr(target, "bearing", None)
    if direction is None:
        return None
    return _octant_unit(direction)


def _downstream(inp: GenerationInput, target: Any) -> str | None:
    """The downstream bearing of the river a target belongs to, if any."""

    if isinstance(target, PointFeature):
        name: str | None = target.feature_id
    elif isinstance(target, WaterContact) and target.kind == "river":
        name = target.name
    else:
        return None
    for contact in inp.site.rivers:
        if contact.name == name:
            return contact.downstream
    return None


# -- footprint growth (D4) --------------------------------------------------------


def _body_cells(terrain: GridTerrain, target: Any) -> frozenset[Cell]:
    if isinstance(target, WaterContact) and target.kind == "river":
        return terrain.waterway_cells.get(target.name or "", frozenset())
    if isinstance(target, WaterContact) and target.kind == "sea":
        return frozenset(cell for cell in _window_cells(terrain) if terrain.is_sea(cell))
    return frozenset()


def _reach_target(inp: GenerationInput, target: Any, reach: int) -> Cell | None:
    """The walkable, unblocked cell nearest the location that touches the water."""

    if isinstance(target, PointFeature):
        return target.cell
    body = _body_cells(inp.terrain, target)
    if not body:
        return None
    centre = inp.location.cell
    best: tuple[tuple[float, int, int], Cell] | None = None
    for y in range(centre[1] - reach, centre[1] + reach + 1):
        for x in range(centre[0] - reach, centre[0] + reach + 1):
            cell = (x, y)
            if cell in inp.blocked or not inp.terrain.walkable(cell):
                continue
            if not any(neighbour in body for neighbour in _neighbours8(cell)):
                continue
            key = (math.hypot(x - centre[0], y - centre[1]), y, x)
            if best is None or key < best[0]:
                best = (key, cell)
    return None if best is None else best[1]


def _path_to(inp: GenerationInput, start: Cell, goal: Cell | None) -> list[Cell] | None:
    """The 4-connected walkable path from start to goal, or None."""

    if goal is None:
        return None
    if start == goal:
        return [start]
    parent: dict[Cell, Cell | None] = {start: None}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for dx, dy in _STEPS:
            neighbour = (cell[0] + dx, cell[1] + dy)
            if neighbour in parent:
                continue
            if neighbour in inp.blocked or not inp.terrain.walkable(neighbour):
                continue
            parent[neighbour] = cell
            if neighbour == goal:
                path = []
                cursor: Cell | None = neighbour
                while cursor is not None:
                    path.append(cursor)
                    cursor = parent[cursor]
                path.reverse()
                return path
            queue.append(neighbour)
    return None


def _grow_footprint(
    inp: GenerationInput, morphology: str, target: Any, reach: int
) -> tuple[frozenset[Cell], bool, bool, list[str]]:
    centre = inp.location.cell
    if centre in inp.blocked or not inp.terrain.walkable(centre):
        raise GenerationError(f"{inp.map_id}: location cell not walkable")
    budget_cells = inp.budget.footprint_cells
    footprint: set[Cell] = {centre}
    warnings: list[str] = []

    water_target = target
    if water_target is not None:
        goal = _reach_target(inp, water_target, reach)
        path = _path_to(inp, centre, goal)
        if path is None:
            water_target = None
            if _settlement_class(inp) == "port":
                raise GenerationError(
                    f"{inp.map_id}: water_gap: no sea or river within {reach} cells"
                )
        else:
            footprint.update(path)
            if len(footprint) > budget_cells:
                warnings.append(f"footprint_reach_overflow:{len(footprint) - budget_cells}")

    if water_target is not None:
        water_vec = _water_vector(morphology, water_target)
        growth = (
            (centre[0] + 0.5 * water_vec[0], centre[1] + 0.5 * water_vec[1])
            if water_vec is not None
            else (float(centre[0]), float(centre[1]))
        )
    else:
        growth = (float(centre[0]), float(centre[1]))

    while len(footprint) < budget_cells:
        candidates = []
        seen = set()
        for cell in sorted(footprint, key=lambda item: (item[1], item[0])):
            for dx, dy in _STEPS:
                neighbour = (cell[0] + dx, cell[1] + dy)
                if neighbour in seen:
                    continue
                seen.add(neighbour)
                if neighbour in footprint:
                    continue
                if neighbour in inp.blocked or not inp.terrain.walkable(neighbour):
                    continue
                candidates.append(neighbour)
        if not candidates:
            raise GenerationError(f"{inp.map_id}: footprint_short")
        best = min(
            candidates,
            key=lambda cell: _growth_score(cell, footprint, centre, growth),
        )
        footprint.add(best)

    midpoint = _midpoint(footprint)
    if midpoint not in footprint:
        raise GenerationError(f"{inp.map_id}: anchor_outside_footprint")
    if midpoint != centre:
        warnings.append("footprint_location_offset")

    water_contact = any(
        inp.terrain.is_water(neighbour)
        for cell in footprint
        for neighbour in _neighbours8(cell)
    )
    if isinstance(target, PointFeature) and target.cell in footprint:
        water_contact = True

    river_name: str | None = None
    if isinstance(target, PointFeature):
        river_name = target.feature_id
    elif isinstance(target, WaterContact) and target.kind == "river":
        river_name = target.name
    river_cells = (
        inp.terrain.waterway_cells.get(river_name, frozenset())
        if river_name is not None
        else frozenset()
    )
    river_contact = any(
        neighbour in river_cells
        for cell in footprint
        for neighbour in _neighbours8(cell)
    )

    return frozenset(footprint), water_contact, river_contact, warnings


def _growth_score(
    cell: Cell,
    footprint: set[Cell],
    centre: Cell,
    growth: tuple[float, float],
) -> tuple[int, float, int, int]:
    midpoint = _midpoint(footprint | {cell})
    balanced = 0 if midpoint == centre else 1
    distance = (cell[0] - growth[0]) ** 2 + (cell[1] - growth[1]) ** 2
    return (balanced, distance, cell[1], cell[0])


# -- frame, envelope and candidates (D5) ------------------------------------------


@dataclass(frozen=True)
class _Frame:
    location_cell: Cell
    footprint: frozenset[Cell]
    terrain: GridTerrain
    radius: int
    spacing: float
    centre: tuple[float, float]
    major: tuple[float, float]
    minor: tuple[float, float]
    semi_major: float
    semi_minor: float

    def in_envelope(self, point: tuple[float, float]) -> bool:
        dx = point[0] - self.centre[0]
        dy = point[1] - self.centre[1]
        along_major = (dx * self.major[0] + dy * self.major[1]) / self.semi_major
        along_minor = (dx * self.minor[0] + dy * self.minor[1]) / self.semi_minor
        return along_major**2 + along_minor**2 <= 1.0

    def in_town(self, point: tuple[float, float]) -> bool:
        cell = _cell_of_rel(self.location_cell, point)
        return cell in self.footprint and not self.terrain.is_water(cell)

    def admissible(self, point: tuple[float, float]) -> bool:
        return self.in_town(point) and self.in_envelope(point)


def _frame(
    inp: GenerationInput,
    morphology: str,
    water_vec: tuple[float, float] | None,
    uphill_vec: tuple[float, float] | None,
    footprint: frozenset[Cell],
) -> _Frame:
    radius = inp.budget.envelope_radius_m
    if (
        morphology in ("river_crossing", "waterside_linear", "harbour_crescent")
        and water_vec is not None
    ):
        centre = (0.25 * radius * water_vec[0], 0.25 * radius * water_vec[1])
        major = (-water_vec[1], water_vec[0])
        minor = water_vec
        semi_major = radius * math.sqrt(2)
        semi_minor = radius / math.sqrt(2)
    elif morphology == "hill_terraces" and uphill_vec is not None:
        centre = (0.0, 0.0)
        major = (-uphill_vec[1], uphill_vec[0])
        minor = uphill_vec
        semi_major = radius * math.sqrt(2)
        semi_minor = radius / math.sqrt(2)
    else:
        centre = (0.0, 0.0)
        major = (1.0, 0.0)
        minor = (0.0, 1.0)
        semi_major = float(radius)
        semi_minor = float(radius)
    spacing = min(
        600.0,
        max(
            60.0,
            round(
                0.8
                * radius
                * math.sqrt(math.pi / max(inp.budget.node_count, 1))
            ),
        ),
    )
    return _Frame(
        location_cell=inp.location.cell,
        footprint=footprint,
        terrain=inp.terrain,
        radius=radius,
        spacing=float(spacing),
        centre=centre,
        major=major,
        minor=minor,
        semi_major=semi_major,
        semi_minor=semi_minor,
    )


def _envelope_candidates(
    frame: _Frame, rng: random.Random
) -> list[tuple[float, float]]:
    xs = [cell[0] for cell in frame.footprint]
    ys = [cell[1] for cell in frame.footprint]
    centre_x, centre_y = frame.location_cell
    min_x = (min(xs) - centre_x) * 1000 - 500
    max_x = (max(xs) - centre_x) * 1000 + 500
    min_y = (min(ys) - centre_y) * 1000 - 500
    max_y = (max(ys) - centre_y) * 1000 + 500
    step = frame.spacing / 2
    points: list[tuple[float, float]] = []
    row = 0
    while min_y + row * step <= max_y + 1e-9:
        y = min_y + row * step
        column = 0
        while min_x + column * step <= max_x + 1e-9:
            x = min_x + column * step
            jitter_x = (rng.random() - 0.5) * 0.6 * step
            jitter_y = (rng.random() - 0.5) * 0.6 * step
            point = (x + jitter_x, y + jitter_y)
            if frame.admissible(point):
                points.append(point)
            column += 1
        row += 1
    return points


def _water_candidates(
    inp: GenerationInput, frame: _Frame
) -> list[tuple[float, float]]:
    centre_x, centre_y = frame.location_cell
    points: set[tuple[float, float]] = set()
    for cell in sorted(frame.footprint, key=lambda item: (item[1], item[0])):
        left = (cell[0] - centre_x) * 1000 - 500
        bottom = (cell[1] - centre_y) * 1000 - 500
        for water in _neighbours8(cell):
            if not inp.terrain.is_water(water):
                continue
            water_x = float((water[0] - centre_x) * 1000)
            water_y = float((water[1] - centre_y) * 1000)
            point = (
                min(max(water_x, left + 50), left + 950),
                min(max(water_y, bottom + 50), bottom + 950),
            )
            if not frame.in_town(point):
                continue
            distance = point_to_cell_distance(
                _world_of_rel(frame.location_cell, point), water
            )
            if distance > inp.config.water_edge_max_m:
                continue
            points.add(point)
    return sorted(points, key=lambda point: (point[1], point[0]))


def _spacing_ok(
    point: tuple[float, float], placed: list[tuple[float, float]], minimum: float
) -> bool:
    return all(
        math.hypot(point[0] - other[0], point[1] - other[1]) >= minimum
        for other in placed
    )


def _pick(
    pool: list[tuple[float, float]],
    placed: list[tuple[float, float]],
    minimum: float,
    key,
    *,
    maximise: bool = False,
) -> tuple[float, float] | None:
    valid = [point for point in pool if _spacing_ok(point, placed, minimum)]
    if not valid:
        return None
    return max(valid, key=key) if maximise else min(valid, key=key)


# -- node placement (D6) ----------------------------------------------------------


def _gate_bearings(inp: GenerationInput) -> list[str]:
    ordered: list[str | None] = [
        *inp.forced_gates,
        inp.site.capital_bearing,
        *(feature.bearing for feature in inp.site.neighbours),
        *(feature.bearing for feature in inp.site.fords),
        *FALLBACK_BEARINGS,
    ]
    bearings: list[str] = []
    for bearing in ordered:
        if bearing is None or bearing in bearings:
            continue
        bearings.append(bearing)
    return bearings


def _place_nodes(
    inp: GenerationInput,
    rng: random.Random,
    morphology: str,
    target: Any,
    footprint: frozenset[Cell],
    water_contact: bool,
    river_contact: bool,
    water_vec: tuple[float, float] | None,
    uphill_vec: tuple[float, float] | None,
    downstream: str | None,
) -> tuple[list[Slot], list[str], dict[str, str]]:
    node_count = inp.budget.node_count
    frame = _frame(inp, morphology, water_vec, uphill_vec, footprint)
    envelope = _envelope_candidates(frame, rng)
    water_points = _water_candidates(inp, frame)
    slots: list[Slot] = []
    warnings: list[str] = []
    gate_octants: dict[str, str] = {}

    slots.append(Slot("central_plaza", "anchor", "中央廣場", (0.0, 0.0)))
    if (
        morphology == "river_crossing"
        and isinstance(target, PointFeature)
        and target.cell in footprint
    ):
        slots.append(
            Slot(
                "ford_crossing",
                "crossing",
                "渡口",
                _rel_of_cell(frame.location_cell, target.cell),
            )
        )

    placed = [slot.rel_m for slot in slots]
    midway = _midpoint(footprint)
    used_approaches: set[tuple[Cell, str]] = set()
    gates: list[tuple[str, Slot]] = []
    for bearing in _gate_bearings(inp):
        if len(gates) >= inp.budget.gate_count:
            break
        delta_x, delta_y = OCTANT_VECTORS[bearing]
        approach = midway
        while approach in footprint:
            approach = (approach[0] + delta_x, approach[1] + delta_y)
        if (
            not inp.terrain.walkable(approach)
            or approach in inp.blocked
            or (approach, OPPOSITE[bearing]) in used_approaches
        ):
            continue
        direction = _octant_unit(bearing)
        chosen = None
        step = 25.0
        while step <= 1.5 * frame.radius + 1e-9:
            point = (direction[0] * step, direction[1] * step)
            if frame.in_town(point) and _spacing_ok(
                point, placed, 0.6 * frame.spacing
            ):
                chosen = point
            step += 25.0
        if chosen is None:
            continue
        slot = Slot(
            f"{OCTANT_WORDS[bearing]}_gate",
            "gate",
            f"{OCTANT_ZH[bearing]}門",
            chosen,
        )
        gates.append((bearing, slot))
        gate_octants[slot.slot_id] = bearing
        slots.append(slot)
        placed.append(slot.rel_m)
        used_approaches.add((approach, OPPOSITE[bearing]))

    if len(gates) < inp.budget.gate_count:
        warnings.append(f"gate_shortfall:{inp.budget.gate_count - len(gates)}")
    if not gates:
        raise GenerationError(f"{inp.map_id}: no_gate")

    chain_cap = 1 if node_count < 12 else 2 if node_count < 20 else 3
    chain_budget = max(0, (node_count - len(slots)) // 3)
    for _bearing, gate in gates:
        if chain_budget <= 0:
            break
        gate_x, gate_y = gate.rel_m
        distance = math.hypot(gate_x, gate_y)
        count = min(chain_cap, int(distance // (2 * frame.spacing)), chain_budget)
        if count <= 0:
            continue
        perpendicular = _unit((-gate_y, gate_x)) or (0.0, 1.0)
        for index in range(1, count + 1):
            fraction = index / (count + 1)
            target_x = gate_x * (1 - fraction)
            target_y = gate_y * (1 - fraction)
            offset = (rng.random() - 0.5) * 0.4 * frame.spacing
            target_x += perpendicular[0] * offset
            target_y += perpendicular[1] * offset
            best = None
            best_distance = None
            for point in envelope:
                distance_to_target = math.hypot(point[0] - target_x, point[1] - target_y)
                if distance_to_target > frame.spacing / 2:
                    continue
                if not _spacing_ok(point, placed, 0.6 * frame.spacing):
                    continue
                if best is None or distance_to_target < best_distance:
                    best = point
                    best_distance = distance_to_target
            if best is None:
                continue
            slot = Slot(f"{gate.slot_id}_road_{index}", "approach", "大街", best)
            slots.append(slot)
            placed.append(best)
            envelope.remove(best)
            chain_budget -= 1

    settlement_class = _settlement_class(inp)
    eligible = [
        entry
        for entry in inp.catalogue
        if settlement_class in entry.classes
        and node_count >= entry.min_nodes
        and (entry.requires != "water" or water_contact)
        and (entry.requires != "river" or river_contact)
    ]
    eligible.sort(key=lambda entry: (entry.priority, entry.slot_id))
    ring_count = sum(1 for entry in eligible if entry.placement == "ring")
    theta_zero: float | None = None
    ring_index = 0
    uphill_h: tuple[float, float] | None = None

    for entry in eligible:
        if len(slots) >= node_count:
            break
        point = None
        if entry.placement == "near_anchor":
            point = _pick(
                envelope,
                placed,
                0.6 * frame.spacing,
                lambda item: math.hypot(item[0], item[1]),
            )
            pool = envelope
        elif entry.placement == "high_ground":
            if uphill_h is None:
                if uphill_vec is not None:
                    uphill_h = uphill_vec
                elif water_vec is not None:
                    uphill_h = (-water_vec[0], -water_vec[1])
                else:
                    uphill_h = _octant_unit(
                        OCTANTS[int(rng.random() * 8)]
                    )
            point = _pick(
                envelope,
                placed,
                0.6 * frame.spacing,
                lambda item: (
                    inp.terrain.band(_cell_of_rel(frame.location_cell, item)),
                    item[0] * uphill_h[0] + item[1] * uphill_h[1],
                ),
                maximise=True,
            )
            pool = envelope
        elif entry.placement == "periphery":
            if water_vec is not None:
                outward = (-water_vec[0], -water_vec[1])
            elif gates:
                gate_unit = _unit(gates[0][1].rel_m)
                outward = (-gate_unit[0], -gate_unit[1]) if gate_unit else (1.0, 0.0)
            else:
                outward = (1.0, 0.0)
            point = _pick(
                envelope,
                placed,
                0.6 * frame.spacing,
                lambda item: item[0] * outward[0] + item[1] * outward[1],
                maximise=True,
            )
            pool = envelope
        elif entry.placement == "ring":
            if theta_zero is None:
                theta_zero = rng.random() * 2 * math.pi
            angle = theta_zero + ring_index * (2 * math.pi / ring_count)
            ring_index += 1
            ring_x = 0.55 * frame.radius * math.cos(angle)
            ring_y = 0.55 * frame.radius * math.sin(angle)
            point = _pick(
                envelope,
                placed,
                0.6 * frame.spacing,
                lambda item: math.hypot(item[0] - ring_x, item[1] - ring_y),
            )
            pool = envelope
        elif entry.placement == "water_edge":
            point = _pick(
                water_points,
                placed,
                0.6 * frame.spacing,
                lambda item: math.hypot(item[0], item[1]),
            )
            pool = water_points
        elif entry.placement == "water_downstream":
            if downstream is not None:
                downstream_unit = _octant_unit(downstream)
                point = _pick(
                    water_points,
                    placed,
                    0.6 * frame.spacing,
                    lambda item: item[0] * downstream_unit[0]
                    + item[1] * downstream_unit[1],
                    maximise=True,
                )
                pool = water_points
            elif water_contact:
                point = _pick(
                    water_points,
                    placed,
                    0.6 * frame.spacing,
                    lambda item: math.hypot(item[0], item[1]),
                )
                pool = water_points
            else:
                if water_vec is not None:
                    outward = (-water_vec[0], -water_vec[1])
                elif gates:
                    gate_unit = _unit(gates[0][1].rel_m)
                    outward = (
                        (-gate_unit[0], -gate_unit[1]) if gate_unit else (1.0, 0.0)
                    )
                else:
                    outward = (1.0, 0.0)
                point = _pick(
                    envelope,
                    placed,
                    0.6 * frame.spacing,
                    lambda item: item[0] * outward[0] + item[1] * outward[1],
                    maximise=True,
                )
                pool = envelope
        else:  # pragma: no cover - a catalogue outside PLACEMENTS is a bug
            raise GenerationError(
                f"{inp.map_id}: unknown placement {entry.placement!r}"
            )

        if point is None:
            warnings.append(f"role_unplaced:{entry.slot_id}")
            continue
        slot = Slot(entry.slot_id, entry.slot_id, entry.key_zh, point)
        slots.append(slot)
        placed.append(point)
        pool.remove(point)

    lane = 0
    while len(slots) < node_count:
        chosen = None
        for minimum in (frame.spacing, 0.6 * frame.spacing):
            best = None
            best_key = None
            for point in envelope:
                nearest = min(
                    (
                        math.hypot(point[0] - other[0], point[1] - other[1])
                        for other in placed
                    ),
                    default=math.inf,
                )
                if nearest < minimum:
                    continue
                key = (nearest, -point[1], -point[0])
                if best_key is None or key > best_key:
                    best = point
                    best_key = key
            if best is not None:
                chosen = best
                break
        if chosen is None:
            raise GenerationError(f"{inp.map_id}: envelope_full")
        lane += 1
        slot = Slot(f"lane_{lane:02d}", "filler", "巷弄", chosen)
        slots.append(slot)
        placed.append(chosen)
        envelope.remove(chosen)

    return slots, warnings, gate_octants


# -- roads and directions (D7) ----------------------------------------------------


@dataclass
class _Edge:
    u: int  # slot order index
    v: int
    length: float
    forced: bool = False
    alive: bool = True

    @property
    def key(self) -> tuple[int, int]:
        return (self.u, self.v) if self.u < self.v else (self.v, self.u)


class _DisjointSet:
    def __init__(self, size: int) -> None:
        self._parent = list(range(size))

    def find(self, item: int) -> int:
        parent = self._parent
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(self, left: int, right: int) -> bool:
        left_root, right_root = self.find(left), self.find(right)
        if left_root == right_root:
            return False
        self._parent[right_root] = left_root
        return True

    def connected(self) -> bool:
        return len({self.find(item) for item in range(len(self._parent))}) == 1


def _crosses_water(
    start: tuple[float, float],
    end: tuple[float, float],
    terrain: GridTerrain,
    location_cell: Cell,
) -> bool:
    length = math.hypot(end[0] - start[0], end[1] - start[1])
    steps = max(1, math.ceil(length / 50))
    for index in range(steps + 1):
        fraction = index / steps
        point = (
            start[0] + (end[0] - start[0]) * fraction,
            start[1] + (end[1] - start[1]) * fraction,
        )
        if terrain.is_water(_cell_of_rel(location_cell, point)):
            return True
    return False


def _is_crossing(slot_id: str) -> bool:
    return bool(words(slot_id) & CROSSING_WORDS)


def _build_roads(
    inp: GenerationInput,
    slots: list[Slot],
    gate_octants: dict[str, str],
    coordinates: list[tuple[int, int]],
) -> tuple[list[tuple[int, int, int]], list[str]]:
    positions = [slot.rel_m for slot in slots]
    # Directions are assigned from the emitted integer coordinates, so a rounded
    # or collision-shifted node cannot leave a road pointing somewhere else
    # than its document segment.
    direction_positions = [(float(x), float(y)) for x, y in coordinates]
    orders = {slot.slot_id: index for index, slot in enumerate(slots)}
    warnings: list[str] = []
    crossing_safe = [_is_crossing(slot.slot_id) for slot in slots]

    def edge_key(left: int, right: int) -> tuple[int, int]:
        return (left, right) if left < right else (right, left)

    candidates: list[_Edge] = []
    for left in range(len(slots)):
        for right in range(left + 1, len(slots)):
            dx = positions[right][0] - positions[left][0]
            dy = positions[right][1] - positions[left][1]
            length = math.hypot(dx, dy)
            midpoint = (
                (positions[left][0] + positions[right][0]) / 2,
                (positions[left][1] + positions[right][1]) / 2,
            )
            radius_squared = (length / 2) ** 2
            blocked = False
            for other in range(len(slots)):
                if other in (left, right):
                    continue
                if (positions[other][0] - midpoint[0]) ** 2 + (
                    positions[other][1] - midpoint[1]
                ) ** 2 < radius_squared:
                    blocked = True
                    break
            if blocked:
                continue
            if _crosses_water(
                positions[left],
                positions[right],
                inp.terrain,
                inp.location.cell,
            ) and not (crossing_safe[left] or crossing_safe[right]):
                continue
            key = edge_key(left, right)
            candidates.append(_Edge(key[0], key[1], length))
    candidates.sort(
        key=lambda edge: (edge.length, edge.u, edge.v)
    )

    forced: list[_Edge] = []
    forced_keys: set[tuple[int, int]] = set()
    plaza = orders["central_plaza"]
    for slot in slots:
        if slot.slot_id not in gate_octants:
            continue
        prefix = f"{slot.slot_id}_road_"
        approaches = sorted(
            (
                (int(other.slot_id[len(prefix) :]), other.slot_id)
                for other in slots
                if other.slot_id.startswith(prefix)
                and other.slot_id[len(prefix) :].isdigit()
            ),
            key=lambda item: item[0],
        )
        chain = [slot.slot_id, *(slot_id for _, slot_id in approaches), "central_plaza"]
        for source_id, destination_id in zip(chain, chain[1:]):
            source, destination = orders[source_id], orders[destination_id]
            if _crosses_water(
                positions[source],
                positions[destination],
                inp.terrain,
                inp.location.cell,
            ):
                continue
            key = edge_key(source, destination)
            if key in forced_keys:
                continue
            forced.append(_Edge(key[0], key[1], math.hypot(
                positions[key[0]][0] - positions[key[1]][0],
                positions[key[0]][1] - positions[key[1]][1],
            ), forced=True))
            forced_keys.add(key)

    tree = _DisjointSet(len(slots))
    degrees = [0] * len(slots)
    tree_keys: set[tuple[int, int]] = set()

    def admit(edge: _Edge, respect_cap: bool) -> bool:
        if tree.find(edge.u) == tree.find(edge.v):
            return False
        if respect_cap and (
            degrees[edge.u] >= inp.config.max_degree
            or degrees[edge.v] >= inp.config.max_degree
        ):
            return False
        tree.union(edge.u, edge.v)
        degrees[edge.u] += 1
        degrees[edge.v] += 1
        tree_keys.add(edge.key)
        return True

    for edge in forced:
        admit(edge, True)
    for edge in candidates:
        if edge.key in tree_keys:
            continue
        admit(edge, True)

    if not tree.connected():
        for edge in candidates:
            if edge.key in tree_keys:
                continue
            if admit(edge, False) and tree.connected():
                break
    if not tree.connected():
        raise GenerationError(f"{inp.map_id}: graph_disconnected")
    if max(degrees) > inp.config.max_degree:
        raise GenerationError(f"{inp.map_id}: degree_overflow")

    target_loops = round(inp.budget.loop_ratio * (len(slots) - 1))
    loop_keys: set[tuple[int, int]] = set()
    for edge in candidates:
        if len(loop_keys) >= target_loops:
            break
        if edge.key in tree_keys:
            continue
        if (
            degrees[edge.u] >= inp.config.max_degree
            or degrees[edge.v] >= inp.config.max_degree
        ):
            continue
        loop_keys.add(edge.key)
        degrees[edge.u] += 1
        degrees[edge.v] += 1

    edges = [
        edge
        for edge in [*forced, *candidates]
        if edge.key in tree_keys or edge.key in loop_keys
    ]
    unique_edges: dict[tuple[int, int], _Edge] = {}
    for edge in edges:
        unique_edges.setdefault(edge.key, edge)
    edges = list(unique_edges.values())

    directions, direction_warnings = _assign_directions(
        slots, direction_positions, edges, tree_keys, forced_keys
    )
    warnings.extend(direction_warnings)

    edges = [edge for edge in edges if edge.alive]
    loops = len(edges) - (len(slots) - 1)
    if loops < target_loops:
        warnings.append(f"loop_shortfall:{target_loops - loops}")

    roads = []
    for edge in edges:
        roads.append((edge.u, edge.v, directions[edge.u][edge.v]))
        roads.append((edge.v, edge.u, directions[edge.v][edge.u]))
    roads.sort(key=lambda road: (road[0], road[1]))
    return roads, warnings


def _assign_directions(
    slots: list[Slot],
    positions: list[tuple[float, float]],
    edges: list[_Edge],
    tree_keys: set[tuple[int, int]],
    forced_keys: set[tuple[int, int]],
) -> tuple[dict[int, dict[int, int]], list[str]]:
    orders = {slot.slot_id: index for index, slot in enumerate(slots)}
    incident: dict[int, list[int]] = {index: [] for index in range(len(slots))}
    for index, edge in enumerate(edges):
        incident[edge.u].append(index)
        incident[edge.v].append(index)

    def rows(node: int) -> list[tuple[int, int, float]]:
        result = []
        for edge_index in incident[node]:
            edge = edges[edge_index]
            other = edge.v if edge.u == node else edge.u
            dx = positions[other][0] - positions[node][0]
            dy = positions[other][1] - positions[node][1]
            result.append((orders[slots[other].slot_id], other, math.atan2(dy, dx)))
        result.sort()
        return result

    def costs(node: int) -> list[list[float]]:
        return [
            [
                abs(math.remainder(angle - octant * math.pi / 4, 2 * math.pi))
                for octant in range(8)
            ]
            for _, _, angle in rows(node)
        ]

    def assign(node: int) -> dict[int, int]:
        neighbours = [other for _, other, _ in rows(node)]
        table = costs(node)
        size = len(neighbours)
        if size == 0:
            return {}
        best_total = None
        best: tuple[int, ...] | None = None
        for permutation in itertools.permutations(range(8), size):
            total = 0.0
            for column, octant in enumerate(permutation):
                total += table[column][octant]
            if best_total is None or total < best_total:
                best_total = total
                best = permutation
        return {neighbours[index]: best[index] for index in range(size)}

    assignment = {node: assign(node) for node in range(len(slots))}

    def deviation(node: int) -> float:
        table = costs(node)
        assigned = assignment[node]
        if not table:
            return 0.0
        return max(
            table[column][assigned[other]]
            for column, (_, other, _) in enumerate(rows(node))
        )

    while True:
        progress = False
        for node in range(len(slots)):
            if deviation(node) <= 3 * math.pi / 8:
                continue
            removable = [
                edge_index
                for edge_index in incident[node]
                if edges[edge_index].key not in tree_keys
                and edges[edge_index].key not in forced_keys
            ]
            if not removable:
                continue
            chosen = max(
                removable,
                key=lambda edge_index: (
                    edges[edge_index].length,
                    -min(
                        orders[slots[edges[edge_index].u].slot_id],
                        orders[slots[edges[edge_index].v].slot_id],
                    ),
                ),
            )
            edge = edges[chosen]
            incident[edge.u].remove(chosen)
            incident[edge.v].remove(chosen)
            edge.alive = False
            assignment[edge.u] = assign(edge.u)
            assignment[edge.v] = assign(edge.v)
            progress = True
            break
        if not progress:
            break

    warnings = []
    for node in range(len(slots)):
        if deviation(node) > 3 * math.pi / 8:
            warnings.append(f"direction_deviation:{slots[node].slot_id}")
    return assignment, warnings


# -- document data (D8) -----------------------------------------------------------


def _node_coordinates(slots: list[Slot], margin: int) -> list[tuple[int, int]]:
    """The emitted integer coordinate of every slot, collisions repaired."""

    offset_x = margin - min(int(round(slot.rel_m[0])) for slot in slots)
    offset_y = margin - min(int(round(slot.rel_m[1])) for slot in slots)
    coordinates: list[tuple[int, int]] = []
    used: set[tuple[int, int]] = set()
    for slot in slots:
        x = int(round(slot.rel_m[0])) + offset_x
        y = int(round(slot.rel_m[1])) + offset_y
        while (x, y) in used:
            x += 1
        used.add((x, y))
        coordinates.append((x, y))
    return coordinates


def _document_data(
    inp: GenerationInput,
    slots: list[Slot],
    roads: list[tuple[int, int, int]],
    gate_octants: dict[str, str],
    footprint: frozenset[Cell],
    coordinates: list[tuple[int, int]],
) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    for slot, (x, y) in zip(slots, coordinates):
        anchor = slot.role == "anchor"
        nodes[slot.slot_id] = {
            "x_m": x,
            "y_m": y,
            "prototype_parent": "anchor_room" if anchor else "grid_room",
            "key": slot.key_zh,
            "desc": "",
            "anchor_key": inp.location.location_id if anchor else None,
            "typeclass": None,
            "scene_archetype": "city_street",
        }

    road_rows = [
        {
            "source": slots[source].slot_id,
            "destination": slots[destination].slot_id,
            "direction": OCTANTS[octant],
        }
        for source, destination, octant in roads
    ]

    min_x = min(cell[0] for cell in footprint)
    max_x = max(cell[0] for cell in footprint)
    min_y = min(cell[1] for cell in footprint)
    max_y = max(cell[1] for cell in footprint)
    shape = [
        "".join(
            "#" if (x, y) in footprint else "."
            for x in range(min_x, max_x + 1)
        )
        for y in range(min_y, max_y + 1)
    ]
    gates = [
        {
            "return_direction": OPPOSITE[gate_octants[slot.slot_id]],
            "destination_node": slot.slot_id,
        }
        for slot in slots
        if slot.role == "gate"
    ]

    return {
        "version": 1,
        "kind": "settlement",
        "id": inp.map_id,
        "location_ref": inp.location.location_id,
        "options": {"map_visual_range": 2, "map_mode": "nodes"},
        "exit_prototype": {
            "prototype_parent": "xyz_exit",
            "typeclass": "typeclasses.exits.CostedXYZExit",
        },
        "nodes": nodes,
        "roads": road_rows,
        "wilderness_entry": {
            "shape": shape,
            "offset": {
                "dx": min_x - inp.location.cell[0],
                "dy": min_y - inp.location.cell[1],
            },
            "gates": gates,
        },
        "city_gate": None,
    }


# -- the generator ----------------------------------------------------------------


def generate_settlement(inp: GenerationInput) -> GenerationResult:
    """Generate one settlement's coarse street graph and document data."""

    rng = random.Random(seed_for(inp.map_id))
    settlement_class = _settlement_class(inp)
    reach = math.ceil(math.sqrt(inp.budget.footprint_cells) / 2) + 1
    morphology, target = _morphology(inp, reach)
    footprint, water_contact, river_contact, warnings = _grow_footprint(
        inp, morphology, target, reach
    )
    sea_contact = any(
        inp.terrain.is_sea(neighbour)
        for cell in footprint
        for neighbour in _neighbours8(cell)
    )
    if morphology == "harbour_crescent" and not sea_contact:
        raise GenerationError(
            f"{inp.map_id}: water_unreachable: the sea is within reach but no "
            "walkable path reaches it"
        )
    if morphology in ("waterside_linear", "river_crossing") and not river_contact:
        raise GenerationError(
            f"{inp.map_id}: water_unreachable: the river is within reach but no "
            "walkable path reaches it"
        )
    water_vec = _water_vector(morphology, target)
    uphill_vec = _octant_unit(inp.site.uphill) if inp.site.uphill else None
    slots, placement_warnings, gate_octants = _place_nodes(
        inp,
        rng,
        morphology,
        target,
        footprint,
        water_contact,
        river_contact,
        water_vec,
        uphill_vec,
        _downstream(inp, target),
    )
    warnings.extend(placement_warnings)
    coordinates = _node_coordinates(slots, inp.config.margin_m)
    roads, road_warnings = _build_roads(inp, slots, gate_octants, coordinates)
    warnings.extend(road_warnings)
    data = _document_data(
        inp, slots, roads, gate_octants, footprint, coordinates
    )

    relative_path = f"content/maps/settlements/{inp.map_id}.yaml"
    try:
        document = document_from_data(relative_path, data)
    except AuthoringError as error:
        raise GenerationError(f"{inp.map_id}: invalid_document: {error}") from error
    findings = lint_settlement(document, inp.location.cell, inp.terrain)
    errors = sorted(
        {finding.code for finding in findings if finding.severity == "error"}
    )
    if errors:
        raise GenerationError(
            f"{inp.map_id}: lint_error: {', '.join(errors)}"
        )

    return GenerationResult(
        map_id=inp.map_id,
        settlement_class=settlement_class,
        morphology=morphology,
        footprint=footprint,
        slots=tuple(slots),
        data=data,
        warnings=tuple(sorted(set(warnings))),
    )


__all__ = [
    "FALLBACK_BEARINGS",
    "GenerationConfig",
    "GenerationError",
    "GenerationInput",
    "GenerationResult",
    "MORPHOLOGIES",
    "OCTANT_WORDS",
    "OCTANT_ZH",
    "SETTLEMENT_CLASSES",
    "Slot",
    "generate_settlement",
    "morphology_of",
    "seed_for",
    "settlement_class_of",
]
