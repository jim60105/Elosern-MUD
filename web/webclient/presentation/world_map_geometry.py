"""Cached continental geometry, independent of every character's knowledge.

Only geometry is cached. Disclosure and wire identity belong to world_map.
Terrain washes use the canonical classifier on a 5 km display raster; they
never assign a whole district to each of its intersecting terrain regions.
"""
from __future__ import annotations

import math
from functools import cache


def point(x, y):
    return [int(x) if float(x).is_integer() else x, int(y) if float(y).is_integer() else y]


def common_layer():
    """The coastline, national borders and capital markers."""

    from world.maps.static_references import binding_signature

    return _common_layer(binding_signature())


@cache
def _common_layer(_signature):
    from world.lore.anchors import anchor_geography
    from world.lore.nations import NATION_REGISTRY
    from world.lore.wilderness_regions import mainland_boundary_km
    from world.maps.wilderness_provider import national_borders

    coast = [point(x, y) for x, y in mainland_boundary_km()]
    coast.append(coast[0][:])
    nations = []
    for key, nation in sorted(NATION_REGISTRY.items()):
        x, y = anchor_geography()[nation.capital_anchor_key].cell
        nations.append(dict(id=key, name=nation.display_name_zh, x=x + .5, y=y + .5))
    return dict(coastline=coast, borders=[[point(x, y) for x, y in border.points]
                                       for border in national_borders()], nations=nations)


def world_node_point(node_id):
    from world.rules.map_knowledge import decode_node
    from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
    from world.lore.anchors import LOCAL_FRAME_ANCHOR_REGISTRY, world_position_m
    from world.maps.map_data import settlement_graph

    node = decode_node(node_id)
    if node["prefix"] == "wild":
        return node["x"] + .5, node["y"] + .5
    if node["prefix"] == "grid":
        key = next((key for key, placement in ANCHOR_PLACEMENT_REGISTRY.items()
                    if placement.zcoord == node["z_map_key"]), None)
        if key in LOCAL_FRAME_ANCHOR_REGISTRY:
            graph = settlement_graph(node["z_map_key"])
            site = graph.node_at((node["x"], node["y"])) if graph is not None else None
            if site is not None:
                x, y = world_position_m(key, site.physical_coordinate)
                return tuple(point(x / 1000, y / 1000))
    return None


def current_point(actor):
    """Resolve an interior's canonical enclosing place, never invent axes."""
    from typeclasses.rooms import GridRoom, TerrainRoom
    from world.rules.map_knowledge import _derive_node_id
    from .map_quest_destinations import enclosing_anchor_cell, instance_origin

    location = instance_origin(getattr(actor, "location", None))
    if isinstance(location, (GridRoom, TerrainRoom)):
        node_id = _derive_node_id(location)
        return world_node_point(node_id) if node_id is not None else None
    cell = enclosing_anchor_cell(location)
    if cell is not None:
        x, y = cell
        return x + .5, y + .5
    return None


def clip_lines(vertices):
    """Split a polyline at canonical district boundaries, without names or IDs."""
    from world.maps.district_partition import district_at

    pieces = {}
    owner = None
    line = []
    provisional = False
    def flush():
        if owner is not None and len(line) >= 2:
            pieces.setdefault(owner, []).append(line[:])
    for (x0, y0), (x1, y1) in zip(vertices, vertices[1:]):
        steps = max(1, math.ceil(max(abs(x1-x0), abs(y1-y0))))
        for step in range(1 if line else 0, steps + 1):
            t = step / steps
            x, y = x0 + (x1-x0)*t, y0 + (y1-y0)*t
            key = district_at((math.floor(x), math.floor(y)))
            p = point(round(x, 3), round(y, 3))
            if key != owner:
                flush()
                owner, line, provisional = key, [p], False
                continue
            if provisional:
                line[-1] = p
            elif not line or p != line[-1]:
                line.append(p)
            provisional = step != steps
    flush()
    return pieces


def raster_rings(cells, step=5):
    """Trace a cell union with land on the left; preserve holes and corners."""
    edges = set()
    for x, y in cells:
        corners = ((x,y), (x+step,y), (x+step,y+step), (x,y+step))
        for a,b in zip(corners, corners[1:] + corners[:1]):
            if (b,a) in edges:
                edges.remove((b,a))
            else:
                edges.add((a,b))
    outgoing = {}
    for a,b in edges:
        outgoing.setdefault(a, set()).add(b)
    rings = []
    while edges:
        a,b = min(edges)
        start = a
        ring = [a]
        while True:
            edges.remove((a,b))
            outgoing[a].remove(b)
            ring.append(b)
            if b == start:
                break
            dx,dy = b[0]-a[0], b[1]-a[1]
            # At diagonally touching components take the strongest left turn.
            choices = outgoing[b]
            c = max(choices, key=lambda c: (dx*(c[1]-b[1])-dy*(c[0]-b[0]),
                                            dx*(c[0]-b[0])+dy*(c[1]-b[1]), c))
            a,b = b,c
        body = ring[:-1]
        simple = []
        for i,p in enumerate(body):
            before, after = body[i-1], body[(i+1)%len(body)]
            if (p[0]-before[0])*(after[1]-p[1]) != (p[1]-before[1])*(after[0]-p[0]):
                simple.append(list(p))
        simple.append(simple[0][:])
        rings.append(simple)
    return rings


def terrain_layers():
    """Terrain washes and nominal nations per district."""

    from world.maps.static_references import binding_signature

    return _terrain_layers(binding_signature())


@cache
def _terrain_layers(_signature):
    from world.lore.wilderness_regions import frame_cells
    from world.maps.district_partition import district_at
    from world.maps.wilderness_provider import region_for_coordinates, nominal_nation_for_coordinates

    size = frame_cells()
    groups = {}
    nations = {}
    for y in range(0, size, 5):
        for x in range(0, size, 5):
            key = district_at((x+2, y+2))
            if key is not None:
                region = region_for_coordinates(x+2, y+2)
                groups.setdefault((key, region), []).append((x,y))
                nations.setdefault(key,set()).add(nominal_nation_for_coordinates(x+2,y+2))
    terrain = {}
    for (key,region), cells in sorted(groups.items()):
        terrain.setdefault(key,[]).append(dict(region=region, polygons=raster_rings(cells)))
    return terrain, {key: sorted(values) for key,values in nations.items()}


@cache
def _district_lines(_signature):
    from world.maps.geography import current
    from world.maps.wilderness_provider import national_borders
    from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
    from world.lore.anchors import AnchorKind, anchors, world_position_m
    from world.maps.map_data import settlement_graph

    result = {}
    def add(kind, vertices):
        for key,lines in clip_lines(vertices).items():
            result.setdefault(key,dict(rivers=[],ridge=[],roads=[]))[kind].extend(lines)
    for route in current().terrain.waterway_routes.values():
        add("rivers", route)
    for border in national_borders():
        if border.nation_keys != ("altoria", "valhalla"):
            add("ridge", border.points)
    # There is no authored overland road network. Include the canonical roads
    # of public settlements; a hidden village's approach geometry is private.
    for key,placement in ANCHOR_PLACEMENT_REGISTRY.items():
        if anchors()[key].kind is not AnchorKind.CAPITAL:
            continue
        graph = settlement_graph(placement.zcoord)
        if graph is None:
            continue
        for road in graph.roads:
            source, dest = graph.nodes[road.source_id], graph.nodes[road.destination_id]
            vertices = [source.physical_coordinate, *road.bend_points, dest.physical_coordinate]
            # world_position_m accepts authored physical coordinates.
            add("roads", [(x/1000,y/1000) for x,y in
                          (world_position_m(key,p) for p in vertices)])
    return result


def district_lines():
    """District line geometry at the current static-reference bindings."""

    from world.maps.static_references import binding_signature

    return _district_lines(binding_signature())


@cache
def _district_geometry(_signature):
    from world.lore.map_districts import current as current_districts
    from world.maps.district_partition import district_outlines

    terrain,nations = terrain_layers()
    lines = district_lines()
    result = {}
    districts = current_districts().districts
    for key,rings in district_outlines().items():
        district = districts[key]
        outline = []
        for ring in rings:
            converted = [point(ring[i]/1000, ring[i+1]/1000) for i in range(0,len(ring),2)]
            if converted[0] != converted[-1]:
                converted.append(converted[0][:])
            outline.append(converted)
        from world.lore.map_districts import landmark_node_id

        x,y = world_node_point(landmark_node_id(district))
        result[key] = dict(name=district.district_name_zh, outline=outline,
                           landmark=dict(name=district.landmark_name_zh,x=x,y=y),
                           nations=nations.get(key,[]), terrain=terrain.get(key,[]),
                           **lines.get(key,dict(rivers=[],ridge=[],roads=[])))
    return result


def district_geometry():
    """District geometry at the current static-reference bindings."""

    from world.maps.static_references import binding_signature

    return _district_geometry(binding_signature())


@cache
def _place_geometry(_signature):
    """Internal (owner, wire row, visit-only, canonical visit IDs) records."""
    from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
    from world.lore.anchors import AnchorKind, anchor_geography, anchors
    from world.lore.wilderness_regions import harbor_sites
    from world.maps.district_partition import district_at
    from world.maps.map_data import settlement_graph
    from world.maps.static_references import settlement_node_xyz
    from world.rules.map_knowledge import encode_grid, encode_wild
    from world.maps.wilderness_provider import WILDERNESS_NAME

    result=[]
    for key,geo in sorted(anchor_geography().items()):
        anchor=anchors()[key]
        x,y=geo.cell
        hidden=anchor.kind in (AnchorKind.ELVEN_VILLAGE,AnchorKind.DUNGEON)
        kind="hidden" if hidden else "capital"
        ids={encode_wild(WILDERNESS_NAME,x,y)}
        placement=ANCHOR_PLACEMENT_REGISTRY.get(key)
        if placement is not None:
            node_xyz = settlement_node_xyz(placement.node, source=f"anchor placement {key}")
            ids.add(encode_grid(node_xyz[2], node_xyz[0], node_xyz[1]))
            graph = settlement_graph(placement.zcoord)
            if graph is not None:
                ids.update(encode_grid(placement.zcoord, node.x, node.y) for node in graph.nodes.values())
        result.append((district_at((x,y)),dict(id=key,name=anchor.display_name_zh,kind=kind,x=x+.5,y=y+.5),hidden,frozenset(ids)))
    for key,site in sorted(harbor_sites().items()):
        x,y=site.cell
        result.append((district_at((x,y)),dict(id=key,name=site.display_name,kind="harbour",x=x+.5,y=y+.5),False,
                       frozenset((encode_wild(WILDERNESS_NAME,x,y),))))
    return tuple(result)


def place_geometry():
    """Place visit geometry at the current static-reference bindings."""

    from world.maps.static_references import binding_signature

    return _place_geometry(binding_signature())
