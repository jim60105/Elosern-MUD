"""Command line for the settlement site, budget, fit and generation tools.

``site``, ``budget`` and ``lint`` read a workspace and print to stdout; none of
them writes a file. ``generate`` is the one writing command, and it only ever
creates a settlement source that does not exist yet.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys
from pathlib import Path
from typing import Any

from elosern_map_core.authoring import gate_approach_cell
from elosern_map_core.codec import document_from_data, serialize_document
from elosern_map_core.diagnostics import AuthoringError

from tools.settlement_synthesis.budget import (
    NATIONAL_KINDS,
    BudgetError,
    size_budget,
)
from tools.settlement_synthesis.fit_lint import lint_settlement
from tools.settlement_synthesis.generate import (
    OCTANT_WORDS,
    GenerationConfig,
    GenerationError,
    GenerationInput,
    GenerationResult,
    generate_settlement,
)
from tools.settlement_synthesis.geometry import cell_of, world_position
from tools.settlement_synthesis.roles import DEFAULT_CATALOGUE
from tools.settlement_synthesis.site import analyse_site
from tools.settlement_synthesis.workspace import (
    WorkspaceError,
    WorkspaceView,
    load_workspace,
    settlement_path,
    write_atomic,
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


def _forced_gates(value: str) -> tuple[str, ...] | None:
    bearings = tuple(item.strip() for item in value.split(",") if item.strip())
    for bearing in bearings:
        if bearing not in OCTANT_WORDS:
            print(
                f"settlement_synthesis: unknown octant {bearing!r}; choose from "
                f"{', '.join(OCTANT_WORDS)}",
                file=sys.stderr,
            )
            return None
    return bearings


def _report(result: GenerationResult) -> dict[str, Any]:
    nodes = result.data["nodes"]
    return {
        "map_id": result.map_id,
        "settlement_class": result.settlement_class,
        "morphology": result.morphology,
        "footprint_cells": len(result.footprint),
        "warnings": list(result.warnings),
        "slots": [
            {
                "id": slot.slot_id,
                "role": slot.role,
                "key": slot.key_zh,
                "x_m": nodes[slot.slot_id]["x_m"],
                "y_m": nodes[slot.slot_id]["y_m"],
            }
            for slot in result.slots
        ],
    }


def _existing_document(view: WorkspaceView, location_id: str) -> str | None:
    """The relative path of a settlement already bound to one location."""

    path = settlement_path(view.root, location_id)
    if path.is_file():
        return path.relative_to(view.root).as_posix()
    for document in view.world.settlements.values():
        if document.location_ref == location_id:
            return document.relative_path
    return None


def _generation_input(
    view: WorkspaceView, location: Any, forced_gates: tuple[str, ...]
) -> GenerationInput:
    budget = size_budget(location)
    reach = math.ceil(math.sqrt(budget.footprint_cells) / 2) + 1
    radius = max(
        reach + 6,
        math.ceil(1.5 * budget.envelope_radius_m / 1000) + 6,
        10,
    )
    terrain = view.terrain_window(location.cell, radius)
    site = analyse_site(location, terrain, view.roster)
    return GenerationInput(
        map_id=location.location_id,
        location=location,
        site=site,
        budget=budget,
        terrain=terrain,
        blocked=view.blocked_cells(location.location_id),
        catalogue=DEFAULT_CATALOGUE,
        forced_gates=forced_gates,
        config=GenerationConfig(),
    )


def _generate_one(
    view: WorkspaceView,
    location: Any,
    *,
    plan_only: bool,
    forced_gates: tuple[str, ...],
) -> int:
    if location.kind not in NATIONAL_KINDS:
        print(
            f"settlement_synthesis: {location.location_id}: kind "
            f"{location.kind!r} has no size budget",
            file=sys.stderr,
        )
        return 1
    existing = _existing_document(view, location.location_id)
    if existing is not None:
        print(f"exists: {existing}")
        return 1
    try:
        result = generate_settlement(
            _generation_input(view, location, forced_gates)
        )
    except (BudgetError, GenerationError) as error:
        print(f"settlement_synthesis: {error}", file=sys.stderr)
        return 1
    print(json.dumps(_report(result), ensure_ascii=False, indent=2, sort_keys=True))
    if plan_only:
        return 0
    relative_path = f"content/maps/settlements/{result.map_id}.yaml"
    try:
        text = serialize_document(
            document_from_data(relative_path, result.data), None
        )
    except AuthoringError as error:
        print(f"settlement_synthesis: {error}", file=sys.stderr)
        return 1
    write_atomic(settlement_path(view.root, result.map_id), text)
    return 0


def _generate(args: argparse.Namespace) -> int:
    forced_gates = _forced_gates(args.gates)
    if forced_gates is None:
        return 2
    if args.missing:
        if args.location is not None:
            print(
                "settlement_synthesis: --missing takes no LOCATION_ID",
                file=sys.stderr,
            )
            return 2
        if not args.nation:
            print(
                "settlement_synthesis: --missing requires --nation",
                file=sys.stderr,
            )
            return 2
    elif args.location is None:
        print("settlement_synthesis: a LOCATION_ID is required", file=sys.stderr)
        return 2

    try:
        view = _workspace(args)
    except WorkspaceError as error:
        print(f"settlement_synthesis: {error}", file=sys.stderr)
        return 2

    if not args.missing:
        try:
            location = view.location(args.location)
        except WorkspaceError as error:
            print(f"settlement_synthesis: {error}", file=sys.stderr)
            return 2
        return _generate_one(
            view, location, plan_only=args.plan_only, forced_gates=forced_gates
        )

    targets = [
        ref
        for ref in view.roster
        if ref.nation == args.nation
        and ref.kind in NATIONAL_KINDS
        and _existing_document(view, ref.location_id) is None
    ]
    targets.sort(key=lambda ref: (-(ref.population or 0), ref.location_id))
    status = 0
    for ref in targets:
        try:
            current = _workspace(args)
        except WorkspaceError as error:
            print(f"settlement_synthesis: {error}", file=sys.stderr)
            return 2
        try:
            location = current.location(ref.location_id)
        except WorkspaceError as error:
            print(f"settlement_synthesis: {error}", file=sys.stderr)
            status = 1
            continue
        if (
            _generate_one(
                current,
                location,
                plan_only=args.plan_only,
                forced_gates=forced_gates,
            )
            != 0
        ):
            status = 1
    return status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tools.settlement_synthesis",
        description=(
            "Settlement site analysis, size budget, terrain-fit lint and street-"
            "graph generation."
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

    generate = commands.add_parser(
        "generate",
        help="generate one settlement street graph from its site and budget",
    )
    generate.add_argument("location", nargs="?", metavar="LOCATION_ID")
    generate.add_argument(
        "--root", default=".", help="workspace root (default: the current directory)"
    )
    generate.add_argument("--lore", default=None, help="JSON lore override file")
    generate.add_argument(
        "--gates",
        default="",
        metavar="OCTANT[,OCTANT...]",
        help="forced gate bearings, highest priority first",
    )
    generate.add_argument(
        "--plan-only",
        action="store_true",
        help="print the report and write nothing",
    )
    generate.add_argument(
        "--missing",
        action="store_true",
        help=(
            "generate every national settlement of --nation that has no "
            "settlement source yet"
        ),
    )
    generate.add_argument(
        "--nation", default=None, help="nation key for --missing"
    )
    generate.set_defaults(handler=_generate)

    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    return arguments.handler(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
