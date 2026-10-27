"""Adapt a live xyzgrid ``XYMap`` to the pure sparse-graph contract.

Synthetic test maps and builder-authored maps still arrive as parsed ASCII. This
transient adapter gives route planning the same sparse graph contract without
persisting or caching a second authority. Identity is the map's node index,
which is only valid for the lifetime of the loaded map; the routing and
validation algorithms themselves live in :mod:`elosern_map_core.sparse`.
"""

from __future__ import annotations

from elosern_map_core.sparse import (
    SparseGraphError,
    SparseNode,
    SparseRoad,
    SparseSettlementGraph,
)


def graph_from_xymap(xymap) -> SparseSettlementGraph | None:
    """Adapt a live contrib ``XYMap`` for maps without a sparse declaration."""

    if xymap is None or not getattr(xymap, "node_index_map", None):
        return None
    prototypes = getattr(xymap, "prototypes", None) or {}
    nodes = []
    for node in sorted(xymap.node_index_map.values(), key=lambda item: item.node_index):
        prototype = prototypes.get((node.X, node.Y))
        if not prototype:
            prototype = {"key": getattr(node, "key", str(node.node_index))}
        nodes.append(
            SparseNode(
                node_id=str(node.node_index),
                x=node.X,
                y=node.Y,
                prototype=dict(prototype),
            )
        )
    roads = []
    seen = set()
    for node in xymap.node_index_map.values():
        for direction, neighbor in node.links.items():
            pair = (node.node_index, neighbor.node_index)
            if pair in seen:
                continue
            seen.add(pair)
            roads.append(
                SparseRoad(
                    road_id=f"{node.node_index}>{neighbor.node_index}",
                    source_id=str(node.node_index),
                    destination_id=str(neighbor.node_index),
                    direction_hint=direction,
                )
            )
    try:
        return SparseSettlementGraph(
            str(xymap.Z),
            nodes,
            roads,
            options=getattr(xymap, "options", None),
            exit_prototype=prototypes.get(("*", "*", "*"), {}),
        )
    except SparseGraphError:
        return None
