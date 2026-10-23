"""On-demand world map. Knowledge filtering precedes every serialization."""
from __future__ import annotations

import hashlib
import math

from web.webclient.presentation.map_panels import (
    MAP_MAX_TITLE, WORLD_MAP_SCHEMA_VERSION, WORLD_MAX_QUEST_MARKERS, validate_world_map,
)
from web.webclient.presentation.registry import PanelUnavailableError
from web.webclient.presentation import world_map_geometry as geometry
from world.rules.map_knowledge import KnowledgeError, decode_node
from world.rules.map_discovery import persisted_visits


TRAIL_CELL_CAP = 20_000


def district_wire_id(key):
    """Stable nonsemantic identity; never send descriptive registry keys unlit."""
    return "d_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def trail_for_visits(visit_ids):
    cells = set()
    for node_id in visit_ids:
        node = decode_node(node_id)
        if node["prefix"] == "wild":
            cells.add((node["x"], node["y"]))
    resolution = 1 if len(cells) <= TRAIL_CELL_CAP else 5
    if resolution == 5:
        cells = {(x//5,y//5) for x,y in cells}
    by_row = {}
    for x,y in cells:
        by_row.setdefault(y,[]).append(x)
    rows=[]
    for y,xs in sorted(by_row.items()):
        runs=[]
        for x in sorted(xs):
            if runs and runs[-1][0]+runs[-1][1] == x:
                runs[-1][1] += 1
            else:
                runs.append([x,1])
        rows.append([y,runs])
    return dict(resolution_km=resolution, rows=rows)


def quest_markers(actor, lit):
    from web.webclient.presentation.map_quest_destinations import accepted_destinations_with_tracking
    from world.maps.district_partition import district_at
    from world.quests.definitions import QUEST_DEFINITION_REGISTRY

    destinations,tracked = accepted_destinations_with_tracking(actor)
    markers=[]
    for destination in destinations:
        definition=QUEST_DEFINITION_REGISTRY.get(destination.definition_key)
        if destination.world_cell is None or definition is None:
            continue
        cell=destination.world_cell
        approximate=district_at(cell) not in lit
        x,y=cell[0]+.5,cell[1]+.5
        if approximate:
            # Half-grid ties go toward positive infinity, independent of the
            # language's ties-to-even rounding. No exact-derived metadata.
            x,y=50*math.floor((x+25)/50),50*math.floor((y+25)/50)
        markers.append(dict(id=destination.quest_id,title=definition.display_name[:MAP_MAX_TITLE],
                            tracked=destination.quest_id in tracked,x=x,y=y,approximate=approximate))
    markers.sort(key=lambda row:(not row["tracked"],row["id"]))
    return markers[:WORLD_MAX_QUEST_MARKERS]


def assemble_world_map(*, visit_ids, current, markers):
    """Assemble with fresh containers; cached static bodies remain private."""
    from world.lore.map_districts import MAP_DISTRICT_REGISTRY

    lit={key for key,district in MAP_DISTRICT_REGISTRY.items() if district.landmark_node in visit_ids}
    permitted=[]
    visited=[]
    for owner,row,hidden,node_ids in geometry.place_geometry():
        seen=bool(visit_ids.intersection(node_ids))
        if seen:
            visited.append(dict(row))
        if seen or (not hidden and owner in lit):
            permitted.append((owner,dict(row)))
    districts=[]
    for key,body in geometry.district_geometry().items():
        row=dict(id=district_wire_id(key),lit=key in lit,outline=body["outline"])
        if key in lit:
            row.update(body)
            row["places"]=[place for owner,place in permitted if owner == key]
        districts.append(row)
    # The shared validator returns detached containers, including all nested
    # static geometry. No client/caller can mutate the geometry cache.
    return validate_world_map(dict(schema_version=WORLD_MAP_SCHEMA_VERSION,available=True,
        common=geometry.common_layer(),districts=districts,trail=trail_for_visits(visit_ids),
        visited_places=visited,current=dict(x=current[0],y=current[1]),quest_markers=markers))


def world_map_presenter(context):
    from world.lore.map_districts import MAP_DISTRICT_REGISTRY

    actor=context.actor
    current=geometry.current_point(actor)
    if current is None:
        raise PanelUnavailableError
    try:
        visits=persisted_visits(actor)
    except KnowledgeError as error:  # observability: ignore R2: unreadable knowledge is explicitly unavailable, never reset
        raise PanelUnavailableError from error
    ids={visit.node_id for visit in visits}
    lit={key for key,district in MAP_DISTRICT_REGISTRY.items() if district.landmark_node in ids}
    return assemble_world_map(visit_ids=ids,current=current,markers=quest_markers(actor,lit))
