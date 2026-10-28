"""Check the authored map sources the way the editor and the game would.

Run from the repository root, inside the map-core environment (no Evennia,
Django or database is needed):

    uv run --locked --project packages/map-core python \
        .agents/skills/map-data-authoring/scripts/check_map_sources.py [ROOT]

It reports three layers, in order:

1. core authoring gate: structure errors (the editor refuses to load) and
   semantic work-in-progress diagnostics (saveable, not game-ready), with the
   current partition freshness supplied;
2. game-adoption cross-file rules the core does not check but the game
   enforces at startup (binding/anchor agreement, footprint geometry, scene
   identifiers, doorway names, district spacing ...);
3. generated-artifact freshness: the district partition and the external
   reference context.

Exit status: 0 when nothing blocks game adoption, 1 otherwise, 2 when the
sources do not even load. The script reads files only and never writes.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

from elosern_map_core import diagnose_world, discover_source_documents, load_authoring_world
from elosern_map_core.authoring import gate_approach_cell, terrain_definition
from elosern_map_core.diagnostics import AuthoringError
from elosern_map_core.geometry import cell_center_m, local_to_world_m
from elosern_map_core.partition_codec import (
    PartitionDocumentError,
    partition_freshness,
    read_partition_metadata,
)
from elosern_map_core.reference_context import (
    ReferenceContextError,
    check_workspace_freshness,
    decode_reference_context,
)
from elosern_map_core.terrain import is_land_cell, is_walkable_cell, is_within_frame

PARTITION_PATH = "world/maps/data/district_partition.json"
REFERENCE_PATH = "content/map-reference-context.json"
MIN_VORONOI_SPACING_KM = 100  # mirrors world/lore/map_districts.py
DELTAS = {
    "n": (0, 1), "ne": (1, 1), "e": (1, 0), "se": (1, -1),
    "s": (0, -1), "sw": (-1, -1), "w": (-1, 0), "nw": (-1, 1),
}


def _diag_line(item: dict) -> str:
    where = item.get("relative_path") or "?"
    if item.get("line"):
        where += f":{item['line']}"
    field = item.get("field_path") or ""
    return f"[{item.get('category')}/{item.get('code')}] {where} {field} - {item.get('message')}"


def _load_reference(root: Path):
    path = root / REFERENCE_PATH
    if not path.is_file():
        return None, "missing"
    try:
        context = decode_reference_context(path.read_text(encoding="utf-8"))
    except (ReferenceContextError, ValueError) as error:
        return None, f"undecodable: {error}"
    freshness = check_workspace_freshness(context, root)
    return context, "current" if freshness else f"stale ({getattr(freshness, 'status', '')} {getattr(freshness, 'reason', '')})".strip()


def _partition(root: Path, world):
    path = root / PARTITION_PATH
    if not path.is_file():
        return None, "missing"
    try:
        metadata = read_partition_metadata(path.read_text(encoding="utf-8"))
    except (PartitionDocumentError, ValueError) as error:
        return None, f"unreadable: {error}"
    freshness = partition_freshness(metadata, world.partition_signature)
    return freshness, "current" if freshness.current else "stale"


def game_rules(world, context) -> tuple[list[str], list[str]]:
    problems: list[str] = []
    warnings: list[str] = []
    terrain = terrain_definition(world.continent)
    frame = world.continent.terrain.frame_cells
    locations = world.locations.locations
    scenes = context.identifier_set("scene_archetypes") if context else None
    nations = context.identifier_set("nations") if context else None

    def check_cell(label: str, cell) -> None:
        if not is_within_frame(frame, cell):
            problems.append(f"{label} cell {cell} is outside the frame")
        elif not is_land_cell(terrain, cell):
            problems.append(f"{label} cell {cell} is not on the mainland")

    def check_scene(label: str, scene) -> None:
        if scene is not None and scenes is not None and scene not in scenes:
            problems.append(f"{label} names unregistered scene archetype {scene!r}")

    for key, location in sorted(locations.items()):
        check_cell(f"location {key!r}", location.cell)
        check_scene(f"location {key!r}", location.scene_archetype)
    for key, site in sorted(world.continent.harbor_sites.items()):
        check_cell(f"harbor site {key!r}", site.cell)
    for key, region in sorted(world.continent.regions.items()):
        if not region.scene_archetype:
            problems.append(f"region {key!r} declares no scene archetype")
        check_scene(f"region {key!r}", region.scene_archetype)
        if nations is not None:
            for nation in (region.nation_key, *region.nominal_nation_keys):
                if nation is not None and nation not in nations:
                    problems.append(f"region {key!r} names unknown nation {nation!r}")

    bound_locations: dict[str, str] = {}
    footprints: dict[str, frozenset] = {}
    point_anchors: dict[str, tuple] = {}
    approaches: list[tuple[str, str, tuple | None]] = []
    for sid, settlement in sorted(world.settlements.items()):
        label = f"settlement {sid!r}"
        if settlement.location_ref in bound_locations:
            problems.append(
                f"{label} binds location {settlement.location_ref!r} already bound by "
                f"{bound_locations[settlement.location_ref]!r}"
            )
        bound_locations[settlement.location_ref] = sid
        anchors = [n for n in settlement.nodes.values() if n.prototype_parent == "anchor_room"]
        if settlement.nodes and len(anchors) != 1:
            problems.append(f"{label} declares {len(anchors)} anchor_room nodes, expected exactly one")
        for node in anchors:
            if node.anchor_key != settlement.location_ref:
                problems.append(
                    f"{label} anchor node {node.node_id!r} anchor_key {node.anchor_key!r} "
                    f"!= location_ref {settlement.location_ref!r}"
                )
            if settlement.binding.local_anchor_m != (node.x_m, node.y_m):
                problems.append(
                    f"{label} binding.local_anchor_m {settlement.binding.local_anchor_m} != "
                    f"anchor node {node.node_id!r} position {(node.x_m, node.y_m)}"
                )
        location = locations.get(settlement.location_ref)
        if location is not None and settlement.binding.anchor_cell != location.cell:
            problems.append(
                f"{label} binding.anchor_cell {settlement.binding.anchor_cell} != "
                f"location {settlement.location_ref!r} cell {location.cell} "
                "(move both together)"
            )
        for node in settlement.nodes.values():
            check_scene(f"{label} node {node.node_id!r}", node.scene_archetype)

        entry = settlement.wilderness_entry
        if entry is None:
            continue
        cells = entry.mask_cells
        widths = {len(row) for row in entry.shape}
        if len(widths) != 1:
            problems.append(f"{label} wilderness_entry.shape is ragged")
        for cell in sorted(cells):
            if not is_walkable_cell(terrain, cell):
                problems.append(f"{label} footprint cell {cell} is not walkable terrain")
        anchor_cell = entry.anchor_cell
        if location is not None and anchor_cell is not None and anchor_cell != location.cell:
            warnings.append(
                f"{label} footprint anchor cell {anchor_cell} (mask bounding-box midpoint) "
                f"!= location cell {location.cell}: the world-map marker and the real "
                "wilderness entrance are in different places"
            )
        if not cells:
            problems.append(f"{label} wilderness_entry.shape has no '#' cell")
            continue
        if entry.is_point_shape:
            point_anchors[sid] = anchor_cell
            if len(entry.gates) != 1:
                problems.append(f"{label} point-shape entry must have exactly one gate")
        else:
            seen = set()
            stack = [next(iter(cells))]
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in seen:
                    continue
                seen.add((cx, cy))
                stack.extend(c for c in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)) if c in cells)
            if seen != set(cells):
                problems.append(f"{label} footprint '#' cells are not 4-connected")
            if anchor_cell not in cells:
                problems.append(f"{label} footprint anchor cell {anchor_cell} is not a '#' cell")
        footprints[sid] = entry.footprint_cells
        destinations = [gate.destination_node for gate in entry.gates]
        if len(set(destinations)) != len(destinations):
            problems.append(f"{label} two wilderness gates share one destination node")
        for gate in entry.gates:
            approach = gate_approach_cell(entry, gate.return_direction)
            approaches.append((sid, gate.return_direction, approach))
            if approach is None:
                problems.append(f"{label} gate {gate.return_direction!r} has no approach cell")
            elif entry.is_point_shape:
                dx, dy = DELTAS[gate.return_direction]
                neighbour = (anchor_cell[0] + dx, anchor_cell[1] + dy)
                if not is_walkable_cell(terrain, neighbour):
                    problems.append(
                        f"{label} point anchor {anchor_cell} has unwalkable neighbour {neighbour} "
                        f"in its gate direction {gate.return_direction!r}"
                    )
            elif not is_walkable_cell(terrain, approach):
                problems.append(f"{label} gate {gate.return_direction!r} approach {approach} is not walkable")

    for sid, cells in footprints.items():
        for other, other_cells in footprints.items():
            if other > sid and cells & other_cells:
                problems.append(f"settlement {sid!r} footprint overlaps {other!r}")
        for other, point in point_anchors.items():
            if other != sid and point in cells:
                problems.append(f"settlement {sid!r} footprint contains the point anchor of {other!r}")
    seen_keys = set()
    for sid, direction, approach in approaches:
        if approach is None:
            continue
        for other, point in point_anchors.items():
            if other != sid and approach == point:
                problems.append(f"settlement {sid!r} gate {direction!r} approach {approach} is the point anchor of {other!r}")
        if (approach, direction) in seen_keys:
            problems.append(f"settlement {sid!r} gate {direction!r} collides with another gate's approach")
        seen_keys.add((approach, direction))
        for other, cells in footprints.items():
            if other != sid and approach in cells:
                problems.append(f"settlement {sid!r} gate {direction!r} approach {approach} lies inside {other!r}")

    room_owner: dict[str, str] = {}
    doorways: dict[tuple, str] = {}
    for iid, interior in sorted(world.interiors.items()):
        for room in interior.rooms.values():
            check_scene(f"interior {iid!r} room {room.room_id!r}", room.scene_archetype)
            if room.room_id in room_owner:
                problems.append(
                    f"room id {room.room_id!r} is declared by both {room_owner[room.room_id]!r} and {iid!r}"
                )
            room_owner.setdefault(room.room_id, iid)
        exterior = interior.exterior
        if exterior is not None:
            key = (exterior.settlement, exterior.node, exterior.doorway_key)
            if key in doorways:
                problems.append(
                    f"interiors {doorways[key]!r} and {iid!r} open onto {exterior.settlement}:"
                    f"{exterior.node} with the same doorway_key {exterior.doorway_key!r}"
                )
            doorways.setdefault(key, iid)

    seen_names: dict[tuple, str] = {}
    seeds: dict[str, tuple] = {}
    for did, district in sorted(world.districts.districts.items()):
        for field in ("district_name_zh", "landmark_name_zh"):
            value = getattr(district, field)
            if (field, value) in seen_names:
                problems.append(f"district {did!r} duplicate {field} {value!r} (also {seen_names[(field, value)]!r})")
            seen_names.setdefault((field, value), did)
        if district.kind != "voronoi":
            continue
        ref = district.landmark
        position = None
        if ref.domain == "wilderness_cell" and ref.cell is not None:
            position = cell_center_m(ref.cell)
        elif ref.domain == "location" and ref.object_id in locations:
            position = cell_center_m(locations[ref.object_id].cell)
        elif ref.domain == "settlement_node" and ref.map_id in world.settlements:
            settlement = world.settlements[ref.map_id]
            node = settlement.nodes.get(ref.object_id)
            if node is not None:
                position = local_to_world_m(
                    settlement.binding.anchor_cell, settlement.binding.local_anchor_m, (node.x_m, node.y_m)
                )
        if position is not None:
            seeds[did] = position
    ordered = sorted(seeds.items())
    for index, (did, (ax, ay)) in enumerate(ordered):
        for other, (bx, by) in ordered[index + 1:]:
            distance_km = math.hypot(ax - bx, ay - by) / 1000
            if distance_km < MIN_VORONOI_SPACING_KM:
                problems.append(
                    f"districts {did!r} and {other!r} landmarks are {distance_km:.1f} km apart "
                    f"(minimum {MIN_VORONOI_SPACING_KM} km)"
                )
    return problems, warnings


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    sources = discover_source_documents(root)
    try:
        world = load_authoring_world(sources)
    except AuthoringError as error:
        print("STRUCTURE REJECTED - the editor shows a stale preview and refuses writes:")
        for item in error.diagnostics:
            print("  " + _diag_line(item.as_dict()))
        return 2

    freshness, partition_state = _partition(root, world)
    diagnostics = diagnose_world(world, partition_freshness=freshness)
    context, context_state = _load_reference(root)
    problems, warnings = game_rules(world, context)

    print(f"loaded {len(world.documents)} documents from {root}")
    print(f"core semantic diagnostics: {len(diagnostics)}")
    for item in diagnostics:
        print("  " + _diag_line(item.as_dict()))
    print(f"game-adoption cross-file problems: {len(problems)}")
    for problem in problems:
        print("  - " + problem)
    print(f"warnings (not enforced, usually a mistake): {len(warnings)}")
    for warning in warnings:
        print("  - " + warning)
    print(f"district partition: {partition_state}")
    if partition_state != "current":
        print(
            "  regenerate: `uv run --locked --project tools/map-editor python "
            ".agents/skills/map-data-authoring/scripts/regenerate_partition.py` (or the editor's 分區 chip)"
        )
    print(f"reference context: {context_state}")
    if context_state != "current":
        print("  regenerate: `uv run --locked python -m tools.map_reference_context` (deletions stay refused until current)")
    blocked = bool(diagnostics or problems or partition_state != "current")
    print("RESULT:", "not game-ready" if blocked else "game-ready as far as static checks can tell")
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
