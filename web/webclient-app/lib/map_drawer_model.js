// The map drawer's pure readings (OpenSpec change redesign-map-drawer;
// design §6.2/§6.5): the commission list each tab mirrors as text and the
// off-screen pointer targets. Every line comes from the validated
// `area_map` / `world_map` body or from arithmetic on its coordinates; no
// route, place or precision is ever invented. No Vue, no DOM.

import { formatDistance, project } from "@elosern/map-view";
import { areaUnit, compassWord, isRadialLayer, placeNodes } from "./area_map_view.js";
import { farPointAlongBearing } from "./map_edge_pointers.js";

/** A rounded distance for reading: 10 m, then 0.1 km, then whole km. */
export function roughDistance(metres) {
  if (!(metres >= 0)) return "";
  let rounded;
  if (metres < 1000) rounded = Math.max(10, Math.round(metres / 10) * 10);
  else if (metres < 100000) rounded = Math.round(metres / 100) * 100;
  else rounded = Math.round(metres / 10000) * 10000;
  return formatDistance(rounded);
}

function bearingWord(bearingDeg) {
  const rad = (bearingDeg * Math.PI) / 180;
  return compassWord(Math.sin(rad), Math.cos(rad));
}

function byTracked(rows) {
  return rows
    .map((row, index) => ({ row, index }))
    .sort((a, b) => Number(b.row.tracked) - Number(a.row.tracked) || a.index - b.index)
    .map((entry) => entry.row);
}

function currentEntry(area, placed) {
  return placed.find((entry) => entry.node.id === area.current_node) ?? null;
}

/**
 * The area tab's commission rows: `{ id, title, tracked, kind, nodeId, sub,
 * metres }` where kind is `node` (a drawn node), `fog` (a node identity the
 * player has not uncovered) or `bearing` (a destination elsewhere).
 */
export function areaQuestRows(area) {
  if (!area || area.available !== true) return [];
  const placed = placeNodes(area);
  const byId = new Map(placed.map((entry) => [entry.node.id, entry]));
  const unit = areaUnit(area);
  const here = currentEntry(area, placed);
  const rows = area.quest_markers.map((marker) => {
    const base = { id: marker.id, title: marker.title, tracked: marker.tracked === true, nodeId: null, metres: null };
    const destination = marker.destination;
    if (destination.kind === "node") {
      const entry = byId.get(destination.node_id);
      if (!entry) return { ...base, kind: "fog", sub: "在此區域 · 尚未探明" };
      if (entry.node.id === area.current_node) return { ...base, kind: "node", nodeId: entry.node.id, metres: 0, sub: `${entry.node.label} · 就在這裡` };
      if (unit && here) {
        const dx = entry.x - here.x;
        const dy = entry.y - here.y;
        const metres = Math.hypot(dx, dy) * unit.metres;
        return { ...base, kind: "node", nodeId: entry.node.id, metres, sub: `${entry.node.label} · ${compassWord(dx, dy)}方 ${roughDistance(metres)}` };
      }
      return { ...base, kind: "node", nodeId: entry.node.id, sub: entry.node.label };
    }
    const metres = destination.distance_km * 1000;
    return {
      ...base,
      kind: "bearing",
      metres,
      bearing: destination.bearing_deg,
      sub: `區域外 · ${bearingWord(destination.bearing_deg)}方 ${roughDistance(metres)}`,
    };
  });
  return byTracked(rows);
}

/** The world tab's commission rows: `{ id, title, tracked, approximate, sub, km }`. */
export function worldQuestRows(world) {
  if (!world || world.available !== true) return [];
  const here = world.current;
  const rows = world.quest_markers.map((marker) => {
    const dx = marker.x - here.x;
    const dy = marker.y - here.y;
    const km = Math.hypot(dx, dy);
    const where = km < 0.5 ? "就在附近" : `${compassWord(dx, dy)}方 ${roughDistance(km * 1000)}`;
    return {
      id: marker.id,
      title: marker.title,
      tracked: marker.tracked === true,
      approximate: marker.approximate === true,
      km,
      sub: marker.approximate ? `大致方位 · ${where}` : where,
    };
  });
  return byTracked(rows);
}

/**
 * Pointer targets for the area tab in frame pixels. Radial (coordinate-free)
 * layers have no north, so a bearing would mislead: they list commissions
 * as text only. A fogged destination has no position and stays list-only.
 */
export function areaPointerTargets(area, view, frame) {
  if (!area || area.available !== true || !view || !frame || isRadialLayer(area)) return [];
  const placed = placeNodes(area);
  const here = currentEntry(area, placed);
  if (!here) return [];
  const rows = areaQuestRows(area);
  const byId = new Map(placed.map((entry) => [entry.node.id, entry]));
  const targets = [];
  for (const row of rows) {
    if (row.kind === "node" && row.metres > 0) {
      const p = project(view, frame, byId.get(row.nodeId));
      targets.push({ id: row.id, title: row.title, sub: row.sub, distance: row.metres, x: p.x, y: p.y });
    } else if (row.kind === "bearing") {
      const far = farPointAlongBearing(here, row.bearing, view.span * 20);
      const p = project(view, frame, far);
      targets.push({ id: row.id, title: row.title, sub: row.sub, distance: row.metres, x: p.x, y: p.y });
    }
  }
  return targets;
}

/** Pointer targets for the world tab in frame pixels (precision as supplied). */
export function worldPointerTargets(world, view, frame) {
  if (!world || world.available !== true || !view || !frame) return [];
  const rows = new Map(worldQuestRows(world).map((row) => [row.id, row]));
  return world.quest_markers.map((marker) => {
    const row = rows.get(marker.id);
    const p = project(view, frame, marker);
    return { id: marker.id, title: marker.title, sub: row.sub, distance: row.km, x: p.x, y: p.y };
  });
}
