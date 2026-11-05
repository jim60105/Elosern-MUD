"""Shared probes and fixtures for the on-demand ``area_map`` presenter and the ``map.view`` action."""

import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from web.webclient.presentation.area_map import area_map_presenter
from web.webclient.presentation.map_panels import AREA_MAX_EDGES, AREA_MAX_NODES, AREA_MAX_QUEST_MARKERS
from web.webclient.presentation.registry import PresenterSpec
from ..test_local_map._support import EAST_GATE_XYZ, _context, _live


ROOT = Path(__file__).resolve().parents[5]

NODE_TEST = "web/static/webclient/js/tests/protocol_area_map.test.js"

def _render(actor):
    return area_map_presenter(_context(actor))

def _wilderness_fixture_maps() -> tuple[str, ...]:
    """The settlement maps the wilderness area cases actually stand on.

    Every window is read at the city gate's approach cell, and the hidden
    point entrance's gate room is named by the disclosure case; no other
    settlement map is read here.
    """
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

    point = next(
        candidate
        for candidate in WILDERNESS_ENTRY_REGISTRY.values()
        if candidate.is_point_shape
    )
    return tuple(sorted({EAST_GATE_XYZ[2], point.gates[0].destination.map_id}))

def _by_id(payload):
    return {node["id"]: node for node in payload["nodes"]}

def _edge_set(payload):
    return {frozenset((edge["source"], edge["destination"])) for edge in payload["edges"]}

def _decode_overview(payload):
    """``{(coarse_x, coarse_y): facts | None}`` of one overview window."""
    overview = payload["district"]
    window = overview["window"]
    cells = {}
    for row, runs in enumerate(overview["rows"]):
        column = 0
        for run in runs:
            for offset in range(run["length"]):
                cell = (window["min_x"] + column + offset, window["min_y"] + row)
                cells[cell] = None if run["kind"] == "unknown" else {
                    key: value for key, value in run.items() if key not in ("length", "kind")
                }
            column += run["length"]
    return cells

def _js_accepts(payload) -> bool:
    script = (
        "const fs=require('node:fs');"
        "const P=require('./web/static/webclient/js/elosern/protocol.js');"
        "try{P.validateMapPanel('area_map',JSON.parse(fs.readFileSync(0,'utf8')));"
        "process.stdout.write('ok')}catch(e){process.stdout.write('no:'+e.message)}"
    )
    result = subprocess.run(
        ["node", "-e", script],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        cwd=ROOT,
        check=True,
    )
    return result.stdout == "ok"

def _undirected(pairs):
    adjacency = {}
    for a, b in pairs:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    return adjacency

def _decode_rows(payload):
    """Window offset -> run facts (``None`` for unknown) from the RLE rows."""
    window = payload["window"]
    cells = {}
    for row_index, runs in enumerate(payload["rows"]):
        column = 0
        for run in runs:
            facts = None if run["kind"] == "unknown" else {k: v for k, v in run.items() if k != "length"}
            for offset in range(run["length"]):
                cells[(window["min_x"] + column + offset, window["min_y"] + row_index)] = facts
            column += run["length"]
    return cells

def _knowledge(visits, visited_grid=()):
    """A synthetic schema-2 record: ``visits`` maps a wild cell to its sight."""
    from world.rules.map_knowledge import CHUNK_CELLS, SCHEMA_VERSION

    name = _live("world.maps.wilderness_provider", "WILDERNESS_NAME")
    chunks = {}
    for (x, y), sight in visits.items():
        chunk = chunks.setdefault(f"{x // CHUNK_CELLS}:{y // CHUNK_CELLS}", {})
        chunk[str((y % CHUNK_CELLS) * CHUNK_CELLS + (x % CHUNK_CELLS))] = {
            "first_seen_tick": 1,
            "last_seen_tick": 1,
            "sight": sight,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "visited": {node_id: {"first_seen_tick": 1, "last_seen_tick": 1} for node_id in visited_grid},
        "wilderness": {name: chunks},
    }

def _synthetic_visits(start, count):
    """``count`` deterministic visits: a dense block around the window plus a
    far scatter across the frame, with sights 0..8."""
    max_x = _live("world.maps.wilderness_provider", "WILDERNESS_MAX_X")
    max_y = _live("world.maps.wilderness_provider", "WILDERNESS_MAX_Y")
    visits = {}
    sx, sy = start
    for dy in range(-30, 31):
        for dx in range(-30, 31):
            if (dx * 7 + dy * 3) % 4 == 0:
                visits[(sx + dx, sy + dy)] = (dx * dx + dy) % 9
    seed = 12345
    while len(visits) < count:
        seed = (seed * 1103515245 + 12345) % (2**31)
        x = seed % (max_x + 1)
        seed = (seed * 1103515245 + 12345) % (2**31)
        y = seed % (max_y + 1)
        visits.setdefault((x, y), seed % 9)
    return visits

class _Session:
    def __init__(self, puppet):
        self.sent = []
        self.puppet = puppet
        self.ndb = SimpleNamespace()
        self.sessid = 1

    def msg(self, **kwargs):
        self.sent.append(kwargs)

    def frames(self, name):
        return [call[name][0][0] for call in self.sent if name in call]

class _Calendar:
    year, season_index, season_name, day_in_season, hour, minute, second = 1, 0, "春", 1, 8, 0, 0

def _status_spec():
    return PresenterSpec("status", 1, ("missing_data", "無法讀取"), lambda ctx: {"schema_version": 1, "available": True})

def _largest_grid_body(labels: int = 16) -> dict:
    """A schema-valid grid area at the node and edge ceilings."""
    map_key = "t_large"
    width = 32

    def node_id(i):
        return f"grid:{map_key}:{(i % width) * 137}:{(i // width) * 211}"

    nodes = [
        {
            "id": node_id(i),
            "label": "合" * labels,
            "x": (i % width) * 137,
            "y": (i // width) * 211,
            "visibility": "current" if i == 0 else ("visited" if i % 2 else "seen"),
            "gateway": {"leads_to": "合成荒野"} if i % 97 == 0 else None,
            "action": {"kind": "move", "exit_ref": str(100000 + i), "destination": node_id(i)} if 0 < i < 9 else None,
        }
        for i in range(AREA_MAX_NODES)
    ]
    pairs = set()
    step = 1
    while len(pairs) < AREA_MAX_EDGES:
        for i in range(AREA_MAX_NODES):
            j = (i + step) % AREA_MAX_NODES
            pairs.add((min(i, j), max(i, j)))
            if len(pairs) == AREA_MAX_EDGES:
                break
        step += 1
    edges = [{"source": node_id(a), "destination": node_id(b)} for a, b in sorted(pairs)]
    markers = [
        {
            "id": f"t_q{i:061d}",
            "title": "委" * 128,
            "tracked": i == 0,
            "destination": {"kind": "bearing", "bearing_deg": 359.9, "distance_km": 2699.9},
        }
        for i in range(AREA_MAX_QUEST_MARKERS)
    ]
    return {
        "schema_version": 4,
        "available": True,
        "layer": "grid",
        "map_id": map_key,
        "frame": {"key": map_key, "unit": "m"},
        "current_node": node_id(0),
        "title": "合成大城",
        "nodes": nodes,
        "edges": edges,
        "quest_markers": markers,
    }
