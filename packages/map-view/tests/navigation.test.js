// Pan, pointer-anchored zoom, whole-map fit and host-rectangle navigation,
// checked against hand-computed pixel values on synthetic metre inputs.

import assert from "node:assert/strict";
import { test } from "node:test";

import { createView } from "../src/values.js";
import { project, scaleOf, unproject } from "../src/projection.js";
import {
  DEFAULT_MARGIN_PX,
  centreOn,
  fitBounds,
  panByPixels,
  wheelFactor,
  zoomAt,
  zoomBy,
} from "../src/navigation.js";

const FRAME = Object.freeze({ width: 1000, height: 600 });
const close = (actual, expected, digits = 9) => assert.ok(Math.abs(actual - expected) < 10 ** -digits, `${actual} ≉ ${expected}`);
const closePoint = (actual, expected, digits = 9) => {
  close(actual.x, expected.x, digits);
  close(actual.y, expected.y, digits);
};

test("keeps unequal metric gaps unequal after pan and zoom", () => {
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
  assert.deepEqual(nodes[1], { x: 1100, y: 500 });
});

test("pans so the content follows the pointer", () => {
  // k = 2 px/m: dragging 40 px right and 20 px down moves the centre 20 m
  // west and 10 m north.
  const view = createView(3000, 2000, 500);
  const panned = panByPixels(view, FRAME, 40, 20);
  assert.deepEqual(panned, { cx: 2980, cy: 2010, span: 500 });
  const before = project(view, FRAME, { x: 3100, y: 2050 });
  const after = project(panned, FRAME, { x: 3100, y: 2050 });
  assert.deepEqual({ x: after.x - before.x, y: after.y - before.y }, { x: 40, y: 20 });
});

test("keeps the map point under the zoom anchor and the zoom reversible", () => {
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
      assert.equal(zoomed.span, span);
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

test("keeps the anchor fixed when limits clamp the requested span", () => {
  const start = createView(500, 500, 100);
  const anchor = { x: 900, y: 100 };
  const under = unproject(start, FRAME, anchor);
  const clamped = zoomAt(start, FRAME, 5, anchor, { min: 20, max: 400 });
  assert.equal(clamped.span, 20);
  closePoint(unproject(clamped, FRAME, anchor), under, 9);
  // Already at a limit: the view does not drift.
  const stuck = zoomAt(createView(500, 500, 400), FRAME, 4000, anchor, { min: 20, max: 400 });
  close(stuck.cx, 500);
  close(stuck.cy, 500);
  assert.equal(stuck.span, 400);
});

test("maps wheel delta to a continuous span factor", () => {
  assert.equal(wheelFactor(0), 1);
  close(wheelFactor(100), 1.0018 ** 100);
  close(wheelFactor(-100) * wheelFactor(100), 1);
  const view = createView(0, 0, 1000);
  assert.ok(zoomBy(view, FRAME, wheelFactor(-100)).span < 1000);
});

function fitsInside(view, frame, bounds, marginPx) {
  const sw = project(view, frame, { x: bounds.minX, y: bounds.minY });
  const ne = project(view, frame, { x: bounds.maxX, y: bounds.maxY });
  assert.ok(sw.x >= marginPx - 1e-9);
  assert.ok(ne.x <= frame.width - marginPx + 1e-9);
  assert.ok(ne.y >= marginPx - 1e-9);
  assert.ok(sw.y <= frame.height - marginPx + 1e-9);
  return { sw, ne };
}

test("fits the whole extent on both axes in a wide viewport", () => {
  const continent = { minX: 0, minY: 0, maxX: 2700, maxY: 2700 };
  // 1600 x 600: height-limited. Inner height 552 px for 2700 km ->
  // k = 552/2700, span = 1600 / k = 1600 * 2700 / 552.
  const wide = { width: 1600, height: 600 };
  const view = fitBounds(continent, wide, { marginPx: 24 });
  close(view.span, (1600 * 2700) / 552);
  assert.equal(view.cx, 1350);
  assert.equal(view.cy, 1350);
  const { sw, ne } = fitsInside(view, wide, continent, 24);
  // North-south touches the margins exactly: the wide frame does not clip it.
  close(ne.y, 24);
  close(sw.y, 576);
  // No distortion: projected width:height equals the true 1:1.
  close((ne.x - sw.x) / (sw.y - ne.y), 1);
});

test("refits for a tall viewport and keeps relative geometry", () => {
  const tall = { width: 600, height: 900 };
  const land = { minX: 300, minY: 100, maxX: 2400, maxY: 2700 };
  const view = fitBounds(land, tall, { marginPx: 24 });
  // bw 2100, bh 2600: candidates 552/2100 and 852/2600 -> 552/2100 wins.
  close(view.span, (600 * 2100) / 552);
  const { sw, ne } = fitsInside(view, tall, land, 24);
  close(sw.x, 24);
  close(ne.x, 576);
  close((ne.x - sw.x) / (sw.y - ne.y), 2100 / 2600);
});

test("requires an explicit floor to fit a single point", () => {
  const point = { minX: 5, minY: 5, maxX: 5, maxY: 5 };
  assert.throws(() => fitBounds(point, FRAME), RangeError);
  assert.deepEqual(fitBounds(point, FRAME, { minSpan: 300 }), { cx: 5, cy: 5, span: 300 });
});

test("recentres and fits in the current scope's units", () => {
  // The same 3 km square in metres and kilometres projects to same pixels.
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

test("defaults the fit margin to the shared frame margin", () => {
  const frame = { width: 600, height: 600 };
  const bounds = { minX: 0, minY: 0, maxX: 100, maxY: 100 };
  const sw = project(fitBounds(bounds, frame), frame, { x: 0, y: 0 });
  close(sw.x, DEFAULT_MARGIN_PX);
  close(sw.y, frame.height - DEFAULT_MARGIN_PX);
});
