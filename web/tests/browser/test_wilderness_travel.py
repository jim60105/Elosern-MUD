"""Wilderness travel stage acceptance (wilderness-travel-interface, task 4.1;
wilderness-travel-map-ui, task 3.1; wilderness-travel-walking-ui, task 3.1).

The journeys run in the live client against injected committed state: the
room's panels arrive through the store's own ``receive`` seam, and a
responder on the live sender holds every ``map.view`` the travel stage sends
so the test answers it with its action result and a synthetic schema-2
wilderness ``area_map`` in either order. The walking journeys hold every
``explore.move`` the same way and answer it with its result and the next
cell's panels. Nothing here names shipped content.
"""

from __future__ import annotations

import os
import tempfile

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest, ui_scale
from .browser_helpers import (
    inject_snapshot,
    scene_block,
    store_state,
    valid_status_panel,
    wait_for_store_state,
)

WINDOW = 41
CX, CY = 60, 80
WILD = "wilderness:合成荒原:%d,%d" % (CX, CY)
TOWN = "grid:t_synth_map:2,0"
SHOTS = os.environ.get(
    "ELOSERN_TRAVEL_SHOTS", os.path.join(tempfile.gettempdir(), "wilderness-travel-shots")
)


def _art(subject: str) -> dict:
    return {
        "schema_version": 4,
        "available": True,
        "kind": "scene",
        "scene": scene_block("/art/scene/t_travel.png", subject, label="合成荒原", alt="合成荒原"),
        "portrait_catalog": {},
    }


def _run(terrain: str) -> dict:
    return {
        "length": 1, "kind": "terrain", "terrain": terrain, "passable": terrain != "water",
        "band": 3, "tier": 0, "road": False, "ford": False,
    }


def _rows(known) -> list:
    """Schema-2 rows (south to north) from ``known(col, row)``, which returns a
    terrain class or None for an unknown cell; equal neighbours merge."""
    rows = []
    for row in range(WINDOW):
        runs: list = []
        for col in range(WINDOW):
            terrain = known(col, row)
            run = _run(terrain) if terrain else {"length": 1, "kind": "unknown"}
            last = runs[-1] if runs else None
            if last and {**last, "length": 0} == {**run, "length": 0}:
                last["length"] += 1
            else:
                runs.append(run)
        rows.append(runs)
    return rows


def _fact_area(cx: int = CX, cy: int = CY) -> dict:
    """A window whose west half (columns 0..20) is revealed: woodland on the
    northern rows, a water line along row 18, open ground elsewhere; the
    east half is unknown."""

    def known(col, row):
        if col > 20:
            return None
        if row == 18:
            return "water"
        return "woodland" if row > 24 else "open_ground"

    area = _area(cx, cy)
    area["rows"] = _rows(known)
    return area


def _area(cx: int = CX, cy: int = CY) -> dict:
    """A schema-2 wilderness window centred on ``(cx, cy)``: a 3 x 3 revealed
    open-ground block around the party, everything else unknown."""
    rows = []
    for row in range(WINDOW):
        y = cy - 20 + row
        if abs(y - cy) <= 1:
            rows.append(
                [
                    {"length": 19, "kind": "unknown"},
                    {
                        "length": 3, "kind": "terrain", "terrain": "open_ground", "passable": True,
                        "band": 3, "tier": 0, "road": False, "ford": False,
                    },
                    {"length": 19, "kind": "unknown"},
                ]
            )
        else:
            rows.append([{"length": WINDOW, "kind": "unknown"}])
    current = "wild:elosern:%d:%d" % (cx, cy)
    return {
        "schema_version": 2,
        "available": True,
        "layer": "wilderness",
        "map_id": "elosern",
        "frame": {"key": "elosern", "unit": "km"},
        "current_node": current,
        "title": "合成荒原",
        "nodes": [
            {
                "id": current, "label": "合成荒原", "x": cx + 0.5, "y": cy + 0.5,
                "visibility": "current", "visited": True, "gateway": None, "action": None,
            }
        ],
        "edges": [],
        "quest_markers": [],
        "district_name": "合成東麓",
        "cell_km": 1,
        "window": {"min_x": cx - 20, "min_y": cy - 20, "width": WINDOW, "height": WINDOW},
        "rows": rows,
        "light_phase": "day",
        "ground_radius": 1,
        "entities": [],
        "sightings": [],
    }


def _row(identity: str, name: str, reserve: int, stage: str = "normal", label: str = "合成充沛", asleep: bool = False) -> dict:
    return {
        "identity": identity, "name": name, "reserve_percent": reserve, "stage": stage, "label": label,
        "severity": "informational" if stage in ("normal", "sleeping") else "harmful",
        "restriction": "沉睡中，無法行動" if asleep else None, "asleep": asleep,
    }


def _party(companions: list[tuple[int, str]]) -> dict:
    def slot(identity, name, role):
        return {
            "identity": identity, "display_name": name, "portrait_ref": None,
            "hp_current": 100, "hp_maximum": 100, "mp_current": 50, "mp_maximum": 50,
            "sp_current": 40, "sp_maximum": 40, "role": role, "knocked_out": False, "unread": False,
            "bond_stage": None if role == "commander" else "初識",
            "membership": None if role == "commander" else {"general": True, "temporary_commissions": []},
        }

    return {
        "schema_version": 3,
        "available": True,
        "general_quota": {"used": len(companions), "limit": 4},
        "viewed_member_id": 1,
        "slots": [slot(1, "合成主角", "commander"), *[slot(i, n, "companion") for i, n in companions]],
    }


# Holds every map.view on the live sender (recorded, never forwarded) and
# answers one held request in the requested order.
_HOLD_MAPS = """() => {
  const store = window.__elosernBridge.store;
  if (window.__travelHold) return;
  const sender = store.getSender();
  const original = sender.sendAction.bind(sender);
  window.__travelHold = { views: [] };
  sender.sendAction = (env) => {
    if (env && env.action_id === 'map.view') {
      window.__travelHold.views.push(env);
      return undefined;
    }
    return original(env);
  };
}"""

_ANSWER = """([area, order, requestIndex]) => {
  const store = window.__elosernBridge.store;
  const env = window.__travelHold.views[requestIndex];
  const v = store.view;
  const revision = v.revision + 1;
  const result = () => store.receive(v.generation, 'ui_action_result', [{
    protocol_version: 1, presentation_epoch: v.epoch, request_id: env.request_id,
    outcome: 'success', code: 'completed', message: '地圖已更新。', presentation_revision: revision,
  }], {});
  const body = () => store.receive(v.generation, 'ui_update', [{
    protocol_version: 1, presentation_epoch: v.epoch, base_revision: revision - 1, revision,
    mode: v.mode, panels: { area_map: area }, removed_panels: [], layout_version: v.layoutVersion,
    server_time: v.serverTime,
  }], {});
  const outcomes = order === 'result-first' ? [result(), body()] : [body(), result()];
  return outcomes.map((o) => !!o.accepted);
}"""


def _travel(page) -> dict:
    return page.evaluate("() => JSON.parse(JSON.stringify(window.__elosernBridge.store.view.travel))")


def _held(page) -> int:
    return page.evaluate("() => window.__travelHold.views.length")


class _TravelStage(BrowserAcceptanceTest):
    """The shared travel-stage journey helpers (no tests of its own)."""

    def _enter(self, page, panels: dict) -> None:
        page.evaluate(_HOLD_MAPS)
        inject_snapshot(page, panels)
        wait_for_store_state(page, lambda s: (s.get("panels") or {}).get("art", {}).get("available") is True)

    def _wait_views(self, page, count: int) -> None:
        page.wait_for_function("(n) => window.__travelHold.views.length >= n", arg=count, timeout=15000)

    def _answer(self, page, index: int, order: str = "body-first", area: dict | None = None) -> None:
        accepted = page.evaluate(_ANSWER, [area or _area(), order, index])
        self.assertEqual(accepted, [True, True])

    def _wait_ready(self, page) -> None:
        try:
            page.wait_for_selector('[data-testid="travel-map"][data-map-status="ready"]', timeout=15000)
        except Exception as error:  # observability: ignore R2: test diagnostics re-raised with the live state
            state = page.evaluate(
                "() => { const v = window.__elosernBridge.store.view; return JSON.stringify({"
                " status: v.travel.mapStatus, layout: v.travel.layout, revision: v.revision,"
                " pub: v.mapPublications, inFlight: v.dispatch.inFlight, result: v.lastActionResult,"
                " held: window.__travelHold.views.map((e) => e.request_id) }); }"
            )
            raise AssertionError(f"travel map not ready: {state}") from error

    def _shoot(self, page, name: str) -> None:
        os.makedirs(SHOTS, exist_ok=True)
        page.screenshot(path=os.path.join(SHOTS, name))



class TravelLayoutTests(_TravelStage):
    """The travel layout, its own area refresh and the party medallions."""

    @covers_requirement("webclient-travel-layout::wilderness-presentation-follows-committed-room-identity")
    def test_settlement_gate_layout(self):
        """A committed wilderness identity selects travel and a settlement
        identity restores the ordinary stage, at both acceptance viewports."""
        for viewport in ((1451, 790), (2560, 1440)):
            page = self.logged_in_page(viewport)
            self._enter(page, {"status": valid_status_panel("合成主角", "42"), "art": _art(WILD)})
            page.wait_for_selector('[data-testid="travel-map"]', timeout=15000)
            self._wait_views(page, 1)
            self._answer(page, 0)
            self._wait_ready(page)
            stage = page.locator('[data-testid="elosern-stage"]')
            self.assertEqual(stage.get_attribute("data-travel"), "true")
            # Both portrait anchors are empty and out of the layout.
            for anchor in ("anchor-actor-left", "anchor-actor-right"):
                self.assertEqual(page.locator(f'[data-testid="{anchor}"] [data-testid="stage-actor"]').count(), 0)
                self.assertFalse(page.locator(f'[data-testid="{anchor}"]').is_visible())
            # The medallions stand in the vitals column, inside the stage, above
            # the band; the place card stands alone in the map column.
            medallions = page.locator('[data-testid="party-medallions"]').bounding_box()
            band = page.locator('[data-testid="stage-band"]').bounding_box()
            self.assertIsNotNone(medallions)
            self.assertLessEqual(medallions["y"] + medallions["height"], band["y"] + 1)
            self.assertEqual(page.locator('[data-testid="anchor-map"] .local-map').count(), 0)
            self.assertTrue(page.locator('[data-testid="place-card"]').is_visible())
            # A visible focus ring survives in the travel stage: the map
            # itself is the focus stop.
            page.locator('[data-testid="travel-map"]').focus()
            self.assertTrue(page.evaluate("() => document.activeElement.matches('[data-testid=\"travel-map\"]:focus-visible')"))
            self._shoot(page, "travel-%dx%d.png" % viewport)

            # Through the gate: the settlement's identity restores the stage.
            inject_snapshot(page, {"status": valid_status_panel("合成主角", "42"), "art": _art(TOWN)})
            page.wait_for_selector('[data-testid="travel-map"]', state="detached", timeout=15000)
            self.assertIsNone(stage.get_attribute("data-travel"))
            self.assertEqual(page.locator('[data-testid="party-medallions"]').count(), 0)
            self.assertFalse(_travel(page)["layout"])
            page.close()

    @covers_requirement("webclient-travel-layout::travel-area-refresh-follows-committed-state")
    def test_refresh_adoption(self):
        """Only the current request's own result and body make the stage
        ready, in either order; a same-position snapshot recovers once."""
        page = self.logged_in_page((1451, 790))
        self._enter(page, {"status": valid_status_panel("合成主角", "42"), "art": _art(WILD)})
        self._wait_views(page, 1)
        held = page.evaluate("() => window.__travelHold.views.map((e) => e.payload)")
        self.assertEqual(held, [{"scope": "area"}])
        self.assertEqual(_travel(page)["mapStatus"], "refreshing")
        self._answer(page, 0, "result-first")
        self._wait_ready(page)
        self.assertEqual(_travel(page)["map"]["party"], {"x": CX, "y": CY})

        # An external full snapshot at the same position and time asks once.
        inject_snapshot(page, {"status": valid_status_panel("合成主角", "42"), "art": _art(WILD)})
        self._wait_views(page, 2)
        self.assertEqual(_travel(page)["mapStatus"], "refreshing")
        self._answer(page, 1, "body-first")
        self._wait_ready(page)
        # The owner's own completion never asks again.
        page.wait_for_timeout(600)
        self.assertEqual(_held(page), 2)
        state = store_state(page)
        self.assertIsNone((state.get("dispatch") or {}).get("inFlight"))

    @covers_requirement("webclient-travel-layout::medallions-identify-committed-physiological-subjects")
    def test_medallion_subjects(self):
        """Each present member joins its own body-keyed reserve and posture;
        a member with no committed row is not with the party."""
        status = valid_status_panel("合成主角", "42")
        status["fatigue"] = [
            _row("42", "合成主角", 73),
            _row("101", "合成甲", 2, "forced_sleep", "合成昏睡", asleep=True),
            _row("102", "合成乙", 38, "moderate", "合成疲勞"),
        ]
        page = self.logged_in_page((1451, 790))
        self._enter(page, {"status": status, "art": _art(WILD), "party": _party([(101, "合成甲"), (102, "合成乙"), (103, "合成丙")])})
        page.wait_for_selector('[data-testid="party-medallions"]', timeout=15000)
        medallions = page.locator('[data-testid="party-medallion"]')
        identities = medallions.evaluate_all("(els) => els.map((el) => el.dataset.identity)")
        self.assertEqual(identities, ["42", "101", "102"])
        facts = medallions.evaluate_all(
            "(els) => els.map((el) => [el.dataset.controlled, el.dataset.asleep,"
            " el.querySelector('[data-testid=\"party-medallion__bar\"]').dataset.reserve])"
        )
        self.assertEqual(facts, [["true", "false", "73"], ["false", "true", "2"], ["false", "false", "38"]])
        self.assertEqual(
            medallions.nth(2).locator('[data-testid="party-medallion__sr"]').text_content(),
            "合成乙：精力 38%（合成疲勞）",
        )
        self.assertEqual(page.locator('[data-testid="party-medallion__moon"]').count(), 1)
        # The dock never repeats the medallions' fatigue lines.
        self.assertEqual(page.locator('[data-testid="status-panel__fatigue"]').count(), 0)


# The canvas's alpha at the centre of window cell (col, row), rows south to
# north, and the largest alpha at or east of a canvas x.
_ALPHA = """([cells, eastOf]) => {
  const canvas = document.querySelector('[data-testid="travel-map__canvas"]');
  const ctx = canvas.getContext('2d');
  const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  const s = canvas.width / 41;
  const at = ([col, row]) => data[(((40 - row) * s + s / 2) * canvas.width + col * s + s / 2) * 4 + 3];
  let east = 0;
  for (let j = 0; j < canvas.height; j += 1) {
    for (let i = eastOf; i < canvas.width; i += 1) east = Math.max(east, data[(j * canvas.width + i) * 4 + 3]);
  }
  return { size: [canvas.width, canvas.height], alpha: cells.map(at), east };
}"""

# A digest of every canvas pixel, to prove an operation left them alone.
_DIGEST = """() => {
  const canvas = document.querySelector('[data-testid="travel-map__canvas"]');
  const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
  let h = 2166136261;
  for (let k = 0; k < data.length; k += 7) h = Math.imul(h ^ data[k], 16777619);
  return h >>> 0;
}"""

_PAINTS = "() => window.__elosernBridge.travelPaint.stats().count"

# The repaint benchmark: the real painter on a rich synthetic 41 x 41 grid
# (bands, tiers, roads, a river with a ford, woods, two districts, a
# settlement footprint, phase and radius), 5 warm-up paints, then 20 timed
# state changes (party, reveal, phase, radius and flags all move).
_BENCH = """() => {
  const S = 12, N = 41, phases = ['day', 'dusk', 'night', 'dawn'];
  const grid = (k) => {
    const ox = 1000 + k, oy = 2000 + (k % 3);
    const party = { x: ox + 20, y: oy + 20 };
    const cells = [];
    for (let row = 0; row < N; row += 1) {
      for (let col = 0; col < N; col += 1) {
        const x = ox + col, y = oy + row;
        const known = (x - party.x) ** 2 + (y - party.y) ** 2 < (14 + (k % 5)) ** 2 || (col + row * 3 + k) % 11 === 0;
        const river = Math.abs(y - (2012 + 3 * Math.sin(x * 0.2))) < 0.6;
        const road = y === 2020 + Math.round((x - 1020) * 0.4);
        const wood = Math.sin(x * 0.37) * Math.cos(y * 0.29) > 0.45;
        const terrain = river ? 'water' : x < ox + 5 && y < oy + 5 ? 'settlement' : wood ? 'woodland' : (x + y) % 7 === 0 ? 'hills' : 'open_ground';
        const band = Math.max(0, Math.min(15, Math.round(6 + 4 * Math.sin(x * 0.15) + 3 * Math.cos(y * 0.11))));
        cells.push({
          x, y, known,
          terrain: known ? terrain : null,
          band: known ? band : null,
          tier: known ? (band > 9 ? (band % 3) + 1 : 0) : null,
          road: known && road, ford: known && road && river,
          node: null,
          display: known ? { terrain_label: 't', district_key: x < 1020 ? 'w' : 'e', district_name: 'd', settlement: terrain === 'settlement', ford_label: null } : null,
        });
      }
    }
    return { mapId: 'bench', origin: { x: ox, y: oy }, width: N, height: N, cells, party,
      lightPhase: phases[k % 4], groundRadius: 1 + (k % 6), entities: [], sightings: [] };
  };
  const { paintTravelMap } = window.__elosernBridge.travelPaint;
  const canvas = document.createElement('canvas');
  canvas.width = N * S;
  canvas.height = N * S;
  const ctx = canvas.getContext('2d');
  const cache = {};
  const grids = Array.from({ length: 25 }, (_, k) => grid(k));
  for (let k = 0; k < 5; k += 1) paintTravelMap(ctx, grids[k], { cache });
  const samples = [];
  for (let k = 5; k < 25; k += 1) {
    const started = performance.now();
    paintTravelMap(ctx, grids[k], { cache });
    ctx.getImageData(0, 0, 1, 1);
    samples.push(performance.now() - started);
  }
  return { samples, ua: navigator.userAgent, dpr: window.devicePixelRatio, size: [canvas.width, canvas.height] };
}"""


class TravelMapTests(_TravelStage):
    """The painted travel map: disclosed facts, the camera and the repaint
    budget (wilderness-travel-map-ui)."""

    def _open(self, viewport, area=None):
        page = self.logged_in_page(viewport)
        self._enter(page, {"status": valid_status_panel("合成主角", "42"), "art": _art(WILD)})
        self._wait_views(page, 1)
        before = page.evaluate(_PAINTS)
        self._answer(page, 0, area=area)
        self._wait_ready(page)
        page.wait_for_function("(n) => window.__elosernBridge.travelPaint.stats().count > n", arg=before, timeout=15000)
        page.wait_for_timeout(200)
        return page

    @covers_requirement("webclient-travel-map::travel-painting-uses-disclosed-cell-facts")
    def test_map_fact_layers(self):
        """Unknown ground is transparent on the real canvas, known ground is
        painted, and no ink reaches past the revealed edge."""
        page = self._open((1451, 790), _fact_area())
        layers = page.evaluate(_ALPHA, [[[10, 20], [20, 26], [10, 18], [22, 20], [21, 26], [30, 18], [40, 40]], int(21.5 * 12)])
        self.assertEqual(layers["size"], [41 * 12, 41 * 12])
        known, unknown = layers["alpha"][:3], layers["alpha"][3:]
        self.assertEqual(known, [255, 255, 255])
        self.assertEqual(unknown, [0, 0, 0, 0])
        # Woodland dabs and the water line stop with the reveal: nothing is
        # painted more than half a cell into the unknown half.
        self.assertEqual(layers["east"], 0)
        page.close()

    @covers_requirement("webclient-travel-map::travel-camera-preserves-the-open-stage")
    def test_map_viewports(self):
        """At both viewports the party is centred in the open stage, zoom
        steps and clamps at the scaled cell sizes, and neither zoom, hover nor
        a resize repaints or changes a canvas pixel."""
        for viewport in ((1451, 790), (2560, 1440)):
            scale = ui_scale(viewport)
            page = self._open(viewport, _fact_area())
            header = page.evaluate(
                "() => { const s = document.querySelector('[data-testid=elosern-stage]').getBoundingClientRect();"
                " const h = document.querySelector('[data-metric=\"--header-h\"]').getBoundingClientRect().height;"
                " return s.top + h; }"
            )
            band = page.locator('[data-testid="stage-band"]').bounding_box()
            seal = page.locator('[data-testid="travel-map__party"]').bounding_box()
            self.assertAlmostEqual(seal["x"] + seal["width"] / 2, viewport[0] / 2, delta=2)
            self.assertAlmostEqual(seal["y"] + seal["height"] / 2, (header + band["y"]) / 2, delta=2)
            self._shoot(page, "travel-map-%dx%d.png" % viewport)

            paints = page.evaluate(_PAINTS)
            digest = page.evaluate(_DIGEST)
            stage = page.locator('[data-testid="travel-map"]')
            self.assertEqual(float(stage.get_attribute("data-cell-px")), 30 * scale)
            page.mouse.move(viewport[0] / 2 + 80, (header + band["y"]) / 2)
            for _ in range(6):
                page.mouse.wheel(0, -120)
            page.wait_for_timeout(100)
            self.assertEqual(stage.get_attribute("data-zoom"), "46")
            self.assertAlmostEqual(float(stage.get_attribute("data-cell-px")), 46 * scale, places=3)
            for _ in range(9):
                page.mouse.wheel(0, 120)
            page.wait_for_timeout(100)
            self.assertEqual(stage.get_attribute("data-zoom"), "18")
            page.mouse.move(viewport[0] / 2 - 120, (header + band["y"]) / 2 - 40)
            page.wait_for_timeout(100)
            # Hover over known ground outlines its cell (an overlay, no paint).
            self.assertEqual(page.locator('[data-testid="travel-map__hover"]').count(), 1)
            page.set_viewport_size({"width": viewport[0] - 200, "height": viewport[1] - 60})
            page.wait_for_timeout(300)
            self.assertEqual(page.evaluate(_PAINTS), paints)
            self.assertEqual(page.evaluate(_DIGEST), digest)
            page.close()

    @covers_requirement("webclient-travel-map::travel-painting-uses-disclosed-cell-facts")
    def test_repaint_budget(self):
        """Every warmed repaint of a full-fact window takes at most 50 ms at
        both viewports, and camera-only input paints nothing."""
        os.makedirs(SHOTS, exist_ok=True)
        lines = []
        for viewport in ((1451, 790), (2560, 1440)):
            page = self._open(viewport)
            result = page.evaluate(_BENCH)
            samples = result["samples"]
            lines.append(
                "%dx%d dpr=%s canvas=%s ua=%s samples_ms=%s"
                % (viewport[0], viewport[1], result["dpr"], result["size"], result["ua"], [round(v, 2) for v in samples])
            )
            self.assertEqual(len(samples), 20)
            self.assertLessEqual(max(samples), 50.0, lines[-1])
            # The bench painted off screen; the live map's own count only
            # moves on content.
            paints = page.evaluate(_PAINTS)
            page.mouse.move(viewport[0] / 2, viewport[1] / 3)
            page.mouse.wheel(0, -120)
            page.mouse.move(viewport[0] / 2 + 90, viewport[1] / 3)
            page.wait_for_timeout(200)
            self.assertEqual(page.evaluate(_PAINTS), paints)
            page.close()
        with open(os.path.join(SHOTS, "travel-repaint-budget.txt"), "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
        print("\n".join(lines))


# ── walking (wilderness-travel-walking-ui) ──────────────────────────────

_STEPS = (
    ("north", "n", 0, 1), ("northeast", "ne", 1, 1), ("east", "e", 1, 0), ("southeast", "se", 1, -1),
    ("south", "s", 0, -1), ("southwest", "sw", -1, -1), ("west", "w", -1, 0), ("northwest", "nw", -1, 1),
)


def _node(x: int, y: int) -> str:
    return "wild:elosern:%d:%d" % (x, y)


def _walk_panels(cx: int, cy: int) -> dict:
    """The eager panels of synthetic cell ``(cx, cy)``: the local map names it
    as the canonical current node and the exploration panel carries one
    direction row per step."""
    current = _node(cx, cy)
    neighbours = [
        {
            "id": _node(cx + dx, cy + dy), "label": "合成荒原", "x": cx + dx, "y": cy + dy,
            "visibility": "visible_unvisited", "current": False, "anchor": False, "landmark": False,
            "gateway": None, "action": {"kind": "move", "exit_ref": "e_wild_" + key, "destination": _node(cx + dx, cy + dy)},
        }
        for _, key, dx, dy in _STEPS
    ]
    return {
        "status": valid_status_panel("合成主角", "42"),
        "art": _art("wilderness:合成荒原:%d,%d" % (cx, cy)),
        "local_map": {
            "schema_version": 1, "available": True, "layer": "wilderness", "current_node": current,
            "title": "合成荒原",
            "nodes": [
                {
                    "id": current, "label": "合成荒原", "x": cx, "y": cy, "visibility": "current",
                    "current": True, "anchor": False, "landmark": False, "gateway": None, "action": None,
                },
                *neighbours,
            ],
            "edges": [], "legend": ["每格約一公里"],
        },
        "exploration": {
            "schema_version": 6, "available": True, "kind": "exploration",
            "move": [
                {
                    "exit_ref": "e_wild_" + key, "label": word, "destination": _node(cx + dx, cy + dy),
                    "enabled": True, "disabled_reason": None,
                }
                for word, key, dx, dy in _STEPS
            ],
            "look": {"room": {"identity": 900, "display_name": "合成荒原", "room": True}, "entities": [], "objects": []},
            "interact": [],
            "character": {"available": True}, "quests": {"available": True}, "inventory": {"available": True},
        },
    }


def _walk_area(cx: int, cy: int) -> dict:
    """``_area`` with the eight neighbours as move nodes."""
    area = _area(cx, cy)
    for _, key, dx, dy in _STEPS:
        node = _node(cx + dx, cy + dy)
        area["nodes"].append({
            "id": node, "label": "合成荒原", "x": cx + dx + 0.5, "y": cy + dy + 0.5, "visibility": "seen",
            "visited": False, "gateway": None, "action": {"kind": "move", "exit_ref": "e_wild_" + key, "destination": node},
        })
        area["edges"].append({"source": _node(cx, cy), "destination": node})
    return area


# Holds every explore.move as well (recorded, never forwarded).
_HOLD_MOVES = """() => {
  const store = window.__elosernBridge.store;
  if (window.__travelMoves) return;
  const sender = store.getSender();
  const original = sender.sendAction.bind(sender);
  window.__travelMoves = [];
  sender.sendAction = (env) => {
    if (env && env.action_id === 'explore.move') {
      window.__travelMoves.push(env);
      return undefined;
    }
    return original(env);
  };
}"""

# Commits held move `index`: its successful result, then the next cell's
# panels at the revision the result declared (the publication may follow
# its result; the queue accepts both orders).
_COMMIT_MOVE = """([index, panels]) => {
  const store = window.__elosernBridge.store;
  const env = window.__travelMoves[index];
  const v = store.view;
  const revision = v.revision + 1;
  const body = store.receive(v.generation, 'ui_update', [{
    protocol_version: 1, presentation_epoch: v.epoch, base_revision: revision - 1, revision,
    mode: v.mode, panels, removed_panels: [], layout_version: v.layoutVersion, server_time: v.serverTime,
  }], {});
  const result = store.receive(v.generation, 'ui_action_result', [{
    protocol_version: 1, presentation_epoch: v.epoch, request_id: env.request_id,
    outcome: 'success', code: 'moved', message: '你向前走去。', presentation_revision: revision,
  }], {});
  return [!!body.accepted, !!result.accepted];
}"""


def _moves(page) -> list:
    return page.evaluate("() => window.__travelMoves.map((e) => e.payload)")


def _map_focused(page) -> bool:
    return page.evaluate("() => document.activeElement && document.activeElement.matches('[data-testid=\"travel-map\"]')")


class TravelWalkingTests(_TravelStage):
    """Keyboard-only neighbour stepping and the commit-paced held walk
    (wilderness-travel-walking-ui)."""

    def _walk_stage(self, motion_level: str = "off"):
        page = self.logged_in_page((1451, 790), motion_level)
        page.evaluate(_HOLD_MOVES)
        self._enter(page, _walk_panels(CX, CY))
        self._wait_views(page, 1)
        self._answer(page, 0, area=_walk_area(CX, CY))
        self._wait_ready(page)
        return page

    # Temporary association (no canonical ID before the archive sync): the
    # nearest existing requirement, the MODIFIED keyboard composite whose
    # travel scenario hands movement focus to the map.
    @covers_requirement("webclient-exit-compass::the-compass-is-one-keyboard-composite")
    def test_keyboard_only_step(self):
        """Entering travel focuses the map; a tapped arrow only aims and the
        aim persists; Enter sends exactly one existing move payload."""
        page = self._walk_stage()
        page.wait_for_function("() => document.activeElement && document.activeElement.matches('[data-testid=\"travel-map\"]')", timeout=15000)
        self.assertEqual(page.locator('[data-testid="exit-compass"]').count(), 0)
        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(600)
        self.assertEqual(_moves(page), [])
        self.assertEqual(_travel(page)["aim"], "east")
        self.assertEqual(page.locator('[data-testid="travel-map__neighbour"][data-state="aimed"]').count(), 1)
        page.keyboard.press("Enter")
        page.wait_for_function("() => window.__travelMoves.length >= 1", timeout=15000)
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)
        self.assertEqual(_moves(page), [{"exit_ref": "e_wild_e", "current_node": _node(CX, CY)}])

        # The step commits: the stage asks for the new cell's map and the aim stays.
        self.assertEqual(page.evaluate(_COMMIT_MOVE, [0, _walk_panels(CX + 1, CY)]), [True, True])
        self._wait_views(page, 2)
        self._answer(page, 1, area=_walk_area(CX + 1, CY))
        page.wait_for_function(
            "(n) => window.__elosernBridge.store.view.travel.map && window.__elosernBridge.store.view.travel.map.currentNode === n",
            arg=_node(CX + 1, CY), timeout=15000,
        )
        self._wait_ready(page)
        self.assertEqual(_travel(page)["aim"], "east")
        self.assertIsNone(_travel(page)["walking"])
        self.assertEqual(len(_moves(page)), 1)
        self.assertTrue(_map_focused(page))
        self._shoot(page, "travel-walk-aim-1451x790.png")
        page.close()

    # Temporary association: the nearest existing commit-driven continuous
    # movement requirement until the archive sync mints the walking IDs.
    @covers_requirement("webclient-exit-compass::continuous-movement-is-commit-driven")
    def test_held_walk_release(self):
        """A 400 ms hold sends one step and nothing more until it commits;
        releasing during the post-step wait sends no next step and leaves
        focus on the map."""
        page = self._walk_stage("full")
        page.locator('[data-testid="travel-map"]').focus()
        page.keyboard.down("ArrowRight")
        page.wait_for_timeout(250)
        self.assertEqual(_moves(page), [])
        page.wait_for_function("() => window.__travelMoves.length >= 1", timeout=15000)
        page.wait_for_timeout(500)
        self.assertEqual(len(_moves(page)), 1)
        self.assertEqual(_travel(page)["walking"]["direction"], "east")
        self.assertEqual(page.locator('[data-testid="travel-walk-stop"]').get_attribute("aria-disabled"), None)

        self.assertEqual(page.evaluate(_COMMIT_MOVE, [0, _walk_panels(CX + 1, CY)]), [True, True])
        page.wait_for_function("() => (window.__elosernBridge.store.view.travel.walking || {}).progress === 1", timeout=15000)
        self._shoot(page, "travel-walk-held-1451x790.png")
        # Release while the walk dwells and waits for the new cell's map.
        page.keyboard.up("ArrowRight")
        page.wait_for_function("() => window.__elosernBridge.store.view.travel.walking === null", timeout=15000)
        self._wait_views(page, 2)
        self._answer(page, 1, area=_walk_area(CX + 1, CY))
        self._wait_ready(page)
        page.wait_for_timeout(1000)
        self.assertEqual(len(_moves(page)), 1)
        self.assertTrue(_map_focused(page))
        page.close()
