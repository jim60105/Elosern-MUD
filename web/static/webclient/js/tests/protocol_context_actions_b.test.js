/*
 * context_actions panel rejections: version parity, freeform scales, malformed groups, atomicity.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { T_ACT_ARENA, T_ACT_SOLO, T_FIRE_LABEL, snapshot, validStatusPanel } = require("./protocol_support.js");
const { nestedSkills, validCategoryGroup, validCombatPanel, validCombatParticipant, validCombatSkill, validRecoveryPanel, validSkillGroup } = require("./protocol_fixtures.js");

test("the combat form is byte-identical to version 4 plus suggestions", () => {
  const version6 = validCombatPanel();
  const stripV6 = (panel) => {
    const copy = JSON.parse(JSON.stringify(panel));
    copy.participants.forEach((participant) => delete participant.conditions);
    copy.skills.forEach((category) =>
      category.groups.forEach((group) =>
        group.skills.forEach((skill) => {
          delete skill.hostile;
          delete skill.beneficial;
        })
      )
    );
    delete copy.schema_version;
    delete copy.suggestions;
    return copy;
  };
  const version4 = Object.assign({ schema_version: 4 }, stripV6(version6));
  assert.equal(version6.schema_version, 6);
  // Every combat field serializes exactly as at version 4; only the version
  // field, the suggestions envelope (v5) and the v6 participant conditions
  // and skill hostile/beneficial facts are added.
  const version4Copy = Object.assign({}, version4);
  delete version4Copy.schema_version;
  assert.deepEqual(stripV6(version6), version4Copy);
  assert.deepEqual(version6.suggestions, { status: "unavailable" });
  assert.deepEqual(version6.participants[0].conditions, []);
  assert.doesNotThrow(() => Protocol.validateContextActionsPanel(version6));
  assert.throws(() => Protocol.validateContextActionsPanel(version4));
  // A version-5 payload is rejected by the v6 mirror.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(Object.assign({}, version6, { schema_version: 5 }))
  );
  assert.throws(() =>
    Protocol.validatePanel(
      "context_actions",
      Protocol.PANEL_ALLOWLIST.context_actions,
      Object.assign({}, version6, { schema_version: 5 })
    )
  );
});

test("participant conditions are exact bounded status rows", () => {
  const row = { code: "t_ash_burn", label: "合成灼燒", severity: "harmful" };
  const withConditions = (conditions) =>
    validCombatPanel({ participants: [validCombatParticipant({ conditions: conditions })] });
  assert.doesNotThrow(() =>
    Protocol.validateContextActionsPanel(withConditions(Array(8).fill(row)))
  );
  [
    Array(9).fill(row),
    [Object.assign({}, row, { severity: "hidden" })],
    [Object.assign({}, row, { label: " " })],
    [Object.assign({}, row, { code: "Bad Code" })],
    [Object.assign({}, row, { remaining_seconds: 30 })],
    [{ code: "t_ash_burn", label: "合成灼燒" }],
    null,
  ].forEach((conditions) => {
    assert.throws(() => Protocol.validateContextActionsPanel(withConditions(conditions)));
  });
  const missing = validCombatParticipant();
  delete missing.conditions;
  assert.throws(() =>
    Protocol.validateContextActionsPanel(validCombatPanel({ participants: [missing] }))
  );
});

test("skill hostile and beneficial are required booleans", () => {
  ["hostile", "beneficial"].forEach((field) => {
    [null, 1, "true"].forEach((value) => {
      const skill = validCombatSkill({ [field]: value });
      assert.throws(() =>
        Protocol.validateContextActionsPanel(validCombatPanel({ skills: nestedSkills(skill) }))
      );
    });
    const missing = validCombatSkill();
    delete missing[field];
    assert.throws(() =>
      Protocol.validateContextActionsPanel(validCombatPanel({ skills: nestedSkills(missing) }))
    );
  });
  const both = validCombatSkill({ hostile: true, beneficial: true });
  assert.doesNotThrow(() =>
    Protocol.validateContextActionsPanel(validCombatPanel({ skills: nestedSkills(both) }))
  );
});

test("the unavailable forms differ only in schema_version", () => {
  const version4 = {
    schema_version: 4,
    available: false,
    reason: { code: "presentation_unavailable", message: "目前無法顯示此介面" },
  };
  const version6 = {
    schema_version: 6,
    available: false,
    reason: { code: "presentation_unavailable", message: "目前無法顯示此介面" },
  };
  const withoutVersion = (panel) => {
    const copy = Object.assign({}, panel);
    delete copy.schema_version;
    return copy;
  };
  assert.deepEqual(withoutVersion(version6), withoutVersion(version4));
  assert.doesNotThrow(() =>
    Protocol.validatePanel("context_actions", 6, version6)
  );
  assert.throws(() => Protocol.validatePanel("context_actions", 6, version4));
  assert.throws(() =>
    Protocol.validatePanel("context_actions", 6, Object.assign({}, version6, { schema_version: 5 }))
  );
  // The unavailable form rejects a suggestions field: the field set stays
  // exactly schema_version/available/reason.
  assert.throws(() =>
    Protocol.validatePanel(
      "context_actions",
      6,
      Object.assign({}, version6, { suggestions: { status: "unavailable" } })
    )
  );
});

test("freeform_scales is optional and validated when present", () => {
  const scales = [
    { scale: 0.25, label: "1/4", mp_cost: 5 },
    { scale: 0.5, label: "1/2", mp_cost: 10 },
    { scale: 1, label: "1", mp_cost: 20 },
    { scale: 2, label: "2", mp_cost: 40 },
    { scale: 4, label: "4", mp_cost: 80 },
  ];
  assert.doesNotThrow(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: nestedSkills(validCombatSkill({ freeform_scales: scales })) })
    )
  );
  const bad = (overrides) =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: nestedSkills(validCombatSkill({ freeform_scales: [Object.assign({}, scales[0], overrides)] })) })
    );
  assert.throws(() => bad({ scale: 3 }));
  assert.throws(() => bad({ label: "x" }));
  assert.throws(() => bad({ mp_cost: 0 }));
  assert.throws(() => Protocol.validateContextActionsPanel(
    validCombatPanel({ skills: nestedSkills(validCombatSkill({ freeform_scales: [] })) })
  ));
  // A ladder prefix (bottom rungs only) is the server-authoritative shape.
  assert.doesNotThrow(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: nestedSkills(validCombatSkill({ freeform_scales: scales.slice(0, 3) })) })
    )
  );
  // A set that is not a prefix (missing the 0.25 rung) still rejects.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: nestedSkills(validCombatSkill({ freeform_scales: scales.slice(2) })) })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        skills: nestedSkills(validCombatSkill({ freeform_scales: [Object.assign({}, scales[0], { label: "4" }), ...scales.slice(1)] })),
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        skills: nestedSkills(Object.assign(validCombatSkill(), { cost: { sp: 30 }, freeform_scales: scales })),
      })
    )
  );
});

test("rejects malformed context_actions panels atomically", () => {
  assert.throws(() =>
    Protocol.validatePanel("context_actions", Protocol.PANEL_ALLOWLIST.context_actions, {
      schema_version: 6,
      available: false,
    })
  );
  assert.throws(() => Protocol.validateContextActionsPanel(validCombatPanel({ extra: 1 })));
  assert.throws(() => Protocol.validateContextActionsPanel(validCombatPanel({ kind: "exploration" })));
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ root_actions: ["attack", "skills", "items", "defend", "flee", "bogus"] })
    )
  );
  // A disabled skill must carry a disabled_reason.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: nestedSkills(validCombatSkill({ enabled: false, disabled_reason: null })) })
    )
  );
  // Only AREA skills may carry shorthands.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: nestedSkills(validCombatSkill({ shorthands: ["all-enemies"] })) })
    )
  );
  // portrait_ref must be an opaque decimal catalog key or null in version 3.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        participants: [validCombatParticipant({ portrait_ref: "https://x.test/a.png" })],
      })
    )
  );
  assert.doesNotThrow(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        participants: [validCombatParticipant({ portrait_ref: "42" })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        participants: [validCombatParticipant({ portrait_ref: "4.2" })],
      })
    )
  );
  // A flat v2 skill array is not a valid v3 payload.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: [validCombatSkill()] })
    )
  );
  // Skill targets must reference a presented participant.
  assert.throws(() =>
    Protocol.validateContextActionsPanel({ skills: nestedSkills(validCombatSkill({ targets: [99] })) })
  );
  // A recovery session must not expose cast/flee root actions.
  assert.throws(() => Protocol.validateContextActionsPanel(validRecoveryPanel({ root_actions: ["attack"] })));
  // A ready session must have a null reason.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        session: {
          session_id: "hostile:1:0",
          mode: "hostile",
          round: 0,
          state: "ready",
          reason: { code: "x", message: "說明" },
        },
      })
    )
  );
});

test("rejects malformed category and skill groups", () => {
  // Unregistered category key.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: [validCategoryGroup({ category: "bogus" })] })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: [validCategoryGroup({ category: "movement" })] })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: [validCategoryGroup({ category: "innate_gift" })] })
    )
  );
  // Co-nullability of group and label.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        skills: [validCategoryGroup({ groups: [validSkillGroup({ group: null, label: T_FIRE_LABEL })] })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        skills: [validCategoryGroup({ groups: [validSkillGroup({ group: "fire", label: null })] })],
      })
    )
  );
  // Empty groups array: empty categories are omitted, not emitted empty.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({ skills: [validCategoryGroup({ groups: [] })] })
    )
  );
  // An empty skill group is rejected.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validCombatPanel({
        skills: [validCategoryGroup({ groups: [validSkillGroup({ skills: [] })] })],
      })
    )
  );
  // The top-level array is bounded by the SkillCategory count.
  const tooMany = [];
  for (let index = 0; index < 7; index++) {
    tooMany.push(validCategoryGroup());
  }
  assert.throws(() => Protocol.validateContextActionsPanel(validCombatPanel({ skills: tooMany })));
});

test("the flattened skill-count bound rejects a small-category payload", () => {
  // Design D-5: MAX_SKILLS applies to the flattened descriptor total, not to
  // the top-level category-group count. A payload whose flattened total is
  // 193 must be rejected even though its category-group count is far below
  // the bound. Skills are spread across sub-groups so each group stays within
  // the global MAX_LIST_ITEMS bound — the panel's flattened total, not any
  // single array, is what must exceed MAX_SKILLS.
  const subGroups = [];
  for (let group = 0; group < 3; group++) {
    const skills = [];
    const count = group === 2 ? 65 : 64;
    for (let index = 1; index <= count; index++) {
      const flat = group * 64 + index;
      skills.push(validCombatSkill({ key: "skill_" + flat, label: "技能名稱" + flat }));
    }
    subGroups.push(validSkillGroup({ group: "group_" + group, label: "群組" + group, skills: skills }));
  }
  assert.throws(() =>
    Protocol.validateContextActionsPanel(validCombatPanel({ skills: [validCategoryGroup({ groups: subGroups })] }))
  );
  // 192 skills across the same shape still passes, and the payload also
  // satisfies the global envelope safety (every array within MAX_LIST_ITEMS,
  // canonical JSON within the byte bound) that the real client applies
  // before panel validation.
  subGroups[2].skills.pop();
  const accepted = validCombatPanel({ skills: [validCategoryGroup({ groups: subGroups })] });
  assert.doesNotThrow(() =>
    Protocol.validateContextActionsPanel(accepted)
  );
  assert.doesNotThrow(() => Protocol.checkEnvelope(accepted));
});

test("a category without a group carries exactly one null-keyed sub-group", () => {
  // The single-null-group case must be accepted: a martial_arts category
  // whose members never declare a group emits exactly one { group: null,
  // label: null } sub-group listing every owned skill.
  const panel = validCombatPanel({
    skills: [
      validCategoryGroup({
        category: "martial_arts",
        label: "武技",
        groups: [
          validSkillGroup({ group: null, label: null, skills: [validCombatSkill()] }),
        ],
      }),
    ],
  });
  assert.doesNotThrow(() => Protocol.validateContextActionsPanel(panel));
});

test("sexual_act sub-group keys accept Traditional Chinese line names", () => {
  // The act catalog keys sexual_act sub-groups by their Traditional Chinese
  // line names (獨處, 羞恥, 關係, 戰鬥); the group key is a bounded string,
  // not an ASCII identifier.
  const panel = validCombatPanel({
    skills: [
      validCategoryGroup({
        category: "sexual_act",
        label: "性愛行為",
        groups: [
          validSkillGroup({
            group: "獨處",
            label: "獨處",
            skills: [validCombatSkill({ key: T_ACT_SOLO })],
          }),
          validSkillGroup({
            group: "戰鬥",
            label: "戰鬥",
            skills: [validCombatSkill({ key: T_ACT_ARENA })],
          }),
        ],
      }),
    ],
  });
  assert.doesNotThrow(() => Protocol.validateContextActionsPanel(panel));
});

test("skill group keys reject empty or whitespace strings", () => {
  for (const bad of ["", "   "]) {
    const panel = validCombatPanel({
      skills: [
        validCategoryGroup({
          category: "sexual_act",
          label: "性愛行為",
          groups: [validSkillGroup({ group: bad, label: "獨處" })],
        }),
      ],
    });
    assert.throws(() => Protocol.validateContextActionsPanel(panel));
  }
});

test("duplicate skill keys across categories are rejected", () => {
  const panel = validCombatPanel({
    skills: [
      validCategoryGroup(),
      validCategoryGroup({
        category: "martial_arts",
        label: "武技",
        groups: [validSkillGroup({ group: null, label: null })],
      }),
    ],
  });
  assert.throws(() => Protocol.validateContextActionsPanel(panel));
});

test("a combat snapshot with a malformed context_actions panel is rejected atomically", () => {
  const bad = snapshot({
    mode: "combat",
    panels: {
      status: validStatusPanel({ combat: { mode: "hostile", round: 0 } }),
      context_actions: validCombatPanel({ kind: "bogus" }),
    },
  });
  const store = Protocol.createStore();
  assert.equal(store.receive(1, "ui_snapshot", [bad], {}).accepted, false);
  assert.equal(store.getState().phase, "idle");
});

