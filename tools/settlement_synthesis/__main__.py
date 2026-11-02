"""Read-only command line for the settlement site, budget and fit tools.

All three commands read a workspace and print to stdout. None of them writes a
file, so a run can never change the sources it inspects.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

from elosern_map_core.authoring import gate_approach_cell

from tools.settlement_synthesis.budget import BudgetError, size_budget
from tools.settlement_synthesis.fit_lint import lint_settlement
from tools.settlement_synthesis.geometry import cell_of, world_position
from tools.settlement_synthesis.site import analyse_site
from tools.settlement_synthesis.workspace import (
    WorkspaceError,
    WorkspaceView,
    load_workspace,
)

#: The lint window never shrinks below this many cells.
SETTLEMENT_RADIUS_FLOOR = 8

#: The relief neighbourhood analysed around a location.
RELIEF_RADIUS = 3

#: The default water search radius: a 20-cell (20 km) box around the site.
DEFAULT_SITE_RADIUS = 20


def _as_json(value: Any) -> str:
    return json.dumps(
        dataclasses.asdict(value), ensure_ascii=False, indent=2, sort_keys=True
    )


def _workspace(args: argparse.Namespace) -> WorkspaceView:
    lore = getattr(args, "lore", None)
    return load_workspace(Path(args.root), Path(lore) if lore else None)


def _lint_radius(document: Any, location_cell: tuple[int, int]) -> int:
    """The terrain window one map's fit check can reach."""

    anchor = document.local_anchor_m
    if anchor is None:
        return SETTLEMENT_RADIUS_FLOOR
    cells = [
        cell_of(world_position(location_cell, anchor, node.coordinate))
        for node in document.nodes.values()
    ]
    for road in document.roads:
        cells.extend(
            cell_of(world_position(location_cell, anchor, (bend.x_m, bend.y_m)))
            for bend in road.bends
        )
    geometry = document.wilderness_geometry(location_cell)
    if geometry is not None:
        cells.extend(geometry.footprint_cells)
        for gate in geometry.gates:
            approach = gate_approach_cell(geometry, gate.return_direction)
            if approach is not None:
                cells.append(approach)
    reach = max(
        max(abs(cell[0] - location_cell[0]), abs(cell[1] - location_cell[1]))
        for cell in cells
    )
    return max(SETTLEMENT_RADIUS_FLOOR, RELIEF_RADIUS + reach)


def _site(args: argparse.Namespace) -> int:
    try:
        view = _workspace(args)
        location = view.location(args.location)
        terrain = view.terrain_window(
            location.cell, max(args.radius, RELIEF_RADIUS)
        )
        context = analyse_site(
            location,
            terrain,
            view.roster,
            radius=args.radius,
            relief_radius=RELIEF_RADIUS,
        )
    except WorkspaceError as error:
        print(f"settlement_synthesis: {error}", file=sys.stderr)
        return 2
    print(_as_json(context))
    return 0


def _budget(args: argparse.Namespace) -> int:
    try:
        view = _workspace(args)
        location = view.location(args.location)
    except WorkspaceError as error:
        print(f"settlement_synthesis: {error}", file=sys.stderr)
        return 2
    try:
        budget = size_budget(location)
    except BudgetError as error:
        print(f"settlement_synthesis: {error}", file=sys.stderr)
        return 1
    print(_as_json(budget))
    return 0


def _lint(args: argparse.Namespace) -> int:
    try:
        view = _workspace(args)
    except WorkspaceError as error:
        print(f"settlement_synthesis: {error}", file=sys.stderr)
        return 2
    map_ids = args.maps or sorted(view.world.settlements)
    findings = []
    for map_id in map_ids:
        document = view.world.settlements.get(map_id)
        if document is None:
            print(f"settlement_synthesis: unknown map {map_id!r}", file=sys.stderr)
            return 2
        try:
            location = view.location(document.location_ref)
            terrain = view.terrain_window(
                location.cell, _lint_radius(document, location.cell)
            )
        except WorkspaceError as error:
            print(f"settlement_synthesis: {error}", file=sys.stderr)
            return 2
        findings.extend(lint_settlement(document, location.cell, terrain))
    for finding in findings:
        print(
            f"{finding.severity.upper()} {finding.code} {finding.map_id} "
            f"{finding.object_id}: {finding.message}"
        )
    errors = sum(1 for finding in findings if finding.severity == "error")
    warnings = sum(1 for finding in findings if finding.severity == "warning")
    print(f"fit: {errors} errors, {warnings} warnings")
    return 1 if errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.settlement_synthesis",
        description=(
            "Read-only settlement site analysis, size budget and terrain-fit lint."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    site = commands.add_parser(
        "site", help="print one settlement's site context as JSON"
    )
    site.add_argument("location", metavar="LOCATION_ID")
    site.add_argument(
        "--root", default=".", help="workspace root (default: the current directory)"
    )
    site.add_argument("--lore", default=None, help="JSON lore override file")
    site.add_argument(
        "--radius",
        type=int,
        default=DEFAULT_SITE_RADIUS,
        help=(
            "water search radius in wilderness cells (default: %(default)s); the "
            f"relief neighbourhood is always {RELIEF_RADIUS} cells"
        ),
    )
    site.set_defaults(handler=_site)

    budget = commands.add_parser(
        "budget", help="print one settlement's size budget as JSON"
    )
    budget.add_argument("location", metavar="LOCATION_ID")
    budget.add_argument(
        "--root", default=".", help="workspace root (default: the current directory)"
    )
    budget.add_argument("--lore", default=None, help="JSON lore override file")
    budget.set_defaults(handler=_budget)

    lint = commands.add_parser(
        "lint", help="check settlement maps for terrain fit"
    )
    lint.add_argument(
        "maps",
        nargs="*",
        metavar="MAP_ID",
        help="settlement map ids to check (default: every map in the workspace)",
    )
    lint.add_argument(
        "--root", default=".", help="workspace root (default: the current directory)"
    )
    lint.set_defaults(handler=_lint)

    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    return arguments.handler(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
