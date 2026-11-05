// The one wilderness window decoder (OpenSpec change
// wilderness-travel-window-ui, design "Shared decoder cutover").
// Dependency-light ES module: no Vue, no DOM.
//
// `decodeWildernessGrid(area)` turns a schema-4 wilderness `area_map` body
// into its decoded cell grid. Both map consumers read it: the drawer's
// `area_map_view.decodeWindow` and the travel stage's
// `travel-grid.decodeTravelGrid`, so they share coordinates and rejection.
//
// `decodeDistrictOverview(area)` decodes the schema-4 `district` record: the
// coarse RLE overview of the current lit district. It returns the coarse
// origin/size, the ladder `cellKm`, the frozen runs and one expanded cell per
// revealed coarse cell; `null` means no overview (or a body it cannot lay out
// exactly). The wire validator alone owns ladder membership, the 0..2700 frame
// and the finite caps; this decoder only refuses a structure it cannot lay out.
//
// The decoder trusts a validated body: the store validates every body
// against the exact wire schema before it is committed
// (protocol/panels/map_panels.js), and that validator alone owns value
// bounds and cross-field rules. The decoder only refuses a body whose rows
// it cannot lay out exactly — a non-wilderness or older schema (node-form
// wilderness included), a row count or run total other than the window's,
// an unknown run with any extra key, a revealed run without its exact keys —
// and returns null rather than guessing. Bodies are immutable once
// committed, so the per-body cache never goes stale.
//
// `cells` is row-major and south-to-north: index `row * width + col` is the
// cell at `(origin.x + col, origin.y + row)`; row 0 is the window's southern
// edge (map y grows northward). An unknown cell is `null`: it carries no
// fact at all.

/** The wilderness area_map schema this decoder reads. */
export const WILDERNESS_GRID_SCHEMA = 4;

const UNKNOWN_KEYS = ["kind", "length"];
const TERRAIN_KEYS = ["band", "display", "ford", "kind", "length", "passable", "road", "terrain", "tier"];
const DISPLAY_KEYS = ["district_key", "district_name", "ford_label", "settlement", "terrain_label"];
const OVERVIEW_KEYS = ["cell_km", "key", "name_zh", "rows", "window"];
const OVERVIEW_WINDOW_KEYS = ["height", "min_x", "min_y", "width"];
const OVERVIEW_UNKNOWN_KEYS = ["kind", "length"];
const OVERVIEW_TERRAIN_KEYS = ["band", "kind", "length", "passable", "terrain"];
const OVERVIEW_TERRAIN_CLASSES = new Set([
  "open_ground", "hills", "mountain", "woodland", "water", "ridge", "settlement",
]);

const cache = new WeakMap();
const overviewCache = new WeakMap();

function plain(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function keysAre(value, keys) {
  if (!plain(value)) return false;
  const own = Object.keys(value).sort();
  return own.length === keys.length && own.every((key, index) => key === keys[index]);
}

function count(value, max) {
  return Number.isInteger(value) && value >= 1 && value <= max;
}

function ownKeysAre(value, keys) {
  if (!plain(value)) return false;
  const own = Object.keys(value).sort();
  return own.length === keys.length && own.every((key, index) => key === keys[index]);
}

function overviewRun(run, width) {
  if (!plain(run) || !Number.isInteger(run.length) || run.length < 1 || run.length > width) return undefined;
  if (run.kind === "unknown") {
    return ownKeysAre(run, OVERVIEW_UNKNOWN_KEYS) ? Object.freeze({ length: run.length, kind: "unknown" }) : undefined;
  }
  if (run.kind !== "terrain" || !ownKeysAre(run, OVERVIEW_TERRAIN_KEYS)) return undefined;
  if (!OVERVIEW_TERRAIN_CLASSES.has(run.terrain)) return undefined;
  if (!Number.isInteger(run.band) || run.band < 0 || run.band > 15 || typeof run.passable !== "boolean") return undefined;
  return Object.freeze({
    length: run.length,
    kind: "terrain",
    terrain: run.terrain,
    band: run.band,
    passable: run.passable,
  });
}

function sameOverviewRun(a, b) {
  if (a.kind !== b.kind) return false;
  if (a.kind === "unknown") return true;
  return a.terrain === b.terrain && a.band === b.band && a.passable === b.passable;
}

// One district record: the decoded overview, null for no overview, or
// undefined when the record cannot be laid out exactly.
function decodeOverviewValue(value) {
  if (value === null) return null;
  if (!ownKeysAre(value, OVERVIEW_KEYS)) return undefined;
  if (typeof value.key !== "string" || value.key.length === 0 || value.key.length > 128) return undefined;
  if (typeof value.name_zh !== "string" || value.name_zh.length === 0) return undefined;
  const cellKm = value.cell_km;
  if (!Number.isInteger(cellKm) || cellKm < 1 || cellKm > 1000) return undefined;
  const window = value.window;
  if (!ownKeysAre(window, OVERVIEW_WINDOW_KEYS)) return undefined;
  if (![window.min_x, window.min_y, window.width, window.height].every(Number.isInteger)) return undefined;
  if (window.min_x < 0 || window.min_y < 0 || !count(window.width, 4096) || !count(window.height, 4096)) return undefined;
  if (window.width * window.height > 32768) return undefined;
  if (!Array.isArray(value.rows) || value.rows.length !== window.height) return undefined;
  const rows = [];
  const cells = new Array(window.width * window.height).fill(null);
  for (let row = 0; row < window.height; row += 1) {
    const source = value.rows[row];
    if (!Array.isArray(source)) return undefined;
    const runs = [];
    let column = 0;
    for (const run of source) {
      const decoded = overviewRun(run, window.width);
      if (!decoded) return undefined;
      if (runs.length && sameOverviewRun(decoded, runs[runs.length - 1])) return undefined;
      if (decoded.kind === "terrain") {
        for (let offset = 0; offset < decoded.length; offset += 1) {
          cells[row * window.width + column + offset] = Object.freeze({
            x: window.min_x + column + offset,
            y: window.min_y + row,
            terrain: decoded.terrain,
            band: decoded.band,
            passable: decoded.passable,
          });
        }
      }
      column += decoded.length;
      runs.push(decoded);
    }
    if (column !== window.width) return undefined;
    rows.push(Object.freeze(runs));
  }
  return Object.freeze({
    key: value.key,
    nameZh: value.name_zh,
    cellKm,
    origin: Object.freeze({ x: window.min_x, y: window.min_y }),
    width: window.width,
    height: window.height,
    rows: Object.freeze(rows),
    cells: Object.freeze(cells),
  });
}

// The district of a schema-4 wilderness body: null, a decoded overview, or
// undefined when the body is not a schema-4 wilderness body it can lay out.
function districtOf(area) {
  if (!plain(area) || area.layer !== "wilderness" || area.schema_version !== WILDERNESS_GRID_SCHEMA) return undefined;
  if (!Object.prototype.hasOwnProperty.call(area, "district")) return undefined;
  return decodeOverviewValue(area.district);
}

function decode(area) {
  if (!plain(area) || area.layer !== "wilderness" || area.schema_version !== WILDERNESS_GRID_SCHEMA) return null;
  if (districtOf(area) === undefined) return null;
  const window = area.window;
  if (!plain(window) || !Array.isArray(area.rows)) return null;
  const { min_x: minX, min_y: minY, width, height } = window;
  if (!Number.isInteger(minX) || !Number.isInteger(minY) || !count(width, 4096) || !count(height, 4096)) return null;
  if (area.rows.length !== height) return null;
  const cells = new Array(width * height).fill(null);
  for (let row = 0; row < height; row += 1) {
    const runs = area.rows[row];
    if (!Array.isArray(runs)) return null;
    let column = 0;
    for (const run of runs) {
      if (!plain(run) || !count(run.length, width) || column + run.length > width) return null;
      if (run.kind === "unknown") {
        if (!keysAre(run, UNKNOWN_KEYS)) return null;
      } else if (run.kind === "terrain") {
        if (!keysAre(run, TERRAIN_KEYS) || !keysAre(run.display, DISPLAY_KEYS)) return null;
        const display = Object.freeze({ ...run.display });
        for (let offset = 0; offset < run.length; offset += 1) {
          const x = minX + column + offset;
          const y = minY + row;
          cells[row * width + column + offset] = Object.freeze({
            x,
            y,
            terrain: run.terrain,
            passable: run.passable,
            band: run.band,
            tier: run.tier,
            road: run.road,
            ford: run.ford,
            display,
          });
        }
      } else {
        return null;
      }
      column += run.length;
    }
    if (column !== width) return null;
  }
  return Object.freeze({
    origin: Object.freeze({ x: minX, y: minY }),
    width,
    height,
    cells: Object.freeze(cells),
  });
}

/**
 * The decoded grid of a wilderness area_map body, or null when the body is
 * not a schema-3 wilderness window it can lay out exactly. Cached per body.
 */
export function decodeWildernessGrid(area) {
  if (!plain(area)) return null;
  if (cache.has(area)) return cache.get(area);
  const grid = decode(area);
  cache.set(area, grid);
  return grid;
}

/**
 * The decoded coarse overview of a schema-4 wilderness body, or null when the
 * body carries none (or is not one this decoder can lay out exactly). Cached
 * per body.
 */
export function decodeDistrictOverview(area) {
  if (!plain(area)) return null;
  if (overviewCache.has(area)) return overviewCache.get(area);
  const district = districtOf(area);
  const overview = district === undefined ? null : district;
  overviewCache.set(area, overview);
  return overview;
}

/** The decoded cell at map coordinates `(x, y)`: a cell, null (unknown) or undefined outside the window. */
export function wildernessCellAt(grid, x, y) {
  if (!grid) return undefined;
  const col = x - grid.origin.x;
  const row = y - grid.origin.y;
  if (col < 0 || row < 0 || col >= grid.width || row >= grid.height) return undefined;
  return grid.cells[row * grid.width + col];
}
