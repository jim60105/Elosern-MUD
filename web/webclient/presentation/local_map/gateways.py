"""Registered-gateway lookup shared by the grid and wilderness adapters.

A gateway is a registered wilderness-entry gate: the pair of a wilderness
approach cell and a grid gate room. These helpers answer "which cell/room is a
gateway?" from ``WILDERNESS_ENTRY_REGISTRY`` and name the far side of one, so
both layer adapters resolve gateway identity through one registry face
(design D1/D5).
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from world.maps.published import PublishedView, SourceMemo

_Gateway = tuple[tuple[int, int], tuple[tuple[int, int], str], str]


def _wild_region_label(x: int, y: int) -> str:
    """The region display name for one wilderness cell."""
    from world.lore.wilderness_regions import regions
    from world.maps.wilderness_provider import region_for_coordinates

    return regions()[region_for_coordinates(x, y)].display_name_zh


@dataclass(frozen=True, slots=True)
class _GatewayTable:
    """Every registered gateway of one published input set (design D2)."""

    rows: tuple[_Gateway, ...]
    by_approach: Mapping[tuple[int, int], _Gateway]
    by_gate_room: Mapping[tuple[tuple[int, int], str], _Gateway]


_GATEWAY_TABLE = SourceMemo()


def _unwrap(view):
    return view.source if isinstance(view, PublishedView) else view


def _build_gateway_table(entries) -> _GatewayTable:
    """Build the gateway rows and first-match lookups with ONE settlement index (D2).

    A gate whose ``approach_cell`` is ``None`` is skipped, never raised on --
    the shared core map diagnostics validate the registry before publication
    and this presenter must not go unavailable on authored data (design D1).
    """
    from world.maps.static_references import (
        settlement_node_xy,
        settlement_reference_index,
    )

    index = settlement_reference_index()
    rows: list[_Gateway] = []
    by_approach: dict[tuple[int, int], _Gateway] = {}
    by_gate_room: dict[tuple[tuple[int, int], str], _Gateway] = {}
    for entry in entries.values():
        for gate in entry.gates:
            approach = entry.approach_cell(gate)
            if approach is None:
                continue
            gate_xy = settlement_node_xy(
                gate.destination,
                index=index,
                source=f"wilderness gate {entry.anchor_key}",
            )
            row = (approach, (gate_xy, gate.z_map_key), entry.anchor_key)
            rows.append(row)
            by_approach.setdefault(approach, row)
            by_gate_room.setdefault((gate_xy, gate.z_map_key), row)
    return _GatewayTable(
        rows=tuple(rows),
        by_approach=MappingProxyType(by_approach),
        by_gate_room=MappingProxyType(by_gate_room),
    )


def _gateway_table() -> _GatewayTable:
    """The gateway table of the published registry, settlement graphs and geography (D2)."""
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
    from world.maps import geography
    from world.maps.map_data import SETTLEMENT_GRAPHS

    entries = _unwrap(WILDERNESS_ENTRY_REGISTRY)
    sources = (entries, _unwrap(SETTLEMENT_GRAPHS), geography.current())
    return _GATEWAY_TABLE.resolve(
        sources, None, lambda: _build_gateway_table(entries)
    )


def _registered_gateways() -> list[_Gateway]:
    """Every registered gateway's ``(approach_cell, (grid_xy, z_map_key), anchor_key)``.

    Walks ``WILDERNESS_ENTRY_REGISTRY`` (deferred import, lore's own module
    boundary) in registry order; a gate whose ``approach_cell`` is ``None`` is
    skipped (design D1). Rows are memoized per published entry registry,
    settlement graphs and geography (design D2); each call returns a fresh list.
    """
    return list(_gateway_table().rows)


def _wilderness_gateway_at(x: int, y: int) -> _Gateway | None:
    """The registered gateway whose approach cell is ``(x, y)``, or ``None`` (design D1)."""
    return _gateway_table().by_approach.get((x, y))


def _grid_gateway_at(x: int, y: int, z: str) -> _Gateway | None:
    """The registered gateway whose gate room is ``(x, y, z)``, or ``None`` (design D1)."""
    return _gateway_table().by_gate_room.get(((x, y), z))


def _wilderness_gateways_by_approach() -> Mapping[tuple[int, int], _Gateway]:
    """First registered gateway per approach cell, in registry order (design D3)."""
    return _gateway_table().by_approach


def _gateway_far_side_label(layer: str, approach_cell: tuple[int, int], anchor_key: str) -> str:
    """The name of the place a gateway's traversal reaches (design D5).

    The wilderness side names the anchor the gate leads INTO; the grid side
    names the wilderness region the gate opens ONTO -- the far side either
    way, never the terrain the gateway node itself stands on.
    """
    if layer == "wilderness":
        from world.lore.anchors import anchors

        return anchors()[anchor_key].display_name_zh
    return _wild_region_label(*approach_cell)
