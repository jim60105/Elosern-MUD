"""The read-only ``map.view`` action (world-map drawer design §5.1).

``map.view`` names the on-demand map panel a client wants published. It is an
allowlisted read: the adapter changes no location, clock, knowledge or quest
state and never enters the text command parser; the dispatcher's completion
renders and publishes only the requested panel (bounded parts when it is
large). The drawer re-requests its active scope after each committed move;
movement itself never pushes a map.

This change admits only ``{"scope": "area"}``. The ``world`` scope is added
to the same exact union by its owning change (publish-world-map-panel).
"""

from typing import Any

from web.webclient.presentation.map_panels import AREA_MAP_PANEL
from web.webclient.presentation.protocol import ProtocolValidationError

#: The exact scopes this action admits, and the panel each one publishes.
MAP_VIEW_SCOPES: dict[str, str] = {"area": AREA_MAP_PANEL}

#: Every panel ``map.view`` may publish (the dispatcher's affected-panel set).
MAP_VIEW_PANELS: tuple[str, ...] = tuple(MAP_VIEW_SCOPES.values())


def validate_map_view_payload(payload: Any) -> dict[str, str]:
    """Validate the exact ``map.view`` payload ``{"scope": <scope>}``."""
    if not isinstance(payload, dict) or set(payload) != {"scope"}:
        raise ProtocolValidationError("map.view requires exactly the scope field")
    scope = payload["scope"]
    if not isinstance(scope, str) or scope not in MAP_VIEW_SCOPES:
        raise ProtocolValidationError("map.view scope is not an admitted value")
    return {"scope": scope}


def map_view_adapter(actor: Any, payload: dict[str, str], session: Any = None) -> dict[str, Any]:
    """Publish the requested map panel; a pure read with no state change."""
    return {
        "outcome": "success",
        "code": "map.view",
        "message": "已更新地圖。",
        "affected_panels": (MAP_VIEW_SCOPES[payload["scope"]],),
    }


__all__ = ["MAP_VIEW_PANELS", "MAP_VIEW_SCOPES", "map_view_adapter", "validate_map_view_payload"]
