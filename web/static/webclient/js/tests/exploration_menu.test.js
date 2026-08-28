/*
 * DOM-independent tests for the exploration-menu model.
 *
 * Runs with Node 24's built-in test runner; no npm packages. Covers root
 * routing, move/look/interact submenus, scripted keyword buttons, the free-form
 * flow, disabled-row non-submission, and the navigate-kind service affordance
 * being dock-navigation only (never submitted as an action).
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const ExplorationMenu = require("../elosern/exploration_menu.js");

function validPanel(overrides) {
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
      look: {
        room: { identity: 3, display_name: "南門", room: true },
        entities: [{ identity: 5, display_name: "南門守衛", kind: "npc", portrait_ref: null }],
        objects: [{ identity: 6, display_name: "木箱" }],
      },
      interact: [
        {
          identity: 5,
          display_name: "南門守衛",
          portrait_ref: null,
          affordances: [
            {
              kind: "action",
              action_id: "explore.talk_scripted",
              label: "交談",
              enabled: true,
              disabled_reason: null,
            },
            {
              kind: "navigate",
              surface: "guild",
              label: "公會服務",
              enabled: true,
              disabled_reason: null,
            },
          ],
          keywords: [
            { keyword_id: "公會", label: "公會" },
            { keyword_id: "再見", label: "再見" },
          ],
        },
      ],
      character: { available: true },
      quests: { available: true },
      inventory: { available: true },
    },
    overrides || {}
  );
}

test("root routes Move/Look/Interact/Character plus available quests and inventory", () => {
  const model = ExplorationMenu.buildMenus(validPanel(), { currentNode: "room:3" });
  const keys = model.menus.root.items.map((item) => item.key);
  assert.deepEqual(keys, ["move", "look", "interact", "character", "quests", "inventory", "wait"]);
  // The 背包 root row is a frameless drawer open (the 角色 row precedent):
  // the exact shape carries openDrawer and no submenu/service-submenu field.
  const inventory = model.menus.root.items.find((item) => item.key === "inventory");
  assert.deepEqual(inventory, {
    key: "inventory",
    label: "背包",
    enabled: true,
    actionId: null,
    payload: null,
    openDrawer: "inventory",
  });
});

test("quests and inventory are omitted when the services capability is absent", () => {
  const model = ExplorationMenu.buildMenus(
    validPanel({ quests: { available: false }, inventory: { available: false } }),
    {}
  );
  const keys = model.menus.root.items.map((item) => item.key);
  assert.deepEqual(keys, ["move", "look", "interact", "character", "wait"]);
});

test("move rows carry the exit_ref and canonical current_node payload", () => {
  const model = ExplorationMenu.buildMenus(validPanel(), { currentNode: "room:3" });
  const moveItem = model.menus.move.items[0];
  assert.equal(moveItem.enabled, true);
  assert.equal(moveItem.actionId, "explore.move");
  assert.deepEqual(moveItem.payload, { exit_ref: "42", current_node: "room:3" });
});

test("a locked exit row is disabled and never submits", () => {
  const panel = validPanel({
    move: [
      {
        exit_ref: "42",
        label: "東",
        destination: "room:7",
        enabled: false,
        disabled_reason: { code: "locked", message: "此出口目前無法通行。" },
      },
    ],
  });
  const model = ExplorationMenu.buildMenus(panel, { currentNode: "room:3" });
  const moveItem = model.menus.move.items[0];
  assert.equal(moveItem.enabled, false);
  assert.equal(moveItem.actionId, null);
  assert.equal(moveItem.description, "此出口目前無法通行。");
});

test("move rows disable without the local-map current_node", () => {
  const model = ExplorationMenu.buildMenus(validPanel(), { currentNode: null });
  const moveItem = model.menus.move.items[0];
  assert.equal(moveItem.enabled, false);
  assert.equal(moveItem.actionId, null);
});

test("look items cover the room marker plus entities and objects", () => {
  const model = ExplorationMenu.buildMenus(validPanel(), {});
  const keys = model.menus.look.items.map((item) => item.key);
  assert.deepEqual(keys, ["look-room", "entity-5", "object-6", "back"]);
  assert.deepEqual(model.menus.look.items[0].payload, { room: true });
  assert.deepEqual(model.menus.look.items[1].payload, { target_id: 5 });
  assert.deepEqual(model.menus.look.items[2].payload, { target_id: 6 });
});

test("every exploration submenu ends with an enabled back row", () => {
  const model = ExplorationMenu.buildMenus(validPanel(), { currentNode: "room:3" });
  ["move", "look", "interact", "wait"].forEach((key) => {
    const items = model.menus[key].items;
    const back = items[items.length - 1];
    assert.equal(back.key, "back", `${key} must end with the back row`);
    assert.equal(back.label, "返回上一層");
    assert.equal(back.enabled, true);
    assert.equal(back.goBack, true);
    assert.equal(back.actionId, null, "the back row never submits an action");
  });
  // Dynamic menus (target affordances, scripted keywords) also end with it.
  const target = ExplorationMenu.targetById(model, 5);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  assert.equal(targetMenu.items[targetMenu.items.length - 1].key, "back");
  const scripted = ExplorationMenu.scriptedAffordanceFor(target);
  const keywordMenu = ExplorationMenu.keywordMenuFor(model, target, scripted);
  assert.equal(keywordMenu.items[keywordMenu.items.length - 1].key, "back");
});

test("the root menu never gains a back row", () => {
  const model = ExplorationMenu.buildMenus(validPanel(), {});
  const keys = model.menus.root.items.map((item) => item.key);
  assert.deepEqual(keys, ["move", "look", "interact", "character", "quests", "inventory", "wait"]);
  assert.ok(keys.indexOf("back") === -1);
});

test("parentKeyFor maps every submenu key to its parent", () => {
  assert.equal(ExplorationMenu.parentKeyFor("move"), "root");
  assert.equal(ExplorationMenu.parentKeyFor("look"), "root");
  assert.equal(ExplorationMenu.parentKeyFor("interact"), "root");
  assert.equal(ExplorationMenu.parentKeyFor("wait"), "root");
  assert.equal(ExplorationMenu.parentKeyFor("target-5"), "interact");
  assert.equal(ExplorationMenu.parentKeyFor("keywords-5"), "target-5");
  assert.equal(ExplorationMenu.parentKeyFor("root"), "root");
  assert.equal(ExplorationMenu.parentKeyFor("unknown-key"), "root");
});

test("menu models carry the mockup grid geometry", () => {
  const model = ExplorationMenu.buildMenus(validPanel(), { currentNode: "room:3" });
  assert.equal(model.menus.root.grid, true);
  assert.equal(model.menus.root.gridCols, 7);
  // The move frame navigates as a single-column list: its keyboard geometry
  // carries no fixed column count (the rendered exit-outlet grid is
  // width-adaptive, so the DOM-independent router assumes no column count).
  assert.equal(model.menus.move.grid, true, "move must be a grid");
  assert.equal(model.menus.move.gridCols, null, "move must use no fixed column count");
  ["look", "interact", "wait"].forEach((key) => {
    assert.equal(model.menus[key].grid, true, `${key} must be a grid`);
    assert.equal(model.menus[key].gridCols, 2, `${key} must use 2 columns`);
  });
  const target = ExplorationMenu.targetById(model, 5);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  assert.equal(targetMenu.gridCols, 2);
  const scripted = ExplorationMenu.scriptedAffordanceFor(target);
  const keywordMenu = ExplorationMenu.keywordMenuFor(model, target, scripted);
  assert.equal(keywordMenu.gridCols, 2);
});

test("interact targets open their server-authored affordances", () => {
  const model = ExplorationMenu.buildMenus(validPanel(), {});
  const targetItem = model.menus.interact.items[0];
  assert.equal(targetItem.enabled, true);
  assert.equal(targetItem.openTarget, 5);
});

test("a target with no affordances is disabled", () => {
  const panel = validPanel({
    interact: [{ identity: 8, display_name: "路人", portrait_ref: null, affordances: [] }],
  });
  const model = ExplorationMenu.buildMenus(panel, {});
  const targetItem = model.menus.interact.items[0];
  assert.equal(targetItem.enabled, false);
  assert.equal(targetItem.actionId, null);
});

test("the navigate-kind service affordance is dock-navigation only, never an action", () => {
  const model = ExplorationMenu.buildMenus(validPanel(), {});
  const target = ExplorationMenu.targetById(model, 5);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const service = targetMenu.items.find((item) => item.key === "service-guild");
  assert.ok(service);
  assert.equal(service.enabled, true);
  assert.equal(service.actionId, null);
  assert.equal(service.payload, null);
  assert.equal(service.openServiceSubmenu, "guild");
});

test("scripted keyword buttons submit explore.talk_scripted with the server IDs", () => {
  const model = ExplorationMenu.buildMenus(validPanel(), {});
  const target = ExplorationMenu.targetById(model, 5);
  const scripted = ExplorationMenu.scriptedAffordanceFor(target);
  assert.ok(scripted);
  const keywordMenu = ExplorationMenu.keywordMenuFor(model, target, scripted);
  const keywordKeys = keywordMenu.items.map((item) => item.key);
  assert.deepEqual(keywordKeys, ["kw-公會", "kw-再見", "back"]);
  assert.deepEqual(keywordMenu.items[0].payload, { npc_id: 5, keyword_id: "公會" });
  assert.equal(keywordMenu.items[0].actionId, "explore.talk_scripted");
});

test("free-form dialogue keeps the server-held target reference", () => {
  const panel = validPanel({
    interact: [
      {
        identity: 9,
        display_name: "吟遊詩人",
        portrait_ref: null,
        affordances: [
          {
            kind: "action",
            action_id: "explore.talk_freeform",
            label: "自由交談",
            enabled: true,
            disabled_reason: null,
          },
        ],
      },
    ],
  });
  const model = ExplorationMenu.buildMenus(panel, {});
  const target = ExplorationMenu.targetById(model, 9);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const freeform = targetMenu.items.find((item) => item.key === "talk-freeform");
  assert.ok(freeform);
  assert.equal(freeform.freeform, true);
  assert.equal(freeform.npcId, 9);
  assert.equal(freeform.actionId, null);
});

test("engage submits explore.engage only when enabled", () => {
  const panel = validPanel({
    interact: [
      {
        identity: 10,
        display_name: "哥布林",
        portrait_ref: null,
        affordances: [
          {
            kind: "action",
            action_id: "explore.engage",
            label: "戰鬥",
            enabled: true,
            disabled_reason: null,
          },
        ],
      },
    ],
  });
  const model = ExplorationMenu.buildMenus(panel, {});
  const target = ExplorationMenu.targetById(model, 10);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const engage = targetMenu.items.find((item) => item.key === "engage");
  assert.equal(engage.actionId, "explore.engage");
  assert.deepEqual(engage.payload, { monster_id: 10 });
});

test("party invite submits explore.party_invite with the server NPC id", () => {
  const panel = validPanel({
    interact: [
      {
        identity: 11,
        display_name: "艾洛希雅",
        portrait_ref: null,
        affordances: [
          {
            kind: "action",
            action_id: "explore.party_invite",
            label: "邀請",
            enabled: true,
            disabled_reason: null,
          },
        ],
      },
    ],
  });
  const model = ExplorationMenu.buildMenus(panel, {});
  const target = ExplorationMenu.targetById(model, 11);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const invite = targetMenu.items.find((item) => item.key === "party-invite");
  assert.equal(invite.actionId, "explore.party_invite");
  assert.deepEqual(invite.payload, { npc_id: 11, message: "" });
});

test("a disabled party invite keeps its reason and never submits", () => {
  const panel = validPanel({
    interact: [
      {
        identity: 11,
        display_name: "艾洛希雅",
        portrait_ref: null,
        affordances: [
          {
            kind: "action",
            action_id: "explore.party_invite",
            label: "邀請",
            enabled: false,
            disabled_reason: { code: "party_full", message: "你的隊伍已經滿了（最多 4 人）。" },
          },
        ],
      },
    ],
  });
  const model = ExplorationMenu.buildMenus(panel, {});
  const target = ExplorationMenu.targetById(model, 11);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const invite = targetMenu.items.find((item) => item.key === "party-invite");
  assert.equal(invite.enabled, false);
  assert.equal(invite.actionId, null);
  assert.equal(invite.payload, null);
  assert.match(invite.description, /滿/);
});

test("party leave submits explore.party_leave with the server NPC id", () => {
  const panel = validPanel({
    interact: [
      {
        identity: 12,
        display_name: "艾洛希雅",
        portrait_ref: null,
        affordances: [
          {
            kind: "action",
            action_id: "explore.party_leave",
            label: "解散",
            enabled: true,
            disabled_reason: null,
          },
        ],
      },
    ],
  });
  const model = ExplorationMenu.buildMenus(panel, {});
  const target = ExplorationMenu.targetById(model, 12);
  const targetMenu = ExplorationMenu.targetMenuFor(model, target);
  const leave = targetMenu.items.find((item) => item.key === "party-leave");
  assert.equal(leave.actionId, "explore.party_leave");
  assert.deepEqual(leave.payload, { npc_id: 12 });
});
