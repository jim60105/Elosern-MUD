// Metric placement of the nodes a host already placed. Nothing here invents a
// coordinate: a node without finite x and y is not a metric point, and a layer
// that holds one such node is not metric. Coordinate-free room graphs stay on
// their own renderer and never reach these helpers.

import { FREEZE, isFiniteNumber, requirePoint } from "./values.js";

function hasMetricPosition(node) {
  return !!node && isFiniteNumber(node.x) && isFiniteNumber(node.y);
}

/** Only the nodes that already carry finite x and y; nothing is fabricated. */
export function metricPoints(nodes) {
  return FREEZE((Array.isArray(nodes) ? nodes : []).filter(hasMetricPosition));
}

/** True when a layer can use metric projection (non-empty, every node placed). */
export function isMetricLayer(nodes) {
  return Array.isArray(nodes) && nodes.length > 0 && nodes.every(hasMetricPosition);
}

/** Axis-aligned bounds of the points that carry finite metric coordinates. */
export function metricBounds(points) {
  const metric = metricPoints(points);
  if (!metric.length) return null;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const { x, y } of metric) {
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
  }
  return FREEZE({ minX, minY, maxX, maxY });
}

/** Axis-aligned bounds of every supplied point (an empty list is infinite). */
export function boundsOfPoints(points) {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const { x, y } of points) {
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
  }
  return FREEZE({ minX, minY, maxX, maxY });
}

/**
 * Bounds centred on `here` that reach every supplied point, on both axes
 * independently. Used for a neighbourhood fit around a scope's own anchor.
 */
export function boundsCentredOn(here, points) {
  requirePoint(here, "here");
  let rx = 0;
  let ry = 0;
  for (const { x, y } of points) {
    rx = Math.max(rx, Math.abs(x - here.x));
    ry = Math.max(ry, Math.abs(y - here.y));
  }
  return FREEZE({ minX: here.x - rx, minY: here.y - ry, maxX: here.x + rx, maxY: here.y + ry });
}
