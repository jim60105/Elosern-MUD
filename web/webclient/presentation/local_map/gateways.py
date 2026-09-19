"""Registered-gateway lookup shared by the grid and wilderness adapters.

A gateway is a registered wilderness-entry gate: the pair of a wilderness
approach cell and a grid gate room. These helpers answer "which cell/room is a
gateway?" from ``WILDERNESS_ENTRY_REGISTRY`` and name the far side of one, so
both layer adapters resolve gateway identity through one registry face
(design D1/D5).
"""


def _wild_region_label(x: int, y: int) -> str:
    """The region display name for one wilderness cell."""
    from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY
    from world.maps.wilderness_provider import region_for_coordinates

    return WILDERNESS_REGION_REGISTRY[region_for_coordinates(x, y)].display_name_zh


def _registered_gateways() -> list[tuple[tuple[int, int], tuple[tuple[int, int], str], str]]:
    """Every registered gateway's ``(approach_cell, (grid_xy, z_map_key), anchor_key)``.

    Walks ``WILDERNESS_ENTRY_REGISTRY`` (deferred import, lore's own module
    boundary). A gate whose ``approach_cell`` is ``None`` is skipped, never
    raised on -- the registry is validated at sync time
    (``validate_wilderness_entries``) and this presenter must not go
    unavailable on authored data (design D1).
    """
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

    result: list[tuple[tuple[int, int], tuple[tuple[int, int], str], str]] = []
    for entry in WILDERNESS_ENTRY_REGISTRY.values():
        for gate in entry.gates:
            approach = entry.approach_cell(gate)
            if approach is None:
                continue
            result.append((approach, (gate.grid_xy, gate.z_map_key), entry.anchor_key))
    return result


def _wilderness_gateway_at(
    x: int, y: int
) -> tuple[tuple[int, int], tuple[tuple[int, int], str], str] | None:
    """The registered gateway whose approach cell is ``(x, y)``, or ``None`` (design D1)."""
    for approach, grid_gate, anchor_key in _registered_gateways():
        if approach == (x, y):
            return approach, grid_gate, anchor_key
    return None


def _grid_gateway_at(
    x: int, y: int, z: str
) -> tuple[tuple[int, int], tuple[tuple[int, int], str], str] | None:
    """The registered gateway whose gate room is ``(x, y, z)``, or ``None`` (design D1)."""
    for approach, (grid_xy, z_map_key), anchor_key in _registered_gateways():
        if grid_xy == (x, y) and z_map_key == z:
            return approach, (grid_xy, z_map_key), anchor_key
    return None


def _gateway_far_side_label(layer: str, approach_cell: tuple[int, int], anchor_key: str) -> str:
    """The name of the place a gateway's traversal reaches (design D5).

    The wilderness side names the anchor the gate leads INTO; the grid side
    names the wilderness region the gate opens ONTO -- the far side either
    way, never the terrain the gateway node itself stands on.
    """
    if layer == "wilderness":
        from world.lore.anchors import ANCHOR_REGISTRY

        return ANCHOR_REGISTRY[anchor_key].display_name_zh
    return _wild_region_label(*approach_cell)
