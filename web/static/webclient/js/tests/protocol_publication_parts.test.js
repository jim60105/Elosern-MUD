/*
 * Bounded general publication assembly (webclient-publication-assembly):
 * exact ui_publication_part wire bounds, the invisible ordered assembler with
 * its fixed deadline, and the production store's one atomic adoption.
 *
 * Fixtures are synthetic: a valid near-cap lore_codex panel (invented labels)
 * plus the shared valid status panel. No shipped lore or presentation copy is
 * named.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const core = require("../elosern/protocol/core.js");
const { validStatusPanel } = require("./protocol_support.js");
const F = require("./map_panel_fixtures.js");

const EPOCH = "p".repeat(22);
const OTHER_EPOCH = "q".repeat(22);
const TRANSFER = "ab".repeat(16);
const TRANSFER_B = "cd".repeat(16);
const PART_BYTES = Protocol.PUBLICATION_PART_BYTES;
const CHUNK_BYTES = Protocol.PUBLICATION_CHUNK_BYTES;

const CATEGORIES = [
  "race",
  "nation",
  "region",
  "monster",
  "element",
  "magic",
  "anchor",
  "guild",
];

function serverTime() {
  return {
    year: 1204,
    season_index: 2,
    season_label: "仲夏",
    day_in_season: 17,
    hour: 14,
    minute: 30,
    second: 5,
  };
}

function snapshotDoc(panels, overrides) {
  return Object.assign(
    {
      protocol_version: 1,
      presentation_epoch: EPOCH,
      revision: 1,
      mode: "exploration",
      panels: panels,
      layout_version: 1,
      server_time: serverTime(),
    },
    overrides || {}
  );
}

function deltaDoc(panels, overrides) {
  return Object.assign(
    {
      protocol_version: 1,
      presentation_epoch: EPOCH,
      revision: 2,
      base_revision: 1,
      removed_panels: [],
      mode: "exploration",
      panels: panels,
      layout_version: 1,
      server_time: serverTime(),
    },
    overrides || {}
  );
}

// One schema-valid lore_codex panel with tunable field widths. The category
// keys are protocol vocabulary; labels and field names are invented.
function codexPanel(width, last) {
  function value(index) {
    return "字".repeat(index === 0 ? last : width);
  }
  const entries = [];
  for (let entry = 0; entry < 8; entry++) {
    const card = [];
    for (let field = 0; field < 8; field++) {
      card.push({ name: "field_" + field, value: value(entry * 8 + field) });
    }
    entries.push({ key: "entry_" + entry, title: "條目", card: card });
  }
  const categories = CATEGORIES.map((key, position) => ({
    key: key,
    label: "類別" + position,
    count: position === 0 ? entries.length : 0,
    entries: position === 0 ? entries : [],
  }));
  return {
    schema_version: 1,
    available: true,
    categories: categories,
    discovered_total: entries.length,
  };
}

function codexFits(panel) {
  try {
    Protocol.validateLoreCodexPanel(panel);
    return true;
  } catch (error) {
    return false;
  }
}

// The largest valid lore_codex panel, just under its own 65,536-byte cap.
function nearCapCodex() {
  let bestWidth = 0;
  let low = 0;
  let high = 1024;
  while (low <= high) {
    const width = Math.floor((low + high) / 2);
    if (codexFits(codexPanel(width, width))) {
      bestWidth = width;
      low = width + 1;
    } else {
      high = width - 1;
    }
  }
  let chosen = codexPanel(bestWidth, bestWidth);
  low = 0;
  high = 1024;
  while (low <= high) {
    const last = Math.floor((low + high) / 2);
    const candidate = codexPanel(bestWidth, last);
    if (codexFits(candidate)) {
      chosen = candidate;
      low = last + 1;
    } else {
      high = last - 1;
    }
  }
  const size = core.jsonByteSize(chosen);
  assert.ok(size > Protocol.MAX_CANONICAL_JSON_BYTES - 512, "fixture sits near the panel cap");
  return chosen;
}

function chunkStrings(raw) {
  const chunks = [];
  for (let index = 0; index < raw.length; index += CHUNK_BYTES) {
    chunks.push(raw.subarray(index, index + CHUNK_BYTES).toString("base64"));
  }
  return chunks;
}

// Split one logical document into exact part frames exactly as the server
// encoder does. `overrides` may deliberately disagree with the logical body
// to model a header/body contradiction.
function framesFor(logical, overrides) {
  const options = Object.assign(
    {
      epoch: logical.presentation_epoch,
      revision: logical.revision,
      kind: logical.base_revision === undefined ? "snapshot" : "delta",
      baseRevision: logical.base_revision,
      transferId: TRANSFER,
    },
    overrides || {}
  );
  const raw = Buffer.from(core.canonicalJson(logical), "utf8");
  const count = Math.ceil(raw.length / PART_BYTES);
  const frames = [];
  for (let index = 0; index < count; index++) {
    const part = raw.subarray(index * PART_BYTES, Math.min(raw.length, (index + 1) * PART_BYTES));
    const frame = {
      protocol_version: 1,
      presentation_epoch: options.epoch,
      revision: options.revision,
      publication_kind: options.kind,
      transfer_id: options.transferId,
      part_index: index,
      part_count: count,
      total_bytes: raw.length,
      chunks: chunkStrings(part),
    };
    if (options.kind === "delta") {
      frame.base_revision = options.baseRevision;
    }
    frames.push(frame);
  }
  return { frames: frames, raw: raw };
}

function fakeClock() {
  let time = 0;
  let sequence = 0;
  const timers = new Map();
  const cleared = new Map();
  return {
    now: function () {
      return time;
    },
    setTimer: function (callback, delay) {
      sequence += 1;
      const handle = sequence;
      timers.set(handle, { at: time + delay, callback: callback });
      return handle;
    },
    clearTimer: function (handle) {
      const entry = timers.get(handle);
      if (entry) {
        cleared.set(handle, entry);
        timers.delete(handle);
      }
    },
    advance: function (milliseconds) {
      time += milliseconds;
      Array.from(timers.entries()).forEach(function (pair) {
        if (pair[1].at <= time) {
          timers.delete(pair[0]);
          pair[1].callback();
        }
      });
    },
    // Advance without dispatching due callbacks (a delayed timer turn).
    jump: function (milliseconds) {
      time += milliseconds;
    },
    // Fire callbacks that were cancelled/cleared (a call already queued).
    fireCleared: function () {
      const pending = Array.from(cleared.values());
      cleared.clear();
      pending.forEach(function (entry) {
        entry.callback();
      });
    },
    pending: function () {
      return timers.size;
    },
  };
}

function makeStore(clock) {
  if (!clock) {
    return Protocol.createStore();
  }
  return Protocol.createStore({
    now: clock.now,
    setTimer: clock.setTimer,
    clearTimer: clock.clearTimer,
  });
}

function activeStore(clock) {
  const store = makeStore(clock);
  store.beginTransport(1);
  const result = store.receive(
    1,
    "ui_snapshot",
    [snapshotDoc({ status: validStatusPanel() }, { revision: 1 })],
    {}
  );
  assert.equal(result.accepted, true);
  return store;
}

function sendFrames(store, frames, generation) {
  return frames.map(function (frame) {
    return store.receive(generation === undefined ? 1 : generation, "ui_publication_part", [frame], {});
  });
}

function makeAssembler(clock, failures) {
  return Protocol.createPublicationAssembler({
    now: clock.now,
    setTimer: clock.setTimer,
    clearTimer: clock.clearTimer,
    onFailure: function (failure) {
      failures.push(failure);
    },
  });
}

// ---------------------------------------------------------------------------
// Exact part wire.
// ---------------------------------------------------------------------------

test("a part frame derives its exact header, chunk count and decoded sizes", () => {
  const { frames, raw } = framesFor(snapshotDoc({ status: validStatusPanel() }));
  assert.equal(frames.length, 1);
  const decoded = Protocol.validatePublicationPart(frames[0]);
  assert.deepEqual(decoded.header, {
    protocolVersion: 1,
    epoch: EPOCH,
    revision: 1,
    kind: "snapshot",
    transferId: TRANSFER,
    partIndex: 0,
    partCount: 1,
    totalBytes: raw.length,
    baseRevision: null,
  });
  const total = decoded.chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  assert.equal(total, raw.length);
  assert.deepEqual(
    framesFor(deltaDoc({ status: validStatusPanel() })).frames[0].base_revision,
    1
  );
});

test("the 683-part and 16 MiB ceilings are exact before any allocation", () => {
  const total = Protocol.PUBLICATION_MAX_BYTES;
  const count = Protocol.PUBLICATION_MAX_PARTS;
  const remainder = total - PART_BYTES * (count - 1);
  const chunks = [];
  for (let index = 0; index < Math.ceil(remainder / CHUNK_BYTES) - 1; index++) {
    chunks.push(Buffer.alloc(CHUNK_BYTES, 0x61).toString("base64"));
  }
  chunks.push(Buffer.alloc(remainder - CHUNK_BYTES * (chunks.length), 0x61).toString("base64"));
  const last = {
    protocol_version: 1,
    presentation_epoch: EPOCH,
    revision: 1,
    publication_kind: "snapshot",
    transfer_id: TRANSFER,
    part_index: count - 1,
    part_count: count,
    total_bytes: total,
    chunks: chunks,
  };
  const decoded = Protocol.validatePublicationPart(last);
  assert.equal(decoded.header.partCount, 683);
  assert.equal(decoded.chunks.length, 11);
  // Every non-final chunk of a part is 1,536 raw bytes; the final one is the
  // exact 1,024-byte remainder of the 16,384-byte final part.
  assert.equal(decoded.chunks[10].length, 1024);

  assert.throws(
    () => Protocol.validatePublicationPart(Object.assign({}, last, { part_count: count + 1 })),
    /part_count/
  );
  assert.throws(
    () => Protocol.validatePublicationPart(Object.assign({}, last, { total_bytes: total + 1 })),
    /total_bytes/
  );
  assert.throws(
    () => Protocol.validatePublicationPart(Object.assign({}, last, { part_index: count })),
    /part_index/
  );
});

test("contradictory base, kind, chunk and field shapes reject", () => {
  const snapshotFrame = framesFor(snapshotDoc({ status: validStatusPanel() })).frames[0];
  const deltaFrames = framesFor(deltaDoc({ status: validStatusPanel() })).frames;

  assert.throws(
    () => Protocol.validatePublicationPart(Object.assign({}, snapshotFrame, { base_revision: 1 })),
    /snapshot part forbids base_revision/
  );
  const missingBase = Object.assign({}, deltaFrames[0]);
  delete missingBase.base_revision;
  assert.throws(() => Protocol.validatePublicationPart(missingBase), /requires base_revision/);
  assert.throws(
    () => Protocol.validatePublicationPart(Object.assign({}, deltaFrames[0], { base_revision: 2 })),
    /older than revision/
  );
  assert.throws(
    () => Protocol.validatePublicationPart(Object.assign({}, snapshotFrame, { chunks: ["AAA=AAAA"] })),
    /canonical base64|chunks/
  );
  const badChunk = Object.assign({}, snapshotFrame, {
    chunks: snapshotFrame.chunks.slice(),
  });
  badChunk.chunks[0] = Buffer.alloc(CHUNK_BYTES - 1, 0x61).toString("base64");
  assert.throws(() => Protocol.validatePublicationPart(badChunk), /chunk 0 size/);
  assert.throws(
    () => Protocol.validatePublicationPart(Object.assign({}, snapshotFrame, { unknown: true })),
    /unknown fields/
  );
  assert.throws(
    () => Protocol.validatePublicationPart(Object.assign({}, snapshotFrame, { transfer_id: "AB".repeat(16) })),
    /transfer_id/
  );
});

// ---------------------------------------------------------------------------
// Invisible assembler (unit, deterministic clock).
// ---------------------------------------------------------------------------

test("ordered parts assemble exactly once and a duplicate or skipped index fails", () => {
  const clock = fakeClock();
  const failures = [];
  const assembler = makeAssembler(clock, failures);
  const panel = nearCapCodex();
  const { frames } = framesFor(snapshotDoc({ lore_codex: panel }));
  assert.ok(frames.length > 1);
  const decoded = frames.map((frame) => Protocol.validatePublicationPart(frame));
  const context = { phase: "awaiting_initial_snapshot", committedRevision: null };

  assert.equal(assembler.accept(decoded[0].header, decoded[0].chunks, context).status, "pending");
  const duplicate = assembler.accept(decoded[0].header, decoded[0].chunks, context);
  assert.equal(duplicate.status, "failed");
  assert.equal(duplicate.reason, "duplicate_part");
  assert.equal(duplicate.recover, true);
  assert.equal(failures.length, 1);
  assert.equal(assembler.stats().live, false);
  assert.equal(clock.pending(), 0);

  const other = makeAssembler(fakeClock(), []);
  const otherDecoded = frames.map((frame) => Protocol.validatePublicationPart(frame));
  assert.equal(other.accept(otherDecoded[0].header, otherDecoded[0].chunks, context).status, "pending");
  const skipped = other.accept(otherDecoded[2].header, otherDecoded[2].chunks, context);
  assert.equal(skipped.status, "failed");
  assert.equal(skipped.reason, "out_of_order");
});

test("a complete transfer decodes strict UTF-8 JSON once and frees its buffers", () => {
  const clock = fakeClock();
  const assembler = makeAssembler(clock, []);
  const logical = snapshotDoc({ status: validStatusPanel() });
  const raw = Buffer.from(core.canonicalJson(logical), "utf8");
  const frame = {
    protocol_version: 1,
    presentation_epoch: EPOCH,
    revision: 1,
    publication_kind: "snapshot",
    transfer_id: TRANSFER,
    part_index: 0,
    part_count: 1,
    total_bytes: raw.length,
    chunks: chunkStrings(raw),
  };
  const decoded = Protocol.validatePublicationPart(frame);
  const result = assembler.accept(decoded.header, decoded.chunks, {
    phase: "awaiting_initial_snapshot",
    committedRevision: null,
  });
  assert.equal(result.status, "complete");
  assert.equal(result.kind, "snapshot");
  assert.deepEqual(result.logical, logical);
  assert.equal(assembler.stats().live, false);
  assert.equal(clock.pending(), 0);
});

test("a body that is not UTF-8 or not JSON fails without adoption", () => {
  function assembleBytes(bytes) {
    const clock = fakeClock();
    const failures = [];
    const assembler = makeAssembler(clock, failures);
    const frame = {
      protocol_version: 1,
      presentation_epoch: EPOCH,
      revision: 1,
      publication_kind: "snapshot",
      transfer_id: TRANSFER,
      part_index: 0,
      part_count: 1,
      total_bytes: bytes.length,
      chunks: chunkStrings(bytes),
    };
    const decoded = Protocol.validatePublicationPart(frame);
    const result = assembler.accept(decoded.header, decoded.chunks, {
      phase: "awaiting_initial_snapshot",
      committedRevision: null,
    });
    assert.equal(result.status, "failed");
    assert.equal(result.reason, "invalid_body");
    assert.equal(result.recover, true);
    assert.equal(failures.length, 1);
    assert.equal(assembler.stats().live, false);
    assert.equal(clock.pending(), 0);
  }
  assembleBytes(Buffer.from([0xff, 0xfe, 0xfd]));
  assembleBytes(Buffer.from("{not json", "utf8"));
  // Valid UTF-8 that is not a JSON document is still an invalid body.
  assembleBytes(Buffer.from("字".repeat(10), "utf8"));
});

test("a multi-byte character crossing a part boundary decodes intact", () => {
  const clock = fakeClock();
  const assembler = makeAssembler(clock, []);
  // 40,000 CJK characters: 120,000 UTF-8 bytes in two parts. Part two starts
  // inside a three-byte code point.
  const text = "字".repeat(40000);
  const bytes = Buffer.from('{"text":"' + text + '"}', "utf8");
  assert.ok(bytes.length > PART_BYTES);
  const frames = [];
  for (let index = 0, count = Math.ceil(bytes.length / PART_BYTES); index < count; index++) {
    frames.push({
      protocol_version: 1,
      presentation_epoch: EPOCH,
      revision: 1,
      publication_kind: "snapshot",
      transfer_id: TRANSFER,
      part_index: index,
      part_count: count,
      total_bytes: bytes.length,
      chunks: chunkStrings(bytes.subarray(index * PART_BYTES, (index + 1) * PART_BYTES)),
    });
  }
  let result = null;
  frames.forEach((frame) => {
    const decoded = Protocol.validatePublicationPart(frame);
    result = assembler.accept(decoded.header, decoded.chunks, {
      phase: "awaiting_initial_snapshot",
      committedRevision: null,
    });
  });
  assert.equal(result.status, "complete");
  assert.equal(result.logical.text, text);
});

test("the first-part deadline is fixed, expires once and is never refreshed", () => {
  const clock = fakeClock();
  const failures = [];
  const assembler = makeAssembler(clock, failures);
  const panel = nearCapCodex();
  const { frames } = framesFor(snapshotDoc({ lore_codex: panel }));
  const decoded = frames.map((frame) => Protocol.validatePublicationPart(frame));
  const context = { phase: "awaiting_initial_snapshot", committedRevision: null };

  assembler.accept(decoded[0].header, decoded[0].chunks, context);
  clock.advance(20_000);
  assert.equal(assembler.accept(decoded[1].header, decoded[1].chunks, context).status, "pending");
  clock.advance(9_999);
  assert.equal(clock.pending(), 1);
  assert.equal(assembler.stats().live, true);
  clock.advance(1);
  assert.equal(failures.length, 1);
  assert.equal(failures[0].reason, "timeout");
  assert.equal(assembler.stats().live, false);
  assert.equal(clock.pending(), 0);
  clock.advance(60_000);
  assert.equal(failures.length, 1);
});

test("a final part after the deadline but before the timer turn still fails", () => {
  const clock = fakeClock();
  const failures = [];
  const assembler = makeAssembler(clock, failures);
  const panel = nearCapCodex();
  const { frames } = framesFor(snapshotDoc({ lore_codex: panel }));
  const decoded = frames.map((frame) => Protocol.validatePublicationPart(frame));
  const context = { phase: "awaiting_initial_snapshot", committedRevision: null };
  assembler.accept(decoded[0].header, decoded[0].chunks, context);
  clock.jump(Protocol.PUBLICATION_ASSEMBLY_TIMEOUT_MS);
  const result = assembler.accept(decoded[1].header, decoded[1].chunks, context);
  assert.equal(result.status, "failed");
  assert.equal(result.reason, "timeout");
  assert.equal(failures.length, 1);
  assert.equal(clock.pending(), 0);
});

test("a newer snapshot supersedes an unfinished transfer; an older one is ignored", () => {
  const clock = fakeClock();
  const failures = [];
  const assembler = makeAssembler(clock, failures);
  const panel = nearCapCodex();
  const older = framesFor(snapshotDoc({ lore_codex: panel }, { revision: 5 }), {
    transferId: TRANSFER,
  });
  const newer = framesFor(snapshotDoc({ lore_codex: panel }, { revision: 7 }), {
    transferId: TRANSFER_B,
  });
  const context = { phase: "awaiting_initial_snapshot", committedRevision: null };

  const first = Protocol.validatePublicationPart(older.frames[0]);
  assembler.accept(first.header, first.chunks, context);
  const staleFrame = Protocol.validatePublicationPart(newer.frames[0]);
  // The older header of a third transfer is ignored, keeping the live one.
  const stale = Protocol.validatePublicationPart(
    framesFor(snapshotDoc({ lore_codex: panel }, { revision: 4 }), {
      transferId: "ef".repeat(16),
    }).frames[0]
  );
  const ignored = assembler.accept(stale.header, stale.chunks, context);
  assert.equal(ignored.status, "failed");
  assert.equal(ignored.reason, "superseded_transfer");
  assert.equal(assembler.stats().transferId, TRANSFER);

  // A newer same-epoch snapshot starts at part 0 and replaces the old one.
  const superseded = assembler.accept(staleFrame.header, staleFrame.chunks, context);
  assert.equal(superseded.status, "pending");
  assert.equal(assembler.stats().transferId, TRANSFER_B);
  assert.equal(assembler.stats().revision, 7);
  assert.equal(failures.length, 0);
  assert.equal(clock.pending(), 1);
});

test("a fresh-epoch part never disturbs the live transfer", () => {
  const clock = fakeClock();
  const failures = [];
  const assembler = makeAssembler(clock, failures);
  const panel = nearCapCodex();
  const { frames } = framesFor(snapshotDoc({ lore_codex: panel }, { revision: 5 }));
  const first = Protocol.validatePublicationPart(frames[0]);
  assembler.accept(first.header, first.chunks, {
    phase: "awaiting_initial_snapshot",
    committedRevision: null,
  });

  const other = Protocol.validatePublicationPart(
    framesFor(snapshotDoc({ lore_codex: panel }, { revision: 9, presentation_epoch: OTHER_EPOCH }), {
      transferId: TRANSFER_B,
    }).frames[0]
  );
  const result = assembler.accept(other.header, other.chunks, {
    phase: "awaiting_initial_snapshot",
    committedRevision: null,
  });
  assert.equal(result.reason, "different_epoch");
  assert.equal(assembler.stats().transferId, TRANSFER);
  assert.equal(failures.length, 0);
});

test("a replayed finished transfer and a later delta are both rejected safely", () => {
  const clock = fakeClock();
  const assembler = makeAssembler(clock, []);
  const logical = snapshotDoc({ status: validStatusPanel() });
  const { frames } = framesFor(logical);
  const decoded = Protocol.validatePublicationPart(frames[0]);
  const context = { phase: "awaiting_initial_snapshot", committedRevision: null };
  assert.equal(assembler.accept(decoded.header, decoded.chunks, context).status, "complete");
  const replay = assembler.accept(decoded.header, decoded.chunks, context);
  assert.equal(replay.reason, "finished_transfer");
  assert.equal(replay.recover, false);

  // A delta arriving while an incomplete snapshot is live abandons it.
  const failures = [];
  const second = makeAssembler(fakeClock(), failures);
  const panel = nearCapCodex();
  const snapshot = framesFor(snapshotDoc({ lore_codex: panel }, { revision: 5 }));
  const part = Protocol.validatePublicationPart(snapshot.frames[0]);
  second.accept(part.header, part.chunks, {
    phase: "awaiting_initial_snapshot",
    committedRevision: null,
  });
  const deltaFrame = Protocol.validatePublicationPart(
    framesFor(deltaDoc({ status: validStatusPanel() }, { revision: 6, base_revision: 4 }), {
      transferId: TRANSFER_B,
    }).frames[0]
  );
  const skipped = second.accept(deltaFrame.header, deltaFrame.chunks, {
    phase: "active",
    committedRevision: 4,
  });
  assert.equal(skipped.reason, "preceding_transfer");
  assert.equal(skipped.recover, true);
  assert.equal(failures.length, 1);
  assert.equal(second.stats().live, false);
});

test("clear and prune release buffers without a recovery signal", () => {
  const clock = fakeClock();
  const failures = [];
  const assembler = makeAssembler(clock, failures);
  const panel = nearCapCodex();
  const { frames } = framesFor(snapshotDoc({ lore_codex: panel }, { revision: 5 }));
  const decoded = Protocol.validatePublicationPart(frames[0]);
  const context = { phase: "awaiting_initial_snapshot", committedRevision: null };
  assembler.accept(decoded.header, decoded.chunks, context);
  assert.equal(assembler.stats().live, true);
  assert.equal(clock.pending(), 1);
  assembler.clear();
  assert.equal(assembler.stats().live, false);
  assert.equal(clock.pending(), 0);
  assert.equal(failures.length, 0);

  const second = makeAssembler(fakeClock(), failures);
  const again = Protocol.validatePublicationPart(frames[0]);
  second.accept(again.header, again.chunks, context);
  second.pruneThrough(5);
  assert.equal(second.stats().live, false);
  assert.equal(failures.length, 0);
});

test("a superseded transfer's queued timer cannot orphan the new deadline", () => {
  const clock = fakeClock();
  const failures = [];
  const assembler = makeAssembler(clock, failures);
  const panel = nearCapCodex();
  const context = { phase: "awaiting_initial_snapshot", committedRevision: null };
  const older = framesFor(snapshotDoc({ lore_codex: panel }, { revision: 5 }), {
    transferId: TRANSFER,
  });
  const newer = framesFor(snapshotDoc({ lore_codex: panel }, { revision: 7 }), {
    transferId: TRANSFER_B,
  });
  const first = Protocol.validatePublicationPart(older.frames[0]);
  assembler.accept(first.header, first.chunks, context);
  const superseding = Protocol.validatePublicationPart(newer.frames[0]);
  assert.equal(assembler.accept(superseding.header, superseding.chunks, context).status, "pending");
  // The older transfer's cancelled callback was already queued: it must not
  // relinquish the replacement timer.
  clock.fireCleared();
  assert.equal(assembler.stats().transferId, TRANSFER_B);
  assert.equal(clock.pending(), 1);
  assembler.clear();
  assert.equal(clock.pending(), 0);
  assert.equal(failures.length, 0);
});

// ---------------------------------------------------------------------------
// Store integration: one invisible atomic adoption.
// ---------------------------------------------------------------------------

test("an initial multipart snapshot establishes only after its final part", () => {
  const clock = fakeClock();
  const store = makeStore(clock);
  store.beginTransport(1);
  let notified = 0;
  store.subscribe(() => {
    notified += 1;
  });
  const panel = nearCapCodex();
  const logical = snapshotDoc({ lore_codex: panel });
  const { frames, raw } = framesFor(logical);
  assert.ok(frames.length > 1, "the fixture exceeds one intact frame");
  assert.ok(raw.length > Protocol.MAX_CANONICAL_JSON_BYTES);

  const partial = sendFrames(store, frames.slice(0, -1));
  partial.forEach((result) => {
    assert.equal(result.accepted, false);
    assert.equal(result.pending, true);
  });
  assert.equal(notified, 0);
  const before = store.getState();
  assert.equal(before.phase, "awaiting_initial_snapshot");
  assert.equal(before.activeEpoch, null);
  assert.equal(before.revision, null);
  assert.deepEqual(before.panels, {});

  const final = sendFrames(store, frames.slice(-1))[0];
  assert.equal(final.accepted, true);
  assert.equal(final.established, true);
  assert.equal(final.revision, 1);
  assert.equal(notified, 1, "exactly one notification for the complete publication");
  const state = store.getState();
  assert.equal(state.phase, "active");
  assert.equal(state.activeEpoch, EPOCH);
  assert.equal(state.revision, 1);
  assert.deepEqual(state.panels.lore_codex, panel);
  assert.deepEqual(store.publicationAssemblyStats().live, false);
  assert.equal(clock.pending(), 0);
});

test("a multipart delta is atomic and commits exactly once", () => {
  const clock = fakeClock();
  const store = activeStore(clock);
  const panel = nearCapCodex();
  let notified = 0;
  store.subscribe(() => {
    notified += 1;
  });
  const before = store.getState();
  const logical = deltaDoc(
    { lore_codex: panel },
    {
      revision: 2,
      base_revision: 1,
      mode: "combat",
      server_time: Object.assign(serverTime(), { hour: 15 }),
    }
  );
  const { frames, raw } = framesFor(logical);
  assert.ok(frames.length > 1);
  assert.ok(raw.length > Protocol.MAX_CANONICAL_JSON_BYTES);
  const results = sendFrames(store, frames);
  for (let index = 0; index < results.length - 1; index++) {
    assert.equal(results[index].pending, true);
  }
  assert.equal(results.at(-1).accepted, true);
  assert.equal(results.at(-1).revision, 2);
  assert.equal(notified, 1);
  const after = store.getState();
  assert.equal(after.revision, 2);
  assert.equal(after.mode, "combat");
  assert.equal(after.serverTime.hour, 15);
  assert.deepEqual(after.panels.lore_codex, panel);
  assert.ok(before.revision === 1);
});

test("the logical document must agree with its part headers", () => {
  const clock = fakeClock();
  const store = activeStore(clock);
  const panel = nearCapCodex();
  const { frames } = framesFor(snapshotDoc({ lore_codex: panel }, { revision: 2 }), {
    revision: 3,
  });
  const results = sendFrames(store, frames);
  const last = results.at(-1);
  assert.equal(last.accepted, false);
  assert.equal(last.reason, "invalid");
  assert.equal(last.recovery, "needed");
  const state = store.getState();
  assert.equal(state.revision, 1);
  assert.equal(state.recovery.status, "needed");
  assert.equal(state.recovery.cause, "invalid");
  assert.equal(state.mutationsLocked, true);
});

test("a stale malformed part never disturbs newer work or starts recovery", () => {
  const clock = fakeClock();
  const store = activeStore(clock);
  const panel = nearCapCodex();
  const latest = framesFor(snapshotDoc({ lore_codex: panel }, { revision: 2 }));
  assert.equal(store.receive(1, "ui_publication_part", [latest.frames[0]], {}).pending, true);

  // A trustworthy stale header whose chunk is non-canonical base64: decode is
  // never reached, so the live revision-2 transfer and recovery state stay
  // untouched.
  const staleChunk = {
    protocol_version: 1,
    presentation_epoch: EPOCH,
    revision: 1,
    publication_kind: "snapshot",
    transfer_id: "ef".repeat(16),
    part_index: 0,
    part_count: 1,
    total_bytes: 1,
    chunks: ["AB=="],
  };
  const staleResult = store.receive(1, "ui_publication_part", [staleChunk], {});
  assert.equal(staleResult.accepted, false);
  assert.equal(staleResult.reason, "not_newer");
  assert.equal(staleResult.recovery, undefined);
  assert.equal(store.getState().recovery.status, "idle");
  assert.equal(store.publicationAssemblyStats().live, true);

  // The same stale target with a header that cannot even be inspected stays
  // inert as well (identifiable epoch and revision, corrupt count).
  const staleInspected = Object.assign({}, staleChunk, {
    part_count: 4,
    part_index: 3,
  });
  const second = store.receive(1, "ui_publication_part", [staleInspected], {});
  assert.equal(second.reason, "not_newer");
  assert.equal(store.getState().recovery.status, "idle");
  assert.equal(store.publicationAssemblyStats().live, true);
  assert.equal(clock.pending(), 1);
});

test("assembly never legalizes a panel-local or on-demand violation", () => {
  const clock = fakeClock();
  const store = activeStore(clock);

  // A lore_codex panel over its own 65,536-byte panel cap: the whole logical
  // document would fit 16 MiB, but the panel local bound still rejects.
  const wide = codexPanel(1024, 1024);
  assert.throws(() => Protocol.validateLoreCodexPanel(wide));
  const oversized = framesFor(snapshotDoc({ lore_codex: wide }, { revision: 2 }));
  const rejected = sendFrames(store, oversized.frames).at(-1);
  assert.equal(rejected.accepted, false);
  assert.equal(rejected.reason, "invalid");
  assert.equal(store.getState().revision, 1);

  // An on-demand map body never rides a general publication.
  const withMap = deltaDoc({ area_map: F.gridArea() }, { revision: 2, base_revision: 1 });
  const mapFrame = framesFor(withMap, { transferId: TRANSFER_B }).frames[0];
  const mapResult = store.receive(1, "ui_publication_part", [mapFrame], {});
  assert.equal(mapResult.accepted, false);
  assert.equal(mapResult.reason, "invalid");
  assert.deepEqual(store.getState().maps, {});
  assert.equal(store.getState().revision, 1);
});

test("a base mismatch at final adoption preserves the committed presentation", () => {
  const clock = fakeClock();
  const store = activeStore(clock);
  const panel = nearCapCodex();
  const delta = framesFor(
    deltaDoc({ lore_codex: panel }, { revision: 5, base_revision: 1 })
  );
  const first = store.receive(1, "ui_publication_part", [delta.frames[0]], {});
  assert.equal(first.pending, true);

  // A newer intact snapshot commits revision 3 while the transfer is live; its
  // target (5) survives the prune, so the final part still needs base 3.
  const snapshot = store.receive(
    1,
    "ui_snapshot",
    [snapshotDoc({ status: validStatusPanel() }, { revision: 3 })],
    {}
  );
  assert.equal(snapshot.accepted, true);
  assert.equal(store.publicationAssemblyStats().live, true);

  const results = sendFrames(store, delta.frames.slice(1));
  const last = results.at(-1);
  assert.equal(last.accepted, false);
  assert.equal(last.reason, "base_mismatch");
  assert.equal(last.recovery, "needed");
  const state = store.getState();
  assert.equal(state.revision, 3);
  assert.equal(state.recovery.status, "needed");
  assert.equal(state.recovery.cause, "base_mismatch");
  assert.deepEqual(state.panels.status, validStatusPanel());
  assert.equal(Object.prototype.hasOwnProperty.call(state.panels, "lore_codex"), false);
});

test("a later intact delta cannot skip an incomplete general transfer", () => {
  const clock = fakeClock();
  const store = makeStore(clock);
  store.beginTransport(1);
  store.receive(1, "ui_snapshot", [snapshotDoc({ status: validStatusPanel() }, { revision: 1 })], {});
  const panel = nearCapCodex();
  const pendingFrames = framesFor(snapshotDoc({ lore_codex: panel }, { revision: 2 }));
  const pending = store.receive(1, "ui_publication_part", [pendingFrames.frames[0]], {});
  assert.equal(pending.pending, true);

  const later = store.receive(
    1,
    "ui_update",
    [deltaDoc({ status: validStatusPanel() }, { revision: 2, base_revision: 1 })],
    {}
  );
  assert.equal(later.accepted, false);
  assert.equal(later.reason, "incomplete_predecessor");
  assert.equal(later.recovery, "needed");
  const state = store.getState();
  assert.equal(state.revision, 1);
  assert.equal(state.recovery.status, "needed");
  assert.equal(store.publicationAssemblyStats().live, false);
});

test("a delta part cannot establish initial state", () => {
  const store = makeStore();
  store.beginTransport(1);
  const delta = framesFor(deltaDoc({ status: validStatusPanel() }, { revision: 2, base_revision: 1 }));
  const result = store.receive(1, "ui_publication_part", [delta.frames[0]], {});
  assert.equal(result.accepted, false);
  assert.equal(result.reason, "update_cannot_establish_epoch");
  assert.equal(store.getState().activeEpoch, null);
});

test("a detached store re-establishes from a fresh-epoch multipart snapshot", () => {
  const clock = fakeClock();
  const store = activeStore(clock);
  store.receive(
    1,
    "ui_protocol_error",
    [{ protocol_version: 1, code: "no_puppet", message: "沒有角色", reload_required: false }],
    {}
  );
  assert.equal(store.getState().phase, "detached");
  const panel = nearCapCodex();
  const logical = snapshotDoc({ lore_codex: panel }, { presentation_epoch: OTHER_EPOCH, revision: 1 });
  const { frames } = framesFor(logical);
  const results = sendFrames(store, frames);
  assert.equal(results.at(-1).accepted, true);
  assert.equal(results.at(-1).established, true);
  const state = store.getState();
  assert.equal(state.phase, "active");
  assert.equal(state.activeEpoch, OTHER_EPOCH);
  assert.equal(state.revision, 1);
});

test("pending parts never notify, change the revision or adopt an epoch", () => {
  const clock = fakeClock();
  const store = activeStore(clock);
  let notified = 0;
  store.subscribe(() => {
    notified += 1;
  });
  const panel = nearCapCodex();
  // The small status document is one part; the large snapshot stays pending.
  const large = framesFor(snapshotDoc({ lore_codex: panel }, { revision: 2 }));
  const pending = store.receive(1, "ui_publication_part", [large.frames[0]], {});
  assert.equal(pending.accepted, false);
  assert.equal(pending.pending, true);
  assert.equal(notified, 0);
  assert.equal(store.getState().revision, 1);
  assert.equal(store.getState().activeEpoch, EPOCH);

  // A matching action result is still recorded, but the pending publication
  // never advances the presentation or releases a gate of its own.
  const result = store.receive(
    1,
    "ui_action_result",
    [
      {
        protocol_version: 1,
        presentation_epoch: EPOCH,
        request_id: "session:1",
        outcome: "success",
        code: "completed",
        message: "完成",
        presentation_revision: 2,
      },
    ],
    {}
  );
  assert.equal(result.accepted, true);
  assert.equal(store.getState().revision, 1);
  assert.equal(store.getState().lastActionResult.presentationRevision, 2);
  assert.equal(notified, 1, "only the action result notified");
  assert.equal(store.publicationAssemblyStats().live, true);
});

test("a disconnect frees both assembly owners and their timers", () => {
  const clock = fakeClock();
  const store = activeStore(clock);
  const mapParts = F.encodeParts(F.largeWorldMap(100000), "P".repeat(22));
  const mapUpdate = {
    protocol_version: 1,
    presentation_epoch: EPOCH,
    revision: 2,
    base_revision: 1,
    removed_panels: [],
    mode: "exploration",
    panels: { world_map: mapParts[0] },
    layout_version: 1,
    server_time: serverTime(),
  };
  const mapResult = store.receive(1, "ui_update", [mapUpdate], {});
  assert.equal(mapResult.pending, true);
  // A general part may start beside the specialized map transfer (it is not
  // an intact ui_update).
  const panel = nearCapCodex();
  const general = framesFor(snapshotDoc({ lore_codex: panel }, { revision: 2 }));
  store.receive(1, "ui_publication_part", [general.frames[0]], {});
  assert.deepEqual(store.mapAssemblyStats().live, 1);
  assert.equal(store.publicationAssemblyStats().live, true);
  assert.equal(clock.pending(), 1);

  store.setConnected(false);
  assert.deepEqual(store.mapAssemblyStats(), { live: 0, bytes: 0 });
  assert.equal(store.publicationAssemblyStats().live, false);
  assert.equal(clock.pending(), 0);
});

test("an old generation part or timer callback cannot touch live state", () => {
  const clock = fakeClock();
  const store = activeStore(clock);
  const panel = nearCapCodex();
  const general = framesFor(deltaDoc({ lore_codex: panel }, { revision: 2, base_revision: 1 }));
  store.receive(1, "ui_publication_part", [general.frames[0]], {});
  assert.equal(store.publicationAssemblyStats().live, true);
  store.beginTransport(2);
  assert.equal(store.publicationAssemblyStats().live, false);
  assert.deepEqual(store.getState().recovery, { status: "idle", cause: null, generation: 2 });
  // A call that was already queued fires after the clear: it is inert.
  clock.fireCleared();
  assert.equal(store.getState().recovery.status, "idle");
  assert.equal(store.getState().activeEpoch, null);
  const stale = store.receive(1, "ui_publication_part", [general.frames[1]], {});
  assert.equal(stale.accepted, false);
  assert.equal(stale.reason, "stale_generation");
});

test("a completed general snapshot prunes obsolete map assembly and keeps a complete map", () => {
  const clock = fakeClock();
  const store = activeStore(clock);
  const committed = store.receive(
    1,
    "ui_update",
    [deltaDoc({ area_map: F.gridArea() }, { revision: 2, base_revision: 1 })],
    {}
  );
  assert.equal(committed.accepted, true);
  assert.ok(store.getState().maps.area_map);

  const mapParts = F.encodeParts(F.largeWorldMap(100000), "P".repeat(22));
  const partialMap = store.receive(
    1,
    "ui_update",
    [
      deltaDoc({ world_map: mapParts[0] }, { revision: 3, base_revision: 2 }),
    ],
    {}
  );
  assert.equal(partialMap.pending, true);
  assert.equal(store.mapAssemblyStats().live, 1);

  const panel = nearCapCodex();
  const logical = snapshotDoc({ lore_codex: panel }, { revision: 4 });
  const results = sendFrames(store, framesFor(logical).frames);
  assert.equal(results.at(-1).accepted, true);
  const state = store.getState();
  assert.equal(state.revision, 4);
  assert.ok(state.maps.area_map, "a same-epoch complete map survives the snapshot");
  assert.equal(Object.prototype.hasOwnProperty.call(state.maps, "world_map"), false);
  assert.deepEqual(store.mapAssemblyStats().live, 0);
});

test("a recovered generation keeps mutations locked through an unrelated delta", () => {
  const clock = fakeClock();
  const store = activeStore(clock);
  // Expire a general transfer, which records a recovery need.
  const panel = nearCapCodex();
  const general = framesFor(snapshotDoc({ lore_codex: panel }, { revision: 2 }));
  store.receive(1, "ui_publication_part", [general.frames[0]], {});
  clock.advance(Protocol.PUBLICATION_ASSEMBLY_TIMEOUT_MS);
  assert.equal(store.getState().recovery.status, "needed");
  assert.equal(store.getState().recovery.cause, "timeout");
  assert.equal(store.getState().mutationsLocked, true);

  // An unrelated but individually valid delta still commits its presentation
  // without clearing the recovery need or unlocking.
  const delta = store.receive(
    1,
    "ui_update",
    [deltaDoc({ status: validStatusPanel() }, { revision: 2, base_revision: 1 })],
    {}
  );
  assert.equal(delta.accepted, true);
  assert.equal(store.getState().revision, 2);
  assert.equal(store.getState().recovery.status, "needed");
  assert.equal(store.getState().mutationsLocked, true);

  // A complete validated snapshot is the A-side clearer.
  const repair = store.receive(
    1,
    "ui_snapshot",
    [snapshotDoc({ status: validStatusPanel() }, { revision: 3 })],
    {}
  );
  assert.equal(repair.accepted, true);
  assert.deepEqual(store.getState().recovery, { status: "idle", cause: null, generation: 1 });
  assert.equal(store.getState().mutationsLocked, false);
});

test("an establishment clears a provisional assembly from another epoch", () => {
  const clock = fakeClock();
  const store = makeStore(clock);
  store.beginTransport(1);
  const panel = nearCapCodex();
  const provisional = framesFor(
    snapshotDoc({ lore_codex: panel }, { presentation_epoch: EPOCH, revision: 100 })
  );
  const pending = store.receive(1, "ui_publication_part", [provisional.frames[0]], {});
  assert.equal(pending.pending, true);
  assert.equal(store.publicationAssemblyStats().live, true);

  const established = store.receive(
    1,
    "ui_snapshot",
    [snapshotDoc({ status: validStatusPanel() }, { presentation_epoch: OTHER_EPOCH, revision: 1 })],
    {}
  );
  assert.equal(established.accepted, true);
  assert.equal(store.getState().activeEpoch, OTHER_EPOCH);
  assert.equal(store.publicationAssemblyStats().live, false);
  assert.equal(clock.pending(), 0);
  clock.fireCleared();
  assert.equal(store.getState().recovery.status, "idle");
});
