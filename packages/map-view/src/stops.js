// Named zoom stops: the shared stepping rules for a scope's own stop table.
// The spans and labels are the host's policy (a game's continent and district
// scales, an editor's own); this module only orders, dedupes, selects and
// bounds them.

import { FREEZE, requirePositive } from "./values.js";

/** Continuous wheel zoom may go this far past the narrowest/widest stop. */
export const ZOOM_IN_SLACK = 0.5;
export const ZOOM_OUT_SLACK = 1.25;
/** Plus/minus treat spans within this ratio as "already at that stop". */
export const STOP_STEP_TOLERANCE = 0.05;
/** Stops whose spans differ by less than this ratio collapse into one. */
const STOP_DEDUPE_RATIO = 1.01;

/** A validated, frozen named zoom stop (span = map units across the frame). */
export function createStop(key, label, span) {
  return FREEZE({ key, label, span: requirePositive(span, `${key} span`) });
}

/**
 * Widest first; a stop not clearly narrower than the one before collapses
 * into it so plus/minus never land on a no-op step.
 */
export function orderedStops(list) {
  const out = [];
  for (const entry of list) {
    const last = out[out.length - 1];
    if (!last || last.span / entry.span >= STOP_DEDUPE_RATIO) out.push(entry);
  }
  return FREEZE(out);
}

function requireStops(stops) {
  if (!Array.isArray(stops) || !stops.length) {
    throw new TypeError("map-view: stops must be a non-empty array");
  }
  return stops;
}

/** Continuous-zoom limits derived from the scope's stops. */
export function spanLimits(stops) {
  requireStops(stops);
  const spans = stops.map((s) => s.span);
  return FREEZE({ min: Math.min(...spans) * ZOOM_IN_SLACK, max: Math.max(...spans) * ZOOM_OUT_SLACK });
}

/** The stop whose span is closest to `span` on a log scale (pill caption). */
export function nearestStop(stops, span) {
  requireStops(stops);
  requirePositive(span, "span");
  let best = stops[0];
  for (const entry of stops) {
    if (Math.abs(Math.log(entry.span / span)) < Math.abs(Math.log(best.span / span))) best = entry;
  }
  return best;
}

/** `＋`: the widest stop clearly narrower than span, or null at the end. */
export function nextStop(stops, span) {
  requireStops(stops);
  requirePositive(span, "span");
  return stops.find((s) => s.span < span * (1 - STOP_STEP_TOLERANCE)) ?? null;
}

/** `－`: the narrowest stop clearly wider than span, or null at the end. */
export function previousStop(stops, span) {
  requireStops(stops);
  requirePositive(span, "span");
  return [...stops].reverse().find((s) => s.span > span * (1 + STOP_STEP_TOLERANCE)) ?? null;
}
