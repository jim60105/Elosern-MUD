/*
 * DOM-independent tests for the character-menu model.
 *
 * Runs with Node 24's built-in test runner; no npm packages. Covers trait,
 * passive, equipment, disguise, guild, and wallet rendering with true values
 * and no disguised substitution.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const CharacterMenu = require("../elosern/character_menu.js");
const { SYNTH_SKILL } = require("./support/synthetic-data.js");

// File-local synthetic rows (test-data-independence): invented t_-keyed skills,
// passive, and equipment with invented prose. The group `group` fields keep
// their wire taxonomy values; only shipped ids/prose are replaced.
const T_WATER_SKILL = { key: "t_tide_prick", label: "潮針術" };
const T_PASSIVE = { key: "t_bulwark_sense", label: "合成壁覺" };
const T_FIRE_GROUP_LABEL = "焰系";
const T_WATER_GROUP_LABEL = "潮系";
const T_MOVE_SKILL = { key: "t_gale_hop", label: "颶風跳" };
const T_SWORD = { item_key: "t_thorn_fang", display_name: "荊牙刃" };

function validPanel(overrides) {
  return Object.assign(
    {
      schema_version: 7,
      available: true,
      kind: "character",
      traits: [
        { key: "hp", label: "生命", base: 10, current: 10, max: 10, effective: 10, layers: [] },
        { key: "atk_phys", label: "攻擊", base: 5, current: 5, max: null, effective: 5, layers: [] },
      ],
      actives: [
        {
          category: "elemental_magic",
          label: "元素魔法",
          groups: [
            { group: "fire", label: T_FIRE_GROUP_LABEL, skills: [{ key: SYNTH_SKILL.id, label: SYNTH_SKILL.label }] },
            { group: "water", label: T_WATER_GROUP_LABEL, skills: [T_WATER_SKILL] },
          ],
        },
      ],
      passives: [
        {
          category: "enhancement",
          label: "強化",
          groups: [
            {
              group: null,
              label: null,
              skills: [T_PASSIVE],
            },
          ],
        },
      ],
      equipment: [
        { slot: "weapon_main", item_key: T_SWORD.item_key, display_name: T_SWORD.display_name, adjustment: "攻擊 +2" },
      ],
      disguise: { active: false, description: "", displayed: [] },
      guild: { rank: null, merit: 0 },
      wallet: 100,
      persona: { background: null, personality: null, life_story: null, habit: null },
      intimate: null,
    },
    overrides || {}
  );
}

test("character menu lists true trait rows with gauges and statics", () => {
  const menu = CharacterMenu.buildMenu(validPanel());
  const labels = menu.items.map((item) => item.label);
  assert.ok(labels.includes("生命：10 / 10"));
  assert.ok(labels.includes("攻擊：5"));
  assert.ok(labels.includes("主動技能"));
  assert.ok(labels.includes(SYNTH_SKILL.label));
  assert.ok(labels.includes(T_WATER_SKILL.label));
  assert.ok(labels.includes("被動技能"));
  assert.ok(labels.includes(T_PASSIVE.label));
  assert.ok(labels.includes(`weapon_main：${T_SWORD.display_name}`));
  assert.ok(labels.includes("階級：未加入公會"));
  assert.ok(labels.includes("功績：0"));
  assert.ok(labels.includes("錢包：100 銅"));
});

test("active and passive skill sections flatten the category-grouped payload", () => {
  const menu = CharacterMenu.buildMenu(
    validPanel({
      actives: [
        {
          category: "movement",
          label: "移動",
          groups: [
            {
              group: null,
              label: null,
              skills: [
                { key: "flee", label: "逃跑" },
                T_MOVE_SKILL,
              ],
            },
          ],
        },
      ],
    })
  );
  const labels = menu.items.map((item) => item.label);
  assert.ok(labels.includes("主動技能"));
  assert.ok(labels.includes("逃跑"));
  assert.ok(labels.includes(T_MOVE_SKILL.label));
  // The category/group taxonomy stays wire-only; the menu flattens it.
  assert.ok(!labels.includes("移動"));
  assert.ok(!labels.includes("元素魔法"));
  assert.ok(!labels.includes(T_FIRE_GROUP_LABEL));
});

test("an empty actives or passives list renders no skill section", () => {
  const menu = CharacterMenu.buildMenu(
    validPanel({ actives: [], passives: [] })
  );
  const labels = menu.items.map((item) => item.label);
  assert.ok(!labels.includes("主動技能"));
  assert.ok(!labels.includes("被動技能"));
});

test("every character row is display-only and never submits", () => {
  const menu = CharacterMenu.buildMenu(validPanel());
  menu.items.forEach((item) => {
    assert.equal(item.enabled, false);
    assert.equal(item.actionId, null);
  });
});

test("an honest disguise reports displayed values without substituting", () => {
  const menu = CharacterMenu.buildMenu(
    validPanel({
      disguise: {
        active: true,
        description: "目前以偽裝的外貌示人。",
        displayed: [
          { key: "atk_phys", label: "攻擊", value: 12 },
          { key: "agility", label: "敏捷", value: 10 },
        ],
      },
    })
  );
  const labels = menu.items.map((item) => item.label);
  assert.ok(labels.includes("偽裝"));
  assert.ok(labels.includes("目前以偽裝的外貌示人。"));
  assert.ok(labels.includes("攻擊：12"));
  assert.ok(labels.includes("敏捷：10"));
  // The true attack row is still reported from the panel's true traits.
  assert.ok(labels.includes("攻擊：5"));
});

test("an undisguised actor has no disguise section", () => {
  const menu = CharacterMenu.buildMenu(validPanel());
  const labels = menu.items.map((item) => item.label);
  assert.ok(!labels.includes("偽裝"));
});

test("persona background renders as a display-only row when present", () => {
  const menu = CharacterMenu.buildMenu(
    validPanel({
      persona: {
        background: "在公會登記的新人冒險者",
        personality: null,
        life_story: null,
        habit: null,
      },
    })
  );
  const labels = menu.items.map((item) => item.label);
  assert.ok(labels.includes("背景"));
  assert.ok(labels.includes("背景：在公會登記的新人冒險者"));
  menu.items.forEach((item) => {
    assert.equal(item.enabled, false);
    assert.equal(item.actionId, null);
  });
});

test("a character without a background renders no persona row", () => {
  const menu = CharacterMenu.buildMenu(validPanel());
  const labels = menu.items.map((item) => item.label);
  assert.ok(!labels.includes("背景"));
});

test("a version-5 payload renders totals and ignores the breakdown layers", () => {
  // The legacy client is totals-only at v5 (render-equipment-
  // breakdown-webclient closed the transitional v4 window): the menu reads
  // current/max on every row (statics included), never renders the
  // breakdown layers or the adjustment text, and errors on nothing.
  const panel = validPanel({
    traits: validPanel().traits.map((row) =>
      Object.assign({}, row, {
        layers: row.key === "hp" ? [] : [{ source: "equipment", name: T_SWORD.display_name, kind: "flat", amount: 2 }],
      })
    ),
  });
  const consoleErrors = [];
  const originalError = console.error;
  console.error = (...args) => consoleErrors.push(args);
  try {
    const menu = CharacterMenu.buildMenu(panel);
    console.error = originalError;
    const labels = menu.items.map((item) => item.label);
    assert.ok(labels.includes("生命：10 / 10"));
    assert.ok(labels.includes("攻擊：5"), "static rows keep the total display");
    assert.ok(
      !labels.some((label) => label.includes(T_SWORD.display_name) && label.includes("+2")),
      "layer amounts never render"
    );
    assert.ok(!labels.some((label) => label.includes("攻擊 +2")), "adjustment text never renders");
    assert.deepEqual(consoleErrors, [], "no console errors while ignoring layers");
  } finally {
    console.error = originalError;
  }
});
