/*
 * party panel v3 mirror: commander row 0, companion rows, panel shapes,
 * rejections.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { VALID_EPOCH, serverTime } = require("./protocol_support.js");


function validCommanderSlot(overrides) {
  return Object.assign(
    {
      identity: 1,
      display_name: "影行者",
      portrait_ref: null,
      hp_current: 80,
      hp_maximum: 100,
      mp_current: 30,
      mp_maximum: 50,
      sp_current: 12,
      sp_maximum: 40,
      role: "commander",
      knocked_out: false,
      unread: false,
      bond_stage: null,
      membership: null,
    },
    overrides || {}
  );
}

function validCompanionSlot(overrides) {
  return Object.assign(
    {
      identity: 41,
      display_name: "守衛長薇拉",
      portrait_ref: null,
      hp_current: 180,
      hp_maximum: 220,
      mp_current: 60,
      mp_maximum: 80,
      sp_current: 24,
      sp_maximum: 40,
      role: "companion",
      knocked_out: false,
      unread: false,
      bond_stage: "摯友",
      membership: { general: true, temporary_commissions: [] },
    },
    overrides || {}
  );
}

function validPartyPanel(slots, viewedMemberId) {
  const rows = slots || [validCommanderSlot()];
  const used = rows.filter(
    (slot) => slot && slot.membership && slot.membership.general === true
  ).length;
  return {
    schema_version: 3,
    available: true,
    general_quota: { used: used, limit: Protocol.PARTY_GENERAL_LIMIT },
    viewed_member_id:
      viewedMemberId === undefined
        ? rows.length > 0 && rows[0].identity !== undefined
          ? rows[0].identity
          : 1
        : viewedMemberId,
    slots: rows,
  };
}

test("party available form validates; the commander row alone is legal", () => {
  assert.deepEqual(Protocol.validatePartyPanel(validPartyPanel()), validPartyPanel());
  const commanderOnly = validPartyPanel([validCommanderSlot()]);
  assert.deepEqual(Protocol.validatePartyPanel(commanderOnly), commanderOnly);
  assert.deepEqual(Protocol.validatePartyPanel(commanderOnly).slots.length, 1);
  // Paired astral code points are legal text on both mirrors.
  assert.doesNotThrow(() =>
    Protocol.validatePartyPanel(
      validPartyPanel([validCommanderSlot(), validCompanionSlot({ display_name: "薇拉\u{1F600}" })])
    )
  );
  for (const portrait_ref of ["42", "1".repeat(32)]) {
    const panel = validPartyPanel([validCommanderSlot(), validCompanionSlot({ portrait_ref })]);
    assert.deepEqual(Protocol.validatePartyPanel(panel), panel);
  }
  // Bounds only: zero gauges and current greater than maximum are trait truth.
  assert.doesNotThrow(() =>
    Protocol.validatePartyPanel(
      validPartyPanel([
        validCommanderSlot({ hp_current: 0, mp_current: 0, sp_current: 0 }),
        validCompanionSlot({ hp_current: 500, hp_maximum: 1 }),
      ])
    )
  );
  // The two session flags are independent booleans on a companion row.
  const flagged = validPartyPanel([
    validCommanderSlot(),
    validCompanionSlot({ knocked_out: true, unread: true }),
  ]);
  assert.deepEqual(Protocol.validatePartyPanel(flagged), flagged);
});

test("the maximal row count is the commander plus every companion slot", () => {
  const rows = [validCommanderSlot()];
  for (let index = 0; index < Protocol.PARTY_MAX_SLOTS; index++) {
    rows.push(
      validCompanionSlot({
        identity: 100 + index,
        membership: { general: false, temporary_commissions: [] },
      })
    );
  }
  const maximal = validPartyPanel(rows, 1);
  assert.equal(Protocol.validatePartyPanel(maximal).slots.length, Protocol.PARTY_MAX_ROWS);
  assert.equal(Protocol.PARTY_MAX_ROWS, Protocol.PARTY_MAX_SLOTS + 1);
});

test("party validator mirrors the server drift rejections", () => {
  const full = (overrides) => validCompanionSlot(overrides);
  for (const bad of [
    // prototype-named own keys from JSON.parse must read as unknown fields
    validPartyPanel([
      validCommanderSlot(),
      JSON.parse(
        '{"identity":41,"display_name":"a","portrait_ref":null,"hp_current":1,"hp_maximum":1,' +
          '"mp_current":0,"mp_maximum":0,"sp_current":0,"sp_maximum":0,"role":"companion",' +
          '"knocked_out":false,"unread":false,"bond_stage":"友",' +
          '"membership":{"general":true,"temporary_commissions":[]},"__proto__":{}}'
      ),
    ]),
    validPartyPanel([validCommanderSlot(), { ...full(), constructor: 1 }]),
    // over the envelope row bound
    validPartyPanel(
      [
        validCommanderSlot(),
        ...Array.from({ length: Protocol.PARTY_MAX_SLOTS + 1 }, (_, index) =>
          full({ identity: index + 1, membership: { general: false, temporary_commissions: [] } })
        ),
      ],
      1
    ),
    // missing row keys
    validPartyPanel([validCommanderSlot(), { identity: 2, display_name: "a", role: "companion" }]),
    // no commander row at all
    validPartyPanel([full()]),
    // two commander rows
    validPartyPanel([validCommanderSlot(), validCommanderSlot({ identity: 2 })]),
    // commander row not first
    validPartyPanel([full(), validCommanderSlot()], 1),
    // the commander row carries no bond stage, membership, or knockout
    validPartyPanel([validCommanderSlot({ bond_stage: "摯友" })]),
    validPartyPanel([validCommanderSlot({ membership: { general: true, temporary_commissions: [] } })]),
    validPartyPanel([validCommanderSlot({ knocked_out: true })]),
    // an unknown role
    validPartyPanel([validCommanderSlot(), full({ role: "ally" })]),
    // malformed membership and quota
    validPartyPanel([validCommanderSlot(), full({ membership: [] })]),
    validPartyPanel([validCommanderSlot(), full({ membership: { general: 1, temporary_commissions: [] } })]),
    validPartyPanel([
      validCommanderSlot(),
      full({
        membership: {
          general: false,
          temporary_commissions: [{ quest_id: "q", role_id: "r", label: "l", x: 1 }],
        },
      }),
    ]),
    { schema_version: 3, available: true, slots: [validCommanderSlot()] },
    {
      schema_version: 3,
      available: true,
      general_quota: { used: 5, limit: 4 },
      viewed_member_id: 1,
      slots: [validCommanderSlot()],
    },
    // viewed_member_id must name a presented row
    validPartyPanel([validCommanderSlot(), full()], 99),
    validPartyPanel([validCommanderSlot(), full()], 0),
    validPartyPanel([validCommanderSlot(), full()], true),
    // unknown row key (a token field must never ride the party row)
    validPartyPanel([validCommanderSlot(), { ...full(), token: "a1" }]),
    // numeric bond_stage (raw affinity can never reach the wire)
    validPartyPanel([validCommanderSlot(), full({ bond_stage: 3 })]),
    validPartyPanel([validCommanderSlot(), full({ bond_stage: "" })]),
    // gauge and flag type drift
    validPartyPanel([validCommanderSlot(), full({ hp_current: -1 })]),
    validPartyPanel([validCommanderSlot(), full({ mp_maximum: -1 })]),
    validPartyPanel([validCommanderSlot(), full({ sp_current: "3" })]),
    validPartyPanel([validCommanderSlot(), full({ knocked_out: "yes" })]),
    validPartyPanel([validCommanderSlot(), full({ unread: 1 })]),
    // over-bound display name
    validPartyPanel([
      validCommanderSlot(),
      full({ display_name: "同".repeat(Protocol.PARTY_MAX_DISPLAY_NAME + 1) }),
    ]),
    ...[42, "4a", "", "４２", "1".repeat(33)].map((portrait_ref) =>
      validPartyPanel([validCommanderSlot(), full({ portrait_ref })])
    ),
    // duplicate identities
    validPartyPanel([validCommanderSlot(), full({ identity: 7 }), full({ identity: 7 })]),
    // unpaired surrogate halves are not valid JSON text (server parity)
    validPartyPanel([validCommanderSlot(), full({ display_name: "\uD800" })]),
    validPartyPanel([validCommanderSlot(), full({ display_name: "\uDC00a" })]),
    validPartyPanel([validCommanderSlot(), full({ bond_stage: "\uD83D\uD83D" })]),
    // version drift
    { schema_version: 2, available: true, slots: [validCommanderSlot()] },
    // availability and container drift
    { schema_version: 3, available: "yes", slots: [validCommanderSlot()] },
    { schema_version: 3, available: false, slots: [validCommanderSlot()] },
    { schema_version: 3, available: true, slots: {} },
  ]) {
    assert.throws(() => Protocol.validatePartyPanel(bad));
  }
});

test("party is in the production panel allowlist and rejects atomically", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.party, 3);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 5,
    mode: "exploration",
    panels: {
      party: validPartyPanel([validCommanderSlot(), validCompanionSlot({ bond_stage: 9 })]),
    },
    layout_version: 1,
    server_time: serverTime(),
  };
  assert.throws(() => Protocol.validateSnapshot(envelope));
  envelope.panels = { party: validPartyPanel() };
  envelope.revision = 6;
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
  envelope.panels = {
    party: {
      schema_version: 3,
      available: false,
      reason: { code: "party_unavailable", message: "隊伍資訊目前無法顯示" },
    },
  };
  envelope.revision = 7;
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
});
