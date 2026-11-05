// The travel stage's cell grid (OpenSpec changes wilderness-travel-interface
// and wilderness-travel-window-ui). Dependency-light ES module: no Vue, no
// DOM.
//
// `decodeTravelGrid(area)` turns one validated schema-4 wilderness
// `area_map` body into the grid the travel stage paints from. The rows come
// from the one shared decoder (lib/wilderness-grid.js, the drawer's too), so
// both maps lay out and refuse a window identically; the base design's
// temporary adapter is gone.
//
// Nothing here is guessed. A cell is `known` only where the window carries a
// revealed run, and its terrain, band, tier, flags and display annotation are
// that run's; an unknown cell carries no fact at all. The light phase, the
// ground radius, the live-sight entities and the distant sightings are the
// committed window's own, passed through unchanged: the browser computes no
// phase from the hour and no radius from the terrain. A node keeps its
// payload object verbatim (its id, action, gateway and landmark included).

import { decodeDistrictOverview, decodeWildernessGrid } from "./wilderness-grid.js";

/** The cell coordinates `{ x, y }` a payload node stands in. */
function nodeCell(area, node) {
  return { x: Math.floor(node.x / area.cell_km), y: Math.floor(node.y / area.cell_km) };
}

function unknownCell(x, y, node) {
  return Object.freeze({ x, y, known: false, terrain: null, band: null, tier: null, road: false, ford: false, node, display: null });
}

/**
 * The travel grid of an available wilderness area_map body, else null.
 *
 * `cells` is row-major and south-to-north: index `row * width + col` is the
 * cell at `(origin.x + col, origin.y + row)`, and row 0 is the window's
 * southern edge (map y grows northward). `party` is the committed current
 * node's cell.
 */
export function decodeTravelGrid(area) {
  if (!area || area.available !== true || area.layer !== "wilderness") return null;
  const window = decodeWildernessGrid(area);
  if (!window || !Array.isArray(area.nodes) || !Array.isArray(area.entities) || !Array.isArray(area.sightings)) return null;
  const current = area.nodes.find((node) => node.id === area.current_node);
  if (!current) return null;
  const nodes = new Map();
  for (const node of area.nodes) {
    const { x, y } = nodeCell(area, node);
    const key = `${x}:${y}`;
    // A gateway shares its approach cell with nothing else; the first
    // payload node on a cell keeps it (payload order is the server's).
    if (!nodes.has(key)) nodes.set(key, node);
  }
  const { origin, width, height } = window;
  const cells = window.cells.map((cell, index) => {
    const x = origin.x + (index % width);
    const y = origin.y + Math.floor(index / width);
    const node = nodes.get(`${x}:${y}`) ?? null;
    if (!cell) return unknownCell(x, y, node);
    return Object.freeze({
      x,
      y,
      known: true,
      terrain: cell.terrain,
      band: cell.band,
      tier: cell.tier,
      road: cell.road,
      ford: cell.ford,
      node,
      display: cell.display,
    });
  });
  return Object.freeze({
    mapId: area.map_id,
    title: area.title,
    frame: area.frame,
    // The body-level district caption (the current cell's district, else
    // its region): the place card's fallback where no district is disclosed.
    districtName: area.district_name,
    // Kilometres per cell (the stage's scale bar; wilderness-travel-map-ui).
    cellKm: area.cell_km,
    currentNode: area.current_node,
    origin,
    width,
    height,
    cells: Object.freeze(cells),
    party: Object.freeze(nodeCell(area, current)),
    lightPhase: area.light_phase,
    groundRadius: area.ground_radius,
    // The current lit district's coarse overview (or null): the stage paints
    // it behind the fine window, clipped out of the fine-window rectangle.
    district: decodeDistrictOverview(area),
    entities: Object.freeze(area.entities.map((entity) => Object.freeze({ ...entity, cell: Object.freeze({ ...entity.cell }) }))),
    sightings: Object.freeze(area.sightings.map((sighting) => Object.freeze({ ...sighting }))),
  });
}

/** The grid cell at map coordinates `(x, y)`, or null outside the window. */
export function travelCellAt(grid, x, y) {
  if (!grid) return null;
  const col = x - grid.origin.x;
  const row = y - grid.origin.y;
  if (col < 0 || row < 0 || col >= grid.width || row >= grid.height) return null;
  return grid.cells[row * grid.width + col];
}
