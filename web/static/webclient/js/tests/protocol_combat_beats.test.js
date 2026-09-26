/*
 * combat_beats panel v1 mirror: the exact available form, the closed kind set,
 * contiguous seq, non-decreasing action, the damage invariants, the identity
 * shape, the byte budget, and snapshot integration.
 *
 * All fixtures are synthetic: invented keys, invented prose.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { VALID_EPOCH, serverTime } = require("./protocol_support.js");

const HERO_REF = "101";
const FOE_REF = "202";
const ROUND_ID = "hostile:5:9/1";

function beat(overrides) {
  return Object.assign(
    {
      seq: 0,
      action: 0,
      kind: "other",
      actor: HERO_REF,
      target: null,
      amount: null,
      hp_after: null,
      text: "合成行動。",
    },
    overrides || {}
  );
}

function rollBeat(overrides) {
  return beat(
    Object.assign({ kind: "roll", target: FOE_REF, text: "合成擲骰。" }, overrides || {})
  );
}

function damageBeat(overrides) {
  return beat(
    Object.assign(
      {
        seq: 1,
        kind: "damage",
        target: FOE_REF,
        amount: 12,
        hp_after: 18,
        text: "合成傷害。",
      },
      overrides || {}
    )
  );
}

function validPanel(overrides) {
  return Object.assign(
    {
      schema_version: 1,
      available: true,
      round: ROUND_ID,
      beats: [rollBeat(), damageBeat()],
    },
    overrides || {}
  );
}

function unavailablePanel() {
  return {
    schema_version: 1,
    available: false,
    reason: {
      code: "presentation_unavailable",
      message: "目前無法顯示此介面",
    },
  };
}

function snapshotWith(panel) {
  return {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 4,
    mode: "exploration",
    panels: { combat_beats: panel },
    layout_version: 1,
    server_time: serverTime(),
  };
}

test("combat_beats available and empty-beats forms validate", () => {
  assert.deepEqual(Protocol.validateCombatBeatsPanel(validPanel()), validPanel());
  assert.deepEqual(
    Protocol.validateCombatBeatsPanel(validPanel({ beats: [] })),
    validPanel({ beats: [] })
  );
  assert.equal(Protocol.PANEL_ALLOWLIST.combat_beats, 1);
  assert.deepEqual(Protocol.COMBAT_BEATS_KINDS, [
    "roll",
    "damage",
    "target_defeated",
    "other",
  ]);
  assert.equal(Protocol.COMBAT_BEATS_SCHEMA_VERSION, 1);
});

test("combat_beats unavailable form validates through the panel dispatch", () => {
  assert.deepEqual(
    Protocol.validatePanel("combat_beats", 1, unavailablePanel()),
    unavailablePanel()
  );
});

test("combat_beats validator mirrors the server drift rejections", () => {
  const cases = [
    validPanel({ beats: [beat({ kind: "skill" })] }),
    validPanel({ beats: [beat({ extra: 1 })] }),
    validPanel({ beats: [beat({ seq: 3 })] }),
    validPanel({ beats: [rollBeat(), damageBeat({ hp_after: null })] }),
    validPanel({ beats: [rollBeat(), damageBeat({ amount: null })] }),
    validPanel({ beats: [rollBeat(), damageBeat({ target: null })] }),
    validPanel({ beats: [rollBeat({ amount: 3 })] }),
    validPanel({ beats: [rollBeat({ hp_after: 3 })] }),
    validPanel({ beats: [beat({ actor: "hero" })] }),
    validPanel({ beats: [beat({ actor: "1".repeat(33) })] }),
    validPanel({ beats: [rollBeat({ action: 1 }), damageBeat({ action: 0 })] }),
    validPanel({ beats: [damageBeat({ amount: -1 })] }),
    validPanel({ beats: [beat({ amount: 1.5 })] }),
    validPanel({ beats: [beat()].concat(new Array(64).fill(beat())) }),
    validPanel({ extra: 1 }),
    validPanel({ available: false }),
    validPanel({ schema_version: 2 }),
    validPanel({ round: " " }),
    validPanel({ round: "s".repeat(161) }),
    validPanel({ round: 4 }),
    validPanel({ beats: {} }),
  ];
  for (const bad of cases) {
    assert.throws(
      () => Protocol.validateCombatBeatsPanel(bad),
      undefined,
      JSON.stringify(bad).slice(0, 120)
    );
  }
});

test("combat_beats counts astral text by code point and enforces its byte budget", () => {
  const astral = "\u{10348}";
  assert.doesNotThrow(() =>
    Protocol.validateCombatBeatsPanel(
      validPanel({ beats: [beat({ text: astral.repeat(256) })] })
    )
  );
  assert.throws(() =>
    Protocol.validateCombatBeatsPanel(
      validPanel({ beats: [beat({ text: astral.repeat(257) })] })
    )
  );
  const bulky = validPanel({
    beats: Array.from({ length: 64 }, (unused, index) =>
      beat({ seq: index, text: "字".repeat(256) })
    ),
  });
  assert.throws(() => Protocol.validateCombatBeatsPanel(bulky));
});

test("a snapshot carrying combat_beats passes and a bad beat rejects it", () => {
  assert.doesNotThrow(() => Protocol.validateSnapshot(snapshotWith(validPanel())));
  assert.doesNotThrow(() =>
    Protocol.validateSnapshot(snapshotWith(unavailablePanel()))
  );
  assert.throws(() =>
    Protocol.validateSnapshot(
      snapshotWith(validPanel({ beats: [beat({ kind: "skill" })] }))
    )
  );
  assert.throws(() =>
    Protocol.validateSnapshot(
      snapshotWith(validPanel({ beats: [rollBeat(), damageBeat({ seq: 7 })] }))
    )
  );
});
