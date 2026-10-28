"""A small synthetic workspace for editor mechanism tests.

No shipped world data is read or copied: every document is a fixed synthetic
candidate. The module depends only on the standard library, ``ruamel.yaml``
and the core's region-key vocabulary, so both the editor's own tests and the repository's wrapper/browser tests can
load it by file path.

Independently known geometry (used by assertions, not recomputed here):

- the settlement binds local anchor (0, 0) to cell (5, 5), whose centre is
  (5500 m, 5500 m); node ``yard`` at local (300, 400) therefore sits at world
  (5800 m, 5900 m);
- the straight road ``gate>yard`` from (0, 0) to (300, 400) is 500 m long; the
  return road ``yard>gate`` bends at (300, 0) and is 400 + 300 = 700 m long.
"""

from __future__ import annotations

import copy
import hashlib
import json
from io import StringIO
from pathlib import Path

from elosern_map_core.terrain import REGION_KEYS
from ruamel.yaml import YAML

SETTLEMENT_ID = "synthetic_town"
INTERIOR_ID = "synthetic_hall"
LOCATION_ID = "synthetic_place"
BARE_LOCATION_ID = "synthetic_wilds"
#: Authored prose that must stay inert text in every consumer.
HOSTILE_DESC = '<img src="x" onerror="window.__mapEditorPwned=1"><script>window.__mapEditorPwned=2</script>'
#: A scene identifier that looks like a URL; it must never be fetched.
URL_LIKE_SCENE = "https://example.invalid/scene.png"



def continent_data() -> dict:
    return {
        "version": 1,
        "kind": "continent",
        "id": "continent",
        "frame_cells": 40,
        "cell_size_km": 1,
        "mainland_boundary_km": [
            {"east_km": 0, "north_km": 0},
            {"east_km": 40, "north_km": 0},
            {"east_km": 40, "north_km": 40},
            {"east_km": 0, "north_km": 40},
        ],
        "regions": {
            key: {
                "display_name_zh": f"region-{key}",
                "nation_key": None,
                "terrain_flavor_zh": [f"flavor-{key}", f"second-flavor-{key}"],
                "nominal_nation_keys": [],
                "scene_archetype": None,
            }
            for key in sorted(REGION_KEYS)
        },
        "harbor_sites": {},
        "terrain": {
            "forest_edge": [{"cell_x": 0, "cell_y": 30}, {"cell_x": 39, "cell_y": 30}],
            "ridge": {
                "base_x": 10,
                "period": 5,
                "step": 1,
                "min_x": 0,
                "max_x": 39,
                "north_limit_y": 35,
                "mountain_corridor_half_width": 2,
                "passes": [{"y_min": 4, "y_max": 5}],
            },
            "coastal_y_max": 10,
            "waterways": {
                "synthetic_river": {
                    "route": [{"cell_x": 20, "cell_y": 20}, {"cell_x": 0, "cell_y": 20}],
                    "fords": [{"cell_x": 10, "cell_y": 20}],
                }
            },
            "border_river_key": "synthetic_river",
        },
    }


def locations_data() -> dict:
    return {
        "version": 1,
        "kind": "locations",
        "id": "locations",
        "locations": {
            LOCATION_ID: {
                "kind": "capital",
                "display_name_zh": "合成城",
                "description": "A synthetic town.",
                "cell": {"cell_x": 5, "cell_y": 5},
                "geographic_constraint": "synthetic",
                "scene_archetype": None,
            },
            BARE_LOCATION_ID: {
                "kind": "dungeon",
                "display_name_zh": "合成荒野",
                "description": "A place with no local map.",
                "cell": {"cell_x": 30, "cell_y": 12},
                "geographic_constraint": "synthetic",
                "scene_archetype": None,
            },
        },
    }


def districts_data() -> dict:
    return {
        "version": 1,
        "kind": "districts",
        "id": "districts",
        "districts": {
            "synthetic_district": {
                "district_name_zh": "合成區",
                "landmark_name_zh": "合成地標",
                "landmark": {
                    "domain": "settlement_node",
                    "map_id": SETTLEMENT_ID,
                    "object_id": "yard",
                    "cell": None,
                },
                "kind": "voronoi",
                "region_key": None,
            }
        },
    }


def settlement_data() -> dict:
    return {
        "version": 1,
        "kind": "settlement",
        "id": SETTLEMENT_ID,
        "location_ref": LOCATION_ID,
        "binding": {
            "anchor_cell": {"cell_x": 5, "cell_y": 5},
            "local_anchor_m": {"east_m": 0, "north_m": 0},
        },
        "options": {"map_visual_range": 2, "map_mode": "nodes"},
        "exit_prototype": {"prototype_parent": "xyz_exit", "typeclass": "tests.Exit"},
        "nodes": {
            "gate": {
                "x_m": 0,
                "y_m": 0,
                "prototype_parent": "anchor_room",
                "key": "Gate",
                "desc": "The way in.",
                "anchor_key": LOCATION_ID,
                "typeclass": None,
                "scene_archetype": URL_LIKE_SCENE,
            },
            "yard": {
                "x_m": 300,
                "y_m": 400,
                "prototype_parent": "grid_room",
                "key": "Yard",
                "desc": HOSTILE_DESC,
                "anchor_key": None,
                "typeclass": None,
                "scene_archetype": None,
            },
        },
        "roads": [
            {"source": "gate", "destination": "yard", "direction": "ne", "bends": []},
            {"source": "yard", "destination": "gate", "direction": "s", "bends": [{"x_m": 300, "y_m": 0}]},
        ],
        "wilderness_entry": {
            "shape": ["#"],
            "origin": {"cell_x": 5, "cell_y": 5},
            "gates": [{"return_direction": "n", "destination_node": "gate"}],
        },
        "city_gate": {"node": "gate", "exit_key": "Gate", "exit_aliases": ["gate"]},
    }


def interior_data() -> dict:
    return {
        "version": 1,
        "kind": "interior",
        "id": INTERIOR_ID,
        "rooms": {
            "front": {"name_zh": "前廳", "desc_zh": "A synthetic front room.", "scene_archetype": None, "art_key": None},
            "back": {"name_zh": "後室", "desc_zh": "A synthetic back room.", "scene_archetype": None, "art_key": None},
        },
        "connections": [
            {"source": "front", "destination": "back", "label": "in"},
            {"source": "back", "destination": "front", "label": "out"},
        ],
        "interior_links": [],
        "exterior": {
            "settlement": SETTLEMENT_ID,
            "node": "yard",
            "room": "front",
            "doorway_key": "Door",
            "doorway_aliases": ["door"],
        },
    }


def yaml_text(data: dict) -> str:
    dumper = YAML(typ="rt", pure=True)
    output = StringIO()
    dumper.dump(copy.deepcopy(data), output)
    return output.getvalue()


DOCUMENTS = {
    "content/maps/continent.yaml": continent_data,
    "content/maps/locations.yaml": locations_data,
    "content/maps/districts.yaml": districts_data,
    f"content/maps/settlements/{SETTLEMENT_ID}.yaml": settlement_data,
    f"content/maps/interiors/{INTERIOR_ID}.yaml": interior_data,
}


def write_workspace(root: str | Path) -> Path:
    """Write the synthetic world sources under ``root`` and return it."""

    root = Path(root)
    for relative_path, factory in DOCUMENTS.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml_text(factory()), encoding="utf-8")
    return root


def write_reference_context(root: str | Path, *, rules: tuple[str, ...] = ("external/**/*.txt",)) -> Path:
    """Write one external source plus a current reference context for it."""

    root = Path(root)
    external = root / "external" / "declarations.txt"
    external.parent.mkdir(parents=True, exist_ok=True)
    external.write_text("synthetic external declaration\n", encoding="utf-8")
    manifest = {"external/declarations.txt": hashlib.sha256(external.read_bytes()).hexdigest()}
    digest = hashlib.sha256()
    digest.update(b"schema_version=1\n")
    digest.update(b"exporter_version=1\n")
    for rule in sorted(rules):
        digest.update(f"rule:{rule}\n".encode("utf-8"))
    for path, file_hash in sorted(manifest.items()):
        digest.update(f"{path}:{file_hash}\n".encode("utf-8"))
    document = {
        "schema_version": 1,
        "exporter_version": 1,
        "external_identifiers": {},
        "incoming_references": {},
        "source_manifest": manifest,
        "discovery_rules": list(rules),
        "fingerprint": digest.hexdigest(),
    }
    target = root / "content" / "map-reference-context.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def tree_digest(root: str | Path) -> dict[str, str]:
    """``{relative_path: sha256}`` of every regular file (unchanged-baseline checks)."""

    root = Path(root)
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


if __name__ == "__main__":  # pragma: no cover - manual helper
    import sys

    print(write_workspace(sys.argv[1]))
