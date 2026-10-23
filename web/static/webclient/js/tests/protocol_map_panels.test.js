/*
 * On-demand map panel protocol (define-map-panel-protocol): exact area/world
 * schemas, separate epoch-scoped map storage, and bounded atomic part
 * assembly in the production decoder/store.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { serverTime, validStatusPanel } = require("./protocol_support.js");
const F = require("./map_panel_fixtures.js");

const EPOCH = "m".repeat(22);
const TRANSFER_A = "A".repeat(22);
const TRANSFER_B = "B".repeat(22);
const TRANSFER_C = "C".repeat(22);

function envelope(revision, panels, extra) {
  return Object.assign(
    {
      protocol_version: 1,
      presentation_epoch: EPOCH,
      revision,
      mode: "exploration",
      panels,
      layout_version: 1,
      server_time: serverTime(),
    },
    extra || {}
  );
}

function activeStore() {
  const store = Protocol.createStore();
  store.beginTransport(1);
  const result = store.receive(1, "ui_snapshot", [envelope(1, { status: validStatusPanel() })], {});
  assert.equal(result.accepted, true);
  return store;
}

function sendParts(store, revision, panel, parts, extra) {
  return parts.map((part) => store.receive(1, "ui_update", [envelope(revision, { [panel]: part }, extra)], {}));
}

function rejects(fn) {
  assert.throws(fn, Error);
}

// ---------------------------------------------------------------------------
// Exact schemas.
// ---------------------------------------------------------------------------

test("each area layer validates its exact frame and coordinate form", () => {
  assert.deepEqual(Protocol.validateAreaMapPanel(F.gridArea()), F.gridArea());
  assert.deepEqual(Protocol.validateAreaMapPanel(F.interiorArea()), F.interiorArea());
  const wild = F.wildernessArea();
  assert.equal(Protocol.validateAreaMapPanel(wild).nodes.length, 225);
});

test("coordinate frames are not interchangeable between layers", () => {
  // A grid frame declares metres; a room-graph frame has no coordinates.
  rejects(() => Protocol.validateAreaMapPanel(F.gridArea({ frame: { key: F.MAP, unit: "km" } })));
  rejects(() => Protocol.validateAreaMapPanel(F.gridArea({ frame: { key: "t_other", unit: "m" } })));
  const withXY = F.interiorArea();
  withXY.nodes[0] = Object.assign({}, withXY.nodes[0], { x: 0, y: 0 });
  rejects(() => Protocol.validateAreaMapPanel(withXY));
  rejects(() => Protocol.validateAreaMapPanel(F.wildernessArea({ map_id: "t_map", frame: { key: "t_map", unit: "km" } })));
  // A grid node from another map cannot inherit this frame.
  const foreign = F.gridArea();
  foreign.nodes[2] = F.gridNode(2, 1, { id: "grid:t_other:2:1" });
  rejects(() => Protocol.validateAreaMapPanel(foreign));
  // Grid metres are integers; wilderness km may be fractional cell centres.
  const fractional = F.gridArea();
  fractional.nodes[0] = Object.assign({}, fractional.nodes[0], { x: 10.5 });
  rejects(() => Protocol.validateAreaMapPanel(fractional));
});

test("malformed or secretly enriched area records are rejected", () => {
  const extraNode = F.gridArea();
  extraNode.nodes[1] = Object.assign({}, extraNode.nodes[1], { secret: "x" });
  rejects(() => Protocol.validateAreaMapPanel(extraNode));
  rejects(() => Protocol.validateAreaMapPanel(F.gridArea({ legend: [] })));
  const boolCoord = F.gridArea();
  boolCoord.nodes[1] = Object.assign({}, boolCoord.nodes[1], { x: true });
  rejects(() => Protocol.validateAreaMapPanel(boolCoord));
  const both = F.gridArea();
  both.quest_markers[0] = Object.assign({}, both.quest_markers[0], {
    destination: { kind: "node", node_id: `grid:${F.MAP}:1:2`, bearing_deg: 1 },
  });
  rejects(() => Protocol.validateAreaMapPanel(both));
  const gateway = F.gridArea();
  gateway.nodes[2] = Object.assign({}, gateway.nodes[2], { gateway: { leads_to: "x", z: 1 } });
  rejects(() => Protocol.validateAreaMapPanel(gateway));
  const twoCurrent = F.gridArea();
  twoCurrent.nodes[1] = Object.assign({}, twoCurrent.nodes[1], { visibility: "current" });
  rejects(() => Protocol.validateAreaMapPanel(twoCurrent));
});

test("world districts and markers expose only their precision", () => {
  assert.deepEqual(Protocol.validateWorldMapPanel(F.worldMap()), F.worldMap());
  const enrichedDark = F.worldMap();
  enrichedDark.districts[0] = Object.assign({}, enrichedDark.districts[0], { name: "秘密" });
  rejects(() => Protocol.validateWorldMapPanel(enrichedDark));
  const stringLit = F.worldMap();
  stringLit.districts[0] = Object.assign({}, stringLit.districts[0], { lit: "false" });
  rejects(() => Protocol.validateWorldMapPanel(stringLit));
  const leaky = F.worldMap();
  leaky.quest_markers[1] = Object.assign({}, leaky.quest_markers[1], { node_id: "room:5" });
  rejects(() => Protocol.validateWorldMapPanel(leaky));
  const offGrid = F.worldMap();
  offGrid.quest_markers[1] = Object.assign({}, offGrid.quest_markers[1], { x: 651 });
  rejects(() => Protocol.validateWorldMapPanel(offGrid));
  const landmarkNode = F.worldMap();
  landmarkNode.districts[1] = Object.assign({}, landmarkNode.districts[1], {
    landmark: { name: "塔", x: 1, y: 1, node_id: "room:5" },
  });
  rejects(() => Protocol.validateWorldMapPanel(landmarkNode));
});

test("world geometry, winding and trail encoding are exact", () => {
  const open = F.worldMap();
  open.common.coastline = open.common.coastline.slice(0, -1);
  rejects(() => Protocol.validateWorldMapPanel(open));
  const holesOnly = F.worldMap();
  holesOnly.districts[0] = { id: "t_dark", lit: false, outline: [F.hole(0, 0, 10)] };
  rejects(() => Protocol.validateWorldMapPanel(holesOnly));
  const overlap = F.worldMap({ trail: { resolution_km: 1, rows: [[3, [[0, 3], [2, 1]]]] } });
  rejects(() => Protocol.validateWorldMapPanel(overlap));
  const unsorted = F.worldMap({ trail: { resolution_km: 1, rows: [[4, [[0, 1]]], [3, [[0, 1]]]] } });
  rejects(() => Protocol.validateWorldMapPanel(unsorted));
  const coarse = F.worldMap({ trail: { resolution_km: 5, rows: [[539, [[539, 1]]]] } });
  assert.equal(Protocol.validateWorldMapPanel(coarse).trail.resolution_km, 5);
  rejects(() => Protocol.validateWorldMapPanel(F.worldMap({ trail: { resolution_km: 5, rows: [[540, [[0, 1]]]] } })));
  rejects(() => Protocol.validateWorldMapPanel(F.worldMap({ trail: { resolution_km: 2, rows: [] } })));
  const unknownNation = F.worldMap();
  unknownNation.districts[1] = Object.assign({}, unknownNation.districts[1], { nations: ["t_none"] });
  rejects(() => Protocol.validateWorldMapPanel(unknownNation));
});

// ---------------------------------------------------------------------------
// Envelope placement.
// ---------------------------------------------------------------------------

test("an eager snapshot never carries a map panel", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);
  const result = store.receive(
    1,
    "ui_snapshot",
    [envelope(1, { status: validStatusPanel(), area_map: F.gridArea() })],
    {}
  );
  assert.equal(result.accepted, false);
  assert.equal(result.reason, "invalid");
});

test("a single-frame map update lands in the separate map slot", () => {
  const store = activeStore();
  const result = store.receive(1, "ui_update", [envelope(2, { area_map: F.gridArea() })], {});
  assert.equal(result.accepted, true);
  const state = store.getState();
  assert.deepEqual(state.maps.area_map, F.gridArea());
  assert.equal(Object.prototype.hasOwnProperty.call(state.panels, "area_map"), false);
  const unavailable = {
    schema_version: 1,
    available: false,
    reason: { code: "map_unavailable", message: "地圖目前無法顯示" },
  };
  assert.equal(store.receive(1, "ui_update", [envelope(3, { world_map: unavailable })], {}).accepted, true);
  assert.deepEqual(store.getState().maps.world_map, unavailable);
});

// ---------------------------------------------------------------------------
// On-demand storage and epochs.
// ---------------------------------------------------------------------------

test("same-epoch eager refreshes retain maps; a new epoch clears them", () => {
  const store = activeStore();
  store.receive(1, "ui_update", [envelope(2, { area_map: F.gridArea() })], {});
  // An eager update and a same-epoch full snapshot keep the map unchanged.
  assert.equal(store.receive(1, "ui_update", [envelope(3, { status: validStatusPanel() })], {}).accepted, true);
  assert.equal(store.receive(1, "ui_snapshot", [envelope(4, { status: validStatusPanel() })], {}).accepted, true);
  assert.deepEqual(store.getState().maps.area_map, F.gridArea());
  // A no-puppet detachment and a new transport generation clear both stores.
  store.receive(1, "ui_protocol_error", [
    { protocol_version: 1, code: "no_puppet", message: "沒有角色", reload_required: false },
  ], {});
  assert.deepEqual(store.getState().maps, {});
  const fresh = activeStore();
  fresh.receive(1, "ui_update", [envelope(2, { area_map: F.gridArea() })], {});
  fresh.beginTransport(2);
  assert.deepEqual(fresh.getState().maps, {});
});

// ---------------------------------------------------------------------------
// Bounded part assembly.
// ---------------------------------------------------------------------------

test("a complete transfer is adopted atomically, metadata included", () => {
  const store = activeStore();
  const body = F.wildernessArea();
  const parts = F.encodeParts(body, TRANSFER_A);
  assert.ok(parts.length > 1);
  let notified = 0;
  store.subscribe(() => notified++);
  const results = sendParts(store, 2, "area_map", parts, { mode: "combat" });
  results.slice(0, -1).forEach((result) => assert.equal(result.partial, true));
  assert.equal(results[results.length - 1].accepted, true);
  assert.equal(notified, 1);
  const state = store.getState();
  assert.deepEqual(state.maps.area_map, body);
  assert.equal(state.revision, 2);
  assert.equal(state.mode, "combat");
  assert.deepEqual(store.mapAssemblyStats(), { live: 0, bytes: 0 });
});

test("a missing part leaves nothing visible", () => {
  const store = activeStore();
  const parts = F.encodeParts(F.wildernessArea(), TRANSFER_A);
  sendParts(store, 2, "area_map", parts.slice(0, -1), { mode: "combat" });
  const state = store.getState();
  assert.deepEqual(state.maps, {});
  assert.equal(state.revision, 1);
  assert.equal(state.mode, "exploration");
  assert.equal(store.mapAssemblyStats().live, 1);
});

test("duplicate, conflicting and replayed parts never adopt mixed state", () => {
  const store = activeStore();
  const parts = F.encodeParts(F.wildernessArea(), TRANSFER_A);
  sendParts(store, 2, "area_map", [parts[0]]);
  // An identical duplicate is dropped without disturbing the assembly.
  assert.equal(sendParts(store, 2, "area_map", [parts[0]])[0].reason, "duplicate_part");
  assert.equal(store.mapAssemblyStats().live, 1);
  // Conflicting metadata on the same transfer discards it.
  assert.equal(sendParts(store, 2, "area_map", [parts[1]], { mode: "combat" })[0].reason, "conflicting_part");
  assert.equal(store.mapAssemblyStats().live, 0);
  // Its remaining parts can never reopen it.
  assert.equal(sendParts(store, 2, "area_map", [parts[2]])[0].reason, "finished_transfer");
  assert.deepEqual(store.getState().maps, {});
  // After a completed transfer, a replayed part is stale.
  const fresh = F.encodeParts(F.wildernessArea(), TRANSFER_B);
  sendParts(store, 3, "area_map", fresh);
  assert.ok(store.getState().maps.area_map);
  assert.equal(sendParts(store, 3, "area_map", [fresh[0]])[0].reason, "not_newer");
});

test("a newer transfer retires an older one; a stray older one is ignored", () => {
  const store = activeStore();
  const older = F.encodeParts(F.wildernessArea({ title: "舊地圖" }), TRANSFER_A);
  const newer = F.encodeParts(F.wildernessArea({ title: "新地圖" }), TRANSFER_B);
  sendParts(store, 2, "area_map", older.slice(0, 2));
  sendParts(store, 3, "area_map", newer.slice(0, 1));
  // A same-or-lower-revision frame of another transfer never disturbs the live one.
  assert.equal(
    sendParts(store, 3, "area_map", F.encodeParts(F.wildernessArea(), TRANSFER_C).slice(0, 1))[0].reason,
    "superseded_transfer"
  );
  assert.equal(sendParts(store, 2, "area_map", older.slice(2, 3))[0].reason, "finished_transfer");
  sendParts(store, 3, "area_map", newer.slice(1));
  assert.equal(store.getState().maps.area_map.title, "新地圖");
});

test("an interleaved newer eager update makes an unfinished transfer stale", () => {
  const store = activeStore();
  const parts = F.encodeParts(F.wildernessArea(), TRANSFER_A);
  sendParts(store, 2, "area_map", parts.slice(0, 1));
  assert.equal(store.receive(1, "ui_update", [envelope(3, { status: validStatusPanel() })], {}).accepted, true);
  assert.equal(store.mapAssemblyStats().live, 0);
  assert.equal(sendParts(store, 2, "area_map", parts.slice(1, 2))[0].reason, "not_newer");
  assert.deepEqual(store.getState().maps, {});
});

test("malformed chunks, counts and bodies are rejected", () => {
  const store = activeStore();
  const parts = F.encodeParts(F.wildernessArea(), TRANSFER_A);
  const bad = (mutate) => {
    const value = JSON.parse(JSON.stringify(parts[0]));
    mutate(value.part);
    return sendParts(store, 2, "area_map", [value])[0];
  };
  assert.equal(bad((p) => { p.chunk = p.chunk.slice(0, -4); }).accepted, false);
  assert.equal(bad((p) => { p.chunk = p.chunk.replace(/.$/, "*"); }).accepted, false);
  assert.equal(bad((p) => { p.count += 1; }).accepted, false);
  assert.equal(bad((p) => { p.byte_length = Protocol.MAP_MAX_BYTES.area_map + 1; p.count = Math.ceil(p.byte_length / 1536); }).accepted, false);
  assert.equal(bad((p) => { p.index = p.count; }).accepted, false);
  assert.equal(bad((p) => { p.extra = 1; }).accepted, false);
  // A part frame carries exactly one panel.
  const mixed = store.receive(1, "ui_update", [envelope(2, { area_map: parts[0], status: validStatusPanel() })], {});
  assert.equal(mixed.accepted, false);
  // A body that decodes but violates the schema is never adopted.
  const invalid = F.encodeParts(Object.assign(F.gridArea(), { secret: 1 }), TRANSFER_B);
  const outcome = sendParts(store, 2, "area_map", invalid);
  assert.equal(outcome[outcome.length - 1].reason, "invalid_body");
  // Bytes that are not UTF-8 are never adopted.
  const raw = Buffer.from([0x7b, 0xff, 0x7d]);
  const notUtf8 = {
    schema_version: 1,
    available: true,
    part: { transfer_id: TRANSFER_C, index: 0, count: 1, byte_length: 3, chunk: raw.toString("base64") },
  };
  assert.equal(sendParts(store, 3, "area_map", [notUtf8])[0].reason, "invalid_body");
  assert.deepEqual(store.getState().maps, {});
});

test("a multi-byte character straddling a part boundary decodes intact", () => {
  const store = activeStore();
  const canonical = require("../elosern/protocol/core.js").canonicalJson;
  let body = null;
  // Grow an ASCII pad until byte 1536 is a UTF-8 continuation byte, i.e. a
  // three-byte character is split across the first two parts.
  for (let pad = 0; pad < 60 && body === null; pad++) {
    // Keys serialize sorted, so the pad goes into the first node's label,
    // which precedes every long label.
    const candidate = F.gridArea();
    candidate.nodes[0] = Object.assign({}, candidate.nodes[0], { label: "合成街角" + "x".repeat(pad) });
    candidate.nodes = candidate.nodes.concat(
      Array.from({ length: 6 }, (_, i) => F.gridNode(10 + i, 10, { label: "長".repeat(250) }))
    );
    const raw = Buffer.from(canonical(candidate), "utf8");
    if (raw.length > 1536 && (raw[1536] & 0xc0) === 0x80) body = candidate;
  }
  assert.ok(body, "a straddling layout exists");
  const parts = F.encodeParts(body, TRANSFER_A);
  assert.ok(parts.length >= 2);
  sendParts(store, 2, "area_map", parts);
  assert.deepEqual(store.getState().maps.area_map, body);
});

test("chunk size sits exactly at the generic string ceiling", () => {
  assert.equal(Protocol.MAP_PART_CHUNK_CHARS, Protocol.MAX_STRING_CODE_POINTS);
  assert.equal(Protocol.MAP_PART_RAW_BYTES * 4 / 3, Protocol.MAP_PART_CHUNK_CHARS);
  assert.equal(Protocol.maxMapParts("world_map"), Math.ceil(Protocol.MAP_MAX_BYTES.world_map / 1536));
});
