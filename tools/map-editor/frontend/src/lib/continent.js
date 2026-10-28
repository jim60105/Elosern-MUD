// Continent authoring helpers (frontend design §4.1): editor-local selection
// references for continental features and their control points, the stored
// coordinate frame of each feature, input mapping from a canvas point to the
// stored unit, and the named single-document command descriptors.
//
// Every derived value (terrain preview, ridge walls, pass centres, national
// borders, cell centres) comes from the service's core projection. Nothing
// here classifies terrain or validates a document: the service and the core
// schema decide. Frames are labelled explicitly: mainland vertices are
// kilometre geometry (`km 地理`), every other control point is a one-
// kilometre wilderness cell index (`1 km 格`), and metres are metres.

export const KM = 1000;
export const MAINLAND = "continent:mainland";
export const FOREST = "continent:forest_edge";
export const RIDGE = "continent:ridge";
export const CONTINENT_DOCUMENT = "content/maps/continent.yaml";
export const LOCATIONS_DOCUMENT = "content/maps/locations.yaml";
export const DISTRICTS_DOCUMENT = "content/maps/districts.yaml";

export const FRAME_KM = "km 地理";
export const FRAME_CELL = "1 km 格";
export const FRAME_LOCAL_M = "m 地方";

export const waterwayRef = (id) => `continent:waterway:${id}`;
export const fordFeatureRef = (id) => `continent:ford:${id}`;
export const siteRef = (id) => `continent:site:${id}`;
export const regionRef = (id) => `continent:region:${id}`;
export const passRef = (index) => `continent:pass#${index}`;
export const districtRef = (id) => `district:${id}`;
export const footprintRef = (id) => `footprint:${id}`;
export const pointRef = (feature, index) => `${feature}#${index}`;

const ID = "[a-z][a-z0-9_]*";
const PATTERNS = [
  [new RegExp(`^continent:(mainland|forest_edge)(?:#(\\d+))?$`), (m) => ({ kind: m[1], id: null, index: m[2] })],
  [new RegExp(`^continent:(waterway|ford):(${ID})(?:#(\\d+))?$`), (m) => ({ kind: m[1], id: m[2], index: m[3] })],
  [/^continent:ridge$/, () => ({ kind: "ridge", id: null })],
  [/^continent:pass#(\d+)$/, (m) => ({ kind: "pass", id: null, index: m[1] })],
  [new RegExp(`^continent:(site|region):(${ID})$`), (m) => ({ kind: m[1], id: m[2] })],
  [new RegExp(`^district:(${ID})$`), (m) => ({ kind: "district", id: m[1] })],
  [new RegExp(`^footprint:(${ID})$`), (m) => ({ kind: "footprint", id: m[1] })],
];

// { kind, id, index (number | null), feature (the feature ref of a point) }
export function parseContinentRef(ref) {
  for (const [pattern, build] of PATTERNS) {
    const match = pattern.exec(ref ?? "");
    if (!match) continue;
    const parsed = build(match);
    const index = parsed.index === undefined || parsed.index === null ? null : Number(parsed.index);
    const feature = ["mainland", "forest_edge", "waterway", "ford"].includes(parsed.kind)
      ? String(ref).replace(/#\d+$/, "")
      : null;
    return { kind: parsed.kind, id: parsed.id, index, feature };
  }
  return null;
}

export function isPointRef(ref) {
  const parsed = parseContinentRef(ref);
  return Boolean(parsed?.feature && parsed.index !== null);
}

// The command `feature` argument of a feature or point reference.
export function commandFeature(ref) {
  const parsed = parseContinentRef(ref);
  if (!parsed?.feature) return null;
  if (parsed.kind === "mainland") return { kind: "mainland" };
  if (parsed.kind === "forest_edge") return { kind: "forest_edge" };
  if (parsed.kind === "waterway") return { kind: "waterway_route", waterway_id: parsed.id };
  return { kind: "waterway_ford", waterway_id: parsed.id };
}

export function frameOf(ref) {
  return parseContinentRef(ref)?.kind === "mainland" ? FRAME_KM : FRAME_CELL;
}

export function cellMetres(world) {
  return (world?.continent?.cell_size_km ?? 1) * KM;
}

// [{ stored: [a, b], m: {x, y} }] of a feature, in its stored frame and in
// continental metres (core cell centres for cell features).
export function featurePoints(world, featureRef) {
  const continent = world?.continent;
  const parsed = parseContinentRef(featureRef);
  if (!continent || !parsed?.feature) return [];
  const pair = (stored, m) => ({ stored: [stored[0], stored[1]], m: { x: m[0], y: m[1] } });
  if (parsed.kind === "mainland") {
    return continent.mainland_boundary_km.map((km) => pair(km, [km[0] * KM, km[1] * KM]));
  }
  if (parsed.kind === "forest_edge") return (continent.forest_edge ?? []).map((cell, i) => pair(cell, continent.forest_edge_m[i]));
  const waterway = continent.waterways.find((row) => row.id === parsed.id);
  if (!waterway) return [];
  if (parsed.kind === "waterway") return (waterway.route ?? []).map((cell, i) => pair(cell, waterway.route_m[i]));
  return (waterway.fords ?? []).map((cell, i) => pair(cell, waterway.fords_m[i]));
}

// The stored value a canvas point (continental metres) maps to.
export function storedFromMetres(world, ref, point) {
  if (parseContinentRef(ref)?.kind === "mainland") return [Math.round(point.x / KM) + 0, Math.round(point.y / KM) + 0];
  return cellOfMetres(world, point);
}

export function cellOfMetres(world, point) {
  const size = cellMetres(world);
  return [Math.floor(point.x / size) + 0, Math.floor(point.y / size) + 0];
}

// The other frame of a stored control point, read-only (design §4.1).
export function companionText(world, ref, stored) {
  if (parseContinentRef(ref)?.kind === "mainland") {
    const size = world?.continent?.cell_size_km ?? 1;
    return `對應野外格 (${Math.floor(stored[0] / size)}, ${Math.floor(stored[1] / size)}) · ${FRAME_CELL}`;
  }
  const size = world?.continent?.cell_size_km ?? 1;
  return `格中心 東 ${(stored[0] + 0.5) * size} km、北 ${(stored[1] + 0.5) * size} km · ${FRAME_KM}`;
}

function distanceToSegment(p, a, b) {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const length = dx * dx + dy * dy;
  const t = length ? Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / length)) : 0;
  return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
}

// Insertion position for 加控制點 at `point`: after the nearest segment's
// first vertex (a closed ring also considers its closing segment). This is
// input mapping only; the service validates the resulting document.
export function insertionIndex(points, point, { closed = false } = {}) {
  if (points.length < 2) return points.length;
  let best = { index: points.length, distance: Infinity };
  const count = closed ? points.length : points.length - 1;
  for (let i = 0; i < count; i += 1) {
    const distance = distanceToSegment(point, points[i], points[(i + 1) % points.length]);
    if (distance < best.distance) best = { index: i + 1, distance };
  }
  if (!closed) {
    // Beyond either end (the nearest point of the line is an end vertex),
    // extend the polyline instead of bending its end segment.
    const first = Math.hypot(point.x - points[0].x, point.y - points[0].y);
    const last = Math.hypot(point.x - points.at(-1).x, point.y - points.at(-1).y);
    if (first <= best.distance && first <= last) return 0;
    if (last <= best.distance) return points.length;
  }
  return best.index;
}

// The stored point 前方插入 / 後方插入 adds next to point `index`.
export function neighbourPoint(points, index, before) {
  const here = points[index]?.stored;
  if (!here) return null;
  const other = points[before ? index - 1 : index + 1]?.stored;
  if (!other) return [here[0] + (before ? -1 : 1), here[1]];
  return [Math.floor((here[0] + other[0]) / 2), Math.floor((here[1] + other[1]) / 2)];
}

export function nextId(prefix, existing) {
  const taken = new Set(existing);
  for (let n = 1; ; n += 1) {
    const candidate = `${prefix}_${n}`;
    if (!taken.has(candidate)) return candidate;
  }
}

export function sameStored(a, b) {
  return Array.isArray(a) && Array.isArray(b) && a[0] === b[0] && a[1] === b[1];
}

// -- command descriptors ----------------------------------------------------
// { name, documentId, arguments }; the expected fingerprint is taken from the
// snapshot the command is built against (see documentCommand).

export function settlementDocument(world, settlementId) {
  return world?.settlements?.find((row) => row.id === settlementId)?.relative_path ?? `content/maps/settlements/${settlementId}.yaml`;
}

export function documentCommand(workspace, descriptor) {
  const row = (workspace?.documents ?? []).find((item) => item.relative_path === descriptor.documentId);
  return { ...descriptor, expected: row ? row.fingerprint : "absent" };
}

const continentCommand = (name, args) => ({ name, documentId: CONTINENT_DOCUMENT, arguments: args });

export function movePoint(ref, stored) {
  const parsed = parseContinentRef(ref);
  return continentCommand("move_control_point", { feature: commandFeature(ref), index: parsed.index, point: stored });
}

export function insertPoint(featureRef, index, stored) {
  return continentCommand("insert_control_point", { feature: commandFeature(featureRef), index, point: stored });
}

export function removePoint(ref) {
  return continentCommand("remove_control_point", { feature: commandFeature(ref), index: parseContinentRef(ref).index });
}

export const terrainParameter = (field, value) => continentCommand("set_terrain_parameter", { field, value });
export const addPass = (yMin, yMax) => continentCommand("add_ridge_pass", { y_min: yMin, y_max: yMax });
export const setPass = (index, yMin, yMax) => continentCommand("set_ridge_pass", { index, y_min: yMin, y_max: yMax });
export const removePass = (index) => continentCommand("remove_ridge_pass", { index });
export const addWaterway = (id, route) => continentCommand("add_waterway", { waterway_id: id, route });
export const removeWaterway = (id) => continentCommand("remove_waterway", { waterway_id: id });
export const regionField = (id, field, value) => continentCommand("set_region_field", { region_id: id, field, value });
export const addSite = (id, fields) => continentCommand("add_site", { site_id: id, ...fields });
export const siteField = (id, field, value) => continentCommand("set_site_field", { site_id: id, field, value });
export const removeSite = (id) => continentCommand("remove_site", { site_id: id });

export const createLocation = (id, fields) => ({
  name: "create_location",
  documentId: LOCATIONS_DOCUMENT,
  arguments: { location_id: id, ...fields },
});
export const locationField = (id, field, value) => ({
  name: "set_location_field",
  documentId: LOCATIONS_DOCUMENT,
  arguments: { location_id: id, field, value },
});
export const deleteLocation = (id) => ({ name: "delete_location", documentId: LOCATIONS_DOCUMENT, arguments: { location_id: id } });

export const createDistrict = (id, fields) => ({
  name: "create_district",
  documentId: DISTRICTS_DOCUMENT,
  arguments: { district_id: id, ...fields },
});
export const districtField = (id, field, value) => ({
  name: "set_district_field",
  documentId: DISTRICTS_DOCUMENT,
  arguments: { district_id: id, field, value },
});

export const footprintCell = (world, settlementId, cell, filled) => ({
  name: "set_footprint_cell",
  documentId: settlementDocument(world, settlementId),
  arguments: { settlement_id: settlementId, cell, filled },
});
export const binding = (world, settlementId, anchorCell, localAnchor) => ({
  name: "set_binding",
  documentId: settlementDocument(world, settlementId),
  arguments: { settlement_id: settlementId, anchor_cell: anchorCell, local_anchor_m: localAnchor },
});

// The removal command of a selected continental object, or null when this
// kind has no delete command (the inline explanation says so).
export function removalOf(world, ref) {
  const parsed = parseContinentRef(ref);
  if (!parsed) return null;
  if (parsed.feature && parsed.index !== null) return removePoint(ref);
  if (parsed.kind === "waterway") return removeWaterway(parsed.id);
  if (parsed.kind === "pass") return removePass(parsed.index);
  if (parsed.kind === "site") return removeSite(parsed.id);
  return null;
}

// -- footprint grid ----------------------------------------------------------
// The editable grid of one footprint: the mask plus a one-cell margin, north
// row first, so a neighbouring cell can be filled from the keyboard.
export function footprintGrid(footprint) {
  if (!footprint) return null;
  const filled = new Set(footprint.cells.map(([x, y]) => `${x},${y}`));
  const [ox, oy] = footprint.origin;
  const width = footprint.shape[0]?.length ?? 0;
  const height = footprint.shape.length;
  const west = ox - 1;
  const south = oy - 1;
  const rows = [];
  for (let y = oy + height; y >= south; y -= 1) {
    const cells = [];
    for (let x = west; x <= ox + width; x += 1) cells.push({ x, y, filled: filled.has(`${x},${y}`) });
    rows.push({ y, cells });
  }
  return { rows, west, east: ox + width, south, north: oy + height };
}

// -- terrain preview raster ---------------------------------------------------
// Muted ink per region (index into the preview's sorted region keys) with the
// surface class drawn over it; colour is never the only carrier: the ridge
// walls and waterways are also drawn as lines, and regions are named in the
// inspector.
const REGION_TINTS = [
  [96, 108, 92],
  [88, 104, 80],
  [70, 92, 64],
  [84, 98, 74],
  [100, 110, 120],
  [104, 112, 124],
  [104, 100, 82],
];
const SEA = [11, 16, 22, 0];
const WATER = [60, 96, 120, 200];
const RIDGE_TONE = [140, 124, 100, 210];

export function previewColor(value, surfaceCount = 4) {
  const surface = value % surfaceCount;
  const region = Math.floor(value / surfaceCount);
  if (surface === 0) return SEA;
  if (surface === 2) return WATER;
  if (surface === 3) return RIDGE_TONE;
  const [r, g, b] = REGION_TINTS[region % REGION_TINTS.length];
  return [r, g, b, 90];
}

// RGBA bytes, north row first (image order), of a core terrain preview.
export function previewPixels(preview) {
  const { columns, rows, samples } = preview;
  const surfaces = preview.surfaces?.length ?? 4;
  const pixels = new Uint8ClampedArray(columns * rows * 4);
  for (let row = 0; row < rows; row += 1) {
    for (let column = 0; column < columns; column += 1) {
      const colour = previewColor(samples[row * columns + column], surfaces);
      const offset = ((rows - 1 - row) * columns + column) * 4;
      pixels.set(colour, offset);
    }
  }
  return pixels;
}
