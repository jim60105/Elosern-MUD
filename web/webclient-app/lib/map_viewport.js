// Pure metric viewport for the map drawer (OpenSpec change
// establish-map-viewport; approved design
// docs/superpowers/specs/2026-10-22-world-map-drawer-design.md §6.2-§6.4).
// Dependency-free ES module: no Vue, no DOM. Every function returns a new
// frozen plain object and never mutates its inputs.
//
// Consumers: AreaMapView (settlement grids in metres, wilderness cells) and
// WorldMapView (continent in kilometres). The old overlay math in
// lib/map_view.js keeps serving MapOverlay until redesign-map-drawer migrates
// every caller and deletes it; this module does not re-export it.
//
// Types
//   view  { cx, cy, span }        centre in map units, span = map units across
//                                 the full measured frame width
//   frame { width, height }       measured CSS pixels of the map surface
//   rect  { left, top, right, bottom }   CSS pixels inside the frame
//   bounds { minX, minY, maxX, maxY }    map units
//   unit  { key, metres }         metres per map unit
//   stop  { key, label, span }    a named zoom stop (map units across width)
//
// Canonical frames are +x east and +y north. Projection uses one uniform
// scale k = frame.width / view.span for both axes and inverts only the north
// axis for the screen, so canonical coordinates are never rewritten and
// unequal metric gaps stay unequal (no row/column rank compression).
//
// Units: the world map is in kilometres (UNITS.km), settlement grids are in
// metres (UNITS.m), and the wilderness area view counts cells whose size comes
// from the provider panel's scale (cellUnit(cellMetres)). Fit, recentre,
// stops and pan all operate in the current scope's units; only scaleBar and
// formatDistance convert to metres for captions.
//
// Coordinate-free layers (instances and interiors) carry no room coordinates
// and stay on the separate radial renderer: metricPoints/isMetricLayer never
// fabricate a position.
//
// Edge clamping: the host measures its own chrome and passes it in through
// usableRect (the open ~360 px detail drawer plus floating-control insets);
// this module never queries the DOM.
//
// Invalid programmer input (non-finite numbers, non-positive frame or span)
// throws TypeError/RangeError instead of leaking NaN into view state. A host
// whose ResizeObserver reports a 0x0 frame on first paint skips the call.
// `null` is reserved for "no data" answers (no metric points, no further
// stop).
//
// Visual evidence: this slice adds no component. The real AreaMapView,
// WorldMapView and MapDrawer stories in the consuming changes exercise this
// module and carry the Storybook/agent-browser evidence.

// ── constants ───────────────────────────────────────────────────────────

/** Detail drawer width the edge pointers avoid when something is selected. */
export const DETAIL_DRAWER_WIDTH = 360;
/** Default pixel margin kept between map content/pointers and the frame. */
export const DEFAULT_MARGIN_PX = 24;
/** Fixed world stop spans in kilometres (design §6.3). */
export const WORLD_COUNTRY_SPAN_KM = 800;
export const WORLD_DISTRICT_SPAN_KM = 200;
export const WORLD_NEARBY_SPAN_KM = 40;
/** Wilderness surroundings stop: the provider's 15 x 15 cell window. */
export const WILDERNESS_WINDOW_CELLS = 15;
/** Wilderness nearby stop: the eight neighbours plus one ring of context. */
export const WILDERNESS_NEARBY_CELLS = 5;
/** Floor for the settlement nearby stop so a lone node never zooms forever. */
export const MIN_NEARBY_SPAN_M = 400;
/** Continuous wheel zoom may go this far past the narrowest/widest stop. */
export const ZOOM_IN_SLACK = 0.5;
export const ZOOM_OUT_SLACK = 1.25;
/** Plus/minus treat spans within these ratios as "already at that stop". */
export const STOP_STEP_TOLERANCE = 0.05;
/** Wheel zoom: span multiplier per wheel deltaY unit. */
export const WHEEL_ZOOM_BASE = 1.0018;
/** Stops whose spans differ by less than this ratio collapse into one. */
const STOP_DEDUPE_RATIO = 1.01;

// ── validation ──────────────────────────────────────────────────────────

function finite(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function requireFinite(value, name) {
  if (!finite(value)) {
    throw new TypeError(`map_viewport: ${name} must be a finite number`);
  }
  return value;
}

function requirePositive(value, name) {
  requireFinite(value, name);
  if (value <= 0) {
    throw new RangeError(`map_viewport: ${name} must be positive`);
  }
  return value;
}

function requireFrame(frame) {
  if (!frame) throw new TypeError("map_viewport: frame is required");
  requirePositive(frame.width, "frame.width");
  requirePositive(frame.height, "frame.height");
  return frame;
}

function requireView(view) {
  if (!view) throw new TypeError("map_viewport: view is required");
  requireFinite(view.cx, "view.cx");
  requireFinite(view.cy, "view.cy");
  requirePositive(view.span, "view.span");
  return view;
}

function requirePoint(point, name) {
  if (!point) throw new TypeError(`map_viewport: ${name} is required`);
  requireFinite(point.x, `${name}.x`);
  requireFinite(point.y, `${name}.y`);
  return point;
}

function requireBounds(bounds) {
  if (!bounds) throw new TypeError("map_viewport: bounds is required");
  for (const key of ["minX", "minY", "maxX", "maxY"]) requireFinite(bounds[key], `bounds.${key}`);
  if (bounds.maxX < bounds.minX || bounds.maxY < bounds.minY) {
    throw new RangeError("map_viewport: bounds max must not be below min");
  }
  return bounds;
}

function requireRect(rect) {
  if (!rect) throw new TypeError("map_viewport: rect is required");
  for (const key of ["left", "top", "right", "bottom"]) requireFinite(rect[key], `rect.${key}`);
  if (rect.right < rect.left || rect.bottom < rect.top) {
    throw new RangeError("map_viewport: rect right/bottom must not be below left/top");
  }
  return rect;
}

const freeze = Object.freeze;

/** Builds a validated, frozen view. */
export function createView(cx, cy, span) {
  return freeze(requireView({ cx, cy, span }));
}

// ── units and captions ──────────────────────────────────────────────────

export const UNITS = freeze({
  m: freeze({ key: "m", metres: 1 }),
  km: freeze({ key: "km", metres: 1000 }),
});

/** Wilderness cell unit from the provider panel's metres-per-cell scale. */
export function cellUnit(cellMetres) {
  return freeze({ key: "cell", metres: requirePositive(cellMetres, "cellMetres") });
}

export function toMetres(value, unit) {
  return requireFinite(value, "value") * requirePositive(unit?.metres, "unit.metres");
}

/** `850 m`, `1.5 km`, `40 km`. */
export function formatDistance(metres) {
  // Round first so a value just under a unit switch shows as the next unit.
  const rounded = Number(requireFinite(metres, "metres").toFixed(1));
  if (Math.abs(rounded) >= 1000) {
    return `${Number((rounded / 1000).toFixed(3))} km`;
  }
  return `${rounded} m`;
}

/**
 * Scale bar for a caption: the largest 1/2/5 x 10^n metre length whose
 * on-screen length is at most maxPx at the view's uniform scale.
 */
export function scaleBar(view, frame, unit, maxPx = 120) {
  requirePositive(maxPx, "maxPx");
  const metresPerPx = toMetres(1, unit) / scaleOf(view, frame);
  const budget = metresPerPx * maxPx;
  let metres = 10 ** Math.floor(Math.log10(budget));
  for (const step of [5, 2]) {
    if (metres * step <= budget * (1 + 1e-9)) {
      metres *= step;
      break;
    }
  }
  return freeze({ metres, px: metres / metresPerPx, text: formatDistance(metres) });
}

// ── projection ──────────────────────────────────────────────────────────

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
  return freeze({
    x: frame.width / 2 + (point.x - view.cx) * k,
    y: frame.height / 2 - (point.y - view.cy) * k,
  });
}

/** Frame pixel -> map point; the exact inverse of project. */
export function unproject(view, frame, pixel) {
  const k = scaleOf(view, frame);
  requirePoint(pixel, "pixel");
  return freeze({
    x: view.cx + (pixel.x - frame.width / 2) / k,
    y: view.cy - (pixel.y - frame.height / 2) / k,
  });
}

/** The frame pixel rectangle covered by one wilderness cell (col,row)-(col+1,row+1). */
export function cellRect(view, frame, col, row) {
  const sw = project(view, frame, { x: col, y: row });
  const ne = project(view, frame, { x: col + 1, y: row + 1 });
  return freeze({ left: sw.x, top: ne.y, right: ne.x, bottom: sw.y });
}

/** A cell's representative centre in cell units; markers use this convention. */
export function cellCentre(col, row) {
  return freeze({ x: requireFinite(col, "col") + 0.5, y: requireFinite(row, "row") + 0.5 });
}

// ── pan and zoom ────────────────────────────────────────────────────────

/** Drag pan: the content follows the pointer by (dxPx, dyPx). */
export function panByPixels(view, frame, dxPx, dyPx) {
  const k = scaleOf(view, frame);
  requireFinite(dxPx, "dxPx");
  requireFinite(dyPx, "dyPx");
  return freeze({ cx: view.cx - dxPx / k, cy: view.cy + dyPx / k, span: view.span });
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
  return freeze({
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
  return freeze({
    cx: point.x - (target.x - frame.width / 2) / k,
    cy: point.y + (target.y - frame.height / 2) / k,
    span: view.span,
  });
}

// ── fit ─────────────────────────────────────────────────────────────────

function rectCentre(rect) {
  return { x: (rect.left + rect.right) / 2, y: (rect.top + rect.bottom) / 2 };
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
    throw new RangeError("map_viewport: fit area is empty after margins");
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
    throw new RangeError("map_viewport: zero-extent bounds need an explicit minSpan");
  }
  const centre = { x: (bounds.minX + bounds.maxX) / 2, y: (bounds.minY + bounds.maxY) / 2 };
  return centreOn({ cx: centre.x, cy: centre.y, span }, frame, centre, area);
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
  return freeze({ minX, minY, maxX, maxY });
}

function hasMetricPosition(node) {
  return !!node && finite(node.x) && finite(node.y);
}

/** Only the nodes that already carry finite x and y; nothing is fabricated. */
export function metricPoints(nodes) {
  return freeze((Array.isArray(nodes) ? nodes : []).filter(hasMetricPosition));
}

/** True when a layer can use metric projection (non-empty, every node placed). */
export function isMetricLayer(nodes) {
  return Array.isArray(nodes) && nodes.length > 0 && nodes.every(hasMetricPosition);
}

// ── zoom stops ──────────────────────────────────────────────────────────

function stop(key, label, span) {
  return freeze({ key, label, span: requirePositive(span, `${key} span`) });
}

// Widest first; a stop not clearly narrower than the one before collapses
// into it so plus/minus never land on a no-op step.
function orderedStops(list) {
  const out = [];
  for (const entry of list) {
    const last = out[out.length - 1];
    if (!last || last.span / entry.span >= STOP_DEDUPE_RATIO) out.push(entry);
  }
  return freeze(out);
}

/**
 * World stops in km: 大陸 fits the actual continent bounds for this frame's
 * aspect ratio (never narrower than 國), then 國 800, 地區 200, 近郊 40.
 */
export function worldStops(continentBounds, frame, { marginPx = DEFAULT_MARGIN_PX } = {}) {
  const continent = fitBounds(continentBounds, frame, { marginPx }).span;
  return orderedStops([
    stop("continent", "大陸", Math.max(continent, WORLD_COUNTRY_SPAN_KM)),
    stop("country", "國", WORLD_COUNTRY_SPAN_KM),
    stop("district", "地區", WORLD_DISTRICT_SPAN_KM),
    stop("nearby", "近郊", WORLD_NEARBY_SPAN_KM),
  ]);
}

/**
 * Settlement stops in metres, derived from known geometry: 全城 fits every
 * known node, 近處 fits the current node and its adjacent nodes (floored at
 * minNearbySpan, capped at 全城), and 街區 is their geometric mean.
 */
export function settlementStops(wholeBounds, nearbyBounds, frame, {
  marginPx = DEFAULT_MARGIN_PX,
  minNearbySpan = MIN_NEARBY_SPAN_M,
} = {}) {
  const whole = fitBounds(wholeBounds, frame, { marginPx, minSpan: minNearbySpan }).span;
  const nearby = Math.min(whole, fitBounds(nearbyBounds, frame, { marginPx, minSpan: minNearbySpan }).span);
  return orderedStops([
    stop("whole", "全城", whole),
    stop("district", "街區", Math.sqrt(whole * nearby)),
    stop("nearby", "近處", nearby),
  ]);
}

function cellWindow(cells) {
  const half = cells / 2;
  return { minX: -half, minY: -half, maxX: half, maxY: half };
}

/** Wilderness stops in cell units: 周邊 (the 15-cell window) and 近處. */
export function wildernessStops(frame, { marginPx = DEFAULT_MARGIN_PX } = {}) {
  return orderedStops([
    stop("surroundings", "周邊", fitBounds(cellWindow(WILDERNESS_WINDOW_CELLS), frame, { marginPx }).span),
    stop("nearby", "近處", fitBounds(cellWindow(WILDERNESS_NEARBY_CELLS), frame, { marginPx }).span),
  ]);
}

function requireStops(stops) {
  if (!Array.isArray(stops) || !stops.length) {
    throw new TypeError("map_viewport: stops must be a non-empty array");
  }
  return stops;
}

/** Continuous-zoom limits derived from the scope's stops. */
export function spanLimits(stops) {
  requireStops(stops);
  const spans = stops.map((s) => s.span);
  return freeze({ min: Math.min(...spans) * ZOOM_IN_SLACK, max: Math.max(...spans) * ZOOM_OUT_SLACK });
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

// ── drawer-aware edge clamping ──────────────────────────────────────────

/**
 * The rectangle edge pointers and the pill may use: the frame minus a margin,
 * the host-measured floating-control insets, and the open detail drawer on the
 * right. A rectangle squeezed below zero collapses to its midpoint.
 */
export function usableRect(frame, {
  drawerOpen = false,
  drawerWidth = DETAIL_DRAWER_WIDTH,
  marginPx = DEFAULT_MARGIN_PX,
  insets = null,
} = {}) {
  requireFrame(frame);
  requireFinite(marginPx, "marginPx");
  const inset = { top: 0, right: 0, bottom: 0, left: 0, ...(insets ?? {}) };
  for (const key of ["top", "right", "bottom", "left"]) requireFinite(inset[key], `insets.${key}`);
  const drawer = drawerOpen ? requireFinite(drawerWidth, "drawerWidth") : 0;
  let left = marginPx + inset.left;
  let right = frame.width - marginPx - inset.right - drawer;
  let top = marginPx + inset.top;
  let bottom = frame.height - marginPx - inset.bottom;
  if (right < left) left = right = (left + right) / 2;
  if (bottom < top) top = bottom = (top + bottom) / 2;
  return freeze({ left, top, right, bottom });
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
    return freeze({ x: point.x, y: point.y, inside: true, side: null, angle });
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
  return freeze({
    x: Math.min(rect.right, Math.max(rect.left, reach.x)),
    y: Math.min(rect.bottom, Math.max(rect.top, reach.y)),
    inside: false,
    side,
    angle,
  });
}
