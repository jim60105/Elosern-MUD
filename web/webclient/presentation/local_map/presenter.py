"""The ``local_map`` presenter: assembles the layer payload and validates it.

Reads canonical room, map, and knowledge data (never rendered ANSI) and never
mutates knowledge, traits, clock, or location. The exact schema-version-1
contract lives in :mod:`web.webclient.presentation.local_map.validate`; the
four layer adapters live in the sibling modules.
"""

from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.local_map.builder import _GraphBuilder, _visited_map
from web.webclient.presentation.local_map.grid import _grid_layer
from web.webclient.presentation.local_map.interior import _interior_graph
from web.webclient.presentation.local_map.validate import (
    LEGEND_LABELS,
    LOCAL_MAP_SCHEMA_VERSION,
    validate_local_map,
)
from web.webclient.presentation.local_map.wilderness import _wilderness_layer
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.map_knowledge import KnowledgeError, parse_knowledge


def local_map_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``local_map`` panel for the authenticated puppet."""
    actor = context.actor
    location = getattr(actor, "location", None)
    if location is None:
        raise PanelUnavailableError
    try:
        visits = parse_knowledge(actor)
    except KnowledgeError:
        raise PanelUnavailableError

    from typeclasses.rooms import GridRoom, InstanceRoom, TerrainRoom

    # Module import of the terrain provider (never a from-import of the
    # constant, which would freeze the figure at import time and hide a
    # provider-module patch from the presenter).
    from world.maps import wilderness_provider

    builder = _GraphBuilder(_visited_map(visits))
    if isinstance(location, GridRoom):
        layer = _grid_layer(actor, visits, builder)
        title = f"{location.key}街道圖"
    elif isinstance(location, TerrainRoom):
        layer = _wilderness_layer(actor, visits, builder)
        title = "荒野地圖"
    elif isinstance(location, InstanceRoom):
        layer = _interior_graph(actor, visits, builder, is_instance=True)
        title = f"{location.key}空間平面圖"
    else:
        layer = _interior_graph(actor, visits, builder, is_instance=False)
        title = f"{location.key}平面圖"

    if not any(node["current"] for node in builder.nodes):
        raise PanelUnavailableError

    # The wilderness legend appends one localized scale note after the four
    # state labels (webclient-map-scale-legend D1/D2). The figure is read as a
    # module attribute of its owning provider module at assembly time -- never
    # a from-import binding, which would freeze the value and hide provider
    # patches -- so a single constant edit is the only source of the distance.
    legend = list(LEGEND_LABELS)
    if layer == "wilderness":
        legend.append(f"每格約 {wilderness_provider.WILDERNESS_KM_PER_CELL} 公里")

    payload = {
        "schema_version": LOCAL_MAP_SCHEMA_VERSION,
        "available": True,
        "layer": layer,
        "current_node": next(node["id"] for node in builder.nodes if node["current"]),
        "title": title,
        "nodes": builder.nodes,
        "edges": builder.edges,
        "legend": legend,
    }
    return validate_local_map(payload)
