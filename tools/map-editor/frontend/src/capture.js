// Offline capture entry. A local-file page that draws one authoring view
// from a structured, in-memory payload through the shared map surface.
//
// The runner opens `capture-dist/index.html` from disk and calls
//
//   await window.renderMapCapture({ world, partition, view, map_id, width,
//                                   height, bounds, hidden_layers })
//
// `world` is the existing projection (interiors and terrain preview
// included), `partition` is null or { outlines } in scene metres, `view` is
// continent/settlement/interior, `map_id` is null only for the continent,
// `bounds` is null or [minX, minY, maxX, maxY] in the CLI's own frame, and
// `hidden_layers` names the layers to leave out.
//
// The promise resolves with { bounds, units, axes } only after the font
// faces, the terrain raster and the laid-out paint are complete; it rejects
// with the underlying error and leaves the same error on
// `window.__mapCaptureState`, so a partial render is never reported as ready.
//
// Nothing here fetches, opens a socket or reads a service: every asset is a
// file next to this page and every coordinate arrives in the payload.
import "@game/tokens.css";
import "@game/fonts.css";
import "@game/fonts-mono.css";
import "./styles/editor.css";
import "./styles/capture.css";

import { createApp, nextTick, reactive } from "vue";
import { unproject } from "@elosern/map-view";
import CaptureApp from "./components/CaptureApp.vue";
import {
  CAPTURE_VIEWS,
  boxOfView,
  captureAxes,
  captureScene,
  captureUnits,
  convergeFit,
  expandToAspect,
  fitView,
  frameBoundsOf,
  normalizedHidden,
  sceneExtent,
  sceneFrameBounds,
  unionBox,
  viewOfBox,
} from "./lib/capture.js";
import { sceneFor } from "./lib/map_scene.js";

const state = reactive({ scene: null, view: null, frame: null, label: "" });
// The mounted instance is the only way to reach the surface the host renders:
// the entry measures and waits on exactly the component it is looking at.
const host = createApp(CaptureApp, { state }).mount("#map-capture");

// `renderMapCapture` callers read this instead of guessing from the DOM.
const report = { status: "idle", error: null, bounds: null, units: null, axes: null };
window.__mapCaptureState = report;

function positive(value, name) {
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    throw new RangeError(`capture: ${name} must be a positive finite number`);
  }
  return value;
}

function readRequest(payload) {
  if (!payload || typeof payload !== "object") throw new TypeError("capture: payload must be an object");
  const { world, view } = payload;
  if (!world || typeof world !== "object") throw new TypeError("capture: payload.world is required");
  if (!CAPTURE_VIEWS.includes(view)) throw new RangeError(`capture: view must be one of ${CAPTURE_VIEWS.join(", ")}`);
  const mapId = payload.map_id ?? null;
  if (view === "continent" && mapId !== null) throw new TypeError("capture: the continent takes no map_id");
  if (view !== "continent" && typeof mapId !== "string") throw new TypeError(`capture: ${view} needs a string map_id`);
  const hidden = payload.hidden_layers ?? [];
  if (!Array.isArray(hidden) || hidden.some((name) => typeof name !== "string")) {
    throw new TypeError("capture: hidden_layers must be an array of layer names");
  }
  return {
    world,
    partition: payload.partition ?? null,
    view,
    mapId,
    frame: { width: positive(payload.width, "width"), height: positive(payload.height, "height") },
    bounds: payload.bounds ?? null,
    hidden: normalizedHidden(view, hidden),
  };
}

function nextPaint() {
  return new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
}

// Show one camera and wait until it is fully painted and measurable.
async function show({ scene, view, frame, label }) {
  state.scene = scene;
  state.view = view;
  state.frame = frame;
  state.label = label;
  await nextTick();
  await host.surface.ready();
  await nextPaint();
}

// The scene bounds the painted content actually occupies: strokes and font
// ink included, because the browser measured them. The dot-field background
// is excluded — it is the image, not the content.
function paintedBox(view, frame) {
  const svg = host.surface.element;
  if (!svg) return null;
  const rect = svg.getBoundingClientRect();
  if (!(rect.width > 0) || !(rect.height > 0)) return null;
  const kx = frame.width / rect.width;
  const ky = frame.height / rect.height;
  let box = null;
  for (const node of svg.querySelectorAll("path, rect, circle, text, image, line, polyline, polygon")) {
    if (node.hasAttribute("data-background") || node.closest("defs")) continue;
    const painted = node.getBoundingClientRect();
    if (!painted.width && !painted.height) continue;
    const left = (painted.left - rect.left) * kx;
    const top = (painted.top - rect.top) * ky;
    const corner = unproject(view, frame, { x: left, y: top });
    const opposite = unproject(view, frame, {
      x: left + painted.width * kx,
      y: top + painted.height * ky,
    });
    box = unionBox(box, { minX: corner.x, minY: opposite.y, maxX: opposite.x, maxY: corner.y });
  }
  return box;
}

// Full-map fit: the unfiltered reference geometry, then bounded convergence
// on what is really painted (pixel-sized cards, glyphs and measured labels
// grow the extent as the scale shrinks). Hiding layers never enters here, so
// the camera cannot move when the caller hides something.
async function fitCamera({ scene, frame, view, label }) {
  const extent = sceneExtent(scene) ?? scene.bounds;
  if (!extent) throw new Error("capture: the scene has no reference geometry to fit");
  const { bounds } = await convergeFit(extent, async (candidate) => {
    const camera = fitView(candidate, frame);
    await show({ scene, view: camera, frame, label });
    return paintedBox(camera, frame);
  });
  return fitView(bounds, frame);
}

window.renderMapCapture = async (payload) => {
  report.status = "rendering";
  report.error = null;
  report.bounds = null;
  report.units = null;
  report.axes = null;
  try {
    const request = readRequest(payload);
    const { view, frame, bounds } = request;
    const scene = sceneFor(request.world, view, request.mapId, [], { partition: request.partition });
    if (!scene) throw new Error(`capture: no ${view} map ${request.mapId ?? ""} in the payload`.trim());
    const camera = bounds
      ? viewOfBox(expandToAspect(sceneFrameBounds(view, bounds), frame.width, frame.height), frame)
      : await fitCamera({ scene, frame, view, label: view });
    await show({
      scene: captureScene(scene, view, request.hidden),
      view: camera,
      frame,
      label: view,
    });
    const result = {
      bounds: frameBoundsOf(view, boxOfView(camera, frame)),
      units: captureUnits(view),
      axes: captureAxes(view),
    };
    report.bounds = result.bounds;
    report.units = result.units;
    report.axes = result.axes;
    report.status = "ready";
    return result;
  } catch (error) {
    report.status = "error";
    report.error = String(error?.message ?? error);
    throw error;
  }
};
