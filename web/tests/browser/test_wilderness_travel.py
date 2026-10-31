"""Wilderness travel stage acceptance (wilderness-travel-interface, task 4.1;
wilderness-travel-map-ui, task 3.1; wilderness-travel-walking-ui, task 3.1;
wilderness-travel-window-ui, task 4.1).

The journeys run in the live client against injected committed state: the
room's panels arrive through the store's own ``receive`` seam, and a
responder on the live sender holds every ``map.view`` the travel stage sends
so the test answers it with its action result and a synthetic schema-3
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


def _display(terrain: str, district: str | None = "t_east", ford: bool = False) -> dict:
    """A synthetic schema-3 display annotation (``district`` None: undisclosed)."""
    return {
        "terrain_label": "合成" + terrain, "district_key": district,
        "district_name": None if district is None else "合成%s區" % district,
        "settlement": terrain == "settlement", "ford_label": "合成渡口" if ford else None,
    }


def _run(terrain: str) -> dict:
    return {
        "length": 1, "kind": "terrain", "terrain": terrain, "passable": terrain != "water",
        "band": 3, "tier": 0, "road": False, "ford": False, "display": _display(terrain),
    }


def _rows(known) -> list:
    """Schema-3 rows (south to north) from ``known(col, row)``, which returns a
    terrain class (or a full run dict) or None for an unknown cell; equal
    neighbours merge."""
    rows = []
    for row in range(WINDOW):
        runs: list = []
        for col in range(WINDOW):
            terrain = known(col, row)
            if isinstance(terrain, dict):
                run = {"length": 1, **terrain}
            else:
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
    """A schema-3 wilderness window centred on ``(cx, cy)``: a 3 x 3 revealed
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
                        "band": 3, "tier": 0, "road": False, "ford": False, "display": _display("open_ground"),
                    },
                    {"length": 19, "kind": "unknown"},
                ]
            )
        else:
            rows.append([{"length": WINDOW, "kind": "unknown"}])
    current = "wild:elosern:%d:%d" % (cx, cy)
    return {
        "schema_version": 3,
        "available": True,
        "layer": "wilderness",
        "map_id": "elosern",
        "frame": {"key": "elosern", "unit": "km"},
        "current_node": current,
        "title": "合成荒原",
        "nodes": [
            {
                "id": current, "label": "合成荒原", "x": cx + 0.5, "y": cy + 0.5,
                "visibility": "current", "visited": True, "gateway": None, "action": None, "landmark": None,
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

# The repaint benchmark: the real painter on the real decoder's output
# (wilderness-travel-window-ui) for rich synthetic 41 x 41 schema-3 bodies
# (bands, tiers, roads, a river with a ford, woods, two districts, a
# settlement footprint, phase and radius), 5 warm-up paints, then 20 timed
# state changes (party, reveal, phase, radius and flags all move). The canvas
# size comes from the decoded window, never a constant.
_BENCH = """() => {
  const S = 12, N = 41, phases = ['day', 'dusk', 'night', 'dawn'];
  const labels = { open_ground: '曠', hills: '丘', woodland: '林', water: '河', settlement: '聚' };
  const body = (k) => {
    const ox = 1000 + k, oy = 2000 + (k % 3);
    const party = { x: ox + 20, y: oy + 20 };
    const rows = [];
    for (let row = 0; row < N; row += 1) {
      const runs = [];
      for (let col = 0; col < N; col += 1) {
        const x = ox + col, y = oy + row;
        const known = (x - party.x) ** 2 + (y - party.y) ** 2 < (14 + (k % 5)) ** 2 || (col + row * 3 + k) % 11 === 0 || (x === party.x && y === party.y);
        let run = { length: 1, kind: 'unknown' };
        if (known) {
          const river = Math.abs(y - (2012 + 3 * Math.sin(x * 0.2))) < 0.6;
          const road = y === 2020 + Math.round((x - 1020) * 0.4);
          const wood = Math.sin(x * 0.37) * Math.cos(y * 0.29) > 0.45;
          const terrain = river ? 'water' : x < ox + 5 && y < oy + 5 ? 'settlement' : wood ? 'woodland' : (x + y) % 7 === 0 ? 'hills' : 'open_ground';
          const band = Math.max(0, Math.min(15, Math.round(6 + 4 * Math.sin(x * 0.15) + 3 * Math.cos(y * 0.11))));
          const ford = road && river;
          run = { length: 1, kind: 'terrain', terrain, passable: terrain !== 'water' && terrain !== 'settlement',
            band, tier: band > 9 ? (band % 3) + 1 : 0, road, ford,
            display: { terrain_label: labels[terrain], district_key: x < 1020 ? 'w' : 'e', district_name: x < 1020 ? '西' : '東',
              settlement: terrain === 'settlement', ford_label: ford ? '渡' : null } };
        }
        const last = runs[runs.length - 1];
        if (last && JSON.stringify({ ...last, length: 0 }) === JSON.stringify({ ...run, length: 0 })) last.length += 1;
        else runs.push(run);
      }
      rows.push(runs);
    }
    const current = 'wild:elosern:' + party.x + ':' + party.y;
    return { schema_version: 3, available: true, layer: 'wilderness', map_id: 'elosern', frame: { key: 'elosern', unit: 'km' },
      current_node: current, title: '合成', nodes: [{ id: current, label: '合成', x: party.x + 0.5, y: party.y + 0.5,
        visibility: 'current', visited: true, gateway: null, action: null, landmark: null }],
      edges: [], quest_markers: [], district_name: '合成', cell_km: 1,
      window: { min_x: ox, min_y: oy, width: N, height: N }, rows,
      light_phase: phases[k % 4], ground_radius: 1 + (k % 6), entities: [], sightings: [] };
  };
  const { paintTravelMap, decode } = window.__elosernBridge.travelPaint;
  const grids = Array.from({ length: 25 }, (_, k) => decode(body(k)));
  if (grids.some((g) => !g)) return { error: 'the decoder refused a bench body' };
  const canvas = document.createElement('canvas');
  canvas.width = grids[0].width * S;
  canvas.height = grids[0].height * S;
  const ctx = canvas.getContext('2d');
  const cache = {};
  for (let k = 0; k < 5; k += 1) paintTravelMap(ctx, grids[k], { cache });
  const samples = [];
  for (let k = 5; k < 25; k += 1) {
    const started = performance.now();
    paintTravelMap(ctx, grids[k], { cache });
    ctx.getImageData(0, 0, 1, 1);
    samples.push(performance.now() - started);
  }
  return { samples, ua: navigator.userAgent, dpr: window.devicePixelRatio, size: [canvas.width, canvas.height],
    known: grids[0].cells.filter((c) => c.known).length };
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
            self.assertNotIn("error", result)
            self.assertEqual(result["size"], [41 * 12, 41 * 12])
            self.assertGreater(result["known"], 0)
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


# ── the live window (wilderness-travel-window-ui) ───────────────────────


def _window_area(phase: str = "dusk", radius: int = 3) -> dict:
    """A schema-3 window whose west half (columns 0..20) is revealed: open
    ground in a disclosed district, a ford crossing in an undisclosed one, a
    lit landmark on a visited cell, two hostiles in live sight (one without a
    supplied threat), one remembered hostile-free cell and three distant
    sightings."""
    cx, cy = CX, CY

    def known(col, row):
        if col > 20:
            return None
        if row == 18 and col == 17:
            return {"kind": "terrain", "terrain": "water", "passable": True, "band": 1, "tier": 0, "road": False,
                    "ford": True, "display": _display("water", None, ford=True)}
        if row == 18:
            return {"kind": "terrain", "terrain": "water", "passable": False, "band": 1, "tier": 0, "road": False,
                    "ford": False, "display": _display("water", None)}
        return "woodland" if row > 26 else "open_ground"

    area = _area(cx, cy)
    area["rows"] = _rows(known)
    area["light_phase"] = phase
    area["ground_radius"] = radius
    area["nodes"].append({
        "id": _node(cx - 3, cy + 2), "label": "合成荒原", "x": cx - 2.5, "y": cy + 2.5, "visibility": "visited",
        "visited": True, "gateway": None, "action": None, "landmark": {"name": "合成石標"},
    })
    area["nodes"].sort(key=lambda node: (node["y"], node["x"]))
    area["entities"] = [
        {"id": "0123456789abcdef", "cell": {"x": cx - 1, "y": cy + 1}, "kind": "hostile", "hostile": True,
         "label": "合成狼", "count": 1, "threat": "合成中階"},
        {"id": "fedcba9876543210", "cell": {"x": cx - 2, "y": cy - 1}, "kind": "hostile", "hostile": True,
         "label": "合成豬", "count": 1, "threat": None},
    ]
    reach = (radius + 0.5) ** 2
    area["entities"] = [
        e for e in area["entities"] if (e["cell"]["x"] - cx) ** 2 + (e["cell"]["y"] - cy) ** 2 <= reach
    ]
    area["sightings"] = [
        {"bearing": "北", "distance_km": 25, "silhouette_zh": "合成塔影", "name": None},
        {"bearing": "東南", "distance_km": 40, "silhouette_zh": "合成城牆", "name": "合成城"},
        {"bearing": "西南西", "distance_km": 15, "silhouette_zh": "合成望台", "name": None},
    ]
    return area


# The screen boxes of the protected controls and every chip/card.
_BOXES = """() => {
  const box = (el) => { const r = el.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; };
  const all = (sel) => [...document.querySelectorAll(sel)].map(box);
  return {
    protected: [
      ...all('[data-testid="stage-band"]'),
      ...all('[data-testid="place-card"]'),
      ...all('[data-testid="party-medallions"]'),
      ...all('[data-testid="anchor-vitals"] .status-panel'),
    ],
    cards: all('[data-testid="travel-map__sighting"]'),
    chips: all('.travel-map__chips .tm-chip'),
  };
}"""


def _overlaps(a, b) -> bool:
    return a[0] < b[2] - 1 and b[0] < a[2] - 1 and a[1] < b[3] - 1 and b[1] < a[3] - 1


class TravelWindowTests(_TravelStage):
    """The live window on the stage: live hostiles and the lit landmark,
    remembered ground, distant cards, the supplied phase and the place card
    (wilderness-travel-window-ui)."""

    @covers_requirement("webclient-travel-map::travel-painting-uses-disclosed-cell-facts")
    def test_live_memory_and_distant_cards(self):
        """Only the supplied annotations draw; a hostile without a threat says
        so; distant cards stay clear of the protected controls; the supplied
        phase alone retints the map and the place card states it."""
        for viewport in ((1451, 790), (2560, 1440)):
            page = self.logged_in_page(viewport)
            self._enter(page, {"status": valid_status_panel("合成主角", "42"), "art": _art(WILD)})
            self._wait_views(page, 1)
            before = page.evaluate(_PAINTS)
            self._answer(page, 0, area=_window_area())
            self._wait_ready(page)
            page.wait_for_function("(n) => window.__elosernBridge.travelPaint.stats().count > n", arg=before, timeout=15000)
            page.wait_for_timeout(300)

            # Live hostiles: one seal and chip each, the threat or its absence.
            self.assertEqual(page.locator('[data-testid="travel-map__hostile"]').count(), 2)
            chips = page.locator('[data-testid="travel-map__hostile-chip"]').all_text_contents()
            self.assertEqual(len(chips), 2)
            self.assertIn("合成中階", chips[0])
            self.assertEqual(page.locator('[data-testid="travel-map__hostile-chip"] .tm-chip__unknown').count(), 1)
            # The lit landmark carries its ornament and name; the ford its label.
            self.assertEqual(page.locator('[data-testid="travel-map__landmark"]').count(), 1)
            chip_text = " ".join(page.locator(".travel-map__chips .tm-chip").all_text_contents())
            self.assertIn("合成石標", chip_text)
            self.assertIn("合成渡口", chip_text)
            # The place card: the party cell's disclosed district and terrain,
            # and the supplied phase on the time line.
            grid = _travel(page)["map"]
            here = next(c for c in grid["cells"] if c["x"] == CX and c["y"] == CY)["display"]
            self.assertEqual(
                page.locator('[data-testid="place-card__location"]').text_content().strip(),
                "%s・%s" % (here["district_name"], here["terrain_label"]),
            )
            self.assertIn("黃昏", page.locator('[data-testid="place-card"]').text_content())
            # Distant cards: one per sighting, none under a protected control,
            # and no chip beneath one either.
            boxes = page.evaluate(_BOXES)
            self.assertEqual(len(boxes["cards"]), 3)
            for card in boxes["cards"]:
                for guard in boxes["protected"]:
                    self.assertFalse(_overlaps(card, guard), (card, guard))
            for chip in boxes["chips"]:
                for guard in boxes["protected"]:
                    self.assertFalse(_overlaps(chip, guard), (chip, guard))
            self._shoot(page, "travel-window-dusk-%dx%d.png" % viewport)

            # The supplied phase alone: night retints the stage and the card.
            paints = page.evaluate(_PAINTS)
            inject_snapshot(page, {"status": valid_status_panel("合成主角", "42"), "art": _art(WILD)})
            self._wait_views(page, 2)
            self._answer(page, 1, area=_window_area(phase="night", radius=1))
            self._wait_ready(page)
            page.wait_for_function("(n) => window.__elosernBridge.travelPaint.stats().count > n", arg=paints, timeout=15000)
            page.wait_for_timeout(300)
            self.assertIn("is-night", page.locator('[data-testid="travel-map"]').get_attribute("class"))
            self.assertIn("夜晚", page.locator('[data-testid="place-card"]').text_content())
            radius = page.locator('[data-testid="travel-map__sight"]').get_attribute("r")
            cell_px = float(page.locator('[data-testid="travel-map"]').get_attribute("data-cell-px"))
            self.assertAlmostEqual(float(radius), 1.5 * cell_px, places=2)
            self._shoot(page, "travel-window-night-%dx%d.png" % viewport)
            page.close()


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
            "landmark": None,
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

    @covers_requirement("webclient-travel-walking::travel-aim-maps-to-guarded-neighbour-movement")
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

    @covers_requirement("webclient-travel-walking::held-walking-waits-for-committed-steps-and-dwell")
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
        self.assertEqual(page.locator('[data-testid="leg-stop"]').get_attribute("aria-disabled"), None)

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


# The travel log journey's live hooks: every explore.move envelope is recorded
# (and still sent) so the test can resend a step from a node it has left.
_RECORD_MOVES = """() => {
  const store = window.__elosernBridge.store;
  if (window.__logMoves) return;
  const sender = store.getSender();
  const original = sender.sendAction.bind(sender);
  window.__logMoves = [];
  sender.sendAction = (env) => {
    if (env && env.action_id === 'explore.move') window.__logMoves.push(env);
    return original(env);
  };
}"""

_LOG_STATE = """() => {
  const store = window.__elosernBridge.store;
  return JSON.parse(JSON.stringify({
    entries: store.view.travel.entries,
    narrative: store.narrative.map((l) => ({ kind: l.kind, text: l.text })),
    result: store.view.lastActionResult,
    layout: store.view.travel.layout,
  }));
}"""


class TravelLogTests(BrowserAcceptanceTest):
    """The committed travel band log over the real producers
    (wilderness-travel-log-ui): a look, a step and a refused step."""

    def _send(self, page, text: str) -> None:
        page.evaluate("(text) => window.__elosernBridge.store.sendText(text)", text)

    def _fixture(self, page, call: str) -> list[str]:
        from .browser_helpers import narrative_log_text

        seen = narrative_log_text(page).count("TRAVEL_LOG_FIXTURE")
        self._send(page, f"@py __import__('web.tests.browser.travel_log_fixture', fromlist=['run']).{call}")
        wait_for_store_state(
            page, lambda _s: narrative_log_text(page).count("TRAVEL_LOG_FIXTURE") > seen, timeout=60000,
        )
        lines = [line for line in narrative_log_text(page).splitlines() if "TRAVEL_LOG_FIXTURE" in line]
        return lines[-1].split()

    def _state(self, page) -> dict:
        return page.evaluate(_LOG_STATE)

    def _dispatch(self, page, action: str, payload: dict) -> str:
        page.wait_for_function(
            "() => { const v = window.__elosernBridge.store.view; return v.dispatch.inFlight === null && !v.mutationsLocked; }",
            timeout=30000,
        )
        request = page.evaluate(
            "([a, p]) => window.__elosernBridge.store.dispatchAction(a, p)", [action, payload]
        )
        self.assertTrue(request)
        page.wait_for_function(
            "(id) => { const r = window.__elosernBridge.store.view.lastActionResult; return r && r.requestId === id; }",
            arg=request, timeout=30000,
        )
        return request

    @covers_requirement(
        "webclient-contextual-hud::the-message-window-presents-the-current-response-one-page-at-a-time-in-the-band-s-message-region",
        "webclient-travel-log::travel-log-retains-typed-chronological-entries",
    )
    def test_committed_log_and_full_prose(self):
        """A real look, step and refused step: typed notices reach the band
        log once, the step's ordinary narration and the look's full prose stay
        in the full log only, and a refusal is one travel entry plus exactly
        one full-log line."""
        page = self.logged_in_page((1451, 790), "off")
        page.evaluate(_RECORD_MOVES)
        placed = self._fixture(page, "run(me)")
        self.assertEqual(placed[1], "ok", placed)
        origin = placed[-1]
        # The shared browser account leaves the wilderness again, even when an
        # assertion fails half way.
        self.addCleanup(lambda: page.is_closed() or self._fixture(page, f"restore(me, {origin})"))
        page.wait_for_function("() => !!window.__elosernBridge.store.view.travel.layout", timeout=30000)
        log = page.locator('[data-testid="travel-log"]')
        log.wait_for(timeout=15000)
        self.assertEqual(page.locator('[data-testid="message-page"]').count(), 0)
        region = page.locator('[data-testid="travel-log__scroll"]')
        self.assertEqual(region.get_attribute("role"), "log")
        self.assertEqual(region.get_attribute("aria-live"), "polite")

        # 1. An explicit look: one typed summary, its full prose in the full log.
        self._dispatch(page, "explore.look", {"room": True})
        page.wait_for_function(
            "() => window.__elosernBridge.store.view.travel.entries.some((e) => e.kind === 'look')", timeout=30000,
        )
        state = self._state(page)
        looks = [e for e in state["entries"] if e["kind"] == "look"]
        self.assertEqual(len(looks), 1)
        summary = looks[0]["text"]
        self.assertNotIn("\n", summary)
        self.assertEqual([l["text"] for l in state["narrative"] if l["kind"] == "sys"].count(summary), 1)
        # The full appearance stays ordinary narration: the summary's own
        # opening words appear in a raw narrative line, not only as the notice.
        head = summary.split("：", 1)[-1].rstrip("…")[:6]
        self.assertTrue(head)
        self.assertTrue(any(head in l["text"] for l in state["narrative"] if l["kind"] == "out"))
        shown = page.locator(f'[data-entry-id="{looks[0]["id"]}"] [data-testid="travel-log__text"]')
        self.assertEqual(shown.text_content(), summary)

        # 2. A committed step: its ordinary narration is full-log only.
        before_ids = {e["id"] for e in state["entries"]}
        page.wait_for_function(
            "() => { const v = window.__elosernBridge.store.view; return v.dispatch.inFlight === null && !v.mutationsLocked; }",
            timeout=30000,
        )
        # One committed neighbour step through the guarded exit activation.
        sent = page.evaluate(
            """() => {
              const store = window.__elosernBridge.store;
              const map = store.view.panels.local_map || {};
              const node = (map.nodes || []).find((n) => n.action && n.action.destination && n.id !== map.current_node);
              if (!node) return { sent: false, reason: "no-node" };
              return store.activateExit(node.action.exit_ref);
            }"""
        )
        self.assertTrue(sent.get("sent"), sent)
        page.wait_for_function("() => window.__logMoves.length >= 1", timeout=30000)
        step = page.evaluate("() => window.__logMoves[0]")
        page.wait_for_function(
            "(id) => { const r = window.__elosernBridge.store.view.lastActionResult; return r && r.requestId === id; }",
            arg=step["request_id"], timeout=30000,
        )
        self.assertEqual(self._state(page)["result"]["outcome"], "success")
        page.wait_for_timeout(500)
        state = self._state(page)
        moved_lines = [l["text"] for l in state["narrative"] if l["kind"] == "out" and "移動到了" in l["text"]]
        self.assertTrue(moved_lines)
        self.assertFalse(any("移動到了" in e["text"] for e in state["entries"]))
        for entry in state["entries"]:
            if entry["id"] not in before_ids:
                self.assertNotEqual(entry["kind"], "refusal")

        # 3. A refused step: the same step resent from the node it left.
        errors_before = [l for l in state["narrative"] if l["kind"] == "err"]
        refused = self._dispatch(page, "explore.move", step["payload"])
        state = self._state(page)
        self.assertNotEqual(state["result"]["outcome"], "success")
        message = state["result"]["message"]
        refusals = [e for e in state["entries"] if e["kind"] == "refusal"]
        self.assertEqual(len(refusals), 1)
        self.assertEqual(refusals[0]["text"], message)
        self.assertIn(refused, refusals[0]["id"])
        errors = [l for l in state["narrative"] if l["kind"] == "err"][len(errors_before):]
        self.assertEqual([l["text"] for l in errors], [message])

        # The full log stays one action away and holds the look's summary.
        page.locator('[data-testid="message-log-open"]').click()
        page.wait_for_selector('[data-testid="fulllog-overlay"]', timeout=15000)
        self.assertIn(summary, page.locator('[data-testid="fulllog-overlay"]').inner_text())
        page.keyboard.press("Escape")
        os.makedirs(SHOTS, exist_ok=True)
        page.screenshot(path=os.path.join(SHOTS, "travel-log-1451x790.png"))
        self.assertEqual(self._fixture(page, f"restore(me, {origin})")[1], "restored")
        page.close()


# ── the leg panel (wilderness-travel-leg-ui) ────────────────────────────

_CAPACITY = {"normal": 5, "light": 4, "moderate": 3, "severe": 2}


def _leg_panels(cx: int, cy: int) -> dict:
    """``_walk_panels`` whose status v6 carries a synthetic travel capacity:
    per-stage foot counts, one 1200 s quote per step row and no pace
    threshold reached."""
    panels = _walk_panels(cx, cy)
    panels["status"] = {
        **panels["status"],
        "travel_capacity": {
            "capacity": dict(_CAPACITY),
            "neighbours": [{"exit_ref": "e_wild_" + key, "seconds": 1200} for _, key, _, _ in _STEPS],
            "at_pace": {"cautious": False, "standard": False},
        },
    }
    return panels


# Holds every explore.look as well (recorded, never forwarded).
_HOLD_LOOKS = """() => {
  const store = window.__elosernBridge.store;
  if (window.__travelLooks) return;
  const sender = store.getSender();
  const original = sender.sendAction.bind(sender);
  window.__travelLooks = [];
  sender.sendAction = (env) => {
    if (env && env.action_id === 'explore.look') {
      window.__travelLooks.push(env);
      return undefined;
    }
    return original(env);
  };
}"""

# Every rendered text run of the panel (screen-reader-only reasons aside)
# with its computed font size.
_LEG_TEXT = """() => {
  const panel = document.querySelector('[data-testid="leg-panel"]');
  const out = [];
  const walker = document.createTreeWalker(panel, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const text = node.textContent.trim();
    const el = node.parentElement;
    if (!text || el.closest('.leg-sr')) continue;
    out.push([text, parseFloat(getComputedStyle(el).fontSize)]);
  }
  return out;
}"""

_FOCUS_RING = """() => {
  const el = document.activeElement;
  const style = getComputedStyle(el);
  return {
    testid: el.getAttribute('data-testid'),
    ring: style.boxShadow !== 'none' || (style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0),
  };
}"""


class TravelLegTests(_TravelStage):
    """The leg panel's gauge, persisted preferences and guarded actions
    (wilderness-travel-leg-ui)."""

    def _leg_stage(self, viewport=(1451, 790), motion_level: str = "off"):
        page = self.logged_in_page(viewport, motion_level)
        page.evaluate(_HOLD_MOVES)
        page.evaluate(_HOLD_LOOKS)
        self._enter(page, _leg_panels(CX, CY))
        self._wait_views(page, 1)
        self._answer(page, 0, area=_walk_area(CX, CY))
        self._wait_ready(page)
        page.wait_for_selector('[data-testid="leg-panel"][data-gauge="capacity"]', timeout=15000)
        return page

    @covers_requirement("webclient-travel-leg::leg-panel-projects-supplied-state-and-persisted-preferences")
    def test_gauge_preferences_and_actions(self):
        """The supplied capacity draws one tick per counted step with the
        pace's camp line; every text run keeps the 16px x scale floor and
        every control shows a focus ring; the pace radio and the nightfall
        switch persist through the layout wrapper and freeze while walking,
        when 停步 stays live; 環顧 sends exactly the room look and 紮營 opens
        the existing sleep form."""
        page = self._leg_stage()
        scale = ui_scale((1451, 790))
        ticks = page.locator('[data-testid="leg-tick"]')
        self.assertEqual(ticks.count(), sum(_CAPACITY.values()))
        buckets = [ticks.nth(i).get_attribute("data-bucket") for i in range(ticks.count())]
        self.assertEqual(
            buckets, ["normal"] * 5 + ["light"] * 4 + ["moderate"] * 3 + ["severe"] * 2
        )
        # Standard camps on the first moderate step (index 9).
        camp = page.locator('[data-testid="leg-tick"]:has([data-testid="leg-camp-mark"])')
        self.assertEqual(camp.count(), 1)
        self.assertEqual(camp.get_attribute("data-bucket"), "moderate")
        sizes = page.evaluate(_LEG_TEXT)
        self.assertTrue(sizes)
        for text, size in sizes:
            self.assertGreaterEqual(size + 0.01, 16 * scale, text)
        self.assertEqual(page.locator('[data-testid="leg-depart"]').get_attribute("aria-disabled"), "true")

        # The aimed row's quote reaches the intent line.
        page.locator('[data-testid="travel-map"]').focus()
        page.keyboard.press("ArrowRight")
        # The aimed row's 1200 s quote reaches the intent line as 20 minutes.
        page.wait_for_function(
            "() => { const el = document.querySelector('[data-testid=\"leg-intent\"]');"
            " return el.dataset.quote === 'minutes' && el.dataset.minutes === '20'; }",
            timeout=15000,
        )
        self._shoot(page, "travel-leg-1451x790.png")

        # Keyboard: the radio group is one stop; arrows choose; Tab walks on
        # through the switch and the three actions, each with a focus ring.
        page.locator('[data-testid="leg-pace-standard"]').focus()
        page.keyboard.press("ArrowRight")
        page.wait_for_function(
            "() => window.__elosernBridge.store.view.travel.preferences.pace === 'forced'", timeout=15000
        )
        self.assertEqual(page.evaluate(_FOCUS_RING), {"testid": "leg-pace-forced", "ring": True})
        for expected in ("leg-night", "leg-depart", "leg-camp", "leg-look"):
            page.keyboard.press("Tab")
            self.assertEqual(page.evaluate(_FOCUS_RING), {"testid": expected, "ring": True})
        self.assertEqual(page.locator('[data-testid="leg-night"]').get_attribute("role"), "switch")
        self.assertEqual(page.locator('[data-testid="leg-pace"]').get_attribute("role"), "radiogroup")
        page.locator('[data-testid="leg-night"]').click()
        page.wait_for_function(
            "() => window.__elosernBridge.store.view.travel.preferences.stopAtNight === false", timeout=15000
        )
        stored = page.evaluate("() => JSON.parse(localStorage.getItem('elosern.layout')).preferences")
        self.assertEqual((stored["travelPace"], stored["travelStopAtNight"]), ("forced", False))

        # 紮營: the existing sleep form, with no request of its own.
        page.locator('[data-testid="leg-camp"]').click()
        page.wait_for_selector('[data-testid="sleep-card"]', timeout=15000)
        self.assertEqual(_moves(page), [])
        page.keyboard.press("Escape")
        page.keyboard.press("Escape")
        page.wait_for_selector('[data-testid="sleep-card"]', state="detached", timeout=15000)
        self.assertEqual(_moves(page), [])
        self.assertEqual(page.evaluate("() => window.__travelLooks.length"), 0)

        # Walking: the preferences freeze and 停步 is live.
        page.locator('[data-testid="travel-map"]').focus()
        page.keyboard.down("ArrowRight")
        page.wait_for_function("() => window.__travelMoves.length >= 1", timeout=15000)
        self.assertEqual(page.locator('[data-testid="leg-pace-cautious"]').get_attribute("aria-disabled"), "true")
        self.assertEqual(page.locator('[data-testid="leg-night"]').get_attribute("aria-disabled"), "true")
        self.assertIsNone(page.locator('[data-testid="leg-stop"]').get_attribute("aria-disabled"))
        frozen = page.evaluate(
            "() => [window.__elosernBridge.store.setTravelPace('cautious'),"
            " window.__elosernBridge.store.view.travel.preferences.pace]"
        )
        self.assertEqual(frozen, [False, "forced"])
        self._shoot(page, "travel-leg-walking-1451x790.png")
        page.keyboard.up("ArrowRight")
        page.wait_for_function("() => window.__elosernBridge.store.view.travel.walking === null", timeout=15000)
        # The step commits on the next cell, whose map the stage adopts.
        self.assertEqual(page.evaluate(_COMMIT_MOVE, [0, _leg_panels(CX + 1, CY)]), [True, True])
        self._wait_views(page, 2)
        self._answer(page, 1, area=_walk_area(CX + 1, CY))
        self._wait_ready(page)
        page.wait_for_function("() => window.__elosernBridge.store.view.dispatch.inFlight === null", timeout=15000)
        # 環顧: exactly the existing guarded room look.
        page.locator('[data-testid="leg-look"]').click()
        page.wait_for_function("() => window.__travelLooks.length >= 1", timeout=15000)
        # The look holds the single-flight gate, so no second send can follow.
        self.assertEqual(page.evaluate("() => window.__elosernBridge.store.view.dispatch.inFlight !== null"), True)
        self.assertEqual(page.evaluate("() => window.__travelLooks.map((e) => e.payload)"), [{"room": True}])
        self.assertEqual(page.locator('[data-testid="leg-look"]').get_attribute("aria-disabled"), "true")
        page.close()

        # The wide acceptance size keeps the floor at its own scale.
        wide = self._leg_stage((2560, 1440))
        wide_scale = ui_scale((2560, 1440))
        for text, size in wide.evaluate(_LEG_TEXT):
            self.assertGreaterEqual(size + 0.01, 16 * wide_scale, text)
        self._shoot(wide, "travel-leg-2560x1440.png")
        wide.close()
