// The exit compass's pure model (exploration-exit-compass design D1; scene
// overview redesign §3.1 and §3.5). The prototype
// `docs/design/scene-overview-redesign/compass-model.js` is the reference;
// this module reads the committed shapes instead of mock data:
//
// - the exit rows are `ExplorationMenu.moveItems` output (the same rows, and
//   therefore the same `explore.move` payloads, the retired 出口 chips used);
// - the map is the committed `view.localMapModel` (`LocalMap.reducePanel`).
//
// Each exit resolves to exactly one angled or portal target. The bearing is
// the minimap's own `LocalMap.remoteDirection` formula, so the compass and the
// minimap's remote-direction markers can never disagree.
import ExplorationMenu from "../lib/exploration_menu.js";
import LocalMap from "../lib/local_map.js";
import { disabledRowReason, exitLabel } from "./dock-exits.js";

export const SNAP_TOLERANCE = 30; // degrees either side of the aim
export const DEAD_ZONE = 0.2; // fraction of the pad radius
export const HOLD_MS = 400; // press length that starts continuous movement
export const STEP_DWELL_MS = 350; // minimum dwell in each room while continuing

// The server's own "map not synchronised" wording (`moveItems`), used only
// for a row the server enabled but the client cannot submit because no
// current node is committed.
export const MAP_UNSYNCED_REASON = "地圖資料尚未同步。";

// The canonical direction tokens (`ExplorationMenu.normalizeDirection`) and
// their fixed angles; up and down are vertical portals, never angled.
const WORD_ANGLES = Object.freeze({
  north: 0,
  northeast: 45,
  east: 90,
  southeast: 135,
  south: 180,
  southwest: 225,
  west: 270,
  northwest: 315,
});
const GEO_LAYERS = new Set(["grid", "wilderness"]);
const OCTANT_GLYPHS = ["↑", "↗", "→", "↘", "↓", "↙", "←", "↖"];
const PORTAL_GLYPHS = Object.freeze({ up: "⇧", down: "⇩" });

export function normalizeAngle(deg) {
  return ((deg % 360) + 360) % 360;
}

export function angleDelta(a, b) {
  const d = Math.abs(normalizeAngle(a) - normalizeAngle(b));
  return d > 180 ? 360 - d : d;
}

export function octantIndex(angle) {
  return Math.floor(normalizeAngle(angle) / 45 + 0.5) % 8;
}

export function octantGlyph(angle) {
  return OCTANT_GLYPHS[octantIndex(angle)];
}

export function portalGlyph(vertical) {
  return PORTAL_GLYPHS[vertical] || "✦";
}

function hasCoordinates(node) {
  return !!node && Number.isFinite(node.x) && Number.isFinite(node.y);
}

function mapNodes(localMapModel) {
  if (!localMapModel) {
    return [];
  }
  const nodes = Array.isArray(localMapModel.nodes) ? localMapModel.nodes : [];
  const remembered = Array.isArray(localMapModel.remembered) ? localMapModel.remembered : [];
  return [...nodes, ...remembered];
}

function findNode(nodes, id) {
  if (id === null || id === undefined) {
    return null;
  }
  return nodes.find((node) => node && String(node.id) === String(id)) || null;
}

// Rule 1 (map bearing): a geographic layer, the destination on the committed
// map, both nodes with coordinates, and the coordinates different.
function mapBearing(item, localMapModel, nodes) {
  if (!localMapModel || !GEO_LAYERS.has(localMapModel.layer)) {
    return null;
  }
  const current = findNode(nodes, localMapModel.currentNode);
  const destination = findNode(nodes, item.destination);
  if (!hasCoordinates(current) || !hasCoordinates(destination)) {
    return null;
  }
  if (current.x === destination.x && current.y === destination.y) {
    return null;
  }
  return LocalMap.remoteDirection(current, destination).theta;
}

// The reason a disabled target shows: the row's server-authored reason, or,
// for a row disabled only because no current node is committed (`moveItems`
// leaves such a row without a description), the server's own "map not
// synchronised" wording. A row the server disabled without a reason while a
// current node exists stays reason-less: nothing is invented.
function targetReason(item, mapSynced) {
  if (item.enabled !== false) {
    return null;
  }
  const reason = disabledRowReason(item);
  if (reason) {
    return reason;
  }
  return mapSynced ? null : MAP_UNSYNCED_REASON;
}

function exitRefOf(item) {
  if (item.payload && item.payload.exit_ref !== undefined) {
    return String(item.payload.exit_ref);
  }
  const key = String(item.key || "");
  return key.startsWith("exit-") ? key.slice("exit-".length) : key;
}

// Resolve every exit row, in payload order, to exactly one target.
// `options.currentNode` is the canonical current node the rows were built
// with (the exploration resolver's own value); null means no map is synced.
export function resolveTargets(rows, localMapModel, options = {}) {
  const mapSynced = options.currentNode !== null && options.currentNode !== undefined && options.currentNode !== "";
  const nodes = mapNodes(localMapModel);
  const angled = [];
  const portals = [];
  (Array.isArray(rows) ? rows : []).forEach((item, order) => {
    if (!item) {
      return;
    }
    const destinationNode = findNode(nodes, item.destination);
    const base = {
      key: item.key,
      exitRef: exitRefOf(item),
      item,
      order,
      destination: item.destination ?? null,
      destinationOnMap: !!destinationNode,
      label: exitLabel(item, localMapModel),
      enabled: item.enabled !== false,
      reason: targetReason(item, mapSynced),
    };
    const token = ExplorationMenu.normalizeDirection(item.label);
    const bearing = mapBearing(item, localMapModel, nodes);
    if (bearing !== null) {
      angled.push({ ...base, kind: "angled", angle: bearing, source: "map", vertical: null, glyph: octantGlyph(bearing) });
    } else if (token && token in WORD_ANGLES) {
      const angle = WORD_ANGLES[token];
      angled.push({ ...base, kind: "angled", angle, source: "word", vertical: null, glyph: octantGlyph(angle) });
    } else {
      const vertical = token === "up" || token === "down" ? token : null;
      portals.push({ ...base, kind: "portal", source: "portal", vertical, glyph: portalGlyph(vertical) });
    }
  });
  // Stable ascending order; equal angles keep payload order.
  angled.sort((a, b) => a.angle - b.angle || a.order - b.order);
  assignPortalSlots(portals);
  return { angled, portals, cycle: [...angled, ...portals] };
}

// Up is pinned to 0° and down to 180°; the other portals, in payload order,
// take the free slot of a 12-slot (30°) ring nearest their ideal position
// round((i + 0.5) · 12 / n), the clockwise slot winning a tie. More than ten
// non-vertical portals switch the ring to 24 slots (15°).
export function assignPortalSlots(portals) {
  const others = portals.filter((portal) => !portal.vertical);
  const count = others.length > 10 ? 24 : 12;
  const step = 360 / count;
  const taken = new Set();
  for (const portal of portals) {
    if (portal.vertical === "up") {
      portal.slot = 0;
      taken.add(0);
    } else if (portal.vertical === "down") {
      portal.slot = 180;
      taken.add(180);
    }
  }
  others.forEach((portal, i) => {
    const ideal = Math.round(((i + 0.5) * count) / others.length) % count;
    portal.slot = ideal * step;
    for (let off = 0; off < count; off += 1) {
      const cw = ((ideal + off) % count) * step;
      const ccw = ((ideal - off + count) % count) * step;
      const free = !taken.has(cw) ? cw : !taken.has(ccw) ? ccw : null;
      if (free !== null) {
        portal.slot = free;
        break;
      }
    }
    // A ring with no free slot left (more portals than slots) keeps the
    // ideal slot: beads overlap rather than vanish.
    taken.add(portal.slot);
  });
  portals.sort((a, b) => a.slot - b.slot || a.order - b.order);
  return portals;
}

// Snap an aim to the nearest angled exit within the tolerance; a tie goes to
// the smaller clockwise angle (the list is ascending and only a strictly
// smaller delta replaces the best).
export function snapAngled(angled, aim, tolerance = SNAP_TOLERANCE) {
  if (aim === null || aim === undefined) {
    return null;
  }
  let best = null;
  let bestDelta = Infinity;
  for (const target of angled || []) {
    const d = angleDelta(target.angle, aim);
    if (d <= tolerance && d < bestDelta) {
      best = target;
      bestDelta = d;
    }
  }
  return best;
}

// On the outer track the aim snaps to the nearest portal, whatever the angle.
export function snapPortal(portals, aim) {
  if (aim === null || aim === undefined) {
    return null;
  }
  let best = null;
  let bestDelta = Infinity;
  for (const portal of portals || []) {
    const d = angleDelta(portal.slot, aim);
    if (d < bestDelta) {
      best = portal;
      bestDelta = d;
    }
  }
  return best;
}

export const NO_AIM = Object.freeze({ angle: null, target: null, zone: "none" });

// Pointer -> aim. `r` is the distance from the centre as a fraction of the pad
// radius; `ringStart` is where the portal track begins (same unit).
export function aimFromPointer(targets, r, angle, ringStart) {
  if (r < DEAD_ZONE) {
    return { angle: null, target: null, zone: "dead" };
  }
  if (r >= ringStart && targets.portals.length > 0) {
    return { angle, target: snapPortal(targets.portals, angle), zone: "ring" };
  }
  return { angle, target: snapAngled(targets.angled, angle), zone: "pad" };
}

// Held arrow keys -> an eight-way aim angle, or null when they cancel out.
export function aimFromKeys(keys) {
  const dx = (keys.has("ArrowRight") ? 1 : 0) - (keys.has("ArrowLeft") ? 1 : 0);
  const dy = (keys.has("ArrowUp") ? 1 : 0) - (keys.has("ArrowDown") ? 1 : 0);
  if (dx === 0 && dy === 0) {
    return null;
  }
  return normalizeAngle((Math.atan2(dx, dy) * 180) / Math.PI);
}

// The `[` / `]` cycle: angled exits by ascending angle, then portals by
// ascending slot, wrapping. `current` is the aimed target (matched by key, so
// a re-resolved room still finds its place) or null.
export function cycleTarget(targets, current, step) {
  const list = targets.cycle;
  if (list.length === 0) {
    return null;
  }
  const index = current ? list.findIndex((target) => target.key === current.key) : -1;
  if (index === -1) {
    return step > 0 ? list[0] : list[list.length - 1];
  }
  return list[(index + step + list.length) % list.length];
}

// The aim a cycled (or otherwise chosen) target implies.
export function aimForTarget(target) {
  if (!target) {
    return NO_AIM;
  }
  return target.kind === "angled"
    ? { angle: target.angle, target, zone: "pad" }
    : { angle: target.slot, target, zone: "ring" };
}

// Re-resolve an aim against a new room's targets (an arrival commit): a pad
// aim re-snaps its angle to the angled exits, a ring aim to the portals.
export function resnapAim(targets, aim) {
  if (!aim || aim.angle === null || aim.angle === undefined) {
    return aim && aim.zone === "dead" ? aim : NO_AIM;
  }
  if (aim.zone === "ring") {
    return { ...aim, target: snapPortal(targets.portals, aim.angle) };
  }
  return { ...aim, zone: "pad", target: snapAngled(targets.angled, aim.angle) };
}

// The continuous-movement step on arrival: re-snap the held aim to the new
// room's angled exits; stop when nothing is in tolerance or the exit is
// disabled. Portals never chain.
export function nextStep(targets, aim) {
  if (aim === null || aim === undefined) {
    return { stop: "no-aim", target: null };
  }
  const target = snapAngled(targets.angled, aim);
  if (!target) {
    return { stop: "no-exit", target: null };
  }
  if (!target.enabled) {
    return { stop: "disabled", target };
  }
  return { stop: null, target };
}
