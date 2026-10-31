/*
 * The published area_map panel (publish-area-map-panel) in the browser
 * validator: the measured node/edge/byte ceilings, large valid graphs that
 * travel as parts, malformed move actions, and no fabricated coordinates on
 * coordinate-free layers. Fixtures are synthetic (t_-keyed); no shipped lore.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { serverTime, validStatusPanel } = require("./protocol_support.js");
const F = require("./map_panel_fixtures.js");

const C = Protocol.MAP_CONSTANTS;
const EPOCH = "a".repeat(22);
const TRANSFER = "T".repeat(22);

function accepts(payload) {
  try {
    Protocol.validateMapPanel("area_map", payload);
    return true;
  } catch (_) {
    return false;
  }
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

// A synthetic grid graph with `count` nodes on a metre lattice and a ring of
// roads plus chords up to `edges`.
function largeGrid(count, edges) {
  const id = (i) => `grid:${F.MAP}:${(i % 32) * 137}:${Math.floor(i / 32) * 211}`;
  const nodes = [];
  for (let i = 0; i < count; i++) {
    nodes.push({
      id: id(i),
      label: "合".repeat(16),
      x: (i % 32) * 137,
      y: Math.floor(i / 32) * 211,
      visibility: i === 0 ? "current" : i % 2 ? "visited" : "seen",
      gateway: i % 97 === 0 ? { leads_to: "合成荒野" } : null,
      action: i > 0 && i < 9 ? { kind: "move", exit_ref: String(100000 + i), destination: id(i) } : null,
    });
  }
  const pairs = new Set();
  const list = [];
  for (let step = 1; list.length < edges; step++) {
    for (let i = 0; i < count && list.length < edges; i++) {
      const j = (i + step) % count;
      const key = `${Math.min(i, j)}-${Math.max(i, j)}`;
      if (i === j || pairs.has(key)) continue;
      pairs.add(key);
      list.push({ source: id(Math.min(i, j)), destination: id(Math.max(i, j)) });
    }
  }
  return F.gridArea({ current_node: id(0), nodes, edges: list, quest_markers: [] });
}

test("the measured area ceilings are finite and mirrored", () => {
  assert.equal(C.AREA_MAX_NODES, 512);
  assert.equal(C.AREA_MAX_EDGES, 2048);
  assert.equal(C.AREA_MAX_BYTES, 393216);
  assert.equal(Protocol.MAP_MAX_BYTES.area_map, C.AREA_MAX_BYTES);
  // The wilderness window has its own exact caps (wilderness-area-map-reveal).
  assert.equal(C.WILDERNESS_WINDOW, 41);
  assert.equal(C.WILDERNESS_MAX_NODES, 41 * 41);
  assert.equal(C.WILDERNESS_MAX_ENTITIES, 4096);
  assert.equal(C.WILDERNESS_MAX_SIGHTINGS, 256);
});

test("the largest supported graph validates and is never truncated", () => {
  const body = largeGrid(C.AREA_MAX_NODES, C.AREA_MAX_EDGES);
  const normalized = Protocol.validateMapPanel("area_map", body);
  assert.equal(normalized.nodes.length, C.AREA_MAX_NODES);
  assert.equal(normalized.edges.length, C.AREA_MAX_EDGES);
  assert.equal(accepts(largeGrid(C.AREA_MAX_NODES + 1, 10)), false);
  assert.equal(accepts(largeGrid(128, C.AREA_MAX_EDGES + 1)), false);
});

test("a large area map arrives whole through bounded parts", () => {
  const body = largeGrid(C.AREA_MAX_NODES, C.AREA_MAX_EDGES);
  const parts = F.encodeParts(body, TRANSFER);
  assert.ok(parts.length > 1);
  const store = Protocol.createStore();
  store.beginTransport(1);
  const frame = (revision, panels) => ({
    protocol_version: 1,
    presentation_epoch: EPOCH,
    revision,
    base_revision: revision - 1,
    removed_panels: [],
    mode: "exploration",
    panels,
    layout_version: 1,
    server_time: serverTime(),
  });
  const snapshot = (revision, panels) => {
    const value = frame(revision, panels);
    delete value.base_revision;
    delete value.removed_panels;
    return value;
  };
  assert.equal(store.receive(1, "ui_snapshot", [snapshot(1, { status: validStatusPanel() })], {}).accepted, true);
  for (const part of parts) {
    store.receive(1, "ui_update", [frame(2, { area_map: part })], {});
  }
  assert.deepEqual(store.getState().maps.area_map, Protocol.validateMapPanel("area_map", body));
});

test("malformed move actions are rejected", () => {
  const cases = [
    (a) => (a.nodes[1].action = { kind: "teleport", exit_ref: "1", destination: a.nodes[1].id }),
    (a) => (a.nodes[1].action = { kind: "move", exit_ref: "", destination: a.nodes[1].id }),
    (a) => (a.nodes[1].action = { kind: "move", exit_ref: "東門", destination: a.nodes[1].id }),
    (a) => (a.nodes[1].action = { kind: "move", exit_ref: "1", destination: "north" }),
    (a) => (a.nodes[1].action = { kind: "move", exit_ref: "1", destination: a.nodes[1].id, cost: 1 }),
    (a) => (a.nodes[1].action = { kind: "move", exit_ref: "1" }),
    (a) => (a.nodes[1].action = "move"),
  ];
  for (const mutate of cases) {
    const area = clone(F.gridArea());
    mutate(area);
    assert.equal(accepts(area), false, JSON.stringify(area.nodes[1].action));
  }
  assert.equal(accepts(F.gridArea()), true);
});

test("coordinate-free layers never carry fabricated coordinates", () => {
  const interior = clone(F.interiorArea());
  assert.equal(accepts(interior), true);
  const withXY = clone(interior);
  withXY.nodes[1].x = 0;
  withXY.nodes[1].y = 0;
  assert.equal(accepts(withXY), false);
  const instance = clone(interior);
  instance.layer = "instance";
  instance.map_id = "instance:40";
  instance.frame = { key: "instance:40", unit: "none" };
  assert.equal(accepts(instance), true);
  instance.frame.unit = "m";
  assert.equal(accepts(instance), false);
  const gridNoXY = clone(F.gridArea());
  delete gridNoXY.nodes[1].x;
  assert.equal(accepts(gridNoXY), false);
});

test("room-graph gateway references and the wilderness window are bounded", () => {
  const interior = clone(F.interiorArea());
  interior.nodes.push({ id: "room:43", label: "合成街道", visibility: "seen", gateway: { leads_to: "合成街道" }, action: null });
  interior.edges.push({ source: "room:41", destination: "room:43" });
  assert.equal(accepts(interior), true);
  const wild = clone(F.wildernessArea());
  assert.equal(accepts(wild), true);
  // A node outside the 41-cell window is rejected, not clipped.
  wild.nodes.push(F.wildNode(F.WILD_MIN - 1, F.WILD_C));
  assert.equal(accepts(wild), false);
});

// A fully revealed window whose every cell is a visited node: exactly at the
// node cap, and one more node is rejected.
function fullWindow() {
  const area = clone(F.wildernessArea({ entities: [], sightings: [] }));
  area.rows = F.wildRowsFor(() => ({ terrain: "open_ground", passable: true, band: 1, tier: 0, road: false, ford: false }));
  area.nodes = [];
  for (let y = F.WILD_MIN; y < F.WILD_MIN + 41; y++) {
    for (let x = F.WILD_MIN; x < F.WILD_MIN + 41; x++) {
      const current = x === F.WILD_C && y === F.WILD_C;
      area.nodes.push(F.wildNode(x, y, { label: "曠", visibility: current ? "current" : "visited", visited: true }));
    }
  }
  area.edges = [];
  return area;
}

test("the wilderness node, entity and sighting caps are exact", () => {
  const full = fullWindow();
  assert.equal(full.nodes.length, C.WILDERNESS_MAX_NODES);
  assert.equal(accepts(full), true);
  const over = clone(full);
  over.nodes.push(F.wildNode(F.WILD_MIN, F.WILD_MIN, { id: "grid:t_map:1:1", gateway: { leads_to: "合成" } }));
  assert.equal(accepts(over), false);
  const sightings = clone(F.wildernessArea());
  sightings.sightings = Array.from({ length: C.WILDERNESS_MAX_SIGHTINGS }, () => sightings.sightings[0]);
  assert.equal(accepts(sightings), true);
  sightings.sightings.push(sightings.sightings[0]);
  assert.equal(accepts(sightings), false);
  const entities = clone(fullWindow());
  entities.ground_radius = 8;
  const cells = [];
  for (let dy = -8; dy <= 8; dy++) for (let dx = -8; dx <= 8; dx++) if (dx * dx + dy * dy <= 8.5 * 8.5) cells.push([dx, dy]);
  entities.entities = [];
  for (let i = 0; i < C.WILDERNESS_MAX_ENTITIES; i++) {
    const [dx, dy] = cells[i % cells.length];
    entities.entities.push({ id: i.toString(16).padStart(16, "0"), cell: { x: F.WILD_C + dx, y: F.WILD_C + dy }, kind: "hostile", hostile: true, label: "狼" });
  }
  assert.equal(accepts(entities), true);
  entities.entities.push({ id: "ffffffffffffffff", cell: { x: F.WILD_C, y: F.WILD_C }, kind: "npc", hostile: false, label: "人" });
  assert.equal(accepts(entities), false);
});

test("wilderness rows are exact, merged and frame-bounded", () => {
  const cases = {
    "short row": (a) => (a.rows[0] = [{ length: 40, kind: "unknown" }]),
    "long row": (a) => (a.rows[0] = [{ length: 42, kind: "unknown" }]),
    "40 rows": (a) => a.rows.pop(),
    "zero length": (a) => a.rows[0].unshift({ length: 0, kind: "unknown" }),
    "unmerged unknown": (a) => (a.rows[0] = [{ length: 20, kind: "unknown" }, { length: 21, kind: "unknown" }]),
    "unknown with terrain": (a) => (a.rows[0] = [{ length: 41, kind: "unknown", terrain: "sea" }]),
    "unknown with passable": (a) => (a.rows[0] = [{ length: 41, kind: "unknown", passable: false }]),
    "band 16": (a) => (a.rows[20].find((r) => r.kind === "terrain").band = 16),
    "tier 4": (a) => (a.rows[20].find((r) => r.kind === "terrain").tier = 4),
    "unknown terrain class": (a) => (a.rows[20].find((r) => r.kind === "terrain").terrain = "lava"),
    "string flag": (a) => (a.rows[20].find((r) => r.kind === "terrain").road = "no"),
    "visited flag on a run": (a) => (a.rows[20].find((r) => r.kind === "terrain").visited = true),
    "window 15": (a) => (a.window.width = 15),
    "off-centre window": (a) => (a.window.min_x += 1),
    "node on unknown": (a) => a.nodes.push(F.wildNode(F.WILD_MIN, F.WILD_MIN)),
    "node off its cell": (a) => (a.nodes[1].x += 1),
    "far gateway": (a) => a.nodes.push(F.wildNode(F.WILD_C + 2, F.WILD_C, { id: "grid:t_map:2:2", gateway: { leads_to: "合成鎮" } })),
    "gateway on unknown": (a) => {
      a.rows[21] = [{ length: 41, kind: "unknown" }];
      a.entities = [];
      a.nodes = a.nodes.filter((n) => Math.floor(n.y) !== F.WILD_C + 1);
      a.edges = a.edges.filter((e) => a.nodes.some((n) => n.id === e.destination));
      a.nodes.push(F.wildNode(F.WILD_C + 1, F.WILD_C + 1, { id: "grid:t_map:3:3", gateway: { leads_to: "合成鎮" } }));
    },
    "entity outside sight": (a) => (a.entities[0].cell = { x: F.WILD_C + 5, y: F.WILD_C }),
    "entity on unknown": (a) => (a.entities[0].cell = { x: F.WILD_MIN, y: F.WILD_MIN }),
    "semantic entity id": (a) => (a.entities[0].id = "object:12"),
    "entity kind monster": (a) => (a.entities[0].kind = "monster"),
    "entity extra field": (a) => (a.entities[0].dbref = 1),
    "sighting coordinates": (a) => (a.sightings[0].x = 1),
    "sighting source key": (a) => (a.sightings[0].source_key = "x"),
    "sighting 23 km": (a) => (a.sightings[0].distance_km = 23),
    "sighting free bearing": (a) => (a.sightings[0].bearing = "north"),
    "radius 9": (a) => (a.ground_radius = 9),
    "phase noon": (a) => (a.light_phase = "noon"),
    "schema 1": (a) => (a.schema_version = 1),
  };
  for (const [name, mutate] of Object.entries(cases)) {
    const area = clone(F.wildernessArea());
    mutate(area);
    assert.equal(accepts(area), false, name);
  }
  // The same adjacent gateway on a revealed cell is accepted.
  const gated = clone(F.wildernessArea());
  gated.nodes = gated.nodes.filter((n) => n.id !== `wild:elosern:${F.WILD_C + 1}:${F.WILD_C + 1}`);
  gated.edges = gated.edges.filter((e) => e.destination !== `wild:elosern:${F.WILD_C + 1}:${F.WILD_C + 1}`);
  gated.nodes.push(F.wildNode(F.WILD_C + 1, F.WILD_C + 1, { id: "grid:t_map:3:3", gateway: { leads_to: "合成鎮" } }));
  assert.equal(accepts(gated), true);
  // A window hanging over the frame's west edge keeps negative origins and
  // unknown padding.
  const shift = 110;
  const edge = clone(F.wildernessArea());
  const moveId = (id) => id.replace(/^wild:elosern:(\d+):(\d+)$/, (_, x, y) => `wild:elosern:${x - shift}:${y - shift}`);
  edge.current_node = moveId(edge.current_node);
  edge.window.min_x -= shift;
  edge.window.min_y -= shift;
  assert.ok(edge.window.min_x < 0);
  for (const node of edge.nodes) {
    node.id = moveId(node.id);
    node.x -= shift;
    node.y -= shift;
    if (node.action) node.action.destination = moveId(node.action.destination);
  }
  for (const e of edge.edges) {
    e.source = moveId(e.source);
    e.destination = moveId(e.destination);
  }
  for (const entity of edge.entities) {
    entity.cell.x -= shift;
    entity.cell.y -= shift;
  }
  assert.equal(accepts(edge), true);
});
