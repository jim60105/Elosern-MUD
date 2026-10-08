/*
 * skill_use panel v1 mirror: the exact available form, unique bounded
 * identities, opening line-up cross references, the enabled/disabled_reason
 * pairing, the registered version, and panel validation through the facade.
 *
 * All fixtures are synthetic: invented keys, invented prose.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");

function panel(overrides) {
  const base = {
    schema_version: 1,
    available: true,
    kind: "skill_use",
    scale: 1,
    skill: {
      key: "t_soft_mend",
      label: "合成癒合",
      description: "合成用的單體治療。",
      target_spec: "single",
      usable_out_of_combat: true,
      cost: { mp: 11 },
      enabled: true,
      disabled_reason: null,
      targets: [
        { identity: 3, label: "測試者（自己）", enabled: true, disabled_reason: null },
        { identity: 5, label: "村民（1）", enabled: true, disabled_reason: null },
        { identity: 6, label: "村民（2）", enabled: false, disabled_reason: { code: "target_dead", message: "目標已失去行動能力。" } },
      ],
      openings: [
        {
          identity: 9,
          label: "合成狼（開戰）",
          target_ids: [9],
          enabled: true,
          disabled_reason: null,
        },
      ],
    },
  };
  return overrides ? overrides(base) || base : base;
}

test("the registered allowlist version is 1", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.skill_use, 1);
  assert.equal(Protocol.SKILL_USE_SCHEMA_VERSION, 1);
});

test("a valid preview passes through the facade and validatePanel", () => {
  assert.doesNotThrow(() => Protocol.validateSkillUsePanel(panel()));
  assert.doesNotThrow(() => Protocol.validatePanel("skill_use", 1, panel()));
});

test("the common unavailable form is accepted", () => {
  assert.doesNotThrow(() =>
    Protocol.validatePanel("skill_use", 1, {
      schema_version: 1,
      available: false,
      reason: { code: "skill_use_unavailable", message: "技能施放預覽目前無法顯示" },
    })
  );
});

test("an area opening discloses a line-up of advertised monsters", () => {
  const area = panel((p) => {
    p.skill.target_spec = "area";
    p.skill.openings = [
      { identity: 9, label: "甲等 2 名（全體開戰）", target_ids: [9, 12], enabled: true, disabled_reason: null },
      { identity: 12, label: "乙等 2 名（全體開戰）", target_ids: [9, 12], enabled: true, disabled_reason: null },
    ];
  });
  assert.doesNotThrow(() => Protocol.validateSkillUsePanel(area));
});

test("freeform rungs are shape-checked and an unadvertised scale stays readable", () => {
  const scaled = panel((p) => {
    p.scale = 0.5;
    p.skill.freeform_scales = [
      { scale: 0.25, label: "1/4", mp_cost: 3 },
      { scale: 0.5, label: "1/2", mp_cost: 6 },
    ];
  });
  assert.doesNotThrow(() => Protocol.validateSkillUsePanel(scaled));
  const forged = panel((p) => {
    p.scale = 4;
    p.skill.enabled = false;
    p.skill.disabled_reason = { code: "scaled_cast_forbidden", message: "尚未掌握該屬性精髓，無法自由調整威力。" };
    p.skill.targets.forEach((row) => {
      row.enabled = false;
      row.disabled_reason = { code: "scaled_cast_forbidden", message: "不可。" };
    });
    p.skill.openings[0].enabled = false;
    p.skill.openings[0].disabled_reason = { code: "scaled_cast_forbidden", message: "不可。" };
  });
  assert.doesNotThrow(() => Protocol.validateSkillUsePanel(forged));
});

const BAD = {
  "unknown field": (p) => { p.skill.extra = 1; },
  "wrong version": (p) => { p.schema_version = 2; },
  "wrong kind": (p) => { p.kind = "combat"; },
  "duplicate identity": (p) => { p.skill.targets.push(Object.assign({}, p.skill.targets[0])); },
  "dangling line-up": (p) => { p.skill.openings[0].target_ids = [9, 99]; },
  "single opening widened": (p) => { p.skill.openings[0].target_ids = [9, 3]; },
  "anchor missing from line-up": (p) => { p.skill.target_spec = "area"; p.skill.openings[0].target_ids = [3]; },
  "target doubles as opening": (p) => { p.skill.targets[0].identity = 9; },
  "disabled without reason": (p) => { p.skill.targets[0].enabled = false; },
  "enabled with reason": (p) => { p.skill.targets[0].disabled_reason = { code: "x", message: "y" }; },
  "skill enabled mismatch": (p) => { p.skill.enabled = false; p.skill.disabled_reason = { code: "x", message: "y" }; },
  "boolean identity": (p) => { p.skill.targets[0].identity = true; },
  "unsafe identity": (p) => { p.skill.targets[0].identity = Number.MAX_SAFE_INTEGER + 1; },
  "empty label": (p) => { p.skill.targets[0].label = "  "; },
  "overlong label": (p) => { p.skill.targets[0].label = "長".repeat(129); },
  "too many targets": (p) => {
    p.skill.targets = Array.from({ length: 65 }, (_, i) => ({ identity: 100 + i, label: "x", enabled: true, disabled_reason: null }));
  },
  "none with targets": (p) => { p.skill.target_spec = "none"; p.skill.openings = []; },
  "self with openings": (p) => { p.skill.target_spec = "self"; p.skill.targets = [p.skill.targets[0]]; },
  "bad scale": (p) => { p.scale = 0.3; },
  "boolean scale": (p) => { p.scale = true; },
  "unordered rungs": (p) => { p.skill.freeform_scales = [{ scale: 0.5, label: "1/2", mp_cost: 6 }]; },
};

for (const [name, mutate] of Object.entries(BAD)) {
  test(`malformed preview is rejected: ${name}`, () => {
    assert.throws(() => Protocol.validateSkillUsePanel(panel((p) => { mutate(p); })));
  });
}
