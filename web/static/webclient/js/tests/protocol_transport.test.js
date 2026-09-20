/*
 * Transport-generation lifecycle: epochs, revisions, retired-epoch bounds, atomic panel replacement.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { EPOCH_A, EPOCH_B, EPOCH_C, actionResult, connectedStore, nested, protocolError, snapshot, unavailableStatusPanel, update, validStatusPanel } = require("./protocol_support.js");


test("connection_open begins a new generation and locks mutations", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);
  assert.equal(store.getState().phase, "awaiting_initial_snapshot");
  assert.equal(store.getState().mutationsLocked, true);
  assert.deepEqual(store.getState().panels, {});
});

test("only the first valid snapshot of the generation establishes the epoch", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);
  store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_A, revision: 1 })], {});
  assert.equal(store.getState().activeEpoch, EPOCH_A);

  // A different-epoch full snapshot on the same active socket is rejected.
  const result = store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_C, revision: 1 })], {});
  assert.equal(result.accepted, false);
  assert.equal(result.reason, "different_epoch");
  assert.equal(store.getState().activeEpoch, EPOCH_A, "state is retained");
  assert.equal(store.getState().revision, 1);
});

test("ui_update and ui_action_result never establish an epoch", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);
  const updateResult = store.receive(1, "ui_update", [update({ revision: 5 })], {});
  assert.equal(updateResult.accepted, false);
  assert.equal(updateResult.reason, "update_cannot_establish_epoch");

  const resultResult = store.receive(1, "ui_action_result", [actionResult()], {});
  assert.equal(resultResult.accepted, false);
  assert.equal(resultResult.reason, "different_epoch");

  assert.equal(store.getState().phase, "awaiting_initial_snapshot");

  // A later valid snapshot still adopts.
  store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_A, revision: 1 })], {});
  assert.equal(store.getState().activeEpoch, EPOCH_A);
});

test("lower-revision adoption in a new transport generation", () => {
  const store = connectedStore(EPOCH_A, 40);
  assert.equal(store.getState().revision, 40);

  store.beginTransport(2);
  assert.equal(store.getState().activeEpoch, null);
  assert.equal(store.getState().phase, "awaiting_initial_snapshot");

  const result = store.receive(2, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_B, revision: 1 })], {});
  assert.equal(result.accepted, true);
  assert.equal(store.getState().activeEpoch, EPOCH_B);
  assert.equal(store.getState().revision, 1);
});

test("retired epochs and prior receiver generations are discarded", () => {
  const store = connectedStore(EPOCH_A, 40);
  store.beginTransport(2);
  assert.equal(store.getState().retiredEpochCount, 1);

  // A snapshot for the retired epoch is rejected even before adoption.
  let result = store.receive(2, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_A, revision: 99 })], {});
  assert.equal(result.accepted, false);
  assert.equal(result.reason, "retired_epoch");

  store.receive(2, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_B, revision: 1 })], {});

  // A delayed message from the retired epoch is discarded after adoption too.
  result = store.receive(2, "ui_update", [update({ presentation_epoch: EPOCH_A, revision: 50 })], {});
  assert.equal(result.accepted, false);
  assert.equal(result.reason, "different_epoch");
  assert.equal(store.getState().revision, 1);

  // A receiver callback tagged with the older generation is discarded first.
  result = store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_B, revision: 3 })], {});
  assert.equal(result.accepted, false);
  assert.equal(result.reason, "stale_generation");
  assert.equal(store.getState().revision, 1);
});

test("the retired-epoch set is bounded", () => {
  const store = Protocol.createStore();
  for (let gen = 1; gen <= 20; gen++) {
    store.beginTransport(gen);
    store.receive(gen, "ui_snapshot", [snapshot({ presentation_epoch: genLetter(gen), revision: 1 })], {});
  }
  const state = store.getState();
  assert.ok(state.retiredEpochCount <= Protocol.MAX_RETIRED_EPOCHS);
});

function genLetter(gen) {
  const alphabet = "abcdefghijklmnopqrstuvwxyz";
  return alphabet[(gen - 1) % 26].repeat(22);
}

test("same-active-generation different-epoch snapshot is rejected", () => {
  const store = connectedStore(EPOCH_B, 7);
  const result = store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_C, revision: 1 })], {});
  assert.equal(result.accepted, false);
  assert.equal(result.reason, "different_epoch");
  assert.equal(store.getState().activeEpoch, EPOCH_B);
  assert.equal(store.getState().revision, 7);
});

test("non-newer revisions in the active epoch are discarded", () => {
  const store = connectedStore(EPOCH_B, 7);
  assert.equal(store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_B, revision: 7 })], {}).reason, "not_newer");
  assert.equal(store.receive(1, "ui_update", [update({ presentation_epoch: EPOCH_B, revision: 6 })], {}).reason, "not_newer");
  assert.equal(store.getState().revision, 7);

  const result = store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_B, revision: 8 })], {});
  assert.equal(result.accepted, true);
  assert.equal(store.getState().revision, 8);
});

test("snapshots replace every panel atomically", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);
  const first = validStatusPanel({ resources: { hp: { current: 80, maximum: 100 } } });
  store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_A, revision: 1, panels: { status: first } })], {});

  const second = validStatusPanel({
    resources: { hp: { current: 12, maximum: 100 } },
    conditions: [],
    disguise_active: true,
    combat: { mode: "hostile", round: 3 },
  });
  const result = store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_A, revision: 2, panels: { status: second } })], {});
  assert.equal(result.accepted, true);
  assert.deepEqual(store.getState().panels.status, second, "entire panel object replaced");
});

test("updates completely replace each named panel without merging", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);
  store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_A, revision: 1 })], {});

  const leanStatus = validStatusPanel({ conditions: [], disguise_active: false, combat: null });
  const result = store.receive(1, "ui_update", [update({ presentation_epoch: EPOCH_A, revision: 2, panels: { status: leanStatus } })], {});
  assert.equal(result.accepted, true);
  assert.deepEqual(store.getState().panels.status, leanStatus, "no omitted nested fields are retained");
  assert.equal(store.getState().mode, "exploration");
  assert.equal(store.getState().revision, 2);
});

test("a multi-panel message with one malformed panel is rejected atomically", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);
  const seen = [];
  store.subscribe((state) => seen.push(state));

  // Valid status plus an unregistered panel name: the whole update is rejected.
  const mixed = snapshot({
    panels: { status: validStatusPanel(), mystery: unavailableStatusPanel() },
  });
  const result = store.receive(1, "ui_snapshot", [mixed], {});
  assert.equal(result.accepted, false);
  assert.equal(seen.length, 0, "no subscriber observes a partially applied message");

  // A malformed included status payload rejects the whole update.
  const malformedStatus = {
    schema_version: 1,
    available: true,
    actor: { name: "x", identity: "1", location: null },
    resources: { hp: { current: 1 }, mp: { current: 1 }, sp: { current: 1 } },
    conditions: [],
    disguise_active: false,
    combat: null,
  };
  const malformed = update();
  malformed.panels = { status: malformedStatus };
  assert.equal(store.receive(1, "ui_snapshot", [malformed], {}).reason, "invalid");
  assert.equal(store.getState().phase, "awaiting_initial_snapshot");

  // After a valid adoption, a malformed update leaves committed state intact.
  store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_A, revision: 1 })], {});
  const before = store.getState().revision;
  const bad = update({
    presentation_epoch: EPOCH_A,
    revision: 2,
    panels: { status: validStatusPanel({ disguise_active: "yes" }) },
  });
  assert.equal(store.receive(1, "ui_update", [bad], {}).accepted, false);
  assert.equal(store.getState().revision, before);
});

test("action results are epoch-scoped and surfaced to subscribers", () => {
  const store = connectedStore(EPOCH_A, 1);
  const seen = [];
  store.subscribe((state) => seen.push(state.lastActionResult));

  let result = store.receive(1, "ui_action_result", [actionResult({ presentation_epoch: EPOCH_A })], {});
  assert.equal(result.accepted, true);
  assert.equal(store.getState().lastActionResult.outcome, "success");
  assert.equal(seen.length, 1);

  // A result from a different epoch is discarded.
  result = store.receive(1, "ui_action_result", [actionResult({ presentation_epoch: EPOCH_B })], {});
  assert.equal(result.accepted, false);
  assert.equal(seen.length, 1);
});

test("an incompatible protocol locks graphical mutations", () => {
  const store = connectedStore(EPOCH_A, 1);
  assert.equal(store.getState().mutationsLocked, false);

  const result = store.receive(1, "ui_protocol_error", [protocolError({ code: "unsupported_version" })], {});
  assert.equal(result.accepted, true);
  const state = store.getState();
  assert.equal(state.mutationsLocked, true);
  assert.equal(state.protocolError.code, "unsupported_version");
  assert.equal(state.protocolError.reloadRequired, true);

  // Ordinary presentation remains usable: a newer snapshot still applies.
  const accepted = store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_A, revision: 2 })], {});
  assert.equal(accepted.accepted, true);
});

