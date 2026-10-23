// The minimap island's automatic metric projection (OpenSpec change
// compute-minimap-auto-scale-projection; approved design
// docs/superpowers/specs/2026-10-22-minimap-auto-scale-design.md §3–§5, §6.3).
// Pure: no Vue, no DOM, no allocation proportional to distance.
//
// API
// ---
// `projectIsland(model, previousLevel = null, options = {})` projects the
// browser local-map model's in-view `nodes` and `edges` (the reduced model of
// web/static/webclient/js/elosern/local_map.js; `col`/`row`/`cell` are
// ignored, so the overlay lattice is untouched) onto the 240-unit island
// square with the current node at its centre (`options.footprint` overrides
// the exit marker footprint used for overlap spreading). It returns
//
//   { mode, level, nodes, exitStubs, grid, scaleLabel }
//
// - `mode`: "uniform" or "compressed".
// - `level`: the chosen ladder level M (metres per 100 user units); the
//   caller feeds it back as `previousLevel` for hysteresis.
// - `nodes[]`: `{ id, x, y, tier, gateway }` in user units, current first,
//   then the same-map nodes in payload order. `tier` is "current", "exit" or
//   "context".
// - `exitStubs[]`: `{ bearing, label, action }` for each cross-map exit
//   target (a gate's far side), in payload order. `action` is the target
//   node's own nullable action object, passed by reference.
// - `grid`: uniform `{ kind: "dots", spacing, metres, offsetX, offsetY }`
//   (dots `spacing` units apart, one dot on every integer world multiple of
//   `metres`; `offsetX`/`offsetY` are that lattice's screen phase in
//   [0, spacing)), or compressed `{ kind: "rings", rings: [{ distance,
//   radius, label }] }`.
// - `scaleLabel`: the caption, `格距 <spacing>` or `距離壓縮`.
//
// The caller owns the previous level and resets it when the current node's
// map changes: `previousLevelFor(memory, currentId)` returns the remembered
// level only while `mapKeyOf(currentId)` is unchanged, and
// `rememberLevel(currentId, projection)` builds the next memory. Ordinary
// moves on one map therefore keep hysteresis.
//
// Numerical policies
// ------------------
// - Distances are metres. Grid coordinates are metres already; wilderness
//   coordinates are one-kilometre cell indices (the fixed coordinate frame of
//   world/maps/wilderness_provider.py), so wilderness deltas are multiplied by
//   WILDERNESS_CELL_METRES. This is a unit conversion, not a configurable
//   geography constant: the localized legend is never parsed and payload
//   coordinates are never rewritten.
// - Tiers: an exit is the other endpoint of an edge incident to the current
//   node whose label is a non-empty string, whatever its action (a locked
//   exit is still an exit). Star edges with an empty label only mark context.
// - Nodes whose map key differs from the current node's (a gate's cross-layer
//   target at its renderer-local slot) take part in no distance, scale or
//   placement. When they are exits they become exit stubs at their raw
//   bearing from the current node, labelled `通往 <leads_to>` from the
//   current gate's metadata (city side), else the target's (a wilderness
//   payload's adjacent city gate), else the target's own server-authored
//   label. A non-exit cross-map node yields nothing. The map key (`grid:<z>`,
//   `wild:<name>`) rather than the bare prefix decides this, because two
//   grid z-maps' coordinates are not comparable either. Remembered nodes are
//   skipped: they keep the existing edge-direction markers.
// - Scale candidates are the positive exit distances; with no exits, the
//   positive context distances. With no positive candidate the level is
//   DEFAULT_LEVEL in uniform mode.
// - The ideal level is the smallest ladder value M with d_max * 100 / M <=
//   R_MAX. With none, the projection is compressed at the coarsest level (so
//   the returned level stays a valid hysteresis input). When the nearest
//   candidate lands strictly inside R_MIN at the ideal level, it is
//   compressed at the ideal level. Otherwise it is uniform and the previous
//   level is kept when it is the ideal or one step coarser and still places
//   every candidate within [R_MIN, R_MAX].
// - Compressed radii: r(d) = R_MIN + (R_MAX - R_MIN) * ln(d/d_min) /
//   ln(d_max/d_min) for d >= d_min; r = R_MIN * d / d_min below d_min. When
//   every candidate shares one distance, it maps to EQUAL_RADIUS and other
//   distances scale linearly from that point (R_MIN * d / d_min below,
//   EQUAL_RADIUS * d / d_min above), which stays monotonic and finite.
// - Zero-distance exits have no bearing: the k of them take bearings
//   i * 360 / k in payload order, north first, at radius R_MIN, and never
//   enter a logarithm or a divisor. Zero-distance context sits at the centre.
// - Hysteresis narrows "fits every exit" to [R_MIN, R_MAX]: a retained
//   coarser level must not put the nearest exit inside R_MIN, which would
//   contradict the compression rule. Context-only inputs follow the same
//   policy, so context can select compression when there are no exits.
// - Overlap: positive-distance exits whose marker centres are closer than the footprint are
//   grouped (single link, around the circle) and each group of n is spread
//   symmetrically about its circular mean bearing at the separation that
//   clears the footprint at the group's smallest radius, capped so no member
//   moves more than MAX_SPREAD_DEG from the mean. Members keep their signed
//   order around the mean (a group straddling north stays in order); a group
//   whose bearings cancel out has no mean and is left as is. One bounded
//   pass: a very large coincident group may still touch within the cap, and a
//   spread member may approach an exit outside its group. Every other exit
//   keeps its exact bearing; radii never change.
// - Context outside the canvas square is omitted. Exits always lie within
//   R_MAX.
// - Rings use the readable distances 1 and 3 × 10^k metres, mapped by the
//   same radial function, with radius within [RING_MIN_RADIUS,
//   CANVAS_SIZE / 2]. Distances inside the candidate span are preferred, then
//   those nearest it; each ring clears every other by RING_MIN_GAP units, at
//   most MAX_RINGS of them, returned in ascending distance.
import LocalMap from "./local_map.js";

export const CANVAS_SIZE = 240;
export const CENTRE = CANVAS_SIZE / 2;
export const R_MIN = 36;
export const R_MAX = 88;
export const LEVELS = Object.freeze([
  10, 15, 20, 30, 50, 75, 100, 150, 200, 300, 500, 750, 1000, 1500, 2000, 3000, 5000,
]);
export const DEFAULT_LEVEL = 100;
export const EQUAL_RADIUS = 0.75 * R_MAX;
export const MAX_SPREAD_DEG = 20;
// One exit marker's footprint diameter: twice the actionable halo radius
// (HALO_R in composables/use-map-lattice-geometry.js), the largest exit mark.
export const EXIT_FOOTPRINT = 20;
// Uniform dots stand 20 units apart: one dot per M / 5 metres.
export const DOT_SPACING = 20;
// Wilderness cells are one kilometre (the provider's fixed coordinate frame).
export const WILDERNESS_CELL_METRES = 1000;
export const RING_MIN_RADIUS = 18;
export const RING_MIN_GAP = 16;
export const MAX_RINGS = 4;

const EPSILON = 1e-9;
const RING_MANTISSAS = [1, 3];
const RING_MAX_DISTANCE = 1e6;

export function mapKeyOf(id) {
  if (typeof id !== "string" || id === "") return null;
  const parts = id.split(":");
  if (parts[0] === "grid" || parts[0] === "wild") {
    return parts.length >= 2 ? `${parts[0]}:${parts[1]}` : null;
  }
  return parts[0];
}

export function previousLevelFor(memory, currentId) {
  if (!memory || memory.mapKey === null || memory.mapKey !== mapKeyOf(currentId)) return null;
  return LEVELS.includes(memory.level) ? memory.level : null;
}

export function rememberLevel(currentId, projection) {
  return { mapKey: mapKeyOf(currentId), level: projection ? projection.level : null };
}

export function formatDistance(metres) {
  return metres >= 1000 ? `${metres / 1000} km` : `${metres} m`;
}

function finitePoint(node) {
  return !!node && Number.isFinite(node.x) && Number.isFinite(node.y);
}

function normalizeDeg(angle) {
  return ((angle % 360) + 360) % 360;
}

function circularMean(bearings) {
  let sx = 0;
  let sy = 0;
  for (const bearing of bearings) {
    const rad = (bearing * Math.PI) / 180;
    sx += Math.sin(rad);
    sy += Math.cos(rad);
  }
  if (Math.hypot(sx, sy) < 1e-6 * bearings.length) return null;
  return normalizeDeg((Math.atan2(sx, sy) * 180) / Math.PI);
}

// Signed smallest difference a - b in (-180, 180].
function angleDelta(a, b) {
  const d = normalizeDeg(a - b);
  return d > 180 ? d - 360 : d;
}

function screen(radius, bearing) {
  const rad = (bearing * Math.PI) / 180;
  return { x: CENTRE + radius * Math.sin(rad), y: CENTRE - radius * Math.cos(rad) };
}

function findCurrent(nodes, currentNode) {
  if (currentNode !== null && currentNode !== undefined) {
    const byId = nodes.find((node) => node && String(node.id) === String(currentNode));
    if (byId) return byId;
  }
  return nodes.find((node) => node && (node.current === true || node.visibility === "current")) || null;
}

function exitIdsOf(edges, currentId) {
  const ids = new Set();
  for (const edge of edges) {
    if (!edge || typeof edge.label !== "string" || edge.label.length === 0) continue;
    if (String(edge.source) === currentId) ids.add(String(edge.destination));
    else if (String(edge.destination) === currentId) ids.add(String(edge.source));
  }
  return ids;
}

function fits(level, dMin, dMax) {
  return dMax * 100 / level <= R_MAX + EPSILON && dMin * 100 / level >= R_MIN - EPSILON;
}

// Selects { mode, level } from the positive candidate distances.
export function selectScale(candidates, previousLevel = null) {
  if (candidates.length === 0) return { mode: "uniform", level: DEFAULT_LEVEL };
  const dMin = Math.min(...candidates);
  const dMax = Math.max(...candidates);
  const idealIndex = LEVELS.findIndex((level) => dMax * 100 / level <= R_MAX + EPSILON);
  if (idealIndex < 0) return { mode: "compressed", level: LEVELS[LEVELS.length - 1] };
  const ideal = LEVELS[idealIndex];
  if (dMin * 100 / ideal < R_MIN - EPSILON) return { mode: "compressed", level: ideal };
  const previousIndex = LEVELS.indexOf(previousLevel);
  if (
    previousIndex >= 0 &&
    previousIndex - idealIndex >= 0 &&
    previousIndex - idealIndex <= 1 &&
    fits(previousLevel, dMin, dMax)
  ) {
    return { mode: "uniform", level: previousLevel };
  }
  return { mode: "uniform", level: ideal };
}

// The radial mapper for one projection: distance in metres -> radius in units.
export function radialMapper(mode, level, candidates) {
  if (mode === "uniform") return (d) => (d * 100) / level;
  const dMin = Math.min(...candidates);
  const dMax = Math.max(...candidates);
  if (dMax - dMin <= EPSILON * dMax) {
    return (d) => (d < dMin ? (R_MIN * d) / dMin : (EQUAL_RADIUS * d) / dMin);
  }
  const span = Math.log(dMax / dMin);
  return (d) => (d < dMin ? (R_MIN * d) / dMin : R_MIN + ((R_MAX - R_MIN) * Math.log(d / dMin)) / span);
}

// Spreads overlapping exits (each { bearing, radius, order }) in place.
export function spreadExits(exits, footprint = EXIT_FOOTPRINT) {
  if (exits.length < 2) return exits;
  const sorted = [...exits].sort((a, b) => a.bearing - b.bearing || a.order - b.order);
  const overlaps = (a, b) => {
    const pa = screen(a.radius, a.bearing);
    const pb = screen(b.radius, b.bearing);
    return Math.hypot(pa.x - pb.x, pa.y - pb.y) < footprint - EPSILON;
  };
  // Single-link groups along the bearing order, closing the circle.
  const groups = [[sorted[0]]];
  for (let i = 1; i < sorted.length; i += 1) {
    if (overlaps(sorted[i - 1], sorted[i])) groups[groups.length - 1].push(sorted[i]);
    else groups.push([sorted[i]]);
  }
  if (groups.length > 1 && overlaps(sorted[sorted.length - 1], sorted[0])) {
    const last = groups.pop();
    groups[0] = [...last, ...groups[0]];
  }
  for (const group of groups) {
    const n = group.length;
    if (n < 2) continue;
    const mean = circularMean(group.map((exit) => exit.bearing));
    // A group wrapping the whole circle has no defined mean: leave it.
    if (mean === null) continue;
    const radius = Math.min(...group.map((exit) => exit.radius));
    let sep = (2 * Math.asin(Math.min(1, footprint / (2 * Math.max(radius, EPSILON)))) * 180) / Math.PI;
    if (((n - 1) / 2) * sep > MAX_SPREAD_DEG) sep = (2 * MAX_SPREAD_DEG) / (n - 1);
    const ordered = [...group].sort(
      (a, b) => angleDelta(a.bearing, mean) - angleDelta(b.bearing, mean) || a.order - b.order,
    );
    ordered.forEach((exit, i) => {
      exit.bearing = normalizeDeg(mean + (i - (n - 1) / 2) * sep);
    });
  }
  return exits;
}

function dotGrid(level, current, factor) {
  const metres = level / 5;
  const cx = current.x * factor;
  const cy = current.y * factor;
  const phaseX = ((metres - (((cx % metres) + metres) % metres)) % metres) * DOT_SPACING / metres;
  const phaseY = ((((cy % metres) + metres) % metres) * DOT_SPACING) / metres;
  return { kind: "dots", spacing: DOT_SPACING, metres, offsetX: phaseX, offsetY: phaseY };
}

// Readable rings: distances inside the candidate span are chosen first
// (ascending), then the remaining in-canvas ones nearest the span, each kept
// only when it clears every chosen ring by RING_MIN_GAP units.
function ringGrid(mapper, dMin, dMax) {
  const options = [];
  for (let decade = 10; decade <= RING_MAX_DISTANCE; decade *= 10) {
    for (const mantissa of RING_MANTISSAS) {
      const distance = mantissa * decade;
      const radius = mapper(distance);
      if (Number.isFinite(radius) && radius >= RING_MIN_RADIUS && radius <= CENTRE) {
        options.push({ distance, radius });
      }
    }
  }
  const outside = (d) => (d < dMin ? dMin / d : d > dMax ? d / dMax : 1);
  const priority = [...options].sort(
    (a, b) => outside(a.distance) - outside(b.distance) || a.distance - b.distance,
  );
  const chosen = [];
  for (const option of priority) {
    if (chosen.length >= MAX_RINGS) break;
    if (chosen.every((ring) => Math.abs(ring.radius - option.radius) >= RING_MIN_GAP)) chosen.push(option);
  }
  chosen.sort((a, b) => a.distance - b.distance);
  return {
    kind: "rings",
    rings: chosen.map((ring) => ({ ...ring, label: formatDistance(ring.distance) })),
  };
}

export function projectIsland(model, previousLevel = null, options = {}) {
  const nodes = Array.isArray(model && model.nodes) ? model.nodes : [];
  const edges = Array.isArray(model && model.edges) ? model.edges : [];
  const current = findCurrent(nodes, model ? model.currentNode : null);
  if (!finitePoint(current)) {
    return {
      mode: "uniform",
      level: DEFAULT_LEVEL,
      nodes: [],
      exitStubs: [],
      grid: { kind: "dots", spacing: DOT_SPACING, metres: DEFAULT_LEVEL / 5, offsetX: 0, offsetY: 0 },
      scaleLabel: `格距 ${formatDistance(DEFAULT_LEVEL / 5)}`,
    };
  }
  const currentId = String(current.id);
  const currentKey = mapKeyOf(currentId);
  const factor = currentId.startsWith("wild:") ? WILDERNESS_CELL_METRES : 1;
  const exitIds = exitIdsOf(edges, currentId);

  const placed = [];
  const exitStubs = [];
  nodes.forEach((node, order) => {
    if (!node || node === current || String(node.id) === currentId) return;
    if (node.visibility === "remembered" || !finitePoint(node)) return;
    const id = String(node.id);
    const isExit = exitIds.has(id);
    if (mapKeyOf(id) !== currentKey) {
      if (isExit) {
        const zero = node.x === current.x && node.y === current.y;
        const leadsTo =
          (current.gateway && current.gateway.leads_to) ||
          (node.gateway && node.gateway.leads_to) ||
          node.label;
        exitStubs.push({
          bearing: zero ? 0 : LocalMap.remoteDirection(current, node).theta,
          label: `通往 ${leadsTo}`,
          action: node.action === undefined ? null : node.action,
        });
      }
      return;
    }
    const distance = Math.hypot(node.x - current.x, node.y - current.y) * factor;
    placed.push({
      node,
      order,
      tier: isExit ? "exit" : "context",
      distance,
      bearing: distance > 0 ? LocalMap.remoteDirection(current, node).theta : null,
      radius: 0,
    });
  });

  const exits = placed.filter((entry) => entry.tier === "exit");
  const context = placed.filter((entry) => entry.tier === "context");
  const pool = exits.length > 0 ? exits : context;
  const candidates = pool.filter((entry) => entry.distance > 0).map((entry) => entry.distance);
  const { mode, level } = selectScale(candidates, previousLevel);
  const mapper = candidates.length > 0 ? radialMapper(mode, level, candidates) : (d) => (d * 100) / level;

  const zeroExits = exits.filter((entry) => entry.distance === 0);
  zeroExits.forEach((entry, i) => {
    entry.bearing = (i * 360) / zeroExits.length;
    entry.radius = R_MIN;
  });
  for (const entry of placed) {
    if (entry.tier === "exit" && entry.distance === 0) continue;
    entry.radius = entry.distance > 0 ? mapper(entry.distance) : 0;
    if (entry.bearing === null) entry.bearing = 0;
  }
  // Zero-distance exits keep their even spacing; only real bearings spread.
  spreadExits(
    exits.filter((entry) => entry.distance > 0),
    options && Number.isFinite(options.footprint) ? options.footprint : EXIT_FOOTPRINT,
  );

  const out = [{ id: current.id, x: CENTRE, y: CENTRE, tier: "current", gateway: current.gateway ?? null }];
  for (const entry of placed) {
    const point = screen(entry.radius, entry.bearing);
    if (
      entry.tier === "context" &&
      (point.x < -EPSILON || point.x > CANVAS_SIZE + EPSILON || point.y < -EPSILON || point.y > CANVAS_SIZE + EPSILON)
    ) {
      continue;
    }
    out.push({ id: entry.node.id, x: point.x, y: point.y, tier: entry.tier, gateway: entry.node.gateway ?? null });
  }

  const grid =
    mode === "uniform"
      ? dotGrid(level, current, factor)
      : ringGrid(mapper, Math.min(...candidates), Math.max(...candidates));
  const scaleLabel = mode === "uniform" ? `格距 ${formatDistance(grid.metres)}` : "距離壓縮";
  return { mode, level, nodes: out, exitStubs, grid, scaleLabel };
}
