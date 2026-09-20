"""Shared module-level helpers for the ``local_map`` test package."""

import importlib
import unittest
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.local_map import LEGEND_LABELS
from world.maps.bootstrap import NORTH_GATE_XYZ, SOUTH_GATE_XYZ, sync_grid, sync_wilderness


def _live(module: str, attribute: str):
    """Fetch a shipped module attribute by runtime name (test-data gate: no
    scan-time registry refs; mirrors the sibling panels' probe idiom)."""
    return getattr(importlib.import_module(module), attribute)


# The sample city's z-map key rides in with the imported gate coordinates --
# the map identity never appears as a literal in this file.
_T_MAP_KEY = NORTH_GATE_XYZ[2]


_T_PLAZA_XYZ = (2, 2, _T_MAP_KEY)


def _t_grid_id(x: int, y: int) -> str:
    return f"grid:{_T_MAP_KEY}:{x}:{y}"


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
