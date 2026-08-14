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

function validPanel(overrides) {
  return Object.assign(
    {
      schema_version: 2,
      available: true,
      kind: "character",
      traits: [
        { key: "hp", label: "生命", current: 10, max: 10 },
        { key: "atk_phys", label: "攻擊", current: 5, max: null },
      ],
      passives: [{ key: "defense_instinct", label: "防禦直覺" }],
      equipment: [
        { slot: "weapon_main", item_key: "plain_sword", display_name: "鐵劍" },
      ],
      disguise: { active: false, description: "", displayed: [] },
      guild: { rank: null, merit: 0 },
      wallet: 100,
      persona: { background: null },
    },
    overrides || {}
  );
}

test("character menu lists true trait rows with gauges and statics", () => {
  const menu = CharacterMenu.buildMenu(validPanel());
  const labels = menu.items.map((item) => item.label);
  assert.ok(labels.includes("生命：10 / 10"));
  assert.ok(labels.includes("攻擊：5"));
  assert.ok(labels.includes("被動技能"));
  assert.ok(labels.includes("防禦直覺"));
  assert.ok(labels.includes("weapon_main：鐵劍"));
  assert.ok(labels.includes("階級：未加入公會"));
  assert.ok(labels.includes("功績：0"));
  assert.ok(labels.includes("錢包：100 銅"));
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
    validPanel({ persona: { background: "在公會登記的新人冒險者" } })
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
