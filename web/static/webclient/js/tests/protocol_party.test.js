/*
 * party panel v1 mirror: slots, panel shapes, rejections.
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
    },
    overrides || {}
  );
}

function validPartyPanel(slots) {
  return { schema_version: 1, available: true, slots: slots || [validPartySlot()] };
}

test("party available form validates and empty slots is legal", () => {
  assert.deepEqual(Protocol.validatePartyPanel(validPartyPanel()), validPartyPanel());
  assert.deepEqual(Protocol.validatePartyPanel(validPartyPanel([])), {
    schema_version: 1,
    available: true,
    slots: [],
  });
  // Paired astral code points are legal text on both mirrors.
  assert.doesNotThrow(() =>
    Protocol.validatePartyPanel(validPartyPanel([validPartySlot({ display_name: "薇拉\u{1F600}" })]))
  );
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
    // fifth row
    validPartyPanel([
      validPartySlot({ identity: 1 }),
      validPartySlot({ identity: 2 }),
      validPartySlot({ identity: 3 }),
      validPartySlot({ identity: 4 }),
      validPartySlot({ identity: 5 }),
    ]),
    // missing row keys
    validPartyPanel([
      { identity: 1, display_name: "a", portrait_ref: null, hp_current: 0, hp_maximum: 0 },
    ]),
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
    // portrait_ref must stay null at version 1
    validPartyPanel([validPartySlot({ portrait_ref: "42" })]),
    // duplicate identities
    validPartyPanel([validPartySlot({ identity: 7 }), validPartySlot({ identity: 7 })]),
    // unpaired surrogate halves are not valid JSON text (server parity)
    validPartyPanel([validPartySlot({ display_name: "\uD800" })]),
    validPartyPanel([validPartySlot({ display_name: "\uDC00a" })]),
    validPartyPanel([validPartySlot({ bond_stage: "\uD83D\uD83D" })]),
    // version drift
    { schema_version: 2, available: true, slots: [] },
    // availability and container drift
    { schema_version: 1, available: "yes", slots: [] },
    { schema_version: 1, available: false, slots: [] },
    { schema_version: 1, available: true, slots: {} },
  ]) {
    assert.throws(() => Protocol.validatePartyPanel(bad));
  }
});

test("party is in the production panel allowlist and rejects atomically", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.party, 1);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 5,
    mode: "exploration",
    panels: {
      party: { schema_version: 1, available: true, slots: [{ ...validPartySlot(), bond_stage: 9 }] },
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
      schema_version: 1,
      available: false,
      reason: { code: "party_unavailable", message: "隊伍資訊目前無法顯示" },
    },
  };
  envelope.revision = 7;
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
});

