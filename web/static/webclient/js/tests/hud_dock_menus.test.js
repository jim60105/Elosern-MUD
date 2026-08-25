/*
 * DOM-independent tests for the H3 webclient-hud-03-action-dock menu
 * additions (task 2.8): the router breadcrumb trail, menu titles on every
 * stackable frame, the suggestions frame's four statuses, the combat
 * category/group skill frames (single-subgroup collapse), and the corrected
 * root geometry (root gridCols equals the item count).
 *
 * Runs with Node 24's built-in test runner; no npm packages.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const KeyboardRouter = require("../elosern/keyboard_router.js");
const ExplorationMenu = require("../elosern/exploration_menu.js");
const CombatMenu = require("../elosern/combat_menu.js");
const ServiceMenu = require("../elosern/service_menu.js");
const CreationMenu = require("../elosern/creation_menu.js");
const CharacterMenu = require("../elosern/character_menu.js");

// ---------------------------------------------------------------- fixtures

function explorationPanel(overrides) {
  return Object.assign(
    {
      schema_version: 1,
      available: true,
      kind: "exploration",
      move: [
        {
          exit_ref: "42",
          label: "東",
          destination: "room:7",
          enabled: true,
          disabled_reason: null,
        },
      ],
      look: { room: null, entities: [], objects: [] },
      interact: [],
      character: { available: true },
      quests: { available: true },
      inventory: { available: true },
    },
    overrides || {}
  );
}

function combatPanel(overrides) {
  return Object.assign(
    {
      schema_version: 5,
      available: true,
      kind: "combat",
      session: {
        session_id: "hostile:1:0",
        mode: "hostile",
        round: 0,
        state: "ready",
        reason: null,
      },
      participants: [
        {
          identity: 2,
          token: "e1",
          display_name: "哥布林",
          team: "foes",
          state: "active",
          hp_current: 100,
          hp_maximum: 100,
          portrait_ref: null,
        },
      ],
      root_actions: ["attack", "skills", "items", "defend", "flee"],
      secondary_actions: ["forfeit"],
      skills: [
        {
          category: "elemental_magic",
          label: "元素魔法",
          groups: [
            {
              group: "fire",
              label: "火",
              skills: [
                {
                  key: "fire_ball",
                  label: "火球術",
                  description: "凝聚火焰魔力，對單一敵人造成魔法傷害。",
                  cost: { mp: 20 },
                  target_spec: "single",
                  element: "fire",
                  enabled: true,
                  disabled_reason: null,
                  targets: [2],
                  shorthands: [],
                  freeform_scales: [
                    { scale: 0.5, label: "小", mp_cost: 10 },
                    { scale: 1, label: "中", mp_cost: 20 },
                    { scale: 2, label: "大", mp_cost: 40 },
                  ],
                },
              ],
            },
            {
              group: "water",
              label: "水",
              skills: [
                {
                  key: "ice_arrow",
                  label: "冰箭術",
                  description: "凝聚冰魔力，對單一敵人造成魔法傷害。",
                  cost: { mp: 15 },
                  target_spec: "single",
                  element: "ice",
                  enabled: true,
                  disabled_reason: null,
                  targets: [2],
                  shorthands: [],
                },
              ],
            },
          ],
        },
      ],
      suggestions: { status: "unavailable" },
    },
    overrides || {}
  );
}

function suggestionsEnvelope(status, cards) {
  return { status: status, cards: cards || [] };
}

// ---------------------------------------------------------------- trail

test("router.trail() lists every stacked frame title in push order", () => {
  const router = KeyboardRouter.createRouter({ onEvent: () => {} });
  router.reset({
    items: [KeyboardRouter.menuItem("戰鬥", true), KeyboardRouter.menuItem("技能", true)],
    grid: true,
    gridCols: 2,
    title: "戰鬥",
  });
  router.pushMenu({
    items: [KeyboardRouter.menuItem("元素魔法", true)],
    grid: true,
    gridCols: 1,
    title: "元素魔法",
  });
  assert.deepEqual(router.trail(), ["戰鬥", "元素魔法"]);
  assert.equal(router.depth(), 2);
  router.press(KeyboardRouter.ESCAPE);
  assert.deepEqual(router.trail(), ["戰鬥"]);
  assert.equal(router.depth(), 1);
  router.reset();
  assert.deepEqual(router.trail(), []);
});

// ---------------------------------------------------------------- titles

test("exploration menus carry fixed breadcrumb titles", () => {
  const model = ExplorationMenu.buildMenus(explorationPanel(), {
    currentNode: "room:3",
    suggestions: suggestionsEnvelope("unavailable"),
  });
  assert.equal(model.menus.root.title, "探索");
  assert.equal(model.menus.move.title, "移動");
  assert.equal(model.menus.look.title, "查看");
  assert.equal(model.menus.interact.title, "互動");
  assert.equal(model.menus.wait.title, "等待");
});

test("combat menus carry fixed breadcrumb titles", () => {
  const combat = CombatMenu.buildMenus(combatPanel(), {});
  assert.equal(combat.menus.root.title, "戰鬥");
  assert.equal(combat.menus.categories.title, "技能");
  assert.equal(combat.menus.forfeit.title, "投降");
  const category = CombatMenu.openCategory(combat, 0);
  // Two groups: the category opens the group frame.
  assert.equal(category.title, "元素魔法");
  const group = CombatMenu.openGroup(combat, 0, 0);
  assert.equal(group.title, "火");
  const scale = CombatMenu.openSkill(combat, "fire_ball");
  assert.equal(scale.title, "威力");
  const target = CombatMenu.openSkillTargets(combat, "fire_ball");
  assert.equal(target.title, "目標");
});

test("service menus carry fixed breadcrumb titles", () => {
  const model = ServiceMenu.buildMenus({
    schema_version: 1,
    available: true,
    guild: { registration: { registered: false }, board: [] },
    shop: { stock: [] },
  });
  const menus = model.menus;
  assert.equal(menus.root.title, "服務");
  assert.equal(menus.guild.title, "公會");
  assert.equal(menus.shop.title, "商店");
  assert.equal(menus.board.title, "任務板");
  assert.equal(menus.quests.title, "任務記錄");
  assert.equal(menus.inventory.title, "背包");
});

test("creation and character menus carry fixed breadcrumb titles", () => {
  const creation = CreationMenu.buildMenus({
    schema_version: 1,
    available: true,
    presets: [],
  });
  assert.equal(creation.menus.root.title, "建角");
  assert.equal(creation.menus.presets.title, "預設角色");

  const character = CharacterMenu.buildMenu({
    schema_version: 1,
    available: true,
    traits: [{ label: "HP", current: 100, max: 100 }],
    wallet: 1234,
  });
  assert.equal(character.title, "角色狀態");
  // The wallet row renders as display-only copper text.
  const walletRow = character.items.find((item) => item.key === "wallet");
  assert.equal(walletRow.label, "錢包：1234 銅");
});

// ---------------------------------------------------------------- suggestions frame

test("suggestions frame: generating shows one disabled row", () => {
  const menu = ExplorationMenu.suggestionsMenu(suggestionsEnvelope("generating"));
  assert.deepEqual(
    menu.items.map((item) => item.key),
    ["suggestions-generating", "back"]
  );
  assert.equal(menu.items[0].enabled, false);
  assert.equal(menu.gridCols, menu.items.length);
  assert.equal(menu.title, "建議");
});

test("suggestions frame: ready lists card rows plus dismiss", () => {
  const cards = [
    {
      kind: "known_action",
      action_code: "explore.look",
      params: {},
      label: "查看房間",
      hint: null,
    },
    { kind: "freeform", params: { npc_id: 5 }, label: "和南門守衛交談", hint: null },
  ];
  const menu = ExplorationMenu.suggestionsMenu(suggestionsEnvelope("ready", cards));
  assert.deepEqual(
    menu.items.map((item) => item.key),
    ["action-explore.look", "action-explore.talk_freeform", "action-options.dismiss", "back"]
  );
  assert.equal(menu.items[0].actionId, "explore.look");
  assert.equal(menu.items[1].actionId, "explore.talk_freeform");
  assert.deepEqual(menu.items[1].payload, { npc_id: 5, speech: "和南門守衛交談" });
  assert.equal(menu.items[2].actionId, "options.dismiss");
  assert.deepEqual(menu.items[2].payload, {});
  // The root entry appears for the non-unavailable statuses.
  const root = ExplorationMenu.rootItems(explorationPanel(), suggestionsEnvelope("ready", cards));
  const keys = root.map((item) => item.key);
  assert.ok(keys.includes("suggestions"));
  const suggItem = root.find((item) => item.key === "suggestions");
  assert.equal(suggItem.openSubmenu, "suggestions");
});

test("suggestions frame: degraded with zero cards keeps the muted empty line", () => {
  const menu = ExplorationMenu.suggestionsMenu(suggestionsEnvelope("degraded"));
  assert.deepEqual(
    menu.items.map((item) => item.key),
    ["suggestions-empty", "action-options.dismiss", "back"]
  );
  assert.equal(menu.items[0].enabled, false);
});

test("suggestions unavailable: no root entry, no menu", () => {
  const root = ExplorationMenu.rootItems(explorationPanel(), suggestionsEnvelope("unavailable"));
  assert.ok(!root.some((item) => item.key === "suggestions"));
  const model = ExplorationMenu.buildMenus(explorationPanel(), {
    currentNode: "room:3",
    suggestions: suggestionsEnvelope("unavailable"),
  });
  assert.equal(model.menus.suggestions, undefined);
});

// ---------------------------------------------------------------- geometry

test("root geometry: gridCols equals the item count (single-row tab bar)", () => {
  const model = ExplorationMenu.buildMenus(explorationPanel(), {
    currentNode: "room:3",
    suggestions: suggestionsEnvelope("ready", [
      { kind: "known_action", action_code: "explore.look", params: {}, label: "查看房間" },
    ]),
  });
  const root = model.menus.root;
  // 5 base entries + 2 available services + 1 suggestions entry = 8.
  assert.equal(root.gridCols, root.items.length);
  assert.equal(root.items.length, 8);
  assert.equal(root.grid, true);

  const combat = CombatMenu.buildMenus(combatPanel(), {});
  const combatRoot = combat.menus.root;
  assert.equal(combatRoot.gridCols, combatRoot.items.length);
  assert.equal(combatRoot.items.length, 6);

  const recoveryRoot = CombatMenu.rootItems(
    combatPanel({
      session: {
        session_id: "hostile:1:0",
        mode: "hostile",
        round: 0,
        state: "recovery",
        reason: "defeated",
      },
    })
  );
  assert.equal(recoveryRoot.length, 1);
});

// ---------------------------------------------------------------- category/group frames

test("category frame: one row per skill category badged with the skill count", () => {
  const combat = CombatMenu.buildMenus(combatPanel(), {});
  const cats = CombatMenu.categoryItems(combat.panel);
  assert.deepEqual(cats.map((item) => item.key), ["skill-cat-0"]);
  assert.equal(cats[0].label, "元素魔法");
  assert.equal(cats[0].actionId, "open-category");
  assert.deepEqual(cats[0].payload, { categoryIndex: 0 });
  assert.equal(cats[0].skillCount, 2);
  // The skills tab pushes the category frame.
  assert.ok(combat.menus.categories);
  assert.equal(combat.menus.categories.items.length, 1);
});

test("openCategory: a single-sub-group category collapses straight to the skill frame", () => {
  const panel = combatPanel({
    skills: [
      {
        category: "elemental_magic",
        label: "元素魔法",
        groups: [
          {
            group: "fire",
            label: "火",
            skills: [
              {
                key: "fire_ball",
                label: "火球術",
                description: "凝聚火焰魔力，對單一敵人造成魔法傷害。",
                cost: { mp: 20 },
                target_spec: "single",
                element: "fire",
                enabled: true,
                disabled_reason: null,
                targets: [2],
                shorthands: [],
              },
            ],
          },
        ],
      },
    ],
  });
  const combat = CombatMenu.buildMenus(panel, {});
  const menu = CombatMenu.openCategory(combat, 0);
  // Single group: the frame is the group's skill frame (design D11).
  assert.equal(menu.title, "火");
  assert.equal(menu.gridCols, 1);
  assert.deepEqual(
    menu.items.map((item) => item.key),
    ["fire_ball"]
  );
  assert.equal(menu.items[0].actionId, "open-skill");
  assert.deepEqual(menu.items[0].payload, { skillKey: "fire_ball" });
});

test("openCategory: a multi-group category opens the group frame", () => {
  const combat = CombatMenu.buildMenus(combatPanel(), {});
  const menu = CombatMenu.openCategory(combat, 0);
  assert.equal(menu.title, "元素魔法");
  assert.deepEqual(
    menu.items.map((item) => item.key),
    ["skill-group-0-0", "skill-group-0-1"]
  );
  assert.deepEqual(menu.items[0].payload, { categoryIndex: 0, groupIndex: 0 });
  assert.deepEqual(menu.items[1].payload, { categoryIndex: 0, groupIndex: 1 });
  assert.equal(menu.gridCols, menu.items.length);

  const groupFrame = CombatMenu.openGroup(combat, 0, 1);
  assert.equal(groupFrame.title, "水");
  assert.deepEqual(
    groupFrame.items.map((item) => item.key),
    ["ice_arrow"]
  );
  assert.equal(groupFrame.gridCols, 1);
});

test("move rows expose normalized direction and destination node", () => {
  const panel = explorationPanel({
    move: [
      {
        exit_ref: "42",
        label: "東",
        destination: "room:7",
        enabled: true,
        disabled_reason: null,
      },
      {
        exit_ref: "43",
        label: "上",
        destination: "room:9",
        enabled: true,
        disabled_reason: null,
      },
      {
        exit_ref: "44",
        label: "大廳門",
        destination: "room:11",
        enabled: true,
        disabled_reason: null,
      },
    ],
  });
  const items = ExplorationMenu.moveItems(panel, "room:3");
  assert.equal(items[0].direction, "east");
  assert.equal(items[0].destination, "room:7");
  assert.equal(items[1].direction, "up");
  assert.equal(items[1].destination, "room:9");
  // A named door label normalizes to null (the renderer shows it verbatim).
  assert.equal(items[2].direction, null);
  assert.equal(items[2].destination, "room:11");
  // The payload always carries the canonical current_node.
  assert.deepEqual(items[0].payload, { exit_ref: "42", current_node: "room:3" });

  // normalizeDirection unit behavior.
  assert.equal(ExplorationMenu.normalizeDirection("北"), "north");
  assert.equal(ExplorationMenu.normalizeDirection("NE"), "northeast");
  assert.equal(ExplorationMenu.normalizeDirection("下"), "down");
  assert.equal(ExplorationMenu.normalizeDirection("大廳門"), null);
});
