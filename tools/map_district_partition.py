"""Offline district-partition adapter: explicit snapshot in, frozen artifact out.

The algorithm, its input rasterization and the artifact encoding live in
``elosern_map_core.partition`` (the ``generation`` extra of the pure map core).
This module is only the game-side adapter that binds the published shipped
world into an explicit, immutable snapshot:

* the terrain definition of the published geography;
* the declared nation and terrain-region identifiers;
* the live anchor footprint cells (land that is never walkable);
* each district's resolved landmark cell, routed same-nation gateway approach
  cells and containing footprint; and
* the source dependency signature of the authored map sources.

Then it writes the result to ``world/maps/data/district_partition.json``, the
sole committed, read-only generated output. The runtime decodes that file
through ``world.maps.district_partition``; it never imports this module.

Regenerate after any change to the district document, the terrain model
(mainland, ridge, passes, waterways, fords, forest edge, nominal claims),
anchor footprints, gateways or the settlement routes to a grid landmark::

    uv run --locked python -m tools.map_district_partition

``--check`` regenerates in memory and exits non-zero when the committed file
differs byte for byte.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from elosern_map_core.partition import (
    DistrictSeed,
    PartitionInputSnapshot,
    generate_partition,
    partition_input,
)
from elosern_map_core.partition_codec import partition_source_signature
from elosern_map_core.sources import discover_source_documents

#: The repository root the shipped sources are read from.
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPOSITORY_ROOT / "world" / "maps" / "data" / "district_partition.json"


def _districts() -> tuple[DistrictSeed, ...]:
    """Resolve every published district into the partition's seed form."""
    from world.lore import map_districts, wilderness_entry
    from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
    from world.lore.anchors import LOCAL_FRAME_ANCHOR_REGISTRY, world_position_m
    from world.maps.map_data import settlement_graph
    from world.maps.static_references import settlement_node_xy
    from world.rules.map_knowledge import decode_node

    entries = wilderness_entry.WILDERNESS_ENTRY_REGISTRY
    seeds = []
    for district in map_districts.current().districts.values():
        landmark_node = map_districts.landmark_node_id(district)
        if landmark_node is None:
            raise ValueError(
                f"{district.district_id}: landmark {district.landmark!r} does not resolve to a node"
            )
        parts = decode_node(landmark_node)
        if parts["prefix"] == "wild":
            seeds.append(
                DistrictSeed(
                    district.district_id,
                    district.kind,
                    (parts["x"], parts["y"]),
                    district.region_key,
                )
            )
            continue
        map_key, xy = parts["z_map_key"], (parts["x"], parts["y"])
        graph = settlement_graph(map_key)
        node = graph.node_at(xy) if graph is not None else None
        anchor_key = next(
            (
                placement.anchor_key
                for placement in ANCHOR_PLACEMENT_REGISTRY.values()
                if placement.zcoord == map_key and placement.anchor_key in LOCAL_FRAME_ANCHOR_REGISTRY
            ),
            None,
        )
        if node is None or anchor_key is None:
            raise ValueError(f"{district.district_id}: grid landmark {landmark_node} does not resolve")
        cell = map_districts.cell_of_position(world_position_m(anchor_key, node.physical_coordinate))
        approaches = []
        footprint: frozenset[tuple[int, int]] = frozenset()
        for entry in entries.values():
            if cell in entry.footprint_cells:
                footprint = entry.footprint_cells
            for gate in entry.gates:
                gate_node = (
                    graph.node_at(
                        settlement_node_xy(
                            gate.destination,
                            source=f"wilderness gate {entry.anchor_key}",
                        )
                    )
                    if gate.z_map_key == map_key
                    else None
                )
                approach = entry.approach_cell(gate)
                if gate_node is None or approach is None:
                    continue
                if graph.route(gate_node.node_id, node.node_id) is not None:
                    approaches.append(approach)
        seeds.append(
            DistrictSeed(
                district.district_id,
                district.kind,
                cell,
                district.region_key,
                tuple(sorted(set(approaches))),
                footprint,
            )
        )
    return tuple(seeds)


def _footprint_cells() -> frozenset[tuple[int, int]]:
    """Every anchor footprint cell of the live gateway registry."""
    from world.lore import wilderness_entry

    cells: set[tuple[int, int]] = set()
    for entry in wilderness_entry.WILDERNESS_ENTRY_REGISTRY.values():
        cells.update(entry.footprint_cells)
    return frozenset(cells)


def map_input_snapshot(root: str | Path | None = None) -> PartitionInputSnapshot:
    """The explicit immutable map inputs of the currently published world."""
    from world.lore.nations import NATION_REGISTRY
    from world.lore.wilderness_regions import regions
    from world.maps.wilderness_provider import terrain_definition

    base = Path(root) if root is not None else REPOSITORY_ROOT
    return PartitionInputSnapshot(
        terrain=terrain_definition(),
        nation_names=tuple(sorted(NATION_REGISTRY)),
        region_names=tuple(sorted(regions())),
        footprints=_footprint_cells(),
        districts=_districts(),
        source_signature=partition_source_signature(discover_source_documents(base)),
    )


def artifact_text(root: str | Path | None = None) -> str:
    """The complete committed artifact text for the current sources."""
    return generate_partition(partition_input(map_input_snapshot(root)))


def _bootstrap() -> None:
    root = REPOSITORY_ROOT
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    import django

    django.setup()
    import evennia

    evennia._init()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the frozen map-district partition.")
    parser.add_argument("--check", action="store_true", help="fail when the committed file is stale")
    parser.add_argument("--output", type=Path, default=DATA_PATH)
    args = parser.parse_args(argv)
    _bootstrap()
    from world.lore import map_districts
    from world.maps import map_data
    from world.maps.geography import load_and_publish

    map_data.load_and_publish()
    load_and_publish()
    map_districts.load_and_publish()
    text = artifact_text()
    current = args.output.read_text(encoding="utf-8") if args.output.exists() else None
    if args.check:
        if current != text:
            print(f"{args.output} is stale; run: uv run --locked python -m tools.map_district_partition")
            return 1
        print(f"{args.output} is up to date")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    print(f"wrote {args.output} ({len(text.encode())} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
