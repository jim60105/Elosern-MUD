/*
 * SkillBook use menu model (skillbook-authoritative-casting D6): exact
 * explore.cast payloads per TargetSpec, AREA presenter-order selection,
 * monster-opening confirmation, scale frames, disabled reasons, and
 * selection reconciliation against a newer panel. Synthetic fixtures only.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Menu = require("../elosern/skill_use_menu.js");

function panel(spec, overrides) {
  const base = {
    schema_version: 1,
    available: true,
    kind: "skill_use",
    scale: 1,
    skill: {
      key: "t_soft_mend",
      label: "合成癒合",
      description: "合成用技能。",
      target_spec: spec,
      usable_out_of_combat: true,
      cost: { mp: 11 },
      enabled: true,
      disabled_reason: null,
      targets: [],
      openings: [],
    },
  };
  if (spec === "self") {
    base.skill.targets = [{ identity: 3, label: "測試者（自己）", enabled: true, disabled_reason: null }];
  }
  if (spec === "single" || spec === "area") {
    base.skill.targets = [
      { identity: 3, label: "測試者（自己）", enabled: true, disabled_reason: null },
      { identity: 5, label: "村民（1）", enabled: true, disabled_reason: null },
      { identity: 6, label: "村民（2）", enabled: false, disabled_reason: { code: "target_dead", message: "目標已失去行動能力。" } },
    ];
    base.skill.openings = [
      { identity: 9, label: "合成狼（開戰）", target_ids: spec === "area" ? [9, 12] : [9], enabled: true, disabled_reason: null },
    ];
    if (spec === "area") {
      base.skill.openings.push({ identity: 12, label: "乙等 2 名（全體開戰）", target_ids: [9, 12], enabled: true, disabled_reason: null });
    }
  }
  if (overrides) overrides(base);
  return base;
}

test("NONE and SELF require one explicit confirmation carrying no target", () => {
  for (const spec of ["none", "self"]) {
    const menu = Menu.useMenu(Menu.createModel(panel(spec)));
    const confirm = menu.items.find((item) => item.kind === "confirm");
    assert.equal(confirm.actionId, "explore.cast");
    assert.deepEqual(confirm.payload, { skill_key: "t_soft_mend" });
    assert.ok(!("target_ids" in confirm.payload));
  }
});

test("SINGLE rows submit exactly one server identity and keep disabled reasons", () => {
  const menu = Menu.useMenu(Menu.createModel(panel("single")));
  const villager = menu.items.find((item) => item.key === "target-5");
  assert.deepEqual(villager.payload, { skill_key: "t_soft_mend", target_ids: [5] });
  const dead = menu.items.find((item) => item.key === "target-6");
  assert.equal(dead.enabled, false);
  assert.equal(dead.actionId, null);
  assert.equal(dead.disabledReason.code, "target_dead");
});

test("duplicate display names keep distinct identities", () => {
  const menu = Menu.useMenu(Menu.createModel(panel("single")));
  const keys = menu.items.filter((item) => item.kind === "target").map((item) => item.key);
  assert.deepEqual(keys, ["target-3", "target-5", "target-6"]);
});

test("AREA selection toggles enabled rows only and submits in presenter order", () => {
  const model = Menu.createModel(panel("area"));
  assert.equal(Menu.toggle(model, 5), true);
  assert.equal(Menu.toggle(model, 3), true);
  assert.equal(Menu.toggle(model, 6), false, "a disabled candidate is never selectable");
  const menu = Menu.useMenu(model);
  const confirm = menu.items.find((item) => item.key === "area-confirm");
  assert.equal(confirm.enabled, true);
  assert.deepEqual(confirm.payload, { skill_key: "t_soft_mend", target_ids: [3, 5] });
  assert.ok(!("opening_target_id" in confirm.payload));
  assert.equal(menu.items.find((item) => item.key === "area-5").selected, true);
  Menu.toggle(model, 5);
  Menu.toggle(model, 3);
  const empty = Menu.useMenu(model).items.find((item) => item.key === "area-confirm");
  assert.equal(empty.enabled, false);
  assert.equal(empty.payload, null);
});

test("a monster opening needs a separate confirmation carrying the anchor only", () => {
  const model = Menu.createModel(panel("area"));
  const opening = Menu.useMenu(model).items.find((item) => item.key === "opening-12");
  assert.equal(opening.actionId, "open-skilluse-opening");
  const confirm = Menu.openingMenu(model, 12);
  const submit = confirm.items[0];
  assert.equal(submit.key, "confirm-opening");
  assert.deepEqual(submit.payload, { skill_key: "t_soft_mend", opening_target_id: 12 });
  assert.deepEqual(submit.lineUp, [9, 12]);
  assert.equal(confirm.items[1].key, "cancel-opening");
  assert.equal(Menu.openingMenu(model, 99), null);
});

test("a damaging skill collapses refused ordinary rows into one note", () => {
  const damaging = panel("single", (p) => {
    p.skill.targets.forEach((row) => {
      row.enabled = false;
      row.disabled_reason = { code: "damage_requires_monster_target", message: "該技能會造成傷害。" };
    });
  });
  const items = Menu.useMenu(Menu.createModel(damaging)).items;
  assert.equal(items.filter((item) => item.kind === "target").length, 0);
  assert.equal(items[0].key, "targets-damage-only");
  assert.ok(items.some((item) => item.key === "opening-9"));
});

test("scale rungs re-preview and only advertised skills carry a scale", () => {
  const scaled = panel("none", (p) => {
    p.scale = 0.5;
    p.skill.freeform_scales = [
      { scale: 0.25, label: "1/4", mp_cost: 3 },
      { scale: 0.5, label: "1/2", mp_cost: 6 },
      { scale: 1, label: "1", mp_cost: 11 },
    ];
  });
  const model = Menu.createModel(scaled);
  const use = Menu.useMenu(model);
  assert.equal(use.items[0].key, "scale-open");
  assert.equal(use.items[0].label, "威力 ×1/2");
  assert.deepEqual(use.items[1].payload, { skill_key: "t_soft_mend", scale: 0.5 });
  const rungs = Menu.scaleMenu(model);
  assert.deepEqual(rungs.items.map((item) => item.payload.scale), [0.25, 0.5, 1]);
  assert.equal(rungs.focusKey, "scale-1/2");
  const plain = Menu.useMenu(Menu.createModel(panel("none")));
  assert.ok(!plain.items.some((item) => item.key === "scale-open"));
});

test("a disabled skill offers no confirmation and explains why", () => {
  const disabled = panel("none", (p) => {
    p.skill.enabled = false;
    p.skill.disabled_reason = { code: "insufficient_resource", message: "MP 不足：需要 11。" };
  });
  const confirm = Menu.useMenu(Menu.createModel(disabled)).items[0];
  assert.equal(confirm.enabled, false);
  assert.equal(confirm.actionId, null);
  assert.equal(confirm.disabledReason.message, "MP 不足：需要 11。");
});

test("a newer panel drops vanished or disabled selections", () => {
  const model = Menu.createModel(panel("area"));
  Menu.toggle(model, 3);
  Menu.toggle(model, 5);
  const newer = panel("area", (p) => {
    p.skill.targets = p.skill.targets.filter((row) => row.identity !== 5);
    p.skill.targets[0].enabled = false;
    p.skill.targets[0].disabled_reason = { code: "target_dead", message: "倒下了。" };
  });
  const rebuilt = Menu.createModel(newer, model);
  assert.deepEqual(rebuilt.selected, []);
  const other = Menu.createModel(panel("area", (p) => { p.skill.key = "t_other"; }), model);
  assert.deepEqual(other.selected, []);
});
