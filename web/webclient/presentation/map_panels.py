"""Exact version-1 ``area_map`` / ``world_map`` wire schemas and bounds.

The on-demand map panels (world-map drawer design §5.2/§5.3, OpenSpec change
define-map-panel-protocol) share one fixed wire contract between the server
publishers and the browser decoder. This module is that contract on the
server: schema versions, the closed vocabularies, the finite logical bounds
and the fail-closed validators. It is pure Python and never touches a
Session, an actor or persistent state; node identities are checked against
the canonical node-ID grammar only (no registry or database lookup), exactly
as the mirrored JavaScript validator in
``web/static/webclient/js/elosern/protocol/panels/map_panels.js`` does.

Bounds ownership: ``publish-area-map-panel`` measured real area graphs and
the 225-cell wilderness window and owns the area numbers below;
``transport-world-map-panel``
measures the continental payload and owns the world numbers. Each change
edits the constants here and in the JavaScript mirror together (a
bidirectional parity test pins them). Unrelated panels, including
``local_map`` and its 65,536-byte envelope, keep their own budgets.
"""

from __future__ import annotations

import math
import re
from typing import Any

from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_DEPTH,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    check_envelope,
    check_json_safety,
    json_byte_size,
)

AREA_MAP_PANEL = "area_map"
WORLD_MAP_PANEL = "world_map"
AREA_MAP_SCHEMA_VERSION = 1
WORLD_MAP_SCHEMA_VERSION = 1

#: The on-demand map panels and their registered schema versions. Only these
#: names may register as on-demand presenters, and they never ride an eager
#: snapshot.
MAP_PANEL_SCHEMAS: dict[str, int] = {
    AREA_MAP_PANEL: AREA_MAP_SCHEMA_VERSION,
    WORLD_MAP_PANEL: WORLD_MAP_SCHEMA_VERSION,
}

# Shared text bounds (reused from the local_map labels and titles).
MAP_MAX_LABEL = 256
MAP_MAX_TITLE = 128
MAP_MAX_NODE_ID = 128
MAP_MAX_EXIT_REF = 64
MAP_MAX_ID = 64
MAP_MAX_QUEST_ID = 64

# Coordinate envelope shared by every map frame (a transport bound, not a
# rendering bound): settlement metres, wilderness kilometres and continent
# kilometres all sit far inside it.
MAP_COORD_MIN = -10_000_000
MAP_COORD_MAX = 10_000_000

# Logical-body structural ceiling. A reassembled map body is not a wire frame:
# its lists may exceed the 320-item frame ceiling and are bounded instead by the
# exact per-collection limits below. Depth, field count, string length and
# scalar safety stay the generic ones.
MAP_MAX_LIST_ITEMS = 8_192
#: Envelope depth of a panel value (envelope -> panels -> panel).
MAP_PANEL_DEPTH = 2

# area_map bounds, measured by publish-area-map-panel (see
# docs/development/map-panel-protocol.md): the largest settlement graph is 21
# nodes / 26 roads (about 5 KB fully explored) and the wilderness window is at
# most 225 cells. The ceilings leave room for much larger settlements and
# room graphs: 512 nodes (2.3x the window), four roads per node, and a byte
# cap that holds that graph with 32-character labels and full markers.
AREA_MAX_NODES = 512
AREA_MAX_EDGES = 2_048
AREA_MAX_QUEST_MARKERS = 32
AREA_MAX_BYTES = 393_216
WILDERNESS_WINDOW = 15
WILDERNESS_MAX_NODES = WILDERNESS_WINDOW * WILDERNESS_WINDOW
AREA_MAX_CELL_KM = 1_000

# Measured production geometry plus the full 5 km checkerboard trail.
# The original 1 MiB measurement covered only a 20,000-run 1 km trail.
WORLD_MAX_BYTES = 2_097_152
WORLD_MAX_POLYGON_POINTS = 8_192
WORLD_MAX_POLYLINE_POINTS = 4_096
WORLD_MAX_BORDERS = 256
WORLD_MAX_NATIONS = 32
WORLD_MAX_DISTRICTS = 256
WORLD_MAX_OUTLINE_POLYGONS = 64
WORLD_MAX_TERRAIN_REGIONS = 64
WORLD_MAX_DISTRICT_POLYLINES = 256
WORLD_MAX_PLACES = 256
WORLD_MAX_DISTRICT_NATIONS = 8
WORLD_MAX_QUEST_MARKERS = 64
WORLD_APPROXIMATE_GRID_KM = 50
TRAIL_RESOLUTIONS = (1, 5)
#: Continental frame edge in 1 km cells (the published continent's frame size).
TRAIL_FRAME_CELLS = 2_700
TRAIL_MAX_RUNS = 20_000
TRAIL_DOWNSAMPLED_MAX_RUNS = 145_800

#: Logical byte ceiling per map panel (canonical UTF-8 JSON).
MAP_MAX_BYTES: dict[str, int] = {
    AREA_MAP_PANEL: AREA_MAX_BYTES,
    WORLD_MAP_PANEL: WORLD_MAX_BYTES,
}

AREA_LAYERS = ("grid", "instance", "interior", "wilderness")
AREA_VISIBILITIES = ("current", "visited", "seen")
AREA_ACTION_KINDS = ("move",)
AREA_FRAME_UNITS = {"grid": "m", "instance": "none", "interior": "none", "wilderness": "km"}
WILDERNESS_MAP_ID = "elosern"
PLACE_KINDS = ("capital", "settlement", "harbour", "hidden")

_NUMBER = r"(?:0|[1-9][0-9]*)"
#: Canonical node-ID grammar (ASCII-only, identical in JavaScript).
MAP_NODE_ID_RE = re.compile(
    rf"^(?:grid:[A-Za-z0-9_.-]{{1,64}}:{_NUMBER}:{_NUMBER}"
    rf"|wild:{WILDERNESS_MAP_ID}:{_NUMBER}:{_NUMBER}"
    r"|room:[1-9][0-9]*)$"
)
GRID_MAP_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
ROOM_GRAPH_MAP_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
MAP_ID_RE = re.compile(r"^[a-z0-9._]{1,64}$")
_EXIT_REF_RE = re.compile(r"^[\x00-\x7f]{1,64}$")


class MapPanelError(ProtocolValidationError):
    """A map panel payload violates its exact bounded schema."""


# ---------------------------------------------------------------------------
# Scalar helpers.
# ---------------------------------------------------------------------------


def _code_points(value: str) -> int:
    return sum(1 for _ in value)


def _exact(value: Any, name: str, fields: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MapPanelError(f"{name} must be a JSON object")
    keys = set(value)
    expected = set(fields)
    if keys != expected:
        unknown = sorted(keys - expected)
        missing = sorted(expected - keys)
        raise MapPanelError(f"{name} fields mismatch: unknown {unknown}, missing {missing}")
    return value


def _list(value: Any, name: str, *, minimum: int = 0, maximum: int) -> list[Any]:
    if not isinstance(value, list):
        raise MapPanelError(f"{name} must be a list")
    if not minimum <= len(value) <= maximum:
        raise MapPanelError(f"{name} must hold {minimum}..{maximum} entries")
    return value


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise MapPanelError(f"{name} must be a boolean")
    return value


def _int(value: Any, name: str, minimum: int, maximum: int) -> int:
    # JSON does not distinguish ``3`` from ``3.0``/``3e0`` and the browser
    # decodes all of them to the integer 3, so an integral finite float is
    # normalized to ``int`` here: both validators decide on the same wire text.
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        value = int(value)
    if isinstance(value, bool) or not isinstance(value, int):
        raise MapPanelError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise MapPanelError(f"{name} must be within {minimum}..{maximum}")
    return value


def _number(value: Any, name: str, minimum: float = MAP_COORD_MIN, maximum: float = MAP_COORD_MAX) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MapPanelError(f"{name} must be a number")
    if isinstance(value, float) and not math.isfinite(value):
        raise MapPanelError(f"{name} must be finite")
    if not minimum <= value <= maximum:
        raise MapPanelError(f"{name} must be within {minimum}..{maximum}")
    return value


def _text(value: Any, name: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise MapPanelError(f"{name} must be a string")
    if _code_points(value) > maximum or not value.strip():
        raise MapPanelError(f"{name} must be 1..{maximum} non-blank code points")
    return value


def _node_id(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) > MAP_MAX_NODE_ID or not MAP_NODE_ID_RE.fullmatch(value):
        raise MapPanelError(f"{name} is not a canonical node ID")
    return value


def _map_key(value: Any, name: str) -> str:
    if not isinstance(value, str) or not MAP_ID_RE.fullmatch(value):
        raise MapPanelError(f"{name} must be a 1..64 lowercase identifier")
    return value


def _unique(values: list[Any], name: str) -> None:
    if len(set(values)) != len(values):
        raise MapPanelError(f"{name} must be unique")


def _check_logical_body(payload: dict[str, Any], panel: str) -> None:
    """Generic scalar/structure safety plus the panel's logical byte ceiling."""
    try:
        check_json_safety(
            payload, depth=MAP_PANEL_DEPTH, max_depth=MAX_DEPTH, max_items=MAP_MAX_LIST_ITEMS
        )
    except ProtocolValidationError as error:
        raise MapPanelError(f"{panel} body is not JSON-safe: {error}") from error
    if json_byte_size(payload) > MAP_MAX_BYTES[panel]:
        raise MapPanelError(f"{panel} exceeds {MAP_MAX_BYTES[panel]} canonical bytes")


def _head(payload: Any, panel: str, fields: tuple[str, ...], version: int) -> dict[str, Any]:
    _exact(payload, f"{panel} panel", fields)
    if _int(payload["schema_version"], "schema_version", 1, MAX_SAFE_INTEGER) != version:
        raise MapPanelError(f"unsupported {panel} schema_version")
    if payload["available"] is not True:
        raise MapPanelError(f"available must be true for the {panel} form")
    return payload


# ---------------------------------------------------------------------------
# area_map.
# ---------------------------------------------------------------------------

_AREA_COMMON_FIELDS = (
    "schema_version",
    "available",
    "layer",
    "map_id",
    "frame",
    "current_node",
    "title",
    "nodes",
    "edges",
    "quest_markers",
)
_AREA_WILDERNESS_FIELDS = _AREA_COMMON_FIELDS + ("district_name", "cell_km")


def _area_gateway(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    _exact(value, "gateway", ("leads_to",))
    return {"leads_to": _text(value["leads_to"], "gateway.leads_to", MAP_MAX_LABEL)}


def _area_action(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    _exact(value, "action", ("kind", "exit_ref", "destination"))
    if value["kind"] not in AREA_ACTION_KINDS:
        raise MapPanelError("action.kind is not a stable value")
    exit_ref = value["exit_ref"]
    if not isinstance(exit_ref, str) or not _EXIT_REF_RE.fullmatch(exit_ref):
        raise MapPanelError(f"action.exit_ref must be 1..{MAP_MAX_EXIT_REF} ASCII characters")
    return {
        "kind": value["kind"],
        "exit_ref": exit_ref,
        "destination": _node_id(value["destination"], "action.destination"),
    }


def _area_node(value: Any, layer: str) -> dict[str, Any]:
    if layer == "grid":
        fields = ("id", "label", "x", "y", "visibility", "gateway", "action")
    elif layer == "wilderness":
        fields = ("id", "label", "x", "y", "visibility", "visited", "gateway", "action")
    else:
        fields = ("id", "label", "visibility", "gateway", "action")
    _exact(value, "node", fields)
    node: dict[str, Any] = {
        "id": _node_id(value["id"], "node.id"),
        "label": _text(value["label"], "node.label", MAP_MAX_LABEL),
    }
    if layer == "grid":
        node["x"] = _int(value["x"], "node.x", MAP_COORD_MIN, MAP_COORD_MAX)
        node["y"] = _int(value["y"], "node.y", MAP_COORD_MIN, MAP_COORD_MAX)
    elif layer == "wilderness":
        node["x"] = _number(value["x"], "node.x")
        node["y"] = _number(value["y"], "node.y")
    if value["visibility"] not in AREA_VISIBILITIES:
        raise MapPanelError("node.visibility is not a stable value")
    node["visibility"] = value["visibility"]
    if layer == "wilderness":
        node["visited"] = _bool(value["visited"], "node.visited")
        if node["visibility"] == "current" and not node["visited"]:
            raise MapPanelError("the current wilderness node must be visited")
    node["gateway"] = _area_gateway(value["gateway"])
    node["action"] = _area_action(value["action"])
    return node


def _area_marker(value: Any) -> dict[str, Any]:
    _exact(value, "quest marker", ("id", "title", "tracked", "destination"))
    destination = value["destination"]
    if not isinstance(destination, dict) or "kind" not in destination:
        raise MapPanelError("quest marker destination must be a tagged object")
    if destination["kind"] == "node":
        _exact(destination, "node destination", ("kind", "node_id"))
        normalized = {"kind": "node", "node_id": _node_id(destination["node_id"], "destination.node_id")}
    elif destination["kind"] == "bearing":
        _exact(destination, "bearing destination", ("kind", "bearing_deg", "distance_km"))
        bearing = _number(destination["bearing_deg"], "destination.bearing_deg", 0, 360)
        if bearing >= 360:
            raise MapPanelError("destination.bearing_deg must be below 360")
        normalized = {
            "kind": "bearing",
            "bearing_deg": bearing,
            "distance_km": _number(destination["distance_km"], "destination.distance_km", 0),
        }
    else:
        raise MapPanelError("quest marker destination kind is not a stable value")
    return {
        "id": _text(value["id"], "quest marker id", MAP_MAX_QUEST_ID),
        "title": _text(value["title"], "quest marker title", MAP_MAX_TITLE),
        "tracked": _bool(value["tracked"], "quest marker tracked"),
        "destination": normalized,
    }


def validate_area_map(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``area_map`` payload (raises MapPanelError)."""
    if not isinstance(payload, dict):
        raise MapPanelError("area_map panel must be a JSON object")
    layer = payload.get("layer")
    if layer not in AREA_LAYERS:
        raise MapPanelError("area_map layer is not a stable value")
    fields = _AREA_WILDERNESS_FIELDS if layer == "wilderness" else _AREA_COMMON_FIELDS
    _head(payload, AREA_MAP_PANEL, fields, AREA_MAP_SCHEMA_VERSION)

    map_id = payload["map_id"]
    if layer == "wilderness":
        if map_id != WILDERNESS_MAP_ID:
            raise MapPanelError("a wilderness area_map must use the continental map_id")
    elif layer == "grid":
        if not isinstance(map_id, str) or not GRID_MAP_ID_RE.fullmatch(map_id):
            raise MapPanelError("a grid map_id must be a canonical z-map key")
    elif not isinstance(map_id, str) or not ROOM_GRAPH_MAP_ID_RE.fullmatch(map_id):
        raise MapPanelError("an instance/interior map_id must be a stable bounded identity")
    _exact(payload["frame"], "frame", ("key", "unit"))
    if payload["frame"]["key"] != map_id:
        raise MapPanelError("frame.key must equal map_id")
    if payload["frame"]["unit"] != AREA_FRAME_UNITS[layer]:
        raise MapPanelError(f"frame.unit must be {AREA_FRAME_UNITS[layer]!r} for {layer}")

    current = _node_id(payload["current_node"], "current_node")
    title = _text(payload["title"], "title", MAP_MAX_TITLE)
    limit = WILDERNESS_MAX_NODES if layer == "wilderness" else AREA_MAX_NODES
    nodes = [_area_node(item, layer) for item in _list(payload["nodes"], "nodes", minimum=1, maximum=limit)]
    ids = [node["id"] for node in nodes]
    _unique(ids, "node ids")
    current_rows = [node for node in nodes if node["visibility"] == "current"]
    if len(current_rows) != 1 or current_rows[0]["id"] != current:
        raise MapPanelError("exactly one node must be current and equal current_node")
    for node in nodes:
        node_id = node["id"]
        if layer == "grid" and not node_id.startswith(f"grid:{map_id}:"):
            raise MapPanelError("grid area nodes must belong to the declared map")
        if layer in ("instance", "interior") and not node_id.startswith("room:"):
            raise MapPanelError("instance/interior area nodes must be rooms")
        if layer == "wilderness" and not node_id.startswith("wild:") and node["gateway"] is None:
            raise MapPanelError("a non-wilderness node in the wilderness window must be a gateway")
    if layer == "wilderness" and not current.startswith("wild:"):
        raise MapPanelError("a wilderness area_map must have a wild current node")

    known = set(ids)
    edges = []
    for item in _list(payload["edges"], "edges", maximum=AREA_MAX_EDGES):
        _exact(item, "edge", ("source", "destination"))
        source = _node_id(item["source"], "edge.source")
        destination = _node_id(item["destination"], "edge.destination")
        if source == destination:
            raise MapPanelError("an edge must connect two distinct nodes")
        if source not in known or destination not in known:
            raise MapPanelError("an edge must reference presented nodes")
        edges.append({"source": source, "destination": destination})
    _unique([(edge["source"], edge["destination"]) for edge in edges], "edges")

    markers = [
        _area_marker(item)
        for item in _list(payload["quest_markers"], "quest_markers", maximum=AREA_MAX_QUEST_MARKERS)
    ]
    _unique([marker["id"] for marker in markers], "quest marker ids")

    result: dict[str, Any] = {
        "schema_version": AREA_MAP_SCHEMA_VERSION,
        "available": True,
        "layer": layer,
        "map_id": map_id,
        "frame": {"key": map_id, "unit": AREA_FRAME_UNITS[layer]},
        "current_node": current,
        "title": title,
        "nodes": nodes,
        "edges": edges,
        "quest_markers": markers,
    }
    if layer == "wilderness":
        result["district_name"] = _text(payload["district_name"], "district_name", MAP_MAX_TITLE)
        cell_km = _number(payload["cell_km"], "cell_km", 0, AREA_MAX_CELL_KM)
        if cell_km <= 0:
            raise MapPanelError("cell_km must be positive")
        result["cell_km"] = cell_km
    _check_logical_body(result, AREA_MAP_PANEL)
    return result


# ---------------------------------------------------------------------------
# world_map.
# ---------------------------------------------------------------------------


def _point(value: Any, name: str) -> list[float | int]:
    if not isinstance(value, list) or len(value) != 2:
        raise MapPanelError(f"{name} must be an [x, y] pair")
    return [_number(value[0], f"{name}.x"), _number(value[1], f"{name}.y")]


def _polyline(value: Any, name: str) -> list[list[float | int]]:
    points = _list(value, name, minimum=2, maximum=WORLD_MAX_POLYLINE_POINTS)
    return [_point(point, name) for point in points]


def _signed_area(points: list[list[float | int]]) -> float:
    total = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        total += x0 * y1 - x1 * y0
    return total / 2.0


def _polygon(value: Any, name: str) -> list[list[float | int]]:
    points = [_point(point, name) for point in _list(value, name, minimum=4, maximum=WORLD_MAX_POLYGON_POINTS)]
    if points[0] != points[-1]:
        raise MapPanelError(f"{name} must be closed (first point equals last)")
    if _signed_area(points) == 0:
        raise MapPanelError(f"{name} must enclose a nonzero area")
    return points


def _outline(value: Any, name: str) -> list[list[list[float | int]]]:
    """A list of closed rings: counter-clockwise outer rings, clockwise holes."""
    rings = [_polygon(ring, name) for ring in _list(value, name, minimum=1, maximum=WORLD_MAX_OUTLINE_POLYGONS)]
    if not any(_signed_area(ring) > 0 for ring in rings):
        raise MapPanelError(f"{name} needs at least one counter-clockwise outer ring")
    return rings


def _place(value: Any, name: str) -> dict[str, Any]:
    _exact(value, name, ("id", "name", "kind", "x", "y"))
    if value["kind"] not in PLACE_KINDS:
        raise MapPanelError(f"{name}.kind is not a stable value")
    return {
        "id": _map_key(value["id"], f"{name}.id"),
        "name": _text(value["name"], f"{name}.name", MAP_MAX_LABEL),
        "kind": value["kind"],
        "x": _number(value["x"], f"{name}.x"),
        "y": _number(value["y"], f"{name}.y"),
    }


def _places(value: Any, name: str) -> list[dict[str, Any]]:
    rows = [_place(row, name) for row in _list(value, name, maximum=WORLD_MAX_PLACES)]
    _unique([row["id"] for row in rows], f"{name} ids")
    return rows


def _common(value: Any) -> dict[str, Any]:
    _exact(value, "common", ("coastline", "borders", "nations"))
    nations = []
    for row in _list(value["nations"], "common.nations", maximum=WORLD_MAX_NATIONS):
        _exact(row, "nation", ("id", "name", "x", "y"))
        nations.append(
            {
                "id": _map_key(row["id"], "nation.id"),
                "name": _text(row["name"], "nation.name", MAP_MAX_LABEL),
                "x": _number(row["x"], "nation.x"),
                "y": _number(row["y"], "nation.y"),
            }
        )
    _unique([row["id"] for row in nations], "nation ids")
    return {
        "coastline": _polygon(value["coastline"], "common.coastline"),
        "borders": [
            _polyline(line, "common.borders")
            for line in _list(value["borders"], "common.borders", maximum=WORLD_MAX_BORDERS)
        ],
        "nations": nations,
    }


def _lines(value: Any, name: str) -> list[list[list[float | int]]]:
    return [_polyline(line, name) for line in _list(value, name, maximum=WORLD_MAX_DISTRICT_POLYLINES)]


def _district(value: Any, nation_ids: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MapPanelError("district must be a JSON object")
    lit = value.get("lit")
    if lit is False:
        _exact(value, "unlit district", ("id", "lit", "outline"))
        return {
            "id": _map_key(value["id"], "district.id"),
            "lit": False,
            "outline": _outline(value["outline"], "district.outline"),
        }
    if lit is not True:
        raise MapPanelError("district.lit must be a boolean discriminator")
    _exact(
        value,
        "lit district",
        ("id", "lit", "name", "outline", "landmark", "nations", "terrain", "rivers", "ridge", "roads", "places"),
    )
    landmark = _exact(value["landmark"], "landmark", ("name", "x", "y"))
    nations = [
        _map_key(item, "district.nations")
        for item in _list(value["nations"], "district.nations", maximum=WORLD_MAX_DISTRICT_NATIONS)
    ]
    _unique(nations, "district nations")
    if not set(nations) <= nation_ids:
        raise MapPanelError("district.nations must name common nations")
    terrain = []
    for row in _list(value["terrain"], "district.terrain", maximum=WORLD_MAX_TERRAIN_REGIONS):
        _exact(row, "terrain", ("region", "polygons"))
        terrain.append(
            {
                "region": _map_key(row["region"], "terrain.region"),
                "polygons": _outline(row["polygons"], "terrain.polygons"),
            }
        )
    return {
        "id": _map_key(value["id"], "district.id"),
        "lit": True,
        "name": _text(value["name"], "district.name", MAP_MAX_LABEL),
        "outline": _outline(value["outline"], "district.outline"),
        "landmark": {
            "name": _text(landmark["name"], "landmark.name", MAP_MAX_LABEL),
            "x": _number(landmark["x"], "landmark.x"),
            "y": _number(landmark["y"], "landmark.y"),
        },
        "nations": nations,
        "terrain": terrain,
        "rivers": _lines(value["rivers"], "district.rivers"),
        "ridge": _lines(value["ridge"], "district.ridge"),
        "roads": _lines(value["roads"], "district.roads"),
        "places": _places(value["places"], "district.places"),
    }


def _trail(value: Any) -> dict[str, Any]:
    _exact(value, "trail", ("resolution_km", "rows"))
    resolution = _int(value["resolution_km"], "trail.resolution_km", 1, 5)
    if resolution not in TRAIL_RESOLUTIONS:
        raise MapPanelError("trail.resolution_km must be 1 or 5")
    cells = -(-TRAIL_FRAME_CELLS // resolution)
    rows = []
    previous_row = -1
    total_runs = 0
    for row in _list(value["rows"], "trail.rows", maximum=cells):
        if not isinstance(row, list) or len(row) != 2:
            raise MapPanelError("trail row must be [row_index, runs]")
        row_index = _int(row[0], "trail row index", 0, cells - 1)
        if row_index <= previous_row:
            raise MapPanelError("trail rows must be strictly increasing")
        previous_row = row_index
        runs = []
        end = -1
        for run in _list(row[1], "trail runs", minimum=1, maximum=cells):
            if not isinstance(run, list) or len(run) != 2:
                raise MapPanelError("trail run must be [start_column, length]")
            start = _int(run[0], "trail run start", 0, cells - 1)
            length = _int(run[1], "trail run length", 1, cells)
            if start < end:
                raise MapPanelError("trail runs must be sorted and non-overlapping")
            end = start + length
            if end > cells:
                raise MapPanelError("trail run exceeds the trail grid")
            runs.append([start, length])
        total_runs += len(runs)
        rows.append([row_index, runs])
    maximum_runs = TRAIL_MAX_RUNS if resolution == 1 else TRAIL_DOWNSAMPLED_MAX_RUNS
    if total_runs > maximum_runs:
        raise MapPanelError(f"trail exceeds {maximum_runs} runs")
    return {"resolution_km": resolution, "rows": rows}


def _world_marker(value: Any) -> dict[str, Any]:
    _exact(value, "world quest marker", ("id", "title", "tracked", "x", "y", "approximate"))
    approximate = _bool(value["approximate"], "quest marker approximate")
    x = _number(value["x"], "quest marker x")
    y = _number(value["y"], "quest marker y")
    if approximate:
        # Integral values only (an integral float such as 100.0 normalizes).
        x = _int(x, "quest marker x", MAP_COORD_MIN, MAP_COORD_MAX)
        y = _int(y, "quest marker y", MAP_COORD_MIN, MAP_COORD_MAX)
        if x % WORLD_APPROXIMATE_GRID_KM or y % WORLD_APPROXIMATE_GRID_KM:
            raise MapPanelError("an approximate marker must sit on the 50 km grid")
    return {
        "id": _text(value["id"], "quest marker id", MAP_MAX_QUEST_ID),
        "title": _text(value["title"], "quest marker title", MAP_MAX_TITLE),
        "tracked": _bool(value["tracked"], "quest marker tracked"),
        "x": x,
        "y": y,
        "approximate": approximate,
    }


def validate_world_map(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``world_map`` payload (raises MapPanelError)."""
    _head(
        payload,
        WORLD_MAP_PANEL,
        (
            "schema_version",
            "available",
            "common",
            "districts",
            "trail",
            "visited_places",
            "current",
            "quest_markers",
        ),
        WORLD_MAP_SCHEMA_VERSION,
    )
    common = _common(payload["common"])
    nation_ids = {row["id"] for row in common["nations"]}
    districts = [
        _district(item, nation_ids)
        for item in _list(payload["districts"], "districts", maximum=WORLD_MAX_DISTRICTS)
    ]
    _unique([district["id"] for district in districts], "district ids")
    current = _exact(payload["current"], "current", ("x", "y"))
    markers = [
        _world_marker(item)
        for item in _list(payload["quest_markers"], "quest_markers", maximum=WORLD_MAX_QUEST_MARKERS)
    ]
    _unique([marker["id"] for marker in markers], "quest marker ids")
    result = {
        "schema_version": WORLD_MAP_SCHEMA_VERSION,
        "available": True,
        "common": common,
        "districts": districts,
        "trail": _trail(payload["trail"]),
        "visited_places": _places(payload["visited_places"], "visited_places"),
        "current": {"x": _number(current["x"], "current.x"), "y": _number(current["y"], "current.y")},
        "quest_markers": markers,
    }
    _check_logical_body(result, WORLD_MAP_PANEL)
    return result


#: The largest intact ``ui_update`` frame carrying a world map: the generic
#: frame budget for everything else plus the world map's logical ceiling.
WORLD_MAP_FRAME_MAX_BYTES = MAX_CANONICAL_JSON_BYTES + WORLD_MAX_BYTES


def carries_intact_world_map(envelope: Any) -> bool:
    """Whether a frame claims the scoped world-map allowance.

    True only for an envelope object whose ``panels`` object holds a
    ``world_map`` object that is not a bounded part. Every other frame
    (snapshots, parts, other panels) takes the generic envelope check. The
    browser uses the same predicate (``carriesIntactWorldMap``).
    """
    if not isinstance(envelope, dict):
        return False
    panels = envelope.get("panels")
    if not isinstance(panels, dict):
        return False
    body = panels.get(WORLD_MAP_PANEL)
    return isinstance(body, dict) and "part" not in body


def check_world_map_envelope(envelope: Any) -> dict[str, Any]:
    """Check one intact ``ui_update`` frame under the world-map allowance.

    The world map is the only value exempt from the generic frame budget.
    The rest of the envelope, with the world map replaced by ``null``, passes
    the unchanged generic check: metadata and every sibling panel (including
    ``local_map`` and ``area_map``) keep the 65,536-byte, 320-item, depth and
    string bounds. The world map itself must pass its exact schema, the
    generic scalar rules and its logical byte ceiling. Returns the validated
    world-map body; raises :class:`ProtocolValidationError` otherwise.
    """
    if not carries_intact_world_map(envelope):
        raise MapPanelError("the world-map allowance needs an intact world_map panel")
    panels = dict(envelope["panels"])
    body = panels[WORLD_MAP_PANEL]
    panels[WORLD_MAP_PANEL] = None
    remainder = {**envelope, "panels": panels}
    check_envelope(remainder)
    if json_byte_size(remainder) > MAX_CANONICAL_JSON_BYTES:
        raise JSONSafetyError(
            f"world-map remainder canonical JSON exceeds generic {MAX_CANONICAL_JSON_BYTES} bytes"
        )
    return validate_map_panel(WORLD_MAP_PANEL, body)


_VALIDATORS = {AREA_MAP_PANEL: validate_area_map, WORLD_MAP_PANEL: validate_world_map}


def validate_map_panel(name: str, payload: Any) -> dict[str, Any]:
    """Validate one logical map panel: its available form or the common unavailable form."""
    if name not in MAP_PANEL_SCHEMAS:
        raise MapPanelError(f"{name!r} is not an on-demand map panel")
    if isinstance(payload, dict) and payload.get("available") is False:
        from web.webclient.presentation.protocol import _validate_correlation_id, _validate_identifier, _validate_message

        _exact(payload, f"{name} panel", ("schema_version", "available", "reason"))
        if _int(payload["schema_version"], "schema_version", 1, MAX_SAFE_INTEGER) != MAP_PANEL_SCHEMAS[name]:
            raise MapPanelError(f"unsupported {name} schema_version")
        reason = payload["reason"]
        if not isinstance(reason, dict):
            raise MapPanelError("reason must be a JSON object")
        fields = ("code", "message", "correlation_id") if "correlation_id" in reason else ("code", "message")
        _exact(reason, "reason", fields)
        _validate_identifier(reason["code"], "reason.code")
        _validate_message(reason["message"], "reason.message")
        if "correlation_id" in reason:
            _validate_correlation_id(reason["correlation_id"])
        return payload
    return _VALIDATORS[name](payload)
