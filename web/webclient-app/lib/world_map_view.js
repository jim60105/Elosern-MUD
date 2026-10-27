// Pure geometry, level of detail and reading model for WorldMapView
// (OpenSpec change render-world-map-view; approved design
// docs/superpowers/specs/2026-10-22-world-map-drawer-design.md §4.4, §6.2-§6.5).
// Dependency-light ES module: no Vue, no DOM (text measurement is injected).
//
// Input is a validated `world_map` v1 body (protocol/panels/map_panels.js
// validateWorldMapPanel), in continent kilometres with north-positive y.
// Nothing here invents a district name, a landmark, a place, a nation claim
// or an exact commission point: every drawn fact comes from the payload, and
// an unlit district is only its outline and its opaque wire id.
//
// Geometry is turned into SVG path data in world units once per payload; the
// component draws it inside one `matrix(k 0 0 -k tx ty)` group with
// non-scaling strokes, so a pan or zoom changes a transform and never
// rebuilds a path. Labels, markers and hatching live in screen space.

import { compassWord } from "./area_map_view.js";
import { WORLD_COUNTRY_SPAN_KM, WORLD_DISTRICT_SPAN_KM, WORLD_NEARBY_SPAN_KM, worldStops } from "./map_stops.js";
import {
  DEFAULT_MARGIN_PX,
  centreOn,
  estimateTextWidth,
  fitBounds,
  formatDistance,
  rectsOverlap,
  spanLimits,
} from "@elosern/map-view";

/** The world view's controlled-view signature (one continent, kilometres). */
export const WORLD_SIGNATURE = "world|elosern|km";
/** Label size floor (design §6.3): 16 CSS px at ui-scale 1, never smaller. */
export const LABEL_FONT_PX = 16;
/** Nation names are larger display type (never below the floor). */
export const NATION_FONT_PX = 20;
/** Lit district and place names: views up to this span (inclusive). */
export const NAME_MAX_SPAN_KM = 1000;
/** `未探明` labels: views up to this span (inclusive). */
export const UNLIT_LABEL_MAX_SPAN_KM = 450;
/**
 * Nation names belong to the 大陸 and 國 views. Wheel zoom is continuous, so
 * the boundary is the log midpoint between 國 (800 km) and 地區 (200 km):
 * nations show at spans of 400 km and wider.
 */
export const NATION_MIN_SPAN_KM = Math.sqrt(WORLD_COUNTRY_SPAN_KM * WORLD_DISTRICT_SPAN_KM);
/**
 * The trail is drawn as cells only at the 近郊 view: spans up to the log
 * midpoint between 地區 (200 km) and 近郊 (40 km), about 89 km.
 */
export const TRAIL_CELL_MAX_SPAN_KM = Math.sqrt(WORLD_DISTRICT_SPAN_KM * WORLD_NEARBY_SPAN_KM);
/** The server's approximate-marker grid (map-panel protocol). */
export const APPROXIMATE_GRID_KM = 50;
/**
 * A 50 km grid point is at most 25·√2 ≈ 35.4 km from the true point, so a
 * 36 km circle always covers it. It never shrinks below a readable ring.
 */
export const APPROXIMATE_RADIUS_KM = 36;
export const APPROXIMATE_MIN_RADIUS_PX = 16;
/** Screen gap the trail line keeps between joined cell centres. */
export const TRAIL_MIN_GAP_PX = 9;
/** The motion token that times a district's ink reveal (600 ms at `full`). */
export const REVEAL_TOKEN = "--motion-district-reveal";

// ── level of detail ─────────────────────────────────────────────────────

/** Which label and trail families a view of `span` km shows (inclusive). */
export function lodFor(span) {
  return Object.freeze({
    nations: span >= NATION_MIN_SPAN_KM,
    names: span <= NAME_MAX_SPAN_KM,
    unlit: span <= UNLIT_LABEL_MAX_SPAN_KM,
    trailCells: span <= TRAIL_CELL_MAX_SPAN_KM,
  });
}

// ── bounds, stops and views ─────────────────────────────────────────────

// Payload geometry arrives as [x, y] tuples, so this bounds reducer reads
// them directly instead of the shared point-object helper.
function tupleBounds(points) {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const [x, y] of points) {
    minX = Math.min(minX, x);
    minY = Math.min(minY, y);
    maxX = Math.max(maxX, x);
    maxY = Math.max(maxY, y);
  }
  return { minX, minY, maxX, maxY };
}

/** The common coastline's bounds: the continent the 大陸 stop fits. */
export function continentBounds(world) {
  return tupleBounds(world.common.coastline);
}

export function worldStopsFor(world, frame) {
  return worldStops(continentBounds(world), frame);
}

function frozenView(view) {
  return Object.freeze({ signature: WORLD_SIGNATURE, cx: view.cx, cy: view.cy, span: view.span });
}

function clampSpan(span, stops) {
  const limits = spanLimits(stops);
  return Math.min(limits.max, Math.max(limits.min, span));
}

/**
 * The opening view (design §6.4): 國 centred on the player; when the tracked
 * commission lies within 800 km, the 國 view is centred so the player and it
 * show together (widened only if the pair needs it).
 */
export function openingView(world, frame, stops = worldStopsFor(world, frame)) {
  const here = world.current;
  const tracked = world.quest_markers.find(
    (marker) => marker.tracked && Math.hypot(marker.x - here.x, marker.y - here.y) <= WORLD_COUNTRY_SPAN_KM,
  );
  if (tracked) {
    const fitted = fitBounds(
      {
        minX: Math.min(here.x, tracked.x),
        minY: Math.min(here.y, tracked.y),
        maxX: Math.max(here.x, tracked.x),
        maxY: Math.max(here.y, tracked.y),
      },
      frame,
      { marginPx: 96, minSpan: WORLD_COUNTRY_SPAN_KM },
    );
    return frozenView({ cx: fitted.cx, cy: fitted.cy, span: clampSpan(fitted.span, stops) });
  }
  return frozenView(centreOn({ cx: here.x, cy: here.y, span: clampSpan(WORLD_COUNTRY_SPAN_KM, stops) }, frame, here));
}

/** The 大陸 view: the whole continent at one uniform scale. */
export function wholeView(world, frame, rect = null) {
  const fitted = fitBounds(continentBounds(world), frame, { rect, marginPx: DEFAULT_MARGIN_PX });
  return frozenView(fitted);
}

// ── path data in world units ────────────────────────────────────────────

const fmt = (v) => (Number.isInteger(v) ? String(v) : String(Math.round(v * 100) / 100));

/** Closed rings (outer CCW, holes CW) as one path, for fill-rule evenodd. */
export function ringsPath(rings) {
  return rings
    .map((ring) => `M${ring.map(([x, y]) => `${fmt(x)} ${fmt(y)}`).join("L")}Z`)
    .join("");
}

export function linesPath(lines) {
  return lines.map((line) => `M${line.map(([x, y]) => `${fmt(x)} ${fmt(y)}`).join("L")}`).join("");
}

/** The trail's real cells: one square per run, `resolution_km` wide. */
export function trailCellsPath(trail) {
  const r = trail.resolution_km;
  let d = "";
  for (const [row, runs] of trail.rows) {
    for (const [start, length] of runs) {
      d += `M${start * r} ${row * r}h${length * r}v${r}h${-length * r}Z`;
    }
  }
  return d;
}

/** Number of visited trail cells at the supplied resolution. */
export function trailCellCount(trail) {
  let n = 0;
  for (const [, runs] of trail.rows) for (const [, length] of runs) n += length;
  return n;
}

const GRID_STEPS = [1, 2, 5, 10, 20, 25, 50, 100];

/**
 * The trail line's join grid for a view: the smallest multiple of the
 * supplied resolution whose cells sit at least TRAIL_MIN_GAP_PX apart on
 * screen, so a wide view draws a few thousand joins instead of every cell.
 */
export function trailGridKm(trail, kmPerPx) {
  const r = trail.resolution_km;
  for (const step of GRID_STEPS) {
    if ((r * step) / kmPerPx >= TRAIL_MIN_GAP_PX) return r * step;
  }
  return r * GRID_STEPS[GRID_STEPS.length - 1];
}

function chaikin(points, rounds) {
  let pts = points;
  for (let round = 0; round < rounds && pts.length > 2; round += 1) {
    const next = [pts[0]];
    for (let i = 0; i + 1 < pts.length; i += 1) {
      const [ax, ay] = pts[i];
      const [bx, by] = pts[i + 1];
      next.push([0.75 * ax + 0.25 * bx, 0.75 * ay + 0.25 * by], [0.25 * ax + 0.75 * bx, 0.25 * ay + 0.75 * by]);
    }
    next.push(pts[pts.length - 1]);
    pts = next;
  }
  return pts;
}

// A lattice staircase's segment midpoints lie on its diagonal: keep the
// ends, replace the interior by midpoints, and the stairs become a line.
function unstair(points) {
  if (points.length < 3) return points;
  const out = [points[0]];
  for (let i = 0; i + 1 < points.length; i += 1) {
    out.push([(points[i][0] + points[i + 1][0]) / 2, (points[i][1] + points[i + 1][1]) / 2]);
  }
  out.push(points[points.length - 1]);
  return out;
}

/**
 * The trail as a line on a `gridKm` lattice. Visited lattice cells are
 * joined to their visited orthogonal neighbours, and diagonally only where
 * no orthogonal cell already links the pair. The joins are walked into
 * chains between branch points and each chain is unstaired and corner-smoothed (Chaikin),
 * so a diagonal walk reads as a line rather than a staircase; a cell with no
 * visited neighbour is a dot. The joins only connect cells the payload marks
 * visited; no route between them is implied.
 */
export function trailLinePath(trail, gridKm = trail.resolution_km) {
  const r = trail.resolution_km;
  const cells = new Set();
  const key = (x, y) => `${x},${y}`;
  for (const [row, runs] of trail.rows) {
    const gy = Math.floor((row * r) / gridKm);
    for (const [start, length] of runs) {
      const first = Math.floor((start * r) / gridKm);
      const last = Math.floor(((start + length) * r - 1e-9) / gridKm);
      for (let gx = first; gx <= last; gx += 1) cells.add(key(gx, gy));
    }
  }
  const adjacency = new Map();
  const link = (a, b) => {
    adjacency.get(a).push(b);
    adjacency.get(b).push(a);
  };
  for (const cell of cells) adjacency.set(cell, []);
  for (const cell of cells) {
    const [x, y] = cell.split(",").map(Number);
    const has = (dx, dy) => cells.has(key(x + dx, y + dy));
    if (has(1, 0)) link(cell, key(x + 1, y));
    if (has(0, 1)) link(cell, key(x, y + 1));
    if (has(1, 1) && !has(1, 0) && !has(0, 1)) link(cell, key(x + 1, y + 1));
    if (has(-1, 1) && !has(-1, 0) && !has(0, 1)) link(cell, key(x - 1, y + 1));
  }
  const centre = (cell) => cell.split(",").map((v) => Number(v) * gridKm + gridKm / 2);
  const used = new Set();
  const edgeKey = (a, b) => (a < b ? `${a}|${b}` : `${b}|${a}`);
  const chains = [];
  const walk = (from, to) => {
    const chain = [from, to];
    used.add(edgeKey(from, to));
    let prev = from;
    let at = to;
    while (adjacency.get(at).length === 2) {
      const next = adjacency.get(at).find((n) => n !== prev);
      if (used.has(edgeKey(at, next))) break;
      used.add(edgeKey(at, next));
      chain.push(next);
      prev = at;
      at = next;
    }
    chains.push(chain);
  };
  const ordered = [...cells].sort();
  for (const cell of ordered) {
    const links = adjacency.get(cell);
    if (links.length === 0) chains.push([cell]);
    else if (links.length !== 2) for (const n of links) if (!used.has(edgeKey(cell, n))) walk(cell, n);
  }
  for (const cell of ordered) {
    for (const n of adjacency.get(cell)) if (!used.has(edgeKey(cell, n))) walk(cell, n);
  }
  let d = "";
  let points = 0;
  for (const chain of chains) {
    const pts = chain.length === 1 ? [centre(chain[0]), centre(chain[0])] : chaikin(unstair(chain.map(centre)), 2);
    d += `M${pts.map(([x, y]) => `${fmt(x)} ${fmt(y)}`).join("L")}`;
    points += pts.length;
  }
  return { d, segments: chains.length, points };
}

// ── features ────────────────────────────────────────────────────────────

// Validated payloads are immutable per object: memoise per-payload
// derivations so a pan never re-walks every outline or place list.
const anchorCache = new WeakMap();
const placesCache = new WeakMap();

/** Area-weighted centroid of the largest counter-clockwise ring. */
export function outlineAnchor(rings) {
  if (anchorCache.has(rings)) return anchorCache.get(rings);
  const anchor = computeAnchor(rings);
  anchorCache.set(rings, anchor);
  return anchor;
}

function computeAnchor(rings) {
  let best = null;
  let bestArea = 0;
  for (const ring of rings) {
    let a = 0;
    let cx = 0;
    let cy = 0;
    for (let i = 0; i + 1 < ring.length; i += 1) {
      const cross = ring[i][0] * ring[i + 1][1] - ring[i + 1][0] * ring[i][1];
      a += cross;
      cx += (ring[i][0] + ring[i + 1][0]) * cross;
      cy += (ring[i][1] + ring[i + 1][1]) * cross;
    }
    a /= 2;
    if (a > bestArea) {
      bestArea = a;
      best = { x: cx / (6 * a), y: cy / (6 * a) };
    }
  }
  return best ?? { x: rings[0][0][0], y: rings[0][0][1] };
}

/** Outline bounds in world units. */
export function outlineBounds(rings) {
  return tupleBounds(rings.flat());
}

/**
 * Every drawable place: the places supplied inside lit districts plus the
 * visited places (a hidden place visited before its district lit), one row
 * per id. `district` is the lit district that lists it, if any.
 */
export function placesOf(world) {
  if (placesCache.has(world)) return placesCache.get(world);
  const out = new Map();
  const visited = new Set(world.visited_places.map((place) => place.id));
  for (const district of world.districts) {
    if (!district.lit) continue;
    for (const place of district.places) {
      out.set(place.id, { ...place, district: district.id, visited: visited.has(place.id) });
    }
  }
  for (const place of world.visited_places) {
    if (!out.has(place.id)) out.set(place.id, { ...place, district: null, visited: true });
  }
  const rows = Object.freeze([...out.values()].map((row) => Object.freeze(row)));
  placesCache.set(world, rows);
  return rows;
}

export function districtById(world, id) {
  return world.districts.find((district) => district.id === id) ?? null;
}

/** Lit district ids of a payload. */
export function litIds(world) {
  return new Set(world.districts.filter((district) => district.lit).map((district) => district.id));
}

/**
 * Discovery between two consecutive payloads of one session: `lit` are the
 * ids that were unlit before and are lit now (an id absent before never
 * counts), and `regressed` is true when any lit id went dark, which only
 * happens when the payload belongs to someone else's knowledge.
 */
export function revealTransitions(previous, next) {
  if (!previous) return { lit: [], regressed: false };
  const before = new Map(previous.districts.map((district) => [district.id, district.lit]));
  const lit = [];
  let regressed = false;
  for (const district of next.districts) {
    const was = before.get(district.id);
    if (was === false && district.lit) lit.push(district.id);
    if (was === true && !district.lit) regressed = true;
  }
  return { lit, regressed };
}

/** The ink spread's reach: the farthest outline vertex from the landmark. */
export function revealRadiusKm(district) {
  let r = 0;
  for (const ring of district.outline) {
    for (const [x, y] of ring) r = Math.max(r, Math.hypot(x - district.landmark.x, y - district.landmark.y));
  }
  return r;
}

// ── reading model ───────────────────────────────────────────────────────

const PLACE_KIND_TEXT = { capital: "王都", settlement: "聚落", harbour: "港口", hidden: "隱密之地" };

function distanceText(from, to) {
  const km = Math.hypot(to.x - from.x, to.y - from.y);
  if (km < 0.5) return "就在這裡";
  const rounded = km >= 100 ? Math.round(km / 10) * 10 : Math.max(1, Math.round(km));
  return `${compassWord(to.x - from.x, to.y - from.y)}方 · 直線約 ${formatDistance(rounded * 1000)}`;
}

function nationNames(world, ids) {
  const byId = new Map(world.common.nations.map((nation) => [nation.id, nation.name]));
  return ids.map((id) => byId.get(id)).filter((name) => typeof name === "string");
}

export function parseKey(key) {
  if (typeof key !== "string") return null;
  const at = key.indexOf(":");
  if (at <= 0) return null;
  const kind = key.slice(0, at);
  if (!["district", "place", "quest"].includes(kind)) return null;
  return { kind, id: key.slice(at + 1) };
}

/**
 * The selection reading for `district:<id>`, `place:<id>` or `quest:<id>`.
 * Every line comes from the payload or from arithmetic on its coordinates.
 * An unlit district reads as nameless and lists no nation, landmark or
 * place. Null for a key the payload does not hold.
 */
export function featureDetail(world, key) {
  const parsed = parseKey(key);
  if (!parsed) return null;
  const here = world.current;
  if (parsed.kind === "district") {
    const district = districtById(world, parsed.id);
    if (!district) return null;
    if (!district.lit) {
      return Object.freeze({
        key,
        kind: "district",
        id: district.id,
        lit: false,
        label: "分區",
        title: "未探明",
        nations: [],
        lines: ["尚未抵達此分區的地標", distanceText(here, outlineAnchor(district.outline))],
        places: [],
        quests: [],
      });
    }
    const nations = nationNames(world, district.nations);
    return Object.freeze({
      key,
      kind: "district",
      id: district.id,
      lit: true,
      label: "分區",
      title: district.name,
      nations,
      lines: [
        `地標：${district.landmark.name}`,
        distanceText(here, district.landmark),
      ].filter(Boolean),
      places: district.places.map((place) => place.name),
      quests: world.quest_markers
        .filter((marker) => !marker.approximate && insideOutline(district.outline, marker))
        .map((marker) => ({ id: marker.id, title: marker.title, tracked: marker.tracked })),
    });
  }
  if (parsed.kind === "place") {
    const place = placesOf(world).find((row) => row.id === parsed.id);
    if (!place) return null;
    const district = place.district ? districtById(world, place.district) : null;
    return Object.freeze({
      key,
      kind: "place",
      id: place.id,
      label: PLACE_KIND_TEXT[place.kind],
      title: place.name,
      nations: [],
      lines: [
        district ? `所在分區：${district.name}` : null,
        place.visited ? "曾到訪" : "尚未到訪",
        distanceText(here, place),
      ].filter(Boolean),
      places: [],
      quests: [],
    });
  }
  const marker = world.quest_markers.find((row) => row.id === parsed.id);
  if (!marker) return null;
  return Object.freeze({
    key,
    kind: "quest",
    id: marker.id,
    approximate: marker.approximate,
    label: "委託",
    title: marker.title,
    nations: [],
    lines: [
      marker.tracked ? "追蹤中" : null,
      marker.approximate ? "大致方位 · 誤差約 35 km 內" : "精確位置",
      distanceText(here, marker),
    ].filter(Boolean),
    places: [],
    quests: [],
  });
}

/** Even-odd point-in-outline test in world units. */
export function insideOutline(rings, point) {
  let inside = false;
  for (const ring of rings) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
      const [xi, yi] = ring[i];
      const [xj, yj] = ring[j];
      if (yi > point.y !== yj > point.y && point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi) inside = !inside;
    }
  }
  return inside;
}

/** The accessible name of a selectable feature (the keyboard list). */
export function featureName(world, key) {
  const detail = featureDetail(world, key);
  if (!detail) return "";
  const where = detail.lines[detail.lines.length - 1];
  if (detail.kind === "district" && !detail.lit) return `未探明分區，${where}`;
  if (detail.kind === "quest") return `委託：${detail.title}，${detail.approximate ? "大致方位" : "精確位置"}，${where}`;
  return `${detail.label}：${detail.title}，${where}`;
}

/**
 * The keyboard order of selectable features: commissions (tracked first),
 * then places, lit districts and unlit districts, each nearest first.
 */
export function featureKeys(world) {
  const here = world.current;
  const dist = (p) => Math.hypot(p.x - here.x, p.y - here.y);
  const quests = [...world.quest_markers]
    .sort((a, b) => Number(b.tracked) - Number(a.tracked) || dist(a) - dist(b))
    .map((marker) => `quest:${marker.id}`);
  const places = [...placesOf(world)]
    .sort((a, b) => dist(a) - dist(b))
    .map((place) => `place:${place.id}`);
  const lit = world.districts
    .filter((district) => district.lit)
    .sort((a, b) => dist(a.landmark) - dist(b.landmark))
    .map((district) => `district:${district.id}`);
  const unlit = world.districts
    .filter((district) => !district.lit)
    .map((district) => ({ district, d: dist(outlineAnchor(district.outline)) }))
    .sort((a, b) => a.d - b.d)
    .map(({ district }) => `district:${district.id}`);
  return [...quests, ...places, ...lit, ...unlit];
}

/** Where a feature's focus ring and recentre go, in world units. */
export function featurePoint(world, key) {
  const parsed = parseKey(key);
  if (!parsed) return null;
  if (parsed.kind === "district") {
    const district = districtById(world, parsed.id);
    if (!district) return null;
    return district.lit ? { ...district.landmark } : outlineAnchor(district.outline);
  }
  if (parsed.kind === "place") {
    const place = placesOf(world).find((row) => row.id === parsed.id);
    return place ? { x: place.x, y: place.y } : null;
  }
  const marker = world.quest_markers.find((row) => row.id === parsed.id);
  return marker ? { x: marker.x, y: marker.y } : null;
}

// ── labels ──────────────────────────────────────────────────────────────

/**
 * Label candidates for a view. Priorities (lower wins a collision; ties
 * break on the stable key): the selected feature 0, commissions 1 (tracked
 * before untracked), nations 2, capitals 3, lit district names 4, other
 * places 5, `未探明` 6. Families outside their LOD are not candidates.
 * Each candidate carries its world anchor, its lines and its kind.
 */
export function labelCandidates(world, lod, selectedKey = null) {
  const out = [];
  const pri = (key, base) => (key === selectedKey ? 0 : base);
  for (const marker of world.quest_markers) {
    const key = `quest:${marker.id}`;
    out.push({
      key,
      kind: marker.approximate ? "quest-approx" : "quest",
      lines: marker.approximate ? [marker.title, "大致方位"] : [marker.title],
      x: marker.x,
      y: marker.y,
      priority: pri(key, marker.tracked ? 1 : 1.5),
    });
  }
  if (lod.nations) {
    for (const nation of world.common.nations) {
      out.push({ key: `nation:${nation.id}`, kind: "nation", lines: [nation.name], x: nation.x, y: nation.y, priority: 2 });
    }
  }
  if (lod.names) {
    for (const place of placesOf(world)) {
      const key = `place:${place.id}`;
      out.push({ key, kind: "place", lines: [place.name], x: place.x, y: place.y, priority: pri(key, place.kind === "capital" ? 3 : 5) });
    }
    for (const district of world.districts) {
      if (!district.lit) continue;
      const key = `district:${district.id}`;
      out.push({ key, kind: "district", lines: [district.name], x: district.landmark.x, y: district.landmark.y, priority: pri(key, 4) });
    }
  }
  for (const district of world.districts) {
    if (district.lit) continue;
    const key = `district:${district.id}`;
    if (!lod.unlit && key !== selectedKey) continue;
    const anchor = outlineAnchor(district.outline);
    out.push({ key, kind: "unlit", lines: ["未探明"], x: anchor.x, y: anchor.y, priority: pri(key, 6) });
  }
  return out.sort((a, b) => a.priority - b.priority || (a.key < b.key ? -1 : a.key > b.key ? 1 : 0));
}

/**
 * Greedy priority placement in frame pixels. Each kind tries its own spots;
 * a label that fits nowhere clear of placed labels, marker obstacles (other
 * than its own) and the frame edge is hidden, never shrunk or truncated.
 * `project(candidate)` gives the anchor pixel; `radius(candidate)` its
 * marker radius in px. Returns `[{ key, kind, lines, anchor, x, y, lineHeight,
 * fontPx, box }]`.
 */
export function placeWorldLabels(candidates, project, frame, {
  fontPx = LABEL_FONT_PX,
  nationFontPx = NATION_FONT_PX,
  measure = estimateTextWidth,
  radius = () => 8,
  obstacles = [],
} = {}) {
  const placedBoxes = [];
  const out = [];
  const pad = Math.round(fontPx * 0.25);
  for (const candidate of candidates) {
    const p = project(candidate);
    const size = candidate.kind === "nation" ? nationFontPx : fontPx;
    const spacing = candidate.kind === "nation" ? 0.32 : candidate.kind === "unlit" ? 0.2 : 0.04;
    const lineHeight = Math.round(size * 1.3);
    const ascent = Math.round(size * 1.19);
    const height = (candidate.lines.length - 1) * lineHeight + Math.round(size * 1.5);
    const width = Math.max(...candidate.lines.map((line) => measure(line, size, spacing))) + 4;
    // Cull: an anchor far outside the frame never competes.
    if (p.x < -width || p.y < -height || p.x > frame.width + width || p.y > frame.height + height) continue;
    const r = radius(candidate);
    const gap = Math.round(size * 0.35);
    const centred = (top) => ({ anchor: "middle", left: p.x - width / 2, top });
    const right = { anchor: "start", left: p.x + r + gap, top: p.y - height / 2 };
    const left = { anchor: "end", left: p.x - r - gap - width, top: p.y - height / 2 };
    const above = centred(p.y - r - gap - height);
    const below = centred(p.y + r + gap);
    const options = {
      nation: [
        centred(p.y - r - gap * 2 - height),
        centred(p.y + r + gap * 2),
        right,
        left,
        centred(p.y - r - gap * 2 - height * 2.2),
        centred(p.y + r + gap * 2 + height * 1.2),
      ],
      district: [below, above, right, left],
      place: [right, left, above, below],
      unlit: [centred(p.y - height / 2), centred(p.y + gap), centred(p.y - height - gap)],
      quest: [above, right, left, below],
      "quest-approx": [below, above, right, left],
    }[candidate.kind];
    let chosen = null;
    for (const option of options) {
      const box = { left: option.left, top: option.top, right: option.left + width, bottom: option.top + height };
      if (box.left < 0 || box.top < 0 || box.right > frame.width || box.bottom > frame.height) continue;
      const padded = { left: box.left - pad, right: box.right + pad, top: box.top - pad, bottom: box.bottom + pad };
      if (placedBoxes.some((other) => rectsOverlap(padded, other))) continue;
      if (obstacles.some((ob) => ob.key !== candidate.key && rectsOverlap(box, ob))) continue;
      chosen = { ...option, box };
      break;
    }
    if (!chosen) continue;
    placedBoxes.push(chosen.box);
    const x = chosen.anchor === "middle" ? chosen.left + width / 2 : chosen.anchor === "start" ? chosen.left : chosen.left + width;
    out.push({
      key: candidate.key,
      kind: candidate.kind,
      lines: candidate.lines,
      anchor: chosen.anchor,
      x,
      y: chosen.top + ascent,
      lineHeight,
      fontPx: size,
      box: chosen.box,
    });
  }
  return out;
}
