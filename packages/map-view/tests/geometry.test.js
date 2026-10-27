// Cell, bounds and rectangle geometry: nothing is fabricated, corners and
// centres share one convention, and a host-measured rectangle is honoured
// exactly.

import assert from "node:assert/strict";
import { test } from "node:test";

import { createView } from "../src/values.js";
import { project } from "../src/projection.js";
import { boundsCentredOn, boundsOfPoints, isMetricLayer, metricBounds, metricPoints } from "../src/bounds.js";
import { cellCentre, cellOf, cellRect } from "../src/cells.js";
import { clampToRect, insetRect, rectCentre } from "../src/navigation.js";

const FRAME = Object.freeze({ width: 1000, height: 600 });
const close = (actual, expected, digits = 9) => assert.ok(Math.abs(actual - expected) < 10 ** -digits, `${actual} ≉ ${expected}`);

test("never fabricates coordinates for a coordinate-free layer", () => {
  const rooms = [
    { id: "room:1", label: "Hall" },
    { id: "room:2", label: "Cellar", x: null, y: undefined },
    { id: "room:3", label: "Stair", x: "4", y: "5" },
  ];
  assert.equal(isMetricLayer(rooms), false);
  assert.deepEqual(metricPoints(rooms), []);
  assert.equal(metricBounds(rooms), null);
  assert.deepEqual(rooms[0], { id: "room:1", label: "Hall" });
  assert.equal(isMetricLayer([]), false);
  const grid = [
    { id: "a", x: 10, y: -20 },
    { id: "b", x: 350, y: 40 },
  ];
  assert.equal(isMetricLayer(grid), true);
  assert.deepEqual(metricBounds(grid), { minX: 10, minY: -20, maxX: 350, maxY: 40 });
  // A mixed layer is not metric, and only the placed nodes are returned.
  assert.equal(isMetricLayer([...grid, rooms[0]]), false);
  assert.deepEqual(metricPoints([...grid, rooms[0]]).map((n) => n.id), ["a", "b"]);
});

test("computes bounds of supplied points and around an anchor", () => {
  const points = [
    { x: -4, y: 9 },
    { x: 6, y: -1 },
    { x: 2, y: 2 },
  ];
  assert.deepEqual(boundsOfPoints(points), { minX: -4, minY: -1, maxX: 6, maxY: 9 });
  // Reach is measured per axis from the anchor, never as a radius: the
  // farthest x is 5 away and the farthest y is 8 away.
  assert.deepEqual(boundsCentredOn({ x: 1, y: 1 }, points), { minX: -4, minY: -7, maxX: 6, maxY: 9 });
  assert.deepEqual(boundsCentredOn({ x: 0, y: 0 }, [{ x: 0, y: 0 }]), { minX: 0, minY: 0, maxX: 0, maxY: 0 });
  assert.throws(() => boundsCentredOn(null, []), TypeError);
});

test("projects cell corners and centres with one convention", () => {
  // 10 cells across 1000 px: 100 px per cell, centred on cell (4,7)'s centre.
  const view = createView(4.5, 7.5, 10);
  assert.deepEqual(cellRect(view, FRAME, 4, 7), { left: 450, top: 250, right: 550, bottom: 350 });
  assert.deepEqual(project(view, FRAME, cellCentre(4, 7)), { x: 500, y: 300 });
  assert.equal(cellRect(view, FRAME, 5, 7).left, 550);
  // A cell-unit position belongs to the cell that starts at its floor.
  assert.deepEqual(cellOf({ x: 4.5, y: 7.999 }), { col: 4, row: 7 });
  assert.deepEqual(cellOf({ x: -0.2, y: -1 }), { col: -1, row: -1 });
});

test("insets a host rectangle and collapses one squeezed below zero", () => {
  assert.deepEqual(insetRect(FRAME), { left: 24, top: 24, right: 976, bottom: 576 });
  assert.deepEqual(insetRect(FRAME, { reservedRight: 360 }), { left: 24, top: 24, right: 616, bottom: 576 });
  assert.deepEqual(
    insetRect(FRAME, { reservedRight: 360, insets: { top: 40, left: 10, bottom: 52, right: 6 } }),
    { left: 34, top: 64, right: 610, bottom: 524 },
  );
  // A reservation wider than the frame collapses both sides to the midpoint.
  assert.deepEqual(insetRect({ width: 300, height: 200 }, { reservedRight: 360 }), {
    left: -30,
    top: 24,
    right: -30,
    bottom: 176,
  });
  // The host may zero the margin and keep its own insets.
  assert.deepEqual(insetRect(FRAME, { marginPx: 0, insets: { bottom: 20 } }), {
    left: 0,
    top: 0,
    right: 1000,
    bottom: 580,
  });
  assert.deepEqual(rectCentre({ left: 0, top: 0, right: 1000, bottom: 600 }), { x: 500, y: 300 });
});

test("clamps a target to the nearest rectangle edge on every side", () => {
  const rect = insetRect(FRAME, { reservedRight: 360 });
  // Rect centre (320, 300); half extents 296 x 276.
  assert.deepEqual(clampToRect(rect, { x: 1400, y: 300 }), { x: 616, y: 300, inside: false, side: "right", angle: 0 });
  assert.deepEqual(clampToRect(rect, { x: -500, y: 300 }), { x: 24, y: 300, inside: false, side: "left", angle: 180 });
  assert.deepEqual(clampToRect(rect, { x: 320, y: -900 }), { x: 320, y: 24, inside: false, side: "top", angle: -90 });
  assert.deepEqual(clampToRect(rect, { x: 320, y: 2000 }), { x: 320, y: 576, inside: false, side: "bottom", angle: 90 });
  // A diagonal target up-right: dx 680, dy -600 from the centre.
  // tx = 296/680 = 0.43529, ty = 276/600 = 0.46 -> right edge first.
  const diag = clampToRect(rect, { x: 1000, y: -300 });
  assert.equal(diag.side, "right");
  close(diag.x, 616);
  close(diag.y, 300 - 600 * (296 / 680));
  close(diag.angle, (Math.atan2(-600, 680) * 180) / Math.PI);
  // A steep target hits the top edge.
  const steep = clampToRect(rect, { x: 700, y: -2000 });
  assert.equal(steep.side, "top");
  close(steep.y, 24);
  close(steep.x, 320 + 380 * (276 / 2300));
});

test("leaves on-screen targets, boundary targets and the centre in place", () => {
  const rect = insetRect(FRAME, { reservedRight: 360 });
  assert.deepEqual(clampToRect(rect, { x: 616, y: 576 }), {
    x: 616,
    y: 576,
    inside: true,
    side: null,
    angle: (Math.atan2(276, 296) * 180) / Math.PI,
  });
  assert.deepEqual(clampToRect(rect, { x: 320, y: 300 }), { x: 320, y: 300, inside: true, side: null, angle: 0 });
  // Behind the reservation counts as off-screen.
  assert.deepEqual(clampToRect(rect, { x: 800, y: 300 }), { x: 616, y: 300, inside: false, side: "right", angle: 0 });
  // A rectangle collapsed on both axes degrades to its single point.
  const dot = { left: 5, top: 7, right: 5, bottom: 7 };
  assert.deepEqual(clampToRect(dot, { x: 50, y: 8 }), {
    x: 5,
    y: 7,
    inside: false,
    side: "right",
    angle: (Math.atan2(1, 45) * 180) / Math.PI,
  });
  // Away from the centre row the remaining vertical axis stops the ray.
  assert.equal(clampToRect({ left: -30, top: 24, right: -30, bottom: 176 }, { x: 500, y: -100 }).side, "top");
});
