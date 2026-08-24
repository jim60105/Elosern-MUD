/*
 * DOM-independent tests for the Elosern character-creation menu model.
 *
 * Covers preset-card routing and payload production, custom-form field
 * geometry and race/subrace derivation, advisory bounds validation,
 * confirmation gating, saved-draft restoration, and exact wire payloads.
 * Runs with Node's built-in test runner.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const CreationMenu = require("../elosern/creation_menu.js");

function validPanel(overrides) {
  const axes = {
    hp: { axis: "hp", label: "生命值", explanation: "決定承受", minimum: 0, maximum: 100 },
    mp: { axis: "mp", label: "魔力值", explanation: "驅動魔法", minimum: 0, maximum: 100 },
    sp: { axis: "sp", label: "體力值", explanation: "支撐行動", minimum: 0, maximum: 100 },
    atk_phys: { axis: "atk_phys", label: "物理攻擊", explanation: "影響傷害", minimum: 0, maximum: 21 },
    agility: { axis: "agility", label: "敏捷", explanation: "命中迴避", minimum: 0, maximum: 21 },
    defense: { axis: "defense", label: "防禦", explanation: "減免傷害", minimum: 0, maximum: 21 },
  };
  const humanAxes = ["hp", "mp", "sp", "atk_phys", "agility", "defense"].map((k) =>
    Object.assign({}, axes[k])
  );
  const panel = {
    schema_version: 1,
    available: true,
    kind: "creation",
    draft: null,
    presets: [
      {
        key: "human_wanderer",
        display_name: "艾琳",
        race: "human",
        race_description: "人類",
        subrace: "human_commoner",
        emphasis: "均衡",
        background: "來自南境的旅人",
      },
      {
        key: "elf_guardian",
        display_name: "瑟芮雅",
        race: "elf",
        race_description: "精靈",
        subrace: "fionnen",
        emphasis: "守護",
        background: "斐歐恩護衛",
      },
    ],
    custom: {
      name: { min_length: 1, max_length: 64 },
      adult: {
        age_minimum: 18,
        age_maximum: 10000,
        apparent_age_minimum: 18,
        apparent_age_maximum: 10000,
      },
      races: [
        { key: "human", description: "人類", subraces: ["human_royal", "human_commoner"] },
        { key: "elf", description: "精靈", subraces: ["fionnen", "ciaran"] },
      ],
      subraces: {
        human_royal: { display_name_zh: "王族", common_name_zh: "皇族與大貴族", specialty: "教育" },
        human_commoner: { display_name_zh: "平民", common_name_zh: "普通平民", specialty: "工匠" },
        fionnen: { display_name_zh: "斐歐恩族", common_name_zh: "森林精靈", specialty: "射術" },
        ciaran: { display_name_zh: "基亞蘭族", common_name_zh: "黑暗精靈", specialty: "劍術" },
      },
      profiles: [
        { race: "human", subrace: "human_royal", budget: 181, axes: humanAxes },
        { race: "human", subrace: "human_commoner", budget: 181, axes: humanAxes },
        { race: "elf", subrace: "fionnen", budget: 37, axes: humanAxes },
        { race: "elf", subrace: "ciaran", budget: 37, axes: humanAxes },
      ],
      affinity: {
        human: {
          maximum: 2,
          elements: ["fire", "water", "wind", "earth", "lightning", "ice", "light", "dark"].map((key) => ({
            key,
            label: key,
          })),
        },
        beastfolk: {
          maximum: 1,
          elements: ["fire", "water", "wind", "earth", "lightning", "ice", "light", "dark"].map((key) => ({
            key,
            label: key,
          })),
        },
        elf: {
          maximum: 0,
          elements: ["fire", "water", "wind", "earth", "lightning", "ice", "light", "dark"].map((key) => ({
            key,
            label: key,
          })),
        },
      },
    },
  };
  return Object.assign({}, panel, overrides || {});
}

test("root and preset menus route with exact payloads", () => {
  const root = CreationMenu.rootItems(validPanel());
  assert.equal(root.length, 3);
  assert.equal(root[0].openSubmenu, "presets");
  assert.equal(root[1].openSubmenu, "custom");
  assert.equal(root[2].openSubmenu, "concept");

  const presets = CreationMenu.presetItems(validPanel());
  assert.equal(presets.length, 2);
  assert.equal(presets[0].actionId, "creation.preset");
  assert.deepEqual(presets[0].payload, { preset_key: "human_wanderer" });
  assert.equal(presets[1].presetKey, "elf_guardian");
});

test("disabled empty preset list stays focusable and submits nothing", () => {
  const empty = CreationMenu.presetItems(validPanel({ presets: [] }));
  assert.equal(empty.length, 1);
  assert.equal(empty[0].enabled, false);
  assert.equal(empty[0].actionId, null);
});

test("profile resolution follows race and subrace selection", () => {
  const panel = validPanel();
  const human = CreationMenu.profileFor(panel, "human", "human_commoner");
  assert.equal(human.budget, 181);
  const fionnen = CreationMenu.profileFor(panel, "elf", "fionnen");
  assert.equal(fionnen.budget, 37);
  assert.equal(CreationMenu.profileFor(panel, "human", null), null);
  assert.equal(CreationMenu.profileFor(panel, "human", "fionnen"), null);
});

test("race and subrace geometry derive from the descriptor", () => {
  const panel = validPanel();
  assert.equal(CreationMenu.raceOptions(panel).length, 2);
  const humanSubraces = CreationMenu.subraceOptions(panel, "human");
  assert.equal(humanSubraces.length, 2);
  assert.equal(humanSubraces[0].display_name_zh, "王族");
  const elfSubraces = CreationMenu.subraceOptions(panel, "elf");
  assert.equal(elfSubraces.length, 2);
  assert.equal(elfSubraces[0].display_name_zh, "斐歐恩族");
  const items = CreationMenu.subraceItems(panel, { raceKey: "elf", subraceKey: null });
  assert.equal(items.length, 2);
  assert.equal(items[0].subraceKey, "fionnen");
  assert.equal(items[1].subraceKey, "ciaran");
});

test("axis fields and budget follow the active profile", () => {
  const panel = validPanel();
  const state = CreationMenu.defaultCustomState(panel);
  state.subraceKey = "human_commoner";
  assert.equal(CreationMenu.budgetFor(panel, state), 181);
  const fields = CreationMenu.axisFields(panel, state);
  assert.equal(fields.length, 6);
  const hp = fields.find((f) => f.axis === "hp");
  assert.deepEqual({ min: hp.minimum, max: hp.maximum }, { min: 0, max: 100 });
});

test("the allocation briefing mirrors the server profile exactly", () => {
  const panel = validPanel();
  const humanState = CreationMenu.defaultCustomState(panel);
  humanState.subraceKey = "human_commoner";
  const humanProfile = CreationMenu.profileFor(panel, "human", "human_commoner");
  const humanBriefing = CreationMenu.briefingFor(panel, humanState);
  assert.equal(humanBriefing.budget, humanProfile.budget);
  assert.equal(humanBriefing.axisCount, humanProfile.axes.length);
  humanBriefing.spans.forEach((span, index) => {
    const axis = humanProfile.axes[index];
    assert.equal(span.axis, axis.axis);
    assert.equal(span.minimum, axis.minimum);
    assert.equal(span.maximum, axis.maximum);
  });
  assert.equal(humanBriefing.rule, "六項配點總和必須恰好等於 " + humanProfile.budget + "。");
  // A subrace with no profile resolves to no briefing.
  assert.equal(CreationMenu.briefingFor(panel, { raceKey: "human", subraceKey: null }), null);
});

test("advisory validation flags underage, name, and budget errors", () => {
  const panel = validPanel();
  const state = CreationMenu.defaultCustomState(panel);
  state.displayName = "新角色";
  state.age = "20";
  state.apparentAge = "20";
  state.subraceKey = "human_commoner";
  Object.assign(state.allocations, { hp: "50", mp: "50", sp: "50", atk_phys: "10", agility: "10", defense: "11" });
  assert.equal(CreationMenu.validateCustom(panel, state).valid, true);

  const underage = Object.assign({}, state, { age: "17" });
  const result = CreationMenu.validateCustom(panel, underage);
  assert.equal(result.valid, false);
  assert.ok(result.errors.age);

  const offBudget = Object.assign({}, state);
  offBudget.allocations = Object.assign({}, state.allocations, { hp: "0" });
  assert.equal(CreationMenu.validateCustom(panel, offBudget).valid, false);

  const noSubrace = Object.assign({}, state, { subraceKey: null });
  const missing = CreationMenu.validateCustom(panel, noSubrace);
  assert.equal(missing.valid, false);
  assert.ok(missing.errors.subrace);
});

test("exact custom payload production", () => {
  const panel = validPanel();
  const state = CreationMenu.defaultCustomState(panel);
  state.displayName = "  新角色  ";
  state.age = "20";
  state.apparentAge = "24";
  state.raceKey = "elf";
  state.subraceKey = "fionnen";
  state.background = "  在公會登記的新人冒險者  ";
  Object.assign(state.allocations, { hp: "0", mp: "0", sp: "0", atk_phys: "12", agility: "12", defense: "13" });
  const payload = CreationMenu.customPayload(state);
  assert.deepEqual(payload, {
    display_name: "新角色",
    age: 20,
    apparent_age: 24,
    race: "elf",
    subrace: "fionnen",
    background: "在公會登記的新人冒險者",
    affinity_elements: [],
    allocations: { hp: 0, mp: 0, sp: 0, atk_phys: 12, agility: 12, defense: 13 },
  });
});

test("saved custom draft restores the form at the saved stage", () => {
  const panel = validPanel({
    draft: {
      mode: "custom",
      stage: "custom_filled",
      display_name: "露芙",
      age: 22,
      apparent_age: 22,
      race: "elf",
      subrace: "ciaran",
      allocations: { hp: 0, mp: 0, sp: 0, atk_phys: 12, agility: 12, defense: 13 },
    },
  });
  const state = CreationMenu.stateFromDraft(panel, panel.draft);
  assert.equal(state.displayName, "露芙");
  assert.equal(state.age, "22");
  assert.equal(state.raceKey, "elf");
  assert.equal(state.subraceKey, "ciaran");
  assert.equal(state.allocations.defense, "13");
  assert.equal(CreationMenu.profileFor(panel, state.raceKey, state.subraceKey).budget, 37);
});

test("concept draft pre-fills finite controls without name or ages", () => {
  const panel = validPanel({
    draft: {
      mode: "concept",
      stage: "concept_filled",
      race: "elf",
      subrace: "fionnen",
      allocations: {
        hp: 0,
        mp: 0,
        sp: 0,
        atk_phys: 12,
        agility: 12,
        defense: 13,
      },
      background: null,
      background_generated: true,
    },
  });
  const state = CreationMenu.stateFromDraft(panel, panel.draft);
  assert.equal(state.displayName, "");
  assert.equal(state.age, "");
  assert.equal(state.apparentAge, "");
  assert.equal(state.raceKey, "elf");
  assert.equal(state.subraceKey, "fionnen");
  assert.equal(state.allocations.atk_phys, "12");
  assert.equal(CreationMenu.CONCEPT_ACTION, "creation.concept");
});

test("concept draft restores a preserved background for the continued form", () => {
  const panel = validPanel({
    draft: {
      mode: "concept",
      stage: "concept_filled",
      race: "elf",
      subrace: "fionnen",
      allocations: {
        hp: 0,
        mp: 0,
        sp: 0,
        atk_phys: 12,
        agility: 12,
        defense: 13,
      },
      background: "在公會登記的新人冒險者",
      background_generated: true,
    },
  });
  const state = CreationMenu.stateFromDraft(panel, panel.draft);
  assert.equal(state.background, "在公會登記的新人冒險者");
  const payload = CreationMenu.customPayload(state);
  assert.equal(payload.background, "在公會登記的新人冒險者");
});

test("no draft produces the pristine default custom state", () => {
  const panel = validPanel();
  const state = CreationMenu.stateFromDraft(panel, null);
  assert.equal(state.displayName, "");
  assert.equal(state.raceKey, "human");
  assert.equal(state.subraceKey, null);
  assert.deepEqual(state.affinityElements, []);
});

test("affinity picker derives race bounds and choices from the descriptor", () => {
  const panel = validPanel();
  assert.equal(CreationMenu.affinityMaximum(panel, "human"), 2);
  assert.equal(CreationMenu.affinityMaximum(panel, "beastfolk"), 1);
  assert.equal(CreationMenu.affinityMaximum(panel, "elf"), 0);
  assert.equal(CreationMenu.affinityElementKeys(panel, "human").length, 8);
  assert.deepEqual(
    CreationMenu.affinityChoice(panel, "human", "fire"),
    { key: "fire", label: "fire" }
  );
  assert.equal(CreationMenu.affinityItems(panel, "human").length, 8);
  assert.equal(CreationMenu.affinityItems(panel, "human")[0].affinityKey, "fire");
});

test("affinity toggle and selection mirror the draft state", () => {
  const state = CreationMenu.defaultCustomState(validPanel());
  CreationMenu.toggleAffinity(state, "fire");
  assert.equal(CreationMenu.affinitySelected(state, "fire"), true);
  CreationMenu.toggleAffinity(state, "wind");
  assert.deepEqual(state.affinityElements, ["fire", "wind"]);
  CreationMenu.toggleAffinity(state, "fire");
  assert.deepEqual(state.affinityElements, ["wind"]);
  assert.equal(CreationMenu.customPayload(state).affinity_elements.length, 1);
});

test("saved custom draft restores the affinity set", () => {
  const panel = validPanel({
    draft: {
      mode: "custom",
      stage: "custom_filled",
      display_name: "薇歐蕾特",
      age: 18,
      apparent_age: 18,
      race: "human",
      subrace: "human_royal",
      allocations: { hp: 0, mp: 0, sp: 0, atk_phys: 12, agility: 12, defense: 13 },
      background: null,
      background_generated: false,
      affinity_elements: ["fire", "wind"],
    },
  });
  const state = CreationMenu.stateFromDraft(panel, panel.draft);
  assert.deepEqual(state.affinityElements, ["fire", "wind"]);
});

test("confirmation screens gate activation", () => {
  const preset = CreationMenu.activateConfirm("human_wanderer");
  assert.equal(preset.items[0].actionId, "creation.activate");
  assert.deepEqual(preset.items[0].payload, {});
  assert.equal(preset.items[1].label, "取消");
  const custom = CreationMenu.activateConfirm(null);
  assert.match(custom.items[0].label, /確認建立/);
});

test("buildMenus exposes root and preset menus from the panel", () => {
  const model = CreationMenu.buildMenus(validPanel());
  assert.equal(model.menus.root.items.length, 3);
  assert.equal(model.menus.presets.items.length, 2);
});
