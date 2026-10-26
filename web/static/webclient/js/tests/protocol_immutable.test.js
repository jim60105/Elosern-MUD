/*
 * Immutable committed presentation ownership (webclient-immutable-adoption).
 *
 * The reducer publishes two explicit read contracts over one authoritative
 * state: `getCommittedState()` is one owned frozen committed record per
 * publication (the value every subscriber receives), and `getState()` is a
 * detached mutable snapshot. These tests pin the delta spec's scenarios:
 * reference retention and delta reuse, mutation resistance from both the
 * transport input and a hostile subscriber, old-record stability, snapshot
 * isolation, exactly one notification per complete publication and none for a
 * pending part, and immutable adoption of results, errors and maps.
 *
 * Fixtures are the shared synthetic protocol fixtures: no shipped lore or
 * presentation copy is named.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const core = require("../elosern/protocol/core.js");
const {
  EPOCH_B,
  VALID_EPOCH,
  serverTime,
  validStatusPanel,
  connectedStore,
  snapshot,
  update,
  actionResult,
  protocolError,
} = require("./protocol_support.js");
const fixtures = require("./protocol_fixtures.js");
const F = require("./map_panel_fixtures.js");

// The exact wire transfer identities: 22 URL-safe characters for one map
// body, 32 lowercase hexadecimal characters for one general publication.
const MAP_TRANSFER = "cd".repeat(11);
const PUBLICATION_TRANSFER = "ab".repeat(16);

function storeWithPanels(panels, revision) {
  const store = Protocol.createStore();
  store.beginTransport(1);
  const result = store.receive(
    1,
    "ui_snapshot",
    [snapshot({ revision: revision || 1, panels: panels })],
    {}
  );
  assert.equal(result.accepted, true, "fixture snapshot is valid");
  return store;
}

function statusWith(overrides) {
  return validStatusPanel(overrides);
}

function panelPanels(statusOverrides) {
  return {
    status: statusWith(statusOverrides),
    quest_log: fixtures.validQuestLogPanel([]),
  };
}

// One exact-base delta frame naming only the panels it carries: the shared
// `update` helper deep-merges its default status panel in, which a map-part
// frame must never do.
function deltaFrame(panels, revision) {
  return {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: revision,
    base_revision: revision - 1,
    removed_panels: [],
    mode: "exploration",
    panels: panels,
    layout_version: 1,
    server_time: serverTime(),
  };
}

// A schema-valid lore_codex panel whose canonical bytes exceed one publication
// part, so one logical publication needs a bounded multi-part transfer.
const CODEX_CATEGORIES = [
  "race",
  "nation",
  "region",
  "monster",
  "element",
  "magic",
  "anchor",
  "guild",
];

function codexPanel(valueChars) {
  const entries = [];
  for (let entry = 0; entry < 8; entry++) {
    const card = [];
    for (let field = 0; field < 8; field++) {
      card.push({ name: "field_" + field, value: "字".repeat(valueChars) });
    }
    entries.push({ key: "entry_" + entry, title: "條目", card: card });
  }
  return {
    schema_version: 1,
    available: true,
    categories: CODEX_CATEGORIES.map((key, position) => ({
      key: key,
      label: "類別" + position,
      count: position === 0 ? entries.length : 0,
      entries: position === 0 ? entries : [],
    })),
    discovered_total: entries.length,
  };
}

function chunkStrings(raw) {
  const chunks = [];
  for (let index = 0; index < raw.length; index += Protocol.PUBLICATION_CHUNK_BYTES) {
    chunks.push(
      raw
        .subarray(index, index + Protocol.PUBLICATION_CHUNK_BYTES)
        .toString("base64")
    );
  }
  return chunks;
}

// Split one validated logical presentation into exact publication-part frames,
// exactly as the server encoder does.
function publicationFrames(logical) {
  const raw = Buffer.from(core.canonicalJson(logical), "utf8");
  const size = Protocol.PUBLICATION_PART_BYTES;
  const count = Math.ceil(raw.length / size);
  const frames = [];
  for (let index = 0; index < count; index++) {
    const part = raw.subarray(index * size, Math.min(raw.length, (index + 1) * size));
    const frame = {
      protocol_version: 1,
      presentation_epoch: logical.presentation_epoch,
      revision: logical.revision,
      publication_kind: logical.base_revision === undefined ? "snapshot" : "delta",
      transfer_id: PUBLICATION_TRANSFER,
      part_index: index,
      part_count: count,
      total_bytes: raw.length,
      chunks: chunkStrings(part),
    };
    if (frame.publication_kind === "delta") {
      frame.base_revision = logical.base_revision;
    }
    frames.push(frame);
  }
  return frames;
}

function deepFrozen(value) {
  if (value === null || typeof value !== "object") {
    return true;
  }
  if (!Object.isFrozen(value)) {
    return false;
  }
  return Object.keys(value).every((key) => deepFrozen(value[key]));
}

test("a delta keeps an unchanged eager panel by identity and replaces the changed one", () => {
  const store = storeWithPanels(panelPanels());
  const before = store.getCommittedState();
  const committedQuestLog = before.panels.quest_log;
  const committedStatus = before.panels.status;
  assert.notEqual(committedQuestLog, undefined);

  let notified = 0;
  store.subscribe(() => {
    notified += 1;
  });
  const result = store.receive(
    1,
    "ui_update",
    [update({ revision: 2, panels: { status: statusWith({ disguise_active: true }) } })],
    {}
  );
  assert.equal(result.accepted, true);
  assert.equal(notified, 1, "one complete publication notifies once");

  const after = store.getCommittedState();
  assert.notEqual(after, before, "each publication is its own record");
  assert.equal(after.panels.quest_log, committedQuestLog, "the untouched panel keeps its identity");
  assert.notEqual(after.panels.status, committedStatus, "the replaced panel is a new committed value");
  assert.equal(after.panels.status.disguise_active, true);
  assert.equal(deepFrozen(after), true, "the whole committed record is recursively frozen");
});

test("a metadata-only publication changes the record but reuses every panel value", () => {
  const store = storeWithPanels(panelPanels());
  const before = store.getCommittedState();
  const result = store.receive(
    1,
    "ui_action_result",
    [actionResult({ presentation_revision: 1 })],
    {}
  );
  assert.equal(result.accepted, true);

  const after = store.getCommittedState();
  assert.notEqual(after, before);
  assert.notEqual(after.panels, before.panels, "the panel dictionary is a new frozen dictionary");
  assert.equal(after.panels.status, before.panels.status);
  assert.equal(after.panels.quest_log, before.panels.quest_log);
  assert.equal(after.revision, before.revision, "a result never advances the presentation");
  assert.notEqual(after.lastActionResult, before.lastActionResult);
});

test("an equal complete alignment reuses the already owned panel values", () => {
  const store = storeWithPanels(panelPanels());
  const before = store.getCommittedState();
  // A fresh caller-owned object graph with identical content: the checkpoint
  // must publish the committed values, not new copies of them.
  const result = store.receive(
    1,
    "ui_snapshot",
    [snapshot({ revision: 2, panels: panelPanels() })],
    {}
  );
  assert.equal(result.accepted, true);
  const after = store.getCommittedState();
  assert.equal(after.revision, 2);
  assert.equal(after.panels.status, before.panels.status);
  assert.equal(after.panels.quest_log, before.panels.quest_log);
});

test("a hostile subscriber cannot corrupt committed state", () => {
  const store = storeWithPanels(panelPanels());
  const authoritative = store.getCommittedState().panels.status.resources.hp.current;
  const observations = [];
  // A non-strict function body: a write to a frozen object is silently ignored
  // there, exactly what a third-party listener written in sloppy mode sees.
  const sloppyWrite = new Function(
    "record",
    [
      "record.panels.status.resources.hp.current = 0;",
      "record.panels.status.available = false;",
      "record.panels.quest_log.rows = null;",
      "delete record.panels.quest_log;",
      "record.recovery.status = 'failed';",
    ].join("\n")
  );
  store.subscribe((record) => {
    let strictError = null;
    sloppyWrite(record);
    try {
      record.panels.status.resources.hp.current = 1;
    } catch (error) {
      strictError = error;
    }
    observations.push({ record, strictError });
  });
  let later = null;
  store.subscribe((record) => {
    later = record;
  });

  assert.equal(
    store.receive(1, "ui_update", [update({ revision: 2, panels: {} })], {}).accepted,
    true
  );

  // Observing inside a subscriber proves nothing (the reducer swallows listener
  // exceptions), so the assertions run outside it.
  assert.equal(observations.length, 1, "the subscriber ran once");
  assert.ok(
    observations[0].strictError === null ||
      observations[0].strictError instanceof TypeError,
    "a strict-mode write is rejected with a TypeError"
  );
  const after = store.getCommittedState();
  assert.equal(after.panels.status.resources.hp.current, authoritative);
  assert.equal(after.panels.status.available, true);
  assert.equal(Object.prototype.hasOwnProperty.call(after.panels, "quest_log"), true);
  assert.deepEqual(after.panels.quest_log.rows, []);
  assert.equal(after.recovery.status, "idle");
  assert.equal(later, after, "the later subscriber also reads the authoritative record");
  assert.equal(deepFrozen(after), true);
});

test("mutating the transport envelope after receive cannot change adopted state", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);
  const envelope = snapshot({ revision: 1, panels: panelPanels() });
  assert.equal(store.receive(1, "ui_snapshot", [envelope], {}).accepted, true);
  const adopted = store.getCommittedState();
  const expected = store.getState();

  envelope.panels.status.resources.hp.current = 0;
  envelope.panels.quest_log.rows.push({ quest_id: "t_injected", state: "tracked" });
  envelope.server_time.hour = 23;
  envelope.mode = "combat";

  assert.deepEqual(store.getCommittedState().panels, expected.panels);
  assert.deepEqual(store.getState().panels, expected.panels);
  assert.equal(store.getCommittedState().serverTime.hour, expected.serverTime.hour);
  assert.equal(store.getCommittedState().mode, "exploration");
  assert.equal(adopted.panels.status.resources.hp.current, expected.panels.status.resources.hp.current);

  // The same isolation holds for the other adoption boundaries: an action
  // result's data slot (which the validator returns from the caller's own
  // object) and an on-demand map body.
  const resultPayload = actionResult({
    presentation_revision: 1,
    data: { k0: [{ nested: "before" }] },
  });
  assert.equal(store.receive(1, "ui_action_result", [resultPayload], {}).accepted, true);
  resultPayload.data.k0[0].nested = "after";
  assert.equal(store.getCommittedState().lastActionResult.data.k0[0].nested, "before");

  const mapBody = F.gridArea();
  assert.equal(
    store.receive(1, "ui_update", [update({ revision: 2, panels: { area_map: mapBody } })], {})
      .accepted,
    true
  );
  const committedMap = store.getCommittedState().maps.area_map;
  const mapTitle = committedMap.title;
  mapBody.title = "改寫";
  assert.equal(store.getCommittedState().maps.area_map.title, mapTitle);
  assert.equal(store.getState().maps.area_map.title, mapTitle);
});

test("a result data slot keeping an own __proto__ key survives adoption", () => {
  const store = connectedStore(VALID_EPOCH, 1);
  // JSON.parse keeps "__proto__" as an own data property; the copy must keep
  // that shape instead of turning the key into a prototype.
  const data = JSON.parse('{"__proto__":{"marker":"kept"},"k0":"value"}');
  assert.equal(store.receive(1, "ui_action_result", [actionResult({ presentation_revision: 1, data: data })], {}).accepted, true);
  const adopted = store.getCommittedState().lastActionResult.data;
  assert.equal(Object.prototype.hasOwnProperty.call(adopted, "__proto__"), true);
  assert.equal(Object.getPrototypeOf(adopted), Object.prototype);
  assert.deepEqual(adopted.__proto__, { marker: "kept" });
  assert.equal(adopted.k0, "value");
  assert.equal(Object.isFrozen(adopted.__proto__), true);
  assert.deepEqual(store.getState().lastActionResult.data, data);
});

test("a retained old committed record stays stable across replacement and removal", () => {
  const store = storeWithPanels(panelPanels());
  const first = store.getCommittedState();
  const firstStatusJson = core.canonicalJson(first.panels.status);

  assert.equal(
    store.receive(
      1,
      "ui_update",
      [
        update({
          revision: 2,
          panels: { status: statusWith({ disguise_active: true }) },
          removed_panels: ["quest_log"],
        }),
      ],
      {}
    ).accepted,
    true
  );

  assert.equal(first.revision, 1);
  assert.equal(core.canonicalJson(first.panels.status), firstStatusJson);
  assert.equal(Object.prototype.hasOwnProperty.call(first.panels, "quest_log"), true);
  assert.equal(first.panels.status.disguise_active, false);
  const second = store.getCommittedState();
  assert.equal(Object.prototype.hasOwnProperty.call(second.panels, "quest_log"), false);
  assert.equal(second.panels.status.disguise_active, true);
});

test("detached snapshots stay isolated from the reducer and from later commits", () => {
  const store = storeWithPanels(panelPanels());
  const kept = store.getState();
  const keptJson = core.canonicalJson(kept);

  const edited = store.getState();
  edited.panels.status.resources.hp.current = 0;
  edited.panels.quest_log.rows.push({ quest_id: "t_local", state: "tracked" });
  edited.recovery.status = "failed";
  assert.equal(store.getCommittedState().panels.status.resources.hp.current, 80);
  assert.deepEqual(store.getCommittedState().panels.quest_log.rows, []);
  assert.equal(store.getCommittedState().recovery.status, "idle");
  assert.notEqual(store.getState().panels.status, edited.panels.status, "each snapshot is its own copy");

  assert.equal(
    store.receive(
      1,
      "ui_update",
      [update({ revision: 2, panels: { status: statusWith({ disguise_active: true }) }, removed_panels: ["quest_log"] })],
      {}
    ).accepted,
    true
  );
  assert.equal(core.canonicalJson(kept), keptJson, "the retained snapshot is unchanged");
});

test("one notification per complete publication and none for a pending part", () => {
  const store = storeWithPanels(panelPanels());
  const before = store.getCommittedState();
  const seen = [];
  store.subscribe((record) => {
    seen.push(record);
  });

  const parts = F.encodeParts(F.largeWorldMap(100000), MAP_TRANSFER);
  assert.ok(parts.length > 1, "the fixture transfer has more than one part");
  for (const part of parts.slice(0, -1)) {
    const pending = store.receive(1, "ui_update", [deltaFrame({ world_map: part }, 2)], {});
    assert.equal(pending.pending, true);
  }
  assert.equal(seen.length, 0, "an invisible partial transfer never notifies");
  assert.equal(store.getCommittedState(), before, "and never replaces the committed record");

  assert.equal(
    store.receive(1, "ui_update", [deltaFrame({ world_map: parts[parts.length - 1] }, 2)], {}).accepted,
    true
  );
  assert.equal(seen.length, 1, "the complete map publishes exactly once");
  assert.equal(seen[0], store.getCommittedState());
  assert.notEqual(seen[0].maps.world_map, undefined);
  assert.equal(seen[0].mapPublications.world_map, 2);
  assert.equal(Object.prototype.hasOwnProperty.call(seen[0].panels, "world_map"), false);
});

test("a general publication transfer notifies once, on completion only", () => {
  const store = storeWithPanels(panelPanels());
  const before = store.getCommittedState();
  const seen = [];
  store.subscribe((record) => {
    seen.push(record);
  });

  const logical = snapshot({ revision: 2, panels: { lore_codex: codexPanel(120) } });
  const frames = publicationFrames(logical);
  assert.ok(frames.length > 1, "the logical document needs a bounded multi-part transfer");
  for (const frame of frames.slice(0, -1)) {
    const pending = store.receive(1, "ui_publication_part", [frame], {});
    assert.equal(pending.pending, true);
    assert.equal(store.getCommittedState(), before);
  }
  assert.equal(seen.length, 0, "intermediate parts are invisible");

  const completed = store.receive(1, "ui_publication_part", [frames[frames.length - 1]], {});
  assert.equal(completed.accepted, true);
  assert.equal(seen.length, 1, "the assembled publication notifies exactly once");
  const record = seen[0];
  assert.equal(record, store.getCommittedState());
  assert.equal(record.revision, 2);
  assert.equal(
    record.panels.status,
    before.panels.status,
    "an identical assembled panel value is reused by identity"
  );
  assert.notEqual(record.panels.lore_codex, undefined);
  assert.equal(deepFrozen(record), true);
});

test("same-epoch maps keep their references and a new epoch clears them", () => {
  const store = storeWithPanels(panelPanels());
  assert.equal(
    store.receive(1, "ui_update", [update({ revision: 2, panels: { area_map: F.gridArea() } })], {})
      .accepted,
    true
  );
  const withMap = store.getCommittedState();
  assert.equal(withMap.mapPublications.area_map, 2);

  assert.equal(
    store.receive(1, "ui_snapshot", [snapshot({ revision: 3, panels: panelPanels() })], {}).accepted,
    true
  );
  const aligned = store.getCommittedState();
  assert.equal(aligned.maps.area_map, withMap.maps.area_map, "the map value is reused by identity");
  assert.equal(aligned.mapPublications.area_map, 2);
  assert.equal(withMap.maps.area_map, aligned.maps.area_map);

  store.beginTransport(2);
  assert.equal(store.getCommittedState().maps.area_map, undefined, "a new generation clears maps");
  assert.equal(store.receive(2, "ui_snapshot", [snapshot({ revision: 1, presentation_epoch: EPOCH_B, panels: panelPanels() })], {}).accepted, true);
  assert.deepEqual(Object.keys(store.getCommittedState().maps), []);
  assert.notEqual(withMap.maps.area_map, undefined, "the retained record keeps its map");
});

test("a protocol error is adopted as an owned frozen record", () => {
  const store = connectedStore(VALID_EPOCH, 1);
  const payload = protocolError();
  assert.equal(store.receive(1, "ui_protocol_error", [payload], {}).accepted, true);
  const adopted = store.getCommittedState().protocolError;
  assert.equal(adopted.code, "unsupported_version");
  assert.equal(Object.isFrozen(adopted), true);
  assert.equal(store.getCommittedState().protocolIncompatible, true);
  assert.equal(store.getCommittedState().mutationsLocked, true);
});

test("a listener that publishes again keeps the outer publication's record", () => {
  const store = storeWithPanels(panelPanels());
  const a = [];
  const b = [];
  store.subscribe((record) => {
    a.push(record);
    if (a.length === 1) {
      // The app's own reentrant path: a listener records a recovery episode,
      // which publishes synchronously from inside this callback.
      store.noteRecovery("test_reentrancy");
    }
  });
  store.subscribe((record) => {
    b.push(record);
  });

  assert.equal(store.receive(1, "ui_action_result", [actionResult({ presentation_revision: 1 })], {}).accepted, true);

  assert.equal(a.length, 2, "the recording listener saw both publications");
  assert.equal(b.length, 2, "and so did the later listener");
  const outer = a[0];
  const nested = a[1];
  assert.notEqual(outer, nested);
  assert.equal(outer.recovery.status, "idle", "the outer record is the result publication");
  assert.equal(nested.recovery.status, "needed", "the nested record is the recovery publication");
  assert.deepEqual(b, [nested, outer], "each listener receives the same objects for each publication");
  assert.equal(store.getCommittedState(), nested, "the latest publication is the current record");
});
