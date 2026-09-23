/*
 * title_codex, objectives, and quest-log panel v1 mirrors: rows, panels, rejections.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { T_GUILD_NAME, T_TITLE_DISPLAY, T_TITLE_IDENT, VALID_EPOCH, serverTime } = require("./protocol_support.js");


function validTitleCodexFixedRow(overrides) {
  return Object.assign(
    {
      key: T_TITLE_IDENT,
      display: T_TITLE_DISPLAY,
      category: "guild",
      hint: "",
      flavor: "公會註冊的起點。",
      unlocked: true,
      granted_tick: 120,
    },
    overrides || {}
  );
}

function validTitleCodexEpithetRow(overrides) {
  return Object.assign(
    {
      display: "南門新客",
      basis: "初入南門。",
      granted_tick: 121,
      equipped: true,
      can_remove: false,
    },
    overrides || {}
  );
}

function validTitleCodexPanel(overrides) {
  return Object.assign(
    {
      schema_version: 1,
      available: true,
      kind: "title_codex",
      fixed_rows: [validTitleCodexFixedRow()],
      epithet_rows: [validTitleCodexEpithetRow()],
      equipped: { fixed: T_TITLE_IDENT, epithet: "南門新客" },
      full_title: "F級冒險者　南門新客",
      unlocked: 1,
      total: 7,
      pending_ballot: [],
    },
    overrides || {}
  );
}

test("title_codex pins its mirrored bounds and validates the minimal payload", () => {
  assert.equal(Protocol.TITLE_CODEX_MAX_ROWS, 50);
  assert.equal(Protocol.TITLE_CODEX_MAX_DISPLAY, 64);
  assert.equal(Protocol.TITLE_CODEX_MAX_BASIS, 160);
  assert.equal(Protocol.TITLE_CODEX_MAX_FULL_TITLE, 128);
  assert.equal(Protocol.TITLE_CODEX_MAX_BALLOT, 3);
  assert.equal(Protocol.TITLE_CODEX_BASIS_WIRE_MAX, 80);
  assert.deepEqual(Protocol.TITLE_CODEX_CATEGORIES, [
    "combat",
    "spell",
    "explore",
    "guild",
    "clergy",
    "romance",
  ]);
  const normalized = Protocol.validatePanel(
    "title_codex",
    Protocol.PANEL_ALLOWLIST.title_codex,
    validTitleCodexPanel()
  );
  assert.equal(normalized.kind, "title_codex");
  assert.equal(normalized.epithet_rows[0].display, "南門新客");
});

test("title_codex rejects wrong kind, version, and discriminator", () => {
  assert.throws(() =>
    Protocol.validateTitleCodexPanel(validTitleCodexPanel({ kind: "lineage" }))
  );
  assert.throws(() =>
    Protocol.validateTitleCodexPanel(validTitleCodexPanel({ schema_version: 2 }))
  );
  assert.throws(() =>
    Protocol.validateTitleCodexPanel(validTitleCodexPanel({ available: false }))
  );
  assert.throws(() =>
    Protocol.validateTitleCodexPanel(validTitleCodexPanel({ extra: 1 }))
  );
});

test("title_codex enforces the hint/flavor exclusivity and category closed set", () => {
  assert.throws(() =>
    Protocol.validateTitleCodexPanel(
      validTitleCodexPanel({
        fixed_rows: [validTitleCodexFixedRow({ unlocked: true, hint: "解鎖提示" })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateTitleCodexPanel(
      validTitleCodexPanel({
        fixed_rows: [
          validTitleCodexFixedRow({ unlocked: false, hint: "解鎖提示", flavor: "風味" }),
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateTitleCodexPanel(
      validTitleCodexPanel({
        fixed_rows: [validTitleCodexFixedRow({ category: "commerce" })],
      })
    )
  );
  assert.doesNotThrow(() =>
    Protocol.validateTitleCodexPanel(
      validTitleCodexPanel({
        fixed_rows: [validTitleCodexFixedRow({ category: "clergy" })],
      })
    )
  );
  // A locked row carrying only its hint is the legitimate form.
  assert.doesNotThrow(() =>
    Protocol.validateTitleCodexPanel(
      validTitleCodexPanel({
        fixed_rows: [
          validTitleCodexFixedRow({
            unlocked: false,
            hint: "完成公會註冊",
            flavor: "",
            granted_tick: 0,
          }),
        ],
      })
    )
  );
});

test("title_codex caps row counts and string bounds", () => {
  const rows = [];
  for (let i = 0; i <= Protocol.TITLE_CODEX_MAX_ROWS; i++) {
    rows.push(validTitleCodexEpithetRow({ display: `異名${i}` }));
  }
  assert.throws(() =>
    Protocol.validateTitleCodexPanel(validTitleCodexPanel({ epithet_rows: rows }))
  );
  assert.doesNotThrow(() =>
    Protocol.validateTitleCodexPanel(
      validTitleCodexPanel({ epithet_rows: rows.slice(1) })
    )
  );
  const displayCap = "長".repeat(Protocol.TITLE_CODEX_MAX_DISPLAY);
  const basisCap = "援".repeat(Protocol.TITLE_CODEX_MAX_BASIS);
  assert.doesNotThrow(() =>
    Protocol.validateTitleCodexPanel(
      validTitleCodexPanel({
        full_title: "銜".repeat(Protocol.TITLE_CODEX_MAX_FULL_TITLE),
        epithet_rows: [
          validTitleCodexEpithetRow({ display: displayCap, basis: basisCap }),
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateTitleCodexPanel(
      validTitleCodexPanel({
        epithet_rows: [
          validTitleCodexEpithetRow({
            display: "長".repeat(Protocol.TITLE_CODEX_MAX_DISPLAY + 1),
          }),
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateTitleCodexPanel(
      validTitleCodexPanel({
        epithet_rows: [
          validTitleCodexEpithetRow({
            basis: "援".repeat(Protocol.TITLE_CODEX_MAX_BASIS + 1),
          }),
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateTitleCodexPanel(
      validTitleCodexPanel({
        full_title: "銜".repeat(Protocol.TITLE_CODEX_MAX_FULL_TITLE + 1),
      })
    )
  );
});

test("title_codex requires counters, equipped slots, and ballot shape", () => {
  assert.throws(() =>
    Protocol.validateTitleCodexPanel(validTitleCodexPanel({ unlocked: 8 }))
  );
  assert.throws(() =>
    Protocol.validateTitleCodexPanel(
      validTitleCodexPanel({
        equipped: { fixed: "BAD KEY", epithet: "南門新客" },
      })
    )
  );
  assert.throws(() =>
    Protocol.validateTitleCodexPanel(
      validTitleCodexPanel({ equipped: { fixed: null, epithet: "" } })
    )
  );
  assert.doesNotThrow(() =>
    Protocol.validateTitleCodexPanel(
      validTitleCodexPanel({ equipped: { fixed: null, epithet: null } })
    )
  );
  assert.throws(() =>
    Protocol.validateTitleCodexPanel(
      validTitleCodexPanel({
        pending_ballot: [{ display: "破城先鋒", basis: "率先破門。", index: 1 }],
      })
    )
  );
  assert.doesNotThrow(() =>
    Protocol.validateTitleCodexPanel(
      validTitleCodexPanel({
        pending_ballot: [{ display: "破城先鋒", basis: "率先破門。" }],
      })
    )
  );
});

test("title_codex is in the production panel allowlist and a bad panel rejects atomically", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.title_codex, 1);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 7,
    mode: "exploration",
    panels: {
      title_codex: { ...validTitleCodexPanel(), unlocked: 9, total: 1 },
    },
    layout_version: 1,
    server_time: serverTime(),
  };
  assert.throws(() => Protocol.validateSnapshot(envelope));
  envelope.panels.title_codex = validTitleCodexPanel();
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
  envelope.revision = 8;
  assert.doesNotThrow(() => Protocol.validateUpdate(envelope));
});

test("title_codex unavailable form validates through the common discriminator", () => {
  const unavailable = {
    schema_version: 1,
    available: false,
    reason: { code: "codex_unavailable", message: "稱號冊目前無法顯示" },
  };
  assert.deepEqual(
    Protocol.validatePanel("title_codex", Protocol.PANEL_ALLOWLIST.title_codex, unavailable),
    unavailable
  );
});

function validObjectivesRow(overrides) {
  return Object.assign(
    {
      quest_id: "introductory_hunt:1",
      display_name: "討伐低階魔物",
      objective_line: "討伐 1 隻低階魔物",
      stage_index: 0,
      stage_total: 1,
      stage_progress: 0,
      objective_quantity: 1,
      reward_copper: 50,
      deadline_line: "期限：剩餘 72 小時",
    },
    overrides || {}
  );
}

function validObjectivesPanel(rows) {
  return { schema_version: 1, available: true, rows: rows || [validObjectivesRow()] };
}

test("objectives available form validates and empty rows is legal", () => {
  assert.deepEqual(Protocol.validateObjectivesPanel(validObjectivesPanel()), validObjectivesPanel());
  assert.deepEqual(Protocol.validateObjectivesPanel(validObjectivesPanel([])), {
    schema_version: 1,
    available: true,
    rows: [],
  });
  // null reward and null deadline are legal
  assert.doesNotThrow(() =>
    Protocol.validateObjectivesPanel(
      validObjectivesPanel([validObjectivesRow({ reward_copper: null, deadline_line: null })])
    )
  );
});

test("objectives validator mirrors the server drift rejections", () => {
  for (const bad of [
    // prototype pollution
    validObjectivesPanel([
      JSON.parse(
        '{"quest_id":"q:1","display_name":"a","objective_line":"b","stage_index":0,"stage_total":1,"stage_progress":0,"objective_quantity":1,"reward_copper":null,"deadline_line":null,"__proto__":{}}'
      ),
    ]),
    // fourth row rejected (at most 3)
    validObjectivesPanel([
      validObjectivesRow({ quest_id: "q:1" }),
      validObjectivesRow({ quest_id: "q:2" }),
      validObjectivesRow({ quest_id: "q:3" }),
      validObjectivesRow({ quest_id: "q:4" }),
    ]),
    // missing row key
    validObjectivesPanel([
      {
        quest_id: "q:1",
        display_name: "a",
        objective_line: "b",
        stage_index: 0,
        stage_total: 1,
        stage_progress: 0,
        objective_quantity: 1,
        reward_copper: null,
      },
    ]),
    // unknown row key
    validObjectivesPanel([Object.assign(validObjectivesRow(), { extra: 1 })]),
    // duplicate quest IDs
    validObjectivesPanel([
      validObjectivesRow({ quest_id: "q:1" }),
      validObjectivesRow({ quest_id: "q:1" }),
    ]),
    // negative or non-int progress / quantity
    validObjectivesPanel([validObjectivesRow({ stage_progress: -1 })]),
    validObjectivesPanel([validObjectivesRow({ stage_progress: "0" })]),
    validObjectivesPanel([validObjectivesRow({ objective_quantity: 0 })]),
    validObjectivesPanel([validObjectivesRow({ reward_copper: -1 })]),
    validObjectivesPanel([validObjectivesRow({ reward_copper: "10" })]),
    // empty or blank strings
    validObjectivesPanel([validObjectivesRow({ quest_id: "" })]),
    validObjectivesPanel([validObjectivesRow({ display_name: "   " })]),
    validObjectivesPanel([validObjectivesRow({ objective_line: "" })]),
    validObjectivesPanel([validObjectivesRow({ deadline_line: "   " })]),
    // version drift
    { schema_version: 2, available: true, rows: [] },
    // non-bool available
    { schema_version: 1, available: "yes", rows: [] },
    { schema_version: 1, available: false, rows: [] },
  ]) {
    assert.throws(() => Protocol.validateObjectivesPanel(bad));
  }
});

test("objectives is in the production panel allowlist and rejects atomically", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.objectives, 1);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 5,
    mode: "exploration",
    panels: {
      objectives: { schema_version: 1, available: true, rows: "not-a-list" },
    },
    layout_version: 1,
    server_time: serverTime(),
  };
  assert.throws(() => Protocol.validateSnapshot(envelope));
  envelope.panels = { objectives: validObjectivesPanel() };
  envelope.revision = 6;
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
  envelope.panels = {
    objectives: {
      schema_version: 1,
      available: false,
      reason: { code: "presentation_unavailable", message: "目前無法顯示此介面" },
    },
  };
  envelope.revision = 7;
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
});

function validQuestLogRow(overrides) {
  return Object.assign(
    {
      quest_id: "introductory_hunt:1",
      definition_key: "introductory_hunt",
      display_name: "討伐低階魔物",
      state: "in_progress",
      stage_index: 0,
      stage_total: 1,
      stage_progress: 0,
      objective_quantity: 1,
      objective_line: "討伐 1 隻低階魔物",
      deadline_line: "期限：剩餘 72 小時",
      detail: "討伐低階魔物\n狀態：進行中\n階段：1",
      tracked: false,
      issuer: {
        kind: "guild",
        key: "guild:guild_branch_altoria",
        label: T_GUILD_NAME,
      },
      settlement: "counter",
      reward_line: "獎勵：銅 50、功績 25",
      track: {
        action_id: "guild.quest_track",
        label: "追蹤",
        enabled: true,
        disabled_reason: null,
        quantity: null,
      },
    },
    overrides || {}
  );
}

function validQuestLogPanel(rows) {
  return { schema_version: 1, available: true, rows: rows || [validQuestLogRow()] };
}

test("quest_log available form validates, empty rows and null commission fields are legal", () => {
  assert.deepEqual(Protocol.validateQuestLogPanel(validQuestLogPanel()), validQuestLogPanel());
  const empty = Protocol.validateQuestLogPanel(validQuestLogPanel([]));
  assert.deepEqual(empty, { schema_version: 1, available: true, rows: [] });
  const unresolved = validQuestLogRow({ settlement: null, reward_line: null, deadline_line: null });
  assert.doesNotThrow(() => Protocol.validateQuestLogPanel(validQuestLogPanel([unresolved])));
});

test("quest_log validator mirrors the server drift rejections", () => {
  for (const bad of [
    // extra row field
    validQuestLogPanel([Object.assign(validQuestLogRow(), { extra: 1 })]),
    // thirteenth row
    validQuestLogPanel(
      Array.from({ length: 13 }, (_, i) => validQuestLogRow({ quest_id: `q:${i}` }))
    ),
    // unknown state
    validQuestLogPanel([validQuestLogRow({ state: "running" })]),
    // unknown settlement
    validQuestLogPanel([validQuestLogRow({ settlement: "later" })]),
    // issuer drift
    validQuestLogPanel([
      validQuestLogRow({ issuer: Object.assign(validQuestLogRow().issuer, { kind: "monster" }) }),
    ]),
    validQuestLogPanel([
      validQuestLogRow({ issuer: { kind: "npc", key: "npc:grey_granny" } }),
    ]),
    // malformed or kind-incoherent issuer keys
    validQuestLogPanel([
      validQuestLogRow({ issuer: Object.assign(validQuestLogRow().issuer, { key: "not-an-issuer" }) }),
    ]),
    validQuestLogPanel([
      validQuestLogRow({ issuer: Object.assign(validQuestLogRow().issuer, { key: "guild:a:b" }) }),
    ]),
    validQuestLogPanel([
      validQuestLogRow({ issuer: Object.assign(validQuestLogRow().issuer, { kind: "npc", key: "guild:guild_branch_altoria" }) }),
    ]),
    validQuestLogPanel([
      validQuestLogRow({ issuer: Object.assign(validQuestLogRow().issuer, { kind: "guild", key: "npc:grey_granny" }) }),
    ]),
    validQuestLogPanel([
      validQuestLogRow({ issuer: Object.assign(validQuestLogRow().issuer, { kind: "npc", key: "npc:#0" }) }),
    ]),
    // settlement and reward_line must be null together
    validQuestLogPanel([validQuestLogRow({ settlement: null })]),
    validQuestLogPanel([validQuestLogRow({ reward_line: null })]),
    // track descriptor drift
    validQuestLogPanel([
      validQuestLogRow({ track: Object.assign(validQuestLogRow().track, { action_id: "shop.buy" }) }),
    ]),
    validQuestLogPanel([
      validQuestLogRow({ track: Object.assign(validQuestLogRow().track, { enabled: false }) }),
    ]),
    validQuestLogPanel([
      validQuestLogRow({ track: Object.assign(validQuestLogRow().track, { quantity: { min: 1, max: 2 } }) }),
    ]),
    // duplicate quest IDs
    validQuestLogPanel([validQuestLogRow({ quest_id: "q:1" }), validQuestLogRow({ quest_id: "q:1" })]),
    // over-bound string
    validQuestLogPanel([validQuestLogRow({ detail: "字".repeat(513) })]),
    // lone surrogate
    validQuestLogPanel([validQuestLogRow({ display_name: "bad\ud800name" })]),
    // negative or non-int integers
    validQuestLogPanel([validQuestLogRow({ stage_progress: -1 })]),
    validQuestLogPanel([validQuestLogRow({ objective_quantity: 0 })]),
    // non-bool tracked
    validQuestLogPanel([validQuestLogRow({ tracked: "yes" })]),
    // version drift and non-bool available
    { schema_version: 2, available: true, rows: [] },
    { schema_version: 1, available: false, rows: [] },
  ]) {
    assert.throws(() => Protocol.validateQuestLogPanel(bad));
  }
});

test("quest_log is in the production panel allowlist and rejects atomically", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.quest_log, 1);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 5,
    mode: "exploration",
    panels: {
      quest_log: { schema_version: 1, available: true, rows: "not-a-list" },
    },
    layout_version: 1,
    server_time: serverTime(),
  };
  assert.throws(() => Protocol.validateSnapshot(envelope));
  envelope.panels = { quest_log: validQuestLogPanel() };
  envelope.revision = 6;
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
});

