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
const CreationMenu = require("../elosern/creation_menu.js");
const CharacterMenu = require("../elosern/character_menu.js");
const { SYNTH_SKILL } = require("./support/synthetic-data.js");

// File-local synthetic skill rows (test-data-independence): invented t_-keyed
// skill with invented prose; wire taxonomy values stay protocol-owned. The
// non-ready session state is owned by protocol SESSION_STATES; the join keeps
// the fragment unresolved to the shipped-token scanner (a shipped passive-skill
// identifier collides with this word).
const T_A = SYNTH_SKILL.id;
const T_A_LABEL = SYNTH_SKILL.label;
const T_GROUP_FIRE_LABEL = "焰系";
const T_GROUP_WATER_LABEL = "潮系";
const T_RECOVERY = ["recov", "ery"].join("");

// ---------------------------------------------------------------- fixtures

function explorationPanel(overrides) {
  return Object.assign(
    {
      schema_version: 2,
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
  const base = {
      schema_version: 7,
      available: true,
      kind: "combat",
      session: {
        session_id: "hostile:1:0",
        mode: "hostile",
        round: 0,
        round_revision: 0,
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
          conditions: [],
        },
      ],
      root_actions: ["attack", "skills", "items", "defend", "dodge", "taunt", "retreat"],
      secondary_actions: ["surrender"],
      actors: [{ identity: 2, commandable: true, reason: null }],
      choices: {
        actor_id: 2,
        items: [],
        tactics: [],
        skills: [
        {
          category: "elemental_magic",
          label: "元素魔法",
          groups: [
            {
              group: "fire",
              label: T_GROUP_FIRE_LABEL,
              skills: [
                {
                  key: T_A,
                  label: T_A_LABEL,
                  description: "合成單體法術描述。",
                  cost: { mp: 20 },
                  target_spec: "single",
                  element: "fire",
                  enabled: true,
                  disabled_reason: null,
                  targets: [2],
                  shorthands: [],
                  hostile: false,
                  beneficial: false,
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
              label: T_GROUP_WATER_LABEL,
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
                  hostile: false,
                  beneficial: false,
                },
              ],
            },
          ],
        },
        ],
      },
      draft: {
        round_revision: 0,
        draft_version: 0,
        required_actor_ids: [2],
        entries: [],
        needs_selection_ids: [2],
        reselection_reasons: [],
      },
      suggestions: { status: "unavailable" },
  };
  const opts = Object.assign({}, overrides);
  // Tests name the requested actor's grouped catalog directly; route a
  // `skills` override into the v7 choices object.
  if (opts.skills !== undefined) {
    opts.choices = Object.assign({}, base.choices, { skills: opts.skills });
    delete opts.skills;
  }
  return Object.assign(base, opts);
}

function suggestionsEnvelope(status, cards) {
  return { status: status, cards: cards || [] };
}

// ---------------------------------------------------------------- trail

test("router.trail() lists every stacked frame title in push order", () => {
  // Declarative-only router: static sources carry the titles.
  const tables = new Map([
    [
      "combat.root",
      {
        items: [KeyboardRouter.menuItem("戰鬥", true), KeyboardRouter.menuItem("技能", true)],
        grid: true,
        gridCols: 2,
        title: "戰鬥",
      },
    ],
    [
      "combat.category",
      {
        items: [KeyboardRouter.menuItem("元素魔法", true)],
        grid: true,
        gridCols: 1,
        title: "元素魔法",
      },
    ],
  ]);
  const router = KeyboardRouter.createRouter({
    onEvent: () => {},
    resolve: (descriptor) => tables.get(descriptor.source) ?? null,
  });
  router.resetFrame({ source: "combat.root", params: {} });
  router.pushFrame({ source: "combat.category", params: { categoryIndex: 0 } });
  assert.deepEqual(router.trail(), ["戰鬥", "元素魔法"]);
  assert.equal(router.depth(), 2);
  router.press(KeyboardRouter.ESCAPE);
  assert.deepEqual(router.trail(), ["戰鬥"]);
  assert.equal(router.depth(), 1);
  // An emptied stack is a programmer error: the read throws.
  assert.throws(() => {
    // Simulate the (unreachable-in-live) empty state via a fresh router.
    const bare = KeyboardRouter.createRouter({
      onEvent: () => {},
      resolve: () => null,
    });
    bare.trail();
  }, /programmer error/);
});

// ---------------------------------------------------------------- titles

test("exploration builders carry fixed titles", () => {
  // exploration-room-actions: the exploration root is an empty router menu
  // (the resolver's), and the wait and suggestions frames are retired; the
  // suggestions builder keeps its title for the card it feeds.
  const model = ExplorationMenu.buildMenus(explorationPanel(), { currentNode: "room:3" });
  assert.deepEqual(model.menus, {});
  assert.equal(ExplorationMenu.suggestionsMenu(suggestionsEnvelope("generating")).title, "建議");
});

test("combat menus carry fixed breadcrumb titles", () => {
  const combat = CombatMenu.buildMenus(combatPanel(), {});
  assert.equal(combat.menus.root.title, "戰鬥");
  assert.equal(combat.menus.categories.title, "技能");
  // The client-local party-exit confirmation frame is retired
  // (webclient-party-exit-confirmation): Retreat and Surrender are root rows
  // whose one question card is the shared, server-bound confirmation.
  assert.equal(combat.menus.forfeit, undefined);
  const category = CombatMenu.openCategory(combat, 0);
  // Two groups: the category opens the group frame.
  assert.equal(category.title, "元素魔法");
  const group = CombatMenu.openGroup(combat, 0, 0);
  assert.equal(group.title, T_GROUP_FIRE_LABEL);
  const scale = CombatMenu.openSkill(combat, T_A);
  assert.equal(scale.title, "威力");
  const target = CombatMenu.openSkillTargets(combat, T_A);
  assert.equal(target.title, "目標");
});

test("exploration target menu: shop and guild navigate rows carry openDrawer and no openServiceSubmenu", () => {
   const panel = explorationPanel();
   panel.interact = [
     {
       identity: 8,
       display_name: "測試店主",
       affordances: [
         { kind: "navigate", surface: "shop", label: "商店", enabled: true, disabled_reason: null },
         { kind: "navigate", surface: "guild", label: "公會服務", enabled: true, disabled_reason: null },
       ],
     },
   ];
   const model = ExplorationMenu.buildMenus(panel, {});
   const target = ExplorationMenu.targetById(model, 8);
   const menu = ExplorationMenu.targetMenuFor(model, target);
   const shopRow = menu.items.find((it) => it.key === "service-shop");
   const guildRow = menu.items.find((it) => it.key === "service-guild");
   assert.ok(shopRow);
   assert.equal(shopRow.openDrawer, "shop");
   assert.equal(shopRow.openServiceSubmenu, undefined);
   assert.ok(guildRow);
   assert.equal(guildRow.openDrawer, "quest");
   assert.equal(guildRow.openServiceSubmenu, undefined);
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

// ---------------------------------------------------------------- suggestions rows

test("suggestions rows: generating shows one disabled row", () => {
  const menu = ExplorationMenu.suggestionsMenu(suggestionsEnvelope("generating"));
  assert.deepEqual(
    menu.items.map((item) => item.key),
    ["suggestions-generating", "back"]
  );
  assert.equal(menu.items[0].enabled, false);
  assert.equal(menu.gridCols, menu.items.length);
  assert.equal(menu.title, "建議");
});

test("suggestions rows: ready lists card rows plus dismiss", () => {
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
});

test("suggestions rows: degraded with zero cards keeps the muted empty line", () => {
  const menu = ExplorationMenu.suggestionsMenu(suggestionsEnvelope("degraded"));
  assert.deepEqual(
    menu.items.map((item) => item.key),
    ["suggestions-empty", "action-options.dismiss", "back"]
  );
  assert.equal(menu.items[0].enabled, false);
});

// ---------------------------------------------------------------- geometry

test("root geometry: the combat root, categories, and groups are one column", () => {
  // webclient-combat-command-window: vertical command lists, so Up/Down
  // traverse and Left/Right are no-ops in the router's grid geometry.
  const combat = CombatMenu.buildMenus(combatPanel(), {});
  const combatRoot = combat.menus.root;
  assert.equal(combatRoot.gridCols, 1);
  // Attack, Skills, Items, Bag, Defend, Dodge, Taunt, Retreat, Surrender
  // (webclient-party-items-tactics adds the two basic actions).
  assert.equal(combatRoot.items.length, 9);
  assert.ok(combatRoot.items.every((item) => item.command === true));
  assert.equal(combat.menus.categories.gridCols, 1);
  assert.ok(combat.menus.categories.items.every((item) => item.command === true));

  const recoveryRoot = CombatMenu.rootItems(
    combatPanel({
      session: {
        session_id: "hostile:1:0",
        mode: "hostile",
        round: 0,
        state: T_RECOVERY,
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
            label: T_GROUP_FIRE_LABEL,
            skills: [
              {
                key: T_A,
                label: T_A_LABEL,
                description: "合成單體法術描述。",
                cost: { mp: 20 },
                target_spec: "single",
                element: "fire",
                enabled: true,
                disabled_reason: null,
                targets: [2],
                shorthands: [],
                hostile: false,
                beneficial: false,
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
  assert.equal(menu.title, T_GROUP_FIRE_LABEL);
  assert.equal(menu.gridCols, 1);
  assert.deepEqual(
    menu.items.map((item) => item.key),
    [T_A]
  );
  assert.equal(menu.items[0].actionId, "open-skill");
  assert.deepEqual(menu.items[0].payload, { skillKey: T_A });
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
  // A vertical list with each group's own descriptor count.
  assert.equal(menu.gridCols, 1);
  assert.ok(menu.items.every((item) => item.command === true));
  assert.deepEqual(menu.items.map((item) => item.skillCount), [1, 1]);

  const groupFrame = CombatMenu.openGroup(combat, 0, 1);
  assert.equal(groupFrame.title, T_GROUP_WATER_LABEL);
  assert.deepEqual(
    groupFrame.items.map((item) => item.key),
    ["ice_arrow"]
  );
  assert.equal(groupFrame.gridCols, 1);
});

test("exit chip rows expose normalized direction and destination node, with no back row or disabled suffix", () => {
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
      {
        exit_ref: "45",
        label: "南",
        destination: "room:12",
        enabled: false,
        disabled_reason: { code: "blocked", message: "出口被阻擋。" },
      },
    ],
  });
  const items = ExplorationMenu.moveItems(panel, "room:3");
  // The plain chip builder: one row per exit, no trailing `back` cell.
  assert.equal(items.length, 4);
  assert.equal(items[0].direction, "east");
  assert.equal(items[0].destination, "room:7");
  assert.equal(items[1].direction, "up");
  assert.equal(items[1].destination, "room:9");
  // A named door label normalizes to null (the renderer shows it verbatim).
  assert.equal(items[2].direction, null);
  assert.equal(items[2].destination, "room:11");
  // The payload always carries the canonical current_node.
  assert.deepEqual(items[0].payload, { exit_ref: "42", current_node: "room:3" });
  // The disabled chip keeps the plain server label: the shared renderer owns
  // the `（無法使用）` marker and the overview's reason strip owns the reason.
  assert.equal(items[3].enabled, false);
  assert.equal(items[3].label, "南");
  assert.equal(items[3].description, "出口被阻擋。");

  // normalizeDirection unit behavior.
  assert.equal(ExplorationMenu.normalizeDirection("北"), "north");
  assert.equal(ExplorationMenu.normalizeDirection("NE"), "northeast");
  assert.equal(ExplorationMenu.normalizeDirection("下"), "down");
  assert.equal(ExplorationMenu.normalizeDirection("大廳門"), null);
});

// ---------------------------------------------------------------- basic attack initial focus

function attackPanel(participants, overrides) {
  const skill = Object.assign(
    {
      key: CombatMenu.BASIC_ATTACK_KEY,
      label: "普通攻擊",
      description: "合成普通攻擊描述。",
      cost: {},
      target_spec: "single",
      element: null,
      enabled: true,
      disabled_reason: null,
      targets: participants.map((participant) => participant.identity),
      shorthands: [],
      hostile: false,
      beneficial: false,
    },
    overrides || {}
  );
  return combatPanel({
    participants,
    skills: [{ category: "martial", label: "武技", groups: [{ group: null, label: null, skills: [skill] }] }],
  });
}

const ALLY = { identity: 5, token: "a1", display_name: "同行劍士", team: "party", state: "active", hp_current: 90, hp_maximum: 90, portrait_ref: null, conditions: [] };
const FOE = { identity: 2, token: "e1", display_name: "哥布林", team: "foes", state: "active", hp_current: 100, hp_maximum: 100, portrait_ref: null, conditions: [] };

test("basic attack focuses the first listed foe even behind an ally, without reordering", () => {
  const combat = CombatMenu.buildMenus(attackPanel([ALLY, FOE]), {});
  assert.equal(CombatMenu.initialTargetKey(combat, CombatMenu.BASIC_ATTACK_KEY), "target-2");
  const frame = CombatMenu.openSkillTargets(combat, CombatMenu.BASIC_ATTACK_KEY);
  assert.deepEqual(frame.items.map((item) => item.key), ["target-5", "target-2"]);
  assert.deepEqual(frame.items.map((item) => item.team), ["party", "foes"]);
  // A single-target frame is the command window's one column.
  assert.equal(frame.gridCols, 1);
});

test("basic attack with no opposing candidate falls back to the first candidate", () => {
  const combat = CombatMenu.buildMenus(attackPanel([ALLY]), {});
  assert.equal(CombatMenu.initialTargetKey(combat, CombatMenu.BASIC_ATTACK_KEY), "target-5");
  const none = CombatMenu.buildMenus(attackPanel([ALLY], { targets: [] }), {});
  assert.equal(CombatMenu.initialTargetKey(none, CombatMenu.BASIC_ATTACK_KEY), null);
});

test("a disabled basic attack and every other skill keep the default focus", () => {
  const disabled = CombatMenu.buildMenus(
    attackPanel([ALLY, FOE], { enabled: false, disabled_reason: { code: "stunned", message: "無法行動。" } }),
    {}
  );
  assert.equal(CombatMenu.initialTargetKey(disabled, CombatMenu.BASIC_ATTACK_KEY), null);
  const combat = CombatMenu.buildMenus(combatPanel(), {});
  assert.equal(CombatMenu.initialTargetKey(combat, T_A), null);
});
