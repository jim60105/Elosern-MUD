// The travel stage's cell grid (OpenSpec change wilderness-travel-interface,
// design "Current-protocol adapter"). Dependency-light ES module: no Vue, no
// DOM.
//
// `decodeTravelGrid(area)` turns one validated wilderness `area_map` body
// into the decoded cell grid the travel stage paints from. It is the
// approved temporary adapter over today's schema-2 run-length window: the
// revealed terrain comes from the drawer's own `decodeWindow`, never from a
// second decoder, and window-ui replaces this module at its schema cutover.
//
// Nothing here is guessed. A cell is `known` only where the window carries a
// revealed terrain run, and its terrain is that run's explicit canonical
// class; no label is parsed into terrain. Elevation band, prominence tier,
// road/ford flags, display metadata, the light phase, the ground radius,
// entities and sightings keep the shape's empty values until window-ui
// supplies them. A node keeps its payload object verbatim (its id, action
// and gateway identity included).

import { decodeWindow } from "./area_map_view.js";

/** The cell coordinates `{ x, y }` a payload node stands in. */
function nodeCell(area, node) {
  return { x: Math.floor(node.x / area.cell_km), y: Math.floor(node.y / area.cell_km) };
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
  if (!area || area.available !== true || area.layer !== "wilderness" || !area.window) return null;
  const current = area.nodes.find((node) => node.id === area.current_node);
  if (!current) return null;
  const { min_x: minX, min_y: minY, width, height } = area.window;
  const revealed = new Map(decodeWindow(area).map((cell) => [cell.key, cell]));
  const nodes = new Map();
  for (const node of area.nodes) {
    const { x, y } = nodeCell(area, node);
    const key = `${x}:${y}`;
    // A gateway shares its approach cell with nothing else; the first
    // payload node on a cell keeps it (payload order is the server's).
    if (!nodes.has(key)) nodes.set(key, node);
  }
  const cells = [];
  for (let row = 0; row < height; row += 1) {
    for (let col = 0; col < width; col += 1) {
      const x = minX + col;
      const y = minY + row;
      const key = `${x}:${y}`;
      const terrain = revealed.get(key)?.terrain ?? null;
      cells.push(
        Object.freeze({
          x,
          y,
          known: terrain !== null,
          terrain,
          band: null,
          tier: null,
          road: false,
          ford: false,
          node: nodes.get(key) ?? null,
          display: null,
        }),
      );
    }
  }
  return Object.freeze({
    mapId: area.map_id,
    frame: area.frame,
    currentNode: area.current_node,
    origin: Object.freeze({ x: minX, y: minY }),
    width,
    height,
    cells: Object.freeze(cells),
    party: Object.freeze(nodeCell(area, current)),
    lightPhase: null,
    groundRadius: null,
    entities: Object.freeze([]),
    sightings: Object.freeze([]),
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
