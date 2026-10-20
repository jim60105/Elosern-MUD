"""Exact schema-version-2 ``lineage`` panel and presenter (skill-lineage-panel).

The presenter serializes the pure ``world.rules.lineage_query`` read model for
the session's viewed party member (the commander when no effective selection
exists). It reads no raw persistent records itself and mutates nothing.
Malformed proficiency data fails the panel closed through the common
unavailable form — no fabricated node values.

Wire caps (design §5, mirrored by the JS validator): at most ``MAX_GRAPHS``
connected graphs of at most ``MAX_NODES_PER_GRAPH`` nodes and
``MAX_EDGES_PER_GRAPH`` edges, with bounded text lengths. Truncation follows
one fixed declared order: drop trailing graphs to the graph cap, then trailing
nodes (and every edge touching them) to the per-graph cap, then further
trailing graphs until the payload fits the OOB envelope. No edge ever
references a truncated node. ``completed_count``/``total_count`` and each
graph's ``owned_count``/``total_count``/``consumed`` always describe the FULL
untruncated view.
"""

from dataclasses import replace
from math import isfinite
from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.party_view_selection import resolve_viewed_member
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    _validate_identifier,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.lineage_query import LineageQueryError, LineageView, build_lineage_view

LINEAGE_SCHEMA_VERSION = 2

# Exact shared bounds -- must stay equal in the JS validator.
MAX_GRAPHS = 16
MAX_NODES_PER_GRAPH = 32
MAX_EDGES_PER_GRAPH = 64
MAX_KEY_CODE_POINTS = 64
# Cross-referenced with world/rules/lineage_query.LINEAGE_TEXT_WIRE_MAX: the
# read model clamps rendered 「需「label Lv.N」」 text to this bound before it
# reaches the validator, so a legal 128-code-point registry label can never
# push the whole panel into the unavailable form (rubber-duck R2-1).
MAX_TEXT_CODE_POINTS = 128
# The lineage panel's fixed share of the 65,536-byte snapshot envelope. A
# full snapshot carries every registered panel and this one is the largest:
# reserving 28KiB leaves 36KiB for the other 24 panels, which measured ~15KiB
# for a bare browser character and ~30KiB for the richest fixtures. The
# allocation is a fixed constant (not a per-snapshot remainder) so the 系譜
# command prints exactly the graphs the panel renders. Truncation keeps every
# header count at its full-view value.
MAX_LINEAGE_PANEL_BYTES = 28 * 1024


class LineagePanelError(ProtocolValidationError):
    """The available lineage payload violates its exact bounded schema."""


def _require_number(value: Any, field: str, *, minimum: float, maximum: float) -> float:
    """Return a non-boolean, finite int/float within bounds."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"{field} must be a number")
    if isinstance(value, float) and not isfinite(value):
        raise ProtocolValidationError(f"{field} must be finite")
    if value < minimum or value > maximum:
        raise ProtocolValidationError(f"{field} is out of bounds")
    return value


def _validate_node(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "lineage node",
        {
            "skill_key",
            "display_name_zh",
            "owned",
            "usable",
            "ready",
            "level",
            "xp_into_level",
            "xp_to_next_level",
            "capped",
            "prereq_text_zh",
            "depth",
        },
        {},
    )
    skill_key = _validate_identifier(value["skill_key"], "skill_key")
    if len(skill_key) > MAX_KEY_CODE_POINTS:
        raise LineagePanelError("skill_key exceeds its bound")
    display_name = _require_str(
        value, "display_name_zh", maximum=MAX_TEXT_CODE_POINTS
    )
    if not display_name.strip():
        raise LineagePanelError("display_name_zh must be non-empty")
    prereq_text = _require_str(value, "prereq_text_zh", maximum=MAX_TEXT_CODE_POINTS)
    return {
        "skill_key": skill_key,
        "display_name_zh": display_name,
        "owned": _require_bool(value, "owned"),
        "usable": _require_bool(value, "usable"),
        "ready": _require_bool(value, "ready"),
        "level": _require_int(value, "level", minimum=0, maximum=MAX_SAFE_INTEGER),
        "xp_into_level": _require_number(
            value["xp_into_level"], "xp_into_level", minimum=0, maximum=MAX_SAFE_INTEGER
        ),
        "xp_to_next_level": _require_number(
            value["xp_to_next_level"],
            "xp_to_next_level",
            minimum=0,
            maximum=MAX_SAFE_INTEGER,
        ),
        "capped": _require_bool(value, "capped"),
        "prereq_text_zh": prereq_text,
        "depth": _require_int(
            value, "depth", minimum=0, maximum=MAX_SAFE_INTEGER
        ),
    }


def _validate_key(value: Any, field: str) -> str:
    key = _validate_identifier(value, field)
    if len(key) > MAX_KEY_CODE_POINTS:
        raise LineagePanelError(f"{field} exceeds its bound")
    return key


def _validate_edge(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "lineage edge",
        {"from_key", "to_key", "min_level"},
        {},
    )
    return {
        "from_key": _validate_key(value["from_key"], "from_key"),
        "to_key": _validate_key(value["to_key"], "to_key"),
        "min_level": _require_int(
            value, "min_level", minimum=1, maximum=MAX_SAFE_INTEGER
        ),
    }


def _validate_graph(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "lineage graph",
        {
            "graph_id",
            "group_label_zh",
            "root_keys",
            "owned_count",
            "total_count",
            "consumed",
            "nodes",
            "edges",
        },
        {},
    )
    graph_id = _validate_key(value["graph_id"], "graph_id")
    label = _require_str(value, "group_label_zh", maximum=MAX_TEXT_CODE_POINTS)
    if not label.strip():
        raise LineagePanelError("group_label_zh must be non-empty")
    nodes = value["nodes"]
    if not isinstance(nodes, list) or not 1 <= len(nodes) <= MAX_NODES_PER_GRAPH:
        raise LineagePanelError(
            f"nodes must be a list of 1..{MAX_NODES_PER_GRAPH} entries"
        )
    node_views = [_validate_node(item) for item in nodes]
    node_keys = [node["skill_key"] for node in node_views]
    if len(set(node_keys)) != len(node_keys):
        raise LineagePanelError("nodes must carry unique skill keys")
    roots = value["root_keys"]
    if not isinstance(roots, list) or not 1 <= len(roots) <= len(node_keys):
        raise LineagePanelError("root_keys must be a unique non-empty subset of nodes")
    root_views = [_validate_key(item, "root_keys") for item in roots]
    if len(set(root_views)) != len(root_views):
        raise LineagePanelError("root_keys must be a unique non-empty subset of nodes")
    if any(root not in node_keys for root in root_views):
        raise LineagePanelError("root_keys must name graph nodes")
    if root_views[0] != graph_id:
        raise LineagePanelError("graph_id must be the first root key")
    edges = value["edges"]
    if not isinstance(edges, list) or len(edges) > MAX_EDGES_PER_GRAPH:
        raise LineagePanelError(
            f"edges must be a list of at most {MAX_EDGES_PER_GRAPH} entries"
        )
    edge_views = [_validate_edge(item) for item in edges]
    seen_edges: set[tuple[str, str]] = set()
    for edge in edge_views:
        pair = (edge["from_key"], edge["to_key"])
        if pair[0] == pair[1]:
            raise LineagePanelError("a lineage edge must connect two distinct nodes")
        if pair in seen_edges:
            raise LineagePanelError("a lineage edge may appear only once")
        seen_edges.add(pair)
        if pair[0] not in node_keys or pair[1] not in node_keys:
            raise LineagePanelError("an edge must not reference a truncated node")
    owned = _require_int(
        value, "owned_count", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    total = _require_int(value, "total_count", minimum=0, maximum=MAX_SAFE_INTEGER)
    if owned > total or total < len(node_keys):
        raise LineagePanelError("graph counts must cover the emitted nodes")
    return {
        "graph_id": graph_id,
        "group_label_zh": label,
        "root_keys": root_views,
        "owned_count": owned,
        "total_count": total,
        "consumed": _require_bool(value, "consumed"),
        "nodes": node_views,
        "edges": edge_views,
    }


def validate_lineage(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``lineage`` payload.

    Returns a normalized payload or raises :class:`LineagePanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "lineage panel",
        {
            "schema_version",
            "available",
            "kind",
            "completed_count",
            "total_count",
            "graphs",
        },
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != LINEAGE_SCHEMA_VERSION:
        raise LineagePanelError("unsupported lineage schema_version")
    if not _require_bool(payload, "available"):
        raise LineagePanelError("available must be true for the lineage form")
    if payload["kind"] != "lineage":
        raise LineagePanelError("lineage panel kind must be lineage")
    completed = _require_int(
        payload, "completed_count", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    total = _require_int(payload, "total_count", minimum=0, maximum=MAX_SAFE_INTEGER)
    if completed > total:
        raise LineagePanelError("completed_count must not exceed total_count")
    graphs = payload["graphs"]
    if not isinstance(graphs, list) or len(graphs) > MAX_GRAPHS:
        raise LineagePanelError(f"graphs must be a list of at most {MAX_GRAPHS} entries")
    graph_views = [_validate_graph(item) for item in graphs]
    result = {
        "schema_version": LINEAGE_SCHEMA_VERSION,
        "available": True,
        "kind": "lineage",
        "completed_count": completed,
        "total_count": total,
        "graphs": graph_views,
    }
    # Envelope guarantee: the presenter truncates until a real payload fits;
    # the validator enforces the serialized size directly, so a hand-built
    # all-ceilings payload fails closed rather than being emitted.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise LineagePanelError("lineage payload exceeds the OOB envelope limit")
    return result


def _serialize_graph(graph: Any) -> dict[str, Any]:
    return {
        "graph_id": graph.graph_id,
        "group_label_zh": graph.group_label_zh,
        "root_keys": list(graph.root_keys),
        "owned_count": graph.owned_count,
        "total_count": graph.total_count,
        "consumed": graph.consumed,
        "nodes": [
            {
                "skill_key": node.skill_key,
                "display_name_zh": node.display_name_zh,
                "owned": node.owned,
                "usable": node.usable,
                "ready": node.ready,
                "level": node.level,
                "xp_into_level": node.xp_into_level,
                "xp_to_next_level": node.xp_to_next_level,
                "capped": node.capped,
                "prereq_text_zh": node.prereq_text_zh,
                "depth": node.depth,
            }
            for node in graph.nodes
        ],
        "edges": [
            {
                "from_key": edge.from_key,
                "to_key": edge.to_key,
                "min_level": edge.min_level,
            }
            for edge in graph.edges
        ],
    }


def _truncate_graph_view(graph: Any) -> Any:
    """Apply the per-graph node and edge caps without leaving dangling edges."""
    nodes = graph.nodes[:MAX_NODES_PER_GRAPH]
    node_keys = {node.skill_key for node in nodes}
    return replace(
        graph,
        root_keys=tuple(key for key in graph.root_keys if key in node_keys),
        nodes=nodes,
        edges=tuple(
            edge
            for edge in graph.edges
            if edge.from_key in node_keys and edge.to_key in node_keys
        )[:MAX_EDGES_PER_GRAPH],
    )


def bounded_lineage_view(view: LineageView) -> LineageView | None:
    """The view bounded by the declared caps and the OOB envelope.

    The one truncation both surfaces use, so the Telnet command prints exactly
    the graphs the panel renders. Trailing graphs drop first, then trailing
    nodes (and every edge touching them), then further trailing graphs until
    the serialized payload fits ``MAX_LINEAGE_PANEL_BYTES``, the panel's fixed
    share of the snapshot envelope. Counts keep their full-view values.
    ``None`` means even a single caps-bounded graph cannot fit that share, and
    the caller fails closed.
    """
    graphs = tuple(_truncate_graph_view(graph) for graph in view.graphs[:MAX_GRAPHS])
    while True:
        bounded = replace(view, graphs=graphs)
        payload = {
            "schema_version": LINEAGE_SCHEMA_VERSION,
            "available": True,
            "kind": "lineage",
            "completed_count": bounded.completed_count,
            "total_count": bounded.total_count,
            "graphs": [_serialize_graph(graph) for graph in bounded.graphs],
        }
        if json_byte_size(payload) <= MAX_LINEAGE_PANEL_BYTES:
            return bounded
        if len(graphs) <= 1:
            # The first caps-bounded graph alone exceeds the panel's share of
            # the envelope. Authored graphs never reach this (the per-graph
            # caps bound them far below the allocation), so the caller fails
            # closed rather than emitting an over-budget panel.
            return None
        graphs = graphs[:-1]


def lineage_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``lineage`` panel for the viewed member.

    Truncation (declared order, design §5): trailing graphs to the graph cap,
    then trailing nodes (and every edge touching them) to the per-graph cap,
    then further trailing graphs until the serialized payload fits the
    envelope share. Header counts and each graph's owned/total/consumed always
    come from the FULL view.
    """
    actor = getattr(context, "actor", None)
    if bool(getattr(actor, "creation_pending", False)):
        raise PanelUnavailableError
    member = resolve_viewed_member(context)
    if member is None:
        raise PanelUnavailableError
    try:
        view = build_lineage_view(member)
    except LineageQueryError:
        raise PanelUnavailableError from None
    bounded = bounded_lineage_view(view)
    if bounded is None:
        raise PanelUnavailableError
    payload = {
        "schema_version": LINEAGE_SCHEMA_VERSION,
        "available": True,
        "kind": "lineage",
        "completed_count": view.completed_count,
        "total_count": view.total_count,
        "graphs": [_serialize_graph(graph) for graph in bounded.graphs],
    }
    return validate_lineage(payload)
