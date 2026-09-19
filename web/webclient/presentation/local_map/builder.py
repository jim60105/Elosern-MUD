"""Shared layer-adapter pieces: the bounded graph builder and exit helpers.

Every layer adapter accumulates its nodes/edges through :class:`_GraphBuilder`
and resolves exit identity/traversability through the helpers here, so the four
adapters share one bounded payload accumulator and one fail-closed traversal
probe.
"""

from typing import Any

from world.rules.map_knowledge import NodeVisit


def _visited_map(visits: list[NodeVisit]) -> dict[str, NodeVisit]:
    return {visit.node_id: visit for visit in visits}


def _known_node_id(node_id: str, visited: dict[str, NodeVisit]) -> bool:
    return node_id in visited


class _GraphBuilder:
    """Accumulates bounded nodes/edges and the exact payload node dicts."""

    def __init__(self, visited: dict[str, NodeVisit]) -> None:
        self.visited = visited
        self.nodes: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []
        self._by_id: dict[str, dict[str, Any]] = {}

    def add_node(
        self,
        node_id: str,
        label: str,
        x: int,
        y: int,
        *,
        visibility: str,
        current: bool = False,
        anchor: bool = False,
        landmark: bool = False,
        action: dict[str, Any] | None = None,
    ) -> None:
        existing = self._by_id.get(node_id)
        if existing is not None:
            # A later exit-derived descriptor may enrich a node first added as
            # an origin/return with a travel action; never downgrade a node
            # that already carries one.
            if existing["action"] is None and action is not None:
                existing["action"] = action
            return
        node = {
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
        self.nodes.append(node)
        self._by_id[node_id] = node

    def add_edge(self, source: str, destination: str, label: str, traversable: bool) -> None:
        known = _known_node_id(destination, self.visited)
        self.edges.append(
            {
                "source": source,
                "destination": destination,
                "label": label,
                "known": known,
                "traversable": traversable,
            }
        )

    def remembered(self, cap: int) -> list[dict[str, Any]]:
        """Return the bounded remembered nodes, most-recent ``last_seen`` first."""
        candidates = [
            visit
            for visit in self.visited.values()
            if visit.node_id not in self._by_id and visit.node_id.startswith(("grid:", "wild:", "room:"))
        ]
        candidates.sort(key=lambda visit: (-visit.last_seen_tick, visit.node_id))
        return candidates[:cap]


def _exit_ref(exit_obj: Any) -> str:
    """An opaque, stable ASCII identifier for a real exit (its dbref)."""
    return str(int(exit_obj.id))


def _traversable(exit_obj: Any, actor: Any) -> bool:
    try:
        return bool(exit_obj.access(actor, "traverse"))
    except Exception:
        return False
