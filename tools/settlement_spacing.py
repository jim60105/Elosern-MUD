"""Settlement spacing validation: the committed village and hamlet placement.

The placement script that chose the village and hamlet sites is a throwaway
tool with no tests, so this module is the tested gate that runs in continuous
integration instead. It reads the authored sources, the frozen road artifact
and the lore join, and reports three families of problem:

* minimum spacing, measured in a straight line between cell centres, by kind;
* the road gap between consecutive settlements along one road;
* the placement identity rules for villages and hamlets.

Nothing here writes a file, and nothing here decides where a settlement goes.

The command exits 0 when it finds no problem, 1 when it finds any, and 2 when
one of its inputs does not load::

    uv run --locked python -m tools.settlement_spacing [--root DIR]
        [--lore FILE] [--roads FILE]
"""

from __future__ import annotations

import argparse
import itertools
import math
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from elosern_map_core import discover_source_documents, load_authoring_world
from elosern_map_core.authoring import terrain_definition
from elosern_map_core.documents import LocationDeclaration
from elosern_map_core.roads_codec import decode_road_network
from elosern_map_core.terrain import region_for_coordinates

from tools.settlement_synthesis.workspace import WorkspaceError, load_lore

Cell = tuple[int, int]

#: The repository root the shipped sources are read from.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
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
class SpacingInput:
    """Everything the check reads, as explicit values."""

    places: tuple[Place, ...]
    roads: tuple[tuple[str, str, tuple[Cell, ...]], ...]
    region_of: Callable[[Cell], str]
    region_nation: Mapping[str, str | None]
    forbidden_regions: frozenset[str]


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


def _road_gap_problems(
    inp: SpacingInput, config: SpacingConfig
) -> list[Problem]:
    """The gap along the road between consecutive settlement positions."""

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
            problems.append(
                Problem(
                    "road_gap",
                    f"{first}--{second}",
                    f"{cells[start]} to {cells[end]} is {length:.1f} km "
                    "along the road",
                )
            )
    return problems


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
    root: Path, lore: Path | None, roads: Path
) -> SpacingInput:
    """The explicit check input of one checkout and its artifact."""

    world = load_authoring_world(discover_source_documents(Path(root)))
    definition = terrain_definition(world.continent)
    try:
        network = decode_road_network(Path(roads).read_text(encoding="utf-8"))
    except ValueError as error:
        raise ValueError(f"{roads}: {error}") from error
    rows = load_lore(lore)
    region_nation = {
        region.region_id: region.nation_key
        for region in world.continent.regions.values()
    }
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
    args = parser.parse_args(argv)
    root = Path(args.root)
    roads = args.roads if args.roads is not None else root / ROADS_PATH
    try:
        inp = build_input(root, args.lore, roads)
    except (OSError, ValueError, WorkspaceError) as error:
        print(f"{COMMAND}: the inputs do not load: {error}", file=sys.stderr)
        return 2
    problems = check_spacing(inp)
    for problem in problems:
        print(f"{problem.code} {problem.subject}: {problem.message}")
    print(f"spacing: {len(problems)} problems")
    return 1 if problems else 0


__all__ = [
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
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())