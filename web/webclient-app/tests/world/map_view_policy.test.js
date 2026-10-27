// The game's map view policy, wired through the shared primitives (OpenSpec
// change establish-map-viewport; extracted to @elosern/map-view by
// map-view-shared-foundations). Every expected value below is computed by
// hand from the synthetic inputs, not by calling the module under test. The
// three top-level describe blocks map one-to-one to the webclient-map-viewport
// requirements; the Python wrapper tests/test_map_client_contracts.py checks
// each block ran and passed.

import { describe, expect, it } from "vitest";
import {
  UNITS,
  cellCentre,
  cellRect,
  cellUnit,
  centreOn,
  clampToRect,
  createView,
  fitBounds,
  formatDistance,
  isMetricLayer,
  metricBounds,
  metricPoints,
  nearestStop,
  nextStop,
  panByPixels,
  previousStop,
  project,
  scaleBar,
  scaleOf,
  spanLimits,
  toMetres,
  unproject,
  wheelFactor,
  zoomAt,
  zoomBy,
} from "@elosern/map-view";
import { DETAIL_DRAWER_WIDTH, usableRect } from "../../lib/map_chrome.js";
import {
  MIN_NEARBY_SPAN_M,
  WORLD_COUNTRY_SPAN_KM,
  settlementStops,
  wildernessStops,
  worldStops,
} from "../../lib/map_stops.js";

const EPS = 1e-9;
// A non-square frame: 1000 x 600 px.
const FRAME = Object.freeze({ width: 1000, height: 600 });

function close(actual, expected, digits = 9) {
  expect(actual).toBeCloseTo(expected, digits);
}

function closePoint(actual, expected, digits = 9) {
  close(actual.x, expected.x, digits);
  close(actual.y, expected.y, digits);
}

describe("map navigation preserves uniform geometry and the zoom anchor", () => {
  it("projects with one uniform scale and inverts only the north axis", () => {
    // span 500 m across 1000 px -> k = 2 px/m on both axes.
    const view = createView(3000, 2000, 500);
    expect(scaleOf(view, FRAME)).toBe(2);
    // 100 m east, 50 m north of the centre.
    expect(project(view, FRAME, { x: 3100, y: 2050 })).toEqual({ x: 700, y: 200 });
    // 25 m west, 75 m south.
    expect(project(view, FRAME, { x: 2975, y: 1925 })).toEqual({ x: 450, y: 450 });
    expect(project(view, FRAME, { x: 3000, y: 2000 })).toEqual({ x: 500, y: 300 });
  });

  it("round-trips project and unproject at several views", () => {
    const points = [
      { x: 0, y: 0 },
      { x: 3500, y: 3480 },
      { x: -125.5, y: 9876.25 },
    ];
    for (const view of [createView(0, 0, 10), createView(3500, 3480, 8200), createView(1350, 1350, 2.5)]) {
      for (const p of points) {
        closePoint(unproject(view, FRAME, project(view, FRAME, p)), p, 6);
      }
      closePoint(project(view, FRAME, unproject(view, FRAME, { x: 123, y: 456 })), { x: 123, y: 456 }, 6);
    }
  });

  it("keeps unequal metric gaps unequal after pan and zoom (no rank compression)", () => {
    // Three nodes on one row with 100 m and 350 m gaps (ratio 3.5).
    const nodes = [
      { x: 1000, y: 500 },
      { x: 1100, y: 500 },
      { x: 1450, y: 500 },
    ];
    // A diagonal pair 300 m east, 400 m north: 500 m apart.
    const a = { x: 0, y: 0 };
    const b = { x: 300, y: 400 };
    let view = createView(1200, 500, 2000);
    const views = [view];
    view = panByPixels(view, FRAME, 137, -42);
    views.push(view);
    view = zoomBy(view, FRAME, 0.37, { x: 810, y: 95 });
    views.push(view);
    view = zoomAt(view, FRAME, 9000, { x: 12, y: 590 });
    views.push(view);
    for (const v of views) {
      const [p0, p1, p2] = nodes.map((n) => project(v, FRAME, n));
      close((p2.x - p1.x) / (p1.x - p0.x), 3.5);
      close(p0.y, p1.y);
      close(p1.y, p2.y);
      const pa = project(v, FRAME, a);
      const pb = project(v, FRAME, b);
      const k = scaleOf(v, FRAME);
      close(pb.x - pa.x, 300 * k);
      close(pa.y - pb.y, 400 * k);
      close(Math.hypot(pb.x - pa.x, pb.y - pa.y), 500 * k);
    }
    // Canonical coordinates are never rewritten.
    expect(nodes[1]).toEqual({ x: 1100, y: 500 });
  });

  it("pans so the content follows the pointer", () => {
    // k = 2 px/m: dragging 40 px right and 20 px down moves the centre 20 m
    // west and 10 m north.
    const view = createView(3000, 2000, 500);
    const panned = panByPixels(view, FRAME, 40, 20);
    expect(panned).toEqual({ cx: 2980, cy: 2010, span: 500 });
    const before = project(view, FRAME, { x: 3100, y: 2050 });
    const after = project(panned, FRAME, { x: 3100, y: 2050 });
    expect({ x: after.x - before.x, y: after.y - before.y }).toEqual({ x: 40, y: 20 });
  });

  it("keeps the map point under the zoom anchor and the zoom reversible", () => {
    const start = createView(1350, 1350, 800);
    const anchors = [
      { x: 0, y: 0 },
      { x: 1000, y: 600 },
      { x: 731.5, y: 88.25 },
      null,
    ];
    for (const anchor of anchors) {
      const pin = anchor ?? { x: 500, y: 300 };
      const under = unproject(start, FRAME, pin);
      for (const span of [40, 200, 3333.3]) {
        const zoomed = zoomAt(start, FRAME, span, anchor);
        expect(zoomed.span).toBe(span);
        closePoint(unproject(zoomed, FRAME, pin), under, 6);
        closePoint(project(zoomed, FRAME, under), pin, 6);
        // Zooming back around the same anchor restores the original view.
        const back = zoomAt(zoomed, FRAME, 800, anchor);
        close(back.cx, start.cx, 6);
        close(back.cy, start.cy, 6);
        close(back.span, start.span, 9);
      }
    }
  });

  it("keeps the anchor fixed when limits clamp the requested span", () => {
    const start = createView(500, 500, 100);
    const anchor = { x: 900, y: 100 };
    const under = unproject(start, FRAME, anchor);
    const clamped = zoomAt(start, FRAME, 5, anchor, { min: 20, max: 400 });
    expect(clamped.span).toBe(20);
    closePoint(unproject(clamped, FRAME, anchor), under, 9);
    // Already at a limit: the view does not drift.
    const stuck = zoomAt(createView(500, 500, 400), FRAME, 4000, anchor, { min: 20, max: 400 });
    close(stuck.cx, 500);
    close(stuck.cy, 500);
    expect(stuck.span).toBe(400);
  });

  it("maps wheel delta to a continuous span factor", () => {
    expect(wheelFactor(0)).toBe(1);
    close(wheelFactor(100), 1.0018 ** 100);
    close(wheelFactor(-100) * wheelFactor(100), 1);
    const view = createView(0, 0, 1000);
    expect(zoomBy(view, FRAME, wheelFactor(-100)).span).toBeLessThan(1000);
  });

  it("states explicit metre, kilometre and provider-cell units", () => {
    expect(UNITS.m.metres).toBe(1);
    expect(UNITS.km.metres).toBe(1000);
    expect(toMetres(2.5, UNITS.km)).toBe(2500);
    expect(toMetres(3, cellUnit(1000))).toBe(3000);
    expect(toMetres(3, cellUnit(250))).toBe(750);
    expect(() => cellUnit(0)).toThrow(RangeError);
    expect(formatDistance(850)).toBe("850 m");
    expect(formatDistance(1500)).toBe("1.5 km");
    expect(formatDistance(40000)).toBe("40 km");
    // Rounding happens before the unit switch.
    expect(formatDistance(999.96)).toBe("1 km");
    expect(formatDistance(999.94)).toBe("999.9 m");
  });

  it("sizes the scale bar from the same uniform scale", () => {
    // 500 m across 1000 px: 0.5 m/px; 120 px = 60 m -> the 50 m bar is 100 px.
    expect(scaleBar(createView(0, 0, 500), FRAME, UNITS.m)).toEqual({ metres: 50, px: 100, text: "50 m" });
    // 800 km across 1000 px: 800 m/px; 120 px = 96 km -> 50 km, 62.5 px.
    expect(scaleBar(createView(0, 0, 800), FRAME, UNITS.km)).toEqual({ metres: 50000, px: 62.5, text: "50 km" });
    // 17 one-km cells across 1000 px: 17 m/px; 120 px = 2040 m -> 2 km.
    const bar = scaleBar(createView(0, 0, 17), FRAME, cellUnit(1000));
    expect(bar.metres).toBe(2000);
    expect(bar.text).toBe("2 km");
    close(bar.px, 2000 / 17);
  });

  it("projects wilderness cell corners and centres with one convention", () => {
    // 10 cells across 1000 px: 100 px per cell, centred on cell (4,7)'s centre.
    const view = createView(4.5, 7.5, 10);
    expect(cellRect(view, FRAME, 4, 7)).toEqual({ left: 450, top: 250, right: 550, bottom: 350 });
    expect(project(view, FRAME, cellCentre(4, 7))).toEqual({ x: 500, y: 300 });
    expect(cellRect(view, FRAME, 5, 7).left).toBe(550);
  });

  it("returns frozen results and never mutates its inputs", () => {
    const view = { cx: 10, cy: 20, span: 100 };
    const out = [
      panByPixels(view, FRAME, 5, 5),
      zoomAt(view, FRAME, 50, { x: 1, y: 2 }),
      centreOn(view, FRAME, { x: 0, y: 0 }),
      project(view, FRAME, { x: 0, y: 0 }),
    ];
    expect(view).toEqual({ cx: 10, cy: 20, span: 100 });
    for (const value of out) expect(Object.isFrozen(value)).toBe(true);
  });

  it("rejects invalid frames, views and anchors instead of leaking NaN", () => {
    const view = createView(0, 0, 100);
    expect(() => project(view, { width: 0, height: 600 }, { x: 0, y: 0 })).toThrow(RangeError);
    expect(() => project(view, { width: Number.NaN, height: 600 }, { x: 0, y: 0 })).toThrow(TypeError);
    expect(() => createView(0, 0, 0)).toThrow(RangeError);
    expect(() => createView(Number.NaN, 0, 10)).toThrow(TypeError);
    expect(() => zoomAt(view, FRAME, 10, { x: Number.NaN, y: 0 })).toThrow(TypeError);
    expect(() => panByPixels(view, FRAME, Infinity, 0)).toThrow(TypeError);
  });
});

describe("map zoom stops and fit follow scope and aspect ratio", () => {
  // Synthetic continent: 2700 km square plus an off-centre landmass.
  const CONTINENT = Object.freeze({ minX: 0, minY: 0, maxX: 2700, maxY: 2700 });

  function fitsInside(view, frame, bounds, marginPx) {
    const sw = project(view, frame, { x: bounds.minX, y: bounds.minY });
    const ne = project(view, frame, { x: bounds.maxX, y: bounds.maxY });
    expect(sw.x).toBeGreaterThanOrEqual(marginPx - EPS);
    expect(ne.x).toBeLessThanOrEqual(frame.width - marginPx + EPS);
    expect(ne.y).toBeGreaterThanOrEqual(marginPx - EPS);
    expect(sw.y).toBeLessThanOrEqual(frame.height - marginPx + EPS);
    return { sw, ne };
  }

  it("fits the whole continent on both axes in a wide viewport", () => {
    // 1600 x 600: height-limited. Inner height 552 px for 2700 km ->
    // k = 552/2700, span = 1600 / k = 7826.0869... km.
    const wide = { width: 1600, height: 600 };
    const view = fitBounds(CONTINENT, wide, { marginPx: 24 });
    close(view.span, 1600 * 2700 / 552);
    expect(view.cx).toBe(1350);
    expect(view.cy).toBe(1350);
    const { sw, ne } = fitsInside(view, wide, CONTINENT, 24);
    // North-south touches the margins exactly: the wide frame does not clip it.
    close(ne.y, 24);
    close(sw.y, 576);
    // No distortion: projected width:height equals the true 1:1.
    close((ne.x - sw.x) / (sw.y - ne.y), 1);
  });

  it("refits for a tall viewport and keeps relative geometry", () => {
    // 600 x 900: width-limited. Inner width 552 px for 2700 km.
    const tall = { width: 600, height: 900 };
    const land = { minX: 300, minY: 100, maxX: 2400, maxY: 2700 };
    const view = fitBounds(land, tall, { marginPx: 24 });
    // bw 2100, bh 2600: candidates 552/2100 and 852/2600 -> 552/2100 wins.
    close(view.span, 600 * 2100 / 552);
    const { sw, ne } = fitsInside(view, tall, land, 24);
    close(sw.x, 24);
    close(ne.x, 576);
    close((ne.x - sw.x) / (sw.y - ne.y), 2100 / 2600);
  });

  it("orders world stops continent, 國 800, 地區 200, 近郊 40 km", () => {
    const wide = { width: 1600, height: 600 };
    const stops = worldStops(CONTINENT, wide);
    expect(stops.map((s) => s.key)).toEqual(["continent", "country", "district", "nearby"]);
    expect(stops.map((s) => s.label)).toEqual(["大陸", "國", "地區", "近郊"]);
    close(stops[0].span, 1600 * 2700 / 552);
    expect(stops.slice(1).map((s) => s.span)).toEqual([800, 200, 40]);
    // The continent stop depends on the aspect ratio; the others do not.
    const square = worldStops(CONTINENT, { width: 900, height: 900 });
    close(square[0].span, 900 * 2700 / 852);
  });

  it("never lets the continent stop fall below 國", () => {
    // A small island fits in under 800 km; 大陸 takes 國's span and the
    // duplicate collapses so plus/minus never stalls.
    const stops = worldStops({ minX: 0, minY: 0, maxX: 100, maxY: 100 }, FRAME);
    expect(stops.map((s) => s.span)).toEqual([WORLD_COUNTRY_SPAN_KM, 200, 40]);
    expect(stops[0].key).toBe("continent");
  });

  it("derives settlement stops from known settlement geometry", () => {
    // Settlement A: known nodes span 4000 x 1000 m; neighbours span 600 x 200 m.
    const a = settlementStops(
      { minX: 1000, minY: 2000, maxX: 5000, maxY: 3000 },
      { minX: 2700, minY: 2400, maxX: 3300, maxY: 2600 },
      FRAME,
    );
    expect(a.map((s) => s.label)).toEqual(["全城", "街區", "近處"]);
    // Whole: inner 952 x 552 -> min(952/4000, 552/1000) = 0.238 -> 4201.68 m.
    close(a[0].span, 1000 * 4000 / 952);
    // Nearby: min(952/600, 552/200) -> 600 * 1000 / 952 = 630.25 m.
    close(a[2].span, 1000 * 600 / 952);
    close(a[1].span, Math.sqrt(a[0].span * a[2].span));
    // Settlement B with different geometry yields different stops.
    const b = settlementStops(
      { minX: 0, minY: 0, maxX: 1200, maxY: 2400 },
      { minX: 500, minY: 500, maxX: 900, maxY: 1100 },
      FRAME,
    );
    close(b[0].span, 1000 * 2400 / 552);
    close(b[2].span, 1000 * 600 / 552);
  });

  it("floors a lone-node neighbourhood and keeps a tiny settlement ordered", () => {
    const lone = settlementStops(
      { minX: 0, minY: 0, maxX: 3000, maxY: 1000 },
      { minX: 1500, minY: 500, maxX: 1500, maxY: 500 },
      FRAME,
    );
    expect(lone[2].span).toBe(MIN_NEARBY_SPAN_M);
    // A settlement smaller than the floor collapses to one stop, not three
    // identical ones.
    const tiny = settlementStops(
      { minX: 0, minY: 0, maxX: 50, maxY: 20 },
      { minX: 0, minY: 0, maxX: 10, maxY: 10 },
      FRAME,
    );
    expect(tiny).toEqual([{ key: "whole", label: "全城", span: MIN_NEARBY_SPAN_M }]);
  });

  it("uses the 15-cell window and a nearby stop for the wilderness", () => {
    const stops = wildernessStops(FRAME);
    expect(stops.map((s) => s.label)).toEqual(["周邊", "近處"]);
    // Height-limited: 15 cells into 552 px -> span 1000 * 15 / 552 cells.
    close(stops[0].span, 1000 * 15 / 552);
    close(stops[1].span, 1000 * 5 / 552);
    // The whole 15 x 15 window is visible around the player's cell centre.
    const view = { cx: 100.5, cy: 200.5, span: stops[0].span };
    const top = cellRect(view, FRAME, 100 + 7, 200 + 7);
    const bottom = cellRect(view, FRAME, 100 - 7, 200 - 7);
    expect(top.top).toBeGreaterThanOrEqual(24 - EPS);
    expect(bottom.bottom).toBeLessThanOrEqual(576 + EPS);
  });

  it("jumps between stops with plus/minus and caps the continuous wheel", () => {
    const stops = worldStops(CONTINENT, { width: 1600, height: 600 });
    const continent = stops[0].span;
    expect(nextStop(stops, continent).key).toBe("country");
    expect(nextStop(stops, 800).key).toBe("district");
    // Between stops, plus goes to the next narrower one, minus to the wider.
    expect(nextStop(stops, 500).key).toBe("district");
    expect(previousStop(stops, 500).key).toBe("country");
    // Within tolerance of a stop counts as being on it.
    expect(previousStop(stops, 790).key).toBe("continent");
    expect(nextStop(stops, 40)).toBeNull();
    expect(previousStop(stops, continent)).toBeNull();
    expect(nearestStop(stops, 260).key).toBe("district");
    // The log midpoint of 200 and 40 is about 89.4 km.
    expect(nearestStop(stops, 80).key).toBe("nearby");
    expect(nearestStop(stops, 95).key).toBe("district");
    const limits = spanLimits(stops);
    expect(limits.min).toBe(20);
    close(limits.max, continent * 1.25);
    // Metric limits are spans, never the old lattice scale floor of 1.
    expect(zoomAt(createView(0, 0, 40), FRAME, 1, null, limits).span).toBe(20);
  });

  it("recentres and fits in the current scope's units", () => {
    // The same 3 km square in metres, kilometres and one-km cells projects to
    // the same pixels.
    const scopes = [
      { bounds: { minX: 1000, minY: 1000, maxX: 4000, maxY: 4000 }, point: { x: 2500, y: 3000 } },
      { bounds: { minX: 1, minY: 1, maxX: 4, maxY: 4 }, point: { x: 2.5, y: 3 } },
    ];
    const pixels = scopes.map(({ bounds, point }) => {
      const fitted = fitBounds(bounds, FRAME);
      const centred = centreOn(fitted, FRAME, point);
      return [project(fitted, FRAME, point), project(centred, FRAME, point)];
    });
    closePoint(pixels[0][0], pixels[1][0], 6);
    closePoint(pixels[0][1], { x: 500, y: 300 }, 6);
    closePoint(pixels[1][1], { x: 500, y: 300 }, 6);
  });

  it("fits into a host rectangle that excludes the open drawer", () => {
    const rect = usableRect(FRAME, { drawerOpen: true, marginPx: 0 });
    expect(rect).toEqual({ left: 0, top: 0, right: 640, bottom: 600 });
    const bounds = { minX: 0, minY: 0, maxX: 100, maxY: 100 };
    const view = fitBounds(bounds, FRAME, { rect, marginPx: 20 });
    // Inner 600 x 560 -> k = 5.6, span = 1000 / 5.6.
    close(view.span, 1000 / 5.6);
    closePoint(project(view, FRAME, { x: 50, y: 50 }), { x: 320, y: 300 });
    const ne = project(view, FRAME, { x: 100, y: 100 });
    expect(ne.x).toBeLessThanOrEqual(640 - 20 + EPS);
    // Recentre into the same rectangle.
    closePoint(project(centreOn(view, FRAME, { x: 10, y: 90 }, rect), FRAME, { x: 10, y: 90 }), { x: 320, y: 300 });
  });

  it("requires an explicit floor to fit a single point", () => {
    const point = { minX: 5, minY: 5, maxX: 5, maxY: 5 };
    expect(() => fitBounds(point, FRAME)).toThrow(RangeError);
    expect(fitBounds(point, FRAME, { minSpan: 300 })).toEqual({ cx: 5, cy: 5, span: 300 });
  });

  it("never fabricates coordinates for a coordinate-free map", () => {
    const rooms = [
      { id: "room:1", label: "Hall" },
      { id: "room:2", label: "Cellar", x: null, y: undefined },
      { id: "room:3", label: "Stair", x: "4", y: "5" },
    ];
    expect(isMetricLayer(rooms)).toBe(false);
    expect(metricPoints(rooms)).toEqual([]);
    expect(metricBounds(rooms)).toBeNull();
    expect(rooms[0]).toEqual({ id: "room:1", label: "Hall" });
    expect(isMetricLayer([])).toBe(false);
    const grid = [
      { id: "a", x: 10, y: -20 },
      { id: "b", x: 350, y: 40 },
    ];
    expect(isMetricLayer(grid)).toBe(true);
    expect(metricBounds(grid)).toEqual({ minX: 10, minY: -20, maxX: 350, maxY: 40 });
    // A mixed layer is not metric, and only the placed nodes are returned.
    expect(isMetricLayer([...grid, rooms[0]])).toBe(false);
    expect(metricPoints([...grid, rooms[0]]).map((n) => n.id)).toEqual(["a", "b"]);
  });
});

describe("offscreen geometry avoids the selected detail drawer", () => {
  it("excludes the open ~360 px drawer and host-measured control insets", () => {
    expect(DETAIL_DRAWER_WIDTH).toBe(360);
    expect(usableRect(FRAME)).toEqual({ left: 24, top: 24, right: 976, bottom: 576 });
    expect(usableRect(FRAME, { drawerOpen: true })).toEqual({ left: 24, top: 24, right: 616, bottom: 576 });
    expect(
      usableRect(FRAME, { drawerOpen: true, insets: { top: 40, left: 10, bottom: 52, right: 6 } }),
    ).toEqual({ left: 34, top: 64, right: 610, bottom: 524 });
  });

  it("clamps a target to the right against the drawer and recomputes when it closes", () => {
    const target = { x: 1400, y: 300 };
    const open = clampToRect(usableRect(FRAME, { drawerOpen: true }), target);
    expect(open).toEqual({ x: 616, y: 300, inside: false, side: "right", angle: 0 });
    const closed = clampToRect(usableRect(FRAME), target);
    expect(closed).toEqual({ x: 976, y: 300, inside: false, side: "right", angle: 0 });
  });

  it("uses the same exclusion on every edge", () => {
    const rect = usableRect(FRAME, { drawerOpen: true });
    // Rect centre (320, 300); half extents 296 x 276.
    expect(clampToRect(rect, { x: -500, y: 300 })).toMatchObject({ x: 24, y: 300, side: "left", angle: 180 });
    expect(clampToRect(rect, { x: 320, y: -900 })).toMatchObject({ x: 320, y: 24, side: "top", angle: -90 });
    expect(clampToRect(rect, { x: 320, y: 2000 })).toMatchObject({ x: 320, y: 576, side: "bottom", angle: 90 });
    // A diagonal target up-right: dx 680, dy -600 from the centre.
    // tx = 296/680 = 0.43529, ty = 276/600 = 0.46 -> right edge first.
    const diag = clampToRect(rect, { x: 1000, y: -300 });
    expect(diag.side).toBe("right");
    close(diag.x, 616);
    close(diag.y, 300 - 600 * (296 / 680));
    close(diag.angle, (Math.atan2(-600, 680) * 180) / Math.PI);
    // A steep target hits the top edge, still left of the drawer.
    const steep = clampToRect(rect, { x: 700, y: -2000 });
    expect(steep.side).toBe("top");
    close(steep.y, 24);
    close(steep.x, 320 + 380 * (276 / 2300));
    expect(steep.x).toBeLessThanOrEqual(616);
  });

  it("leaves on-screen targets, boundary targets and the centre in place", () => {
    const rect = usableRect(FRAME, { drawerOpen: true });
    expect(clampToRect(rect, { x: 616, y: 576 })).toMatchObject({ x: 616, y: 576, inside: true, side: null });
    expect(clampToRect(rect, { x: 320, y: 300 })).toEqual({ x: 320, y: 300, inside: true, side: null, angle: 0 });
    // Behind the open drawer counts as offscreen.
    expect(clampToRect(rect, { x: 800, y: 300 })).toMatchObject({ x: 616, inside: false, side: "right" });
  });

  it("collapses a rectangle squeezed by a drawer wider than the frame", () => {
    const narrow = { width: 300, height: 200 };
    const rect = usableRect(narrow, { drawerOpen: true });
    // left 24, right 300 - 24 - 360 = -84 -> both at the midpoint -30.
    expect(rect).toEqual({ left: -30, top: 24, right: -30, bottom: 176 });
    const clamped = clampToRect(rect, { x: 500, y: 100 });
    expect(clamped).toMatchObject({ x: -30, y: 100, inside: false, side: "right" });
    expect(Number.isFinite(clamped.angle)).toBe(true);
    // Away from the centre row the remaining (vertical) axis stops the ray:
    // centre (-30, 100); dy -200 reaches top 24 and dy +400 reaches bottom 176.
    expect(clampToRect(rect, { x: 500, y: -100 })).toMatchObject({ x: -30, y: 24, side: "top" });
    expect(clampToRect(rect, { x: 500, y: 500 })).toMatchObject({ x: -30, y: 176, side: "bottom" });
    // A rectangle collapsed on both axes degrades to its single point.
    const dot = { left: 5, top: 7, right: 5, bottom: 7 };
    expect(clampToRect(dot, { x: 50, y: 8 })).toEqual({ x: 5, y: 7, inside: false, side: "right", angle: (Math.atan2(1, 45) * 180) / Math.PI });
  });

  it("feeds projected offscreen markers through the drawer-aware clamp", () => {
    // k = 2 px/m: a marker 400 m east projects to x = 1300, off the frame.
    const view = createView(0, 0, 500);
    const marker = project(view, FRAME, { x: 400, y: 0 });
    expect(marker).toEqual({ x: 1300, y: 300 });
    expect(clampToRect(usableRect(FRAME, { drawerOpen: true }), marker).x).toBe(616);
    // Panning it into view makes it inside the closed-drawer rectangle.
    const panned = panByPixels(view, FRAME, -500, 0);
    expect(clampToRect(usableRect(FRAME), project(panned, FRAME, { x: 400, y: 0 })).inside).toBe(true);
  });
});
