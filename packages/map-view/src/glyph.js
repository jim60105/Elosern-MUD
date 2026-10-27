// Shared glyph shape foundations: the painted metrics of a map's point glyph,
// the gate arch path, and the footprint of a glyph drawn at a surface's
// uniform scale. A surface scales the whole glyph group (strokes and dashes
// included), so surfaces differ only by that scale and never by shape.
//
// The host supplies the glyph input; this module never inspects a game node,
// a visibility token or a payload:
//
//   glyph { state, gateway, haloTarget }
//     state        "current" for the current position, anything else for a
//                  regular node
//     gateway      the node carries a gate (its arch is the widest shape)
//     haloTarget   the node carries a travel/highlight halo
//
// A footprint is the radius of the whole painted mark, stroke included, at a
// given scale.

import { requirePositive } from "./values.js";

export const HERE_GLOW_R = 14;
export const HERE_RING_R = 10;
export const HERE_DOT_R = 6;
export const NODE_DOT_R = 5.5;
export const HALO_R = 15;
// The gate: a filled arch `GATE_HALF` wide either side, its springing line
// 2 units above the node centre and its base `GATE_HALF` below.
export const GATE_HALF = 8;
export const GATE_STROKE = 2;
// The rim edge markers' landmark ring (edge direction diamonds only).
export const MARKER_LANDMARK_R = 5;
// The mitred base corners are the farthest painted points of the arch.
export const GATE_FOOTPRINT = Math.hypot(GATE_HALF + GATE_STROKE / 2, GATE_HALF + GATE_STROKE / 2);

/** The gate arch's base path; a surface scales the whole glyph group instead. */
export function gatePath() {
  const h = GATE_HALF;
  return `M${-h} ${h} V-2 A${h} ${h} 0 0 1 ${h} -2 V${h} Z`;
}

/** The painted footprint of one glyph input drawn at `size`. */
export function glyphFootprint(glyph, size = 1) {
  requirePositive(size, "size");
  const halo = glyph?.haloTarget ? HALO_R + 1 : 0;
  if (glyph?.state === "current") return Math.max(halo, HERE_GLOW_R) * size;
  if (glyph?.gateway) return Math.max(halo, GATE_FOOTPRINT) * size;
  return Math.max(halo, NODE_DOT_R + GATE_STROKE / 2) * size;
}
