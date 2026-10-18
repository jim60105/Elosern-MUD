/*
 * party_member panel v1 mirror: exact member-tab facts, server-authored
 * descriptors, shape-drift rejections.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");

function descriptor(action_id, params, enabled, reason) {
  return {
    action_id,
    params,
    enabled,
    reason: reason === undefined ? null : reason,
  };
}

function companionActions(memberId, overrides) {
  const options = overrides || {};
  return [
    descriptor("explore.possess", { npc_id: memberId }, true),
    descriptor(
      "explore.party_leave",
      { npc_id: memberId },
      options.leaveReason === undefined,
      options.leaveReason
    ),
    descriptor(
      "npc.persona.read",
      { npc_id: memberId },
      options.personaReason === undefined,
      options.personaReason
    ),
  ];
}

function commanderActions(reason) {
  return [
    descriptor(
      "character.persona.update",
      {},
      reason === undefined,
      reason
    ),
  ];
}

function intimate() {
  return {
    arousal: "中等",
    wetness: "微濕",
    shame: "輕微",
    exposure: "低",
    climax_phase: "未達",
    climax_today: 2,
  };
}

function companionSection(memberId, overrides) {
  return Object.assign(
    {
      bond: { stage: "親睦", step: 3, steps: 7 },
      membership: { general: true, temporary_commissions: [] },
      intimate: null,
      actions: companionActions(memberId),
    },
    overrides || {}
  );
}

function commanderSection(overrides) {
  return Object.assign(
    {
      persona: {
        background: null,
        personality: "沉穩",
        life_story: null,
        habit: null,
      },
      intimate: null,
      actions: commanderActions(),
    },
    overrides || {}
  );
}

function panel(role, memberId, section) {
  const isCommander = role === "commander";
  return {
    schema_version: 1,
    available: true,
    kind: "party_member",
    member_id: memberId,
    role: role,
    companion: isCommander ? null : section,
    commander: isCommander ? section : null,
  };
}

test("party_member companion and commander forms validate", () => {
  assert.equal(Protocol.PARTY_MEMBER_SCHEMA_VERSION, 1);
  const companion = panel("companion", 41, companionSection(41));
  assert.deepEqual(Protocol.validatePartyMemberPanel(companion), companion);
  const commander = panel("commander", 7, commanderSection());
  assert.deepEqual(Protocol.validatePartyMemberPanel(commander), commander);
  // The possession slot accepts the release action while possessing.
  const released = panel(
    "companion",
    41,
    companionSection(41, {
      actions: [
        descriptor("explore.possess_release", { npc_id: 41 }, true),
        ...companionActions(41).slice(1),
      ],
    })
  );
  assert.equal(
    Protocol.validatePartyMemberPanel(released).companion.actions[0].action_id,
    "explore.possess_release"
  );
  // Whitespace persona prose nulls out, exactly like the server.
  const blank = panel(
    "commander",
    7,
    commanderSection({
      persona: {
        background: "   ",
        personality: " 沉穩 ",
        life_story: null,
        habit: "",
      },
    })
  );
  assert.deepEqual(Protocol.validatePartyMemberPanel(blank).commander.persona, {
    background: null,
    personality: "沉穩",
    life_story: null,
    habit: null,
  });
  // A paired astral code point is legal text on both mirrors.
  assert.doesNotThrow(() =>
    Protocol.validatePartyMemberPanel(
      panel("companion", 41, companionSection(41, { bond: { stage: "親睦\u{1F600}", step: 1, steps: 7 } }))
    )
  );
});

test("party_member rejects shape drift", () => {
  const base = panel("companion", 41, companionSection(41));
  const commanderBase = panel("commander", 7, commanderSection());
  const invalid = [
    { ...base, extra: 1 },
    { ...base, commander: commanderSection() },
    { ...base, companion: null },
    { ...commanderBase, companion: companionSection(7) },
    { ...base, role: "ally" },
    { ...base, schema_version: 2 },
    { ...base, available: false },
    { ...base, kind: "party" },
    { ...base, member_id: true },
    { ...base, member_id: 0 },
    panel("companion", 41, companionSection(41, { bond: { stage: "親睦", step: 3, steps: 7, affinity: 30 } })),
    panel("companion", 41, companionSection(41, { bond: { stage: "  ", step: 1, steps: 7 } })),
    panel("companion", 41, companionSection(41, { bond: { stage: "親睦", step: 0, steps: 7 } })),
    panel("companion", 41, companionSection(41, { bond: { stage: "親睦", step: 8, steps: 7 } })),
    panel(
      "companion",
      41,
      companionSection(41, { bond: { stage: "長".repeat(129), step: 1, steps: 7 } })
    ),
    panel(
      "companion",
      41,
      companionSection(41, { membership: { general: 1, temporary_commissions: [] } })
    ),
    panel(
      "companion",
      41,
      companionSection(41, {
        membership: {
          general: false,
          temporary_commissions: [
            { quest_id: "q", role_id: "r", label: "l" },
            { quest_id: "q", role_id: "r", label: "l" },
          ],
        },
      })
    ),
    panel("companion", 41, companionSection(41, { intimate: { ...intimate(), extra: 1 } })),
    panel("companion", 41, companionSection(41, { intimate: { ...intimate(), arousal: "很高" } })),
    panel("companion", 41, companionSection(41, { actions: companionActions(41).slice(0, 2) })),
    panel(
      "companion",
      41,
      companionSection(41, { actions: companionActions(41).slice().reverse() })
    ),
    panel(
      "companion",
      41,
      companionSection(41, {
        actions: [descriptor("explore.possess_other", { npc_id: 41 }, true), ...companionActions(41).slice(1)],
      })
    ),
    panel(
      "companion",
      41,
      companionSection(41, {
        actions: [descriptor("explore.possess", { npc_id: 42 }, true), ...companionActions(41).slice(1)],
      })
    ),
    panel(
      "companion",
      41,
      companionSection(41, {
        actions: [descriptor("explore.possess", { npc_id: 41 }, true, "不行"), ...companionActions(41).slice(1)],
      })
    ),
    panel(
      "companion",
      41,
      companionSection(41, {
        actions: [descriptor("explore.possess", { npc_id: 41 }, false), ...companionActions(41).slice(1)],
      })
    ),
    panel("companion", 41, companionSection(41, { actions: companionActions(41, { leaveReason: "   " }) })),
    panel(
      "companion",
      41,
      companionSection(41, { actions: companionActions(41, { leaveReason: "長".repeat(513) }) })
    ),
    panel(
      "commander",
      7,
      commanderSection({
        persona: {
          background: null,
          personality: null,
          life_story: null,
          habit: null,
          identity: {},
        },
      })
    ),
    panel(
      "commander",
      7,
      commanderSection({
        persona: { background: "長".repeat(601), personality: null, life_story: null, habit: null },
      })
    ),
    panel("commander", 7, commanderSection({ actions: [] })),
    panel(
      "commander",
      7,
      commanderSection({ actions: [descriptor("npc.persona.read", { npc_id: 7 }, true)] })
    ),
  ];
  for (const payload of invalid) {
    assert.throws(() => Protocol.validatePartyMemberPanel(payload));
  }
});

test("the envelope dispatches party_member to its own validator", () => {
  // A wrong companion section proves the allowlisted name reaches the
  // validator rather than being accepted as an unknown panel.
  const broken = panel("companion", 41, companionSection(41, { bond: { stage: "", step: 1, steps: 7 } }));
  assert.throws(() => Protocol.validatePartyMemberPanel(broken));
  assert.equal(Protocol.PANEL_ALLOWLIST.party_member, 1);
});
