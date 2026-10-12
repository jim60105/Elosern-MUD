/*
 * party panel v2 mirror: slots, panel shapes, rejections.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { VALID_EPOCH, serverTime } = require("./protocol_support.js");


function validPartySlot(overrides) {
  return Object.assign(
    {
      identity: 41,
      display_name: "守衛長薇拉",
      portrait_ref: null,
      hp_current: 180,
      hp_maximum: 220,
      bond_stage: "摯友",
      membership: { general: true, temporary_commissions: [] },
    },
    overrides || {}
  );
}

function validPartyPanel(slots) {
  const rows = slots || [validPartySlot()];
  const used = rows.filter(
    (slot) => slot && slot.membership && slot.membership.general === true
  ).length;
  return {
    schema_version: 2,
    available: true,
    general_quota: { used: used, limit: Protocol.PARTY_GENERAL_LIMIT },
    slots: rows,
  };
}

test("party available form validates and empty slots is legal", () => {
  assert.deepEqual(Protocol.validatePartyPanel(validPartyPanel()), validPartyPanel());
  assert.deepEqual(Protocol.validatePartyPanel(validPartyPanel([])), {
    schema_version: 2,
    available: true,
    general_quota: { used: 0, limit: Protocol.PARTY_GENERAL_LIMIT },
    slots: [],
  });
  // Paired astral code points are legal text on both mirrors.
  assert.doesNotThrow(() =>
    Protocol.validatePartyPanel(validPartyPanel([validPartySlot({ display_name: "薇拉\u{1F600}" })]))
  );
  for (const portrait_ref of ["42", "1".repeat(32)]) {
    const panel = validPartyPanel([validPartySlot({ portrait_ref })]);
    assert.deepEqual(Protocol.validatePartyPanel(panel), panel);
  }
});

test("party validator mirrors the server drift rejections", () => {
  for (const bad of [
    // prototype-named own keys from JSON.parse must read as unknown fields
    validPartyPanel([
      JSON.parse(
        '{"identity":41,"display_name":"a","portrait_ref":null,"hp_current":1,"hp_maximum":1,"bond_stage":"友","__proto__":{}}'
      ),
    ]),
    validPartyPanel([
      JSON.parse(
        '{"identity":41,"display_name":"a","portrait_ref":null,"hp_current":1,"hp_maximum":1,"bond_stage":"友","constructor":1}'
      ),
    ]),
    // over the envelope slot bound (the old four-row cap is gone; temporary
    // rows beyond the general quota are legal)
    validPartyPanel(
      Array.from({ length: Protocol.PARTY_MAX_SLOTS + 1 }, (_, index) =>
        validPartySlot({
          identity: index + 1,
          membership: { general: false, temporary_commissions: [] },
        })
      )
    ),
    // missing row keys
    validPartyPanel([
      { identity: 1, display_name: "a", portrait_ref: null, hp_current: 0, hp_maximum: 0 },
    ]),
    // malformed membership and quota
    validPartyPanel([validPartySlot({ membership: [] })]),
    validPartyPanel([
      validPartySlot({ membership: { general: 1, temporary_commissions: [] } }),
    ]),
    validPartyPanel([
      validPartySlot({
        membership: {
          general: false,
          temporary_commissions: [{ quest_id: "q", role_id: "r", label: "l", x: 1 }],
        },
      }),
    ]),
    {
      schema_version: 2,
      available: true,
      slots: [],
    },
    {
      schema_version: 2,
      available: true,
      general_quota: { used: 5, limit: 4 },
      slots: [],
    },
    // unknown row key (a token field must never ride the party row)
    validPartyPanel([{ ...validPartySlot(), token: "a1" }]),
    // numeric bond_stage (raw affinity can never reach the wire)
    validPartyPanel([validPartySlot({ bond_stage: 3 })]),
    validPartyPanel([validPartySlot({ bond_stage: "" })]),
    // negative HP bound
    validPartyPanel([validPartySlot({ hp_current: -1 })]),
    // over-bound display name
    validPartyPanel([
      validPartySlot({ display_name: "同".repeat(Protocol.PARTY_MAX_DISPLAY_NAME + 1) }),
    ]),
    ...[42, "4a", "", "４２", "1".repeat(33)].map(
      (portrait_ref) => validPartyPanel([validPartySlot({ portrait_ref })]),
    ),
    // duplicate identities
    validPartyPanel([validPartySlot({ identity: 7 }), validPartySlot({ identity: 7 })]),
    // unpaired surrogate halves are not valid JSON text (server parity)
    validPartyPanel([validPartySlot({ display_name: "\uD800" })]),
    validPartyPanel([validPartySlot({ display_name: "\uDC00a" })]),
    validPartyPanel([validPartySlot({ bond_stage: "\uD83D\uD83D" })]),
    // version drift
    { schema_version: 1, available: true, slots: [] },
    // availability and container drift
    { schema_version: 2, available: "yes", slots: [] },
    { schema_version: 2, available: false, slots: [] },
    { schema_version: 2, available: true, slots: {} },
  ]) {
    assert.throws(() => Protocol.validatePartyPanel(bad));
  }
});

test("party is in the production panel allowlist and rejects atomically", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.party, 2);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 5,
    mode: "exploration",
    panels: {
      party: validPartyPanel([{ ...validPartySlot(), bond_stage: 9 }]),
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
      schema_version: 2,
      available: false,
      reason: { code: "party_unavailable", message: "隊伍資訊目前無法顯示" },
    },
  };
  envelope.revision = 7;
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
});

