// Uniform metric projection: one scale k = frame.width / view.span on both
// axes, with only the north axis inverted for the screen, so canonical
// coordinates are never rewritten and unequal metric gaps stay unequal (no
// row/column rank compression).

import { FREEZE, requireFrame, requirePoint, requireView } from "./values.js";

/** Pixels per map unit; identical on both axes. */
export function scaleOf(view, frame) {
  requireView(view);
  requireFrame(frame);
  return frame.width / view.span;
}

/** Map point -> frame pixel (north up). */
export function project(view, frame, point) {
  const k = scaleOf(view, frame);
  requirePoint(point, "point");
  return FREEZE({
    x: frame.width / 2 + (point.x - view.cx) * k,
    y: frame.height / 2 - (point.y - view.cy) * k,
  });
}

/** Frame pixel -> map point; the exact inverse of project. */
export function unproject(view, frame, pixel) {
  const k = scaleOf(view, frame);
  requirePoint(pixel, "pixel");
  return FREEZE({
    x: view.cx + (pixel.x - frame.width / 2) / k,
    y: view.cy - (pixel.y - frame.height / 2) / k,
  });
}
