/*
 * Unpuppet (OOC) detachment lifecycle and re-establishment rules.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { EPOCH_A, EPOCH_B, actionResult, connectedStore, protocolError, snapshot, update } = require("./protocol_support.js");


test("no_puppet protocol error enters the detached phase and clears panels", () => {
  const store = connectedStore(EPOCH_A, 5);
  assert.deepEqual(Object.keys(store.getState().panels), ["status"]);

  const result = store.receive(
    1,
    "ui_protocol_error",
    [protocolError({ code: "no_puppet", reload_required: false })],
    {}
  );
  assert.equal(result.accepted, true);
  const state = store.getState();
  assert.equal(state.phase, "detached");
  assert.equal(state.mutationsLocked, true);
  assert.deepEqual(state.panels, {}, "character panels are cleared");
  // The pre-detachment epoch and revision are retained so a late bounded
  // no-puppet rejection can still be accepted against this view.
  assert.equal(state.activeEpoch, EPOCH_A);
  assert.equal(state.revision, 5);
});

test("detached store accepts the no-puppet rejection for its own epoch", () => {
  const store = connectedStore(EPOCH_A, 5);
  store.receive(1, "ui_protocol_error", [protocolError({ code: "no_puppet", reload_required: false })], {});
  const seen = [];
  store.subscribe((state) => seen.push(state.lastActionResult));

  const result = store.receive(
    1,
    "ui_action_result",
    [
      actionResult({
        presentation_epoch: EPOCH_A,
        request_id: "web:3",
        outcome: "rejected",
        code: "no_puppet",
        message: "目前沒有附身角色，無法執行操作",
        presentation_revision: 5,
      }),
    ],
    {}
  );
  assert.equal(result.accepted, true, "the in-flight rejection must unlock the client");
  assert.equal(store.getState().lastActionResult.code, "no_puppet");
  assert.equal(seen.length, 1);
});

test("detached store rejects a foreign-epoch action result", () => {
  const store = connectedStore(EPOCH_A, 5);
  store.receive(1, "ui_protocol_error", [protocolError({ code: "no_puppet", reload_required: false })], {});

  const result = store.receive(
    1,
    "ui_action_result",
    [actionResult({ presentation_epoch: EPOCH_B, request_id: "web:3" })],
    {}
  );
  assert.equal(result.accepted, false);
  assert.equal(result.reason, "different_epoch");
  assert.equal(store.getState().lastActionResult, null);
});

test("detached store re-establishes only on a fresh-epoch full snapshot", () => {
  const store = connectedStore(EPOCH_A, 5);
  store.receive(1, "ui_protocol_error", [protocolError({ code: "no_puppet", reload_required: false })], {});

  // A stale same-epoch snapshot from the retired sequence never re-adopts.
  const sameEpoch = store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_A, revision: 9 })], {});
  assert.equal(sameEpoch.accepted, false);
  assert.equal(sameEpoch.reason, "different_epoch");
  assert.equal(store.getState().phase, "detached");

  // An update can never re-establish a detached store.
  const updateResult = store.receive(1, "ui_update", [update({ presentation_epoch: EPOCH_B, revision: 1 })], {});
  assert.equal(updateResult.accepted, false);
  assert.equal(updateResult.reason, "update_cannot_establish_epoch");
  assert.equal(store.getState().phase, "detached");

  // A genuinely fresh epoch snapshot re-establishes active state.
  const fresh = store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_B, revision: 1 })], {});
  assert.equal(fresh.accepted, true);
  assert.equal(fresh.established, true);
  const state = store.getState();
  assert.equal(state.phase, "active");
  assert.equal(state.activeEpoch, EPOCH_B);
  assert.equal(state.mutationsLocked, false);
  assert.deepEqual(Object.keys(state.panels), ["status"]);
});

test("detached store is re-established by a retired-epoch snapshot only after transport reset", () => {
  // beginTransport retires the old epoch; a detached store then re-adopts
  // only epochs not in the retired set.
  const store = connectedStore(EPOCH_A, 5);
  store.receive(1, "ui_protocol_error", [protocolError({ code: "no_puppet", reload_required: false })], {});
  store.beginTransport(2);
  assert.equal(store.getState().phase, "awaiting_initial_snapshot");
  const retiredEpoch = store.receive(2, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_A, revision: 1 })], {});
  assert.equal(retiredEpoch.reason, "retired_epoch");
  const fresh = store.receive(2, "ui_snapshot", [snapshot({ presentation_epoch: EPOCH_B, revision: 1 })], {});
  assert.equal(fresh.accepted, true);
});

test("no_puppet is a registered protocol error code", () => {
  assert.ok(Protocol.PROTOCOL_ERROR_CODES.indexOf("no_puppet") !== -1);
  assert.deepEqual(
    Protocol.validateProtocolError({ protocol_version: 1, code: "no_puppet", message: "你已離開角色（OOC）。", reload_required: false }),
    { protocolVersion: 1, code: "no_puppet", message: "你已離開角色（OOC）。", reloadRequired: false, correlationId: null }
  );
});

test("sync envelope is exactly { protocol_version: 1 }", () => {
  assert.deepEqual(Protocol.syncEnvelope(), { protocol_version: 1 });
});

test("beginTransport rejects non-increasing generations", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);
  assert.throws(() => store.beginTransport(1));
  assert.throws(() => store.beginTransport(0));
});

