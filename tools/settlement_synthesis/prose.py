"""The read-only prose brief and the key/description-only prose application.

The brief is the machine-readable starting point for an agent prose writer: it
describes every node, its role and where it stands, plus the settlement's site.
It never writes. The prose command applies ``{"<node_id>": {"key", "desc"}}``
and changes nothing else: unknown identities, empty text and extra fields are
collected first, and a refused run leaves the document byte-identical.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from typing import Any

from elosern_map_core.codec import (
    document_from_data,
    parse_document,
    serialize_document,
)

from tools.settlement_synthesis.generate import (
    morphology_of,
    settlement_class_of,
)
from tools.settlement_synthesis.geometry import bearing
from tools.settlement_synthesis.rework import ReworkError
from tools.settlement_synthesis.roles import RoleEntry
from tools.settlement_synthesis.workspace import (
    WorkspaceError,
    WorkspaceView,
    analysis_input,
    settlement_path,
    write_atomic,
)

#: An approach street the generator emits: ``<gate>_gate_road_<n>``.
_APPROACH = re.compile(r"[a-z]+_gate_road_\d+")

#: A filler lane the generator emits.
_LANE = re.compile(r"lane_\d+")


def role_of(
    node_id: str,
    document: Any,
    catalogue: Sequence[RoleEntry],
) -> str:
    """The plan role one authored node id carries, for review."""

    anchor = document.anchor_node
    if anchor is not None and node_id == anchor.node_id:
        return "anchor"
    entry = document.wilderness_entry
    if entry is not None and any(
        gate.destination_node == node_id for gate in entry.gates
    ):
        return "gate"
    for role in catalogue:
        if node_id == role.slot_id or re.fullmatch(
            re.escape(role.slot_id) + r"_\d+", node_id
        ):
            return role.slot_id
    if _APPROACH.fullmatch(node_id):
        return "approach"
    if node_id == "ford_crossing":
        return "crossing"
    if _LANE.fullmatch(node_id):
        return "filler"
    return "authored"


def build_brief(view: WorkspaceView, map_id: str) -> dict[str, Any]:
    """The prose brief for one settlement map, without writing anything."""

    document = view.world.settlements.get(map_id)
    if document is None:
        raise WorkspaceError(f"unknown map {map_id!r}")
    location = view.location(document.location_ref)
    declaration = view.world.locations.locations[document.location_ref]
    generation = analysis_input(view, location, map_id=map_id)
    site = generation.site
    reach = math.ceil(math.sqrt(generation.budget.footprint_cells) / 2) + 1

    water: list[dict[str, Any]] = []
    for contact in site.rivers:
        if _within(site.cell, contact.nearest_cell, reach):
            water.append(_water_row(contact))
    if site.sea is not None and _within(site.cell, site.sea.nearest_cell, reach):
        water.append(_water_row(site.sea))

    neighbours: list[dict[str, Any]] = []
    for neighbour in site.neighbours:
        neighbour_declaration = view.world.locations.locations.get(
            neighbour.feature_id
        )
        if neighbour_declaration is None:
            continue
        neighbours.append(
            {
                "id": neighbour.feature_id,
                "display_name_zh": neighbour_declaration.display_name_zh,
                "bearing": neighbour.bearing,
                "distance_cells": neighbour.distance_cells,
            }
        )

    gate_returns: dict[str, str] = {}
    if document.wilderness_entry is not None:
        for gate in document.wilderness_entry.gates:
            gate_returns[gate.destination_node] = gate.return_direction

    anchor = document.local_anchor_m
    nodes: list[dict[str, Any]] = []
    for node_id, node in document.nodes.items():
        if anchor is None:
            node_bearing: str | None = None
            distance: float | None = None
        else:
            delta_x = node.x_m - anchor[0]
            delta_y = node.y_m - anchor[1]
            node_bearing = bearing(delta_x, delta_y)
            distance = math.hypot(delta_x, delta_y)
        nodes.append(
            {
                "id": node_id,
                "key": node.key,
                "role": role_of(node_id, document, generation.catalogue),
                "bearing": node_bearing,
                "distance_m": distance,
                "desc_empty": not node.desc.strip(),
                "gate_return_direction": gate_returns.get(node_id),
            }
        )

    return {
        "map_id": map_id,
        "location_id": location.location_id,
        "display_name_zh": declaration.display_name_zh,
        "kind": location.kind,
        "nation": location.nation,
        "population": location.population,
        "geographic_constraint": declaration.geographic_constraint,
        "settlement_class": settlement_class_of(generation),
        "morphology": morphology_of(generation),
        "water": water,
        "uphill": site.uphill,
        "neighbours": neighbours,
        "nodes": nodes,
    }


def apply_prose(
    view: WorkspaceView, map_id: str, entries: Mapping[str, Mapping[str, Any]]
) -> int:
    """Replace only the ``key`` and ``desc`` of the listed nodes; return the count."""

    path = settlement_path(view.root, map_id)
    if not path.is_file():
        raise WorkspaceError(f"unknown map {map_id!r}")
    text = path.read_text(encoding="utf-8")
    parsed = parse_document(f"content/maps/settlements/{map_id}.yaml", text)
    source = parsed.document.data
    data = dict(source)
    data["nodes"] = {
        node_id: dict(node) for node_id, node in source["nodes"].items()
    }
    nodes = data["nodes"]

    problems: list[str] = []
    for node_id, fields in entries.items():
        if node_id not in nodes:
            problems.append(f"unknown_node:{node_id}")
            continue
        if not isinstance(fields, Mapping):
            raise ValueError(f"{node_id}: the prose entry must be a JSON object")
        for field in fields:
            if field not in ("key", "desc"):
                problems.append(f"unexpected_field:{node_id}:{field}")
        key = fields.get("key")
        desc = fields.get("desc")
        if not isinstance(key, str) or not key.strip():
            problems.append(f"empty_key:{node_id}")
        if not isinstance(desc, str) or not desc.strip():
            problems.append(f"empty_desc:{node_id}")
    if problems:
        raise ReworkError(problems)

    for node_id, fields in entries.items():
        nodes[node_id]["key"] = fields["key"]
        nodes[node_id]["desc"] = fields["desc"]
    document = document_from_data(parsed.relative_path, data)
    write_atomic(path, serialize_document(document, parsed.round_trip))
    return len(entries)


def _within(left: tuple[int, int], right: tuple[int, int], reach: int) -> bool:
    return max(
        abs(left[0] - right[0]), abs(left[1] - right[1])
    ) <= reach


def _water_row(contact: Any) -> dict[str, Any]:
    return {
        "kind": contact.kind,
        "name": contact.name,
        "bearing": contact.bearing,
        "distance_cells": contact.distance_cells,
    }


__all__ = ["apply_prose", "build_brief", "role_of"]
