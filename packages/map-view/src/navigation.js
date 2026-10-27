// Pan, anchored zoom, whole-map fit and rectangle geometry. Everything is in
// the caller's own units (metres, kilometres or provider cells); the package
// never converts a unit and never asks the host for chrome. A host measures
// its own control insets or an open detail panel and passes the resulting
// rectangle in, so no function here queries the DOM.

import { FREEZE, requireBounds, requireFinite, requireFrame, requirePoint, requirePositive, requireRect, requireView } from "./values.js";
import { scaleOf, unproject } from "./projection.js";

/** Pointer travel (CSS px) below which a press is a click, not a drag. */
export const DRAG_THRESHOLD_PX = 4;
/** Default pixel margin kept between map content and the frame. */
export const DEFAULT_MARGIN_PX = 24;
/** Wheel zoom: span multiplier per wheel deltaY unit. */
export const WHEEL_ZOOM_BASE = 1.0018;

export function rectCentre(rect) {
  return { x: (rect.left + rect.right) / 2, y: (rect.top + rect.bottom) / 2 };
}

/** Drag pan: the content follows the pointer by (dxPx, dyPx). */
export function panByPixels(view, frame, dxPx, dyPx) {
  const k = scaleOf(view, frame);
  requireFinite(dxPx, "dxPx");
  requireFinite(dyPx, "dyPx");
  return FREEZE({ cx: view.cx - dxPx / k, cy: view.cy + dyPx / k, span: view.span });
}

function clampSpan(span, limits) {
  if (!limits) return span;
  const min = requirePositive(limits.min, "limits.min");
  const max = requirePositive(limits.max, "limits.max");
  return Math.min(max, Math.max(min, span));
}

/**
 * Sets the span while the map point under anchorPx (default: frame centre)
 * stays under it. The span is clamped to limits first, and the centre shift
 * is derived from the clamped span.
 */
export function zoomAt(view, frame, nextSpan, anchorPx = null, limits = null) {
  requireView(view);
  requireFrame(frame);
  const span = clampSpan(requirePositive(nextSpan, "nextSpan"), limits);
  const anchor = anchorPx ? requirePoint(anchorPx, "anchorPx") : { x: frame.width / 2, y: frame.height / 2 };
  const pinned = unproject(view, frame, anchor);
  const k = frame.width / span;
  return FREEZE({
    cx: pinned.x - (anchor.x - frame.width / 2) / k,
    cy: pinned.y + (anchor.y - frame.height / 2) / k,
    span,
  });
}

/** Continuous zoom by a span factor (>1 zooms out) around an anchor. */
export function zoomBy(view, frame, factor, anchorPx = null, limits = null) {
  requireView(view);
  return zoomAt(view, frame, view.span * requirePositive(factor, "factor"), anchorPx, limits);
}

/** Span factor for a wheel event's deltaY (positive deltaY zooms out). */
export function wheelFactor(deltaY) {
  return WHEEL_ZOOM_BASE ** requireFinite(deltaY, "deltaY");
}

/** Recentre on a map point at the current span, placing it at rect's centre. */
export function centreOn(view, frame, point, rect = null) {
  const k = scaleOf(view, frame);
  requirePoint(point, "point");
  const target = rect ? rectCentre(requireRect(rect)) : { x: frame.width / 2, y: frame.height / 2 };
  return FREEZE({
    cx: point.x - (target.x - frame.width / 2) / k,
    cy: point.y + (target.y - frame.height / 2) / k,
    span: view.span,
  });
}

/**
 * The view that fits bounds inside rect (default: whole frame) minus marginPx
 * on every side, on both axes at one uniform scale. A zero extent on one axis
 * is ignored; bounds that are a single point need an explicit minSpan, which
 * also floors every result.
 */
export function fitBounds(bounds, frame, { rect = null, marginPx = DEFAULT_MARGIN_PX, minSpan = null } = {}) {
  requireBounds(bounds);
  requireFrame(frame);
  requireFinite(marginPx, "marginPx");
  const area = rect
    ? requireRect(rect)
    : { left: 0, top: 0, right: frame.width, bottom: frame.height };
  const innerW = area.right - area.left - 2 * marginPx;
  const innerH = area.bottom - area.top - 2 * marginPx;
  if (!(innerW > 0) || !(innerH > 0)) {
    throw new RangeError("map-view: fit area is empty after margins");
  }
  const bw = bounds.maxX - bounds.minX;
  const bh = bounds.maxY - bounds.minY;
  const candidates = [];
  if (bw > 0) candidates.push(innerW / bw);
  if (bh > 0) candidates.push(innerH / bh);
  let span = candidates.length ? frame.width / Math.min(...candidates) : null;
  if (minSpan !== null) {
    requirePositive(minSpan, "minSpan");
    span = span === null ? minSpan : Math.max(span, minSpan);
  }
  if (span === null) {
    throw new RangeError("map-view: zero-extent bounds need an explicit minSpan");
  }
  const centre = { x: (bounds.minX + bounds.maxX) / 2, y: (bounds.minY + bounds.maxY) / 2 };
  return centreOn({ cx: centre.x, cy: centre.y, span }, frame, centre, area);
}

/**
 * The rectangle a map's floating content may use: the frame minus a margin,
 * the host-measured insets, and a right-hand reservation (an open detail
 * panel). The host owns the panel's width; this function only subtracts it.
 * A rectangle squeezed below zero collapses to its midpoint.
 */
export function insetRect(frame, {
  marginPx = DEFAULT_MARGIN_PX,
  insets = null,
  reservedRight = 0,
} = {}) {
  requireFrame(frame);
  requireFinite(marginPx, "marginPx");
  requireFinite(reservedRight, "reservedRight");
  const inset = { top: 0, right: 0, bottom: 0, left: 0, ...(insets ?? {}) };
  for (const key of ["top", "right", "bottom", "left"]) requireFinite(inset[key], `insets.${key}`);
  let left = marginPx + inset.left;
  let right = frame.width - marginPx - inset.right - reservedRight;
  let top = marginPx + inset.top;
  let bottom = frame.height - marginPx - inset.bottom;
  if (right < left) left = right = (left + right) / 2;
  if (bottom < top) top = bottom = (top + bottom) / 2;
  return FREEZE({ left, top, right, bottom });
}

/**
 * Places a pixel point inside rect. Inside (edges included) it is unchanged;
 * outside, the ray from the rect centre towards it is cut at the first edge it
 * crosses. `angle` is the screen bearing in degrees (0 = right, 90 = down).
 */
export function clampToRect(rect, point) {
  requireRect(rect);
  requirePoint(point, "point");
  const centre = rectCentre(rect);
  const dx = point.x - centre.x;
  const dy = point.y - centre.y;
  const angle = dx === 0 && dy === 0 ? 0 : (Math.atan2(dy, dx) * 180) / Math.PI;
  const inside = point.x >= rect.left && point.x <= rect.right && point.y >= rect.top && point.y <= rect.bottom;
  if (inside) {
    return FREEZE({ x: point.x, y: point.y, inside: true, side: null, angle });
  }
  // A collapsed axis (zero width or height) cannot stop the ray; the other
  // axis decides, and a fully collapsed rect falls back to a plain clamp.
  const wide = rect.right > rect.left;
  const tall = rect.bottom > rect.top;
  const tx = wide && dx !== 0 ? ((dx > 0 ? rect.right : rect.left) - centre.x) / dx : Infinity;
  const ty = tall && dy !== 0 ? ((dy > 0 ? rect.bottom : rect.top) - centre.y) / dy : Infinity;
  const t = Math.min(tx, ty);
  const horizontal = Number.isFinite(t) ? tx <= ty : Math.abs(dx) >= Math.abs(dy);
  const side = horizontal ? (dx > 0 ? "right" : "left") : dy > 0 ? "bottom" : "top";
  const reach = Number.isFinite(t) ? { x: centre.x + dx * t, y: centre.y + dy * t } : point;
  return FREEZE({
    x: Math.min(rect.right, Math.max(rect.left, reach.x)),
    y: Math.min(rect.bottom, Math.max(rect.top, reach.y)),
    inside: false,
    side,
    angle,
  });
}
