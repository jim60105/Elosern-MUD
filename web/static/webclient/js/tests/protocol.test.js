/*
 * DOM-independent tests for the Elosern OOB protocol reducer.
 *
 * Runs with Node 24's built-in test runner and node:assert; no npm packages.
 * Covers the exact server envelope schemas/discriminators, atomic rejection,
 * transport-generation lifecycle, epoch/revision ordering, and complete panel
 * replacement.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");

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
  // Unavailable form is exact, through the real validatePanel dispatch path.
  assert.deepEqual(
    Protocol.validatePanel("status", Protocol.PANEL_ALLOWLIST.status, unavailableStatusPanel()),
    unavailableStatusPanel()
  );
  const badReason = unavailableStatusPanel();
  badReason.reason = { code: "x" };
  assert.throws(() =>
    Protocol.validatePanel("status", Protocol.PANEL_ALLOWLIST.status, badReason)
  );
  assert.throws(() =>
    Protocol.validatePanel(
      "status",
      Protocol.PANEL_ALLOWLIST.status,
      unavailableStatusPanel({ schema_version: 2 })
    )
  );
  // An internal reason carries a bounded correlation ID.
  assert.doesNotThrow(() =>
    Protocol.validatePanel(
      "status",
      Protocol.PANEL_ALLOWLIST.status,
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
  // Signed modifier values from the deterministic `combat_modifiers.yaml`
  // (e.g. defense -15, accuracy -10) must pass panel validation so the
  // full condition roster reaches the client's character-status drawer.
  assert.doesNotThrow(
    () =>
      Protocol.validateStatusPanel(
        validStatusPanel({
          conditions: [
            {
              code: "high_exposure_defense_penalty",
              label: "高露出",
              severity: "harmful",
              modifiers: { defense: -15, agility: -10 },
            },
          ],
        })
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

  // Over 320 list items.
  assert.throws(() => Protocol.checkGlobalSafety(new Array(322).fill(1)));
  // A 300-item affordance list is inside the global ceiling.
  assert.doesNotThrow(() => Protocol.checkGlobalSafety(new Array(300).fill({ x: 1 })));

  // Over-long string (code points).
  assert.throws(() => Protocol.checkGlobalSafety("x".repeat(3000)));

  // Non-finite numbers.
  assert.throws(() => Protocol.checkGlobalSafety({ value: Infinity }));
  assert.throws(() => Protocol.checkGlobalSafety({ value: NaN }));

  // The global integer bound is the full JavaScript-safe range: negative
  // safe integers (e.g. the signed values from the deterministic
  // combat_modifiers.yaml) are accepted; only values below -2^53 or above
  // 2^53 - 1 are rejected.
  assert.doesNotThrow(() => Protocol.checkGlobalSafety({ defense: -15 }));
  assert.doesNotThrow(() => Protocol.checkGlobalSafety({ value: -9007199254740991 }));
  assert.throws(() => Protocol.checkGlobalSafety({ value: -9007199254740992 }));

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
      schema_version: 5,
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
      suggestions: { status: "unavailable" },
    },
    overrides
  );
}

function validRecoveryPanel(overrides) {
  return deepMerge(
    {
      schema_version: 5,
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
      suggestions: { status: "unavailable" },
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
  assert.equal(Protocol.PANEL_ALLOWLIST.context_actions, 5);
});

function validSuggestions(overrides) {
  return deepMerge(
    {
      status: "unavailable",
    },
    overrides
  );
}

function validContextActionsExplorationPanel(overrides) {
  return deepMerge(
    {
      schema_version: 5,
      available: true,
      kind: "exploration",
      affordances: [],
      suggestions: validSuggestions(),
    },
    overrides
  );
}

test("validates the available context_actions exploration form", () => {
  const affordance = {
    action_id: "explore.talk_scripted",
    label: "註冊",
    params: { npc_id: 5, keyword_id: "註冊" },
    freeform: false,
    navigation: false,
    enabled: true,
    disabled_reason: null,
  };
  const panel = validContextActionsExplorationPanel({
    affordances: [
      {
        action_id: "explore.look",
        label: "南門",
        params: { room: true },
        freeform: false,
        navigation: false,
        enabled: true,
        disabled_reason: null,
      },
      affordance,
      {
        surface: "guild",
        label: "公會服務",
        navigation: true,
        enabled: true,
        disabled_reason: null,
      },
    ],
  });
  const normalized = Protocol.validateContextActionsPanel(panel);
  assert.equal(normalized.schema_version, 5);
  assert.equal(normalized.kind, "exploration");
  assert.equal(normalized.affordances.length, 3);
  assert.deepEqual(normalized.affordances[0].params, { room: true });
  assert.equal(normalized.affordances[1].freeform, false);
  assert.equal(normalized.affordances[2].navigation, true);
  assert.deepEqual(normalized.suggestions, { status: "unavailable" });
  // Cross-form contamination rejects on both sides.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      Object.assign(deepMerge(panel, {}), { session: {}, skills: [] })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      Object.assign(deepMerge(validCombatPanel(), {}), { affordances: [affordance] })
    )
  );
  // Malformed entries reject atomically.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [Object.assign({}, affordance, { action_id: "explore.interact" })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [
          Object.assign({}, affordance, {
            params: { npc_id: 5, keyword_id: "註冊", extra: 1 },
          }),
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [
          {
            surface: "bank",
            label: "公會",
            navigation: true,
            enabled: true,
            disabled_reason: null,
          },
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [Object.assign({}, affordance, { enabled: false, disabled_reason: null })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [Object.assign({}, affordance, { freeform: "yes" })],
      })
    )
  );
  // The 320-entry bound rejects.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: new Array(321).fill(affordance),
      })
    )
  );
  // The freeform entry accepts exactly the binding shape.
  assert.doesNotThrow(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [
          {
            action_id: "explore.talk_freeform",
            label: "自由交談",
            params: { npc_id: 9 },
            freeform: true,
            navigation: false,
            enabled: true,
            disabled_reason: null,
          },
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [
          {
            action_id: "explore.talk_freeform",
            label: "自由交談",
            params: { npc_id: 9, speech: "你好" },
            freeform: true,
            navigation: false,
            enabled: true,
            disabled_reason: null,
          },
        ],
      })
    )
  );
  // The freeform flag must pair with the action code on both sides.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [Object.assign({}, affordance, { freeform: true })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [
          {
            action_id: "explore.talk_freeform",
            label: "自由交談",
            params: { npc_id: 9 },
            freeform: false,
            navigation: false,
            enabled: true,
            disabled_reason: null,
          },
        ],
      })
    )
  );
});

test("validates suggestions envelopes per status", () => {
  // generating/unavailable carry only status.
  assert.deepEqual(Protocol.validateSuggestions({ status: "generating" }), {
    status: "generating",
  });
  assert.deepEqual(Protocol.validateSuggestions({ status: "unavailable" }), {
    status: "unavailable",
  });
  // ready requires 3..5 cards; degraded accepts 0..5.
  const card = {
    kind: "known_action",
    action_code: "explore.look",
    label: "查看房間",
    params: { room: true },
  };
  const readyCards = [
    card,
    { ...card, label: "前往東邊" },
    { ...card, label: "與路人交談" },
  ];
  assert.deepEqual(
    Protocol.validateSuggestions({ status: "ready", cards: readyCards }),
    { status: "ready", cards: readyCards.map((c) => Object.assign({}, c, { hint: null })) }
  );
  assert.doesNotThrow(() =>
    Protocol.validateSuggestions({ status: "degraded", cards: [] })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({ status: "ready", cards: [] })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({ status: "ready", cards: readyCards.slice(0, 2) })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: new Array(6).fill(card),
    })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({ status: "degraded", cards: new Array(6).fill(card) })
  );
  // Unknown status, extra/missing keys reject.
  assert.throws(() => Protocol.validateSuggestions({ status: "bogus" }));
  assert.throws(() =>
    Protocol.validateSuggestions({ status: "generating", cards: [] })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({ status: "unavailable", cards: [] })
  );
  assert.throws(() => Protocol.validateSuggestions({ status: "ready" }));
  assert.throws(() =>
    Protocol.validateSuggestions({ status: "ready", cards: readyCards, extra: 1 })
  );
  // A freeform card must pin explore.talk_freeform with the binding shape.
  assert.doesNotThrow(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        { ...card, label: "自由交談" },
        {
          kind: "freeform",
          action_code: "explore.talk_freeform",
          label: "隨意聊聊",
          params: { npc_id: 9 },
        },
        { ...card, label: "查看怪物" },
      ],
    })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        {
          kind: "freeform",
          action_code: "explore.move",
          label: "自由交談",
          params: { npc_id: 9 },
        },
        card,
        { ...card, label: "與路人交談" },
      ],
    })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        {
          kind: "freeform",
          action_code: "explore.talk_freeform",
          label: "自由交談",
          params: { npc_id: 9, speech: "你好" },
        },
        card,
        { ...card, label: "與路人交談" },
      ],
    })
  );
  // Non-CJK or over-long labels, over-long hints reject.
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        { ...card, label: "hello" },
        card,
        { ...card, label: "與路人交談" },
      ],
    })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        { ...card, label: "很".repeat(25) },
        card,
        { ...card, label: "與路人交談" },
      ],
    })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        { ...card, hint: "很".repeat(61) },
        card,
        { ...card, label: "與路人交談" },
      ],
    })
  );
  // Other booleans in params reject; the room-survey boolean is accepted.
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        {
          ...card,
          params: { room: false },
        },
        card,
        { ...card, label: "與路人交談" },
      ],
    })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        {
          ...card,
          params: { room: true, extra: 1 },
        },
        card,
        { ...card, label: "與路人交談" },
      ],
    })
  );
});

test("a 300-affordance exploration form passes the global envelope gate", () => {
  const affordance = {
    action_id: "explore.look",
    label: "南門",
    params: { room: true },
    freeform: false,
    navigation: false,
    enabled: true,
    disabled_reason: null,
  };
  const panel = validContextActionsExplorationPanel({
    affordances: new Array(300).fill(affordance),
  });
  // The global list ceiling (MAX_LIST_ITEMS) must clear the maximal
  // affordance list or the client would reject every snapshot for a large
  // room before panel validation ever runs.
  assert.doesNotThrow(() => Protocol.checkEnvelope(panel));
  assert.doesNotThrow(() => Protocol.validateContextActionsPanel(panel));
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      Object.assign({}, panel, {
        affordances: new Array(Protocol.CONTEXT_ACTIONS_MAX_AFFORDANCES + 1).fill(affordance),
      })
    )
  );
});

test("the combat form is byte-identical to version 4 plus suggestions", () => {
  const version4 = {
    schema_version: 4,
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
  };
  const version5 = validCombatPanel();
  assert.equal(version4.schema_version, 4);
  assert.equal(version5.schema_version, 5);
  const withoutVersion = (panel) => {
    const copy = Object.assign({}, panel);
    delete copy.schema_version;
    return copy;
  };
  // Every combat field serializes exactly as at version 4; only the version
  // field and the suggestions envelope are added.
  const version4Copy = Object.assign({}, version4, {
    suggestions: { status: "unavailable" },
  });
  assert.deepEqual(withoutVersion(version5), withoutVersion(version4Copy));
  assert.deepEqual(version5.suggestions, { status: "unavailable" });
  assert.doesNotThrow(() => Protocol.validateContextActionsPanel(version5));
  assert.throws(() => Protocol.validateContextActionsPanel(version4));
});

test("the unavailable forms differ only in schema_version", () => {
  const version4 = {
    schema_version: 4,
    available: false,
    reason: { code: "presentation_unavailable", message: "目前無法顯示此介面" },
  };
  const version5 = {
    schema_version: 5,
    available: false,
    reason: { code: "presentation_unavailable", message: "目前無法顯示此介面" },
  };
  const withoutVersion = (panel) => {
    const copy = Object.assign({}, panel);
    delete copy.schema_version;
    return copy;
  };
  assert.deepEqual(withoutVersion(version5), withoutVersion(version4));
  assert.doesNotThrow(() =>
    Protocol.validatePanel("context_actions", 5, version5)
  );
  assert.throws(() => Protocol.validatePanel("context_actions", 5, version4));
  // The unavailable form rejects a suggestions field: the field set stays
  // exactly schema_version/available/reason.
  assert.throws(() =>
    Protocol.validatePanel(
      "context_actions",
      5,
      Object.assign({}, version5, { suggestions: { status: "unavailable" } })
    )
  );
});

test("mirrors every registered panel schema version in the allowlist", () => {
  // The allowlist must cover all eight registered panels so an unmirrored
  // panel can never slip through the registered-version gate.
  assert.equal(Protocol.PANEL_ALLOWLIST.status, 1);
  assert.equal(Protocol.PANEL_ALLOWLIST.local_map, 1);
  assert.equal(Protocol.PANEL_ALLOWLIST.services, 3);
  assert.equal(Protocol.PANEL_ALLOWLIST.art, 1);
  assert.equal(Protocol.PANEL_ALLOWLIST.creation, 1);
  assert.equal(Protocol.PANEL_ALLOWLIST.exploration, 1);
  assert.equal(Protocol.PANEL_ALLOWLIST.character, 5);
  assert.equal(
    Object.keys(Protocol.PANEL_ALLOWLIST).length,
    8,
    "PANEL_ALLOWLIST must list exactly the eight registered panels"
  );
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
  assert.throws(() =>
    Protocol.validatePanel("context_actions", Protocol.PANEL_ALLOWLIST.context_actions, {
      schema_version: 5,
      available: false,
    })
  );
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
  // the top-level category-group count. A payload whose flattened total is
  // 193 must be rejected even though its category-group count is far below
  // the bound. Skills are spread across sub-groups so each group stays within
  // the global MAX_LIST_ITEMS bound — the panel's flattened total, not any
  // single array, is what must exceed MAX_SKILLS.
  const subGroups = [];
  for (let group = 0; group < 3; group++) {
    const skills = [];
    const count = group === 2 ? 65 : 64;
    for (let index = 1; index <= count; index++) {
      const flat = group * 64 + index;
      skills.push(validCombatSkill({ key: "skill_" + flat, label: "技能名稱" + flat }));
    }
    subGroups.push(validSkillGroup({ group: "group_" + group, label: "群組" + group, skills: skills }));
  }
  assert.throws(() =>
    Protocol.validateContextActionsPanel(validCombatPanel({ skills: [validCategoryGroup({ groups: subGroups })] }))
  );
  // 192 skills across the same shape still passes, and the payload also
  // satisfies the global envelope safety (every array within MAX_LIST_ITEMS,
  // canonical JSON within the byte bound) that the real client applies
  // before panel validation.
  subGroups[2].skills.pop();
  const accepted = validCombatPanel({ skills: [validCategoryGroup({ groups: subGroups })] });
  assert.doesNotThrow(() =>
    Protocol.validateContextActionsPanel(accepted)
  );
  assert.doesNotThrow(() => Protocol.checkEnvelope(accepted));
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

test("sexual_act sub-group keys accept Traditional Chinese line names", () => {
  // The act catalog keys sexual_act sub-groups by their Traditional Chinese
  // line names (獨處, 羞恥, 關係, 戰鬥); the group key is a bounded string,
  // not an ASCII identifier.
  const panel = validCombatPanel({
    skills: [
      validCategoryGroup({
        category: "sexual_act",
        label: "性愛行為",
        groups: [
          validSkillGroup({
            group: "獨處",
            label: "獨處",
            skills: [validCombatSkill({ key: "solo_self_touch" })],
          }),
          validSkillGroup({
            group: "戰鬥",
            label: "戰鬥",
            skills: [validCombatSkill({ key: "combat_tease" })],
          }),
        ],
      }),
    ],
  });
  assert.doesNotThrow(() => Protocol.validateContextActionsPanel(panel));
});

test("skill group keys reject empty or whitespace strings", () => {
  for (const bad of ["", "   "]) {
    const panel = validCombatPanel({
      skills: [
        validCategoryGroup({
          category: "sexual_act",
          label: "性愛行為",
          groups: [validSkillGroup({ group: bad, label: "獨處" })],
        }),
      ],
    });
    assert.throws(() => Protocol.validateContextActionsPanel(panel));
  }
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
    Protocol.validatePanel("local_map", Protocol.PANEL_ALLOWLIST.local_map, unavailableStatusPanel()),
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
      schema_version: 3,
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
        rows: [
          {
            item_key: "meal",
            display_name: "普通餐食",
            held: 1,
            equipped: false,
            action: null,
            presentation: {
              kind: "food",
              icon_key: "food",
              rarity: "common",
              summary: "供旅人充飢的普通餐食。",
            },
          },
          {
            item_key: "mystery_relic",
            display_name: "mystery_relic",
            held: 2,
            equipped: false,
            action: null,
            presentation: null,
          },
        ],
        wallet: 1000,
      },
      pagination: {
        board_total: 0,
        quest_total: 0,
        stock_total: 0,
        sellable_total: 0,
        inventory_total: 2,
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
    schema_version: 3,
    available: false,
    reason: { code: "services_unavailable", message: "服務選單目前無法顯示" },
  };
  assert.deepEqual(
    Protocol.validatePanel("services", Protocol.PANEL_ALLOWLIST.services, unavailable),
    unavailable
  );
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
    inventory.push({
      item_key: "meal",
      display_name: "普通餐食",
      held: 2,
      equipped: false,
      action: null,
      presentation: {
        kind: "food",
        icon_key: "food",
        rarity: "common",
        summary: "供旅人充飢的普通餐食。",
      },
    });
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
  const presKey = "k".repeat(Protocol.SERVICES_MAX_PRESENTATION_KEY);
  const presSummary = "獎".repeat(Protocol.SERVICES_MAX_PRESENTATION_SUMMARY);
  for (let i = 0; i < Protocol.SERVICES_MAX_INVENTORY_ROWS; i++) {
    inventory.push({
      item_key: max64,
      display_name: max128,
      held: 20,
      equipped: false,
      action: null,
      presentation: { kind: presKey, icon_key: presKey, rarity: presKey, summary: presSummary },
    });
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

test("services v3 accepts registered and unknown-key presentation rows", () => {
  const panel = validServicesPanel();
  const validated = Protocol.validateServicesPanel(panel);
  assert.deepEqual(validated, panel);
  const rows = validated.inventory.rows;
  const registered = rows.find((r) => r.item_key === "meal");
  assert.deepEqual(registered.presentation, {
    kind: "food",
    icon_key: "food",
    rarity: "common",
    summary: "供旅人充飢的普通餐食。",
  });
  const unknown = rows.find((r) => r.item_key === "mystery_relic");
  assert.equal(unknown.presentation, null);

  // The 240-code-point summary bound is inclusive on a small payload.
  const boundary = validServicesPanel();
  boundary.inventory.rows = [
    {
      item_key: "meal",
      display_name: "普通餐食",
      held: 1,
      equipped: false,
      action: null,
      presentation: {
        kind: "food",
        icon_key: "food",
        rarity: "common",
        summary: "獎".repeat(Protocol.SERVICES_MAX_PRESENTATION_SUMMARY),
      },
    },
  ];
  boundary.pagination.inventory_total = 1;
  assert.doesNotThrow(() => Protocol.validateServicesPanel(boundary));
});

test("services v3 rejects invalid presentation fields", () => {
  const mutate = (row) => {
    const p = validServicesPanel();
    p.inventory.rows = [row];
    p.pagination.inventory_total = 1;
    return p;
  };
  const missing = {
    item_key: "meal",
    display_name: "普通餐食",
    held: 1,
    equipped: false,
    action: null,
    presentation: { kind: "food", icon_key: "food", summary: "供旅人充飢的普通餐食。" },
  };
  assert.throws(() => Protocol.validateServicesPanel(mutate(missing)), /rarity/);

  const extra = {
    item_key: "meal",
    display_name: "普通餐食",
    held: 1,
    equipped: false,
    action: null,
    presentation: {
      kind: "food",
      icon_key: "food",
      rarity: "common",
      summary: "供旅人充飢的普通餐食。",
      color: "red",
    },
  };
  assert.throws(() => Protocol.validateServicesPanel(mutate(extra)), /unknown fields/);

  const overlong = {
    item_key: "meal",
    display_name: "普通餐食",
    held: 1,
    equipped: false,
    action: null,
    presentation: {
      kind: "k".repeat(Protocol.SERVICES_MAX_PRESENTATION_KEY + 1),
      icon_key: "food",
      rarity: "common",
      summary: "供旅人充飢的普通餐食。",
    },
  };
  assert.throws(() => Protocol.validateServicesPanel(mutate(overlong)), /kind/);

  const uppercase = {
    item_key: "meal",
    display_name: "普通餐食",
    held: 1,
    equipped: false,
    action: null,
    presentation: {
      kind: "Potion",
      icon_key: "food",
      rarity: "common",
      summary: "供旅人充飢的普通餐食。",
    },
  };
  assert.throws(() => Protocol.validateServicesPanel(mutate(uppercase)), /kind/);

  const longSummary = {
    item_key: "meal",
    display_name: "普通餐食",
    held: 1,
    equipped: false,
    action: null,
    presentation: {
      kind: "food",
      icon_key: "food",
      rarity: "common",
      summary: "獎".repeat(Protocol.SERVICES_MAX_PRESENTATION_SUMMARY + 1),
    },
  };
  assert.throws(() => Protocol.validateServicesPanel(mutate(longSummary)), /summary/);

  const notObject = {
    item_key: "meal",
    display_name: "普通餐食",
    held: 1,
    equipped: false,
    action: null,
    presentation: "food",
  };
  assert.throws(() => Protocol.validateServicesPanel(mutate(notObject)), /JSON object or null/);
});

test("services v1 payload is rejected by the v3 validator", () => {
  const panel = { ...validServicesPanel(), schema_version: 1 };
  panel.inventory.rows = panel.inventory.rows.map(({ presentation, ...rest }) => rest);
  assert.throws(() => Protocol.validateServicesPanel(panel), /schema_version/);
});

test("services v2 payload is rejected by the v3 validator", () => {
  const panel = { ...validServicesPanel(), schema_version: 2 };
  assert.throws(() => Protocol.validateServicesPanel(panel), /schema_version/);
});

test("services v3 validates inventory row actions exactly", () => {
  const good = validServicesPanel();
  good.inventory.rows[0].action = {
    action_id: "inventory.use",
    label: "使用",
    enabled: false,
    disabled_reason: { code: "hp_full", message: "你的體力已經全滿。" },
    quantity: null,
  };
  assert.deepEqual(
    Protocol.validateServicesPanel(good).inventory.rows[0].action,
    good.inventory.rows[0].action
  );
  const withQuantity = validServicesPanel();
  withQuantity.inventory.rows[0].action = {
    action_id: "inventory.use",
    label: "使用",
    enabled: true,
    disabled_reason: null,
    quantity: { min: 1, max: 2 },
  };
  assert.throws(() => Protocol.validateServicesPanel(withQuantity));
  const unknownId = validServicesPanel();
  unknownId.inventory.rows[0].action = {
    action_id: "inventory.drop",
    label: "丟棄",
    enabled: true,
    disabled_reason: null,
    quantity: null,
  };
  assert.throws(() => Protocol.validateServicesPanel(unknownId));
  const crossServiceId = validServicesPanel();
  crossServiceId.inventory.rows[0].action = {
    action_id: "shop.buy",
    label: "購買",
    enabled: true,
    disabled_reason: null,
    quantity: null,
  };
  assert.throws(() => Protocol.validateServicesPanel(crossServiceId));
  const toggleGood = validServicesPanel();
  toggleGood.inventory.rows[0].action = {
    action_id: "inventory.toggle_equip",
    label: "裝備",
    enabled: true,
    disabled_reason: null,
    quantity: null,
  };
  assert.doesNotThrow(() => Protocol.validateServicesPanel(toggleGood));
  const missing = validServicesPanel();
  delete missing.inventory.rows[0].action;
  assert.throws(() => Protocol.validateServicesPanel(missing));
});

test("services is in the production panel allowlist and a bad panel rejects atomically", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.services, 3);
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
  assert.throws(() =>
    Protocol.validatePanel("art", Protocol.PANEL_ALLOWLIST.art, {
      schema_version: 1,
      available: false,
    })
  );
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
    Protocol.validatePanel(
      "creation",
      Protocol.PANEL_ALLOWLIST.creation,
      {
        schema_version: 1,
        available: false,
        reason: { code: "creation_unavailable", message: "角色建立畫面目前無法顯示" },
      }
    )
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
    Protocol.validatePanel("exploration", Protocol.PANEL_ALLOWLIST.exploration, unavailableStatusPanel()),
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
  assert.equal(Protocol.PANEL_ALLOWLIST.character, 5);
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
// character panel v5 (design D10 + skill category grouping + breakdown rows)
// ---------------------------------------------------------------------------

function validCharacterTraitRow(overrides) {
  return Object.assign(
    {
      key: "hp",
      label: "生命",
      base: 10,
      current: 10,
      max: 10,
      effective: 10,
      layers: [],
    },
    overrides || {}
  );
}

function validCharacterTraitRowV4(overrides) {
  return Object.assign({ key: "hp", label: "生命", current: 10, max: 10 }, overrides || {});
}

function validCharacterPanel(overrides) {
  return Object.assign(
    {
      schema_version: 5,
      available: true,
      kind: "character",
      traits: [
        validCharacterTraitRow(),
        validCharacterTraitRow({
          key: "atk_phys",
          label: "攻擊",
          base: 3,
          current: 5,
          max: null,
          effective: 5,
          layers: [{ source: "equipment", name: "鐵劍", kind: "flat", amount: 2 }],
        }),
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
        { slot: "weapon_main", item_key: "plain_sword", display_name: "鐵劍", adjustment: "攻擊 +2" },
      ],
      disguise: { active: false, description: "", displayed: [] },
      guild: { rank: null, merit: 0 },
      wallet: 100,
      persona: { background: null },
      intimate: null,
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
  // The unavailable fixture carries the registered version (5), and the real
  // validatePanel dispatch path is exercised. The retained legacy v4 branch
  // is accepted on both forms; every other version rejects.
  assert.deepEqual(
    Protocol.validatePanel(
      "character",
      Protocol.PANEL_ALLOWLIST.character,
      unavailableStatusPanel({ schema_version: 5 })
    ),
    unavailableStatusPanel({ schema_version: 5 })
  );
  assert.deepEqual(
    Protocol.validatePanel(
      "character",
      Protocol.PANEL_ALLOWLIST.character,
      unavailableStatusPanel({ schema_version: 4 })
    ),
    unavailableStatusPanel({ schema_version: 4 })
  );
  assert.throws(() =>
    Protocol.validatePanel(
      "character",
      Protocol.PANEL_ALLOWLIST.character,
      unavailableStatusPanel({ schema_version: 2 })
    )
  );
  assert.throws(() =>
    Protocol.validatePanel(
      "character",
      Protocol.PANEL_ALLOWLIST.character,
      unavailableStatusPanel({ schema_version: 6 })
    )
  );
  assert.doesNotThrow(() => Protocol.validateCharacterPanel(validCharacterPanel()));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ extra: 1 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ kind: "status" })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 1 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 2 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 3 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 6 })));
  // The retained legacy branch: a byte-identical v4 payload still validates,
  // and a v5 row under version 4 (or a v4 row under 5) rejects.
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        schema_version: 4,
        traits: [validCharacterTraitRowV4(), validCharacterTraitRowV4({ key: "atk_phys", label: "攻擊", current: 5, max: null })],
        equipment: [{ slot: "weapon_main", item_key: "plain_sword", display_name: "鐵劍" }],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 4 }))
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ traits: [validCharacterTraitRowV4()] })
    )
  );
  const missing = validCharacterPanel();
  delete missing.actives;
  assert.throws(() => Protocol.validateCharacterPanel(missing));
  const missingIntimate = validCharacterPanel();
  delete missingIntimate.intimate;
  assert.throws(() => Protocol.validateCharacterPanel(missingIntimate));
});

test("a character unavailable snapshot at the registered version is accepted atomically", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);
  const status = validStatusPanel();
  const unavailable = unavailableStatusPanel({ schema_version: 5 });
  const accepted = snapshot({ panels: { status: status, character: unavailable } });
  const result = store.receive(1, "ui_snapshot", [accepted], {});
  assert.equal(result.accepted, true);
  assert.deepEqual(store.getState().panels.status, status, "healthy status panel stays intact");
  assert.deepEqual(store.getState().panels.character, unavailable);

  // The identical snapshot at the stale version is rejected with no panel
  // replaced or merged: a different-but-valid status panel must not leak in.
  const differentStatus = validStatusPanel({
    actor: { name: "另一位旅人", identity: "9", location: null },
  });
  const stale = snapshot({
    panels: { status: differentStatus, character: unavailableStatusPanel({ schema_version: 2 }) },
  });
  assert.equal(store.receive(1, "ui_snapshot", [stale], {}).reason, "invalid");
  assert.equal(store.getState().phase, "active", "the version-5 state remains committed");
  assert.deepEqual(store.getState().panels.status, status, "status panel untouched");
  assert.deepEqual(store.getState().panels.character, unavailable, "character panel untouched");
});

test("enforces character D10 bounds and disguise honesty", () => {
  const overRows = new Array(Protocol.CHARACTER_MAX_TRAIT_ROWS + 1).fill(validCharacterTraitRow());
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: overRows,
      })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [validCharacterTraitRow(), validCharacterTraitRow()],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [validCharacterTraitRow({ current: 11, max: 10 })],
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

test("v5 breakdown layers validate exactly", () => {
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [
          validCharacterTraitRow({
            layers: [
              { source: "skill", name: "防禦直覺（1/2）", kind: "mult", amount: 1.5 },
              { source: "condition", name: "劇毒", kind: "pct", amount: -10 },
              { source: "equipment", name: "騎士全套板甲", kind: "flat", amount: 8 },
            ],
          }),
        ],
      })
    )
  );
  const layerBad = (overrides) =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [
          validCharacterTraitRow({
            layers: [
              Object.assign({ source: "equipment", name: "鐵劍", kind: "flat", amount: 2 }, overrides),
            ],
          }),
        ],
      })
    );
  assert.throws(() => layerBad({ source: "innate" }));
  assert.throws(() => layerBad({ kind: "percent" }));
  assert.throws(() => layerBad({ amount: 0 }));
  assert.throws(() => layerBad({ amount: "2" }));
  assert.throws(() => layerBad({ amount: NaN }));
  assert.throws(() => layerBad({ amount: Infinity }));
  assert.throws(() => layerBad({ name: " " }));
  assert.throws(() => layerBad({ extra: 1 }));
  // Layer list bound and exact trait-row shape.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [
          validCharacterTraitRow({
            layers: new Array(17).fill({ source: "equipment", name: "鐵劍", kind: "flat", amount: 2 }),
          }),
        ],
      })
    )
  );
  const missingLayerField = { source: "equipment", name: "鐵劍", kind: "flat" };
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ traits: [validCharacterTraitRow({ layers: [missingLayerField] })] })
    )
  );
  // Fractional totals ride as JSON numbers (scaled rule-table grants).
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [validCharacterTraitRow({ key: "defense", label: "防禦", base: 5, current: 7.5, max: null, effective: 7.5 })],
      })
    )
  );
  // The defining row contract: statics expose effective through current;
  // gauges carry effective == max. Contradictions reject.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [validCharacterTraitRow({ key: "atk_phys", label: "攻擊", base: 10, current: 10, max: null, effective: 15 })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [validCharacterTraitRow({ key: "hp", label: "生命", base: 100, current: 40, max: 115, effective: 100 })],
      })
    )
  );
});

test("v5 equipment rows require the adjustment summary", () => {
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        equipment: [{ slot: "weapon_main", item_key: "plain_sword", display_name: "鐵劍" }],
      })
    )
  );
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        equipment: [{ slot: "weapon_main", item_key: "plain_sword", display_name: "鐵劍", adjustment: "" }],
      })
    )
  );
});

test("character panel v4 validates the intimate status section", () => {
  // A null intimate section (no sexual-state record) is valid.
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(validCharacterPanel({ intimate: null }))
  );
  const intimate = {
    arousal: "中等",
    wetness: "濕潤",
    shame: "輕微",
    exposure: "低",
    climax_phase: "未達",
    climax_today: 0,
  };
  const normalized = Protocol.validateCharacterPanel(validCharacterPanel({ intimate }));
  assert.deepEqual(normalized.intimate, intimate, "a valid intimate section normalizes to itself");
  // A level outside its fixed vocabulary is rejected.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ intimate: { ...intimate, arousal: "極高" } })
    )
  );
  // An over-long level string is rejected.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ intimate: { ...intimate, wetness: "a".repeat(129) } })
    )
  );
  // climax_today must be a non-negative integer.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ intimate: { ...intimate, climax_today: -1 } })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ intimate: { ...intimate, climax_today: 1.5 } })
    )
  );
  // A missing or unknown field in the intimate section is rejected.
  const missingField = { ...intimate };
  delete missingField.shame;
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ intimate: missingField })));
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ intimate: { ...intimate, extra: 1 } })
    )
  );
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

// ---------------------------------------------------------------------------
// character panel v3 active skill row descriptor detail (fix-webclient-
// skillbook-descriptor-data)
// ---------------------------------------------------------------------------

function enrichedActiveRow(key, label) {
  // Matches what Python's _serialize_active_skill_groups emits for a
  // registry-resolvable active skill row.
  return {
    key: key,
    label: label,
    cost: { mp: 14 },
    target_spec: "single",
    usable_out_of_combat: true,
    freeform_scales: [
      { scale: 0.25, label: "1/4", mp_cost: 4 },
      { scale: 0.5, label: "1/2", mp_cost: 7 },
      { scale: 1, label: "1", mp_cost: 14 },
      { scale: 2, label: "2", mp_cost: 28 },
      { scale: 4, label: "4", mp_cost: 56 },
    ],
  };
}

test("character active skill rows accept the registry-backed descriptor subset", () => {
  // A Python-serialized enriched active row validates, and a bare
  // {key, label} row (the unregistered-key fallback shape) still validates.
  assert.doesNotThrow(() =>
    Protocol.validateCharacterActiveSkillRow(enrichedActiveRow("fire_ball", "火球術"))
  );
  assert.doesNotThrow(() =>
    Protocol.validateCharacterActiveSkillRow({ key: "no_such_skill", label: "no_such_skill" })
  );
  // Malformed detail fields fail closed.
  assert.throws(() =>
    Protocol.validateCharacterActiveSkillRow(
      Object.assign({}, enrichedActiveRow("fire_ball", "火球術"), { target_spec: "wild" })
    ),
    /target_spec/
  );
  assert.throws(() =>
    Protocol.validateCharacterActiveSkillRow(
      Object.assign({}, enrichedActiveRow("fire_ball", "火球術"), { usable_out_of_combat: "yes" })
    ),
    /boolean/
  );
  assert.throws(() =>
    Protocol.validateCharacterActiveSkillRow(
      Object.assign({}, enrichedActiveRow("fire_ball", "火球術"), { cost: { mp: -1 } })
    ),
    /within/
  );
});

test("character panel wires active and passive rows through their distinct validators", () => {
  // The live-client regression guard: a full character payload carrying an
  // enriched active row and a bare passive row must pass validateCharacterPanel.
  const payload = validCharacterPanel({
    actives: [
      {
        category: "elemental_magic",
        label: "元素魔法",
        groups: [
          {
            group: "fire",
            label: "火",
            skills: [enrichedActiveRow("fire_ball", "火球術")],
          },
        ],
      },
    ],
  });
  const validated = Protocol.validateCharacterPanel(payload);
  assert.deepEqual(validated.actives[0].groups[0].skills[0].cost, { mp: 14 });
  assert.equal(validated.actives[0].groups[0].skills[0].usable_out_of_combat, true);
  assert.equal(validated.actives[0].groups[0].skills[0].target_spec, "single");
  assert.equal(validated.actives[0].groups[0].skills[0].freeform_scales.length, 5);
  assert.deepEqual(validated.passives[0].groups[0].skills[0], {
    key: "defense_instinct",
    label: "防禦直覺",
  });
  // A freeform_scales entry whose mp_cost does not match the deterministic
  // scaling of the base cost is rejected.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        actives: [
          {
            category: "elemental_magic",
            label: "元素魔法",
            groups: [
              {
                group: "fire",
                label: "火",
                skills: [
                  Object.assign({}, enrichedActiveRow("fire_ball", "火球術"), {
                    freeform_scales: [
                      { scale: 0.25, label: "1/4", mp_cost: 99 },
                      { scale: 0.5, label: "1/2", mp_cost: 7 },
                      { scale: 1, label: "1", mp_cost: 14 },
                      { scale: 2, label: "2", mp_cost: 28 },
                      { scale: 4, label: "4", mp_cost: 56 },
                    ],
                  }),
                ],
              },
            ],
          },
        ],
      })
    ),
    /inconsistent/
  );
});

test("character active row parity with the Python presenter (nullable fields, mp=0)", () => {
  // A present-but-null freeform_scales is accepted and omitted from the
  // normalized row (mirrors Python's field omission).
  const nullScales = validCharacterPanel({
    actives: [
      {
        category: "elemental_magic",
        label: "元素魔法",
        groups: [
          {
            group: "fire",
            label: "火",
            skills: [Object.assign({}, enrichedActiveRow("fire_ball", "火球術"), { freeform_scales: null })],
          },
        ],
      },
    ],
  });
  const validated = Protocol.validateCharacterPanel(nullScales);
  const row = validated.actives[0].groups[0].skills[0];
  assert.equal(row.freeform_scales, undefined, "null freeform_scales is omitted");
  assert.deepEqual(row.cost, { mp: 14 });

  // cost {mp: 0} with freeform_scales present fails closed on both ends.
  const zeroMp = validCharacterPanel({
    actives: [
      {
        category: "elemental_magic",
        label: "元素魔法",
        groups: [
          {
            group: "fire",
            label: "火",
            skills: [
              Object.assign({}, enrichedActiveRow("fire_ball", "火球術"), { cost: { mp: 0 } }),
            ],
          },
        ],
      },
    ],
  });
  assert.throws(
    () => Protocol.validateCharacterPanel(zeroMp),
    /a skill without an mp cost cannot carry freeform_scales/
  );
});
