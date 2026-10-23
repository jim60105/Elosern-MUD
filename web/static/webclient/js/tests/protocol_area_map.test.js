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
  assert.ok(C.WILDERNESS_MAX_NODES < C.AREA_MAX_NODES);
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
    mode: "exploration",
    panels,
    layout_version: 1,
    server_time: serverTime(),
  });
  assert.equal(store.receive(1, "ui_snapshot", [frame(1, { status: validStatusPanel() })], {}).accepted, true);
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
  assert.equal(wild.nodes.length, C.WILDERNESS_MAX_NODES);
  assert.equal(accepts(wild), true);
  wild.nodes.push(Object.assign({}, wild.nodes[0], { id: "wild:elosern:99:99", x: 99.5, y: 99.5 }));
  assert.equal(accepts(wild), false);
});
