"""Measure actual production world-map assembly and its finite trail extremes.

Run with ``uv run --locked python -m tools.world_map_payload --json``.
Geometry, lighting, place filtering and row runs come from the production
presenter. This tool supplies exploration histories and maximal wire markers;
it does not contain a second implementation of map geometry or disclosure.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

REPRESENTATIVE_LIT_DISTRICTS = 12


def canonical_bytes(payload):
    return json.dumps(payload,ensure_ascii=False,separators=(",",":"),sort_keys=True).encode("utf-8")


def wire_bytes(envelope):
    return len(json.dumps(["ui_update",[envelope],{}]).encode("utf-8"))


def district_keys():
    from world.lore.map_districts import MAP_DISTRICT_REGISTRY
    return tuple(sorted(MAP_DISTRICT_REGISTRY))


def _markers():
    from web.webclient.presentation.map_panels import MAP_MAX_QUEST_ID,MAP_MAX_TITLE,WORLD_MAX_QUEST_MARKERS
    return [dict(id=f"commission_{index:02d}_"+"x"*(MAP_MAX_QUEST_ID-14),
                 title=("遙遠邊境的委託"*20)[:MAP_MAX_TITLE],tracked=index==0,
                 x=1250,y=1450,approximate=True) for index in range(WORLD_MAX_QUEST_MARKERS)]


def _all_visits():
    from web.webclient.presentation.world_map_geometry import place_geometry
    from world.lore.map_districts import landmark_node_ids
    visits=set(landmark_node_ids().values())
    for _,_,_,ids in place_geometry():
        visits.update(ids)
    return visits


def _assemble(visits,markers):
    from web.webclient.presentation.world_map import assemble_world_map
    return assemble_world_map(visit_ids=visits,current=(1999.5,1099.5),markers=markers)


def representative_payload():
    from web.webclient.presentation.world_map_geometry import world_node_point
    from world.lore.map_districts import MAP_DISTRICT_REGISTRY, landmark_node_ids
    landmarks=landmark_node_ids()
    districts=sorted(MAP_DISTRICT_REGISTRY.values(),key=lambda row:sum(
        (a-b)**2 for a,b in zip(world_node_point(landmarks[row.key]),(860.5,1080.5))))
    return _assemble({landmarks[row.key] for row in districts[:REPRESENTATIVE_LIT_DISTRICTS]},[])


def one_km_payload():
    """All content and exactly 20,000 distinct wilderness visits, untruncated."""
    from world.rules.map_knowledge import encode_wild
    from world.maps.wilderness_provider import WILDERNESS_NAME
    visits=_all_visits()
    count=sum(node.startswith("wild:") for node in visits)
    for y in range(1000,2700):
        for x in range(1000,2600,2):
            if count >= 20000:
                return _assemble(visits,_markers())
            node=encode_wild(WILDERNESS_NAME,x,y)
            if node not in visits:
                visits.add(node)
                count+=1
    raise AssertionError("fixture failed to fill its finite trail")


def worst_payload():
    """All content with maximal separated 5 km runs over the full frame.

    Each even coarse column is visited in every row, producing 145,800 runs.
    Landmarks/places are also real visits and may merge a few adjacent runs.
    The fixture deliberately includes off-mainland coordinates because map
    knowledge's grammar accepts them, so the transport bound covers every
    valid stored record rather than assuming a walkable-only history.
    """
    from world.rules.map_knowledge import encode_wild
    from world.maps.wilderness_provider import WILDERNESS_NAME
    visits=_all_visits()
    visits.update(encode_wild(WILDERNESS_NAME,x,y) for y in range(0,2700,5) for x in range(0,2700,10))
    return _assemble(visits,_markers())


def measure():
    from web.webclient.presentation.world_map_geometry import common_layer
    cases=dict(common_layer=common_layer(),all_unlit=_assemble(set(),[]),
               representative=representative_payload(),one_km=one_km_payload(),worst=worst_payload())
    return {name:dict(canonical_bytes=len(canonical_bytes(body))) for name,body in cases.items()}


def _bootstrap():
    root=Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0,str(root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE","server.conf.settings")
    import django
    django.setup()
    import evennia
    evennia._init()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json",action="store_true")
    args=parser.parse_args(argv)
    _bootstrap()
    results=measure()
    if args.json:
        print(json.dumps(results,indent=2,sort_keys=True))
    else:
        for name,row in results.items():
            print(f"{name:16} {row['canonical_bytes']:>10,} canonical bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
