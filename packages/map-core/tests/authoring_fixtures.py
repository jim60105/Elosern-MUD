"""Shared synthetic authoring fixtures for package mechanism tests.

No shipped world data is read or pinned: every document here is a small
synthetic candidate built from fixed inputs.
"""

from __future__ import annotations

import copy
from io import StringIO
from collections.abc import Mapping

from ruamel.yaml import YAML

from elosern_map_core.authoring import (
    AuthoritativeExternalResult,
    PartitionFreshness,
    compile_runtime,
    load_authoring_world,
)
from elosern_map_core.codec import document_from_data, parse_document
from elosern_map_core.sources import make_source_document
from elosern_map_core.terrain import REGION_KEYS

CONTINENT_PATH = "content/maps/continent.yaml"
LOCATIONS_PATH = "content/maps/locations.yaml"
DISTRICTS_PATH = "content/maps/districts.yaml"
SETTLEMENT_PATH = "content/maps/settlements/demo_map.yaml"


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
            "forest_edge": [
                {"cell_x": 0, "cell_y": 30},
                {"cell_x": 39, "cell_y": 30},
            ],
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
                "border_river": {
                    "route": [
                        {"cell_x": 20, "cell_y": 20},
                        {"cell_x": 0, "cell_y": 20},
                    ],
                    "fords": [{"cell_x": 10, "cell_y": 20}],
                }
            },
            "border_river_key": "border_river",
        },
    }


def locations_data() -> dict:
    return {
        "version": 1,
        "kind": "locations",
        "id": "locations",
        "locations": {
            "demo_location": {
                "kind": "capital",
                "display_name_zh": "示範城",
                "description": "A synthetic city.",
                "cell": {"cell_x": 5, "cell_y": 5},
                "geographic_constraint": "synthetic",
                "scene_archetype": None,
            }
        },
    }


def districts_data() -> dict:
    return {
        "version": 1,
        "kind": "districts",
        "id": "districts",
        "districts": {
            "demo_district": {
                "district_name_zh": "示範區",
                "landmark_name_zh": "示範地標",
                "landmark": {
                    "domain": "settlement_node",
                    "map_id": "demo_map",
                    "object_id": "plaza",
                    "cell": None,
                },
                "kind": "voronoi",
                "region_key": None,
            }
        },
    }


def settlement_data(
    *,
    nodes: dict | None = None,
    roads: list | None = None,
    entry: dict | None | bool = True,
) -> dict:
    if nodes is None:
        nodes = {
            "gate": {
                "x_m": 0,
                "y_m": 0,
                "prototype_parent": "anchor_room",
                "key": "Gate",
                "desc": "The way in.",
                "anchor_key": "demo_location",
                "typeclass": None,
                "scene_archetype": "city_street",
            },
            "plaza": {
                "x_m": 100,
                "y_m": 0,
                "prototype_parent": "grid_room",
                "key": "Plaza",
                "desc": "The middle of town.\nA second line of prose.",
                "anchor_key": None,
                "typeclass": None,
                "scene_archetype": None,
            },
        }
    if roads is None:
        roads = [
            {
                "source": "gate",
                "destination": "plaza",
                "direction": "e",
                "bends": [{"x_m": 50, "y_m": 10}],
            },
            {
                "source": "plaza",
                "destination": "gate",
                "direction": "w",
                "bends": [],
            },
        ]
    if entry is False:
        entry = None
    elif entry is True:
        entry = {
            "shape": ["#"],
            "origin": {"cell_x": 5, "cell_y": 5},
            "gates": [{"return_direction": "n", "destination_node": "gate"}],
        }
    return {
        "version": 1,
        "kind": "settlement",
        "id": "demo_map",
        "location_ref": "demo_location",
        "binding": {
            "anchor_cell": {"cell_x": 5, "cell_y": 5},
            "local_anchor_m": {"east_m": 0, "north_m": 0},
        },
        "options": {"map_visual_range": 2, "map_mode": "nodes"},
        "exit_prototype": {
            "prototype_parent": "xyz_exit",
            "typeclass": "tests.Exit",
        },
        "nodes": nodes,
        "roads": roads,
        "wilderness_entry": entry,
        "city_gate": {"node": "gate", "exit_key": "Gate", "exit_aliases": ["gate"]},
    }


def yaml_text(data: dict) -> str:
    dumper = YAML(typ="rt", pure=True)
    output = StringIO()
    dumper.dump(copy.deepcopy(data), output)
    return output.getvalue()


def plain_data(value):
    """Copy a frozen typed value tree to plain Python data."""

    if isinstance(value, Mapping):
        return {str(key): plain_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain_data(item) for item in value]
    return value


def source_documents(**settlement_overrides):
    return (
        make_source_document(CONTINENT_PATH, yaml_text(continent_data())),
        make_source_document(LOCATIONS_PATH, yaml_text(locations_data())),
        make_source_document(DISTRICTS_PATH, yaml_text(districts_data())),
        make_source_document(
            SETTLEMENT_PATH,
            yaml_text(settlement_data(**settlement_overrides)),
        ),
    )


def custom_sources(
    *,
    continent: dict | None = None,
    locations: dict | None = None,
    districts: dict | None = None,
    settlement: dict | None = None,
    interiors: dict | None = None,
):
    documents = [
        make_source_document(
            CONTINENT_PATH, yaml_text(continent if continent is not None else continent_data())
        ),
        make_source_document(
            LOCATIONS_PATH, yaml_text(locations if locations is not None else locations_data())
        ),
        make_source_document(
            DISTRICTS_PATH, yaml_text(districts if districts is not None else districts_data())
        ),
    ]
    if settlement is not None:
        documents.append(make_source_document(SETTLEMENT_PATH, yaml_text(settlement)))
    for interior_id, data in (interiors or {}).items():
        documents.append(
            make_source_document(
                f"content/maps/interiors/{interior_id}.yaml",
                yaml_text(data),
            )
        )
    return tuple(documents)


def interior_data(interior_id: str = "demo_interior") -> dict:
    return {
        "version": 1,
        "kind": "interior",
        "id": interior_id,
        "rooms": {
            "hall": {"name_zh": "大廳", "desc_zh": "A hall.", "scene_archetype": None},
            "inner": {"name_zh": "內室", "desc_zh": "An inner room.", "scene_archetype": None},
        },
        "connections": [
            {"source": "hall", "destination": "inner", "label": "in"},
            {"source": "inner", "destination": "hall", "label": "out"},
        ],
        "interior_links": [],
        "exterior": {
            "settlement": "demo_map",
            "node": "plaza",
            "room": "hall",
            "doorway_key": "Door",
            "doorway_aliases": ["door"],
        },
    }


def loaded_world(**settlement_overrides):
    return load_authoring_world(source_documents(**settlement_overrides))


def valid_external(world) -> AuthoritativeExternalResult:
    return AuthoritativeExternalResult(
        version=1,
        fingerprint="external-evidence",
        world_fingerprint=world.fingerprint,
        valid=True,
    )


def current_freshness(world) -> PartitionFreshness:
    return PartitionFreshness(
        algorithm_version=1,
        input_signature=world.partition_signature,
        current=True,
    )


def compiled_snapshot(**settlement_overrides):
    world = loaded_world(**settlement_overrides)
    return compile_runtime(world, valid_external(world), current_freshness(world))


def settlement_document(**overrides):
    return document_from_data(SETTLEMENT_PATH, settlement_data(**overrides))


def parsed_settlement_text(text: str):
    return parse_document(SETTLEMENT_PATH, text)
