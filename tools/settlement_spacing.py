"""Settlement spacing validation: the committed village and hamlet placement.

The placement script that chose the village and hamlet sites is a throwaway
tool with no tests, so this module is the tested gate that runs in continuous
integration instead. It reads the authored sources, the frozen road artifact,
the lore join and the list of completed areas, and reports three families of
problem:

* minimum spacing, measured in a straight line between cell centres, by kind;
* the road gap between consecutive settlements along one road;
* the placement identity rules for villages and hamlets.

Nothing here writes a file, and nothing here decides where a settlement goes.

The command exits 0 when it finds no problem, 1 when it finds any, and 2 when
one of its inputs does not load::

    uv run --locked python -m tools.settlement_spacing [--root DIR]
        [--lore FILE] [--roads FILE] [--areas FILE]
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from elosern_map_core import discover_source_documents, load_authoring_world
from elosern_map_core.authoring import terrain_definition
from elosern_map_core.documents import LocationDeclaration
from elosern_map_core.roads_codec import decode_road_network
from elosern_map_core.terrain import region_for_coordinates

from tools.settlement_synthesis.workspace import WorkspaceError, load_lore

Cell = tuple[int, int]

#: The repository root the shipped sources and the area list are read from.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
#: The completed-area list, relative to the repository root.
AREAS_PATH = Path("tools") / "settlement_spacing_areas.json"
#: The frozen road artifact, relative to the workspace root.
ROADS_PATH = Path("world") / "maps" / "data" / "road_network.json"
COMMAND = "uv run --locked python -m tools.settlement_spacing"

#: The kinds the placement rules govern, largest first.
NATIONAL_KINDS = ("capital", "city", "town", "port")
SMALL_KINDS = ("village", "hamlet")
#: Every kind that counts as a settlement; ``elven_village`` and ``dungeon`` do not.
SETTLEMENT_KINDS = NATIONAL_KINDS + SMALL_KINDS
#: The identifier each small kind must carry.
ID_PREFIXES = {"village": "village_", "hamlet": "hamlet_"}
#: A road step across one axis is one cell; a diagonal step is ``sqrt(2)``.
DIAGONAL_STEP = math.sqrt(2.0)
#: A gap within this distance of the maximum is still at the maximum.
EPSILON = 1e-9
#: The one key the area document may carry.
_AREA_DOCUMENT_KEYS = frozenset({"areas"})
#: The optional keys one area entry may carry.
_AREA_ENTRY_KEYS = frozenset({"id", "region", "bounds"})


@dataclass(frozen=True)
class SpacingConfig:
    """Every threshold and population range the check applies."""

    hamlet_min_km: float = 15.0
    village_min_km: float = 40.0
    road_gap_max_km: float = 75.0
    village_population: tuple[int, int] = (300, 2000)
    hamlet_population: tuple[int, int] = (50, 300)

    def population_range(self, kind: str) -> tuple[int, int]:
        """The inclusive population range of one small kind."""

        return self.hamlet_population if kind == "hamlet" else self.village_population


@dataclass(frozen=True)
class Place:
    """One authored location and the lore row joined to it."""

    location_id: str
    kind: str
    cell: Cell
    display_name_zh: str
    exemption: str | None
    nation: str | None
    population: int | None
    has_lore: bool


@dataclass(frozen=True)
class Area:
    """One completed area: a terrain region, optionally narrowed to a rectangle."""

    area_id: str
    region: str
    bounds: tuple[int, int, int, int] | None


@dataclass(frozen=True)
class SpacingInput:
    """Everything the check reads, as explicit values."""

    places: tuple[Place, ...]
    roads: tuple[tuple[str, str, tuple[Cell, ...]], ...]
    region_of: Callable[[Cell], str]
    region_nation: Mapping[str, str | None]
    forbidden_regions: frozenset[str]
    areas: tuple[Area, ...]


@dataclass(frozen=True)
class Problem:
    """One reported fault, addressed by the code and the subject it names."""

    code: str
    subject: str
    message: str


def check_spacing(
    inp: SpacingInput, config: SpacingConfig = SpacingConfig()
) -> tuple[Problem, ...]:
    """Every problem of one input, sorted by code and then by subject."""

    problems: list[Problem] = []
    problems.extend(_spacing_problems(inp, config))
    problems.extend(_identity_problems(inp, config))
    problems.extend(_road_gap_problems(inp, config))
    return tuple(sorted(problems, key=lambda problem: (problem.code, problem.subject)))


def _exempt(place: Place) -> bool:
    """Whether a place carries a spacing exemption; other kinds' marks do nothing."""

    return place.kind in SMALL_KINDS and place.exemption is not None


def _pair_rule(
    first: Place, second: Place, config: SpacingConfig
) -> tuple[str, str, float] | None:
    """The rule one unordered pair falls under: code, subject and minimum distance.

    ``None`` means the pair takes no part: a pair among the four national kinds
    is never checked, and neither is any pair with a kind outside the settlement
    kinds, so an elven village or a dungeon never constrains a neighbour.
    """

    if first.kind not in SETTLEMENT_KINDS or second.kind not in SETTLEMENT_KINDS:
        return None
    kinds = {first.kind, second.kind}
    if kinds <= set(NATIONAL_KINDS):
        return None
    if _exempt(first) or _exempt(second):
        return None
    if "hamlet" in kinds:
        code, minimum = "hamlet_spacing", config.hamlet_min_km
    else:
        code, minimum = "village_spacing", config.village_min_km
    if first.kind == second.kind:
        return code, min(first.location_id, second.location_id), minimum
    # A village-hamlet pair is governed by the hamlet rule only, so the hamlet
    # is always the subject; otherwise the small kind is.
    if "hamlet" in kinds:
        subject = first if first.kind == "hamlet" else second
    else:
        subject = first if first.kind == "village" else second
    return code, subject.location_id, minimum


def _spacing_problems(
    inp: SpacingInput, config: SpacingConfig
) -> list[Problem]:
    """Minimum spacing by kind, in straight-line kilometres between cell centres."""

    problems: list[Problem] = []
    for first, second in itertools.combinations(inp.places, 2):
        rule = _pair_rule(first, second, config)
        if rule is None:
            continue
        code, subject, minimum = rule
        distance = math.hypot(
            first.cell[0] - second.cell[0], first.cell[1] - second.cell[1]
        )
        if distance >= minimum:
            continue
        other = second if subject == first.location_id else first
        problems.append(
            Problem(
                code,
                subject,
                f"{distance:.1f} km from {other.location_id} ({other.kind}); "
                f"the minimum is {minimum:.0f} km",
            )
        )
    return problems


def _identity_problems(
    inp: SpacingInput, config: SpacingConfig
) -> list[Problem]:
    """The placement identity rules, per kind and per display name."""

    problems: list[Problem] = []
    road_cells = {cell for _, _, cells in inp.roads for cell in cells}
    for place in inp.places:
        region = inp.region_of(place.cell)
        nation = inp.region_nation.get(region)
        if place.kind in SMALL_KINDS:
            prefix = ID_PREFIXES[place.kind]
            if not place.location_id.startswith(prefix):
                problems.append(
                    Problem(
                        "id_prefix",
                        place.location_id,
                        f"a {place.kind} identifier must start with {prefix!r}",
                    )
                )
            if not place.has_lore:
                problems.append(
                    Problem(
                        "missing_lore",
                        place.location_id,
                        f"no lore row declares the {place.kind}",
                    )
                )
            if nation is None:
                problems.append(
                    Problem(
                        "no_nation",
                        place.location_id,
                        f"the region {region!r} lies outside every national border",
                    )
                )
            elif place.has_lore and place.nation != nation:
                problems.append(
                    Problem(
                        "nation_mismatch",
                        place.location_id,
                        f"the lore nation {place.nation!r} differs from {nation!r}",
                    )
                )
            if place.has_lore:
                low, high = config.population_range(place.kind)
                if place.population is None or not low <= place.population <= high:
                    problems.append(
                        Problem(
                            "population_range",
                            place.location_id,
                            f"the population {place.population!r} is outside "
                            f"{low} to {high}",
                        )
                    )
            if region in inp.forbidden_regions:
                problems.append(
                    Problem(
                        "forbidden_region",
                        place.location_id,
                        f"a {place.kind} may not stand in {region!r}",
                    )
                )
            if place.kind == "village" and place.cell not in road_cells:
                problems.append(
                    Problem(
                        "village_off_road",
                        place.location_id,
                        f"the cell {place.cell} is on no road of the artifact",
                    )
                )
        elif place.location_id.startswith(("village_", "hamlet_")):
            problems.append(
                Problem(
                    "id_prefix",
                    place.location_id,
                    f"a reserved small-kind prefix is wrong for a {place.kind}",
                )
            )
    problems.extend(_duplicate_name_problems(inp.places))
    return problems


def _duplicate_name_problems(places: Sequence[Place]) -> list[Problem]:
    """One problem per shared display name, under the smallest identifier."""

    by_name: dict[str, list[Place]] = {}
    for place in places:
        by_name.setdefault(place.display_name_zh, []).append(place)
    problems: list[Problem] = []
    for name, group in by_name.items():
        if len(group) < 2:
            continue
        ordered = sorted(group, key=lambda place: place.location_id)
        others = ", ".join(place.location_id for place in ordered[1:])
        problems.append(
            Problem(
                "duplicate_name",
                ordered[0].location_id,
                f"the display name {name!r} is also used by {others}",
            )
        )
    return problems


def _step_km(first: Cell, second: Cell) -> float:
    """The road length of one step between adjacent cells."""

    dx = abs(second[0] - first[0])
    dy = abs(second[1] - first[1])
    if not dx and not dy:
        return 0.0
    return DIAGONAL_STEP if dx and dy else 1.0


def _settlement_positions(
    cells: Sequence[Cell], marked: frozenset[Cell]
) -> list[int]:
    """The indices of one road that carry a settlement position."""

    positions = {0, len(cells) - 1}
    positions.update(
        index for index, cell in enumerate(cells) if cell in marked
    )
    return sorted(positions)


def _cell_in_area(
    areas: Sequence[Area], region_of: Callable[[Cell], str], cell: Cell
) -> bool:
    """Whether a cell lies in some completed area."""

    for area in areas:
        if region_of(cell) != area.region:
            continue
        if area.bounds is None:
            return True
        x_min, y_min, x_max, y_max = area.bounds
        if x_min <= cell[0] <= x_max and y_min <= cell[1] <= y_max:
            return True
    return False


def _road_gap_problems(
    inp: SpacingInput, config: SpacingConfig
) -> list[Problem]:
    """The gap along the road between consecutive settlement positions."""

    if not inp.areas:
        return []
    # A road end is a settlement position on every road that passes it: the
    # reuse factor merges roads, so a trunk can run through the gate approach
    # of a town it does not end at.
    marked = frozenset(
        {cells[0] for _, _, cells in inp.roads}
        | {cells[-1] for _, _, cells in inp.roads}
        | {place.cell for place in inp.places if place.kind in SMALL_KINDS}
    )
    problems: list[Problem] = []
    for first, second, cells in inp.roads:
        positions = _settlement_positions(cells, marked)
        for start, end in zip(positions, positions[1:]):
            gap = cells[start : end + 1]
            length = sum(
                _step_km(leaving, arriving)
                for leaving, arriving in zip(gap, gap[1:])
            )
            if length <= config.road_gap_max_km + EPSILON:
                continue
            if not all(
                _cell_in_area(inp.areas, inp.region_of, cell) for cell in gap
            ):
                continue
            problems.append(
                Problem(
                    "road_gap",
                    f"{first}--{second}",
                    f"{cells[start]} to {cells[end]} is {length:.1f} km "
                    "along the road",
                )
            )
    return problems


def _reject(label: str, detail: str) -> ValueError:
    """A rejected input value, naming the file and entry that carries it."""

    return ValueError(f"{label}: {detail}")


def _bounds(row: Mapping[str, Any], label: str) -> tuple[int, int, int, int] | None:
    """The validated inclusive rectangle of one area entry, or ``None``."""

    value = row.get("bounds")
    if value is None:
        return None
    if (
        not isinstance(value, list)
        or len(value) != 4
        or not all(
            isinstance(item, int) and not isinstance(item, bool) for item in value
        )
    ):
        raise _reject(label, "bounds is not four integers")
    x_min, y_min, x_max, y_max = value
    if x_min > x_max or y_min > y_max:
        raise _reject(label, "bounds is not an ordered rectangle")
    return (x_min, y_min, x_max, y_max)


def load_areas(path: Path) -> tuple[Area, ...]:
    """The completed-area list of one JSON file, rejecting malformed entries."""

    path = Path(path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise _reject(f"{path}", str(error)) from error
    if not isinstance(document, dict):
        raise _reject(f"{path}", "the document is not an object")
    unknown = set(document) - _AREA_DOCUMENT_KEYS
    if unknown:
        raise _reject(f"{path}", f"unknown keys {sorted(unknown)}")
    rows = document.get("areas")
    if not isinstance(rows, list):
        raise _reject(f"{path}", "'areas' is not a list")
    areas: list[Area] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        label = f"{path}: areas[{index}]"
        if not isinstance(row, dict):
            raise _reject(label, "the entry is not an object")
        unknown = set(row) - _AREA_ENTRY_KEYS
        if unknown:
            raise _reject(label, f"unknown keys {sorted(unknown)}")
        area_id = row.get("id")
        region = row.get("region")
        if not isinstance(area_id, str) or not area_id.strip():
            raise _reject(label, "the entry declares no id")
        if not isinstance(region, str) or not region.strip():
            raise _reject(label, f"the entry {area_id!r} declares no region")
        if area_id in seen:
            raise _reject(label, f"the entry {area_id!r} repeats an identifier")
        seen.add(area_id)
        areas.append(
            Area(area_id, region, _bounds(row, f"{label} {area_id!r}"))
        )
    return tuple(areas)


def _place(
    declaration: LocationDeclaration,
    lore: Mapping[str, tuple[str | None, int | None]],
) -> Place:
    """One authored location with its lore row joined."""

    row = lore.get(declaration.location_id)
    nation, population = row if row is not None else (None, None)
    return Place(
        location_id=declaration.location_id,
        kind=declaration.kind,
        cell=declaration.cell,
        display_name_zh=declaration.display_name_zh,
        exemption=declaration.spacing_exemption,
        nation=nation,
        population=population,
        has_lore=row is not None,
    )


def build_input(
    root: Path, lore: Path | None, roads: Path, areas: Path
) -> SpacingInput:
    """The explicit check input of one checkout, its artifact and its area list."""

    world = load_authoring_world(discover_source_documents(Path(root)))
    definition = terrain_definition(world.continent)
    try:
        network = decode_road_network(Path(roads).read_text(encoding="utf-8"))
    except ValueError as error:
        raise _reject(f"{roads}", str(error)) from error
    rows = load_lore(lore)
    completed = load_areas(Path(areas))
    region_nation = {
        region.region_id: region.nation_key
        for region in world.continent.regions.values()
    }
    for area in completed:
        if area.region not in region_nation:
            raise _reject(
                f"{areas}",
                f"the area {area.area_id!r} names the undeclared region "
                f"{area.region!r}",
            )
    return SpacingInput(
        places=tuple(
            _place(declaration, rows)
            for declaration in world.locations.locations.values()
        ),
        roads=network.roads,
        region_of=lambda cell: region_for_coordinates(definition, cell[0], cell[1]),
        region_nation=region_nation,
        forbidden_regions=(
            frozenset(world.road_network.forbidden_regions)
            if world.road_network is not None
            else frozenset()
        ),
        areas=completed,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the committed village and hamlet placement.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPOSITORY_ROOT,
        help="the repository tree whose authored sources are read",
    )
    parser.add_argument(
        "--lore",
        type=Path,
        default=None,
        help="a JSON nation/population override instead of the shipped lore",
    )
    parser.add_argument(
        "--roads",
        type=Path,
        default=None,
        help="the frozen road artifact; defaults to the artifact under --root",
    )
    parser.add_argument(
        "--areas",
        type=Path,
        default=None,
        help="the completed-area list; defaults to the repository's own list",
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    roads = args.roads if args.roads is not None else root / ROADS_PATH
    areas = args.areas if args.areas is not None else REPOSITORY_ROOT / AREAS_PATH
    try:
        inp = build_input(root, args.lore, roads, areas)
    except (OSError, ValueError, WorkspaceError) as error:
        print(f"{COMMAND}: the inputs do not load: {error}", file=sys.stderr)
        return 2
    problems = check_spacing(inp)
    for problem in problems:
        print(f"{problem.code} {problem.subject}: {problem.message}")
    print(f"spacing: {len(problems)} problems")
    return 1 if problems else 0


__all__ = [
    "AREAS_PATH",
    "Area",
    "COMMAND",
    "NATIONAL_KINDS",
    "Place",
    "Problem",
    "REPOSITORY_ROOT",
    "ROADS_PATH",
    "SETTLEMENT_KINDS",
    "SMALL_KINDS",
    "SpacingConfig",
    "SpacingInput",
    "build_input",
    "check_spacing",
    "load_areas",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())