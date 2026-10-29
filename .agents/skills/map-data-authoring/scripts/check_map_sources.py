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
from pathlib import Path

from elosern_map_core import diagnose_world, discover_source_documents, load_authoring_world
from elosern_map_core.authoring import terrain_definition
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
from elosern_map_core.terrain import is_land_cell, is_within_frame

PARTITION_PATH = "world/maps/data/district_partition.json"
REFERENCE_PATH = "content/map-reference-context.json"
MIN_VORONOI_SPACING_KM = 100  # mirrors world/lore/map_districts.py


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

    for sid, settlement in sorted(world.settlements.items()):
        label = f"settlement {sid!r}"
        anchors = [n for n in settlement.nodes.values() if n.prototype_parent == "anchor_room"]
        for node in anchors:
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
        if entry is not None and location is not None:
            anchor_cell = entry.anchor_cell
            if anchor_cell is not None and anchor_cell != location.cell:
                warnings.append(
                    f"{label} footprint anchor cell {anchor_cell} (mask bounding-box midpoint) "
                    f"!= location cell {location.cell}: the world-map marker and the real "
                    "wilderness entrance are in different places"
                )

    for iid, interior in sorted(world.interiors.items()):
        for room in interior.rooms.values():
            check_scene(f"interior {iid!r} room {room.room_id!r}", room.scene_archetype)

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
