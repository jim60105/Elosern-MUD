// The scale-true dot lattice behind a metric view. Dots sit on every integer
// world multiple of a round 1/2/5 x 10^n step, chosen as the smallest step
// whose on-screen gap is at least `minGapPx` (and, for provider cell units, at
// least one cell, so dots mark cell corners instead of halving a cell). Only
// geometry is returned; the caption text is the host's.

import { FREEZE } from "./values.js";
import { project } from "./projection.js";

/** Smallest 1/2/5 x 10^n value at least `value`. */
export function niceStepAtLeast(value) {
  const power = 10 ** Math.floor(Math.log10(value));
  for (const step of [1, 2, 5, 10]) {
    if (step * power >= value * (1 - 1e-9)) return step * power;
  }
  return 10 * power;
}

/**
 * The dot lattice for a metric view: `{ stepMetres, stepUnits, spacingPx,
 * offsetX, offsetY }`, where the offsets are the lattice phase in
 * [0, spacingPx). Returns null for a scope without a metric unit (a
 * coordinate-free room graph states no distance).
 */
export function dotField(view, frame, unit, minGapPx = 30, minStepMetres = 0) {
  if (!unit) return null;
  const k = frame.width / view.span;
  const metresPerPx = unit.metres / k;
  const stepMetres = niceStepAtLeast(Math.max(minGapPx * metresPerPx, minStepMetres));
  const stepUnits = stepMetres / unit.metres;
  const spacingPx = stepUnits * k;
  const origin = project(view, frame, { x: 0, y: 0 });
  const phase = (value) => ((value % spacingPx) + spacingPx) % spacingPx;
  return FREEZE({
    stepMetres,
    stepUnits,
    spacingPx,
    offsetX: phase(origin.x),
    offsetY: phase(origin.y),
  });
}
