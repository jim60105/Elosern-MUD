/*
 * elosern_actions.js DOM-independent tests (foundation section 5.3/5.2).
 */
const test = require("node:test");
const assert = require("node:assert");

const Actions = require("../plugins/elosern_actions.js");

function makeStoreState(overrides) {
  return Object.assign(
    {
      connected: true,
      mutationsLocked: false,
      awaitingInitialSnapshot: false,
      phase: "active",
      activeEpoch: "a".repeat(22),
      revision: 5,
      lastActionResult: null,
    },
    overrides
  );
}

function makeHarness() {
  const sent = [];
  let state = makeStoreState();
  const notices = [];
  const client = Actions.createActionClient({
    send: (name, args) => sent.push({ name, args }),
    getStoreState: () => state,
    onNotice: (kind, message) => notices.push({ kind, message }),
  });
  return {
    client,
    sent,
    setState: (patch) => {
      state = Object.assign({}, state, patch);
    },
    notices,
  };
}

test("submit sends an exact ui_action envelope", () => {
  const h = makeHarness();
  const requestId = h.client.submit("combat.cast", { skill_key: "fire_ball" });
  assert.ok(requestId);
  assert.strictEqual(h.sent.length, 1);
  const envelope = h.sent[0].args[0];
  assert.strictEqual(h.sent[0].name, "ui_action");
  assert.strictEqual(envelope.protocol_version, 1);
  assert.strictEqual(envelope.presentation_epoch, "a".repeat(22));
  assert.strictEqual(envelope.base_revision, 5);
  assert.strictEqual(envelope.action_id, "combat.cast");
  assert.deepStrictEqual(envelope.payload, { skill_key: "fire_ball" });
  assert.match(envelope.request_id, /^[A-Za-z0-9:_-]{1,64}$/);
});

test("second submit while in flight is refused", () => {
  const h = makeHarness();
  h.client.submit("combat.cast", {});
  assert.strictEqual(h.client.submit("combat.cast", {}), null);
  assert.strictEqual(h.sent.length, 1);
});

test("submit while locked (offline or synchronizing) is refused", () => {
  const h = makeHarness();
  h.setState({ connected: false, mutationsLocked: true });
  assert.strictEqual(h.client.submit("combat.cast", {}), null);
  assert.strictEqual(h.sent.length, 0);
});

test("request IDs are bounded and sequence-local", () => {
  const gen = Actions.createRequestId("web");
  const ids = [];
  for (let i = 0; i < 10; i += 1) {
    ids.push(gen());
  }
  assert.strictEqual(new Set(ids).size, 10);
  ids.forEach((id) => assert.match(id, /^[A-Za-z0-9:_-]{1,64}$/));
});

test("lock releases only after result and accepted revision", () => {
  const h = makeHarness();
  h.client.submit("combat.cast", {});
  // Result declares revision 8, but the store is still at 5.
  h.client.onActionResult({
    requestId: h.sent[0].args[0].request_id,
    epoch: "a".repeat(22),
    outcome: "success",
    code: "ok",
    message: "完成",
    presentation_revision: 8,
  });
  assert.strictEqual(h.client.isInFlight(), true, "still awaiting revision 8");
  // Store accepts revision 8 (e.g. the completion update arrived).
  h.setState({ revision: 8 });
  h.client.onPresentationAccepted({ revision: 8 });
  assert.strictEqual(h.client.isInFlight(), false, "lock released after revision accepted");
});

test("stale outcome triggers resync and waits for recovery snapshot", () => {
  const h = makeHarness();
  h.client.submit("combat.cast", {});
  h.client.onActionResult({
    requestId: h.sent[0].args[0].request_id,
    epoch: "a".repeat(22),
    outcome: "stale",
    code: "stale",
    message: "狀態已更新",
    presentation_revision: 12,
  });
  assert.strictEqual(h.sent.some((m) => m.name === "ui_sync"), true, "stale triggers resync");
  // Lock remains until the store reaches the stale recovery revision.
  assert.strictEqual(h.client.isInFlight(), true);
  h.setState({ revision: 12 });
  h.client.onPresentationAccepted({ revision: 12 });
  assert.strictEqual(h.client.isInFlight(), false);
});

test("error outcome unlocks without waiting", () => {
  const h = makeHarness();
  h.client.submit("combat.cast", {});
  h.client.onActionResult({
    requestId: h.sent[0].args[0].request_id,
    epoch: "a".repeat(22),
    outcome: "error",
    code: "internal_error",
    message: "發生錯誤",
    presentation_revision: 5,
  });
  assert.strictEqual(h.client.isInFlight(), false);
  assert.strictEqual(h.notices.some((n) => n.kind === "error"), true);
});

test("disconnect after submit never retries and shows uncertain notice", () => {
  const h = makeHarness();
  h.client.submit("combat.cast", {});
  const sentCountBefore = h.sent.length;
  h.client.onReconnect();
  // No automatic resubmission of the prior request.
  assert.strictEqual(h.sent.length, sentCountBefore + 1, "only one new ui_sync on reconnect");
  assert.strictEqual(h.sent[h.sent.length - 1].name, "ui_sync");
  assert.strictEqual(h.client.isInFlight(), false);
  assert.strictEqual(h.client.uncertain(), true);
  assert.strictEqual(h.notices.some((n) => n.kind === "uncertain"), true);
});

test("transport reset clears in-flight and uncertain state", () => {
  const h = makeHarness();
  h.client.submit("combat.cast", {});
  h.client.onTransportReset();
  assert.strictEqual(h.client.isInFlight(), false);
  assert.strictEqual(h.client.uncertain(), false);
});

test("lock releases using the reducer-normalized result shape", () => {
  const Protocol = require("../elosern/protocol.js");
  const h = makeHarness();
  h.client.submit("combat.cast", {});
  const requestId = h.sent[0].args[0].request_id;

  // Validate a wire-format envelope through the real reducer, which
  // normalizes presentation_revision -> presentationRevision.
  const envelope = {
    protocol_version: 1,
    presentation_epoch: "a".repeat(22),
    request_id: requestId,
    outcome: "success",
    code: "ok",
    message: "完成",
    presentation_revision: 9,
  };
  const normalized = Protocol.validateActionResult(envelope);
  assert.strictEqual(normalized.presentationRevision, 9);

  // Feed the normalized result: the lock must stay held until the store
  // accepts revision 9.
  h.client.onActionResult(normalized);
  assert.strictEqual(h.client.isInFlight(), true, "still awaiting revision 9");
  h.setState({ revision: 9 });
  h.client.onPresentationAccepted({ revision: 9 });
  assert.strictEqual(h.client.isInFlight(), false);
});

test("no_puppet rejection releases the lock unconditionally", () => {
  const h = makeHarness();
  h.client.submit("combat.cast", {});
  const requestId = h.sent[0].args[0].request_id;
  h.client.onActionResult({
    requestId,
    epoch: "a".repeat(22),
    outcome: "rejected",
    code: "no_puppet",
    message: "目前沒有附身角色，無法執行操作",
    presentation_revision: 5,
  });
  // No presentation will ever gate this rejection; the lock is released
  // immediately, even though the store revision never advanced.
  assert.strictEqual(h.client.isInFlight(), false);
  assert.strictEqual(h.notices.some((n) => n.kind === "result"), true);
});

test("submit while detached (OOC) is refused", () => {
  const h = makeHarness();
  h.setState({ phase: "detached", mutationsLocked: true });
  assert.strictEqual(h.client.submit("combat.cast", {}), null);
  assert.strictEqual(h.sent.length, 0);
  assert.strictEqual(h.client.isLocked(), true);
});

test("detachment with an in-flight mutation releases the lock and warns", () => {
  const h = makeHarness();
  h.client.submit("combat.cast", {});
  assert.strictEqual(h.client.isInFlight(), true);
  h.client.onDetached();
  assert.strictEqual(h.client.isInFlight(), false);
  assert.strictEqual(h.client.uncertain(), true);
  assert.strictEqual(h.notices.some((n) => n.kind === "uncertain"), true);
  // No ui_sync is issued: the server retired the sequence and there is no
  // puppet to synchronize against.
  assert.strictEqual(h.sent.some((m) => m.name === "ui_sync"), false);
});

test("detachment with no in-flight mutation stays silent", () => {
  const h = makeHarness();
  h.client.onDetached();
  assert.strictEqual(h.client.uncertain(), false);
  assert.strictEqual(h.notices.length, 0);
});
