/*
 * services panel v7 shop rows (presentation, viewed facts, one price per row
 * kind), versioned rejection, allowlist atomicity.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { T_MEAL_SUMMARY, VALID_EPOCH, serverTime } = require("./protocol_support.js");
const { validServicesAction, validServicesBoardRow, validServicesPanel, validServicesQuestRow, validServicesSellableRow, validServicesStockRow } = require("./protocol_fixtures.js");

test("services v7 rejects stale facts and reward overflow", () => {
  const item = { item_key: "synthetic_item", display_name: "合成物品", quantity: 1 };
  for (const overrides of [
    { reward_summary: "舊獎勵" },
    { category: "unknown" },
    { reward: null },
    { reward: { copper: 0, merit: 0, items: [item, item] } },
    { reward: { copper: 0, merit: 0, items: Array(9).fill(item) } },
    { rationale: "獎".repeat(Protocol.SERVICES_MAX_BOARD_PROSE + 1) },
  ]) {
    const panel = validServicesPanel();
    panel.guild.board = [validServicesBoardRow(overrides)];
    panel.pagination.board_total = 1;
    assert.throws(() => Protocol.validateServicesPanel(panel));
  }
});

test("services v7 validates ladder bounds and all section rank memberships", () => {
  for (const ladder of [[], ["F", "F"], ["E"], ["F", "x".repeat(9)], Array.from({ length: 17 }, (_, i) => String(i))]) {
    const panel = validServicesPanel();
    panel.guild.board = [validServicesBoardRow()];
    panel.pagination.board_total = 1;
    panel.guild.rank_ladder = ladder;
    assert.throws(() => Protocol.validateServicesPanel(panel));
  }
});


test("a structurally maximal realistic services payload fits the envelope", () => {
  const board = [];
  const quests = [];
  const stock = [];
  const sellable = [];
  for (let i = 0; i < Protocol.SERVICES_MAX_BOARD_ROWS; i++) {
    board.push(validServicesBoardRow());
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_QUEST_ROWS; i++) {
    quests.push(validServicesQuestRow());
  }
  // Every stock row carries a delta on every canonical trait.
  const traits = ["hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power", "guild_merit"];
  const delta = {
    equippable: true,
    changes: traits.map((key) => ({ key: key, label: "攻擊", amount: -12 })),
  };
  for (let i = 0; i < Protocol.SERVICES_MAX_STOCK_ROWS; i++) {
    stock.push(validServicesStockRow({ viewed: { held: 2, delta: delta } }));
  }
  for (let i = 0; i < Protocol.SERVICES_MAX_SELLABLE_ROWS; i++) {
    sellable.push(validServicesSellableRow());
  }
  const panel = validServicesPanel({
    guild: {
      branch_label: "合成公會分行",
      rank_ladder: ["F", "E", "D", "C", "B", "A", "S"],
      registration: { registered: true, register: validServicesAction({ enabled: false, disabled_reason: { code: "already_registered", message: "你已經是冒險者了。" } }) },
      board: board,
      quests: quests,
      rank: {
        rank: "F",
        merit: 60,
        next_rank: "E",
        next_threshold: 50,
        merit_qualified: true,
        exam_request: validServicesAction({ action_id: "guild.exam_request", label: "預約升等考核" }),
      },
    },
    shop: { open: true, member_id: 12345, stock: stock, sellable: sellable },
    pagination: {
      board_total: Protocol.SERVICES_MAX_BOARD_ROWS,
      quest_total: Protocol.SERVICES_MAX_QUEST_ROWS,
      stock_total: Protocol.SERVICES_MAX_STOCK_ROWS,
      sellable_total: Protocol.SERVICES_MAX_SELLABLE_ROWS,
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
  const presKey = "k".repeat(Protocol.SERVICES_MAX_PRESENTATION_KEY);
  const presSummary = "獎".repeat(Protocol.SERVICES_MAX_PRESENTATION_SUMMARY);
  const presentation = { kind: presKey, icon_key: presKey, rarity: presKey, summary: presSummary };
  for (let i = 0; i < Protocol.SERVICES_MAX_BOARD_ROWS; i++) {
    board.push({
      definition_key: max64,
      display_name: max128,
      objective_summary: max128,
      category: "defeat",
      objective_note: max128,
      deadline_line: max64,
      rationale: "獎".repeat(Protocol.SERVICES_MAX_BOARD_PROSE),
      flavor: "獎".repeat(Protocol.SERVICES_MAX_BOARD_PROSE),
      reward: { copper: 0, merit: 0, items: [{ item_key: max64, display_name: max128, quantity: 1 }] },
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
      presentation: presentation,
      buy_copper: 10,
      stock: 20,
      max_stock: 20,
      viewed: { held: 20, delta: { equippable: false, reason: max128 } },
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
      presentation: presentation,
      sell_copper: 5,
      held: 20,
      sell: validServicesAction({
        action_id: "shop.sell",
        enabled: false,
        disabled_reason: { code: "stock_overflow", message: max64 },
      }),
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
      branch_label: "獎".repeat(256),
      rank_ladder: ["F", "E", max64.slice(0, Protocol.SERVICES_MAX_RANK_KEY)],
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
        merit_qualified: false,
        exam_request: validServicesAction({
          action_id: "guild.exam_request",
          enabled: false,
          disabled_reason: { code: "wrong_branch", message: max64 },
        }),
      },
    },
    shop: { open: false, member_id: 1, stock: stock, sellable: sellable },
    pagination: {
      board_total: Protocol.SERVICES_MAX_BOARD_ROWS,
      quest_total: Protocol.SERVICES_MAX_QUEST_ROWS,
      stock_total: Protocol.SERVICES_MAX_STOCK_ROWS,
      sellable_total: Protocol.SERVICES_MAX_SELLABLE_ROWS,
    },
  });
  assert.throws(() => Protocol.validateServicesPanel(panel), /envelope/);
});

function shopPanel(stock, sellable) {
  return validServicesPanel({
    shop: { open: true, member_id: 7, stock: stock, sellable: sellable || [] },
    pagination: {
      ...validServicesPanel().pagination,
      stock_total: stock.length,
      sellable_total: (sellable || []).length,
    },
  });
}

test("services v7 accepts registered and unknown-key presentation rows", () => {
  const panel = shopPanel(
    [validServicesStockRow(), validServicesStockRow({ item_key: "mystery_relic", display_name: "mystery_relic", presentation: null })],
    [validServicesSellableRow()]
  );
  const validated = Protocol.validateServicesPanel(panel);
  assert.deepEqual(validated, panel);
  assert.deepEqual(validated.shop.stock[0].presentation, {
    kind: "food",
    icon_key: "food",
    rarity: "common",
    summary: T_MEAL_SUMMARY,
  });
  assert.equal(validated.shop.stock[1].presentation, null);
  assert.equal(validated.shop.member_id, 7);

  // The 240-code-point summary bound is inclusive on a small payload.
  const boundary = shopPanel([
    validServicesStockRow({
      presentation: { kind: "food", icon_key: "food", rarity: "common", summary: "獎".repeat(Protocol.SERVICES_MAX_PRESENTATION_SUMMARY) },
    }),
  ]);
  assert.doesNotThrow(() => Protocol.validateServicesPanel(boundary));
});

test("services v7 rejects invalid presentation fields", () => {
  const mutate = (presentation) => shopPanel([validServicesStockRow({ presentation: presentation })]);
  assert.throws(() => Protocol.validateServicesPanel(mutate({ kind: "food", icon_key: "food", summary: T_MEAL_SUMMARY })), /rarity/);
  assert.throws(
    () => Protocol.validateServicesPanel(mutate({ kind: "food", icon_key: "food", rarity: "common", summary: T_MEAL_SUMMARY, color: "red" })),
    /unknown fields/
  );
  assert.throws(
    () => Protocol.validateServicesPanel(mutate({ kind: "k".repeat(Protocol.SERVICES_MAX_PRESENTATION_KEY + 1), icon_key: "food", rarity: "common", summary: T_MEAL_SUMMARY })),
    /kind/
  );
  assert.throws(() => Protocol.validateServicesPanel(mutate({ kind: "Potion", icon_key: "food", rarity: "common", summary: T_MEAL_SUMMARY })), /kind/);
  assert.throws(
    () => Protocol.validateServicesPanel(mutate({ kind: "food", icon_key: "food", rarity: "common", summary: "獎".repeat(Protocol.SERVICES_MAX_PRESENTATION_SUMMARY + 1) })),
    /summary/
  );
  assert.throws(() => Protocol.validateServicesPanel(mutate("food")), /JSON object or null/);
  // Sellable rows validate their presentation the same way.
  assert.throws(() =>
    Protocol.validateServicesPanel(shopPanel([], [validServicesSellableRow({ presentation: "food" })]))
  );
});

test("services v7 shop rows carry one price per row kind and the viewed member", () => {
  assert.doesNotThrow(() => Protocol.validateServicesPanel(shopPanel([validServicesStockRow()], [validServicesSellableRow()])));
  const cases = [
    shopPanel([validServicesStockRow({ sell_copper: 5 })]),
    shopPanel([], [validServicesSellableRow({ buy_copper: 10 })]),
    shopPanel([validServicesStockRow({ viewed: { held: 1 } })]),
    shopPanel([validServicesStockRow({ viewed: { held: -1, delta: null } })]),
    shopPanel([validServicesStockRow({ viewed: { held: 0, delta: { equippable: false } } })]),
    shopPanel([validServicesStockRow({ viewed: { held: 0, delta: { equippable: true, changes: [], reason: "x" } } })]),
    shopPanel([validServicesStockRow({ viewed: { held: 0, delta: { equippable: true, changes: [
      { key: "defense", label: "防禦", amount: 2 },
      { key: "atk_phys", label: "攻擊", amount: 6 },
    ] } } })]),
    shopPanel([], [validServicesSellableRow({ held: 0 })]),
    shopPanel([validServicesStockRow({ buy: validServicesAction({ action_id: "inventory.use" }) })]),
  ];
  for (const panel of cases) {
    assert.throws(() => Protocol.validateServicesPanel(panel));
  }
  for (const memberId of [0, -1, true, "7", null]) {
    const panel = shopPanel([validServicesStockRow()]);
    panel.shop.member_id = memberId;
    assert.throws(() => Protocol.validateServicesPanel(panel));
  }
  const noMember = shopPanel([validServicesStockRow()]);
  delete noMember.shop.member_id;
  assert.throws(() => Protocol.validateServicesPanel(noMember));
  const delta = { equippable: true, changes: [{ key: "atk_phys", label: "攻擊", amount: 6 }] };
  const capped = { equippable: false, reason: "accessory_slots_full" };
  assert.doesNotThrow(() =>
    Protocol.validateServicesPanel(
      shopPanel([
        validServicesStockRow({ viewed: { held: 0, delta: delta } }),
        validServicesStockRow({ viewed: { held: 5, delta: capped } }),
      ])
    )
  );
});

test("services v7 carries no inventory section or total", () => {
  assert.throws(() => Protocol.validateServicesPanel({ ...validServicesPanel(), inventory: null }));
  assert.throws(() =>
    Protocol.validateServicesPanel({
      ...validServicesPanel(),
      pagination: { ...validServicesPanel().pagination, inventory_total: 0 },
    })
  );
  assert.throws(() => Protocol.validateServicesPanel({ ...validServicesPanel(), schema_version: 6 }), /schema_version/);
});

test("services v1 payload is rejected by the v3 validator", () => {
  const panel = { ...validServicesPanel(), schema_version: 1 };
  assert.throws(() => Protocol.validateServicesPanel(panel), /schema_version/);
});

test("services v2 payload is rejected by the v3 validator", () => {
  const panel = { ...validServicesPanel(), schema_version: 2 };
  assert.throws(() => Protocol.validateServicesPanel(panel), /schema_version/);
});

test("services is in the production panel allowlist and a bad panel rejects atomically", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.services, 7);
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


function rankedServicesPanel(rank) {
  return validServicesPanel({
    guild: {
      branch_label: "合成公會分行",
      rank_ladder: ["F", "E", "D", "C", "B", "A", "S"],
      registration: {
        registered: true,
        register: validServicesAction({
          enabled: false,
          disabled_reason: { code: "already_registered", message: "你已經是冒險者了。" },
        }),
      },
      board: [],
      quests: [],
      rank: rank,
    },
    pagination: {
      board_total: 0,
      quest_total: 0,
      stock_total: 0,
      sellable_total: 0,
    },
  });
}

function belowMeritRank(overrides) {
  return Object.assign(
    {
      rank: "F",
      merit: 30,
      next_rank: "E",
      next_threshold: 40,
      merit_qualified: false,
      exam_request: validServicesAction({ action_id: "guild.exam_request", label: "預約升等考核" }),
    },
    overrides || {}
  );
}

test("services v5 keeps merit qualification independent of request availability", () => {
  // Below threshold with an enabled request, and qualified with a disabled
  // request, are both valid: no equality constraint remains.
  assert.doesNotThrow(() => Protocol.validateServicesPanel(rankedServicesPanel(belowMeritRank())));
  const qualifiedButClosed = belowMeritRank({
    merit: 40,
    merit_qualified: true,
    exam_request: validServicesAction({
      action_id: "guild.exam_request",
      label: "預約升等考核",
      enabled: false,
      disabled_reason: { code: "schedule_blocked", message: "她現在正忙著，沒有理會你。" },
    }),
  });
  assert.doesNotThrow(() => Protocol.validateServicesPanel(rankedServicesPanel(qualifiedButClosed)));
});

test("services v5 rejects the retired exam fields, action and schema version", () => {
  const legacy = belowMeritRank();
  delete legacy.merit_qualified;
  delete legacy.exam_request;
  legacy.eligible = false;
  legacy.exam_start = validServicesAction({ action_id: "guild.exam_start" });
  assert.throws(() => Protocol.validateServicesPanel(rankedServicesPanel(legacy)));
  assert.throws(() =>
    Protocol.validateServicesPanel(
      rankedServicesPanel(
        belowMeritRank({ exam_request: validServicesAction({ action_id: "guild.exam_start" }) })
      )
    )
  );
  assert.throws(() =>
    Protocol.validateServicesPanel(rankedServicesPanel(belowMeritRank({ merit_qualified: "no" })))
  );
  assert.throws(() =>
    Protocol.validateServicesPanel({ ...rankedServicesPanel(belowMeritRank()), schema_version: 4 })
  );
});
