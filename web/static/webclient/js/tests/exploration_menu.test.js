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
  assert.deepEqual(keys, ["look-room", "entity-5", "object-6"]);
  assert.deepEqual(model.menus.look.items[0].payload, { room: true });
  assert.deepEqual(model.menus.look.items[1].payload, { target_id: 5 });
  assert.deepEqual(model.menus.look.items[2].payload, { target_id: 6 });
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
  assert.deepEqual(keywordKeys, ["kw-公會", "kw-再見"]);
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
