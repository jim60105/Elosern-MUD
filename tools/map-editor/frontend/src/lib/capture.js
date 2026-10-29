// Offline capture presentation contract: coordinate frames, camera
// arithmetic and per-view layer ownership.
//
// Pure module: no DOM, no fetch, no store, no Vue. A capture host feeds it a
// scene built by `lib/map_scene.js` from an in-memory projection, a requested
// CLI-frame extent and a pixel frame, and gets a camera, the reported extent
// in the caller's frame and a layer-filtered scene back. Painted measurement
// is the host's job (fonts, cards and glyphs are pixel-sized), so the
// convergence driver takes a `paint` callback.
//
// Frames (the CLI's own coordinates, never the editor's):
//   continent   kilometres, +x east, +y north; the scene uses metres.
//   settlement  local metres, already the scene's frame.
//   interior    layout grid units, +x right, +y down; the scene negates y.
// Reports are returned in the frame they were requested in, so a caller never
// has to know which conversion happened inside.

import { fitBounds } from "@elosern/map-view";

/** The three authoring views an offline render can select. */
export const CAPTURE_VIEWS = Object.freeze(["continent", "settlement", "interior"]);

/** The layers each view can draw, defaults all visible. */
export const CAPTURE_LAYERS = Object.freeze({
  continent: Object.freeze(["terrain", "water", "ridge", "locations", "footprint", "partition", "labels"]),
  settlement: Object.freeze(["nodes", "roads", "labels"]),
  interior: Object.freeze(["rooms", "connections", "exterior", "labels"]),
});

/** The label layer name; hiding it removes text only. */
export const LABEL_LAYER = "labels";

/** Pointer margin kept between the fitted surface and the image edge. */
export const FIT_MARGIN_PX = 24;
/** Bounded layout convergence of the full-map fit. */
export const FIT_ITERATIONS = 8;
/** Relative growth below which the fitted extent counts as settled. */
export const FIT_TOLERANCE = 0.005;

const IDENTITY = ([minX, minY, maxX, maxY]) => ({ minX, minY, maxX, maxY });

const FRAMES = Object.freeze({
  continent: Object.freeze({
    units: "km",
    axes: Object.freeze({ x: "east", y: "north" }),
    toScene: ([minX, minY, maxX, maxY]) => ({ minX: minX * 1000, minY: minY * 1000, maxX: maxX * 1000, maxY: maxY * 1000 }),
    fromScene: ({ minX, minY, maxX, maxY }) => [minX / 1000, minY / 1000, maxX / 1000, maxY / 1000],
  }),
  settlement: Object.freeze({
    units: "m",
    axes: Object.freeze({ x: "east", y: "north" }),
    toScene: IDENTITY,
    fromScene: ({ minX, minY, maxX, maxY }) => [minX, minY, maxX, maxY],
  }),
  interior: Object.freeze({
    units: "layout",
    axes: Object.freeze({ x: "right", y: "down" }),
    // Down-positive layout units to north-positive scene units.
    toScene: ([minX, minY, maxX, maxY]) => ({ minX, minY: -maxY, maxX, maxY: -minY }),
    // Back out in the same reverse order, so a report is always
    // [minX, minY, maxX, maxY] in the requested frame.
    fromScene: ({ minX, minY, maxX, maxY }) => [minX, -maxY, maxX, -minY],
  }),
});

function frameOf(view) {
  const frame = FRAMES[view];
  if (!frame) throw new RangeError(`capture: unknown view ${JSON.stringify(view)}`);
  return frame;
}

/** The unit name reported for a view's bounds (kilometres, metres, layout). */
export function captureUnits(view) {
  return frameOf(view).units;
}

/** The axis meaning reported for a view; interiors are never geographic. */
export function captureAxes(view) {
  return frameOf(view).axes;
}

/** The layer names a view draws when nothing is hidden. */
export function captureLayers(view) {
  frameOf(view);
  return CAPTURE_LAYERS[view];
}

/**
 * A request frame array [minX, minY, maxX, maxY] in scene coordinates, or
 * null when absent. A malformed or inverted rectangle is a caller error, not
 * something to clamp.
 */
export function sceneFrameBounds(view, bounds) {
  const frame = frameOf(view);
  if (bounds === null || bounds === undefined) return null;
  if (!Array.isArray(bounds) || bounds.length !== 4) {
    throw new TypeError("capture: bounds must be [minX, minY, maxX, maxY]");
  }
  for (const value of bounds) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
      throw new TypeError("capture: bounds values must be finite numbers");
    }
  }
  const [minX, minY, maxX, maxY] = bounds;
  if (maxX < minX || maxY < minY) {
    throw new RangeError("capture: bounds max must not be below min");
  }
  return frame.toScene(bounds);
}

/** Scene bounds back in the requested frame's order. */
export function frameBoundsOf(view, bounds) {
  return frameOf(view).fromScene(bounds);
}

/** Grow bounds to the frame's aspect ratio around their own centre. */
export function expandToAspect(bounds, width, height) {
  const spanX = bounds.maxX - bounds.minX;
  const spanY = bounds.maxY - bounds.minY;
  const cx = (bounds.minX + bounds.maxX) / 2;
  const cy = (bounds.minY + bounds.maxY) / 2;
  const aspect = width / height;
  const targetX = Math.max(spanX, spanY * aspect);
  const targetY = targetX / aspect;
  return { minX: cx - targetX / 2, minY: cy - targetY / 2, maxX: cx + targetX / 2, maxY: cy + targetY / 2 };
}

/** The scene bounds a frame covers at a camera. */
export function boxOfView(view, frame) {
  const tall = (view.span * frame.height) / frame.width;
  return {
    minX: view.cx - view.span / 2,
    maxX: view.cx + view.span / 2,
    minY: view.cy - tall / 2,
    maxY: view.cy + tall / 2,
  };
}

/**
 * A camera covering exactly `bounds` at the frame's aspect ratio, with no
 * margin and no clamp: the image edge is the requested extent. A zero-size
 * request falls back to a single scene unit so the camera stays finite.
 */
export function viewOfBox(bounds, frame) {
  const aspect = frame.width / frame.height;
  const span = Math.max(bounds.maxX - bounds.minX, (bounds.maxY - bounds.minY) * aspect);
  return {
    cx: (bounds.minX + bounds.maxX) / 2,
    cy: (bounds.minY + bounds.maxY) / 2,
    span: span > 0 ? span : 1,
  };
}

/**
 * A camera fitting `bounds` inside the frame minus `marginPx`, uniformly on
 * both axes. A single-point extent has no scale of its own; one scene unit is
 * the fallback, never an output-size floor.
 */
export function fitView(bounds, frame, { marginPx = FIT_MARGIN_PX } = {}) {
  try {
    return fitBounds(bounds, frame, { marginPx });
  } catch {
    return fitBounds(bounds, frame, { marginPx, minSpan: 1 });
  }
}

/** Axis-aligned union of two bounds. */
export function unionBox(a, b) {
  if (!a) return b;
  if (!b) return a;
  return {
    minX: Math.min(a.minX, b.minX),
    minY: Math.min(a.minY, b.minY),
    maxX: Math.max(a.maxX, b.maxX),
    maxY: Math.max(a.maxY, b.maxY),
  };
}

/** True when `inner` lies inside `outer` within a relative tolerance. */
export function boxContains(outer, inner, tolerance = 0) {
  if (!outer || !inner) return false;
  const slackX = (outer.maxX - outer.minX) * tolerance;
  const slackY = (outer.maxY - outer.minY) * tolerance;
  return (
    inner.minX >= outer.minX - slackX &&
    inner.minY >= outer.minY - slackY &&
    inner.maxX <= outer.maxX + slackX &&
    inner.maxY <= outer.maxY + slackY
  );
}

/**
 * The reference geometry of a complete, unfiltered scene: every authored
 * point, every link vertex (road bends included), every mark anchor and the
 * terrain raster's corners. Glyph, card and label padding is pixel-sized and
 * therefore measured by the painting host, not guessed here.
 */
export function sceneExtent(scene) {
  let box = null;
  const add = (point) => {
    if (!Number.isFinite(point?.x) || !Number.isFinite(point?.y)) return;
    box = unionBox(box, { minX: point.x, minY: point.y, maxX: point.x, maxY: point.y });
  };
  for (const shape of scene?.shapes ?? []) for (const point of shape.points ?? []) add(point);
  for (const link of scene?.links ?? []) for (const point of link.points ?? []) add(point);
  for (const mark of scene?.marks ?? []) add(mark);
  if (scene?.raster) {
    add({ x: scene.raster.west, y: scene.raster.south });
    add({ x: scene.raster.east, y: scene.raster.north });
  }
  if (!box) return null;
  return box;
}

/**
 * Grow the camera's extent until the painted surface it produces is inside
 * it. `paint(bounds)` returns the scene bounds actually painted for a camera
 * fitted to `bounds`; growth is monotone so the loop cannot oscillate, and it
 * is bounded so a frame too small to hold pixel-sized cards and labels stops
 * instead of spinning. The result is the union, never a shrink.
 */
export async function convergeFit(initial, paint, { maxIterations = FIT_ITERATIONS, tolerance = FIT_TOLERANCE } = {}) {
  let bounds = initial;
  for (let iteration = 1; iteration <= maxIterations; iteration += 1) {
    const painted = await paint(bounds);
    const grown = unionBox(bounds, painted) ?? bounds;
    const settled = boxContains(grown, bounds, tolerance) && boxContains(bounds, grown, tolerance);
    bounds = grown;
    if (settled) return { bounds, iterations: iteration, converged: true };
  }
  return { bounds, iterations: maxIterations, converged: false };
}

/** The hidden layer names that exist for this view; unknown names are ignored. */
export function normalizedHidden(view, hiddenLayers = []) {
  const known = new Set(captureLayers(view));
  return (Array.isArray(hiddenLayers) ? hiddenLayers : []).filter((name) => known.has(name));
}

// Which geometry layer draws an item, per view. Continent drawables name
// their own layer at the scene boundary; every settlement node mark is
// `nodes` and every road link is `roads`; interior rooms, connections and the
// exterior card are three independent layers.
function layerReader(view) {
  if (view === "continent") return (item) => item.layer ?? null;
  if (view === "settlement") return (item, kind) => (kind === "link" ? "roads" : "nodes");
  if (view === "interior") {
    return (item, kind) => {
      if (kind === "link") return item.kind === "exterior" ? "exterior" : "connections";
      return item.kind === "exterior" ? "exterior" : "rooms";
    };
  }
  frameOf(view);
  return () => null;
}

/**
 * A scene with the named layers left out. Hiding a geometry layer removes
 * that layer's drawables and with them their labels; hiding `labels` removes
 * text only, so cards, glyphs and direction indicators stay. An all-hidden
 * scene keeps the scene's own background unit (the dot field) and nothing
 * else, so a host paints its normal background at the same camera.
 */
export function captureScene(scene, view, hiddenLayers = []) {
  if (!scene) return null;
  const off = new Set(normalizedHidden(view, hiddenLayers));
  const layerOf = layerReader(view);
  const labelsOff = off.has(LABEL_LAYER);
  const kept = (item, kind) => {
    const layer = layerOf(item, kind);
    return layer === null || !off.has(layer);
  };
  const visible = (item) => ({ ...item, showLabel: !labelsOff });
  return {
    ...scene,
    shapes: (scene.shapes ?? []).filter((shape) => kept(shape, "shape")).map(visible),
    links: (scene.links ?? []).filter((link) => kept(link, "link")).map(visible),
    marks: (scene.marks ?? []).filter((mark) => kept(mark, "mark")).map(visible),
    raster: scene.raster && kept(scene.raster, "raster") ? visible(scene.raster) : null,
  };
}
