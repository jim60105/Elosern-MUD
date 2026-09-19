"""Exact schema-version-1 ``local_map`` payload validator and shared bounds.

Holds the wire contract of the ``local_map`` panel: the schema version, the
exact shared bounds (design D10a), the closed vocabularies, the localized
legend labels, and the fail-closed payload validator. The presenter and the
four layer adapters live in the sibling modules of this package.

The payload shape and the exact shared bounds (design D10a) are mirrored by the
client validator in ``web/static/webclient/js/elosern/protocol.js`` and guarded
by a dual-direction parity test.
"""

from typing import Any

from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    json_byte_size,
)
from web.webclient.presentation.protocol_validation import (
    require_exit_ref,
    require_node_id_shape,
)
from world.rules.map_knowledge import decode_node

LOCAL_MAP_SCHEMA_VERSION = 1

# Exact shared bounds (design D10a) -- must stay equal in the JS validator.
MAX_NODES = 64
MAX_EDGES = 128
MAX_LEGEND = 16
MAX_STRING_CODE_POINTS = 256
MAX_TITLE_CODE_POINTS = 128
MAX_NODE_ID_CHARS = 128
MAX_EXIT_REF_CHARS = 64
COORD_MIN = -1024
COORD_MAX = 1024

VISIBILITIES = ("current", "visible_unvisited", "visible_visited", "remembered")
LAYERS = ("grid", "wilderness", "instance", "interior")
ACTION_KINDS = ("move",)

# Grid visual-range option bounds (sample-city-altoria).
MAX_GRID_VISUAL_RANGE = 8
GRID_MODES = ("nodes", "scan")

# Remembered-gateway ceiling (presenter-side only, design D6) -- deliberately
# NOT mirrored in web/static/webclient/js/elosern/protocol.js: it bounds the
# presenter's own candidate selection, not a payload field.
MAX_REMEMBERED_GATEWAYS = 16

# The eight wilderness cardinal directions (wilderness-map-provider).
WILD_DIRECTIONS = ("n", "ne", "e", "se", "s", "sw", "w", "nw")

# Stable localized legend labels explaining the visibility states.
LEGEND_LABELS = (
    "你目前所在的位置",
    "尚未探索的相鄰位置",
    "已經探索過的相鄰位置",
    "曾經到過、但不在附近的遠方位置",
)


class LocalMapError(ProtocolValidationError):
    """The available local_map payload violates its exact bounded schema."""


def _require_node_id(value: Any, field: str) -> str:
    require_node_id_shape(value, field, ProtocolValidationError, MAX_NODE_ID_CHARS)
    decode_node(value)
    return value


def _require_exit_ref(value: Any, field: str) -> str:
    return require_exit_ref(value, field, ProtocolValidationError)


def _require_coord(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolValidationError(f"{field} must be an integer")
    if not COORD_MIN <= value <= COORD_MAX:
        raise ProtocolValidationError(f"{field} must be within {COORD_MIN}..{COORD_MAX}")
    return value


def _validate_action(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    _require_exact_fields(value, "action", {"kind", "exit_ref", "destination"}, {})
    if value["kind"] not in ACTION_KINDS:
        raise ProtocolValidationError("action kind is not a stable value")
    _require_exit_ref(value["exit_ref"], "action.exit_ref")
    _require_node_id(value["destination"], "action.destination")
    return {
        "kind": value["kind"],
        "exit_ref": value["exit_ref"],
        "destination": value["destination"],
    }


def _validate_node(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "node",
        {"id", "label", "x", "y", "visibility", "current", "anchor", "landmark", "action"},
        {},
    )
    node_id = _require_node_id(value["id"], "node.id")
    label = _require_str(value, "label", maximum=MAX_STRING_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("node.label must be non-empty")
    x = _require_coord(value["x"], "node.x")
    y = _require_coord(value["y"], "node.y")
    visibility = value["visibility"]
    if visibility not in VISIBILITIES:
        raise ProtocolValidationError("node.visibility is not a stable value")
    current = _require_bool(value, "current")
    anchor = _require_bool(value, "anchor")
    landmark = _require_bool(value, "landmark")
    action = _validate_action(value["action"])
    if visibility == "current" and not current:
        raise ProtocolValidationError("the current node must carry current=True")
    if current and visibility != "current":
        raise ProtocolValidationError("a non-current node must not carry current=True")
    return {
        "id": node_id,
        "label": label,
        "x": x,
        "y": y,
        "visibility": visibility,
        "current": current,
        "anchor": anchor,
        "landmark": landmark,
        "action": action,
    }


def _validate_edge(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "edge",
        {"source", "destination", "label", "known", "traversable"},
        {},
    )
    source = _require_node_id(value["source"], "edge.source")
    destination = _require_node_id(value["destination"], "edge.destination")
    label = _require_str(value, "label", maximum=MAX_STRING_CODE_POINTS)
    known = _require_bool(value, "known")
    traversable = _require_bool(value, "traversable")
    if source == destination:
        raise ProtocolValidationError("an edge must connect two distinct nodes")
    return {
        "source": source,
        "destination": destination,
        "label": label,
        "known": known,
        "traversable": traversable,
    }


def validate_local_map(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``local_map`` payload.

    Returns a normalized payload or raises :class:`LocalMapError`. The common
    unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "local_map panel",
        {"schema_version", "available", "layer", "current_node", "title", "nodes", "edges", "legend"},
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != LOCAL_MAP_SCHEMA_VERSION:
        raise LocalMapError("unsupported local_map schema_version")
    if not _require_bool(payload, "available"):
        raise LocalMapError("available must be true for the local_map form")
    layer = payload["layer"]
    if layer not in LAYERS:
        raise LocalMapError("layer is not a stable value")
    current_node = _require_node_id(payload["current_node"], "current_node")
    decoded = decode_node(current_node)
    if layer == "grid" and decoded["prefix"] != "grid":
        raise LocalMapError("a grid-layer payload must have a grid current node")
    if layer == "wilderness" and decoded["prefix"] != "wild":
        raise LocalMapError("a wilderness-layer payload must have a wild current node")
    if layer in ("instance", "interior") and decoded["prefix"] != "room":
        raise LocalMapError(
            "an instance/interior payload must have a room current node"
        )
    title = _require_str(payload, "title", maximum=MAX_TITLE_CODE_POINTS)
    if not title.strip():
        raise LocalMapError("title must be non-empty")

    nodes = payload["nodes"]
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= MAX_NODES:
        raise LocalMapError(f"nodes must be a list of 1..{MAX_NODES} entries")
    node_views = [_validate_node(item) for item in nodes]
    if not any(node_view["current"] for node_view in node_views):
        raise LocalMapError("the payload must mark exactly one current node")
    if len([node_view for node_view in node_views if node_view["current"]]) != 1:
        raise LocalMapError("the payload must mark exactly one current node")
    if not any(node_view["id"] == current_node for node_view in node_views):
        raise LocalMapError("current_node must be present in nodes")
    node_ids = [node_view["id"] for node_view in node_views]
    if len(set(node_ids)) != len(node_ids):
        raise LocalMapError("node ids must be unique")

    edges = payload["edges"]
    if not isinstance(edges, list) or len(edges) > MAX_EDGES:
        raise LocalMapError(f"edges must be a list of at most {MAX_EDGES} entries")
    edge_views = [_validate_edge(item) for item in edges]
    node_id_set = set(node_ids)
    for edge_view in edge_views:
        if edge_view["source"] not in node_id_set:
            raise LocalMapError("edge.source must reference a presented node")
        if edge_view["destination"] not in node_id_set:
            raise LocalMapError("edge.destination must reference a presented node")

    legend = payload["legend"]
    if not isinstance(legend, list) or len(legend) > MAX_LEGEND:
        raise LocalMapError(f"legend must be a list of at most {MAX_LEGEND} entries")
    legend_views = []
    for entry in legend:
        text = _require_str({"legend": entry}, "legend", maximum=MAX_STRING_CODE_POINTS)
        if not text.strip():
            raise LocalMapError("legend entries must be non-empty")
        legend_views.append(text)

    result = {
        "schema_version": LOCAL_MAP_SCHEMA_VERSION,
        "available": True,
        "layer": layer,
        "current_node": current_node,
        "title": title,
        "nodes": node_views,
        "edges": edge_views,
        "legend": legend_views,
    }
    # Envelope guarantee (design D10a): a conforming payload must serialize
    # within the OOB envelope limit. The per-field bounds are ceilings, not a
    # guarantee that any combination of them fits, so the validator enforces
    # the serialized size directly -- a payload that would exceed the envelope
    # fails closed rather than being emitted.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise LocalMapError("local_map payload exceeds the OOB envelope limit")
    return result


__all__ = [
    "ACTION_KINDS",
    "COORD_MAX",
    "COORD_MIN",
    "GRID_MODES",
    "LAYERS",
    "LEGEND_LABELS",
    "LOCAL_MAP_SCHEMA_VERSION",
    "MAX_EDGES",
    "MAX_EXIT_REF_CHARS",
    "MAX_GRID_VISUAL_RANGE",
    "MAX_LEGEND",
    "MAX_NODE_ID_CHARS",
    "MAX_NODES",
    "MAX_REMEMBERED_GATEWAYS",
    "MAX_STRING_CODE_POINTS",
    "MAX_TITLE_CODE_POINTS",
    "VISIBILITIES",
    "WILD_DIRECTIONS",
    "LocalMapError",
    "_require_coord",
    "_require_exit_ref",
    "_require_node_id",
    "_validate_action",
    "_validate_edge",
    "_validate_node",
    "validate_local_map",
]
