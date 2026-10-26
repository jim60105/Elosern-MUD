/*
 * Bounded complete recovery (webclient-sync-recovery): the reducer's one
 * failure episode per transport generation.
 *
 * Every failure source records one `recovery` state there — an exact-base
 * mismatch, an invalid or incomplete publication, an assembly rejection or
 * expiry, a recoverable server protocol error, a transport-corrupted frame, and
 * (from the app) a matching action result claiming a revision this client never
 * adopted. The episode costs at most one automatic complete repair: the first
 * recorded need may be requested once, a failure that lands while that repair
 * is requested makes the episode terminal, and nothing but a valid complete
 * snapshot, the claimed revision actually being adopted, the player's own
 * explicit attempt or a new transport generation moves it again. Every state
 * keeps the committed presentation and locks graphical mutations.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const {
  EPOCH_B,
  VALID_EPOCH,
  actionResult,
  protocolError,
  snapshot,
  unavailableStatusPanel,
  update,
  validStatusPanel,
} = require("./protocol_support.js");

// The common unavailable form at any registered schema version is a complete
// valid replacement, so a panel-ownership scenario needs no second rich fixture.
function unavailable(name) {
  return {
    schema_version: Protocol.PANEL_ALLOWLIST[name],
    available: false,
    reason: { code: "unavailable", message: "暫時無法顯示" },
  };
}

function committedStore(options) {
  const store = Protocol.createStore(options);
  store.beginTransport(1);
  const result = store.receive(
    1,
    "ui_snapshot",
    [
      snapshot({
        revision: 7,
        panels: {
          status: validStatusPanel(),
          quest_log: unavailable("quest_log"),
        },
      }),
    ],
    {}
  );
  assert.equal(result.accepted, true);
  return store;
}

// One first part of a two-part logical snapshot: 24,576 raw bytes of padding,
// which is exactly the first part of a 24,577-byte transfer. The second part
// never arrives, so the assembly can only end through its own deadline.
const PART_PADDING = Buffer.alloc(1536).toString("base64");

function publicationPart(overrides) {
  return Object.assign(
    {
      protocol_version: 1,
      presentation_epoch: VALID_EPOCH,
      revision: 8,
      publication_kind: "snapshot",
      transfer_id: "0123456789abcdef0123456789abcdef",
      part_index: 0,
      part_count: 2,
      total_bytes: 24577,
      chunks: Array.from({ length: 16 }, () => PART_PADDING),
    },
    overrides || {}
  );
}

test("an exact-base mismatch records one need and preserves every committed value", () => {
  const store = committedStore();
  const before = store.getState();
  const result = store.receive(
    1,
    "ui_update",
    [
      update({
        revision: 8,
        base_revision: 5,
        panels: { status: validStatusPanel({ disguise_active: true }) },
      }),
    ],
    {}
  );
  assert.equal(result.accepted, false);
  assert.equal(result.reason, "base_mismatch");
  const after = store.getState();
  // The rejected publication changed nothing the client can see except the
  // recovery state and the mutation lock.
  assert.equal(after.revision, before.revision);
  assert.deepEqual(after.panels, before.panels);
  assert.deepEqual(after.serverTime, before.serverTime);
  assert.equal(after.recovery.status, "needed");
  assert.equal(after.recovery.cause, "base_mismatch");
  assert.equal(after.recovery.generation, 1);
  assert.equal(after.mutationsLocked, true);
});

test("simultaneous failures of different sources coalesce into one request", () => {
  const store = committedStore();
  const before = store.getState().panels;
  // A base mismatch, then an unrenderable complete publication, before the
  // renderer had any chance to ask: both belong to the same episode.
  store.receive(
    1,
    "ui_update",
    [update({ revision: 8, base_revision: 5, panels: {} })],
    {}
  );
  store.receive(
    1,
    "ui_snapshot",
    [snapshot({ revision: 8, panels: { bogus_panel: {} } })],
    {}
  );
  const state = store.getState();
  assert.equal(state.recovery.status, "needed");
  assert.deepEqual(state.panels, before);
  assert.equal(store.markRecoveryRequested(false), true);
  assert.equal(store.markRecoveryRequested(false), false);
  assert.equal(store.markRecoveryRequested(false), false);
  assert.equal(store.getState().recovery.status, "requested");
  assert.equal(store.getState().mutationsLocked, true);
});

test("a failure while the repair is requested makes the episode terminal", () => {
  const store = committedStore();
  store.receive(
    1,
    "ui_update",
    [update({ revision: 8, base_revision: 5, panels: {} })],
    {}
  );
  assert.equal(store.markRecoveryRequested(false), true);
  // The repair snapshot itself cannot be rendered.
  store.receive(
    1,
    "ui_snapshot",
    [snapshot({ revision: 9, panels: { bogus_panel: {} } })],
    {}
  );
  const state = store.getState();
  assert.equal(state.recovery.status, "failed");
  // No automatic second attempt, ever, for this generation.
  assert.equal(store.markRecoveryRequested(false), false);
  // Repeated traffic of every ordinary kind cannot re-arm or clear it.
  for (let index = 0; index < 3; index += 1) {
    store.receive(1, "ui_snapshot", [snapshot({ revision: 10 + index, panels: { bogus_panel: {} } })], {});
    store.receive(1, "ui_action_result", [actionResult({ presentation_revision: 40 })], {});
    store.receive(1, "ui_update", [update({ revision: 20 + index, base_revision: 7, panels: {} })], {});
  }
  assert.equal(store.getState().recovery.status, "failed");
  assert.equal(store.getState().mutationsLocked, true);
  assert.equal(store.resetRecoveryEpisode(), false);
  assert.equal(store.getState().recovery.status, "failed");
});

test("an assembly deadline expiring while requested fails the episode and frees its buffers", () => {
  const timers = [];
  const store = committedStore({
    now: () => 0,
    setTimer: (callback) => {
      timers.push(callback);
      return timers.length;
    },
    clearTimer: () => {},
  });
  store.receive(
    1,
    "ui_update",
    [update({ revision: 8, base_revision: 5, panels: {} })],
    {}
  );
  assert.equal(store.markRecoveryRequested(false), true);
  // The repair arrives as parts and the second part never comes.
  const part = store.receive(1, "ui_publication_part", [publicationPart()], {});
  assert.equal(part.pending, true);
  assert.equal(store.publicationAssemblyStats().live, true);
  assert.equal(timers.length > 0, true);
  timers[timers.length - 1]();
  const state = store.getState();
  assert.equal(state.recovery.status, "failed");
  assert.equal(state.recovery.cause, "timeout");
  assert.equal(state.mutationsLocked, true);
  assert.equal(store.publicationAssemblyStats().live, false);
  assert.equal(store.publicationAssemblyStats().bytes, 0);
  assert.equal(store.markRecoveryRequested(false), false);
});

test("a valid complete snapshot ends the episode and replaces every eager panel", () => {
  const store = committedStore();
  store.receive(
    1,
    "ui_update",
    [update({ revision: 8, base_revision: 5, panels: {} })],
    {}
  );
  assert.equal(store.markRecoveryRequested(false), true);
  assert.equal(store.getState().mutationsLocked, true);

  const repaired = store.receive(
    1,
    "ui_snapshot",
    [
      snapshot({
        revision: 9,
        panels: {
          status: validStatusPanel({ disguise_active: true }),
          objectives: unavailable("objectives"),
        },
      }),
    ],
    {}
  );
  assert.equal(repaired.accepted, true);
  const state = store.getState();
  assert.equal(state.recovery.status, "idle");
  assert.equal(state.recovery.cause, null);
  assert.equal(state.mutationsLocked, false);
  // The complete snapshot owns the whole eager set: the panel it names is
  // replaced and the one it omits is gone.
  assert.deepEqual(Object.keys(state.panels).sort(), ["objectives", "status"]);
  assert.equal(state.panels.status.disguise_active, true);
  assert.equal(state.revision, 9);
});

test("a delta neither clears nor re-arms a failed episode", () => {
  const store = committedStore();
  store.receive(
    1,
    "ui_update",
    [update({ revision: 8, base_revision: 5, panels: {} })],
    {}
  );
  store.markRecoveryRequested(false);
  store.receive(
    1,
    "ui_snapshot",
    [snapshot({ revision: 8, panels: { bogus_panel: {} } })],
    {}
  );
  assert.equal(store.getState().recovery.status, "failed");

  const delta = store.receive(
    1,
    "ui_update",
    [update({ revision: 8, base_revision: 7, panels: { status: validStatusPanel() } })],
    {}
  );
  assert.equal(delta.accepted, true);
  assert.equal(store.getState().revision, 8);
  assert.equal(store.getState().recovery.status, "failed");
  assert.equal(store.getState().mutationsLocked, true);

  // The repair that finally lands is still the one outcome that ends it.
  const repaired = store.receive(
    1,
    "ui_snapshot",
    [snapshot({ revision: 9, panels: { status: validStatusPanel() } })],
    {}
  );
  assert.equal(repaired.accepted, true);
  assert.equal(store.getState().recovery.status, "idle");
  assert.equal(store.getState().mutationsLocked, false);
});

test("the player's explicit attempt is exactly one further request", () => {
  const store = committedStore();
  store.receive(
    1,
    "ui_update",
    [update({ revision: 8, base_revision: 5, panels: {} })],
    {}
  );
  store.markRecoveryRequested(false);
  store.receive(
    1,
    "ui_snapshot",
    [snapshot({ revision: 9, panels: { bogus_panel: {} } })],
    {}
  );
  assert.equal(store.getState().recovery.status, "failed");
  assert.equal(store.markRecoveryRequested(true), true);
  assert.equal(store.getState().recovery.status, "requested");
  assert.equal(store.getState().mutationsLocked, true);
  assert.equal(store.markRecoveryRequested(true), false);
  // A second failed attempt is terminal again.
  assert.equal(store.failRecovery("timeout"), true);
  assert.equal(store.getState().recovery.status, "failed");
  assert.equal(store.markRecoveryRequested(false), false);
});

test("a new transport generation resets the episode", () => {
  const store = committedStore();
  store.receive(
    1,
    "ui_update",
    [update({ revision: 8, base_revision: 5, panels: {} })],
    {}
  );
  store.markRecoveryRequested(false);
  store.receive(
    1,
    "ui_snapshot",
    [snapshot({ revision: 8, panels: { bogus_panel: {} } })],
    {}
  );
  assert.equal(store.getState().recovery.status, "failed");
  store.beginTransport(2);
  const state = store.getState();
  assert.equal(state.recovery.status, "idle");
  assert.equal(state.recovery.generation, 2);
  assert.equal(state.mutationsLocked, true);
  const accepted = store.receive(
    2,
    "ui_snapshot",
    [
      snapshot({
        presentation_epoch: EPOCH_B,
        revision: 1,
        panels: { status: validStatusPanel() },
      }),
    ],
    {}
  );
  assert.equal(accepted.accepted, true);
  assert.equal(store.getState().mutationsLocked, false);
});

test("an unadopted claimed revision ends when exactly that revision is adopted", () => {
  const store = committedStore();
  assert.equal(store.noteRecovery("unadopted_result", 9), true);
  assert.equal(store.getState().recovery.status, "needed");
  assert.equal(store.getState().recovery.targetRevision, 9);
  assert.equal(store.getState().mutationsLocked, true);
  store.markRecoveryRequested(false);
  // An older publication cannot satisfy the claim.
  const older = store.receive(
    1,
    "ui_update",
    [update({ revision: 8, base_revision: 7, panels: {} })],
    {}
  );
  assert.equal(older.accepted, true);
  assert.equal(store.getState().recovery.status, "requested");
  assert.equal(store.getState().mutationsLocked, true);
  // The missed publication itself arrives.
  const adopted = store.receive(
    1,
    "ui_update",
    [update({ revision: 9, base_revision: 8, panels: {} })],
    {}
  );
  assert.equal(adopted.accepted, true);
  assert.equal(store.getState().recovery.status, "idle");
  assert.equal(store.getState().mutationsLocked, false);
});

test("a recoverable protocol error records one need; an incompatible one never requests", () => {
  const recoverable = committedStore();
  const accepted = recoverable.receive(
    1,
    "ui_protocol_error",
    [protocolError({ code: "presentation_unavailable", reload_required: false })],
    {}
  );
  assert.equal(accepted.accepted, true);
  assert.equal(recoverable.getState().recovery.status, "needed");
  assert.equal(recoverable.getState().mutationsLocked, true);
  assert.equal(recoverable.markRecoveryRequested(false), true);

  const incompatible = committedStore();
  incompatible.receive(
    1,
    "ui_protocol_error",
    [protocolError({ code: "unsupported_version", reload_required: false })],
    {}
  );
  const state = incompatible.getState();
  assert.equal(state.protocolIncompatible, true);
  assert.equal(state.recovery.status, "idle");
  assert.equal(state.mutationsLocked, true);
  assert.equal(incompatible.markRecoveryRequested(false), false);
  assert.equal(incompatible.markRecoveryRequested(true), false);
  // A later valid publication cannot unlock an incompatible sequence.
  incompatible.receive(
    1,
    "ui_snapshot",
    [snapshot({ revision: 9, panels: { status: validStatusPanel() } })],
    {}
  );
  assert.equal(incompatible.getState().mutationsLocked, true);
});

test("a transport-corrupted frame records one need", () => {
  const store = committedStore();
  const result = store.receive(1, "ui_snapshot", [], {});
  assert.equal(result.reason, "missing_envelope");
  assert.equal(store.getState().recovery.status, "needed");
  assert.equal(store.getState().mutationsLocked, true);
  assert.equal(store.markRecoveryRequested(false), true);
});

test("a matching action result never changes committed presentation", () => {
  const store = committedStore();
  const before = store.getState();
  store.receive(
    1,
    "ui_action_result",
    [actionResult({ presentation_revision: 42 })],
    {}
  );
  const after = store.getState();
  assert.equal(after.revision, before.revision);
  assert.deepEqual(after.panels, before.panels);
  assert.equal(after.lastActionResult.presentationRevision, 42);
});

test("the episode transitions report whether they changed it", () => {
  const store = committedStore();
  assert.equal(store.failRecovery("timeout"), false);
  assert.equal(store.resetRecoveryEpisode(), false);
  assert.equal(store.markRecoveryRequested(false), false);
  assert.equal(store.noteRecovery("invalid"), true);
  assert.equal(store.resetRecoveryEpisode(), false);
  assert.equal(store.markRecoveryRequested(false), true);
  // A re-arm returns the episode to its pending state without ending it.
  assert.equal(store.resetRecoveryEpisode(), true);
  assert.equal(store.getState().recovery.status, "needed");
  assert.equal(store.getState().mutationsLocked, true);
  assert.equal(store.markRecoveryRequested(false), true);
});

test("a rejected staged presentation records the episode", () => {
  const store = committedStore();
  // A newer snapshot whose staged mode is dialogue without a committed or
  // staged dialogue panel: schema-valid, semantically rejected.
  const before = store.getState();
  const rejected = store.receive(
    1,
    "ui_snapshot",
    [
      snapshot({
        revision: 8,
        mode: "dialogue",
        panels: { status: validStatusPanel() },
      }),
    ],
    {}
  );
  assert.equal(rejected.accepted, false);
  assert.equal(rejected.reason, "invalid");
  assert.equal(rejected.recovery, "needed");
  const after = store.getState();
  assert.deepEqual(after.panels, before.panels);
  assert.equal(after.revision, before.revision);
  assert.equal(after.recovery.status, "needed");
  assert.equal(after.mutationsLocked, true);
  assert.equal(store.markRecoveryRequested(false), true);
});

test("an incompatible protocol stays locked after a later recoverable error", () => {
  const store = committedStore();
  store.receive(
    1,
    "ui_protocol_error",
    [protocolError({ code: "unsupported_version", reload_required: false })],
    {}
  );
  assert.equal(store.getState().protocolIncompatible, true);
  // A recoverable error replaces the displayed error but never re-opens the
  // sequence an incompatible peer already invalidated.
  store.receive(
    1,
    "ui_protocol_error",
    [protocolError({ code: "presentation_unavailable", reload_required: false })],
    {}
  );
  assert.equal(store.getState().protocolIncompatible, true);
  assert.equal(store.markRecoveryRequested(false), false);
  store.receive(
    1,
    "ui_snapshot",
    [snapshot({ revision: 9, panels: { status: validStatusPanel() } })],
    {}
  );
  assert.equal(store.getState().protocolIncompatible, true);
  assert.equal(store.getState().mutationsLocked, true);
  assert.equal(store.markRecoveryRequested(true), false);
  // Only a new transport generation clears it.
  store.beginTransport(2);
  assert.equal(store.getState().protocolIncompatible, false);
});
