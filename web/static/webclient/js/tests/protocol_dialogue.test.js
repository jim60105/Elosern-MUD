/*
 * dialogue panel v1 mirror: choices, panels, rejections.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { VALID_EPOCH, serverTime } = require("./protocol_support.js");


test("dialogue choice cap mirrors the panel-owned bound (align-11)", () => {
  assert.equal(Protocol.DIALOGUE_MAX_CHOICES, 4);
});

function validDialogueChoice(overrides) {
  return Object.assign({ keyword_id: "公會", label: "公會" }, overrides || {});
}

function validDialoguePanel(overrides) {
  return Object.assign(
    {
      schema_version: 1,
      available: true,
      kind: "dialogue",
      host: { identity: 41, display_name: "公會職員", portrait_ref: null },
      bond_stage: "熟人",
      line: "歡迎來到冒險者公會。",
      choices: [validDialogueChoice()],
    },
    overrides || {}
  );
}

test("dialogue available form validates and empty choices and null stage are legal", () => {
  assert.deepEqual(Protocol.validateDialoguePanel(validDialoguePanel()), validDialoguePanel());
  assert.equal(Protocol.validateDialoguePanel(validDialoguePanel({ choices: [] })).choices.length, 0);
  assert.equal(Protocol.validateDialoguePanel(validDialoguePanel({ bond_stage: null })).bond_stage, null);
  // Paired astral code points are legal text on both mirrors.
  assert.doesNotThrow(() =>
    Protocol.validateDialoguePanel(validDialoguePanel({ line: "歡迎\u{1F600}。" }))
  );
});

test("dialogue validator mirrors the server drift rejections", () => {
  for (const bad of [
    // prototype-named own keys from JSON.parse must read as unknown fields
    JSON.parse(
      '{"schema_version":1,"available":true,"kind":"dialogue","host":{"identity":41,"display_name":"a","portrait_ref":null},"bond_stage":"友","line":"嗯","choices":[],"__proto__":{}}'
    ),
    validDialoguePanel({ extra: 1 }),
    (() => {
      const missing = validDialoguePanel();
      delete missing.choices;
      return missing;
    })(),
    validDialoguePanel({ schema_version: 2 }),
    // the unavailable form belongs to the registry, not this validator
    { schema_version: 1, available: false },
    validDialoguePanel({ available: false }),
    validDialoguePanel({ kind: "party" }),
    // host vocabulary drift
    validDialoguePanel({ host: { identity: 41, display_name: "a", portrait_ref: "42" } }),
    validDialoguePanel({ host: { identity: 0, display_name: "a", portrait_ref: null } }),
    validDialoguePanel({ host: { identity: 41, display_name: "  ", portrait_ref: null } }),
    validDialoguePanel({
      host: { identity: 41, display_name: "同".repeat(129), portrait_ref: null },
    }),
    // numeric bond_stage can never reach the wire
    validDialoguePanel({ bond_stage: 3 }),
    validDialoguePanel({ bond_stage: "" }),
    // line bounds and orphan surrogates
    validDialoguePanel({ line: "" }),
    validDialoguePanel({ line: "言".repeat(2001) }),
    validDialoguePanel({ line: "\ud800壞" }),
    // choice cap and uniqueness
    validDialoguePanel({ choices: Array.from({ length: Protocol.DIALOGUE_MAX_CHOICES + 1 }, (_, i) => validDialogueChoice({ keyword_id: "詞" + i, label: "詞" + i })) }),
    validDialoguePanel({ choices: [validDialogueChoice(), validDialogueChoice()] }),
    validDialoguePanel({ choices: [validDialogueChoice({ keyword_id: " " })] }),
    // a literal __proto__ keyword pair must hit the duplicate check: the
    // registry is prototype-null so the first row is an own property
    validDialoguePanel({
      choices: [
        validDialogueChoice({ keyword_id: "__proto__" }),
        validDialogueChoice({ keyword_id: "__proto__" }),
      ],
    }),
    validDialoguePanel({ choices: [validDialogueChoice({ keyword_id: "\ud800" })] }),
    validDialoguePanel({ choices: [{ keyword_id: "公會" }] }),
    validDialoguePanel({ choices: [{ keyword_id: "公會", label: "公會", extra: 1 }] }),
    validDialoguePanel({ choices: [{ keyword_id: "公會", label: "說".repeat(129) }] }),
  ]) {
    assert.throws(() => Protocol.validateDialoguePanel(bad));
  }
});

test("dialogue is in the production panel allowlist with dialogue mode accepted", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.dialogue, 1);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 5,
    mode: "dialogue",
    panels: {
      dialogue: { schema_version: 1, available: true, kind: "dialogue" },
    },
    layout_version: 1,
    server_time: serverTime(),
  };
  assert.throws(() => Protocol.validateSnapshot(envelope));
  envelope.panels = { dialogue: validDialoguePanel() };
  envelope.revision = 6;
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
  envelope.panels = {
    dialogue: {
      schema_version: 1,
      available: false,
      reason: { code: "dialogue_unavailable", message: "對話目前無法顯示" },
    },
  };
  envelope.revision = 7;
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
});

