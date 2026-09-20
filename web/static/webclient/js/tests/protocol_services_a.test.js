/*
 * services panel schema (design D4): discriminator, bounds, row ceilings, pagination, maximal payload envelope fit.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { T_MEAL, T_MEAL_LABEL } = require("./protocol_support.js");
const { validServicesAction, validServicesBoardRow, validServicesPanel, validServicesQuestRow, validServicesStockRow } = require("./protocol_fixtures.js");



test("validates the services panel available/unavailable discriminator", () => {
  assert.deepEqual(
    Protocol.validateServicesPanel(validServicesPanel()),
    validServicesPanel()
  );
  const unavailable = {
    schema_version: 4,
    available: false,
    reason: { code: "services_unavailable", message: "服務選單目前無法顯示" },
  };
  assert.deepEqual(
    Protocol.validatePanel("services", Protocol.PANEL_ALLOWLIST.services, unavailable),
    unavailable
  );
  assert.throws(() => Protocol.validateServicesPanel({ ...validServicesPanel(), kind: "combat" }));
  assert.throws(() => Protocol.validateServicesPanel({ ...validServicesPanel(), available: "yes" }));
});

test("services panel rejects unknown-surface and malformed fields", () => {
  assert.throws(() =>
    Protocol.validateServicesPanel({ ...validServicesPanel(), secret: 1 })
  );
  assert.throws(() =>
    Protocol.validateServicesPanel({ ...validServicesPanel(), host: { identity: "公會長", display_name: "x" } })
  );
  assert.throws(() =>
    Protocol.validateServicesPanel({
      ...validServicesPanel(),
      player: { ...validServicesPanel().player, guild_registered: true, guild_rank: null },
    })
  );
  assert.throws(() =>
    Protocol.validateServicesPanel({
      ...validServicesPanel(),
      guild: {
        ...validServicesPanel().guild,
        board: [
          validServicesBoardRow({ accept: validServicesAction({ action_id: "guild.register" }) }),
        ],
      },
      pagination: { ...validServicesPanel().pagination, board_total: 1 },
    })
  );
});

test("services panel enforces quantity bounds and unknown-node-style rejection", () => {
  const panel = validServicesPanel({
    shop: {
      open: true,
      stock: [validServicesStockRow({ buy: validServicesAction({ action_id: "shop.buy" }) })],
      sellable: [],
    },
    pagination: { ...validServicesPanel().pagination, stock_total: 1 },
  });
  assert.throws(() => Protocol.validateServicesPanel(panel), /quantity bounds/);
  const panel2 = validServicesPanel({
    shop: {
      open: true,
      stock: [
        validServicesStockRow({
          buy: validServicesAction({
            action_id: "shop.buy",
            quantity: { min: 1, max: Protocol.SERVICES_MAX_QUANTITY + 1 },
          }),
        }),
      ],
      sellable: [],
    },
    pagination: { ...validServicesPanel().pagination, stock_total: 1 },
  });
  assert.throws(() => Protocol.validateServicesPanel(panel2), /quantity/);
  const booleanQuantity = validServicesPanel({
    shop: {
      open: true,
      stock: [
        validServicesStockRow({
          buy: validServicesAction({ action_id: "shop.buy", quantity: { min: 1, max: true } }),
        }),
      ],
      sellable: [],
    },
    pagination: { ...validServicesPanel().pagination, stock_total: 1 },
  });
  assert.throws(() => Protocol.validateServicesPanel(booleanQuantity), /quantity/);
});

test("services panel enforces row ceilings for every surface", () => {
  const board = [];
  for (let i = 0; i < Protocol.SERVICES_MAX_BOARD_ROWS + 1; i++) {
    board.push(validServicesBoardRow());
  }
  assert.throws(() =>
    Protocol.validateServicesPanel(
      validServicesPanel({
        guild: { ...validServicesPanel().guild, board },
        pagination: { ...validServicesPanel().pagination, board_total: board.length },
      })
    )
  );
  const inventory = [];
  for (let i = 0; i < Protocol.SERVICES_MAX_INVENTORY_ROWS + 1; i++) {
    inventory.push({ item_key: T_MEAL, display_name: T_MEAL_LABEL, held: 1, equipped: false });
  }
  assert.throws(() =>
    Protocol.validateServicesPanel(
      validServicesPanel({
        inventory: { rows: inventory, wallet: 0 },
        pagination: { ...validServicesPanel().pagination, inventory_total: inventory.length },
      })
    )
  );
});

test("services panel pagination must match shipped rows and null surfaces", () => {
  assert.throws(() =>
    Protocol.validateServicesPanel({
      ...validServicesPanel(),
      guild: null,
      pagination: { ...validServicesPanel().pagination, board_total: 1 },
    })
  );
  const withRows = validServicesPanel({
    guild: {
      registration: { registered: true, register: validServicesAction({ enabled: false, disabled_reason: { code: "already_registered", message: "你已經是冒險者了。" } }) },
      board: [validServicesBoardRow()],
      quests: [validServicesQuestRow()],
      rank: null,
    },
    player: {
      wallet: 1000,
      guild_registered: true,
      guild_rank: "F",
      guild_merit: 60,
      next_rank: "E",
      next_threshold: 50,
    },
    pagination: { ...validServicesPanel().pagination, board_total: 1, quest_total: 1 },
  });
  assert.deepEqual(Protocol.validateServicesPanel(withRows), withRows);
  assert.throws(() =>
    Protocol.validateServicesPanel({
      ...withRows,
      pagination: { ...withRows.pagination, board_total: 0 },
    })
  );
});
