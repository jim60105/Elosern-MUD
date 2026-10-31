// Area map host policy and reading model for AreaMapView (OpenSpec change
// render-area-map-view; approved design
// docs/superpowers/specs/2026-10-22-world-map-drawer-design.md §6.2-§6.5).
// Dependency-light ES module: no Vue, no DOM (text measurement is injected).
//
// The neutral geometry (projection, fit, cells, bounds, stops, dot lattice,
// label collision, units) belongs to `@elosern/map-view`. What stays here is
// this game's map: which layers exist, the server's fog and current node, the
// quest markers, the travel descriptors and the Traditional Chinese reading.
//
// Input is a validated `area_map` v2 body (protocol/panels/map_panels.js
// validateAreaMapPanel). Nothing here invents a node, an edge, a coordinate
// or a travel action: every drawn fact comes from the payload. The wilderness
// window's run-length rows decode into ephemeral display cells
// (`decodeWindow`); sight, eligibility, routes and the clock stay the
// server's, so nothing here derives them.
//
// Units per layer
//   grid        map units are the payload's integer metres (UNITS.m)
//   wilderness  map units are cells: payload cell-centre kilometres divided
//               by `cell_km`, so a cell spans [n, n+1) as the shared
//               cellRect and this game's wildernessStops expect; captions
//               convert with
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
  UNITS,
  boundsCentredOn,
  boundsOfPoints,
  cellUnit,
  centreOn,
  createStop,
  dotField,
  fitBounds,
  formatDistance,
  orderedStops,
  spanLimits,
} from "@elosern/map-view";
import { MIN_NEARBY_SPAN_M, settlementStops, wildernessStops } from "./map_stops.js";

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

function currentPlaced(area, placed) {
  return placed.find((entry) => entry.node.id === area.current_node);
}

// Bounds centred on the current node that reach every adjacent node.
function nearbyBounds(area, placed) {
  const here = currentPlaced(area, placed);
  const adjacent = adjacentIds(area);
  return boundsCentredOn(here, placed.filter((entry) => adjacent.has(entry.node.id)));
}

// Bounds centred on `here` that reach every placed node.
function centredBounds(here, placed) {
  return boundsCentredOn(here, placed);
}

// ── zoom stops and the opening view ─────────────────────────────────────

/** The layer's named zoom stops for this frame, widest first. */
export function areaStops(area, placed, frame) {
  if (area.layer === "grid") {
    return settlementStops(boundsOfPoints(placed), nearbyBounds(area, placed), frame, { marginPx: OPENING_MARGIN_PX });
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
  // A near stop not clearly narrower than the whole view collapses into it.
  return orderedStops([createStop("whole", "全圖", whole), createStop("nearby", "近處", near)]);
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
  if (area.layer === "wilderness") {
    // The revealed neighbourhood is the point of the wilderness view: open
    // on the 周邊 stop rather than the eight-neighbour close-up.
    floor = stops.find((stop) => stop.key === "surroundings")?.span ?? nearest;
  }
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

/** The cell-unit bounds of the wilderness window. */
export function windowBounds(area) {
  const { min_x: x, min_y: y, width, height } = area.window;
  return { minX: x, minY: y, maxX: x + width, maxY: y + height };
}

/** The whole known area at one uniform scale (the full window in the wilderness). */
export function wholeView(area, placed, frame, rect = null) {
  const stops = areaStops(area, placed, frame);
  const bounds = area.layer === "wilderness" ? windowBounds(area) : boundsOfPoints(placed);
  const fitted = fitBounds(
    bounds,
    frame,
    { rect, marginPx: OPENING_MARGIN_PX, minSpan: stops[stops.length - 1].span },
  );
  return Object.freeze({ signature: viewSignature(area), cx: fitted.cx, cy: fitted.cy, span: fitted.span });
}

// ── the scale-true dot field and caption ────────────────────────────────

/**
 * The shared dot lattice for this area with the legend caption that states
 * its step in the scale bar's own units. Null for a coordinate-free layer,
 * which states no distance.
 */
export function areaDotField(area, view, frame, minGapPx = DOT_MIN_GAP_PX) {
  const unit = areaUnit(area);
  const field = dotField(view, frame, unit, minGapPx, area.layer === "wilderness" ? unit.metres : 0);
  if (!field) return null;
  return Object.freeze({ ...field, caption: `格距 ${formatDistance(field.stepMetres)}` });
}

// ── reading model ───────────────────────────────────────────────────────

const OCTANTS = ["北", "東北", "東", "東南", "南", "西南", "西", "西北"];

/** Compass word for a north-up map vector (dx east, dy north). */
export function compassWord(dx, dy) {
  const bearing = ((Math.atan2(dx, dy) * 180) / Math.PI + 360) % 360;
  return OCTANTS[Math.round(bearing / 45) % 8];
}

const STATE_TEXT = { current: "你在這裡", visited: "到過", seen: "看過，尚未到訪" };

/** Traditional Chinese names of the wire terrain classes. */
export const TERRAIN_NAMES = Object.freeze({
  open_ground: "曠野",
  hills: "丘陵",
  mountain: "山地",
  woodland: "林地",
  water: "河川",
  ridge: "山脊",
  sea: "海域",
  settlement: "聚落",
});

/** Traditional Chinese names of the light phases. */
export const LIGHT_PHASE_NAMES = Object.freeze({ day: "白晝", dusk: "黃昏", night: "夜晚", dawn: "黎明" });

/** The sixteen sighting compass words, north first and clockwise. */
export const SIGHTING_BEARINGS = Object.freeze([
  "北", "北北東", "東北", "東北東", "東", "東南東", "東南", "南南東",
  "南", "南南西", "西南", "西南西", "西", "西北西", "西北", "北北西",
]);

// ── the wilderness window ───────────────────────────────────────────────

const windowCache = new WeakMap();

/**
 * The revealed cells of a wilderness window as ephemeral display cells, in
 * row order: `{ key, x, y, terrain, passable, band, tier, road, ford, state }`
 * with cell-unit `x`/`y` (the cell spans [x, x+1)). Unknown runs yield no
 * cell. `state` is "current", "visited" (the cell carries a visited node:
 * the server's actual visit record) or "remembered" (revealed without a
 * visit). Empty for other layers.
 */
export function decodeWindow(area) {
  if (area?.layer !== "wilderness" || !area.window) return Object.freeze([]);
  const cached = windowCache.get(area);
  if (cached) return cached;
  const visited = new Set();
  let current = null;
  for (const node of area.nodes) {
    if (!node.id.startsWith("wild:")) continue;
    const key = `${Math.floor(node.x / area.cell_km)}:${Math.floor(node.y / area.cell_km)}`;
    if (node.id === area.current_node) current = key;
    else if (node.visited) visited.add(key);
  }
  const cells = [];
  area.rows.forEach((runs, row) => {
    let column = 0;
    for (const run of runs) {
      if (run.kind === "terrain") {
        for (let offset = 0; offset < run.length; offset += 1) {
          const x = area.window.min_x + column + offset;
          const y = area.window.min_y + row;
          const key = `${x}:${y}`;
          cells.push(
            Object.freeze({
              key,
              x,
              y,
              terrain: run.terrain,
              passable: run.passable,
              band: run.band,
              tier: run.tier,
              road: run.road,
              ford: run.ford,
              state: key === current ? "current" : visited.has(key) ? "visited" : "remembered",
            }),
          );
        }
      }
      column += run.length;
    }
  });
  const out = Object.freeze(cells);
  windowCache.set(area, out);
  return out;
}

/** The display cell under one placed node, or null. */
export function cellUnder(area, entry) {
  const key = `${Math.floor(entry.x)}:${Math.floor(entry.y)}`;
  return decodeWindow(area).find((cell) => cell.key === key) ?? null;
}

/** Live-sight entities at their cell centres, in payload order. */
export function entityMarks(area) {
  if (area?.layer !== "wilderness") return [];
  return area.entities.map((entity) => ({
    id: entity.id,
    x: entity.cell.x + 0.5,
    y: entity.cell.y + 0.5,
    kind: entity.kind,
    hostile: entity.hostile,
    label: entity.label,
  }));
}

/**
 * Distant sightings with the screen bearing of their compass word: `angle`
 * is radians clockwise from north (the word's sector centre). The text is
 * the server's: bearing word, rounded distance, silhouette and an optional
 * district landmark name.
 */
export function sightingMarks(area) {
  if (area?.layer !== "wilderness") return [];
  return area.sightings.map((sighting, index) => {
    const sector = SIGHTING_BEARINGS.indexOf(sighting.bearing);
    return {
      key: `${index}:${sighting.bearing}`,
      angle: (sector * 22.5 * Math.PI) / 180,
      bearing: sighting.bearing,
      head: `${sighting.bearing} · 約 ${sighting.distance_km} km`,
      body: sighting.name ? `${sighting.silhouette_zh}（${sighting.name}）` : sighting.silhouette_zh,
    };
  });
}

/** The legend line for the window's light and sight: e.g. `白晝 · 視野 4 格`. */
export function sightCaption(area) {
  if (area?.layer !== "wilderness") return "";
  return `${LIGHT_PHASE_NAMES[area.light_phase] ?? area.light_phase} · 視野 ${area.ground_radius} 格`;
}

/** The terrain reading of one display cell. */
export function terrainLine(cell) {
  const parts = [TERRAIN_NAMES[cell.terrain] ?? cell.terrain];
  if (cell.ford) parts.push("淺灘");
  parts.push(`海拔第 ${cell.band} 階`);
  if (!cell.passable) parts.push("無法通行");
  return `地形：${parts.join(" · ")}`;
}

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
  if (area.layer === "wilderness") {
    const cell = node.id.startsWith("wild:") ? cellUnder(area, entry) : null;
    if (cell) lines.push(terrainLine(cell));
    if (node.id === area.current_node) {
      lines.push(`所在分區：${area.district_name}`);
      lines.push(sightCaption(area));
    }
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
  let entries = placed.map((entry) => ({
    ...entry,
    id: entry.node.id,
    priority: priority(entry.node),
    lines: labelLines(entry.node),
  }));
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
