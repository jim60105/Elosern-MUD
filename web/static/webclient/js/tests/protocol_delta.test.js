/*
 * Exact-base presentation deltas (webclient-delta-contract).
 *
 * A ui_update is one logical envelope carrying base_revision and
 * removed_panels beside the seven snapshot fields. The store stages every
 * replacement, removal, and metadata field, then commits once and notifies
 * once; a mismatch or an invalid member leaves every committed field intact.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const F = require("./map_panel_fixtures.js");
const {
  VALID_EPOCH,
  serverTime,
  snapshot,
  unavailableStatusPanel,
  update,
  validStatusPanel,
} = require("./protocol_support.js");

// The shared update helper merges over a snapshot, so an explicitly empty
// panel map (a metadata-only or removal-only delta) must bypass the merge.
function delta(overrides) {
  const value = update(overrides);
  if (overrides && Object.prototype.hasOwnProperty.call(overrides, "panels")) {
    value.panels = overrides.panels;
  }
  return value;
}

// The common unavailable form at any registered version validates as a
// complete replacement, so a removal scenario needs no second rich fixture.
function unavailable(name) {
  return {
    schema_version: Protocol.PANEL_ALLOWLIST[name],
    available: false,
    reason: { code: "unavailable", message: "暫時無法顯示" },
  };
}

function committedStore(extraPanels) {
  const store = Protocol.createStore();
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
          objectives: unavailable("objectives"),
          ...(extraPanels || {}),
        },
      }),
    ],
    {}
  );
  assert.equal(result.accepted, true);
  return store;
}

test("the exact-base fields are required and nothing is defaulted", () => {
  const missingBase = delta({ revision: 2 });
  delete missingBase.base_revision;
  assert.throws(() => Protocol.validateUpdate(missingBase), /base_revision/);

  const missingRemovals = delta({ revision: 2 });
  delete missingRemovals.removed_panels;
  assert.throws(() => Protocol.validateUpdate(missingRemovals), /removed_panels/);

  // A snapshot keeps its seven exact fields: a delta field is unknown there.
  assert.throws(() => Protocol.validateSnapshot(delta({ revision: 2 })), /unknown fields/);
  assert.throws(() => Protocol.validateUpdate(delta({ revision: 2, extra: 1 })), /unknown fields/);
});

test("base and target bounds exclude booleans, non-integers and equal values", () => {
  assert.throws(() => Protocol.validateUpdate(delta({ revision: 2, base_revision: true })), /integer/);
  assert.throws(() => Protocol.validateUpdate(delta({ revision: 2, base_revision: 1.5 })), /integer/);
  assert.throws(() => Protocol.validateUpdate(delta({ revision: 2, base_revision: 0 })), /within/);
  assert.throws(() => Protocol.validateUpdate(delta({ revision: 2, base_revision: 2 })), /older/);
  assert.throws(() => Protocol.validateUpdate(delta({ revision: 3, base_revision: 4 })), /older/);
});

test("an empty delta with complete metadata is valid", () => {
  const meta = Protocol.validateUpdate(
    delta({ revision: 2, panels: {}, server_time: serverTime({ hour: 13 }) })
  );
  assert.deepEqual(meta.panels, {});
  assert.deepEqual(meta.removedPanels, []);
  assert.equal(meta.baseRevision, 1);
  // Identical metadata with an empty body is schema-valid for a receiver.
  const store = committedStore();
  const result = store.receive(1, "ui_update", [delta({ revision: 8, panels: {} })], {});
  assert.equal(result.accepted, true);
  assert.equal(store.getState().revision, 8);
  assert.deepEqual(Object.keys(store.getState().panels).sort(), ["objectives", "quest_log", "status"]);
});

test("unknown, on-demand, duplicate and overlapping removals reject atomically", () => {
  const cases = [
    delta({ revision: 2, panels: {}, removed_panels: ["mystery"] }),
    delta({ revision: 2, panels: {}, removed_panels: ["area_map"] }),
    delta({ revision: 2, panels: {}, removed_panels: ["world_map"] }),
    delta({ revision: 2, panels: {}, removed_panels: ["quest_log", "quest_log"] }),
    delta({ revision: 2, panels: { status: validStatusPanel() }, removed_panels: ["status"] }),
    delta({ revision: 2, panels: {}, removed_panels: ["quest_log "]}),
    delta({ revision: 2, panels: {}, removed_panels: "quest_log" }),
    delta({ revision: 2, panels: {}, removed_panels: Array.from({ length: 33 }, (_, i) => `p${i}`) }),
  ];
  for (const payload of cases) {
    assert.throws(() => Protocol.validateUpdate(payload), Error);
  }
  // A mixed valid/invalid list still rejects the whole publication.
  assert.throws(
    () => Protocol.validateUpdate(delta({ revision: 2, panels: {}, removed_panels: ["quest_log", "mystery"] })),
    /unknown panel name/
  );
});

test("three distinct eager operations in one delta", () => {
  const store = committedStore();
  const before = store.getState();
  const result = store.receive(
    1,
    "ui_update",
    [
      delta({
        revision: 8,
        panels: { status: unavailableStatusPanel() },
        removed_panels: ["quest_log"],
      }),
    ],
    {}
  );
  assert.equal(result.accepted, true);
  const state = store.getState();
  // Replaced with the unavailable form: still present, never deleted.
  assert.equal(state.panels.status.available, false);
  // Removed: absent from the committed eager set.
  assert.equal(Object.prototype.hasOwnProperty.call(state.panels, "quest_log"), false);
  // Omitted: unchanged.
  assert.deepEqual(state.panels.objectives, before.panels.objectives);
  assert.equal(state.revision, 8);
});

test("removing an already absent registered eager name is idempotent", () => {
  const store = committedStore();
  const first = store.receive(1, "ui_update", [delta({ revision: 8, panels: {}, removed_panels: ["quest_log"] })], {});
  assert.equal(first.accepted, true);
  const second = store.receive(1, "ui_update", [delta({ revision: 9, panels: {}, removed_panels: ["quest_log"] })], {});
  assert.equal(second.accepted, true);
  assert.equal(Object.prototype.hasOwnProperty.call(store.getState().panels, "quest_log"), false);
});

test("a missing predecessor preserves every committed field and locks mutations", () => {
  const store = committedStore();
  store.setConnected(true);
  const before = store.getState();
  assert.equal(before.mutationsLocked, false);
  let notified = 0;
  store.subscribe(() => notified++);
  const result = store.receive(1, "ui_update", [delta({ revision: 8, base_revision: 6 })], {});
  assert.equal(result.accepted, false);
  assert.equal(result.reason, "base_mismatch");
  assert.equal(notified, 0, "a rejected delta never notifies subscribers");
  const after = store.getState();
  assert.equal(after.revision, 7);
  assert.deepEqual(after.panels, before.panels);
  assert.deepEqual(after.serverTime, before.serverTime);
  assert.equal(after.mode, before.mode);
  assert.equal(after.mutationsLocked, true, "the recovery owner must re-sync before mutations resume");
});

test("a delta never establishes the epoch", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);
  const result = store.receive(1, "ui_update", [delta({ revision: 4, base_revision: 3 })], {});
  assert.equal(result.accepted, false);
  assert.equal(result.reason, "update_cannot_establish_epoch");
  assert.equal(store.getState().activeEpoch, null);
  assert.equal(store.getState().phase, "awaiting_initial_snapshot");
});

test("a newer target may skip unused integers without inventing a predecessor", () => {
  const store = committedStore();
  let notified = 0;
  store.subscribe(() => notified++);
  const result = store.receive(1, "ui_update", [delta({ revision: 10, base_revision: 7 })], {});
  assert.equal(result.accepted, true);
  assert.equal(notified, 1, "one commit, one notification");
  assert.equal(store.getState().revision, 10);
  const next = store.receive(1, "ui_update", [delta({ revision: 11, base_revision: 10, panels: {} })], {});
  assert.equal(next.accepted, true);

  // The invented intermediate 9 is never admissible once 10 committed.
  const replayed = store.receive(1, "ui_update", [delta({ revision: 9, base_revision: 7 })], {});
  assert.equal(replayed.accepted, false);
  assert.equal(replayed.reason, "not_newer");
});

test("one failing member rolls back the whole staged delta", () => {
  const store = committedStore();
  const before = store.getState();
  let notified = 0;
  store.subscribe(() => notified++);
  const broken = delta({
    revision: 9,
    mode: "combat",
    panels: {
      status: validStatusPanel({ disguise_active: "yes" }),
      quest_log: unavailable("quest_log"),
    },
    removed_panels: ["objectives"],
  });
  const result = store.receive(1, "ui_update", [broken], {});
  assert.equal(result.accepted, false);
  assert.equal(result.reason, "invalid");
  assert.equal(notified, 0, "a rejected presentation never notifies");
  const after = store.getState();
  assert.deepEqual(after.panels, before.panels);
  assert.equal(after.mode, before.mode);
  assert.equal(after.revision, before.revision);
  assert.deepEqual(after.serverTime, before.serverTime);
});

test("a delta whose staged mode is dialogue must leave a committed dialogue panel", () => {
  const store = committedStore();
  const rejected = store.receive(
    1,
    "ui_update",
    [delta({ revision: 8, mode: "dialogue", panels: { status: validStatusPanel() } })],
    {}
  );
  assert.equal(rejected.accepted, false);
  assert.equal(rejected.reason, "invalid");
  assert.equal(store.getState().mode, "exploration");

  // A candidate dialogue panel in the same delta satisfies the relation.
  const accepted = store.receive(
    1,
    "ui_update",
    [
      delta({
        revision: 8,
        mode: "dialogue",
        panels: {
          status: validStatusPanel(),
          dialogue: unavailable("dialogue"),
        },
      }),
    ],
    {}
  );
  assert.equal(accepted.accepted, true);
  assert.equal(store.getState().mode, "dialogue");

  // Equal dialogue content may be omitted while the committed panel remains.
  const continued = store.receive(
    1,
    "ui_update",
    [delta({ revision: 9, mode: "dialogue", panels: { status: validStatusPanel() } })],
    {}
  );
  assert.equal(continued.accepted, true);
  assert.equal(store.getState().mode, "dialogue");

  // Removing the committed dialogue panel while staying in dialogue rejects.
  const removing = store.receive(
    1,
    "ui_update",
    [delta({ revision: 10, mode: "dialogue", panels: {}, removed_panels: ["dialogue"] })],
    {}
  );
  assert.equal(removing.accepted, false);
  assert.equal(store.getState().revision, 9);
});

test("an unfinished map transfer never advances the committed revision", () => {
  const store = committedStore();
  let notified = 0;
  store.subscribe(() => notified++);
  const area = F.wildernessArea();
  const parts = F.encodeParts(area, "T".repeat(22));
  assert.ok(parts.length > 1);
  for (const part of parts.slice(0, -1)) {
    const result = store.receive(
      1,
      "ui_update",
      [delta({ revision: 8, base_revision: 7, panels: { area_map: part } })],
      {}
    );
    assert.equal(result.accepted, false);
    assert.equal(result.pending, true);
    assert.equal(store.getState().revision, 7);
  }
  const done = store.receive(
    1,
    "ui_update",
    [delta({ revision: 8, base_revision: 7, panels: { area_map: parts[parts.length - 1] } })],
    {}
  );
  assert.equal(done.accepted, true);
  assert.equal(notified, 1);
  const state = store.getState();
  assert.equal(state.revision, 8);
  assert.deepEqual(state.maps.area_map, Protocol.validateMapPanel("area_map", area));
  assert.equal(Object.prototype.hasOwnProperty.call(state.panels, "area_map"), false);
});

test("a part frame whose baseline differs from the transfer is rejected", () => {
  const store = committedStore();
  const parts = F.encodeParts(F.wildernessArea(), "U".repeat(22));
  const staged = store.receive(1, "ui_update", [delta({ revision: 8, base_revision: 7, panels: { area_map: parts[0] } })], {});
  assert.equal(staged.pending, true);
  const mismatched = store.receive(
    1,
    "ui_update",
    [delta({ revision: 8, base_revision: 6, panels: { area_map: parts[1] } })],
    {}
  );
  assert.equal(mismatched.accepted, false);
  assert.equal(mismatched.reason, "base_mismatch");
  assert.equal(store.getState().revision, 7);
  assert.deepEqual(store.getState().maps, {});
});

test("parts of one transfer must agree on the removal list", () => {
  const store = committedStore();
  const parts = F.encodeParts(F.wildernessArea(), "V".repeat(22));
  assert.equal(
    store.receive(
      1,
      "ui_update",
      [delta({ revision: 8, base_revision: 7, panels: { area_map: parts[0] }, removed_panels: ["objectives"] })],
      {}
    ).pending,
    true
  );
  const conflicting = store.receive(
    1,
    "ui_update",
    [delta({ revision: 8, base_revision: 7, panels: { area_map: parts[1] }, removed_panels: [] })],
    {}
  );
  assert.equal(conflicting.accepted, false);
  assert.equal(conflicting.reason, "conflicting_part");
  assert.equal(store.getState().revision, 7);
  assert.deepEqual(store.getState().maps, {});
});

test("removals never name maps and a snapshot keeps same-epoch maps", () => {
  const store = committedStore();
  store.receive(
    1,
    "ui_update",
    [delta({ revision: 8, base_revision: 7, panels: { area_map: F.gridArea() } })],
    {}
  );
  assert.ok(store.getState().maps.area_map);
  const snapshotResult = store.receive(
    1,
    "ui_snapshot",
    [snapshot({ revision: 9, panels: { status: validStatusPanel() } })],
    {}
  );
  assert.equal(snapshotResult.accepted, true);
  assert.ok(store.getState().maps.area_map, "same-epoch maps survive an eager snapshot");
  assert.deepEqual(Object.keys(store.getState().panels), ["status"]);
});

test("the accepted envelope is the exact nine-field shape", () => {
  const meta = Protocol.validateUpdate(delta({ revision: 2 }));
  assert.deepEqual(Object.keys(meta).sort(), [
    "baseRevision",
    "epoch",
    "layoutVersion",
    "mode",
    "panels",
    "protocolVersion",
    "removedPanels",
    "revision",
    "serverTime",
  ]);
  assert.equal(Protocol.validateSnapshot(snapshot()).epoch, VALID_EPOCH);
});
