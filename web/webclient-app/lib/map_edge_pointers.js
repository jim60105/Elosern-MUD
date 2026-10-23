// Off-screen commission pointers for the map drawer (OpenSpec change
// redesign-map-drawer; approved design
// docs/superpowers/specs/2026-10-22-world-map-drawer-design.md §6.2/§6.5).
// Dependency-free apart from the shared viewport clamp: no Vue, no DOM.
//
// A target is `{ id, title, sub, x, y, distance }` in frame pixels (its
// projected position, usually far outside the frame) with its map distance
// from the player. Targets inside the usable rectangle draw no pointer. The
// rest are ordered nearest first; the three nearest are shown on the
// rectangle's edge where the ray from its centre leaves it (map_viewport.js
// clampToRect, so the pointers avoid the open detail drawer whenever the host
// passes a drawer-aware rectangle), and any further ones collapse into one
// `＋n` chip. Pointers on one side never overlap: in distance order each one
// keeps the spot nearest its true crossing that is a full pitch away from
// those already placed, staying inside the side's span.

import { clampToRect } from "./map_viewport.js";

/** At most this many pointers are drawn; the rest collapse into `＋n`. */
export const MAX_EDGE_POINTERS = 3;
/** Minimum centre-to-centre spacing of two pointers on one side (CSS px). */
export const POINTER_PITCH_PX = 44;

/** A far point along a compass bearing (degrees clockwise from north). */
export function farPointAlongBearing(origin, bearingDeg, reach) {
  const rad = (bearingDeg * Math.PI) / 180;
  return { x: origin.x + Math.sin(rad) * reach, y: origin.y + Math.cos(rad) * reach };
}

function axisOf(side) {
  return side === "top" || side === "bottom" ? "x" : "y";
}

// The span a pointer's centre may use along its side: the rectangle's edge
// shortened by half the pointer's own extent, so the whole chip stays in.
function spanOf(rect, side, halfWidth, halfHeight) {
  const [lo, hi, half] =
    axisOf(side) === "x" ? [rect.left, rect.right, halfWidth] : [rect.top, rect.bottom, halfHeight];
  if (hi - lo <= 2 * half) return [(lo + hi) / 2, (lo + hi) / 2];
  return [lo + half, hi - half];
}

// The free coordinate nearest `want` on [lo, hi] at least `pitch` from every
// taken coordinate; when the side is full the nearest end is used.
function freeSpot(want, taken, lo, hi, pitch) {
  const clear = (v) => taken.every((t) => Math.abs(t - v) >= pitch - 1e-9);
  const inSpan = (v) => v >= lo - 1e-9 && v <= hi + 1e-9;
  const start = Math.min(hi, Math.max(lo, want));
  if (clear(start)) return start;
  const candidates = taken
    .flatMap((t) => [t - pitch, t + pitch])
    .filter((v) => inSpan(v) && clear(v))
    .sort((a, b) => Math.abs(a - start) - Math.abs(b - start));
  if (candidates.length) return candidates[0];
  return Math.abs(start - lo) <= Math.abs(hi - start) ? lo : hi;
}

/**
 * Lays out the visible pointers and the overflow chip. `halfWidth` and
 * `halfHeight` are half a pointer's extent: a top/bottom pointer is centred
 * on its point, a left/right one is vertically centred on it, so the span
 * along each side is shortened by that half to keep the chip inside.
 * Returns `{ pointers: [{ id, title, sub, x, y, side, angle, distance }],
 * more: null | { count, ids, x, y, side, angle } }`.
 */
export function layoutEdgePointers(
  targets,
  rect,
  { max = MAX_EDGE_POINTERS, pitch = POINTER_PITCH_PX, halfWidth = 0, halfHeight = 0 } = {},
) {
  const outside = (Array.isArray(targets) ? targets : [])
    .filter((t) => Number.isFinite(t.x) && Number.isFinite(t.y))
    .map((t) => ({ target: t, clamp: clampToRect(rect, { x: t.x, y: t.y }) }))
    .filter((entry) => !entry.clamp.inside)
    .sort((a, b) => a.target.distance - b.target.distance || String(a.target.id).localeCompare(String(b.target.id)));
  const shown = outside.slice(0, max);
  const hidden = outside.slice(max);
  const taken = { top: [], right: [], bottom: [], left: [] };

  function place(clamp) {
    const side = clamp.side;
    const axis = axisOf(side);
    const [lo, hi] = spanOf(rect, side, halfWidth, halfHeight);
    // Top/bottom chips stack along their width, not their two-line height.
    const spacing = Math.max(pitch, 2 * (axis === "x" ? halfWidth : halfHeight) + 8);
    const v = freeSpot(clamp[axis], taken[side], lo, hi, spacing);
    taken[side].push(v);
    return axis === "x" ? { x: v, y: clamp.y } : { x: clamp.x, y: v };
  }

  const pointers = shown.map(({ target, clamp }) =>
    Object.freeze({
      id: target.id,
      title: target.title,
      sub: target.sub,
      distance: target.distance,
      side: clamp.side,
      angle: clamp.angle,
      ...place(clamp),
    }),
  );
  let more = null;
  if (hidden.length) {
    const first = hidden[0].clamp;
    more = Object.freeze({
      count: hidden.length,
      ids: Object.freeze(hidden.map((entry) => entry.target.id)),
      side: first.side,
      angle: first.angle,
      ...place(first),
    });
  }
  return Object.freeze({ pointers: Object.freeze(pointers), more });
}
