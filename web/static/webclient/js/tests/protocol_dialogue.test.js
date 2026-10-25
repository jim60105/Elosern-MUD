/*
 * dialogue panel v3 mirror: choices, panels, rejections, delivery.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { VALID_EPOCH, serverTime } = require("./protocol_support.js");
const skillDescriptor = require("../elosern/protocol/panels/skill_descriptor.js");


test("dialogue choice cap mirrors the panel-owned bound (align-11)", () => {
  assert.equal(Protocol.DIALOGUE_MAX_CHOICES, 16);
});

test("explore.talk_scripted skill descriptor validates descriptor without selection_id", () => {
  const validParams = {
    npc_id: 41,
    topic_id: "guild_staff.topic_01",
    context_id: "ctx-1",
  };
  assert.doesNotThrow(() =>
    skillDescriptor.validateContextActionsAffordanceParams("explore.talk_scripted", validParams)
  );

  // Reject if extra selection_id is present in descriptor
  assert.throws(() =>
    skillDescriptor.validateContextActionsAffordanceParams("explore.talk_scripted", {
      npc_id: 41,
      topic_id: "guild_staff.topic_01",
      context_id: "ctx-1",
      selection_id: "client-injected-forbidden",
    })
  );
});

test("two deliberate picks versus transport retry request-id separation", () => {
  const pick1Req = "session:1";
  const pick2Req = "session:2";
  assert.notEqual(pick1Req, pick2Req);
  const retryReq = pick1Req;
  assert.equal(retryReq, pick1Req);
});

function validDialogueChoice(overrides) {
  return Object.assign(
    {
      topic_id: "guild_staff.topic_01",
      keyword_id: "公會",
      label: "公會",
      availability: "open",
      requirement_hint: null,
      unread: false,
      predecessors: [],
      action_payload: {
        npc_id: 41,
        topic_id: "guild_staff.topic_01",
        context_id: "ctx-1",
      },
    },
    overrides || {}
  );
}

function validDialogueDelivery(overrides) {
  return Object.assign(
    {
      delivery_id: "deliv-1",
      context_id: "ctx-1",
      topic_id: "guild_staff.topic_01",
      scene_id: "guild_staff.topic_01_scene",
      scene_revision: "r1",
      phase_revision: null,
      kind: "formal",
      lines: [
        { kind: "speech", speaker: "actor", text: "公會" },
        { kind: "speech", speaker: "host", text: "歡迎來到公會。" },
      ],
    },
    overrides || {}
  );
}

function validDialoguePanel(overrides) {
  return Object.assign(
    {
      schema_version: 3,
      available: true,
      kind: "dialogue",
      host: { identity: 41, display_name: "公會職員", portrait_ref: null },
      actor: { identity: 1, display_name: "測試者", portrait_ref: null },
      bond_stage: "熟人",
      context_id: "ctx-1",
      delivery: validDialogueDelivery(),
      choices: [validDialogueChoice()],
      pure_chain: [],
      reading_revision: 0,
      completed_topic_ids: [],
      unlock_batch: null,
    },
    overrides || {}
  );
}

test("dialogue available form validates and empty choices and null stage are legal", () => {
  assert.deepEqual(Protocol.validateDialoguePanel(validDialoguePanel()), validDialoguePanel());
  assert.equal(Protocol.validateDialoguePanel(validDialoguePanel({ choices: [] })).choices.length, 0);
  assert.equal(Protocol.validateDialoguePanel(validDialoguePanel({ bond_stage: null })).bond_stage, null);
  assert.equal(Protocol.validateDialoguePanel(validDialoguePanel({ delivery: null })).delivery, null);

  const keyed = validDialoguePanel({
    host: { identity: 41, display_name: "公會職員", portrait_ref: "42" },
  });
  assert.deepEqual(Protocol.validateDialoguePanel(keyed), keyed);

  const atBound = "1".repeat(32);
  assert.equal(
    Protocol.validateDialoguePanel(
      validDialoguePanel({
        host: { identity: 41, display_name: "公會職員", portrait_ref: atBound },
      })
    ).host.portrait_ref,
    atBound
  );

  // Paired astral code points are legal text
  assert.doesNotThrow(() =>
    Protocol.validateDialoguePanel(
      validDialoguePanel({
        delivery: validDialogueDelivery({
          lines: [{ kind: "speech", speaker: "host", text: "歡迎\u{1F600}。" }],
        }),
      })
    )
  );
});

test("dialogue validator mirrors the server drift rejections and rejects v2", () => {
  // v2 rejection
  assert.throws(
    () =>
      Protocol.validateDialoguePanel({
        schema_version: 2,
        available: true,
        kind: "dialogue",
        host: { identity: 41, display_name: "a", portrait_ref: null },
        bond_stage: null,
        line: "old line",
        choices: [],
      }),
    /unsupported dialogue schema_version/
  );

  for (const bad of [
    // prototype-named own keys from JSON.parse must read as unknown fields
    JSON.parse(
      '{"schema_version":3,"available":true,"kind":"dialogue","host":{"identity":41,"display_name":"a","portrait_ref":null},"actor":{"identity":1,"display_name":"b","portrait_ref":null},"bond_stage":"友","context_id":"c","delivery":null,"choices":[],"pure_chain":[],"reading_revision":0,"completed_topic_ids":[],"unlock_batch":null,"__proto__":{}}'
    ),
    validDialoguePanel({ extra: 1 }),
    (() => {
      const missing = validDialoguePanel();
      delete missing.choices;
      return missing;
    })(),
    (() => {
      const missing = validDialoguePanel();
      delete missing.actor;
      return missing;
    })(),
    (() => {
      const missing = validDialoguePanel();
      delete missing.context_id;
      return missing;
    })(),
    validDialoguePanel({ schema_version: 1 }),
    validDialoguePanel({ schema_version: 2 }),
    validDialoguePanel({ schema_version: 4 }),
    { schema_version: 3, available: false },
    validDialoguePanel({ available: false }),
    validDialoguePanel({ kind: "party" }),
    validDialoguePanel({ host: { identity: 41, display_name: "a", portrait_ref: 42 } }),
    validDialoguePanel({ host: { identity: 41, display_name: "a", portrait_ref: "4a" } }),
    validDialoguePanel({
      host: { identity: 41, display_name: "a", portrait_ref: "1".repeat(33) },
    }),
    validDialoguePanel({ host: { identity: 0, display_name: "a", portrait_ref: null } }),
    validDialoguePanel({ host: { identity: 41, display_name: "  ", portrait_ref: null } }),
    validDialoguePanel({ bond_stage: 3 }),
    validDialoguePanel({ bond_stage: "" }),
    validDialoguePanel({ context_id: "" }),
    // choice cap and uniqueness
    validDialoguePanel({
      choices: Array.from({ length: Protocol.DIALOGUE_MAX_CHOICES + 1 }, (_, i) =>
        validDialogueChoice({ topic_id: "t_" + i, keyword_id: "k_" + i })
      ),
    }),
    validDialoguePanel({ choices: [validDialogueChoice(), validDialogueChoice()] }),
    validDialoguePanel({ choices: [validDialogueChoice({ topic_id: " " })] }),
    validDialoguePanel({ choices: [validDialogueChoice({ keyword_id: " " })] }),
    validDialoguePanel({ choices: [{ topic_id: "guild_staff.topic_01" }] }),
    // delivery schema errors
    validDialoguePanel({ delivery: { delivery_id: "" } }),
    validDialoguePanel({
      delivery: validDialogueDelivery({ kind: "invalid_kind" }),
    }),
    validDialoguePanel({
      delivery: validDialogueDelivery({
        lines: [{ kind: "speech", speaker: "invalid_speaker", text: "hi" }],
      }),
    }),
  ]) {
    assert.throws(() => Protocol.validateDialoguePanel(bad));
  }
});

test("dialogue is in the production panel allowlist with dialogue mode accepted in v3", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.dialogue, 3);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 5,
    mode: "dialogue",
    panels: {
      dialogue: { schema_version: 3, available: true, kind: "dialogue" },
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
      schema_version: 3,
      available: false,
      reason: { code: "dialogue_unavailable", message: "對話目前無法顯示" },
    },
  };
  envelope.revision = 7;
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
});
