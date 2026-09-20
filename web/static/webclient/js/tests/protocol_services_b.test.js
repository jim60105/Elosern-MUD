/*
 * services panel v3 presentation rows, versioned rejection, inventory actions, allowlist atomicity.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { T_MEAL, T_MEAL_LABEL, T_MEAL_SUMMARY, VALID_EPOCH, serverTime } = require("./protocol_support.js");
const { validServicesAction, validServicesBoardRow, validServicesPanel, validServicesQuestRow, validServicesSellableRow, validServicesStockRow } = require("./protocol_fixtures.js");


test("a structurally maximal realistic services payload fits the envelope", () => {
  const board = [];
  const quests = [];
  const stock = [];
  const sellable = [];
  const inventory = [];
  for (let i = 0; i < Protocol.SERVICES_MAX_BOARD_ROWS; i++) {
    board.push(validServicesBoardRow());
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_QUEST_ROWS; i++) {
    quests.push(validServicesQuestRow());
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_STOCK_ROWS; i++) {
    stock.push(validServicesStockRow());
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_SELLABLE_ROWS; i++) {
    sellable.push(validServicesSellableRow());
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_INVENTORY_ROWS; i++) {
    inventory.push({
      item_key: T_MEAL,
      display_name: T_MEAL_LABEL,
      held: 2,
      equipped: false,
      action: null,
      presentation: {
        kind: "food",
        icon_key: "food",
        rarity: "common",
        summary: T_MEAL_SUMMARY,
      },
    });
  }
  const panel = validServicesPanel({
    guild: {
      registration: { registered: true, register: validServicesAction({ enabled: false, disabled_reason: { code: "already_registered", message: "你已經是冒險者了。" } }) },
      board: board,
      quests: quests,
      rank: {
        rank: "F",
        merit: 60,
        next_rank: "E",
        next_threshold: 50,
        eligible: true,
        exam_start: validServicesAction({ action_id: "guild.exam_start", label: "升階考核（E）" }),
      },
    },
    shop: { open: true, stock: stock, sellable: sellable },
    inventory: { rows: inventory, wallet: 1000000 },
    pagination: {
      board_total: Protocol.SERVICES_MAX_BOARD_ROWS,
      quest_total: Protocol.SERVICES_MAX_QUEST_ROWS,
      stock_total: Protocol.SERVICES_MAX_STOCK_ROWS,
      sellable_total: Protocol.SERVICES_MAX_SELLABLE_ROWS,
      inventory_total: Protocol.SERVICES_MAX_INVENTORY_ROWS,
    },
  });
  assert.doesNotThrow(() => Protocol.validateServicesPanel(panel));
  assert.ok(Protocol.jsonByteSize(panel) <= Protocol.MAX_CANONICAL_JSON_BYTES);
});

test("services payload maximizing every string field fails the byte gate", () => {
  // Every string field at its bound on every surface simultaneously. Each
  // field is individually in bounds, so only the serialized-size gate can
  // reject it (design D4).
  const max64 = "獎".repeat(Protocol.SERVICES_MAX_KEY);
  const max128 = "獎".repeat(Protocol.SERVICES_MAX_DISPLAY_NAME);
  const maxDetail = "獎".repeat(Protocol.SERVICES_MAX_DETAIL);
  const board = [];
  const quests = [];
  const stock = [];
  const sellable = [];
  const inventory = [];
  for (let i = 0; i < Protocol.SERVICES_MAX_BOARD_ROWS; i++) {
    board.push({
      definition_key: max64,
      display_name: max128,
      objective_summary: max128,
      reward_summary: max128,
      rank: max64.slice(0, Protocol.SERVICES_MAX_RANK_KEY),
      accept: validServicesAction({ action_id: "guild.quest_accept" }),
    });
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_QUEST_ROWS; i++) {
    quests.push({
      quest_id: max64,
      definition_key: max64,
      display_name: max128,
      state: "in_progress",
      stage_index: 0,
      stage_progress: 0,
      objective_summary: max128,
      deadline_line: max64.slice(0, Protocol.SERVICES_MAX_DEADLINE_LINE),
      detail: maxDetail,
      abandon: validServicesAction({ action_id: "guild.quest_abandon" }),
      turnin: validServicesAction({
        action_id: "guild.quest_turnin",
        enabled: false,
        disabled_reason: { code: "quest_transition", message: max64 },
      }),
      tracked: true,
    });
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_STOCK_ROWS; i++) {
    stock.push({
      item_key: max64,
      display_name: max128,
      buy_copper: 10,
      sell_copper: 5,
      stock: 20,
      max_stock: 20,
      buy: validServicesAction({
        action_id: "shop.buy",
        enabled: false,
        disabled_reason: { code: "insufficient_stock", message: max64 },
      }),
    });
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_SELLABLE_ROWS; i++) {
    sellable.push({
      item_key: max64,
      display_name: max128,
      sell_copper: 5,
      held: 20,
      sell: validServicesAction({
        action_id: "shop.sell",
        enabled: false,
        disabled_reason: { code: "stock_overflow", message: max64 },
      }),
    });
  }
  const presKey = "k".repeat(Protocol.SERVICES_MAX_PRESENTATION_KEY);
  const presSummary = "獎".repeat(Protocol.SERVICES_MAX_PRESENTATION_SUMMARY);
  for (let i = 0; i < Protocol.SERVICES_MAX_INVENTORY_ROWS; i++) {
    inventory.push({
      item_key: max64,
      display_name: max128,
      held: 20,
      equipped: false,
      action: null,
      presentation: { kind: presKey, icon_key: presKey, rarity: presKey, summary: presSummary },
    });
  }
  const panel = validServicesPanel({
    host: {
      identity: "1".repeat(Protocol.SERVICES_MAX_KEY),
      display_name: max128.repeat(2).slice(0, Protocol.SERVICES_MAX_HOST_DISPLAY_NAME),
    },
    player: {
      wallet: 0,
      guild_registered: true,
      guild_rank: "F",
      guild_merit: 0,
      next_rank: "E",
      next_threshold: 1,
    },
    guild: {
      registration: {
        registered: true,
        register: validServicesAction({
          enabled: false,
          disabled_reason: { code: "already_registered", message: max64 },
        }),
      },
      board: board,
      quests: quests,
      rank: {
        rank: "F",
        merit: 0,
        next_rank: "E",
        next_threshold: 1,
        eligible: false,
        exam_start: validServicesAction({
          action_id: "guild.exam_start",
          enabled: false,
          disabled_reason: { code: "below_threshold", message: max64 },
        }),
      },
    },
    shop: { open: false, stock: stock, sellable: sellable },
    inventory: { rows: inventory, wallet: 0 },
    pagination: {
      board_total: Protocol.SERVICES_MAX_BOARD_ROWS,
      quest_total: Protocol.SERVICES_MAX_QUEST_ROWS,
      stock_total: Protocol.SERVICES_MAX_STOCK_ROWS,
      sellable_total: Protocol.SERVICES_MAX_SELLABLE_ROWS,
      inventory_total: Protocol.SERVICES_MAX_INVENTORY_ROWS,
    },
  });
  assert.throws(() => Protocol.validateServicesPanel(panel), /envelope/);
});

test("services v3 accepts registered and unknown-key presentation rows", () => {
  const panel = validServicesPanel();
  const validated = Protocol.validateServicesPanel(panel);
  assert.deepEqual(validated, panel);
  const rows = validated.inventory.rows;
  const registered = rows.find((r) => r.item_key === T_MEAL);
  assert.deepEqual(registered.presentation, {
    kind: "food",
    icon_key: "food",
    rarity: "common",
    summary: T_MEAL_SUMMARY,
  });
  const unknown = rows.find((r) => r.item_key === "mystery_relic");
  assert.equal(unknown.presentation, null);

  // The 240-code-point summary bound is inclusive on a small payload.
  const boundary = validServicesPanel();
  boundary.inventory.rows = [
    {
      item_key: T_MEAL,
      display_name: T_MEAL_LABEL,
      held: 1,
      equipped: false,
      action: null,
      presentation: {
        kind: "food",
        icon_key: "food",
        rarity: "common",
        summary: "獎".repeat(Protocol.SERVICES_MAX_PRESENTATION_SUMMARY),
      },
    },
  ];
  boundary.pagination.inventory_total = 1;
  assert.doesNotThrow(() => Protocol.validateServicesPanel(boundary));
});

test("services v3 rejects invalid presentation fields", () => {
  const mutate = (row) => {
    const p = validServicesPanel();
    p.inventory.rows = [row];
    p.pagination.inventory_total = 1;
    return p;
  };
  const missing = {
    item_key: T_MEAL,
    display_name: T_MEAL_LABEL,
    held: 1,
    equipped: false,
    action: null,
    presentation: { kind: "food", icon_key: "food", summary: T_MEAL_SUMMARY },
  };
  assert.throws(() => Protocol.validateServicesPanel(mutate(missing)), /rarity/);

  const extra = {
    item_key: T_MEAL,
    display_name: T_MEAL_LABEL,
    held: 1,
    equipped: false,
    action: null,
    presentation: {
      kind: "food",
      icon_key: "food",
      rarity: "common",
      summary: T_MEAL_SUMMARY,
      color: "red",
    },
  };
  assert.throws(() => Protocol.validateServicesPanel(mutate(extra)), /unknown fields/);

  const overlong = {
    item_key: T_MEAL,
    display_name: T_MEAL_LABEL,
    held: 1,
    equipped: false,
    action: null,
    presentation: {
      kind: "k".repeat(Protocol.SERVICES_MAX_PRESENTATION_KEY + 1),
      icon_key: "food",
      rarity: "common",
      summary: T_MEAL_SUMMARY,
    },
  };
  assert.throws(() => Protocol.validateServicesPanel(mutate(overlong)), /kind/);

  const uppercase = {
    item_key: T_MEAL,
    display_name: T_MEAL_LABEL,
    held: 1,
    equipped: false,
    action: null,
    presentation: {
      kind: "Potion",
      icon_key: "food",
      rarity: "common",
      summary: T_MEAL_SUMMARY,
    },
  };
  assert.throws(() => Protocol.validateServicesPanel(mutate(uppercase)), /kind/);

  const longSummary = {
    item_key: T_MEAL,
    display_name: T_MEAL_LABEL,
    held: 1,
    equipped: false,
    action: null,
    presentation: {
      kind: "food",
      icon_key: "food",
      rarity: "common",
      summary: "獎".repeat(Protocol.SERVICES_MAX_PRESENTATION_SUMMARY + 1),
    },
  };
  assert.throws(() => Protocol.validateServicesPanel(mutate(longSummary)), /summary/);

  const notObject = {
    item_key: T_MEAL,
    display_name: T_MEAL_LABEL,
    held: 1,
    equipped: false,
    action: null,
    presentation: "food",
  };
  assert.throws(() => Protocol.validateServicesPanel(mutate(notObject)), /JSON object or null/);
});

test("services v1 payload is rejected by the v3 validator", () => {
  const panel = { ...validServicesPanel(), schema_version: 1 };
  panel.inventory.rows = panel.inventory.rows.map(({ presentation, ...rest }) => rest);
  assert.throws(() => Protocol.validateServicesPanel(panel), /schema_version/);
});

test("services v2 payload is rejected by the v3 validator", () => {
  const panel = { ...validServicesPanel(), schema_version: 2 };
  assert.throws(() => Protocol.validateServicesPanel(panel), /schema_version/);
});

test("services v3 validates inventory row actions exactly", () => {
  const good = validServicesPanel();
  good.inventory.rows[0].action = {
    action_id: "inventory.use",
    label: "使用",
    enabled: false,
    disabled_reason: { code: "hp_full", message: "你的體力已經全滿。" },
    quantity: null,
  };
  assert.deepEqual(
    Protocol.validateServicesPanel(good).inventory.rows[0].action,
    good.inventory.rows[0].action
  );
  const withQuantity = validServicesPanel();
  withQuantity.inventory.rows[0].action = {
    action_id: "inventory.use",
    label: "使用",
    enabled: true,
    disabled_reason: null,
    quantity: { min: 1, max: 2 },
  };
  assert.throws(() => Protocol.validateServicesPanel(withQuantity));
  const unknownId = validServicesPanel();
  unknownId.inventory.rows[0].action = {
    action_id: "inventory.drop",
    label: "丟棄",
    enabled: true,
    disabled_reason: null,
    quantity: null,
  };
  assert.throws(() => Protocol.validateServicesPanel(unknownId));
  const crossServiceId = validServicesPanel();
  crossServiceId.inventory.rows[0].action = {
    action_id: "shop.buy",
    label: "購買",
    enabled: true,
    disabled_reason: null,
    quantity: null,
  };
  assert.throws(() => Protocol.validateServicesPanel(crossServiceId));
  const toggleGood = validServicesPanel();
  toggleGood.inventory.rows[0].action = {
    action_id: "inventory.toggle_equip",
    label: "裝備",
    enabled: true,
    disabled_reason: null,
    quantity: null,
  };
  assert.doesNotThrow(() => Protocol.validateServicesPanel(toggleGood));
  const missing = validServicesPanel();
  delete missing.inventory.rows[0].action;
  assert.throws(() => Protocol.validateServicesPanel(missing));
});

test("services is in the production panel allowlist and a bad panel rejects atomically", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.services, 4);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 1,
    mode: "exploration",
    panels: {
      services: { ...validServicesPanel(), kind: "bogus" },
    },
    layout_version: 1,
    server_time: serverTime(),
  };
  const store = Protocol.createStore();
  store.beginTransport(1);
  const accepted = store.receive(1, "ui_snapshot", [envelope], {});
  assert.equal(accepted.accepted, false);
  assert.equal(accepted.reason, "invalid");
  assert.equal(store.getState().phase, "awaiting_initial_snapshot");
});

