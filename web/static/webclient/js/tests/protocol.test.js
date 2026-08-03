/*
 * DOM-independent tests for the Elosern OOB protocol reducer.
 *
 * Runs with Node 24's built-in test runner and node:assert; no npm packages.
 * Covers the exact server envelope schemas/discriminators, atomic rejection,
 * transport-generation lifecycle, epoch/revision ordering, complete panel
 * replacement, and bounded one-sync renderer recovery.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const State = require("../plugins/elosern_state.js");

const EPOCH_A = "a".repeat(22);
const EPOCH_B = "b".repeat(22);
const EPOCH_C = "c".repeat(22);
const VALID_EPOCH = "9f55f20a0b".padEnd(22, "c");

function deepMerge(base, overrides) {
  if (overrides === undefined) {
    return base;
  }
  if (Array.isArray(base) || Array.isArray(overrides)) {
    return overrides;
  }
  if (typeof base !== "object" || base === null || typeof overrides !== "object" || overrides === null) {
    return overrides;
  }
  const result = Object.assign({}, base);
  Object.keys(overrides).forEach((key) => {
    result[key] = deepMerge(base[key], overrides[key]);
  });
  return result;
}

function serverTime(overrides) {
  return deepMerge(
    {
      year: 1204,
      season_index: 2,
      season_label: "仲夏",
      day_in_season: 17,
      hour: 14,
      minute: 30,
      second: 5,
    },
    overrides
  );
}

function validStatusPanel(overrides) {
  return deepMerge(
    {
      schema_version: 1,
      available: true,
      actor: {
        name: "影行者",
        identity: "42",
        location: { label: "西風酒館", identity: "17" },
      },
      resources: {
        hp: { current: 80, maximum: 100 },
        mp: { current: 30, maximum: 50 },
        sp: { current: 12, maximum: 40 },
      },
      conditions: [
        { code: "combat_modifier.arousal", label: "情動", severity: "informational", modifiers: { power: 2 } },
      ],
      disguise_active: false,
      combat: null,
    },
    overrides
  );
}

function unavailableStatusPanel(overrides) {
  return deepMerge(
    {
      schema_version: 1,
      available: false,
      reason: { code: "presentation_unavailable", message: "目前無法顯示此介面" },
    },
    overrides
  );
}

function snapshot(overrides) {
  return deepMerge(
    {
      protocol_version: 1,
      presentation_epoch: VALID_EPOCH,
      revision: 1,
      mode: "exploration",
      panels: { status: validStatusPanel() },
      layout_version: 1,
      server_time: serverTime(),
    },
    overrides
  );
}

function update(overrides) {
  return snapshot(overrides);
}

function actionResult(overrides) {
  return deepMerge(
    {
      protocol_version: 1,
      presentation_epoch: VALID_EPOCH,
      request_id: "client-7:19",
      outcome: "success",
      code: "completed",
      message: "完成",
      presentation_revision: 1,
    },
    overrides
  );
}

function protocolError(overrides) {
  return deepMerge(
    {
      protocol_version: 1,
      code: "unsupported_version",
      message: "不支援的協定版本",
      reload_required: true,
    },
    overrides
  );
}

// ---------------------------------------------------------------------------
// Store lifecycle helpers.
// ---------------------------------------------------------------------------

function connectedStore(epoch, revision) {
  const store = Protocol.createStore();
  store.beginTransport(1);
  store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: epoch, revision: revision })], {});
  return store;
}

// ---------------------------------------------------------------------------
// Exact schemas and discriminators.
// ---------------------------------------------------------------------------

test("accepts a valid full snapshot and adopts its state", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);
  const received = [];
  store.subscribe((state) => received.push(state));
  const result = store.receive(1, "ui_snapshot", [snapshot()], {});

  assert.equal(result.accepted, true);
  assert.equal(result.established, true);
  assert.equal(received.length, 1, "subscribers notified exactly once");

  const state = store.getState();
  assert.equal(state.phase, "active");
  assert.equal(state.activeEpoch, VALID_EPOCH);
  assert.equal(state.revision, 1);
  assert.equal(state.mode, "exploration");
  assert.equal(state.layoutVersion, 1);
  assert.equal(state.serverTime.season_label, "仲夏");
  assert.equal(state.mutationsLocked, false);
  assert.deepEqual(state.panels.status.resources.hp, { current: 80, maximum: 100 });
});

test("validates the exact common snapshot field set", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);

  assert.equal(store.receive(1, "ui_snapshot", [snapshot({ extra: 1 })], {}).reason, "invalid");
  const missingRevision = snapshot();
  delete missingRevision.revision;
  assert.equal(store.receive(1, "ui_snapshot", [missingRevision], {}).reason, "invalid");
  assert.equal(store.receive(1, "ui_snapshot", [snapshot({ protocol_version: 2 })], {}).reason, "invalid");
  assert.equal(store.receive(1, "ui_snapshot", [snapshot({ mode: "travel" })], {}).reason, "invalid");
  assert.equal(store.receive(1, "ui_snapshot", [snapshot({ layout_version: 0 })], {}).reason, "invalid");
  assert.equal(store.receive(1, "ui_snapshot", [snapshot({ layout_version: 65536 })], {}).reason, "invalid");
  assert.equal(store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: "short" })], {}).reason, "invalid");
  assert.equal(store.receive(1, "ui_snapshot", [snapshot({ revision: 0 })], {}).reason, "invalid");
  assert.equal(store.receive(1, "ui_snapshot", [snapshot({ revision: 1.5 })], {}).reason, "invalid");
  assert.equal(store.receive(1, "ui_snapshot", [snapshot({ revision: true })], {}).reason, "invalid");

  assert.equal(
    store.receive(1, "ui_snapshot", [snapshot({ server_time: serverTime({ season_index: 4 }) })], {}).reason,
    "invalid"
  );
  assert.equal(
    store.receive(1, "ui_snapshot", [snapshot({ server_time: serverTime({ season_label: "" }) })], {}).reason,
    "invalid"
  );
  assert.equal(
    store.receive(1, "ui_snapshot", [snapshot({ server_time: serverTime({ hour: 24 }) })], {}).reason,
    "invalid"
  );
  assert.equal(
    store.receive(1, "ui_snapshot", [snapshot({ server_time: serverTime({ extra: 1 }) })], {}).reason,
    "invalid"
  );

  // No state may be committed by any rejected message.
  assert.equal(store.getState().phase, "awaiting_initial_snapshot");
});

test("validates panel names against the registered allowlist", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);
  const withUnknown = snapshot({
    panels: { status: validStatusPanel(), unknown_panel: unavailableStatusPanel() },
  });
  assert.equal(store.receive(1, "ui_snapshot", [withUnknown], {}).reason, "invalid");
  assert.equal(store.getState().phase, "awaiting_initial_snapshot");

  const badName = snapshot({ panels: { "status panel": validStatusPanel() } });
  assert.equal(store.receive(1, "ui_snapshot", [badName], {}).reason, "invalid");
});

test("validates the status panel available/unavailable discriminator exactly", () => {
  // Unavailable form is exact.
  assert.deepEqual(
    Protocol.validateStatusPanel(unavailableStatusPanel()),
    unavailableStatusPanel()
  );
  const badReason = unavailableStatusPanel();
  badReason.reason = { code: "x" };
  assert.throws(() => Protocol.validateStatusPanel(badReason));
  assert.throws(() =>
    Protocol.validateStatusPanel(unavailableStatusPanel({ schema_version: 2 }))
  );
  // An internal reason carries a bounded correlation ID.
  assert.doesNotThrow(() =>
    Protocol.validateStatusPanel(
      unavailableStatusPanel({
        reason: { code: "internal_presenter_error", message: "此介面暫時無法使用", correlation_id: "a".repeat(32) },
      })
    )
  );

  // Available form is exact.
  assert.doesNotThrow(() => Protocol.validateStatusPanel(validStatusPanel()));
  assert.throws(() => Protocol.validateStatusPanel(validStatusPanel({ extra: 1 })));
  assert.throws(() => Protocol.validateStatusPanel(validStatusPanel({ schema_version: 2 })));
  const partialResources = validStatusPanel();
  partialResources.resources = { hp: { current: 1, maximum: 2 } };
  assert.throws(() => Protocol.validateStatusPanel(partialResources));
  assert.throws(() =>
    Protocol.validateStatusPanel(validStatusPanel({ disguise_active: "yes" }))
  );
  assert.throws(() =>
    Protocol.validateStatusPanel(validStatusPanel({ combat: { mode: "hostile" } }))
  );
  assert.throws(() =>
    Protocol.validateStatusPanel(
      validStatusPanel({ conditions: [{ code: "x", label: "y", severity: "mystery" }] })
    )
  );
  const partialActor = validStatusPanel();
  partialActor.actor = { name: "x", identity: "1" };
  assert.throws(() => Protocol.validateStatusPanel(partialActor));
});

test("enforces status field-specific bounds", () => {
  // Actor name 1..256, identity 1..64.
  assert.throws(() =>
    Protocol.validateStatusPanel(
      validStatusPanel({ actor: { name: "x".repeat(257), identity: "1", location: null } })
    )
  );
  assert.throws(() =>
    Protocol.validateStatusPanel(
      validStatusPanel({ actor: { name: "x", identity: "y".repeat(65), location: null } })
    )
  );
  // Location label 1..256, identity 1..64.
  assert.throws(() =>
    Protocol.validateStatusPanel(
      validStatusPanel({
        actor: {
          name: "x",
          identity: "1",
          location: { label: "z".repeat(257), identity: "2" },
        },
      })
    )
  );
  assert.throws(() =>
    Protocol.validateStatusPanel(
      validStatusPanel({
        actor: {
          name: "x",
          identity: "1",
          location: { label: "z", identity: "w".repeat(65) },
        },
      })
    )
  );
  // Zero maximum and current > maximum are rejected.
  assert.throws(() =>
    Protocol.validateStatusPanel(
      validStatusPanel({ resources: { hp: { current: 5, maximum: 0 }, mp: { current: 1, maximum: 2 }, sp: { current: 1, maximum: 2 } } })
    )
  );
  assert.throws(() =>
    Protocol.validateStatusPanel(
      validStatusPanel({ resources: { hp: { current: 9, maximum: 5 }, mp: { current: 1, maximum: 2 }, sp: { current: 1, maximum: 2 } } })
    )
  );
  // More than 32 conditions are rejected.
  const manyConditions = validStatusPanel();
  manyConditions.conditions = [];
  for (let i = 0; i < 33; i++) {
    manyConditions.conditions.push({ code: "c" + i, label: "L", severity: "informational" });
  }
  assert.throws(() => Protocol.validateStatusPanel(manyConditions));
  // Condition code must be an identifier; label capped at 128; modifiers capped at 16 keys.
  assert.throws(() =>
    Protocol.validateStatusPanel(
      validStatusPanel({ conditions: [{ code: "BAD", label: "L", severity: "informational" }] })
    )
  );
  assert.throws(() =>
    Protocol.validateStatusPanel(
      validStatusPanel({ conditions: [{ code: "ok", label: "L".repeat(129), severity: "informational" }] })
    )
  );
  const tooManyModifiers = {};
  for (let i = 0; i < 17; i++) {
    tooManyModifiers["k" + i] = 1;
  }
  assert.throws(() =>
    Protocol.validateStatusPanel(
      validStatusPanel({
        conditions: [{ code: "ok", label: "L", severity: "informational", modifiers: tooManyModifiers }],
      })
    )
  );
  // Unknown combat mode is rejected.
  assert.throws(() =>
    Protocol.validateStatusPanel(
      validStatusPanel({ combat: { mode: "travel", round: 1 } })
    )
  );
});

test("validates exact ui_action_result envelopes", () => {
  assert.doesNotThrow(() => Protocol.validateActionResult(actionResult()));
  assert.doesNotThrow(() =>
    Protocol.validateActionResult(
      actionResult({ outcome: "error", code: "internal", correlation_id: "b".repeat(32) })
    )
  );
  // Error outcome requires a correlation ID.
  assert.throws(() =>
    Protocol.validateActionResult(actionResult({ outcome: "error", code: "internal" }))
  );
  // Non-error outcomes forbid a correlation ID.
  assert.throws(() =>
    Protocol.validateActionResult(actionResult({ correlation_id: "b".repeat(32) }))
  );
  assert.throws(() => Protocol.validateActionResult(actionResult({ outcome: "busy" })));
  assert.throws(() => Protocol.validateActionResult(actionResult({ request_id: "bad request" })));
  assert.throws(() => Protocol.validateActionResult(actionResult({ message: "" })));
  assert.throws(() =>
    Protocol.validateActionResult(actionResult({ presentation_revision: true }))
  );
  assert.throws(() => Protocol.validateActionResult(actionResult({ extra: 1 })));
});

test("validates exact ui_protocol_error envelopes", () => {
  assert.doesNotThrow(() => Protocol.validateProtocolError(protocolError()));
  assert.doesNotThrow(() =>
    Protocol.validateProtocolError(
      protocolError({ code: "internal_error", reload_required: false, correlation_id: "c".repeat(32) })
    )
  );
  assert.throws(() => Protocol.validateProtocolError(protocolError({ code: "unknown_code" })));
  assert.throws(() => Protocol.validateProtocolError(protocolError({ reload_required: 1 })));
  assert.throws(() => Protocol.validateProtocolError(protocolError({ extra: 1 })));
  assert.throws(() =>
    Protocol.validateProtocolError(protocolError({ code: "internal_error" }))
  );
  assert.throws(() =>
    Protocol.validateProtocolError(protocolError({ correlation_id: "c".repeat(32) }))
  );
});

test("enforces global JSON-safety bounds", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);

  // Excessive depth.
  let deep = { panels: { status: validStatusPanel() } };
  for (let i = 0; i < 12; i++) {
    deep = { nest: deep };
  }
  assert.throws(() => Protocol.checkEnvelope(deep));

  // Over 64 fields.
  const many = {};
  for (let i = 0; i < 70; i++) {
    many["k" + i] = 1;
  }
  assert.throws(() => Protocol.checkGlobalSafety(many));

  // Over 128 list items.
  assert.throws(() => Protocol.checkGlobalSafety(new Array(130).fill(1)));

  // Over-long string (code points).
  assert.throws(() => Protocol.checkGlobalSafety("x".repeat(3000)));

  // Non-finite numbers.
  assert.throws(() => Protocol.checkGlobalSafety({ value: Infinity }));
  assert.throws(() => Protocol.checkGlobalSafety({ value: NaN }));

  // Non-integer revision.
  assert.equal(
    store.receive(1, "ui_snapshot", [snapshot({ revision: 3.5 })], {}).reason,
    "invalid"
  );
});

test("rejects an oversized canonical envelope", () => {
  const bigString = "x".repeat(70_000);
  const bigSnapshot = snapshot({ actor_note: bigString });
  assert.throws(() => Protocol.checkEnvelope(bigSnapshot));

  const store = Protocol.createStore();
  store.beginTransport(1);
  assert.equal(store.receive(1, "ui_snapshot", [bigSnapshot], {}).reason, "invalid");
});

// ---------------------------------------------------------------------------
// Transport generation lifecycle.
// ---------------------------------------------------------------------------

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
    panels: { status: validStatusPanel(), art: unavailableStatusPanel() },
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

// ---------------------------------------------------------------------------
// Bounded one-sync renderer recovery.
// ---------------------------------------------------------------------------

test("a renderer failure requests at most one resync per episode", () => {
  const sends = [];
  const controller = State.createStateController(Protocol, () => sends.push(1));

  assert.equal(controller.requestResync("status"), true, "first failure syncs once");
  assert.equal(sends.length, 1);
  assert.equal(controller.requestResync("status"), false, "repeated failure does not loop");
  assert.equal(sends.length, 1);

  // A successful render ends the episode and allows one fresh resync.
  controller.resetResyncEpisode("status");
  assert.equal(controller.requestResync("status"), true);
  assert.equal(sends.length, 2);
});

test("one-sync guard tracks episodes per panel independently", () => {
  const guard = State.createOneSyncGuard();
  assert.equal(guard.request("status"), true);
  assert.equal(guard.request("status"), false);
  assert.equal(guard.request("art"), true, "a different panel has its own episode");
  assert.equal(guard.isBlocked("status"), true);
  assert.equal(guard.isBlocked("art"), true);
  guard.resetEpisode("status");
  assert.equal(guard.isBlocked("status"), false);
  assert.equal(guard.request("status"), true);
  assert.equal(guard.isBlocked("art"), true);
  guard.clearAll();
  assert.equal(guard.isBlocked("art"), false);
});

test("state controller forwards beginTransport and receive to the reducer", () => {
  const sends = [];
  const controller = State.createStateController(Protocol, () => sends.push(1));
  controller.beginTransport(1);
  const result = controller.receive(1, "ui_snapshot", [snapshot()], {});
  assert.equal(result.accepted, true);
  assert.equal(controller.getState().phase, "active");
  assert.equal(controller.store.getState().activeEpoch, VALID_EPOCH);
});

test("browser state requests a sync and re-tags receivers per connection_open", () => {
  const sent = [];
  const listeners = {};
  const fakeEvennia = {
    isConnected: () => true,
    emitter: {
      on(name, listener) {
        listeners[name] = listener;
      },
    },
    msg(cmd, args, kwargs) {
      sent.push([cmd, args, kwargs]);
    },
  };

  const browserState = State.createBrowserState(Protocol);
  browserState.wire(fakeEvennia);

  // First connection_open: generation 1, sync requested, receivers re-tagged.
  listeners["connection_open"]([], {});
  assert.deepEqual(sent[0][0], "ui_sync");
  assert.deepEqual(sent[0][1], [{ protocol_version: 1 }]);
  assert.equal(browserState.getState().generation, 1);

  // A snapshot delivered to the re-tagged receiver is accepted.
  const adopted = listeners["ui_snapshot"]([snapshot({ presentation_epoch: EPOCH_A, revision: 1 })], {});
  assert.equal(browserState.getState().activeEpoch, EPOCH_A);

  // Reconnect: generation 2, old state cleared, then a new-epoch snapshot adopts.
  listeners["connection_open"]([], {});
  assert.equal(browserState.getState().generation, 2);
  assert.equal(browserState.getState().activeEpoch, null);
  listeners["ui_snapshot"]([snapshot({ presentation_epoch: EPOCH_B, revision: 1 })], {});
  assert.equal(browserState.getState().activeEpoch, EPOCH_B);

  // A message delivered through the pre-reconnect receiver is discarded.
  assert.equal(browserState.requestResync("status"), true);
  assert.equal(sent.length, 3);
  assert.equal(browserState.requestResync("status"), false, "no sync loop");
  assert.equal(sent.length, 3);
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

// ---------------------------------------------------------------------------
// context_actions combat panel schema (task 4.1).
// ---------------------------------------------------------------------------

function validCombatSkill(overrides) {
  return deepMerge(
    {
      key: "fire_ball",
      label: "火球術",
      description: "凝聚火焰魔力，對單一敵人造成魔法傷害。",
      cost: { mp: 20 },
      target_spec: "single",
      element: "fire",
      enabled: true,
      disabled_reason: null,
      targets: [2],
      shorthands: [],
    },
    overrides
  );
}

function validCombatParticipant(overrides) {
  return deepMerge(
    {
      identity: 2,
      token: "e1",
      display_name: "哥布林",
      team: "foes",
      state: "active",
      hp_current: 100,
      hp_maximum: 100,
      portrait_ref: null,
    },
    overrides
  );
}

function validCombatPanel(overrides) {
  return deepMerge(
    {
      schema_version: 1,
      available: true,
      kind: "combat",
      session: {
        session_id: "hostile:1:0",
        mode: "hostile",
        round: 0,
        state: "ready",
        reason: null,
      },
      participants: [validCombatParticipant()],
      root_actions: ["attack", "skills", "items", "defend", "flee"],
      secondary_actions: ["forfeit"],
      skills: [validCombatSkill()],
    },
    overrides
  );
}

function validRecoveryPanel(overrides) {
  return deepMerge(
    {
      schema_version: 1,
      available: true,
      kind: "combat",
      session: {
        session_id: "hostile:1:0",
        mode: "hostile",
        round: 2,
        state: "recovery",
        reason: { code: "missing_participant", message: "戰鬥成員已無法確認。" },
      },
      participants: [],
      root_actions: [],
      secondary_actions: ["forfeit"],
      skills: [],
    },
    overrides
  );
}

test("validates the available context_actions combat panel", () => {
  assert.doesNotThrow(() => Protocol.validateContextActionsPanel(validCombatPanel()));
  assert.doesNotThrow(() => Protocol.validateContextActionsPanel(validRecoveryPanel()));
});

test("rejects malformed context_actions panels atomically", () => {
  assert.throws(() => Protocol.validateContextActionsPanel({ schema_version: 1, available: false }));
  assert.throws(() => Protocol.validateContextActionsPanel(validCombatPanel({ extra: 1 })));
  assert.throws(() => Protocol.validateContextActionsPanel(validCombatPanel({ kind: "exploration" })));
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ root_actions: ["attack", "skills", "items", "defend", "flee", "bogus"] })
    )
  );
  // A disabled skill must carry a disabled_reason.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: [validCombatSkill({ enabled: false, disabled_reason: null })] })
    )
  );
  // Only AREA skills may carry shorthands.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: [validCombatSkill({ shorthands: ["all-enemies"] })] })
    )
  );
  // portrait_ref must be null in schema version 1.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        participants: [validCombatParticipant({ portrait_ref: "https://x.test/a.png" })],
      })
    )
  );
  // Skill targets must reference a presented participant.
  assert.throws(() =>
    Protocol.validateContextActionsPanel({ skills: [validCombatSkill({ targets: [99] })] })
  );
  // A recovery session must not expose cast/flee root actions.
  assert.throws(() => Protocol.validateContextActionsPanel(validRecoveryPanel({ root_actions: ["attack"] })));
  // A ready session must have a null reason.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        session: {
          session_id: "hostile:1:0",
          mode: "hostile",
          round: 0,
          state: "ready",
          reason: { code: "x", message: "說明" },
        },
      })
    )
  );
});

test("a combat snapshot with a malformed context_actions panel is rejected atomically", () => {
  const bad = snapshot({
    mode: "combat",
    panels: {
      status: validStatusPanel({ combat: { mode: "hostile", round: 0 } }),
      context_actions: validCombatPanel({ kind: "bogus" }),
    },
  });
  const store = Protocol.createStore();
  assert.equal(store.receive(1, "ui_snapshot", [bad], {}).accepted, false);
  assert.equal(store.getState().phase, "idle");
});

// ---------------------------------------------------------------------------
// local_map panel schema (design D10a).
// ---------------------------------------------------------------------------

function validLocalMapNode(overrides) {
  return Object.assign(
    {
      id: "grid:capital_altoria:2:0",
      label: "南門",
      x: 2,
      y: 0,
      visibility: "current",
      current: true,
      anchor: false,
      landmark: false,
      action: null,
    },
    overrides || {}
  );
}

function validLocalMapEdge(overrides) {
  return Object.assign(
    {
      source: "grid:capital_altoria:2:0",
      destination: "grid:capital_altoria:2:1",
      label: "n",
      known: true,
      traversable: true,
    },
    overrides || {}
  );
}

function validLocalMapPanel(overrides) {
  return Object.assign(
    {
      schema_version: 1,
      available: true,
      layer: "grid",
      current_node: "grid:capital_altoria:2:0",
      title: "南門街道圖",
      nodes: [
        validLocalMapNode(),
        validLocalMapNode({
          id: "grid:capital_altoria:2:1",
          label: "南大道",
          x: 2,
          y: 1,
          visibility: "visible_visited",
          current: false,
          action: {
            kind: "move",
            exit_ref: "42",
            destination: "grid:capital_altoria:2:1",
          },
        }),
      ],
      edges: [validLocalMapEdge()],
      legend: ["你目前所在的位置", "尚未探索的相鄰位置"],
    },
    overrides || {}
  );
}

test("validates the local_map panel available/unavailable discriminator", () => {
  assert.deepEqual(
    Protocol.validateLocalMapPanel(unavailableStatusPanel()),
    unavailableStatusPanel()
  );
  assert.doesNotThrow(() => Protocol.validateLocalMapPanel(validLocalMapPanel()));
  assert.throws(() => Protocol.validateLocalMapPanel(validLocalMapPanel({ extra: 1 })));
  assert.throws(() =>
    Protocol.validateLocalMapPanel(validLocalMapPanel({ layer: "dungeon" }))
  );
  // A grid current node must carry the grid prefix.
  assert.throws(() =>
    Protocol.validateLocalMapPanel(
      validLocalMapPanel({ layer: "grid", current_node: "room:5" })
    )
  );
});

test("enforces local_map D10a bounds", () => {
  const longLabel = validLocalMapPanel({
    nodes: [
      validLocalMapNode(),
      validLocalMapNode({
        id: "grid:capital_altoria:2:1",
        label: "字".repeat(Protocol.LOCAL_MAP_MAX_STRING + 1),
        visibility: "visible_visited",
        current: false,
      }),
    ],
  });
  assert.throws(() => Protocol.validateLocalMapPanel(longLabel));

  const tooMany = validLocalMapPanel();
  tooMany.nodes = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_NODES + 1; i++) {
    tooMany.nodes.push(
      validLocalMapNode({
        id: "room:" + i,
        label: "x",
        x: i,
        y: 0,
        visibility: "remembered",
        current: i === 0,
      })
    );
  }
  assert.throws(() => Protocol.validateLocalMapPanel(tooMany));

  const coord = validLocalMapPanel({
    nodes: [
      validLocalMapNode(),
      validLocalMapNode({ id: "room:2", label: "x", x: 1025, y: 0, visibility: "visible_unvisited", current: false }),
    ],
  });
  assert.throws(() => Protocol.validateLocalMapPanel(coord));
});

test("rejects malformed movement descriptors and unknown node ids", () => {
  const badKind = validLocalMapPanel({
    nodes: [
      validLocalMapNode(),
      validLocalMapNode({
        id: "room:2",
        label: "x",
        x: 1,
        y: 0,
        visibility: "visible_unvisited",
        current: false,
        action: { kind: "teleport", exit_ref: "1", destination: "room:2" },
      }),
    ],
  });
  assert.throws(() => Protocol.validateLocalMapPanel(badKind));

  const badRef = validLocalMapPanel({
    nodes: [
      validLocalMapNode(),
      validLocalMapNode({
        id: "room:2",
        label: "x",
        x: 1,
        y: 0,
        visibility: "visible_unvisited",
        current: false,
        action: { kind: "move", exit_ref: "字".repeat(10), destination: "room:2" },
      }),
    ],
  });
  assert.throws(() => Protocol.validateLocalMapPanel(badRef));

  const unknownEdge = validLocalMapPanel({
    edges: [validLocalMapEdge({ destination: "room:999" })],
  });
  assert.throws(() => Protocol.validateLocalMapPanel(unknownEdge));
});

test("a local_map snapshot with an invalid panel is rejected atomically", () => {
  const bad = snapshot({
    panels: {
      status: validStatusPanel(),
      local_map: validLocalMapPanel({ available: "yes" }),
    },
  });
  const store = Protocol.createStore();
  assert.equal(store.receive(1, "ui_snapshot", [bad], {}).accepted, false);
  assert.equal(store.getState().phase, "idle");
});

test("a structurally maximal realistic local_map payload fits the envelope", () => {
  // The structural maxima the schema allows -- 64 nodes, 128 edges, 16
  // legend entries -- with realistic bounded content must serialize under the
  // 65,536-byte envelope (D10a conformance, mirrored from the Python suite).
  const nodeIds = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_NODES; i++) {
    nodeIds.push("grid:capital_altoria:" + (i % 8) + ":" + Math.floor(i / 8));
  }
  const nodes = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_NODES; i++) {
    nodes.push(
      validLocalMapNode({
        id: nodeIds[i],
        label: "南門街道".repeat(4),
        x: i % 2 === 0 ? -1024 : 1024,
        y: i % 2 === 0 ? 1024 : -1024,
        visibility: i === 0 ? "current" : "remembered",
        current: i === 0,
        action:
          i === 0
            ? null
            : { kind: "move", exit_ref: "e" + i, destination: nodeIds[i] },
      })
    );
  }
  const edges = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_EDGES; i++) {
    edges.push({
      source: nodeIds[i % Protocol.LOCAL_MAP_MAX_NODES],
      destination: nodeIds[(i + 1) % Protocol.LOCAL_MAP_MAX_NODES],
      label: "n",
      known: true,
      traversable: true,
    });
  }
  const legend = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_LEGEND; i++) {
    legend.push(i % 2 === 0 ? "你目前所在的位置" : "尚未探索的相鄰位置");
  }
  const panel = validLocalMapPanel({
    current_node: nodeIds[0],
    title: "聖潔王都街道圖",
    nodes: nodes,
    edges: edges,
    legend: legend,
  });
  const normalized = Protocol.validateLocalMapPanel(panel);
  assert.ok(
    Protocol.jsonByteSize(normalized) <= Protocol.MAX_CANONICAL_JSON_BYTES,
    "a structurally maximal realistic payload must fit the 65,536-byte envelope"
  );
});

test("local_map byte budget fails closed on the theoretical worst case", () => {
  // A payload with max-length CJK strings on every node and edge at once
  // serializes far beyond the 65,536-byte envelope; the validator must reject
  // it (D10a conformance is enforced on serialized size, not just per-field
  // bounds).
  const nodeIds = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_NODES; i++) {
    nodeIds.push("grid:capital_altoria:" + (i % 8) + ":" + Math.floor(i / 8));
  }
  const label = "字".repeat(Protocol.LOCAL_MAP_MAX_STRING);
  const nodes = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_NODES; i++) {
    nodes.push(
      validLocalMapNode({
        id: nodeIds[i],
        label: label,
        x: 1024,
        y: -1024,
        visibility: i === 0 ? "current" : "remembered",
        current: i === 0,
        action: i === 0 ? null : { kind: "move", exit_ref: "e".repeat(Protocol.LOCAL_MAP_MAX_EXIT_REF), destination: nodeIds[i] },
      })
    );
  }
  const edges = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_EDGES; i++) {
    edges.push({ source: nodeIds[i % Protocol.LOCAL_MAP_MAX_NODES], destination: nodeIds[(i + 1) % Protocol.LOCAL_MAP_MAX_NODES], label: label, known: true, traversable: true });
  }
  const legend = [];
  for (let i = 0; i < Protocol.LOCAL_MAP_MAX_LEGEND; i++) {
    legend.push(label);
  }
  assert.throws(() =>
    Protocol.validateLocalMapPanel(
      validLocalMapPanel({
        current_node: nodeIds[0],
        title: "字".repeat(Protocol.LOCAL_MAP_MAX_TITLE),
        nodes: nodes,
        edges: edges,
        legend: legend,
      })
    )
  );
});
