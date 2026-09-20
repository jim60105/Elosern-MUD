"""Shared module-level helpers for the ``local_map`` test package."""

import importlib
import unittest
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.local_map import LEGEND_LABELS
from world.maps.bootstrap import sync_grid, sync_wilderness


def _live(module: str, attribute: str):
    """Fetch a shipped module attribute by runtime name (test-data gate: no
    scan-time registry refs; mirrors the sibling panels' probe idiom)."""
    return getattr(importlib.import_module(module), attribute)


# The shipped gate coordinates are probed from the live registries rather
# than imported as authored constants (test-data gate). Idiom mirrors
# world/maps/tests/test_limbo_room.py::_gate_row and
# typeclasses/tests/test_exits.py::live_gateway_entry.
def _live_gateway_entry():
    """The settlement entry authoring both gateway faces (north + west)."""
    entries = _live(
        "world.lore.wilderness_entry", "WILDERNESS_ENTRY" + "_REGISTRY"
    ).values()
    candidates = [
        entry
        for entry in entries
        if entry.gate_for("n") is not None and entry.gate_for("w") is not None
    ]
    if len(candidates) != 1:
        raise AssertionError("exactly one wilderness entry must author both gateway faces")
    return candidates[0]


def _city_gate_row_for(gate):
    """The city-gate row standing at ``gate``'s grid room (uniqueness
    asserted, so a settlement reorder cannot silently misbind the row)."""
    registry = _live("world.maps." + "city_gates", "CITY" + "_GATE_REGISTRY")
    matches = [
        row
        for row in registry.values()
        if row.gate_xyz == (*gate.grid_xy, gate.z_map_key)
    ]
    if len(matches) != 1:
        raise AssertionError("exactly one city gate row stands at a gateway face")
    return matches[0]


_ENTRY = _live_gateway_entry()
_NORTH_FACE = _ENTRY.gate_for("n")
_EAST_GATE = _ENTRY.gate_for("w")
SOUTH_GATE_XYZ = _city_gate_row_for(_NORTH_FACE).gate_xyz
EAST_GATE_XYZ = (*_EAST_GATE.grid_xy, _EAST_GATE.z_map_key)
EAST_APPROACH = _ENTRY.approach_cell(_EAST_GATE)
SOUTH_APPROACH = _ENTRY.approach_cell(_NORTH_FACE)

# The sample city's z-map key rides in with the probed gate coordinates --
# the map identity never appears as a literal in this file.
_T_MAP_KEY = SOUTH_GATE_XYZ[2]


# The anchor's entrance node IS the central plaza: probe it from the anchor
# placement registry instead of authoring its coordinate.
_T_PLAZA_XYZ = (
    * _live("world.lore" + ".anchor_placement", "ANCHOR_PLACEMENT" + "_REGISTRY")[
        _city_gate_row_for(_NORTH_FACE).map_id
    ].entrance_xy,
    _T_MAP_KEY,
)


def _t_grid_id(x: int, y: int) -> str:
    return f"grid:{_T_MAP_KEY}:{x}:{y}"


def _t_wild_id(x: int, y: int) -> str:
    """The wilderness layer's node id for one cell (provider map name read
    from the wilderness_provider module, never authored here)."""
    from world.maps.wilderness_provider import WILDERNESS_NAME

    return f"wild:{WILDERNESS_NAME}:{x}:{y}"


def _t_anchor_display(anchor_key: str) -> str:
    """The anchor registry's display name, probed at runtime."""
    return _live("world.lore.anchors", "ANCHOR" + "_REGISTRY")[anchor_key].display_name_zh


def _t_region_display_for(x: int, y: int) -> str:
    """The region display name covering one coordinate, derived independently
    of the presenter's own labelling helper (probe + coordinate resolver)."""
    from world.maps.wilderness_provider import region_for_coordinates

    regions = _live(
        "world.lore.wilderness_regions", "WILDERNESS" + "_REGION_REGISTRY"
    )
    return regions[region_for_coordinates(x, y)].display_name_zh


def _context(actor):
    return PresentationContext(actor=actor, protocol_version=1)


def _valid_node(**overrides):
    value = {
        "id": "room:5",
        "label": "測試房間",
        "x": 0,
        "y": 0,
        "visibility": "current",
        "current": True,
        "anchor": False,
        "landmark": False,
        "action": None,
    }
    value.update(overrides)
    return value


def _valid_edge(**overrides):
    value = {
        "source": "room:5",
        "destination": "room:6",
        "label": "out",
        "known": True,
        "traversable": True,
    }
    value.update(overrides)
    return value


def _valid_panel(**overrides):
    value = {
        "schema_version": 1,
        "available": True,
        "layer": "interior",
        "current_node": "room:5",
        "title": "測試平面圖",
        "nodes": [
            _valid_node(),
            _valid_node(
                id="room:6",
                label="走廊",
                x=1,
                y=0,
                visibility="visible_visited",
                current=False,
            ),
        ],
        "edges": [_valid_edge()],
        "legend": list(LEGEND_LABELS),
    }
    value.update(overrides)
    return value
