/*
 * The scoped world-map frame allowance (transport-world-map-panel): an
 * intact world_map above one generic 64 KB frame is adopted by the production
 * decoder/store, while over-bound world maps, oversized siblings, mixed
 * frames and scalar violations keep failing, and local_map keeps its
 * 65,536-byte envelope.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const core = require("../elosern/protocol/core.js");
const { serverTime, validStatusPanel } = require("./protocol_support.js");
const F = require("./map_panel_fixtures.js");

const EPOCH = "w".repeat(22);
const GENERIC = 65536;

function envelope(revision, panels) {
  return {
    protocol_version: 1,
    presentation_epoch: EPOCH,
    revision,
    mode: "exploration",
    panels,
    layout_version: 1,
    server_time: serverTime(),
  };
}

function activeStore() {
  const store = Protocol.createStore();
  store.beginTransport(1);
  const result = store.receive(1, "ui_snapshot", [envelope(1, { status: validStatusPanel() })], {});
  assert.equal(result.accepted, true);
  return store;
}

// A wire round trip: the store only ever sees JSON-decoded frames.
function wire(value) {
  return JSON.parse(JSON.stringify(value));
}

// Extra 2,000-character fields that make a sibling exceed one generic frame
// on their own (each value stays inside the generic string bound).
function paddedSibling(bytes) {
  const fields = {};
  for (let index = 0; core.jsonByteSize(fields) < bytes; index++) {
    fields["t_pad_" + index] = "x".repeat(2000);
  }
  return fields;
}

test("an intact world map above 64 KB is adopted in one frame", () => {
  const store = activeStore();
  const body = F.largeWorldMap(200000);
  const frame = wire(envelope(2, { world_map: body }));
  assert.ok(core.jsonByteSize(frame) > GENERIC);
  assert.throws(() => core.checkEnvelope(frame));
  const result = store.receive(1, "ui_update", [frame], {});
  assert.deepEqual(result, { accepted: true, revision: 2 });
  const state = store.getState();
  assert.equal(core.canonicalJson(state.maps.world_map), core.canonicalJson(Protocol.validateMapPanel("world_map", body)));
  assert.equal(state.revision, 2);
});

test("map publication marks track logical adoption, never clones or unrelated revisions", () => {
  const store = activeStore();
  assert.deepEqual(store.getState().mapPublications, {});
  store.receive(1, "ui_update", [envelope(2, { world_map: F.worldMap() })], {});
  store.receive(1, "ui_update", [envelope(3, { area_map: F.gridArea() })], {});
  assert.deepEqual(store.getState().mapPublications, { world_map: 2, area_map: 3 });
  const copy = store.getState();
  copy.mapPublications.world_map = 999;
  store.receive(1, "ui_snapshot", [envelope(4, { status: validStatusPanel() })], {});
  assert.deepEqual(store.getState().mapPublications, { world_map: 2, area_map: 3 });
  assert.ok(store.getState().maps.world_map);
  const parts = F.encodeParts(F.largeWorldMap(100000), "P".repeat(22));
  for (const part of parts.slice(0, -1)) {
    assert.equal(store.receive(1, "ui_update", [envelope(5, { world_map: part })], {}).partial, true);
    assert.equal(store.getState().mapPublications.world_map, 2);
  }
  assert.equal(store.receive(1, "ui_update", [envelope(5, { world_map: parts.at(-1) })], {}).accepted, true);
  assert.equal(store.getState().mapPublications.world_map, 5);
  assert.equal(store.receive(1, "ui_update", [envelope(5, { world_map: F.worldMap() })], {}).accepted, false);
  assert.equal(store.getState().mapPublications.world_map, 5);
  store.receive(1, "ui_protocol_error", [{ protocol_version: 1, code: "no_puppet", message: "Detached", reload_required: false }], {});
  assert.deepEqual(store.getState().mapPublications, {});
  store.beginTransport(2);
  assert.deepEqual(store.getState().mapPublications, {});
});

test("a world map above its logical ceiling is rejected and the prior map retained", () => {
  const store = activeStore();
  const small = F.worldMap();
  assert.equal(store.receive(1, "ui_update", [wire(envelope(2, { world_map: small }))], {}).accepted, true);
  const big = F.largeWorldMap(Protocol.MAP_MAX_BYTES.world_map + 1);
  assert.ok(core.jsonByteSize(big) > Protocol.MAP_MAX_BYTES.world_map);
  const result = store.receive(1, "ui_update", [wire(envelope(3, { world_map: big }))], {});
  assert.equal(result.accepted, false);
  assert.equal(result.reason, "invalid");
  assert.equal(core.canonicalJson(store.getState().maps.world_map), core.canonicalJson(small));
  assert.equal(store.getState().revision, 2);
});

test("the world ceiling is exact: at the bound adopts, one byte over rejects", () => {
  const max = Protocol.MAP_MAX_BYTES.world_map;
  const at = F.worldMapOfBytes(max);
  const over = F.worldMapOfBytes(max + 1);
  assert.equal(activeStore().receive(1, "ui_update", [wire(envelope(2, { world_map: at }))], {}).accepted, true);
  assert.equal(activeStore().receive(1, "ui_update", [wire(envelope(2, { world_map: over }))], {}).accepted, false);
});

test("siblings keep the generic frame: an oversized companion is rejected", () => {
  const store = activeStore();
  const frame = envelope(2, { world_map: F.worldMap(), status: Object.assign(validStatusPanel(), paddedSibling(70000)) });
  assert.throws(() => Protocol.checkWorldMapEnvelope(wire(frame)), /canonical JSON exceeds|fields|exceeds/);
  assert.equal(store.receive(1, "ui_update", [wire(frame)], {}).accepted, false);
});

test("an area map beside an intact world map stays inside the generic frame", () => {
  const area = F.gridArea();
  area.nodes = area.nodes.concat(
    Array.from({ length: 400 }, (_, index) =>
      F.gridNode(100 + index, 50, { visibility: "seen", label: "合成街道".repeat(20) })
    )
  );
  const frame = wire(envelope(2, { world_map: F.largeWorldMap(100000), area_map: area }));
  assert.throws(() => Protocol.checkWorldMapEnvelope(frame), /exceeds/);
  assert.equal(activeStore().receive(1, "ui_update", [frame], {}).accepted, false);
});

test("a __proto__ sibling cannot hide from the generic walk", () => {
  const text =
    '{"protocol_version":1,"presentation_epoch":"' + EPOCH + '","revision":2,"mode":"exploration",' +
    '"panels":{"world_map":' + JSON.stringify(F.worldMap()) + ',"__proto__":{"t":"' + "x".repeat(3000) + '"}},' +
    '"layout_version":1,"server_time":' + JSON.stringify(serverTime()) + "}";
  const frame = JSON.parse(text);
  assert.ok(Object.keys(frame.panels).includes("__proto__"));
  assert.throws(() => Protocol.checkWorldMapEnvelope(frame), /string exceeds/);
  assert.equal(activeStore().receive(1, "ui_update", [frame], {}).accepted, false);
});

test("scalar and field rules still apply outside and inside the world map", () => {
  const cases = {
    "boolean revision": (f) => { f.revision = true; },
    "unknown envelope field": (f) => { f.extra = 1; },
    "unsafe integer in a sibling": (f) => { f.panels.status = Object.assign(validStatusPanel(), { t: 2 ** 60 }); },
    "unknown world field": (f) => { f.panels.world_map.secret = 1; },
    "long world string": (f) => { f.panels.world_map.districts[1].name = "名".repeat(3000); },
  };
  for (const [name, mutate] of Object.entries(cases)) {
    const frame = wire(envelope(2, { world_map: F.largeWorldMap(80000), status: validStatusPanel() }));
    mutate(frame);
    assert.equal(activeStore().receive(1, "ui_update", [frame], {}).accepted, false, name);
  }
});

test("the allowance is world-map only: snapshots, parts, area and local maps stay generic", () => {
  const big = F.largeWorldMap(100000);
  assert.equal(Protocol.carriesIntactWorldMap(envelope(2, { world_map: big })), true);
  for (const panels of [{ world_map: Object.assign({ part: {} }, big) }, { world_map: null }, { world_map: [] }, { area_map: F.gridArea() }]) {
    assert.equal(Protocol.carriesIntactWorldMap(envelope(2, panels)), false);
  }
  assert.equal(Protocol.carriesIntactWorldMap(Object.assign(envelope(2, {}), { panels: [] })), false);
  assert.equal(Protocol.carriesIntactWorldMap(Object.assign(envelope(2, {}), { panels: null })), false);
  // A snapshot never takes the allowance (and never carries a map).
  const store = Protocol.createStore();
  store.beginTransport(1);
  assert.equal(store.receive(1, "ui_snapshot", [wire(envelope(1, { world_map: big }))], {}).accepted, false);
  // local_map keeps its 65,536-byte envelope even beside an intact world map.
  const local = { schema_version: 1, available: true, layer: "grid", current_node: "grid:t_map:0:0", title: "t", nodes: [], edges: [], legend: ["x".repeat(2000)] };
  for (let index = 0; index < 40; index++) local["t_pad_" + index] = "y".repeat(2000);
  const frame = wire(envelope(2, { world_map: F.worldMap(), local_map: local }));
  assert.ok(core.jsonByteSize(frame.panels.local_map) > GENERIC);
  assert.throws(() => Protocol.checkWorldMapEnvelope(frame), /canonical JSON exceeds|fields/);
});

test("an intact world map frame is bounded by the generic frame plus the world ceiling", () => {
  assert.equal(Protocol.WORLD_MAP_FRAME_MAX_BYTES, GENERIC + Protocol.MAP_MAX_BYTES.world_map);
  assert.equal(Protocol.MAP_MAX_BYTES.world_map, 2097152);
});

test("the full 5 km checkerboard is retained while 1 km trails keep their cap", () => {
  const body = F.worldMap();
  body.trail = {
    resolution_km: 5,
    rows: Array.from({ length: 540 }, (_, y) => [
      y, Array.from({ length: 270 }, (_, x) => [x * 2, 1]),
    ]),
  };
  const store = activeStore();
  assert.equal(store.receive(1, "ui_update", [wire(envelope(2, { world_map: body }))], {}).accepted, true);
  assert.equal(store.getState().maps.world_map.trail.rows.length, 540);
  assert.deepEqual(store.getState().maps.world_map.trail.rows[539][1][269], [538, 1]);
  body.trail.resolution_km = 1;
  assert.throws(() => Protocol.validateMapPanel("world_map", body), /20000 runs/);
});
