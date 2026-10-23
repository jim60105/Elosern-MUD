// Off-screen commission pointers for the map drawer (OpenSpec change
// redesign-map-drawer; approved design
// docs/superpowers/specs/2026-10-22-world-map-drawer-design.md §6.2/§6.5).
// Dependency-free apart from the shared viewport clamp: no Vue, no DOM.
//
// A target is `{ id, title, sub, x, y, distance }` in frame pixels (its
// projected position, usually far outside the frame) with its map distance
// from the player. Targets inside the usable rectangle draw no pointer. The
// rest are ordered nearest first; at most three are shown on the
// rectangle's edge where the ray from its centre leaves it (map_viewport.js
// clampToRect, so the pointers avoid the open detail drawer whenever the host
// passes a drawer-aware rectangle), and any further ones collapse into one
// `＋n` chip. In distance order each pointer keeps the nearest free spot on
// its edge. Conservative chip bounds prevent collisions across corners too;
// a full edge folds excess targets into the list and reserves its ＋n chip.

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
  const placed = [];
  const hidden = [];
  const gap = 8;

  function place(clamp, width = halfWidth) {
    const side = clamp.side;
    const axis = axisOf(side);
    if (2 * width > rect.right - rect.left || 2 * halfHeight > rect.bottom - rect.top) return null;
    const half = axis === "x" ? width : halfHeight;
    const [lo, hi] = spanOf(rect, side, width, halfHeight);
    const start = Math.min(hi, Math.max(lo, clamp[axis]));
    function bounds(v) {
      const x = axis === "x" ? v : clamp.x;
      const y = axis === "y" ? v : clamp.y;
      const left = side === "left" ? x : side === "right" ? x - 2 * width : x - width;
      const top = side === "top" ? y : side === "bottom" ? y - 2 * halfHeight : y - halfHeight;
      return { x, y, left, right: left + 2 * width, top, bottom: top + 2 * halfHeight };
    }
    // Include the free-interval boundaries of every previously painted chip,
    // including chips on adjacent edges. Width/height are conservative DOM
    // bounds, so corner collisions cannot hide behind per-side accounting.
    const candidates = [start, lo, hi];
    for (const item of placed) {
      const box = item.box;
      candidates.push(
        (axis === "x" ? box.left : box.top) - half - gap,
        (axis === "x" ? box.right : box.bottom) + half + gap,
      );
      if (item.clamp.side === side) {
        const spacing = Math.max(pitch, half + (axis === "x" ? item.width : halfHeight) + gap);
        candidates.push(box[axis] - spacing, box[axis] + spacing);
      }
    }
    candidates.sort((a, b) => Math.abs(a - start) - Math.abs(b - start));
    for (const v of candidates) {
      if (v < lo - 1e-9 || v > hi + 1e-9) continue;
      const box = bounds(v);
      const clear = placed.every((item) => {
        if (item.clamp.side === side) {
          const spacing = Math.max(pitch, half + (axis === "x" ? item.width : halfHeight) + gap);
          if (Math.abs(item.box[axis] - v) < spacing - 1e-9) return false;
        }
        const other = item.box;
        return box.right + gap <= other.left || other.right + gap <= box.left ||
          box.bottom + gap <= other.top || other.bottom + gap <= box.top;
      });
      if (clear) return box;
    }
    return null;
  }

  for (const entry of outside) {
    const box = placed.length < max ? place(entry.clamp) : null;
    if (box) placed.push({ ...entry, box, width: halfWidth });
    else hidden.push(entry);
  }
  let more = null;
  if (hidden.length) {
    // Reserve a real spot for ＋n. If necessary, fold the farthest painted
    // pointer into the list rather than letting either button overlap.
    let box;
    while (!(box = place(hidden[0].clamp, Math.min(halfWidth, 40))) && placed.length) {
      hidden.unshift(placed.pop());
    }
    if (box) {
      more = Object.freeze({
        count: hidden.length,
        ids: Object.freeze(hidden.map((entry) => entry.target.id)),
        side: hidden[0].clamp.side,
        angle: hidden[0].clamp.angle,
        x: box.x,
        y: box.y,
      });
    }
  }
  const pointers = placed.map(({ target, clamp, box }) =>
    Object.freeze({
      id: target.id,
      title: target.title,
      sub: target.sub,
      distance: target.distance,
      side: clamp.side,
      angle: clamp.angle,
      x: box.x,
      y: box.y,
    }),
  );
  return Object.freeze({ pointers: Object.freeze(pointers), more });
}
