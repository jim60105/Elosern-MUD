// Pure geometry and reading model for AreaMapView (OpenSpec change
// render-area-map-view; approved design
// docs/superpowers/specs/2026-10-22-world-map-drawer-design.md §6.2-§6.5).
// Dependency-light ES module: no Vue, no DOM (text measurement is injected).
//
// Input is a validated `area_map` v1 body (protocol/panels/map_panels.js
// validateAreaMapPanel). Nothing here invents a node, an edge, a coordinate
// or a travel action: every drawn fact comes from the payload.
//
// Units per layer
//   grid        map units are the payload's integer metres (UNITS.m)
//   wilderness  map units are cells: payload cell-centre kilometres divided
//               by `cell_km`, so a cell spans [n, n+1) like map_viewport's
//               cellRect/wildernessStops; captions convert with
//               cellUnit(cell_km * 1000)
//   instance /  coordinate-free rooms keep the minimap's radial placement
//   interior    (local_map.js layoutRadial); radial units carry no distance,
//               so no dot field, scale bar or distance text exists for them
//
// The view signature `${layer}|${frame.key}|${frame.unit}` scopes view and
// selection state: metre state is never reused for wilderness cells or
// radial rooms, and a new map clears both.

import LocalMap from "./local_map.js";
import {
  DEFAULT_MARGIN_PX,
  MIN_NEARBY_SPAN_M,
  UNITS,
  cellUnit,
  centreOn,
  fitBounds,
  formatDistance,
  nearestStop,
  project,
  scaleBar,
  scaleOf,
  settlementStops,
  spanLimits,
  wildernessStops,
} from "./map_viewport.js";

export { formatDistance, scaleBar, spanLimits, nearestStop };

/** Minimum on-screen gap between scale-true dots (CSS px at ui-scale 1). */
export const DOT_MIN_GAP_PX = 30;
/** Pixel margin the opening fit keeps so the nearest labels stay inside. */
export const OPENING_MARGIN_PX = 72;
/** Radial units the coordinate-free views never zoom tighter than. */
export const RADIAL_MIN_SPAN = 360;
/** Label size floor (design §6.3): 16 CSS px at ui-scale 1, never smaller. */
export const LABEL_FONT_PX = 16;

const RADIAL_LAYERS = new Set(["instance", "interior"]);

export function isRadialLayer(area) {
  return RADIAL_LAYERS.has(area?.layer);
}

export function viewSignature(area) {
  return `${area.layer}|${area.frame.key}|${area.frame.unit}`;
}

/** The metres-per-map-unit of the layer, or null for radial room graphs. */
export function areaUnit(area) {
  if (area.layer === "grid") return UNITS.m;
  if (area.layer === "wilderness") return cellUnit(area.cell_km * 1000);
  return null;
}

// ── placement ───────────────────────────────────────────────────────────

/**
 * Every payload node placed in map units: `{ node, x, y }` in payload order.
 * Metric layers read the payload coordinates (wilderness divided into cell
 * units); radial layers take the shared deterministic radial placement,
 * converted to a north-up frame centred on the current room.
 */
export function placeNodes(area) {
  if (area.layer === "grid") {
    return area.nodes.map((node) => ({ node, x: node.x, y: node.y }));
  }
  if (area.layer === "wilderness") {
    return area.nodes.map((node) => ({ node, x: node.x / area.cell_km, y: node.y / area.cell_km }));
  }
  const radial = LocalMap.layoutRadial(area.nodes, area.edges);
  const byId = new Map(radial.nodes.map((placed) => [String(placed.id), placed]));
  const centre = radial.width / 2;
  return area.nodes.map((node) => {
    const placed = byId.get(String(node.id));
    return { node, x: placed.x - centre, y: centre - placed.y };
  });
}

/** The wilderness cell (col, row) a cell-unit position falls in. */
export function cellOf(placed) {
  return { col: Math.floor(placed.x), row: Math.floor(placed.y) };
}

/** Ids of the nodes one edge away from the current node. */
export function adjacentIds(area) {
  const out = new Set();
  for (const edge of area.edges) {
    if (edge.source === area.current_node) out.add(edge.destination);
    if (edge.destination === area.current_node) out.add(edge.source);
  }
  out.delete(area.current_node);
  return out;
}

/**
 * The node's travel descriptor, only when the server attached a move to a
 * node one road from the current node that leads to that very node.
 */
export function travelAction(area, node, adjacent = adjacentIds(area)) {
  const action = node?.action;
  if (!action || action.kind !== "move") return null;
  if (node.id === area.current_node || !adjacent.has(node.id)) return null;
  if (action.destination !== node.id) return null;
  return action;
}

function boundsOf(points) {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const { x, y } of points) {
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
  }
  return { minX, minY, maxX, maxY };
}

function currentPlaced(area, placed) {
  return placed.find((entry) => entry.node.id === area.current_node);
}

// Bounds centred on the current node that reach every adjacent node.
function nearbyBounds(area, placed) {
  const here = currentPlaced(area, placed);
  const adjacent = adjacentIds(area);
  let rx = 0;
  let ry = 0;
  for (const entry of placed) {
    if (!adjacent.has(entry.node.id)) continue;
    rx = Math.max(rx, Math.abs(entry.x - here.x));
    ry = Math.max(ry, Math.abs(entry.y - here.y));
  }
  return { minX: here.x - rx, minY: here.y - ry, maxX: here.x + rx, maxY: here.y + ry };
}

// Bounds centred on `here` that reach every placed node.
function centredBounds(here, placed) {
  let rx = 0;
  let ry = 0;
  for (const entry of placed) {
    rx = Math.max(rx, Math.abs(entry.x - here.x));
    ry = Math.max(ry, Math.abs(entry.y - here.y));
  }
  return { minX: here.x - rx, minY: here.y - ry, maxX: here.x + rx, maxY: here.y + ry };
}

// ── zoom stops and the opening view ─────────────────────────────────────

/** The layer's named zoom stops for this frame, widest first. */
export function areaStops(area, placed, frame) {
  if (area.layer === "grid") {
    return settlementStops(boundsOf(placed), nearbyBounds(area, placed), frame, { marginPx: OPENING_MARGIN_PX });
  }
  if (area.layer === "wilderness") {
    return wildernessStops(frame);
  }
  // The widest radial stop is the graph seen from the current room, so the
  // centred opening never needs to exceed the zoom limits.
  const here = currentPlaced(area, placed);
  const whole = fitBounds(centredBounds(here, placed), frame, { marginPx: OPENING_MARGIN_PX, minSpan: RADIAL_MIN_SPAN }).span;
  const near = Math.min(
    whole,
    fitBounds(nearbyBounds(area, placed), frame, { marginPx: OPENING_MARGIN_PX, minSpan: RADIAL_MIN_SPAN }).span,
  );
  const stops = [Object.freeze({ key: "whole", label: "全圖", span: whole })];
  // A near stop not clearly narrower than the whole view collapses into it,
  // as map_viewport's own stop lists do.
  if (whole / near >= 1.01) stops.push(Object.freeze({ key: "nearby", label: "近處", span: near }));
  return Object.freeze(stops);
}

/**
 * The opening view (design §6.4): centred on the current node at the zoom
 * that fits its adjacent nodes, never tighter than the layer's nearby stop
 * and never outside the continuous-zoom limits.
 */
export function openingView(area, placed, frame, stops = areaStops(area, placed, frame)) {
  const here = currentPlaced(area, placed);
  const nearest = stops[stops.length - 1].span;
  let floor = area.layer === "grid" ? Math.min(nearest, MIN_NEARBY_SPAN_M) : nearest;
  if (isRadialLayer(area)) {
    // Radial units carry no distance, so zooming in past the room graph buys
    // no detail: the opening still centres on the current room and fits its
    // neighbours, but widens until every room of the small graph is in view
    // rather than leaving roads running off the frame.
    floor = Math.max(floor, fitBounds(centredBounds(here, placed), frame, { marginPx: OPENING_MARGIN_PX }).span);
  }
  const fitted = fitBounds(nearbyBounds(area, placed), frame, { marginPx: OPENING_MARGIN_PX, minSpan: floor });
  const limits = spanLimits(stops);
  const span = Math.min(limits.max, Math.max(limits.min, fitted.span));
  const view = centreOn({ cx: here.x, cy: here.y, span }, frame, here);
  return Object.freeze({ signature: viewSignature(area), cx: view.cx, cy: view.cy, span: view.span });
}

/** The whole known area at one uniform scale. */
export function wholeView(area, placed, frame, rect = null) {
  const stops = areaStops(area, placed, frame);
  const bounds = area.layer === "wilderness" ? boundsOf(placed.map((p) => ({ x: p.x, y: p.y }))) : boundsOf(placed);
  const pad = area.layer === "wilderness" ? 0.5 : 0;
  const fitted = fitBounds(
    { minX: bounds.minX - pad, minY: bounds.minY - pad, maxX: bounds.maxX + pad, maxY: bounds.maxY + pad },
    frame,
    { rect, marginPx: OPENING_MARGIN_PX, minSpan: stops[stops.length - 1].span },
  );
  return Object.freeze({ signature: viewSignature(area), cx: fitted.cx, cy: fitted.cy, span: fitted.span });
}

// ── the scale-true dot field and caption ────────────────────────────────

function niceAtLeast(value) {
  const power = 10 ** Math.floor(Math.log10(value));
  for (const step of [1, 2, 5, 10]) {
    if (step * power >= value * (1 - 1e-9)) return step * power;
  }
  return 10 * power;
}

/**
 * The dot lattice for a metric view: dots sit on every integer world
 * multiple of a round 1/2/5 x 10^n metre step, chosen as the smallest step
 * whose on-screen gap is at least `minGapPx` (and, for wilderness cells, at
 * least one cell, so the dots mark cell corners instead of halving a cell). `spacingPx` is that step at the
 * view's uniform scale, `offsetX/offsetY` the lattice phase in [0, spacing),
 * and the caption states the step with the scale bar's own formatter.
 */
export function dotField(view, frame, unit, minGapPx = DOT_MIN_GAP_PX, minStepMetres = 0) {
  if (!unit) return null;
  const k = scaleOf(view, frame);
  const metresPerPx = unit.metres / k;
  const stepMetres = niceAtLeast(Math.max(minGapPx * metresPerPx, minStepMetres));
  const stepUnits = stepMetres / unit.metres;
  const spacingPx = stepUnits * k;
  const origin = project(view, frame, { x: 0, y: 0 });
  const phase = (value) => ((value % spacingPx) + spacingPx) % spacingPx;
  return Object.freeze({
    stepMetres,
    stepUnits,
    spacingPx,
    offsetX: phase(origin.x),
    offsetY: phase(origin.y),
    caption: `格距 ${formatDistance(stepMetres)}`,
  });
}

// ── reading model ───────────────────────────────────────────────────────

const OCTANTS = ["北", "東北", "東", "東南", "南", "西南", "西", "西北"];

/** Compass word for a north-up map vector (dx east, dy north). */
export function compassWord(dx, dy) {
  const bearing = ((Math.atan2(dx, dy) * 180) / Math.PI + 360) % 360;
  return OCTANTS[Math.round(bearing / 45) % 8];
}

const STATE_TEXT = { current: "你在這裡", visited: "到過", seen: "看過，尚未到訪" };

export function leadsToOf(node) {
  const value = node?.gateway?.leads_to;
  return typeof value === "string" ? value : "";
}

function kindOf(area, node) {
  const gate = leadsToOf(node) !== "";
  if (area.layer === "grid") return gate ? "城門" : "街區";
  if (area.layer === "wilderness") return gate ? "城門" : "荒野";
  return gate ? "出入口" : "房間";
}

/** The visible label line(s) of a node: its full name and the gate's far side. */
export function labelLines(node) {
  const leadsTo = leadsToOf(node);
  if (!leadsTo) return [node.label];
  if (leadsTo === node.label) return [`通往 ${leadsTo}`];
  return [node.label, `通往 ${leadsTo}`];
}

/**
 * The selection reading: every line comes from the payload or from
 * arithmetic on its coordinates. Null for an id the payload does not hold,
 * so a fogged commission target can never be "selected" into view.
 */
export function nodeDetail(area, placed, nodeId) {
  const entry = placed.find((item) => item.node.id === nodeId);
  if (!entry) return null;
  const { node } = entry;
  const unit = areaUnit(area);
  const lines = [STATE_TEXT[node.visibility]];
  const leadsTo = leadsToOf(node);
  if (leadsTo) lines.push(`通往 ${leadsTo}`);
  if (unit && node.id !== area.current_node) {
    const here = currentPlaced(area, placed);
    const dx = entry.x - here.x;
    const dy = entry.y - here.y;
    const metres = Math.hypot(dx, dy) * unit.metres;
    const rounded = metres >= 1000 ? Math.round(metres / 100) * 100 : Math.max(10, Math.round(metres / 10) * 10);
    lines.push(`${compassWord(dx, dy)}方 · 直線約 ${formatDistance(rounded)}`);
  }
  if (area.layer === "wilderness" && node.id === area.current_node) {
    lines.push(`所在分區：${area.district_name}`);
  }
  const quests = area.quest_markers
    .filter((marker) => marker.destination.kind === "node" && marker.destination.node_id === node.id)
    .map((marker) => ({ id: marker.id, title: marker.title, tracked: marker.tracked }));
  return Object.freeze({
    id: node.id,
    kind: kindOf(area, node),
    title: node.label,
    visibility: node.visibility,
    lines,
    quests,
    move: travelAction(area, node),
  });
}

/** Accessible name of a node control: the full name, its gate and its state. */
export function nodeAccessibleName(area, node) {
  const parts = [node.label];
  const leadsTo = leadsToOf(node);
  if (leadsTo && leadsTo !== node.label) parts.push(`通往 ${leadsTo}`);
  else if (leadsTo) parts[0] = `通往 ${leadsTo}`;
  parts.push(STATE_TEXT[node.visibility]);
  if (travelAction(area, node)) parts.push("可前往");
  return parts.join("，");
}

// ── label priority and collision ────────────────────────────────────────

/**
 * Which nodes carry a drawn label, with their priority (lower draws first).
 * Wilderness cells repeat one region name, so only gate cells and cells
 * whose name differs from the current cell's (a town's approach) are named,
 * each distinct name once at the cell nearest the player.
 */
export function labelCandidates(area, placed, selectedId = null) {
  const adjacent = adjacentIds(area);
  const markerIds = new Set(
    area.quest_markers.filter((m) => m.destination.kind === "node").map((m) => m.destination.node_id),
  );
  const priority = (node) => {
    if (node.id === selectedId) return 0;
    if (node.id === area.current_node) return 1;
    if (travelAction(area, node, adjacent)) return 2;
    if (leadsToOf(node)) return 3;
    if (markerIds.has(node.id)) return 4;
    return node.visibility === "visited" ? 5 : 6;
  };
  let entries = placed.map((entry) => ({ ...entry, priority: priority(entry.node), lines: labelLines(entry.node) }));
  if (area.layer === "wilderness") {
    const here = currentPlaced(area, placed);
    const hereLabel = here.node.label;
    const nearest = new Map();
    for (const entry of entries) {
      if (entry.node.id === area.current_node) continue;
      const named = leadsToOf(entry.node) || entry.node.label !== hereLabel || entry.node.id === selectedId;
      if (!named) continue;
      const key = entry.lines.join("\n");
      const distance = Math.hypot(entry.x - here.x, entry.y - here.y);
      const previous = nearest.get(key);
      if (!previous || entry.node.id === selectedId || (previous.node.id !== selectedId && distance < previous.distance)) {
        nearest.set(key, { ...entry, distance });
      }
    }
    entries = [...nearest.values()];
  }
  return entries.sort((a, b) => a.priority - b.priority);
}

/** Rough width of a label at fontPx (CJK one em, Latin about 0.58 em). */
export function estimateTextWidth(text, fontPx) {
  let em = 0;
  for (const ch of text) {
    const code = ch.codePointAt(0);
    em += code > 0x2e80 ? 1 : ch === " " ? 0.3 : 0.58;
  }
  return em * fontPx;
}

function overlaps(a, b) {
  return a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
}

// Liang-Barsky: does the segment cross the box?
function segmentHitsBox(seg, box) {
  const dx = seg.x2 - seg.x1;
  const dy = seg.y2 - seg.y1;
  let t0 = 0;
  let t1 = 1;
  const clip = (p, q) => {
    if (p === 0) return q >= 0;
    const r = q / p;
    if (p < 0) {
      if (r > t1) return false;
      if (r > t0) t0 = r;
    } else {
      if (r < t0) return false;
      if (r < t1) t1 = r;
    }
    return true;
  };
  return (
    clip(-dx, seg.x1 - box.left) &&
    clip(dx, box.right - seg.x1) &&
    clip(-dy, seg.y1 - box.top) &&
    clip(dy, box.bottom - seg.y1) &&
    t0 <= t1
  );
}

/**
 * Greedy navigation-priority label placement in frame pixels. Each label
 * tries above its marker, then below, right, left and the four diagonals,
 * preferring a spot
 * clear of every drawn road (`segments`) before one that crosses a road;
 * a label that fits
 * nowhere clear of higher-priority labels and every marker is hidden, never
 * truncated or shrunk. The selected and current labels are always placed
 * (they may only be clamped inside the frame). Returns
 * `[{ id, lines, anchor, x, y, box }]` in placement order.
 */
export function placeLabels(candidates, project2d, frame, {
  fontPx = LABEL_FONT_PX,
  measure = estimateTextWidth,
  markerRadius = 12,
  obstacles = [],
  segments = [],
} = {}) {
  const lineHeight = Math.round(fontPx * 1.3);
  // A rendered line's glyph box spans about 1.19 em above the baseline and
  // 0.31 em below it (CJK faces), so boxes match what the browser paints.
  const ascent = Math.round(fontPx * 1.19);
  const glyphHeight = Math.round(fontPx * 1.5);
  const gap = Math.round(fontPx * 0.45);
  // Breathing room kept between two drawn labels.
  const spacing = Math.round(fontPx * 0.2);
  const padded = (box) => ({
    left: box.left - spacing,
    right: box.right + spacing,
    top: box.top - spacing,
    bottom: box.bottom + spacing,
  });
  const markers = obstacles.map((p) => ({
    left: p.x - markerRadius,
    right: p.x + markerRadius,
    top: p.y - markerRadius,
    bottom: p.y + markerRadius,
    id: p.id,
  }));
  const placedBoxes = [];
  const out = [];
  for (const entry of candidates) {
    const p = project2d(entry);
    const width = Math.max(...entry.lines.map((line) => measure(line, fontPx))) + 4;
    const height = (entry.lines.length - 1) * lineHeight + glyphHeight;
    const options = [
      { anchor: "middle", left: p.x - width / 2, top: p.y - markerRadius - gap - height },
      { anchor: "middle", left: p.x - width / 2, top: p.y + markerRadius + gap },
      { anchor: "start", left: p.x + markerRadius + gap, top: p.y - height / 2 },
      { anchor: "end", left: p.x - markerRadius - gap - width, top: p.y - height / 2 },
      { anchor: "start", left: p.x + markerRadius * 0.7, top: p.y - markerRadius * 0.7 - gap - height },
      { anchor: "end", left: p.x - markerRadius * 0.7 - width, top: p.y - markerRadius * 0.7 - gap - height },
      { anchor: "start", left: p.x + markerRadius * 0.7, top: p.y + markerRadius * 0.7 + gap },
      { anchor: "end", left: p.x - markerRadius * 0.7 - width, top: p.y + markerRadius * 0.7 + gap },
    ];
    const must = entry.priority <= 1;
    let chosen = null;
    // Passes: clear of roads, then across roads, then (for the selected and
    // current names only) across other markers, never across another label.
    const passes = must ? [[true, true], [false, true], [false, false]] : [[true, true], [false, true]];
    for (const [avoidRoads, avoidMarkers] of passes) {
      for (const option of options) {
        const box = { left: option.left, top: option.top, right: option.left + width, bottom: option.top + height };
        const inside = box.left >= 0 && box.top >= 0 && box.right <= frame.width && box.bottom <= frame.height;
        if (!inside) continue;
        const blocked =
          placedBoxes.some((other) => overlaps(padded(box), other)) ||
          (avoidMarkers && markers.some((marker) => marker.id !== entry.node.id && overlaps(box, marker))) ||
          (avoidRoads && segments.some((seg) => segmentHitsBox(seg, box)));
        if (!blocked) {
          chosen = { ...option, box };
          break;
        }
      }
      if (chosen) break;
    }
    if (!chosen && must) {
      const option = options[0];
      const left = Math.min(Math.max(0, option.left), Math.max(0, frame.width - width));
      const top = Math.min(Math.max(0, option.top), Math.max(0, frame.height - height));
      chosen = { anchor: "middle", left, top, box: { left, top, right: left + width, bottom: top + height } };
    }
    if (!chosen) continue;
    placedBoxes.push(chosen.box);
    const x = chosen.anchor === "middle" ? chosen.left + width / 2 : chosen.anchor === "start" ? chosen.left : chosen.left + width;
    out.push({
      id: entry.node.id,
      lines: entry.lines,
      anchor: chosen.anchor,
      x,
      y: chosen.top + ascent,
      lineHeight,
      box: chosen.box,
      priority: entry.priority,
    });
  }
  return out;
}

export { DEFAULT_MARGIN_PX };
