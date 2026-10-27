// Stop tables: ordering/dedupe, log-nearest selection, plus/minus stepping
// with tolerance, and the continuous-zoom limits derived from a scope's own
// table. The spans and labels belong to the host; these are the shared rules.

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  STOP_STEP_TOLERANCE,
  ZOOM_IN_SLACK,
  ZOOM_OUT_SLACK,
  createStop,
  nearestStop,
  nextStop,
  orderedStops,
  previousStop,
  spanLimits,
} from "../src/stops.js";
import { createView } from "../src/values.js";
import { zoomAt } from "../src/navigation.js";

const FRAME = Object.freeze({ width: 1000, height: 600 });
// A synthetic scope table: spans only, labels are the host's own copy.
const STOPS = orderedStops([
  createStop("continent", "A", 8000),
  createStop("country", "B", 800),
  createStop("district", "C", 200),
  createStop("nearby", "D", 40),
]);

test("orders and dedupes a scope stop table widest first", () => {
  assert.deepEqual(STOPS.map((s) => s.span), [8000, 800, 200, 40]);
  assert.ok(Object.isFrozen(STOPS));
  // A stop not clearly narrower than the one before collapses into it.
  const collapsed = orderedStops([createStop("wide", "A", 800), createStop("same", "B", 795)]);
  assert.deepEqual(collapsed.map((s) => s.key), ["wide"]);
  // A clearly narrower stop is kept.
  assert.deepEqual(orderedStops([createStop("a", "A", 800), createStop("b", "B", 700)]).map((s) => s.key), ["a", "b"]);
  assert.throws(() => createStop("bad", "X", 0), RangeError);
});

test("steps between stops with plus and minus and tolerates a near stop", () => {
  assert.equal(nextStop(STOPS, 8000).key, "country");
  assert.equal(nextStop(STOPS, 800).key, "district");
  // Between stops, plus goes to the next narrower one, minus to the wider.
  assert.equal(nextStop(STOPS, 500).key, "district");
  assert.equal(previousStop(STOPS, 500).key, "country");
  // Within tolerance of a stop counts as being on it.
  assert.equal(previousStop(STOPS, 790).key, "continent");
  assert.equal(nextStop(STOPS, 790).key, "district");
  assert.equal(nextStop(STOPS, 40), null);
  assert.equal(previousStop(STOPS, 8000), null);
  assert.equal(STOP_STEP_TOLERANCE, 0.05);
});

test("picks the log-nearest stop and derives continuous zoom limits", () => {
  assert.equal(nearestStop(STOPS, 260).key, "district");
  // The log midpoint of 200 and 40 is about 89.4; 80 is nearer 40, 95 nearer 200.
  assert.equal(nearestStop(STOPS, 80).key, "nearby");
  assert.equal(nearestStop(STOPS, 95).key, "district");
  const limits = spanLimits(STOPS);
  assert.equal(limits.min, 40 * ZOOM_IN_SLACK);
  assert.equal(limits.max, 8000 * ZOOM_OUT_SLACK);
  // Limits are spans, never a lattice scale floor.
  assert.equal(zoomAt(createView(0, 0, 40), FRAME, 1, null, limits).span, 20);
  assert.throws(() => spanLimits([]), TypeError);
  assert.throws(() => nearestStop(STOPS, 0), RangeError);
});
