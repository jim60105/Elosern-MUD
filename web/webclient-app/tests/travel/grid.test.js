// The temporary travel-grid adapter (wilderness-travel-interface, design
// "Current-protocol adapter"): synthetic schema-2 window bodies built here,
// validated by the real wire validator, decoded into the travel grid.

import { describe, expect, it } from "vitest";
import MapPanels from "../../../static/webclient/js/elosern/protocol/panels/map_panels.js";
import { decodeTravelGrid, travelCellAt } from "../../lib/travel-grid.js";

const { validateAreaMapPanel } = MapPanels;
const WINDOW = 41;
const CX = 60;
const CY = 80;
const wild = (x, y) => `wild:elosern:${x}:${y}`;

// One row of the window: `known` maps an x offset to its terrain run facts.
function row(known) {
  const runs = [];
  for (let col = 0; col < WINDOW; col += 1) {
    const facts = known.get(col);
    const run = facts
      ? { length: 1, kind: "terrain", passable: true, band: 4, tier: 1, road: true, ford: false, ...facts }
      : { length: 1, kind: "unknown" };
    const last = runs.at(-1);
    if (last && JSON.stringify({ ...last, length: 0 }) === JSON.stringify({ ...run, length: 0 })) last.length += 1;
    else runs.push(run);
  }
  return runs;
}

// A window centred on (CX, CY): the current cell is open ground, the cell
// north of it woodland, the one south of it hills; a gateway stands north-east
// of the party on a revealed cell. Everything else is unknown.
function body() {
  const minX = CX - 20;
  const minY = CY - 20;
  const rows = [];
  for (let r = 0; r < WINDOW; r += 1) {
    const y = minY + r;
    const known = new Map();
    if (y === CY) known.set(20, { terrain: "open_ground" });
    if (y === CY + 1) {
      known.set(20, { terrain: "woodland" });
      known.set(21, { terrain: "settlement", passable: false });
    }
    if (y === CY - 1) known.set(20, { terrain: "hills" });
    rows.push(row(known));
  }
  const node = (x, y, fields) => ({
    id: wild(x, y), label: "合成荒原", x: x + 0.5, y: y + 0.5,
    visibility: "seen", visited: false, gateway: null, action: null, ...fields,
  });
  const gateAction = { kind: "move", exit_ref: "e_gate", destination: "grid:t_town:1:1" };
  return {
    schema_version: 2,
    available: true,
    layer: "wilderness",
    map_id: "elosern",
    frame: { key: "elosern", unit: "km" },
    current_node: wild(CX, CY),
    title: "合成荒原",
    nodes: [
      node(CX, CY - 1, { action: { kind: "move", exit_ref: "e_s", destination: wild(CX, CY - 1) } }),
      node(CX, CY, { visibility: "current", visited: true }),
      node(CX, CY + 1, {}),
      { id: "grid:t_town:1:1", label: "合成城門", x: CX + 1.5, y: CY + 1.5, visibility: "seen", visited: false,
        gateway: { leads_to: "合成城" }, action: gateAction },
    ],
    edges: [
      { source: wild(CX, CY), destination: wild(CX, CY - 1) },
      { source: wild(CX, CY), destination: "grid:t_town:1:1" },
    ],
    quest_markers: [],
    district_name: "合成東麓",
    cell_km: 1,
    window: { min_x: minX, min_y: minY, width: WINDOW, height: WINDOW },
    rows,
    light_phase: "dusk",
    ground_radius: 3,
    entities: [],
    sightings: [{ bearing: "北", distance_km: 15, silhouette_zh: "合成塔影", name: null }],
  };
}

describe("decodeTravelGrid", () => {
  it("lays the window out row-major from its southern edge northward", () => {
    const grid = decodeTravelGrid(validateAreaMapPanel(body()));
    expect(grid.origin).toEqual({ x: CX - 20, y: CY - 20 });
    expect([grid.width, grid.height]).toEqual([41, 41]);
    expect(grid.cells).toHaveLength(41 * 41);
    // Index (row * width + col) is the cell at (origin.x + col, origin.y + row).
    expect(grid.cells[0]).toMatchObject({ x: CX - 20, y: CY - 20 });
    expect(grid.cells[41]).toMatchObject({ x: CX - 20, y: CY - 19 });
    expect(grid.cells[41 * 41 - 1]).toMatchObject({ x: CX + 20, y: CY + 20 });
    // South of the party is the row below it, north the row above.
    expect(travelCellAt(grid, CX, CY - 1).terrain).toBe("hills");
    expect(travelCellAt(grid, CX, CY + 1).terrain).toBe("woodland");
    expect(grid.party).toEqual({ x: CX, y: CY });
    expect(grid.currentNode).toBe(wild(CX, CY));
    expect([grid.mapId, grid.frame]).toEqual(["elosern", { key: "elosern", unit: "km" }]);
  });

  it("keeps unknown cells unknown and guesses no fact", () => {
    const grid = decodeTravelGrid(validateAreaMapPanel(body()));
    const known = grid.cells.filter((cell) => cell.known);
    expect(known.map((cell) => `${cell.x}:${cell.y}`).sort()).toEqual(
      [`${CX}:${CY}`, `${CX}:${CY + 1}`, `${CX + 1}:${CY + 1}`, `${CX}:${CY - 1}`].sort(),
    );
    const unknown = travelCellAt(grid, CX + 5, CY + 5);
    expect(unknown).toMatchObject({ known: false, terrain: null, node: null });
    // The adapter carries no elevation, flags, phase, sight or sightings even
    // where the window has them; window-ui supplies those.
    for (const cell of known) {
      expect([cell.band, cell.tier, cell.road, cell.ford, cell.display]).toEqual([null, null, false, false, null]);
    }
    expect([grid.lightPhase, grid.groundRadius, grid.entities, grid.sightings]).toEqual([null, null, [], []]);
  });

  it("keeps each node's action and gateway identity verbatim on its own cell", () => {
    const area = validateAreaMapPanel(body());
    const grid = decodeTravelGrid(area);
    const gate = travelCellAt(grid, CX + 1, CY + 1).node;
    expect(gate).toBe(area.nodes.find((node) => node.id === "grid:t_town:1:1"));
    expect(gate.gateway).toEqual({ leads_to: "合成城" });
    expect(gate.action).toEqual({ kind: "move", exit_ref: "e_gate", destination: "grid:t_town:1:1" });
    expect(travelCellAt(grid, CX, CY - 1).node.action.exit_ref).toBe("e_s");
    expect(travelCellAt(grid, CX - 3, CY).node).toBeNull();
  });

  it("reads no terrain from a label: a known cell needs an explicit class", () => {
    const area = validateAreaMapPanel(body());
    // A body whose decoded window revealed nothing has no known terrain at
    // all, whatever its node labels say.
    const blind = { ...area, rows: Array.from({ length: WINDOW }, () => [{ length: WINDOW, kind: "unknown" }]) };
    const grid = decodeTravelGrid(blind);
    expect(grid.cells.every((cell) => cell.known === false && cell.terrain === null)).toBe(true);
    expect(travelCellAt(grid, CX, CY).node.label).toBe("合成荒原");
  });

  it("decodes nothing from a body the travel stage cannot use", () => {
    const area = validateAreaMapPanel(body());
    expect(decodeTravelGrid(null)).toBeNull();
    expect(decodeTravelGrid({ available: false, reason: { code: "x", message: "y" } })).toBeNull();
    expect(decodeTravelGrid({ ...area, layer: "grid" })).toBeNull();
    expect(decodeTravelGrid({ ...area, current_node: wild(0, 0) })).toBeNull();
    expect(travelCellAt(decodeTravelGrid(area), CX + 30, CY)).toBeNull();
  });
});
