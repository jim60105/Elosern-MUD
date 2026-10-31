// The one wilderness window decoder (OpenSpec change
// wilderness-travel-window-ui, design "Shared decoder cutover").
// Dependency-light ES module: no Vue, no DOM.
//
// `decodeWildernessGrid(area)` turns a schema-3 wilderness `area_map` body
// into its decoded cell grid. Both map consumers read it: the drawer's
// `area_map_view.decodeWindow` and the travel stage's
// `travel-grid.decodeTravelGrid`, so they share coordinates and rejection.
//
// The store validates every body against the exact wire schema before it is
// committed (protocol/panels/map_panels.js). The decoder still refuses any
// body whose rows it cannot lay out exactly — a non-wilderness or older
// schema (node-form wilderness included), a row count or run total other
// than the window's, an unknown run with any extra key, a revealed run
// without its exact fields — and returns null rather than guessing.
//
// `cells` is row-major and south-to-north: index `row * width + col` is the
// cell at `(origin.x + col, origin.y + row)`; row 0 is the window's southern
// edge (map y grows northward). An unknown cell is `null`: it carries no
// fact at all.

/** The wilderness area_map schema this decoder reads. */
export const WILDERNESS_GRID_SCHEMA = 3;

const UNKNOWN_KEYS = ["kind", "length"];
const TERRAIN_KEYS = ["band", "display", "ford", "kind", "length", "passable", "road", "terrain", "tier"];
const DISPLAY_KEYS = ["district_key", "district_name", "ford_label", "settlement", "terrain_label"];

const cache = new WeakMap();

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

function decode(area) {
  if (!plain(area) || area.layer !== "wilderness" || area.schema_version !== WILDERNESS_GRID_SCHEMA) return null;
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

/** The decoded cell at map coordinates `(x, y)`: a cell, null (unknown) or undefined outside the window. */
export function wildernessCellAt(grid, x, y) {
  if (!grid) return undefined;
  const col = x - grid.origin.x;
  const row = y - grid.origin.y;
  if (col < 0 || row < 0 || col >= grid.width || row >= grid.height) return undefined;
  return grid.cells[row * grid.width + col];
}
