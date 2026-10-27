// Uniform metric projection and its exact inverse. Every expected value is
// computed by hand from the synthetic inputs, never by calling the module.

import assert from "node:assert/strict";
import { test } from "node:test";

import { createView } from "../src/values.js";
import { project, scaleOf, unproject } from "../src/projection.js";

// A non-square frame: 1000 x 600 px.
const FRAME = Object.freeze({ width: 1000, height: 600 });
const close = (actual, expected, digits = 9) => assert.ok(Math.abs(actual - expected) < 10 ** -digits, `${actual} ≉ ${expected}`);
const closePoint = (actual, expected, digits = 9) => {
  close(actual.x, expected.x, digits);
  close(actual.y, expected.y, digits);
};

test("projects with one uniform scale and inverts only the north axis", () => {
  // span 500 m across 1000 px -> k = 2 px/m on both axes.
  const view = createView(3000, 2000, 500);
  assert.equal(scaleOf(view, FRAME), 2);
  // 100 m east, 50 m north of the centre.
  assert.deepEqual(project(view, FRAME, { x: 3100, y: 2050 }), { x: 700, y: 200 });
  // 25 m west, 75 m south.
  assert.deepEqual(project(view, FRAME, { x: 2975, y: 1925 }), { x: 450, y: 450 });
  assert.deepEqual(project(view, FRAME, { x: 3000, y: 2000 }), { x: 500, y: 300 });
});

test("round-trips project and unproject at several views", () => {
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

test("returns frozen results and never mutates its inputs", () => {
  const view = { cx: 10, cy: 20, span: 100 };
  const point = { x: 0, y: 0 };
  const out = [project(view, FRAME, point), unproject(view, FRAME, { x: 1, y: 2 })];
  for (const value of out) assert.ok(Object.isFrozen(value));
  assert.deepEqual(view, { cx: 10, cy: 20, span: 100 });
  assert.deepEqual(point, { x: 0, y: 0 });
});

test("rejects invalid frames, views and points instead of leaking NaN", () => {
  const view = createView(0, 0, 100);
  assert.throws(() => project(view, { width: 0, height: 600 }, { x: 0, y: 0 }), RangeError);
  assert.throws(() => project(view, { width: Number.NaN, height: 600 }, { x: 0, y: 0 }), TypeError);
  assert.throws(() => createView(0, 0, 0), RangeError);
  assert.throws(() => createView(Number.NaN, 0, 10), TypeError);
  assert.throws(() => project(view, FRAME, { x: "1", y: 0 }), TypeError);
  assert.throws(() => scaleOf(null, FRAME), TypeError);
});
