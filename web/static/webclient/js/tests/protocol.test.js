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

  // Excessive depth: the bound is 12 (raised for the nested context_actions
  // v3 shape); 13 nested wrappers must still be rejected.
  let deep = { panels: { status: validStatusPanel() } };
  for (let i = 0; i < 13; i++) {
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

// ---------------------------------------------------------------------------
// Unpuppet detachment (OOC) lifecycle.
// ---------------------------------------------------------------------------

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

test("awaiting-snapshot resync is bounded and self-terminating", () => {
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

  // After a reconnect the first sync is immediate; the retry is disarmed.
  listeners["connection_open"]([], {});
  assert.equal(sent.length, 1);
  assert.equal(browserState.isSyncRetryArmed(), true);

  // While the transport is stuck awaiting, a hundred ticks send only the
  // bounded budget; the retry then stays disarmed and reports exhaustion.
  for (let i = 0; i < 100; i += 1) {
    browserState.syncRetryTick();
  }
  assert.equal(sent.length, 1 + State.SYNC_RETRY_MAX_ATTEMPTS);
  assert.equal(browserState.isSyncRetryExhausted(), true);
  assert.equal(browserState.isSyncRetryArmed(), false);

  // Adoption before the budget is spent disarms the retry without a flag.
  listeners["connection_open"]([], {});
  assert.equal(browserState.syncRetryTick(), "sent");
  listeners["ui_snapshot"]([snapshot({ presentation_epoch: EPOCH_B, revision: 1 })], {});
  assert.equal(browserState.getState().phase, "active");
  for (let i = 0; i < 100; i += 1) {
    assert.equal(browserState.syncRetryTick(), "idle");
  }
  assert.equal(browserState.isSyncRetryExhausted(), false);
  assert.equal(browserState.syncRetryAttempts(), 1, "no further attempts");

  // Disconnect stops the retry without exhausting it, and the next reconnect
  // gets a fresh bounded budget.
  listeners["connection_open"]([], {});
  assert.equal(browserState.syncRetryTick(), "sent");
  assert.equal(browserState.syncRetryAttempts(), 1);
  listeners["connection_close"]([], {});
  assert.equal(browserState.syncRetryTick(), "idle");
  assert.equal(browserState.isSyncRetryExhausted(), false);
  listeners["connection_open"]([], {});
  assert.equal(browserState.syncRetryAttempts(), 0, "re-arm resets the budget");
  assert.equal(browserState.syncRetryTick(), "sent");
  assert.equal(browserState.syncRetryAttempts(), 1);

  // The standalone factory honors an explicit budget and never exceeds it.
  let standaloneState = { connected: true, phase: "awaiting_initial_snapshot" };
  const standalone = State.createAwaitingSyncRetry(
    () => standaloneState,
    () => sent.push(["ui_sync", [Protocol.syncEnvelope()], {}]),
    2
  );
  standalone.arm();
  assert.equal(standalone.tick(), "sent");
  assert.equal(standalone.tick(), "sent");
  assert.equal(standalone.tick(), "idle");
  assert.equal(standalone.isExhausted(), true);
  assert.equal(standalone.tick(), "idle");
  assert.equal(standalone.attempts(), 2);
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

function validSkillGroup(overrides) {
  return deepMerge(
    {
      group: "fire",
      label: "火",
      skills: [validCombatSkill()],
    },
    overrides
  );
}

function validCategoryGroup(overrides) {
  return deepMerge(
    {
      category: "elemental_magic",
      label: "元素魔法",
      groups: [validSkillGroup()],
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
      schema_version: 3,
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
      skills: [validCategoryGroup()],
    },
    overrides
  );
}

function validRecoveryPanel(overrides) {
  return deepMerge(
    {
      schema_version: 3,
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

// Wrap a flat skill list into one nested category group for payload tests.
function nestedSkills(...skills) {
  return [validCategoryGroup({ groups: [validSkillGroup({ skills: skills })] })];
}

test("validates the available context_actions combat panel", () => {
  assert.doesNotThrow(() => Protocol.validateContextActionsPanel(validCombatPanel()));
  assert.doesNotThrow(() => Protocol.validateContextActionsPanel(validRecoveryPanel()));
  // The registered production allowlist must advertise the same version the
  // server ships (mirror of web.webclient.presentation.registry).
  assert.equal(Protocol.PANEL_ALLOWLIST.context_actions, 3);
});

test("freeform_scales is optional and validated when present", () => {
  const scales = [
    { scale: 0.25, label: "1/4", mp_cost: 5 },
    { scale: 0.5, label: "1/2", mp_cost: 10 },
    { scale: 1, label: "1", mp_cost: 20 },
    { scale: 2, label: "2", mp_cost: 40 },
    { scale: 4, label: "4", mp_cost: 80 },
  ];
  assert.doesNotThrow(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: nestedSkills(validCombatSkill({ freeform_scales: scales })) })
    )
  );
  const bad = (overrides) =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: nestedSkills(validCombatSkill({ freeform_scales: [Object.assign({}, scales[0], overrides)] })) })
    );
  assert.throws(() => bad({ scale: 3 }));
  assert.throws(() => bad({ label: "x" }));
  assert.throws(() => bad({ mp_cost: 0 }));
  assert.throws(() => Protocol.validateContextActionsPanel(
    validCombatPanel({ skills: nestedSkills(validCombatSkill({ freeform_scales: [] })) })
  ));
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: nestedSkills(validCombatSkill({ freeform_scales: scales.slice(0, 3) })) })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        skills: nestedSkills(validCombatSkill({ freeform_scales: [Object.assign({}, scales[0], { label: "4" }), ...scales.slice(1)] })),
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        skills: nestedSkills(Object.assign(validCombatSkill(), { cost: { sp: 30 }, freeform_scales: scales })),
      })
    )
  );
});

test("rejects malformed context_actions panels atomically", () => {
  assert.throws(() => Protocol.validateContextActionsPanel({ schema_version: 3, available: false }));
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
      validCombatPanel({ skills: nestedSkills(validCombatSkill({ enabled: false, disabled_reason: null })) })
    )
  );
  // Only AREA skills may carry shorthands.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: nestedSkills(validCombatSkill({ shorthands: ["all-enemies"] })) })
    )
  );
  // portrait_ref must be an opaque decimal catalog key or null in version 3.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        participants: [validCombatParticipant({ portrait_ref: "https://x.test/a.png" })],
      })
    )
  );
  assert.doesNotThrow(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        participants: [validCombatParticipant({ portrait_ref: "42" })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        participants: [validCombatParticipant({ portrait_ref: "4.2" })],
      })
    )
  );
  // A flat v2 skill array is not a valid v3 payload.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: [validCombatSkill()] })
    )
  );
  // Skill targets must reference a presented participant.
  assert.throws(() =>
    Protocol.validateContextActionsPanel({ skills: nestedSkills(validCombatSkill({ targets: [99] })) })
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

test("rejects malformed category and skill groups", () => {
  // Unregistered category key.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: [validCategoryGroup({ category: "bogus" })] })
    )
  );
  // Co-nullability of group and label.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        skills: [validCategoryGroup({ groups: [validSkillGroup({ group: null, label: "火" })] })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        skills: [validCategoryGroup({ groups: [validSkillGroup({ group: "fire", label: null })] })],
      })
    )
  );
  // Empty groups array: empty categories are omitted, not emitted empty.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: [validCategoryGroup({ groups: [] })] })
    )
  );
  // An empty skill group is rejected.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        skills: [validCategoryGroup({ groups: [validSkillGroup({ skills: [] })] })],
      })
    )
  );
  // The top-level array is bounded by the SkillCategory count.
  const tooMany = [];
  for (let index = 0; index < 9; index++) {
    tooMany.push(validCategoryGroup());
  }
  assert.throws(() => Protocol.validateContextActionsPanel(validCombatPanel({ skills: tooMany })));
});

test("the flattened skill-count bound rejects a small-category payload", () => {
  // Design D-5: MAX_SKILLS applies to the flattened descriptor total, not to
  // the top-level category-group count. One category with 33 skills must be
  // rejected even though its category-group count is far below the bound.
  const skills = [];
  for (let index = 1; index <= 33; index++) {
    skills.push(validCombatSkill({ key: "skill_" + index, label: "技能名稱" + index }));
  }
  assert.throws(() =>
    Protocol.validateContextActionsPanel(validCombatPanel({ skills: nestedSkills(...skills) }))
  );
  // 32 skills across the same shape still passes.
  skills.pop();
  assert.doesNotThrow(() =>
    Protocol.validateContextActionsPanel(validCombatPanel({ skills: nestedSkills(...skills) }))
  );
});

test("a category without a group carries exactly one null-keyed sub-group", () => {
  // The single-null-group case must be accepted: a martial_arts category
  // whose members never declare a group emits exactly one { group: null,
  // label: null } sub-group listing every owned skill.
  const panel = validCombatPanel({
    skills: [
      validCategoryGroup({
        category: "martial_arts",
        label: "武技",
        groups: [
          validSkillGroup({ group: null, label: null, skills: [validCombatSkill()] }),
        ],
      }),
    ],
  });
  assert.doesNotThrow(() => Protocol.validateContextActionsPanel(panel));
});

test("duplicate skill keys across categories are rejected", () => {
  const panel = validCombatPanel({
    skills: [
      validCategoryGroup(),
      validCategoryGroup({
        category: "martial_arts",
        label: "武技",
        groups: [validSkillGroup({ group: null, label: null })],
      }),
    ],
  });
  assert.throws(() => Protocol.validateContextActionsPanel(panel));
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

// ---------------------------------------------------------------------------
// services panel schema (design D4).
// ---------------------------------------------------------------------------

function validServicesAction(overrides) {
  return Object.assign(
    {
      action_id: "guild.register",
      label: "註冊為冒險者",
      enabled: true,
      disabled_reason: null,
      quantity: null,
    },
    overrides || {}
  );
}

function validServicesBoardRow(overrides) {
  return Object.assign(
    {
      definition_key: "introductory_hunt",
      display_name: "討伐低階魔物",
      objective_summary: "討伐 1 隻低階魔物",
      reward_summary: "獎勵：銅 50、功績 25、治療藥水 × 2",
      rank: "F",
      accept: validServicesAction({ action_id: "guild.quest_accept", label: "接取" }),
    },
    overrides || {}
  );
}

function validServicesQuestRow(overrides) {
  return Object.assign(
    {
      quest_id: "introductory_hunt:1",
      definition_key: "introductory_hunt",
      display_name: "討伐低階魔物",
      state: "in_progress",
      stage_index: 0,
      stage_progress: 0,
      objective_summary: "討伐 1 隻低階魔物",
      deadline_line: null,
      detail: "討伐低階魔物\n狀態：進行中\n階段：1\n目標：討伐 1 隻低階魔物\n進度：0 / 1\n獎勵：銅 50、功績 25、治療藥水 × 2",
      abandon: validServicesAction({ action_id: "guild.quest_abandon", label: "放棄" }),
      turnin: validServicesAction({
        action_id: "guild.quest_turnin",
        label: "回報",
        enabled: false,
        disabled_reason: { code: "quest_transition", message: "這個任務目前無法進行此操作。" },
      }),
    },
    overrides || {}
  );
}

function validServicesStockRow(overrides) {
  return Object.assign(
    {
      item_key: "meal",
      display_name: "普通餐食",
      buy_copper: 10,
      sell_copper: 5,
      stock: 20,
      max_stock: 20,
      buy: validServicesAction({ action_id: "shop.buy", label: "購買", quantity: { min: 1, max: 20 } }),
    },
    overrides || {}
  );
}

function validServicesSellableRow(overrides) {
  return Object.assign(
    {
      item_key: "meal",
      display_name: "普通餐食",
      sell_copper: 5,
      held: 2,
      sell: validServicesAction({ action_id: "shop.sell", label: "販賣", quantity: { min: 1, max: 2 } }),
    },
    overrides || {}
  );
}

function validServicesPanel(overrides) {
  return Object.assign(
    {
      schema_version: 1,
      available: true,
      kind: "services",
      host: null,
      player: {
        wallet: 1000,
        guild_registered: false,
        guild_rank: null,
        guild_merit: 0,
        next_rank: null,
        next_threshold: null,
      },
      guild: {
        registration: {
          registered: false,
          register: validServicesAction(),
        },
        board: [],
        quests: [],
        rank: null,
      },
      shop: null,
      inventory: {
        rows: [{ item_key: "meal", display_name: "普通餐食", held: 1, equipped: false }],
        wallet: 1000,
      },
      pagination: {
        board_total: 0,
        quest_total: 0,
        stock_total: 0,
        sellable_total: 0,
        inventory_total: 1,
      },
    },
    overrides || {}
  );
}

test("validates the services panel available/unavailable discriminator", () => {
  assert.deepEqual(
    Protocol.validateServicesPanel(validServicesPanel()),
    validServicesPanel()
  );
  const unavailable = {
    schema_version: 1,
    available: false,
    reason: { code: "services_unavailable", message: "服務選單目前無法顯示" },
  };
  assert.deepEqual(Protocol.validateServicesPanel(unavailable), unavailable);
  assert.throws(() => Protocol.validateServicesPanel({ ...validServicesPanel(), kind: "combat" }));
  assert.throws(() => Protocol.validateServicesPanel({ ...validServicesPanel(), available: "yes" }));
});

test("services panel rejects unknown-surface and malformed fields", () => {
  assert.throws(() =>
    Protocol.validateServicesPanel({ ...validServicesPanel(), secret: 1 })
  );
  assert.throws(() =>
    Protocol.validateServicesPanel({ ...validServicesPanel(), host: { identity: "公會長", display_name: "x" } })
  );
  assert.throws(() =>
    Protocol.validateServicesPanel({
      ...validServicesPanel(),
      player: { ...validServicesPanel().player, guild_registered: true, guild_rank: null },
    })
  );
  assert.throws(() =>
    Protocol.validateServicesPanel({
      ...validServicesPanel(),
      guild: {
        ...validServicesPanel().guild,
        board: [
          validServicesBoardRow({ accept: validServicesAction({ action_id: "guild.register" }) }),
        ],
      },
      pagination: { ...validServicesPanel().pagination, board_total: 1 },
    })
  );
});

test("services panel enforces quantity bounds and unknown-node-style rejection", () => {
  const panel = validServicesPanel({
    shop: {
      open: true,
      stock: [validServicesStockRow({ buy: validServicesAction({ action_id: "shop.buy" }) })],
      sellable: [],
    },
    pagination: { ...validServicesPanel().pagination, stock_total: 1 },
  });
  assert.throws(() => Protocol.validateServicesPanel(panel), /quantity bounds/);
  const panel2 = validServicesPanel({
    shop: {
      open: true,
      stock: [
        validServicesStockRow({
          buy: validServicesAction({
            action_id: "shop.buy",
            quantity: { min: 1, max: Protocol.SERVICES_MAX_QUANTITY + 1 },
          }),
        }),
      ],
      sellable: [],
    },
    pagination: { ...validServicesPanel().pagination, stock_total: 1 },
  });
  assert.throws(() => Protocol.validateServicesPanel(panel2), /quantity/);
  const booleanQuantity = validServicesPanel({
    shop: {
      open: true,
      stock: [
        validServicesStockRow({
          buy: validServicesAction({ action_id: "shop.buy", quantity: { min: 1, max: true } }),
        }),
      ],
      sellable: [],
    },
    pagination: { ...validServicesPanel().pagination, stock_total: 1 },
  });
  assert.throws(() => Protocol.validateServicesPanel(booleanQuantity), /quantity/);
});

test("services panel enforces row ceilings for every surface", () => {
  const board = [];
  for (let i = 0; i < Protocol.SERVICES_MAX_BOARD_ROWS + 1; i++) {
    board.push(validServicesBoardRow());
  }
  assert.throws(() =>
    Protocol.validateServicesPanel(
      validServicesPanel({
        guild: { ...validServicesPanel().guild, board },
        pagination: { ...validServicesPanel().pagination, board_total: board.length },
      })
    )
  );
  const inventory = [];
  for (let i = 0; i < Protocol.SERVICES_MAX_INVENTORY_ROWS + 1; i++) {
    inventory.push({ item_key: "meal", display_name: "普通餐食", held: 1, equipped: false });
  }
  assert.throws(() =>
    Protocol.validateServicesPanel(
      validServicesPanel({
        inventory: { rows: inventory, wallet: 0 },
        pagination: { ...validServicesPanel().pagination, inventory_total: inventory.length },
      })
    )
  );
});

test("services panel pagination must match shipped rows and null surfaces", () => {
  assert.throws(() =>
    Protocol.validateServicesPanel({
      ...validServicesPanel(),
      guild: null,
      pagination: { ...validServicesPanel().pagination, board_total: 1 },
    })
  );
  const withRows = validServicesPanel({
    guild: {
      registration: { registered: true, register: validServicesAction({ enabled: false, disabled_reason: { code: "already_registered", message: "你已經是冒險者了。" } }) },
      board: [validServicesBoardRow()],
      quests: [validServicesQuestRow()],
      rank: null,
    },
    player: {
      wallet: 1000,
      guild_registered: true,
      guild_rank: "F",
      guild_merit: 60,
      next_rank: "E",
      next_threshold: 50,
    },
    pagination: { ...validServicesPanel().pagination, board_total: 1, quest_total: 1 },
  });
  assert.deepEqual(Protocol.validateServicesPanel(withRows), withRows);
  assert.throws(() =>
    Protocol.validateServicesPanel({
      ...withRows,
      pagination: { ...withRows.pagination, board_total: 0 },
    })
  );
});

test("a structurally maximal realistic services payload fits the envelope", () => {
  const board = [];
  const quests = [];
  const stock = [];
  const sellable = [];
  const inventory = [];
  for (let i = 0; i < Protocol.SERVICES_MAX_BOARD_ROWS; i++) {
    board.push(validServicesBoardRow());
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_QUEST_ROWS; i++) {
    quests.push(validServicesQuestRow());
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_STOCK_ROWS; i++) {
    stock.push(validServicesStockRow());
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_SELLABLE_ROWS; i++) {
    sellable.push(validServicesSellableRow());
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_INVENTORY_ROWS; i++) {
    inventory.push({ item_key: "meal", display_name: "普通餐食", held: 2, equipped: false });
  }
  const panel = validServicesPanel({
    guild: {
      registration: { registered: true, register: validServicesAction({ enabled: false, disabled_reason: { code: "already_registered", message: "你已經是冒險者了。" } }) },
      board: board,
      quests: quests,
      rank: {
        rank: "F",
        merit: 60,
        next_rank: "E",
        next_threshold: 50,
        eligible: true,
        exam_start: validServicesAction({ action_id: "guild.exam_start", label: "升階考核（E）" }),
      },
    },
    shop: { open: true, stock: stock, sellable: sellable },
    inventory: { rows: inventory, wallet: 1000000 },
    pagination: {
      board_total: Protocol.SERVICES_MAX_BOARD_ROWS,
      quest_total: Protocol.SERVICES_MAX_QUEST_ROWS,
      stock_total: Protocol.SERVICES_MAX_STOCK_ROWS,
      sellable_total: Protocol.SERVICES_MAX_SELLABLE_ROWS,
      inventory_total: Protocol.SERVICES_MAX_INVENTORY_ROWS,
    },
  });
  assert.doesNotThrow(() => Protocol.validateServicesPanel(panel));
  assert.ok(Protocol.jsonByteSize(panel) <= Protocol.MAX_CANONICAL_JSON_BYTES);
});

test("services payload maximizing every string field fails the byte gate", () => {
  // Every string field at its bound on every surface simultaneously. Each
  // field is individually in bounds, so only the serialized-size gate can
  // reject it (design D4).
  const max64 = "獎".repeat(Protocol.SERVICES_MAX_KEY);
  const max128 = "獎".repeat(Protocol.SERVICES_MAX_DISPLAY_NAME);
  const maxDetail = "獎".repeat(Protocol.SERVICES_MAX_DETAIL);
  const board = [];
  const quests = [];
  const stock = [];
  const sellable = [];
  const inventory = [];
  for (let i = 0; i < Protocol.SERVICES_MAX_BOARD_ROWS; i++) {
    board.push({
      definition_key: max64,
      display_name: max128,
      objective_summary: max128,
      reward_summary: max128,
      rank: max64.slice(0, Protocol.SERVICES_MAX_RANK_KEY),
      accept: validServicesAction({ action_id: "guild.quest_accept" }),
    });
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_QUEST_ROWS; i++) {
    quests.push({
      quest_id: max64,
      definition_key: max64,
      display_name: max128,
      state: "in_progress",
      stage_index: 0,
      stage_progress: 0,
      objective_summary: max128,
      deadline_line: max64.slice(0, Protocol.SERVICES_MAX_DEADLINE_LINE),
      detail: maxDetail,
      abandon: validServicesAction({ action_id: "guild.quest_abandon" }),
      turnin: validServicesAction({
        action_id: "guild.quest_turnin",
        enabled: false,
        disabled_reason: { code: "quest_transition", message: max64 },
      }),
    });
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_STOCK_ROWS; i++) {
    stock.push({
      item_key: max64,
      display_name: max128,
      buy_copper: 10,
      sell_copper: 5,
      stock: 20,
      max_stock: 20,
      buy: validServicesAction({
        action_id: "shop.buy",
        enabled: false,
        disabled_reason: { code: "insufficient_stock", message: max64 },
      }),
    });
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_SELLABLE_ROWS; i++) {
    sellable.push({
      item_key: max64,
      display_name: max128,
      sell_copper: 5,
      held: 20,
      sell: validServicesAction({
        action_id: "shop.sell",
        enabled: false,
        disabled_reason: { code: "stock_overflow", message: max64 },
      }),
    });
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_INVENTORY_ROWS; i++) {
    inventory.push({ item_key: max64, display_name: max128, held: 20, equipped: false });
  }
  const panel = validServicesPanel({
    host: {
      identity: "1".repeat(Protocol.SERVICES_MAX_KEY),
      display_name: max128.repeat(2).slice(0, Protocol.SERVICES_MAX_HOST_DISPLAY_NAME),
    },
    player: {
      wallet: 0,
      guild_registered: true,
      guild_rank: "F",
      guild_merit: 0,
      next_rank: "E",
      next_threshold: 1,
    },
    guild: {
      registration: {
        registered: true,
        register: validServicesAction({
          enabled: false,
          disabled_reason: { code: "already_registered", message: max64 },
        }),
      },
      board: board,
      quests: quests,
      rank: {
        rank: "F",
        merit: 0,
        next_rank: "E",
        next_threshold: 1,
        eligible: false,
        exam_start: validServicesAction({
          action_id: "guild.exam_start",
          enabled: false,
          disabled_reason: { code: "below_threshold", message: max64 },
        }),
      },
    },
    shop: { open: false, stock: stock, sellable: sellable },
    inventory: { rows: inventory, wallet: 0 },
    pagination: {
      board_total: Protocol.SERVICES_MAX_BOARD_ROWS,
      quest_total: Protocol.SERVICES_MAX_QUEST_ROWS,
      stock_total: Protocol.SERVICES_MAX_STOCK_ROWS,
      sellable_total: Protocol.SERVICES_MAX_SELLABLE_ROWS,
      inventory_total: Protocol.SERVICES_MAX_INVENTORY_ROWS,
    },
  });
  assert.throws(() => Protocol.validateServicesPanel(panel), /envelope/);
});

test("services is in the production panel allowlist and a bad panel rejects atomically", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.services, 1);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 1,
    mode: "exploration",
    panels: {
      services: { ...validServicesPanel(), kind: "bogus" },
    },
    layout_version: 1,
    server_time: serverTime(),
  };
  const store = Protocol.createStore();
  store.beginTransport(1);
  const accepted = store.receive(1, "ui_snapshot", [envelope], {});
  assert.equal(accepted.accepted, false);
  assert.equal(accepted.reason, "invalid");
  assert.equal(store.getState().phase, "awaiting_initial_snapshot");
});

// ---------------------------------------------------------------------------
// art panel v1 (mirror of web.webclient.presentation.art, webclient-art-panel).
// ---------------------------------------------------------------------------

function validArtScene(overrides) {
  return deepMerge(
    {
      archetype: "tavern_interior",
      label: "酒館內部",
      subject_key: "scene:tavern_interior",
      status: "done",
      url: "/art/scene/tavern_interior.png",
      aspect_ratio: "16:9",
      alt: "酒館內部場景",
      placeholder: null,
    },
    overrides
  );
}

function validArtCatalogEntry(overrides) {
  return deepMerge(
    {
      subject_key: "portrait:monster:low",
      status: "done",
      url: "/art/portrait/monster/low.png",
      aspect_ratio: "3:4",
      alt: "低階魔物",
      placeholder: null,
      context: { name: "哥布林", role: "敵方" },
    },
    overrides
  );
}

function validArtPanel(overrides) {
  return deepMerge(
    {
      schema_version: 1,
      available: true,
      kind: "scene",
      scene: validArtScene(),
      portrait_catalog: { "42": validArtCatalogEntry() },
    },
    overrides
  );
}

test("art is in the production panel allowlist and validates the available payload", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.art, 1);
  assert.doesNotThrow(() => Protocol.validateArtPanel(validArtPanel()));
  assert.doesNotThrow(() =>
    Protocol.validateArtPanel(
      validArtPanel({
        scene: validArtScene({
          archetype: "forest_path",
          status: "pending",
          url: null,
          placeholder: { kind: "missing", label: "未生成" },
        }),
        portrait_catalog: {
          "7": validArtCatalogEntry({
            subject_key: null,
            status: null,
            url: null,
            aspect_ratio: null,
            placeholder: { kind: "unavailable", label: "無法提供" },
            context: { name: "旅店主人", role: "對話對象" },
          }),
        },
      })
    )
  );
});

test("rejects malformed art panels atomically", () => {
  assert.throws(() => Protocol.validateArtPanel({ schema_version: 1, available: false }));
  assert.throws(() => Protocol.validateArtPanel(validArtPanel({ kind: "combat" })));
  assert.throws(() => Protocol.validateArtPanel(validArtPanel({ schema_version: 2 })));
  // A pending scene without a placeholder is untruthful.
  assert.throws(() =>
    Protocol.validateArtPanel(
      validArtPanel({
        scene: validArtScene({ status: "pending", url: null, placeholder: null }),
      })
    )
  );
  // A done scene must not carry a placeholder.
  assert.throws(() =>
    Protocol.validateArtPanel(
      validArtPanel({ scene: validArtScene({ placeholder: { kind: "missing", label: "未生成" } }) })
    )
  );
  // A same-origin URL restriction is enforced.
  assert.throws(() =>
    Protocol.validateArtPanel(
      validArtPanel({ scene: validArtScene({ url: "https://evil.test/x.png" }) })
    )
  );
  // Catalog keys must be opaque decimal strings.
  assert.throws(() =>
    Protocol.validateArtPanel(validArtPanel({ portrait_catalog: { abc: validArtCatalogEntry() } }))
  );
  // A malformed context role is rejected.
  assert.throws(() =>
    Protocol.validateArtPanel(
      validArtPanel({ portrait_catalog: { "42": validArtCatalogEntry({ context: { name: "x", role: "boss" } }) } })
    )
  );
});

// ---------------------------------------------------------------------------
// creation panel v1 (mirror of web.webclient.presentation.creation).
// ---------------------------------------------------------------------------

function validCreationPanel(overrides) {
  const axes = Protocol.CREATION_AXES.map((axis) => ({
    axis,
    label: axis === "hp" ? "生命值" : "配點",
    explanation: "測試說明",
    minimum: 0,
    maximum: 100,
  }));
  return deepMerge(
    {
      schema_version: 1,
      available: true,
      kind: "creation",
      draft: null,
      presets: [
        {
          key: "human_wanderer",
          display_name: "艾琳",
          race: "human",
          race_description: "人類",
          subrace: "human_commoner",
          emphasis: "均衡",
          background: "旅人",
        },
        {
          key: "elf_guardian",
          display_name: "瑟芮雅",
          race: "elf",
          race_description: "精靈",
          subrace: "fionnen",
          emphasis: "守護",
          background: "護衛",
        },
      ],
      custom: {
        name: { min_length: 1, max_length: 64 },
        adult: {
          age_minimum: 18,
          age_maximum: 10000,
          apparent_age_minimum: 18,
          apparent_age_maximum: 10000,
        },
        races: [
          { key: "human", description: "人類", subraces: ["human_commoner"] },
          { key: "elf", description: "精靈", subraces: ["fionnen", "ciaran"] },
        ],
        subraces: {
          human_commoner: { display_name_zh: "平民", common_name_zh: "普通平民", specialty: "工匠" },
          fionnen: { display_name_zh: "斐歐恩族", common_name_zh: "森林精靈", specialty: "射術" },
          ciaran: { display_name_zh: "基亞蘭族", common_name_zh: "黑暗精靈", specialty: "劍術" },
        },
        profiles: [
          { race: "human", subrace: "human_commoner", budget: 181, axes },
          { race: "elf", subrace: "fionnen", budget: 37, axes },
          { race: "elf", subrace: "ciaran", budget: 37, axes },
        ],
        affinity: {
          human: {
            maximum: 2,
            elements: [
              { key: "fire", label: "火" },
              { key: "water", label: "水" },
              { key: "wind", label: "風" },
              { key: "earth", label: "土" },
              { key: "lightning", label: "雷" },
              { key: "ice", label: "冰" },
              { key: "light", label: "光" },
              { key: "dark", label: "暗" },
            ],
          },
          beastfolk: {
            maximum: 1,
            elements: [
              { key: "fire", label: "火" },
              { key: "water", label: "水" },
              { key: "wind", label: "風" },
              { key: "earth", label: "土" },
              { key: "lightning", label: "雷" },
              { key: "ice", label: "冰" },
              { key: "light", label: "光" },
              { key: "dark", label: "暗" },
            ],
          },
          elf: {
            maximum: 0,
            elements: [
              { key: "fire", label: "火" },
              { key: "water", label: "水" },
              { key: "wind", label: "風" },
              { key: "earth", label: "土" },
              { key: "lightning", label: "雷" },
              { key: "ice", label: "冰" },
              { key: "light", label: "光" },
              { key: "dark", label: "暗" },
            ],
          },
        },
      },
    },
    overrides
  );
}

test("accepts a valid creation panel and the common unavailable form", () => {
  assert.doesNotThrow(() => Protocol.validateCreationPanel(validCreationPanel()));
  assert.doesNotThrow(() =>
    Protocol.validateCreationPanel({
      schema_version: 1,
      available: false,
      reason: { code: "creation_unavailable", message: "角色建立畫面目前無法顯示" },
    })
  );
});

test("creation panel rejects malformed and unknown-node fields", () => {
  assert.throws(() => Protocol.validateCreationPanel(validCreationPanel({ extra: 1 })));
  assert.throws(() => Protocol.validateCreationPanel(validCreationPanel({ kind: "services" })));
  assert.throws(() => Protocol.validateCreationPanel(validCreationPanel({ schema_version: 2 })));
  const badDraft = validCreationPanel({ draft: { mode: "preset", stage: "custom_filled", preset_key: "x" } });
  assert.throws(() => Protocol.validateCreationPanel(badDraft));
  const personaCard = validCreationPanel();
  personaCard.presets[0].persona = "forbidden";
  assert.throws(() => Protocol.validateCreationPanel(personaCard));
  const unknownProfile = validCreationPanel();
  unknownProfile.custom.profiles[0].axes[0].axis = "luck";
  assert.throws(() => Protocol.validateCreationPanel(unknownProfile));
  const wrongAxes = validCreationPanel();
  wrongAxes.custom.profiles[0].axes = wrongAxes.custom.profiles[0].axes.slice(0, 5);
  assert.throws(() => Protocol.validateCreationPanel(wrongAxes));
});

test("creation panel accepts a valid concept draft with the background indicator", () => {
  const payload = validCreationPanel({
    draft: {
      mode: "concept",
      stage: "concept_filled",
      race: "human",
      subrace: "human_commoner",
      background: null,
      allocations: {
        hp: 50,
        mp: 50,
        sp: 50,
        atk_phys: 10,
        agility: 10,
        defense: 11,
      },
      background_generated: true,
    },
  });
  const validated = Protocol.validateCreationPanel(payload);
  assert.equal(validated.draft.mode, "concept");
  assert.equal(validated.draft.stage, "concept_filled");
  assert.equal(validated.draft.background_generated, true);
  assert.equal(validated.draft.allocations.hp, 50);
  const badStage = validCreationPanel({
    draft: {
      mode: "concept",
      stage: "custom_filled",
      race: "human",
      subrace: "human_commoner",
      background: null,
      allocations: {
        hp: 50,
        mp: 50,
        sp: 50,
        atk_phys: 10,
        agility: 10,
        defense: 11,
      },
      background_generated: true,
    },
  });
  assert.throws(() => Protocol.validateCreationPanel(badStage), /stage/);
  const badIndicator = validCreationPanel({
    draft: {
      mode: "concept",
      stage: "concept_filled",
      race: "human",
      subrace: "human_commoner",
      background: null,
      allocations: {
        hp: 50,
        mp: 50,
        sp: 50,
        atk_phys: 10,
        agility: 10,
        defense: 11,
      },
      background_generated: "yes",
    },
  });
  assert.throws(() => Protocol.validateCreationPanel(badIndicator), /boolean/);
  const leakedPersona = validCreationPanel({
    draft: {
      mode: "concept",
      stage: "concept_filled",
      race: "human",
      subrace: "human_commoner",
      background: null,
      allocations: {
        hp: 50,
        mp: 50,
        sp: 50,
        atk_phys: 10,
        agility: 10,
        defense: 11,
      },
      background_generated: true,
      persona: { personality: "沉穩" },
    },
  });
  assert.throws(() => Protocol.validateCreationPanel(leakedPersona), /unknown/);
});

test("creation panel enforces per-field bounds", () => {
  assert.throws(() =>
    Protocol.validateCreationPanel(validCreationPanel({ presets: [] }))
  );
  const oversizePresets = validCreationPanel();
  while (oversizePresets.presets.length < Protocol.CREATION_MAX_PRESETS + 1) {
    oversizePresets.presets.push(oversizePresets.presets[0]);
  }
  assert.throws(() => Protocol.validateCreationPanel(oversizePresets));
  const longPresetKey = validCreationPanel();
  longPresetKey.presets[0].key = "x".repeat(Protocol.CREATION_MAX_PRESET_KEY + 1);
  assert.throws(() => Protocol.validateCreationPanel(longPresetKey));
  const underageDraft = validCreationPanel({
    draft: {
      mode: "custom",
      stage: "custom_filled",
      display_name: "新角色",
      age: 17,
      apparent_age: 20,
      race: "human",
      subrace: "human_commoner",
      background: null,
      allocations: { hp: 0, mp: 0, sp: 0, atk_phys: 0, agility: 0, defense: 0 },
      background_generated: false,
      affinity_elements: [],
    },
  });
  assert.throws(() => Protocol.validateCreationPanel(underageDraft));
  const badAllocations = validCreationPanel({
    draft: {
      mode: "custom",
      stage: "custom_filled",
      display_name: "新角色",
      age: 20,
      apparent_age: 20,
      race: "human",
      subrace: "human_commoner",
      background: null,
      allocations: { hp: 0 },
      background_generated: false,
      affinity_elements: [],
    },
  });
  assert.throws(() => Protocol.validateCreationPanel(badAllocations));
});

test("a structurally maximal realistic creation payload fits the envelope", () => {
  const payload = validCreationPanel();
  assert.ok(Protocol.jsonByteSize(payload) < Protocol.MAX_CANONICAL_JSON_BYTES / 4);
});

test("creation payload maximizing every string field fails the byte gate", () => {
  const huge = "x".repeat(Protocol.CREATION_MAX_EXPLANATION);
  const axes = Protocol.CREATION_AXES.map((axis, index) => ({
    axis,
    label: "x".repeat(Protocol.CREATION_MAX_LABEL - 1) + String(index),
    explanation: huge,
    minimum: 0,
    maximum: 10000,
  }));
  const card = {
    key: "p".repeat(Protocol.CREATION_MAX_PRESET_KEY),
    display_name: "x".repeat(Protocol.CREATION_MAX_DISPLAY_NAME),
    race: "r".repeat(Protocol.CREATION_MAX_RACE_KEY),
    race_description: "x".repeat(Protocol.CREATION_MAX_DESCRIPTION),
    subrace: "s".repeat(Protocol.CREATION_MAX_SUBRACE_KEY),
    emphasis: "x".repeat(Protocol.CREATION_MAX_EMPHASIS),
    background: "x".repeat(Protocol.CREATION_MAX_BACKGROUND),
  };
  const race = {
    key: "r".repeat(Protocol.CREATION_MAX_RACE_KEY),
    description: "x".repeat(Protocol.CREATION_MAX_DESCRIPTION),
    subraces: Array(Protocol.CREATION_MAX_SUBRACES).fill("s".repeat(Protocol.CREATION_MAX_SUBRACE_KEY)),
  };
  const subraceEntry = {
    display_name_zh: "x".repeat(Protocol.CREATION_MAX_SPECIALTY),
    common_name_zh: "x".repeat(Protocol.CREATION_MAX_SPECIALTY),
    specialty: "x".repeat(Protocol.CREATION_MAX_SPECIALTY),
  };
  const subraces = {};
  for (let i = 0; i < Protocol.CREATION_MAX_SUBRACES; i++) {
    subraces["s" + i] = Object.assign({}, subraceEntry);
  }
  const profile = {
    race: "r".repeat(Protocol.CREATION_MAX_RACE_KEY),
    subrace: "s".repeat(Protocol.CREATION_MAX_SUBRACE_KEY),
    budget: 999999,
    axes,
  };
  const affinityElement = {
    key: "fire",
    label: "x".repeat(Protocol.CREATION_MAX_LABEL),
  };
  const affinityElements = ["fire", "water", "wind", "earth", "lightning", "ice", "light", "dark"].map(
    (key) => Object.assign({}, affinityElement, { key })
  );
  const payload = {
    schema_version: 1,
    available: true,
    kind: "creation",
    draft: null,
    presets: Array(Protocol.CREATION_MAX_PRESETS).fill(Object.assign({}, card)),
    custom: {
      name: { min_length: 1, max_length: 64 },
      adult: {
        age_minimum: 18,
        age_maximum: 10000,
        apparent_age_minimum: 18,
        apparent_age_maximum: 10000,
      },
      races: Array(Protocol.CREATION_MAX_RACES).fill(Object.assign({}, race)),
      subraces,
      profiles: Array(Protocol.CREATION_MAX_PROFILES).fill(Object.assign({}, profile)),
      affinity: {
        human: { maximum: 2, elements: affinityElements },
        beastfolk: { maximum: 1, elements: affinityElements },
        elf: { maximum: 0, elements: affinityElements },
      },
    },
  };
  assert.ok(Protocol.jsonByteSize(payload) > Protocol.MAX_CANONICAL_JSON_BYTES);
  assert.throws(() => Protocol.validateCreationPanel(payload), /envelope/);
});

test("creation is in the production panel allowlist and a bad panel rejects atomically", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.creation, 1);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 1,
    mode: "creation",
    panels: { creation: { ...validCreationPanel(), kind: "bogus" } },
    layout_version: 1,
    server_time: serverTime(),
  };
  const store = Protocol.createStore();
  store.beginTransport(1);
  const accepted = store.receive(1, "ui_snapshot", [envelope], {});
  assert.equal(accepted.accepted, false);
  assert.equal(accepted.reason, "invalid");
  assert.equal(store.getState().phase, "awaiting_initial_snapshot");
});

// ---------------------------------------------------------------------------
// exploration panel v1 (design D10)
// ---------------------------------------------------------------------------

function validExplorationKeyword(overrides) {
  return Object.assign({ keyword_id: "公會", label: "公會" }, overrides || {});
}

function validExplorationAffordance(overrides) {
  return Object.assign(
    {
      kind: "action",
      action_id: "explore.talk_scripted",
      label: "交談",
      enabled: true,
      disabled_reason: null,
    },
    overrides || {}
  );
}

function validExplorationMoveRow(overrides) {
  return Object.assign(
    {
      exit_ref: "42",
      label: "東",
      destination: "room:7",
      enabled: true,
      disabled_reason: null,
    },
    overrides || {}
  );
}

function validExplorationLookEntity(overrides) {
  return Object.assign(
    { identity: 5, display_name: "南門守衛", kind: "npc", portrait_ref: null },
    overrides || {}
  );
}

function validExplorationLookObject(overrides) {
  return Object.assign({ identity: 6, display_name: "木箱" }, overrides || {});
}

function validExplorationTarget(overrides) {
  return Object.assign(
    {
      identity: 5,
      display_name: "南門守衛",
      portrait_ref: null,
      affordances: [validExplorationAffordance()],
      keywords: [validExplorationKeyword()],
    },
    overrides || {}
  );
}

function validExplorationPanel(overrides) {
  return Object.assign(
    {
      schema_version: 1,
      available: true,
      kind: "exploration",
      move: [validExplorationMoveRow()],
      look: {
        room: { identity: 3, display_name: "南門", room: true },
        entities: [validExplorationLookEntity()],
        objects: [validExplorationLookObject()],
      },
      interact: [validExplorationTarget()],
      character: { available: true },
      quests: { available: true },
      inventory: { available: true },
    },
    overrides || {}
  );
}

test("validates the exploration panel available/unavailable discriminator", () => {
  assert.deepEqual(
    Protocol.validateExplorationPanel(unavailableStatusPanel()),
    unavailableStatusPanel()
  );
  assert.doesNotThrow(() => Protocol.validateExplorationPanel(validExplorationPanel()));
  assert.throws(() => Protocol.validateExplorationPanel(validExplorationPanel({ extra: 1 })));
  assert.throws(() => Protocol.validateExplorationPanel(validExplorationPanel({ kind: "services" })));
  assert.throws(() => Protocol.validateExplorationPanel(validExplorationPanel({ schema_version: 2 })));
});

test("enforces exploration D10 bounds", () => {
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        move: Array(Protocol.EXPLORATION_MAX_MOVE_EXITS + 1).fill(validExplorationMoveRow()),
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        move: [validExplorationMoveRow({ exit_ref: "x".repeat(Protocol.EXPLORATION_MAX_EXIT_REF + 1) })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        move: [validExplorationMoveRow({ exit_ref: "中文" })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        move: [validExplorationMoveRow({ destination: "not:a:node" })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        look: {
          ...validExplorationPanel().look,
          entities: Array(Protocol.EXPLORATION_MAX_LOOK_ENTITIES + 1).fill(validExplorationLookEntity()),
        },
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        look: {
          ...validExplorationPanel().look,
          objects: Array(Protocol.EXPLORATION_MAX_LOOK_OBJECTS + 1).fill(validExplorationLookObject()),
        },
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: Array(Protocol.EXPLORATION_MAX_INTERACT_TARGETS + 1).fill(validExplorationTarget()),
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            affordances: Array(Protocol.EXPLORATION_MAX_AFFORDANCES + 1).fill(
              {
                kind: "action",
                action_id: "explore.engage",
                label: "戰鬥",
                enabled: true,
                disabled_reason: null,
              }
            ),
          }),
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            keywords: Array(Protocol.EXPLORATION_MAX_SCRIPTED_KEYWORDS + 1).fill(
              validExplorationKeyword()
            ),
          }),
        ],
      })
    )
  );
});

test("affordance shapes are exact in the exploration panel", () => {
  // navigate never carries an action_id; action never carries a surface.
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            affordances: [
              {
                kind: "navigate",
                action_id: "explore.talk_scripted",
                surface: "guild",
                label: "公會服務",
                enabled: true,
                disabled_reason: null,
              },
            ],
          }),
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            affordances: [
              {
                kind: "action",
                surface: "guild",
                label: "公會服務",
                enabled: true,
                disabled_reason: null,
              },
            ],
          }),
        ],
      })
    )
  );
  // Keywords require a talk_scripted affordance on the target.
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            affordances: [
              validExplorationAffordance({ action_id: "explore.engage" }),
            ],
          }),
        ],
      })
    )
  );
  // explore.take is outside the closed action set.
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            affordances: [
              {
                kind: "action",
                action_id: "explore.take",
                label: "拾取",
                enabled: true,
                disabled_reason: null,
              },
            ],
          }),
        ],
      })
    )
  );
  // explore.party_kick is outside the closed action set.
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            affordances: [
              {
                kind: "action",
                action_id: "explore.party_kick",
                label: "踢出",
                enabled: true,
                disabled_reason: null,
              },
            ],
          }),
        ],
      })
    )
  );
});

test("party invite and leave affordances are closed exploration actions", () => {
  assert.ok(
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            keywords: [],
            affordances: [
              validExplorationAffordance({
                action_id: "explore.party_invite",
                label: "邀請",
              }),
            ],
          }),
        ],
      })
    )
  );
  assert.ok(
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            keywords: [],
            affordances: [
              validExplorationAffordance({
                action_id: "explore.party_leave",
                label: "解散",
              }),
            ],
          }),
        ],
      })
    )
  );
});

test("exploration portrait_ref must be null and entries exact", () => {
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({ interact: [validExplorationTarget({ portrait_ref: "cat:goblin" })] })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        look: {
          ...validExplorationPanel().look,
          entities: [validExplorationLookEntity({ portrait_ref: "cat:goblin" })],
        },
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(validExplorationPanel({ quests: { available: "yes" } }))
  );
});

test("worst-case exploration payload fits the envelope and all-ceilings fails closed", () => {
  const interact = [];
  for (let i = 0; i < Protocol.EXPLORATION_MAX_INTERACT_TARGETS; i++) {
    const affordances = [validExplorationAffordance()];
    for (let j = 1; j < Protocol.EXPLORATION_MAX_AFFORDANCES; j++) {
      affordances.push({
        kind: "action",
        action_id: "explore.engage",
        label: "戰鬥",
        enabled: true,
        disabled_reason: null,
      });
    }
    interact.push(
      validExplorationTarget({
        identity: i + 1,
        affordances,
        keywords: Array(Protocol.EXPLORATION_MAX_SCRIPTED_KEYWORDS).fill(
          validExplorationKeyword()
        ),
      })
    );
  }
  const worst = validExplorationPanel({
    move: Array(Protocol.EXPLORATION_MAX_MOVE_EXITS).fill(validExplorationMoveRow()),
    look: {
      room: { identity: 3, display_name: "南門", room: true },
      entities: Array(Protocol.EXPLORATION_MAX_LOOK_ENTITIES).fill(validExplorationLookEntity()),
      objects: Array(Protocol.EXPLORATION_MAX_LOOK_OBJECTS).fill(validExplorationLookObject()),
    },
    interact,
  });
  const normalized = Protocol.validateExplorationPanel(worst);
  assert.ok(Protocol.jsonByteSize(normalized) <= Protocol.MAX_CANONICAL_JSON_BYTES);

  const overInteract = [];
  for (let i = 0; i < Protocol.EXPLORATION_MAX_INTERACT_TARGETS; i++) {
    overInteract.push(
      validExplorationTarget({
        identity: i + 1,
        affordances: Array(Protocol.EXPLORATION_MAX_AFFORDANCES).fill(
          validExplorationAffordance({ label: "交談".repeat(60) })
        ),
        keywords: Array(Protocol.EXPLORATION_MAX_SCRIPTED_KEYWORDS).fill(
          validExplorationKeyword({
            keyword_id: "k".repeat(Protocol.EXPLORATION_MAX_KEYWORD_ID),
            label: "話".repeat(Protocol.EXPLORATION_MAX_KEYWORD_LABEL),
          })
        ),
      })
    );
  }
  const over = validExplorationPanel({ interact: overInteract });
  assert.throws(() => Protocol.validateExplorationPanel(over), /envelope/);
});

test("exploration and character are in the production panel allowlist", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.exploration, 1);
  assert.equal(Protocol.PANEL_ALLOWLIST.character, 3);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 1,
    mode: "exploration",
    panels: { exploration: { ...validExplorationPanel(), kind: "bogus" } },
    layout_version: 1,
    server_time: serverTime(),
  };
  const store = Protocol.createStore();
  store.beginTransport(1);
  const accepted = store.receive(1, "ui_snapshot", [envelope], {});
  assert.equal(accepted.accepted, false);
  assert.equal(accepted.reason, "invalid");
});

// ---------------------------------------------------------------------------
// character panel v3 (design D10 + skill category grouping)
// ---------------------------------------------------------------------------

function validCharacterPanel(overrides) {
  return Object.assign(
    {
      schema_version: 3,
      available: true,
      kind: "character",
      traits: [
        { key: "hp", label: "生命", current: 10, max: 10 },
        { key: "atk_phys", label: "攻擊", current: 5, max: null },
      ],
      actives: [
        {
          category: "elemental_magic",
          label: "元素魔法",
          groups: [
            { group: "fire", label: "火", skills: [{ key: "fire_ball", label: "火球術" }] },
          ],
        },
      ],
      passives: [
        {
          category: "enhancement",
          label: "強化",
          groups: [
            {
              group: null,
              label: null,
              skills: [{ key: "defense_instinct", label: "防禦直覺" }],
            },
          ],
        },
      ],
      equipment: [
        { slot: "weapon_main", item_key: "plain_sword", display_name: "鐵劍" },
      ],
      disguise: { active: false, description: "", displayed: [] },
      guild: { rank: null, merit: 0 },
      wallet: 100,
      persona: { background: null },
    },
    overrides || {}
  );
}

function characterCategoryGroup(keys) {
  return {
    category: "elemental_magic",
    label: "元素魔法",
    groups: [
      {
        group: null,
        label: null,
        skills: keys.map(function (key) {
          return { key: key, label: key };
        }),
      },
    ],
  };
}

test("validates the character panel available/unavailable discriminator", () => {
  assert.deepEqual(
    Protocol.validateCharacterPanel(unavailableStatusPanel()),
    unavailableStatusPanel()
  );
  assert.doesNotThrow(() => Protocol.validateCharacterPanel(validCharacterPanel()));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ extra: 1 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ kind: "status" })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 1 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 2 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 4 })));
  const missing = validCharacterPanel();
  delete missing.actives;
  assert.throws(() => Protocol.validateCharacterPanel(missing));
});

test("enforces character D10 bounds and disguise honesty", () => {
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: Array(Protocol.CHARACTER_MAX_TRAIT_ROWS + 1).fill({
          key: "hp",
          label: "生命",
          current: 10,
          max: 10,
        }),
      })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [
          { key: "hp", label: "生命", current: 10, max: 10 },
          { key: "hp", label: "生命", current: 10, max: 10 },
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [{ key: "hp", label: "生命", current: 11, max: 10 }],
      })
    )
  );
  // An inactive disguise must not carry displayed rows.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        disguise: {
          active: false,
          description: "",
          displayed: [{ key: "atk_phys", label: "攻擊", value: 12 }],
        },
      })
    )
  );
  // A wallet is a non-negative safe integer.
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ wallet: -1 })));
});

test("character panel v3 validates the category-grouped skill shape", () => {
  // The null group/label pair must be consistent.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        passives: [
          {
            category: "enhancement",
            label: "強化",
            groups: [
              { group: "g", label: null, skills: [] },
            ],
          },
        ],
      })
    )
  );
  // A category group must carry a non-empty groups list.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        passives: [{ category: "enhancement", label: "強化", groups: [] }],
      })
    )
  );
  // Category-group count is bounded by the SkillCategory member count plus
  // the synthetic fallback slot; nine groups (eight real categories plus the
  // "unknown" fallback) must stay acceptable, ten must not.
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        actives: Array(Protocol.CHARACTER_MAX_CATEGORY_GROUPS).fill(
          characterCategoryGroup([])
        ),
      })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        actives: Array(Protocol.CHARACTER_MAX_CATEGORY_GROUPS + 1).fill(
          characterCategoryGroup([])
        ),
      })
    )
  );
  // The flattened row bound applies, not the category-group count.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        passives: [
          characterCategoryGroup(
            Array(Protocol.CHARACTER_MAX_PASSIVE_ROWS + 1).fill("skill")
          ),
        ],
      })
    )
  );
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        passives: [
          characterCategoryGroup(
            Array(Protocol.CHARACTER_MAX_PASSIVE_ROWS / 2).fill("skill")
          ),
          {
            category: "enhancement",
            label: "強化",
            groups: [
              {
                group: null,
                label: null,
                skills: Array(Protocol.CHARACTER_MAX_PASSIVE_ROWS / 2)
                  .fill("skill")
                  .map(function (key, index) {
                    return { key: "skill_" + index, label: "技能" };
                  }),
              },
            ],
          },
        ],
      })
    )
  );
});

test("character panel v3 persona.background round-trips bounded text", () => {
  const withBackground = Protocol.validateCharacterPanel(
    validCharacterPanel({ persona: { background: "  在公會登記的新人冒險者  " } })
  );
  assert.equal(withBackground.persona.background, "在公會登記的新人冒險者");
  const without = Protocol.validateCharacterPanel(
    validCharacterPanel({ persona: { background: null } })
  );
  assert.equal(without.persona.background, null);
  const blank = Protocol.validateCharacterPanel(
    validCharacterPanel({ persona: { background: "   " } })
  );
  assert.equal(blank.persona.background, null);
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        persona: { background: "x".repeat(Protocol.CHARACTER_MAX_BACKGROUND + 1) },
      })
    ),
    /exceeds/
  );
});
