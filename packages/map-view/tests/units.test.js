// Units, distance captions and the scale bar. Expected values are computed by
// hand from the synthetic frames, not by calling the module under test.

import assert from "node:assert/strict";
import { test } from "node:test";

import { createView } from "../src/values.js";
import { UNITS, cellUnit, formatDistance, scaleBar, toMetres } from "../src/units.js";

const FRAME = Object.freeze({ width: 1000, height: 600 });
const close = (actual, expected, digits = 9) => assert.ok(Math.abs(actual - expected) < 10 ** -digits, `${actual} ≉ ${expected}`);

test("states explicit metre, kilometre and provider-cell units", () => {
  assert.equal(UNITS.m.metres, 1);
  assert.equal(UNITS.km.metres, 1000);
  assert.equal(toMetres(2.5, UNITS.km), 2500);
  assert.equal(toMetres(3, cellUnit(1000)), 3000);
  assert.equal(toMetres(3, cellUnit(250)), 750);
  assert.throws(() => cellUnit(0), RangeError);
  assert.throws(() => toMetres(1, { metres: -1 }), RangeError);
});

test("captions a distance in the larger unit past one kilometre", () => {
  assert.equal(formatDistance(850), "850 m");
  assert.equal(formatDistance(1500), "1.5 km");
  assert.equal(formatDistance(40000), "40 km");
  // Rounding happens before the unit switch.
  assert.equal(formatDistance(999.96), "1 km");
  assert.equal(formatDistance(999.94), "999.9 m");
  assert.equal(formatDistance(0), "0 m");
  assert.equal(formatDistance(-1500), "-1.5 km");
});

test("never collapses a sub-decimetre distance to zero", () => {
  // A synthetic compressed ring may sit at an arbitrarily small real
  // distance; the caption keeps the value instead of stating "0 m".
  assert.equal(formatDistance(0.01), "0.01 m");
  assert.equal(formatDistance(1e-9), "1e-9 m");
  assert.equal(formatDistance(0.06), "0.1 m");
});

test("sizes the scale bar from the same uniform scale", () => {
  // 500 m across 1000 px: 0.5 m/px; 120 px = 60 m -> the 50 m bar is 100 px.
  assert.deepEqual(scaleBar(createView(0, 0, 500), FRAME, UNITS.m), { metres: 50, px: 100, text: "50 m" });
  // 800 km across 1000 px: 800 m/px; 120 px = 96 km -> 50 km, 62.5 px.
  assert.deepEqual(scaleBar(createView(0, 0, 800), FRAME, UNITS.km), { metres: 50000, px: 62.5, text: "50 km" });
  // 17 one-km cells across 1000 px: 17 m/px; 120 px = 2040 m -> 2 km.
  const bar = scaleBar(createView(0, 0, 17), FRAME, cellUnit(1000));
  assert.equal(bar.metres, 2000);
  assert.equal(bar.text, "2 km");
  close(bar.px, 2000 / 17);
  // A narrower budget picks a smaller round length.
  assert.equal(scaleBar(createView(0, 0, 500), FRAME, UNITS.m, 60).metres, 20);
});
