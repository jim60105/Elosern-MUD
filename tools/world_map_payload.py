"""Measure the continental ``world_map`` payload from the shipped geography.

OpenSpec change ``transport-world-map-panel`` (world-map drawer design §5.3)
must measure the real continental payload before it selects the world-map
transport bound. No world presenter exists yet (``publish-world-map-panel``
owns it), so this tool assembles the logical body directly from the frozen
generated data the presenter will read:

* the common layer: the mainland boundary, the derived national borders and
  one label per nation at its capital cell;
* every district of the frozen partition with its smoothed outline, and for a
  lit district its name, landmark, claiming nations, terrain washes, the
  authored waterways and the summit ridge clipped to the district, and its
  non-hidden places (capitals, elven villages, harbours);
* synthetic player knowledge: the lit set, a trail, visited hidden places, the
  current position and accepted-quest markers.

Two cases are measured. ``representative`` is an early exploration: the
districts nearest the Altoria start are lit, a short walked trail, two
visited hidden places and three quest markers. ``worst`` is the supported
maximum: every district lit, a 1 km trail at the 20,000-run cap, every hidden
place visited and the full 64 markers with maximum-length titles and IDs.

Two parts of ``worst`` are estimates, not bounds. No terrain-wash geometry
is authored yet, so each lit district carries its own outline once per
terrain region present in it; a real wash also follows interior region
borders and may be longer. The continent has no authored road network yet,
so ``roads`` is empty. The selected bound keeps headroom for both, and the
world presenter (``publish-world-map-panel``) re-measures its real output
against it.

Every number is emitted as an integer whenever it is integral, so the
canonical bytes here equal the browser's canonical re-serialization of the
same decoded body.

Run ``uv run --locked python -m tools.world_map_payload`` to print the
measurements recorded in ``docs/development/map-panel-protocol.md``. The same
builders feed the focused protocol tests and the managed browser transport
fixture, so the recorded numbers and the tested payloads cannot drift apart.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections.abc import Iterable
from functools import cache
from pathlib import Path
from typing import Any

#: Terrain-region sampling step inside a district, in kilometres.
_REGION_SAMPLE_KM = 5
#: How many districts the representative exploration has lit.
REPRESENTATIVE_LIT_DISTRICTS = 12
#: The representative start (the Altoria capital cell, in kilometres).
_REPRESENTATIVE_START = (860, 1080)


def _km(metres: int) -> int | float:
    """Metres to kilometres, as an integer whenever the value is integral."""
    return metres // 1000 if metres % 1000 == 0 else metres / 1000


def _point(x: float, y: float) -> list[int | float]:
    return [int(x) if float(x).is_integer() else x, int(y) if float(y).is_integer() else y]


def canonical_bytes(payload: Any) -> bytes:
    """Canonical UTF-8 JSON: sorted keys, no whitespace, non-ASCII kept."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def wire_bytes(envelope: Any) -> int:
    """Bytes of one ``ui_update`` text frame as Evennia's portal writes it.

    The portal serializes ``[cmdname, args, kwargs]`` with ``json.dumps``
    defaults (``ensure_ascii=True``, spaced separators), so non-ASCII text
    costs six bytes per BMP code point on the socket.
    """
    return len(json.dumps(["ui_update", [envelope], {}]).encode("utf-8"))


# ---------------------------------------------------------------------------
# Static geography (read once per process).
# ---------------------------------------------------------------------------


@cache
def _district_rows() -> tuple[dict[str, Any], ...]:
    """One record per district of the frozen partition, in key order."""
    from world.lore.anchors import LOCAL_FRAME_ANCHOR_REGISTRY, world_position_m
    from world.lore.map_districts import MAP_DISTRICT_REGISTRY
    from world.maps.district_partition import district_outlines, frozen_partition

    outlines = district_outlines()
    partition = frozen_partition()
    rows = []
    for key in partition.district_keys:
        district = MAP_DISTRICT_REGISTRY[key]
        rings = [
            [_point(_km(ring[i]), _km(ring[i + 1])) for i in range(0, len(ring), 2)]
            for ring in outlines[key]
        ]
        for ring in rings:
            if ring[0] != ring[-1]:
                ring.append(list(ring[0]))
        kind, _, rest = district.landmark_node.partition(":")
        if kind == "wild":
            _, x, y = rest.split(":")
            landmark = (int(x) + 0.5, int(y) + 0.5)
        else:
            map_key, x, y = rest.split(":")
            if map_key not in LOCAL_FRAME_ANCHOR_REGISTRY:
                raise ValueError(f"grid landmark {district.landmark_node!r} has no local frame")
            east, north = world_position_m(map_key, (int(x), int(y)))
            landmark = (_km(east), _km(north))
        rows.append(
            {
                "key": key,
                "name": district.district_name_zh,
                "landmark_name": district.landmark_name_zh,
                "landmark": landmark,
                "outline": rings,
            }
        )
    return tuple(rows)


def _district_at_km(x: float, y: float) -> str | None:
    from world.maps.district_partition import district_at

    return district_at((math.floor(x), math.floor(y)))


@cache
def _district_regions() -> dict[str, tuple[str, ...]]:
    """Terrain regions present in each district, sampled on a 5 km lattice."""
    from world.lore.wilderness_regions import CONTINENT_FRAME_CELLS
    from world.maps.wilderness_provider import region_for_coordinates

    found: dict[str, set[str]] = {}
    half = _REGION_SAMPLE_KM // 2
    for y in range(half, CONTINENT_FRAME_CELLS, _REGION_SAMPLE_KM):
        for x in range(half, CONTINENT_FRAME_CELLS, _REGION_SAMPLE_KM):
            owner = _district_at_km(x, y)
            if owner is not None:
                found.setdefault(owner, set()).add(region_for_coordinates(x, y))
    return {key: tuple(sorted(regions)) for key, regions in found.items()}


def _district_nations() -> dict[str, tuple[str, ...]]:
    from world.maps.wilderness_provider import nominal_nation_for_coordinates

    nations = {}
    for row in _district_rows():
        x, y = row["landmark"]
        nations[row["key"]] = (nominal_nation_for_coordinates(math.floor(x), math.floor(y)),)
    return nations


def _clip_polylines(points: Iterable[tuple[float, float]]) -> dict[str, list[list[list[int | float]]]]:
    """Split one polyline into per-district pieces at 1 km resolution.

    Each segment is walked in unit steps; consecutive samples in the same
    district form one piece, which keeps the authored vertices it crosses and
    its two clip ends, so collinear interior samples are not emitted.
    """
    pieces: dict[str, list[list[list[int | float]]]] = {}
    vertices = list(points)
    current_key: str | None = None
    current: list[list[int | float]] = []
    # Whether ``current[-1]`` is a provisional interior sample (replaced by the
    # next sample of the same segment) rather than a kept vertex or clip end.
    provisional = False

    def flush() -> None:
        if current_key is not None and len(current) >= 2:
            pieces.setdefault(current_key, []).append(list(current))

    for (x0, y0), (x1, y1) in zip(vertices, vertices[1:]):
        steps = max(1, math.ceil(max(abs(x1 - x0), abs(y1 - y0))))
        for step in range(1 if current else 0, steps + 1):
            t = step / steps
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            key = _district_at_km(x, y)
            point = _point(round(x, 1), round(y, 1))
            if key != current_key:
                flush()
                current_key, current, provisional = key, [point], False
                continue
            if provisional:
                current[-1] = point
            else:
                current.append(point)
            # The segment's last sample is an authored vertex: keep it.
            provisional = step != steps
    flush()
    return pieces


@cache
def _district_lines() -> dict[str, dict[str, list[Any]]]:
    """Waterways and ridge pieces per district."""
    from world.maps.wilderness_provider import WATERWAY_ROUTES, national_borders

    lines: dict[str, dict[str, list[Any]]] = {}
    for route in WATERWAY_ROUTES.values():
        for key, pieces in _clip_polylines(route).items():
            lines.setdefault(key, {"rivers": [], "ridge": []})["rivers"].extend(pieces)
    ridge = [border.points for border in national_borders() if border.nation_keys != ("altoria", "valhalla")]
    for points in ridge:
        for key, pieces in _clip_polylines(points).items():
            lines.setdefault(key, {"rivers": [], "ridge": []})["ridge"].extend(pieces)
    return lines


@cache
def _places() -> tuple[tuple[str, dict[str, Any]], ...]:
    """``(district key, place row)`` for every authored named place."""
    from world.lore.anchors import ANCHOR_GEOGRAPHY_REGISTRY, ANCHOR_REGISTRY, AnchorKind
    from world.lore.wilderness_regions import HARBOR_SITE_REGISTRY

    kinds = {AnchorKind.CAPITAL: "capital", AnchorKind.ELVEN_VILLAGE: "settlement", AnchorKind.DUNGEON: "hidden"}
    rows = []
    for key, geography in sorted(ANCHOR_GEOGRAPHY_REGISTRY.items()):
        anchor = ANCHOR_REGISTRY[key]
        x, y = geography.cell
        rows.append(
            (
                _district_at_km(x + 0.5, y + 0.5),
                {"id": key, "name": anchor.display_name_zh, "kind": kinds[anchor.kind], "x": x + 0.5, "y": y + 0.5},
            )
        )
    for key, site in sorted(HARBOR_SITE_REGISTRY.items()):
        x, y = site.cell
        rows.append(
            (
                _district_at_km(x + 0.5, y + 0.5),
                {"id": key, "name": site.display_name, "kind": "harbour", "x": x + 0.5, "y": y + 0.5},
            )
        )
    return tuple(rows)


def common_layer() -> dict[str, Any]:
    """The static common-knowledge layer every player receives."""
    from world.lore.anchors import ANCHOR_GEOGRAPHY_REGISTRY
    from world.lore.nations import NATION_REGISTRY
    from world.lore.wilderness_regions import MAINLAND_BOUNDARY_KM
    from world.maps.wilderness_provider import national_borders

    coastline = [_point(x, y) for x, y in MAINLAND_BOUNDARY_KM]
    coastline.append(list(coastline[0]))
    nations = []
    for key, nation in sorted(NATION_REGISTRY.items()):
        x, y = ANCHOR_GEOGRAPHY_REGISTRY[nation.capital_anchor_key].cell
        nations.append({"id": key, "name": nation.display_name_zh, "x": x + 0.5, "y": y + 0.5})
    return {
        "coastline": coastline,
        "borders": [[_point(x, y) for x, y in border.points] for border in national_borders()],
        "nations": nations,
    }


def district_keys() -> tuple[str, ...]:
    return tuple(row["key"] for row in _district_rows())


def _district_body(row: dict[str, Any], lit: bool) -> dict[str, Any]:
    if not lit:
        return {"id": row["key"], "lit": False, "outline": row["outline"]}
    lines = _district_lines().get(row["key"], {"rivers": [], "ridge": []})
    lx, ly = row["landmark"]
    return {
        "id": row["key"],
        "lit": True,
        "name": row["name"],
        "outline": row["outline"],
        "landmark": {"name": row["landmark_name"], "x": lx, "y": ly},
        "nations": list(_district_nations()[row["key"]]),
        "terrain": [
            {"region": region, "polygons": row["outline"]} for region in _district_regions().get(row["key"], ())
        ],
        "rivers": lines["rivers"],
        "ridge": lines["ridge"],
        "roads": [],
        "places": [place for owner, place in _places() if owner == row["key"] and place["kind"] != "hidden"],
    }


def _trail_rows(cells: Iterable[tuple[int, int]]) -> list[list[Any]]:
    by_row: dict[int, list[int]] = {}
    for x, y in set(cells):
        by_row.setdefault(y, []).append(x)
    rows = []
    for y in sorted(by_row):
        runs: list[list[int]] = []
        for x in sorted(by_row[y]):
            if runs and runs[-1][0] + runs[-1][1] == x:
                runs[-1][1] += 1
            else:
                runs.append([x, 1])
        rows.append([y, runs])
    return rows


def _line_cells(waypoints: list[tuple[int, int]]) -> list[tuple[int, int]]:
    cells = []
    for (x0, y0), (x1, y1) in zip(waypoints, waypoints[1:]):
        steps = max(1, abs(x1 - x0), abs(y1 - y0))
        for step in range(steps + 1):
            t = step / steps
            cells.append((round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t)))
    return cells


def build_world_map(
    *,
    lit: Iterable[str],
    trail: dict[str, Any],
    visited_places: list[dict[str, Any]],
    current: tuple[float, float],
    quest_markers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assemble one logical ``world_map`` body (schema version 1)."""
    lit_keys = set(lit)
    return _integral({
        "schema_version": 1,
        "available": True,
        "common": common_layer(),
        "districts": [_district_body(row, row["key"] in lit_keys) for row in _district_rows()],
        "trail": trail,
        "visited_places": visited_places,
        "current": {"x": current[0], "y": current[1]},
        "quest_markers": quest_markers,
    })


def _integral(value: Any) -> Any:
    """A copy with every integral float written as an integer."""
    if isinstance(value, dict):
        return {key: _integral(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_integral(child) for child in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _hidden_places() -> list[dict[str, Any]]:
    return [place for _, place in _places() if place["kind"] == "hidden"]


def representative_payload() -> dict[str, Any]:
    """An early exploration out of the Altoria capital."""
    sx, sy = _REPRESENTATIVE_START
    nearest = sorted(
        _district_rows(),
        key=lambda row: (row["landmark"][0] - sx) ** 2 + (row["landmark"][1] - sy) ** 2,
    )[:REPRESENTATIVE_LIT_DISTRICTS]
    walked = _line_cells([(860, 1080), (1100, 1150), (1340, 1220), (1150, 1363), (830, 1370), (480, 1160), (600, 800)])
    return build_world_map(
        lit=[row["key"] for row in nearest],
        trail={"resolution_km": 1, "rows": _trail_rows(walked)},
        visited_places=_hidden_places()[:2],
        current=(600.5, 800.5),
        quest_markers=[
            {"id": "commission_1", "title": "護送商隊前往河港", "tracked": True, "x": 301.5, "y": 350.5, "approximate": False},
            {"id": "commission_2", "title": "調查山腳的異響", "tracked": False, "x": 1300, "y": 1200, "approximate": True},
            {"id": "commission_3", "title": "採集林地藥草", "tracked": False, "x": 700, "y": 1250, "approximate": True},
        ],
    )


#: The 1 km trail cap (world-map drawer design §5.3): above it the server
#: downsamples to 5 km cells, so a 1 km trail never holds more runs.
TRAIL_CELL_CAP = 20_000


def _worst_trail() -> dict[str, Any]:
    """20,000 isolated 1 km cells (one run each) with four-digit columns."""
    cells = []
    row, column = 1000, 1000
    while len(cells) < TRAIL_CELL_CAP:
        cells.append((column, row))
        column += 2
        if column >= 2600:
            row, column = row + 1, 1000
    return {"resolution_km": 1, "rows": _trail_rows(cells)}


def worst_payload() -> dict[str, Any]:
    """The supported maximum: everything lit, every bounded list at its cap."""
    from web.webclient.presentation.map_panels import MAP_MAX_QUEST_ID, MAP_MAX_TITLE, WORLD_MAX_QUEST_MARKERS

    markers = []
    for index in range(WORLD_MAX_QUEST_MARKERS):
        marker_id = f"commission_{index:02d}_" + "x" * (MAP_MAX_QUEST_ID - 14)
        title = ("遙遠邊境的委託" * 20)[:MAP_MAX_TITLE]
        if index % 2:
            markers.append({"id": marker_id, "title": title, "tracked": index == 1, "x": 1234.5 + index, "y": 1456.5, "approximate": False})
        else:
            markers.append({"id": marker_id, "title": title, "tracked": False, "x": 1250, "y": 1450, "approximate": True})
    return build_world_map(
        lit=district_keys(),
        trail=_worst_trail(),
        visited_places=_hidden_places(),
        current=(1999.5, 1099.5),
        quest_markers=markers,
    )


def measure() -> dict[str, dict[str, int]]:
    """Canonical and on-socket sizes of each measured case."""
    common = common_layer()
    unlit = build_world_map(
        lit=(), trail={"resolution_km": 1, "rows": []}, visited_places=[], current=(860.5, 1080.5), quest_markers=[]
    )
    cases = {"common_layer": common, "all_unlit": unlit, "representative": representative_payload(), "worst": worst_payload()}
    return {name: {"canonical_bytes": len(canonical_bytes(body))} for name, body in cases.items()}


def _bootstrap() -> None:
    """Configure Django and Evennia for a standalone run (no database access)."""
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
    import django

    django.setup()
    import evennia

    evennia._init()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print machine-readable output")
    args = parser.parse_args(argv)
    _bootstrap()
    results = measure()
    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        for name, row in results.items():
            print(f"{name:16} {row['canonical_bytes']:>10,} canonical bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
