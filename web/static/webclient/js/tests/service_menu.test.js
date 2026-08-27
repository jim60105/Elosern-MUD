/*
 * DOM-independent tests for the Elosern service-menu model.
 *
 * Covers surface routing, deterministic ordering, quantity-form validation,
 * destructive-abandon confirmation gating, disabled-row non-submission, and
 * server-string passthrough. Runs with Node's built-in test runner.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const ServiceMenu = require("../elosern/service_menu.js");

function action(overrides) {
  return Object.assign(
    {
      action_id: "guild.register",
      label: "註冊為冒險者",
      enabled: true,
      disabled_reason: null,
      quantity: null,
    },
    overrides || {}
  );
}

function validPanel(overrides) {
  const panel = {
    schema_version: 2,
    available: true,
    kind: "services",
    host: null,
    player: {
      wallet: 1000,
      guild_registered: false,
      guild_rank: null,
      guild_merit: 0,
      next_rank: null,
      next_threshold: null,
    },
    guild: {
      registration: { registered: false, register: action() },
      board: [
        {
          definition_key: "introductory_hunt",
          display_name: "討伐低階魔物",
          objective_summary: "討伐 1 隻低階魔物",
          reward_summary: "獎勵：銅 50、功績 25",
          rank: "F",
          accept: action({ action_id: "guild.quest_accept", label: "接取" }),
        },
      ],
      quests: [
        {
          quest_id: "introductory_hunt:1",
          definition_key: "introductory_hunt",
          display_name: "討伐低階魔物",
          state: "in_progress",
          stage_index: 0,
          stage_progress: 0,
          objective_summary: "討伐 1 隻低階魔物",
          deadline_line: null,
          detail: "討伐低階魔物\n狀態：進行中",
          abandon: action({ action_id: "guild.quest_abandon", label: "放棄" }),
          turnin: action({
            action_id: "guild.quest_turnin",
            label: "回報",
            enabled: false,
            disabled_reason: { code: "quest_transition", message: "尚未完成。" },
          }),
        },
      ],
      rank: null,
    },
    shop: {
      open: true,
      stock: [
        {
          item_key: "meal",
          display_name: "普通餐食",
          buy_copper: 10,
          sell_copper: 5,
          stock: 20,
          max_stock: 20,
          buy: action({
            action_id: "shop.buy",
            label: "購買",
            quantity: { min: 1, max: 20 },
          }),
        },
      ],
      sellable: [],
    },
    inventory: {
      rows: [
        {
          item_key: "meal",
          display_name: "普通餐食",
          held: 2,
          equipped: false,
          presentation: {
            kind: "food",
            icon_key: "food",
            rarity: "common",
            summary: "供旅人充飢的普通餐食。",
          },
        },
      ],
      wallet: 1000,
    },
    pagination: {
      board_total: 1,
      quest_total: 1,
      stock_total: 1,
      sellable_total: 0,
      inventory_total: 1,
    },
  };
  return Object.assign(panel, overrides || {});
}

test("surface routing preserves the stable guild, shop, inventory order", () => {
  const panel = validPanel();
  const model = ServiceMenu.buildMenus(panel);
  assert.deepEqual(model.surfaces, ["guild", "shop", "inventory"]);
  const keys = model.menus.root.items.map((item) => item.key);
  assert.deepEqual(keys, ["guild", "shop", "inventory"]);
});

test("a null surface is routed to a disabled non-submitting root item", () => {
  const panel = validPanel({ shop: null, guild: null });
  const model = ServiceMenu.buildMenus(panel);
  assert.deepEqual(model.surfaces, ["inventory"]);
  const guildRoot = model.menus.root.items.find((item) => item.key === "guild");
  assert.equal(guildRoot.enabled, false);
  assert.equal(guildRoot.actionId, null);
});

test("guild menu exposes register, board, quests, and exam rows", () => {
  const panel = validPanel();
  panel.guild.rank = {
    rank: "F",
    merit: 60,
    next_rank: "E",
    next_threshold: 50,
    eligible: true,
    exam_start: action({ action_id: "guild.exam_start", label: "升階考核（E）" }),
  };
  const items = ServiceMenu.buildMenus(panel).menus.guild.items;
  const register = items.find((item) => item.key === "register");
  assert.equal(register.actionId, "guild.register");
  assert.deepEqual(register.payload, {});
  const exam = items.find((item) => item.key === "exam_start");
  assert.deepEqual(exam.payload, { target_rank: "E" });
  assert.equal(exam.actionId, "guild.exam_start");
});

test("board rows submit guild.quest_accept with the definition key", () => {
  const panel = validPanel();
  const board = ServiceMenu.buildMenus(panel).menus.board.items;
  assert.equal(board.length, 1);
  assert.equal(board[0].actionId, "guild.quest_accept");
  assert.deepEqual(board[0].payload, { definition_key: "introductory_hunt" });
});

test("disabled rows stay focusable but never submit", () => {
  const panel = validPanel();
  panel.guild.quests[0].abandon = action({
    action_id: "guild.quest_abandon",
    label: "放棄",
    enabled: false,
    disabled_reason: { code: "quest_transition", message: "這個任務目前無法進行此操作。" },
  });
  const model = ServiceMenu.buildMenus(panel);
  const questMenu = model.menus.quests.items[0];
  assert.equal(questMenu.enabled, true);
  const detailMenu = ServiceMenu.questMenuFor(model, panel.guild.quests[0]).items;
  const abandon = detailMenu.find((item) => item.key.indexOf("quest-abandon") === 0);
  assert.equal(abandon.enabled, false);
  assert.equal(abandon.actionId, null);
  assert.equal(abandon.confirmActionId, null);
});

test("quest detail menu gates abandon behind confirmation", () => {
  const panel = validPanel();
  const model = ServiceMenu.buildMenus(panel);
  const detailMenu = ServiceMenu.questMenuFor(model, panel.guild.quests[0]).items;
  const abandon = detailMenu.find((item) => item.key.indexOf("quest-abandon") === 0);
  assert.equal(abandon.confirmActionId, "guild.quest_abandon");
  assert.deepEqual(abandon.confirmPayload, { quest_id: "introductory_hunt:1" });
  assert.equal(abandon.confirmLabel, "確認放棄");
  const confirmation = ServiceMenu.confirmMenu(
    abandon.confirmLabel,
    abandon.confirmActionId,
    abandon.confirmPayload
  );
  assert.deepEqual(confirmation.items[0].payload, { quest_id: "introductory_hunt:1" });
  assert.equal(confirmation.items[1].actionId, null);
});

test("completed quest turnin submits guild.quest_turnin", () => {
  const panel = validPanel();
  panel.guild.quests[0].turnin = action({ action_id: "guild.quest_turnin", label: "回報" });
  const model = ServiceMenu.buildMenus(panel);
  const detailMenu = ServiceMenu.questMenuFor(model, panel.guild.quests[0]).items;
  const turnin = detailMenu.find((item) => item.key.indexOf("quest-turnin") === 0);
  assert.equal(turnin.actionId, "guild.quest_turnin");
  assert.deepEqual(turnin.payload, { quest_id: "introductory_hunt:1" });
});

test("stock rows advertise bounded quantity forms", () => {
  const panel = validPanel();
  const stock = ServiceMenu.buildMenus(panel).menus.stock.items;
  assert.equal(stock.length, 1);
  assert.equal(stock[0].actionId, "shop.buy");
  assert.equal(stock[0].itemKey, "meal");
  assert.deepEqual(stock[0].quantity, { min: 1, max: 20 });
});

test("quantity validation rejects empty, non-integer, and out-of-bounds values", () => {
  const state = ServiceMenu.quantityState(1, 1000);
  assert.equal(ServiceMenu.validateQuantity(state), null);
  ServiceMenu.quantityInput(state, "1");
  ServiceMenu.quantityInput(state, "0");
  assert.equal(ServiceMenu.validateQuantity(state), 10);
  ServiceMenu.quantityInput(state, "a");
  assert.equal(ServiceMenu.validateQuantity(state), 10);
  ServiceMenu.quantityBackspace(state);
  ServiceMenu.quantityBackspace(state);
  assert.equal(ServiceMenu.validateQuantity(state), null);

  const small = ServiceMenu.quantityState(1, 3);
  ServiceMenu.quantityInput(small, "4");
  assert.equal(ServiceMenu.validateQuantity(small), null);
  ServiceMenu.quantityInput(small, "0");
  assert.equal(ServiceMenu.validateQuantity(small), null);

  const huge = ServiceMenu.quantityState(1, 1000);
  for (let i = 0; i < 5; i++) {
    ServiceMenu.quantityInput(huge, "9");
  }
  assert.ok(huge.raw.length <= 4);
  assert.ok(ServiceMenu.validateQuantity(huge) <= 1000 || ServiceMenu.validateQuantity(huge) === null);
});

test("inventory rows carry no use or equip control", () => {
  const panel = validPanel();
  const inventory = ServiceMenu.buildMenus(panel).menus.inventory.items;
  assert.equal(inventory.length, 1);
  assert.equal(inventory[0].enabled, false);
  assert.equal(inventory[0].actionId, null);
  assert.ok(inventory[0].label.indexOf("×2") !== -1);
});

test("empty lists render a readable non-submitting placeholder", () => {
  const panel = validPanel({ guild: null, shop: null });
  panel.inventory.rows = [];
  const model = ServiceMenu.buildMenus(panel);
  const items = model.menus.inventory.items;
  assert.equal(items.length, 1);
  assert.equal(items[0].enabled, false);
  assert.equal(items[0].actionId, null);
});
