// Explicit value types shared by every map surface. The package works on
// plain frozen values and never reads a host object: a caller passes a view,
// a frame, a point, a rect or bounds, and gets a new frozen value back.
//
//   view   { cx, cy, span }                 centre in map units, span = map
//                                           units across the full measured
//                                           frame width
//   frame  { width, height }                measured CSS pixels of the surface
//   point  { x, y }                         map units (north-positive) or
//                                           frame pixels, per function
//   rect   { left, top, right, bottom }     CSS pixels inside the frame
//   bounds { minX, minY, maxX, maxY }       map units
//   unit   { key, metres }                  metres per map unit
//   stop   { key, label, span }             a named zoom stop
//
// Canonical frames are +x east and +y north; projection inverts only the
// north axis for the screen. Invalid programmer input (non-finite numbers,
// non-positive frame or span) throws TypeError/RangeError instead of letting
// NaN into view state. A host whose ResizeObserver reports a 0x0 frame on the
// first paint skips the call.

export const FREEZE = Object.freeze;

export function isFiniteNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

export function requireFinite(value, name) {
  if (!isFiniteNumber(value)) {
    throw new TypeError(`map-view: ${name} must be a finite number`);
  }
  return value;
}

export function requirePositive(value, name) {
  requireFinite(value, name);
  if (value <= 0) {
    throw new RangeError(`map-view: ${name} must be positive`);
  }
  return value;
}

export function requireFrame(frame) {
  if (!frame) throw new TypeError("map-view: frame is required");
  requirePositive(frame.width, "frame.width");
  requirePositive(frame.height, "frame.height");
  return frame;
}

export function requireView(view) {
  if (!view) throw new TypeError("map-view: view is required");
  requireFinite(view.cx, "view.cx");
  requireFinite(view.cy, "view.cy");
  requirePositive(view.span, "view.span");
  return view;
}

export function requirePoint(point, name) {
  if (!point) throw new TypeError(`map-view: ${name} is required`);
  requireFinite(point.x, `${name}.x`);
  requireFinite(point.y, `${name}.y`);
  return point;
}

export function requireBounds(bounds) {
  if (!bounds) throw new TypeError("map-view: bounds is required");
  for (const key of ["minX", "minY", "maxX", "maxY"]) requireFinite(bounds[key], `bounds.${key}`);
  if (bounds.maxX < bounds.minX || bounds.maxY < bounds.minY) {
    throw new RangeError("map-view: bounds max must not be below min");
  }
  return bounds;
}

export function requireRect(rect) {
  if (!rect) throw new TypeError("map-view: rect is required");
  for (const key of ["left", "top", "right", "bottom"]) requireFinite(rect[key], `rect.${key}`);
  if (rect.right < rect.left || rect.bottom < rect.top) {
    throw new RangeError("map-view: rect right/bottom must not be below left/top");
  }
  return rect;
}

/** Builds a validated, frozen view. */
export function createView(cx, cy, span) {
  return FREEZE(requireView({ cx, cy, span }));
}
