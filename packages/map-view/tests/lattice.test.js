// The scale-true dot lattice: only geometry comes back, the caption stays the
// host's. Steps are the smallest round 1/2/5 x 10^n value that keeps the
// minimum on-screen gap.

import assert from "node:assert/strict";
import { test } from "node:test";

import { createView } from "../src/values.js";
import { UNITS, cellUnit } from "../src/units.js";
import { dotField, niceStepAtLeast } from "../src/lattice.js";

const FRAME = Object.freeze({ width: 1000, height: 600 });
const close = (actual, expected, digits = 9) => assert.ok(Math.abs(actual - expected) < 10 ** -digits, `${actual} ≉ ${expected}`);

test("chooses the smallest round step whose dots keep the minimum gap", () => {
  assert.equal(niceStepAtLeast(15), 20);
  assert.equal(niceStepAtLeast(10), 10);
  assert.equal(niceStepAtLeast(11), 20);
  assert.equal(niceStepAtLeast(60), 100);
  assert.equal(niceStepAtLeast(510), 1000);
  assert.equal(niceStepAtLeast(1), 1);
});

test("places the lattice phase from the world origin", () => {
  // span 500 m over 1000 px -> k = 2 px/m, 30 px needs 15 m -> a 20 m step,
  // so dots stand 40 px apart. The origin sits at the frame centre.
  const field = dotField(createView(0, 0, 500), FRAME, UNITS.m, 30, 0);
  assert.equal(field.stepMetres, 20);
  assert.equal(field.stepUnits, 20);
  assert.equal(field.spacingPx, 40);
  assert.equal(field.offsetX, 20);
  assert.equal(field.offsetY, 20);
  assert.ok(Object.isFrozen(field));
  // Panning by half a step slides the phase and nothing else.
  const panned = dotField(createView(10, 0, 500), FRAME, UNITS.m, 30, 0);
  assert.equal(panned.offsetX, 0);
  close(panned.spacingPx, 40);
});

test("marks provider cell corners instead of halving a cell", () => {
  // 17 one-kilometre cells over 1000 px: 30 px needs 510 m, but the cell
  // floor forces one whole cell, so the dots mark the cell corners.
  const field = dotField(createView(0, 0, 17), FRAME, cellUnit(1000), 30, 1000);
  assert.equal(field.stepMetres, 1000);
  assert.equal(field.stepUnits, 1);
  close(field.spacingPx, 1000 / 17);
});

test("returns no lattice for a scope without a metric unit", () => {
  // A coordinate-free room graph states no distance: no dots, no caption.
  assert.equal(dotField(createView(0, 0, 100), FRAME, null), null);
});
