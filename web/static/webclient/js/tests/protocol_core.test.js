/*
 * Exact envelope schemas, discriminators, panel allowlists, and global JSON-safety bounds.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { EPOCH_A, VALID_EPOCH, actionResult, connectedStore, nested, protocolError, serverTime, snapshot, unavailableStatusPanel, validStatusPanel } = require("./protocol_support.js");


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
    Protocol.validatePanel(
      "status",
      Protocol.PANEL_ALLOWLIST.status,
      unavailableStatusPanel({ schema_version: 2 })
    ),
    unavailableStatusPanel({ schema_version: 2 })
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
      unavailableStatusPanel({ schema_version: 3 })
    )
  );
  // An internal reason carries a bounded correlation ID.
  assert.doesNotThrow(() =>
    Protocol.validatePanel(
      "status",
      Protocol.PANEL_ALLOWLIST.status,
      unavailableStatusPanel({
        schema_version: 2,
        reason: {
          code: "internal_presenter_error",
          message: "此介面暫時無法使用",
          correlation_id: "a".repeat(32),
        },
      })
    )
  );

  // Available form is exact.
  assert.doesNotThrow(() => Protocol.validateStatusPanel(validStatusPanel()));
  assert.throws(() => Protocol.validateStatusPanel(validStatusPanel({ extra: 1 })));
  assert.throws(() => Protocol.validateStatusPanel(validStatusPanel({ schema_version: 1 })));
  assert.throws(() => Protocol.validateStatusPanel(validStatusPanel({ schema_version: 3 })));
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
  // The optional composed full-title row (title-system D6): accepted when
  // bounded and non-blank, rejected otherwise, absent for an untitled actor.
  assert.doesNotThrow(() =>
    Protocol.validateStatusPanel(
      validStatusPanel({
        actor: {
          name: "x",
          identity: "1",
          location: null,
          full_title: "F級冒險者　南門新客",
        },
      })
    )
  );
  assert.throws(() =>
    Protocol.validateStatusPanel(
      validStatusPanel({
        actor: { name: "x", identity: "1", location: null, full_title: "　" },
      })
    )
  );
  assert.throws(() =>
    Protocol.validateStatusPanel(
      validStatusPanel({
        actor: {
          name: "x",
          identity: "1",
          location: null,
          full_title: "長".repeat(Protocol.MAX_FULL_TITLE_CODE_POINTS + 1),
        },
      })
    )
  );
  assert.throws(() =>
    Protocol.validateStatusPanel(
      validStatusPanel({
        actor: { name: "x", identity: "1", location: null, full_title: 7 },
      })
    )
  );
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

test("ui_action_result data slot accepts the server-legal shapes", () => {
  const valid = Protocol.validateActionResult(
    actionResult({ data: { display_name: "加斯帕・斯諾", rank: 3 } })
  );
  assert.deepEqual(valid.data, { display_name: "加斯帕・斯諾", rank: 3 });
  assert.equal(
    Object.prototype.hasOwnProperty.call(Protocol.validateActionResult(actionResult()), "data"),
    false
  );
  const eight = {};
  for (let index = 0; index < 8; index += 1) {
    eight["key_" + index] = index;
  }
  assert.deepEqual(Protocol.validateActionResult(actionResult({ data: eight })).data, eight);
  // Depth boundary pair: the slot sits at envelope depth 1, so ten list
  // levels below the slot value (deepest leaf at depth 12) is legal.
  assert.doesNotThrow(() => Protocol.validateActionResult(actionResult({ data: { k: nested(10) } })));
});

test("ui_action_result data slot rejects the server-illegal shapes", () => {
  const nine = {};
  for (let index = 0; index < 9; index += 1) {
    nine["key_" + index] = index;
  }
  const rejects = [
    // Nine fields.
    { data: nine },
    // Non-success outcomes.
    { outcome: "rejected", code: "denied", data: { k: 1 } },
    { outcome: "stale", code: "stale", data: { k: 1 } },
    { outcome: "error", code: "internal_error", correlation_id: "b".repeat(32), data: { k: 1 } },
    // Non-object slots.
    { data: [{ k: 1 }] },
    { data: "text" },
    { data: 7 },
    { data: true },
    // Field-name shape.
    { data: { UPPER: 1 } },
    { data: { "has space": 1 } },
    { data: { ["x".repeat(65)]: 1 } },
    // Reserved state keys: top-level, dot-composite, nested, and in lists.
    { data: { actor: "x" } },
    { data: { epoch: "x" } },
    { data: { presentation_revision: 1 } },
    { data: { correlation_id: "b".repeat(32) } },
    { data: { local_path: "/tmp/x" } },
    { data: { "session.id": "1" } },
    { data: { ok: { revision: 7 } } },
    { data: { ok: [{ epoch: "e" }] } },
    // Depth: one level past the boundary (deepest leaf at envelope depth 13).
    { data: { k: nested(11) } },
    // String ceiling.
    { data: { k: "x".repeat(2049) } },
    // Aggregate bytes: individually safe items over the result-data budget.
    { data: { k: new Array(34).fill("x".repeat(2000)) } },
  ];
  for (const overrides of rejects) {
    assert.throws(
      () => Protocol.validateActionResult(actionResult(overrides)),
      undefined,
      JSON.stringify(Object.keys(overrides))
    );
  }
});

test("a budget-legal data slot keeps the whole envelope wire-legal", () => {
  const legalSlot = {};
  for (let index = 0; index < 8; index += 1) {
    legalSlot["k" + index] = "x".repeat(2000);
  }
  const store = connectedStore(EPOCH_A, 1);
  const result = store.receive(
    1,
    "ui_action_result",
    [actionResult({ presentation_epoch: EPOCH_A, data: legalSlot })],
    {}
  );
  assert.equal(result.accepted, true, "whole-envelope safety and the slot budget agree");
  assert.equal(store.getState().lastActionResult.data.k0.length, 2000);
});

test("an exact-budget data slot paired with worst-case standard fields stays wire-legal", () => {
  // Boundary pair mirroring the Python ResultEnvelopeTests: a slot at exactly
  // MAX_RESULT_DATA_BYTES canonical bytes with every standard field at its own
  // worst case (a 512-code-point message of 4-byte code points) must pass the
  // whole-envelope check and the reducer's receive gate; one byte over budget
  // is rejected at the slot level.
  const exact = { x: new Array(30).fill("a".repeat(2048)), y: "" };
  exact.y = "a".repeat(Protocol.MAX_RESULT_DATA_BYTES - Protocol.jsonByteSize(exact));
  assert.equal(Protocol.jsonByteSize(exact), Protocol.MAX_RESULT_DATA_BYTES);
  const worst = actionResult({
    presentation_epoch: EPOCH_A,
    request_id: "r".repeat(64),
    code: "c".repeat(64),
    message: "\u{10FFFF}".repeat(512),
    presentation_revision: Protocol.MAX_SAFE_INTEGER,
    data: exact,
  });
  assert.ok(Protocol.jsonByteSize(worst) <= Protocol.MAX_CANONICAL_JSON_BYTES);
  assert.doesNotThrow(() => {
    Protocol.checkEnvelope(worst);
    return Protocol.validateActionResult(worst);
  });
  const store = connectedStore(EPOCH_A, 1);
  const accepted = store.receive(1, "ui_action_result", [worst], {});
  assert.equal(accepted.accepted, true);
  const over = actionResult({
    presentation_epoch: EPOCH_A,
    data: { ...exact, y: exact.y + "a" },
  });
  assert.throws(() => Protocol.validateActionResult(over));
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

