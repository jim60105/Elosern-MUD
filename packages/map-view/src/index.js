// @elosern/map-view — the one host-neutral source of map view primitives.
//
// A host (the game's area/world maps today, the standalone editor later)
// supplies explicit values and its own policy:
//   - view/frame/point/rect/bounds values and the unit its coordinates use;
//   - its own zoom-stop table (spans and labels), detail-panel width and
//     control insets;
//   - a glyph input per node and a theme of painted roles;
//   - every game concern itself: player knowledge/fog, the current player,
//     quest pointers, travel action descriptors, selection and OOB traffic.
//
// Nothing here imports a store, a protocol module, host shell CSS or the DOM.

export { createView } from "./values.js";
export { project, scaleOf, unproject } from "./projection.js";
export {
  DEFAULT_MARGIN_PX,
  DRAG_THRESHOLD_PX,
  WHEEL_ZOOM_BASE,
  centreOn,
  clampToRect,
  fitBounds,
  insetRect,
  panByPixels,
  rectCentre,
  wheelFactor,
  zoomAt,
  zoomBy,
} from "./navigation.js";
export { UNITS, cellUnit, formatDistance, scaleBar, toMetres } from "./units.js";
export { cellCentre, cellOf, cellRect } from "./cells.js";
export { boundsCentredOn, boundsOfPoints, isMetricLayer, metricBounds, metricPoints } from "./bounds.js";
export {
  STOP_STEP_TOLERANCE,
  ZOOM_IN_SLACK,
  ZOOM_OUT_SLACK,
  createStop,
  nearestStop,
  nextStop,
  orderedStops,
  previousStop,
  spanLimits,
} from "./stops.js";
export { estimateTextWidth, placeLabels, rectsOverlap } from "./labels.js";
export { dotField, niceStepAtLeast } from "./lattice.js";
export {
  GATE_FOOTPRINT,
  GATE_HALF,
  GATE_STROKE,
  HALO_R,
  HERE_DOT_R,
  HERE_GLOW_R,
  HERE_RING_R,
  MARKER_LANDMARK_R,
  NODE_DOT_R,
  gatePath,
  glyphFootprint,
} from "./glyph.js";
export { DEFAULT_THEME, THEME_PREFIX, THEME_ROLES, resolveTheme, themeVars } from "./theme.js";
