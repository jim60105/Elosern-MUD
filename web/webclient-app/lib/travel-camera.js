// The travel stage's camera (OpenSpec change wilderness-travel-map-ui;
// interface design §4.3/§4.4). Pure functions over measured rectangles, no
// DOM: the stage measures the HudFrame's real header, band and side columns
// and hands their rectangles in.
//
// World space is laid out north-up in CSS pixels at `cellPx` per cell: the
// cell `(x, y)` (map y grows northward) spans `[x * cellPx, (x + 1) * cellPx)`
// horizontally and `[-(y + 1) * cellPx, -y * cellPx)` vertically. A camera is
// the translation `{ tx, ty }` that puts world space on the stage, plus the
// cell size it was computed for. Nothing here touches the painted canvas, so
// a camera or zoom change is a transform, never a repaint.

import { SIGHTING_BEARINGS } from "./area_map_view.js";

/** Zoom steps in CSS px per cell before the UI scale (design §4.4). */
export const ZOOM = Object.freeze({ min: 18, max: 46, step: 4, initial: 30 });
/** The smallest fitted cell, before the UI scale. */
export const FIT_MIN_CELL = 14;
/** The camera glide in ms, multiplied by `--motion-travel`. */
export const GLIDE_MS = 380;

function finite(value, fallback) {
  return Number.isFinite(value) ? value : fallback;
}

/** A usable UI scale: a positive finite number, else 1. */
export function safeScale(uiScale) {
  const value = Number(uiScale);
  return Number.isFinite(value) && value > 0 ? value : 1;
}

/** The zoom one step in `direction` (+1 in, -1 out) from `zoom`, clamped. */
export function stepZoom(zoom, direction) {
  const current = clampZoom(zoom);
  return clampZoom(current + Math.sign(direction) * ZOOM.step);
}

/** A zoom snapped onto the 18..46 ladder of 4 px steps. */
export function clampZoom(zoom) {
  const value = finite(Number(zoom), ZOOM.initial);
  const snapped = ZOOM.min + Math.round((value - ZOOM.min) / ZOOM.step) * ZOOM.step;
  return Math.min(ZOOM.max, Math.max(ZOOM.min, snapped));
}

/** The CSS cell size of a zoom at a UI scale (the scale applies once). */
export function cellSize(zoom, uiScale) {
  return clampZoom(zoom) * safeScale(uiScale);
}

/** The world-space centre of cell `(x, y)` at `cellPx`. */
export function cellCentre(x, y, cellPx) {
  return { x: (x + 0.5) * cellPx, y: -(y + 0.5) * cellPx };
}

function usable(rect) {
  return !!rect && Number.isFinite(rect.left) && Number.isFinite(rect.top) && rect.width > 0 && rect.height > 0;
}

/**
 * The stage rectangles from measured bounds, all relative to the map root:
 *
 * - `stage`: the open stage, full width, between the header's bottom and
 *   the band's top;
 * - `safe`: the same strip narrowed past the vitals/medallion column on the
 *   left and the place-card column on the right, inset by `gap`.
 *
 * `root` is the map's own rect; `headerBottom` and `bandTop` are client y
 * values (or null); `left` and `right` are the side columns' client rects
 * (or null). A missing or empty measurement falls back to the root's edge,
 * so a bare stage (no frame) still has a usable rectangle.
 */
export function openStage({ root, headerBottom = null, bandTop = null, left = null, right = null, gap = 16 }) {
  const width = Math.max(1, finite(root?.width, 1));
  const height = Math.max(1, finite(root?.height, 1));
  const ox = finite(root?.left, 0);
  const oy = finite(root?.top, 0);
  const top = Math.min(height - 1, Math.max(0, finite(headerBottom, oy) - oy));
  const bottom = Math.max(top + 1, Math.min(height, finite(bandTop, oy + height) - oy));
  const stage = { left: 0, top, right: width, bottom };
  let safeLeft = usable(left) ? left.left + left.width - ox + gap : gap;
  let safeRight = usable(right) ? right.left - ox - gap : width - gap;
  if (safeRight - safeLeft < 1) {
    safeLeft = 0;
    safeRight = width;
  }
  return { stage, safe: { left: safeLeft, top, right: safeRight, bottom } };
}

function centreOf(rect) {
  return { x: (rect.left + rect.right) / 2, y: (rect.top + rect.bottom) / 2 };
}

/**
 * Follow: the party cell's centre at the centre of the open stage (between
 * the header and the band).
 */
export function followCamera({ party, cellPx, stage }) {
  const c = centreOf(stage);
  const p = cellCentre(finite(party?.x, 0), finite(party?.y, 0), cellPx);
  return { tx: c.x - p.x, ty: c.y - p.y, cellPx };
}

/**
 * Fit: the bounding box of `points` (the party, every route step and the
 * destination, as cells) centred in the safe rectangle between the side
 * columns, with a margin of `margin` cells. The cell shrinks from `cellPx`
 * as needed but never below `minCellPx`; when even that cannot fit, it stays
 * at the minimum, centred, and the stage clips the overflow.
 */
export function fitRouteCamera({ points, cellPx, minCellPx, safe, margin = 1.5 }) {
  const cells = (points ?? []).filter((p) => Number.isFinite(p?.x) && Number.isFinite(p?.y));
  if (!cells.length) return { tx: 0, ty: 0, cellPx };
  const minX = Math.min(...cells.map((p) => p.x));
  const maxX = Math.max(...cells.map((p) => p.x)) + 1;
  const minY = Math.min(...cells.map((p) => p.y));
  const maxY = Math.max(...cells.map((p) => p.y)) + 1;
  const spanX = maxX - minX + margin * 2;
  const spanY = maxY - minY + margin * 2;
  const fit = Math.min((safe.right - safe.left) / spanX, (safe.bottom - safe.top) / spanY);
  const size = Math.max(minCellPx, Math.min(cellPx, fit));
  const c = centreOf(safe);
  const bx = ((minX + maxX) / 2) * size;
  const by = -((minY + maxY) / 2) * size;
  return { tx: c.x - bx, ty: c.y - by, cellPx: size };
}

/** The bearing's screen angle in radians, clockwise from north, or null. */
export function bearingAngle(bearing) {
  const sector = SIGHTING_BEARINGS.indexOf(bearing);
  return sector < 0 ? null : (sector * 22.5 * Math.PI) / 180;
}

/**
 * Distant sightings on the safe rectangle's inset edge. Each card sits where
 * the ray from the safe rectangle's centre along its compass bearing meets
 * the rectangle shrunk by `inset` (`{ x, y }` half extents of the card, so a
 * card's box never crosses the edge). A sighting carries no coordinates and
 * none are made: only the bearing places it. An unknown bearing is dropped.
 * Returns `[{ sighting, angle, x, y, ux, uy }]` in stage coordinates.
 */
export function projectSightings(sightings, { safe, inset = { x: 0, y: 0 } }) {
  const c = centreOf(safe);
  const left = Math.min(c.x, safe.left + inset.x);
  const right = Math.max(c.x, safe.right - inset.x);
  const top = Math.min(c.y, safe.top + inset.y);
  const bottom = Math.max(c.y, safe.bottom - inset.y);
  const out = [];
  for (const sighting of sightings ?? []) {
    const angle = bearingAngle(sighting?.bearing);
    if (angle === null) continue;
    const ux = Math.sin(angle);
    const uy = -Math.cos(angle);
    const limits = [];
    if (ux > 1e-9) limits.push((right - c.x) / ux);
    if (ux < -1e-9) limits.push((left - c.x) / ux);
    if (uy > 1e-9) limits.push((bottom - c.y) / uy);
    if (uy < -1e-9) limits.push((top - c.y) / uy);
    const t = Math.max(0, Math.min(...limits));
    out.push({ sighting, angle, x: c.x + ux * t, y: c.y + uy * t, ux, uy });
  }
  return out;
}
