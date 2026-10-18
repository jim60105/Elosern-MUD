/*
 * party_inventory panel v1 mirror: exact viewed-member equipment, bag rows
 * with server-authored descriptors, the commander purse, and shape drift.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const fx = require("./protocol_fixtures.js");

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function row(overrides) {
  return fx.validPartyInventoryRow(overrides);
}

function panel(overrides) {
  return fx.validPartyInventoryPanel(overrides);
}

test("party_inventory validates its exact available form", () => {
  assert.equal(Protocol.PARTY_INVENTORY_SCHEMA_VERSION, 1);
  const value = panel();
  assert.deepEqual(Protocol.validatePartyInventoryPanel(value), value);
  assert.equal(Protocol.PANEL_ALLOWLIST.party_inventory, 1);
  // The envelope dispatches the allowlisted name to its own validator.
  assert.deepEqual(
    Protocol.validatePanel("party_inventory", 1, value),
    value
  );
});

test("party_inventory carries equipment, slots and the commander purse", () => {
  const value = panel({
    equipment: fx.validPartyInventoryEquipment({
      weapon_main: "t_thorn_fang",
      accessories: ["t_bulwark_plate"],
      accessory_limit: 5,
    }),
    rows: [
      row({
        item_key: "t_thorn_fang",
        display_name: "荊牙刃",
        held: 1,
        equipped_count: 1,
        slot: "weapon_main",
        presentation: {
          kind: "weapon",
          icon_key: "weapon",
          rarity: "uncommon",
          summary: "測試用長劍。",
        },
        use: null,
        toggle: fx.validPartyInventoryDescriptor("toggle"),
        give: fx.validPartyInventoryGive({
          enabled: false,
          reason: "已裝備的物品無法交換；請先卸下。",
          max_quantity: 0,
        }),
      }),
    ],
  });
  assert.deepEqual(Protocol.validatePartyInventoryPanel(value), value);
});

test("party_inventory rejects shape drift", () => {
  const base = panel();
  const invalid = [
    ["unknown top key", () => Object.assign(panel(), { extra: 1 })],
    ["wrong schema", () => panel({ schema_version: 2 })],
    ["schema boolean", () => panel({ schema_version: true })],
    ["unavailable form", () => panel({ available: false })],
    ["wrong kind", () => panel({ kind: "party" })],
    ["negative purse", () => panel({ purse: -1 })],
    ["boolean member", () => panel({ member_id: true })],
    ["unknown row key", () => panel({ rows: [Object.assign(row(), { extra: 1 })] })],
    ["missing use", () => {
      const value = clone(base);
      delete value.rows[0].use;
      return value;
    }],
    ["enabled use with reason", () =>
      panel({
        rows: [
          row({
            use: { route: "field_use", enabled: true, reason: "不行。" },
          }),
        ],
      })],
    ["disabled use without reason", () =>
      panel({
        rows: [row({ use: { route: "field_use", enabled: false, reason: null } })],
      })],
    ["unknown use route", () =>
      panel({
        rows: [row({ use: { route: "toggle", enabled: true, reason: null } })],
      })],
    ["unknown toggle route", () =>
      panel({
        rows: [
          row({
            item_key: "t_thorn_fang",
            equipped_count: 1,
            slot: "weapon_main",
            toggle: { route: "field_use", enabled: true, reason: null },
          }),
        ],
        equipment: fx.validPartyInventoryEquipment({
          weapon_main: "t_thorn_fang",
        }),
      })],
    ["give enabled with reason", () =>
      panel({
        rows: [
          row({
            give: { enabled: true, reason: "不行。", max_quantity: 1 },
          }),
        ],
      })],
    ["give disabled without reason", () =>
      panel({
        rows: [
          row({
            give: { enabled: false, reason: null, max_quantity: 1 },
          }),
        ],
      })],
    ["negative max quantity", () =>
      panel({
        rows: [
          row({
            give: { enabled: false, reason: "不行。", max_quantity: -1 },
          }),
        ],
      })],
    ["boolean max quantity", () =>
      panel({
        rows: [
          row({
            give: { enabled: true, reason: null, max_quantity: true },
          }),
        ],
      })],
    ["duplicate item key", () => panel({ rows: [row(), row()] })],
    ["row over the ceiling", () => {
      const rows = [];
      for (let index = 0; index < 33; index += 1) {
        rows.push(row({ item_key: "t_item_" + index }));
      }
      return panel({ rows: rows });
    }],
    ["accessory overflow", () =>
      panel({
        equipment: fx.validPartyInventoryEquipment({
          accessories: ["a1", "a2", "a3", "a4", "a5", "a6"],
        }),
      })],
    ["accessory limit drift", () =>
      panel({
        equipment: fx.validPartyInventoryEquipment({ accessory_limit: 4 }),
      })],
    ["duplicate equipment key", () =>
      panel({
        equipment: fx.validPartyInventoryEquipment({
          weapon_main: "t_thorn_fang",
          armor: "t_thorn_fang",
        }),
      })],
    ["two equipped copies", () =>
      panel({
        equipment: fx.validPartyInventoryEquipment({
          weapon_main: "t_thorn_fang",
        }),
        rows: [
          row({
            item_key: "t_thorn_fang",
            held: 2,
            equipped_count: 2,
            slot: "weapon_main",
            toggle: fx.validPartyInventoryDescriptor("toggle"),
          }),
        ],
      })],
    ["worn row reports no equipment", () =>
      panel({
        equipment: fx.validPartyInventoryEquipment({
          weapon_main: "t_thorn_fang",
        }),
        rows: [
          row({
            item_key: "t_thorn_fang",
            toggle: fx.validPartyInventoryDescriptor("toggle"),
          }),
        ],
      })],
    ["unworn row reports equipment", () =>
      panel({
        rows: [
          row({
            item_key: "t_thorn_fang",
            equipped_count: 1,
            slot: "weapon_main",
            toggle: fx.validPartyInventoryDescriptor("toggle"),
          }),
        ],
      })],
    ["slot without toggle", () =>
      panel({
        rows: [
          row({
            item_key: "t_thorn_fang",
            equipped_count: 1,
            slot: "weapon_main",
            toggle: null,
          }),
        ],
        equipment: fx.validPartyInventoryEquipment({
          weapon_main: "t_thorn_fang",
        }),
      })],
    ["presentation key drift", () =>
      panel({
        rows: [
          row({
            presentation: {
              kind: "Food",
              icon_key: "food",
              rarity: "common",
              summary: "測試。",
            },
          }),
        ],
      })],
    ["presentation summary over cap", () =>
      panel({
        rows: [
          row({
            presentation: {
              kind: "food",
              icon_key: "food",
              rarity: "common",
              summary: "獎".repeat(241),
            },
          }),
        ],
      })],
    ["item key over cap", () =>
      panel({ rows: [row({ item_key: "k".repeat(65) })] })],
    ["display name over cap", () =>
      panel({ rows: [row({ display_name: "名".repeat(129) })] })],
    ["empty display name", () =>
      panel({ rows: [row({ display_name: "  " })] })],
    ["lone surrogate display name", () =>
      panel({ rows: [row({ display_name: "\ud800" })] })],
    ["row slot without a slot name", () =>
      panel({
        rows: [row({ slot: "bag", toggle: null })],
      })],
  ];
  for (const [name, build] of invalid) {
    assert.throws(
      () => Protocol.validatePartyInventoryPanel(build()),
      undefined,
      name
    );
  }
});

test("party_inventory accepts its maximal bounded form", () => {
  const rows = [];
  for (let index = 0; index < Protocol.PARTY_INVENTORY_MAX_ROWS; index += 1) {
    rows.push(
      row({
        item_key: ("k" + index).padEnd(64, "x"),
        display_name: "名".repeat(128),
        presentation: {
          kind: "k".repeat(32),
          icon_key: "i".repeat(32),
          rarity: "r".repeat(32),
          summary: "獎".repeat(240),
        },
        use: {
          route: "field_use",
          enabled: false,
          reason: "飾品欄已經滿了，最多同時佩戴五個。",
        },
        give: {
          enabled: false,
          reason: "戰鬥中無法交換物品。",
          max_quantity: 999,
        },
      })
    );
  }
  const value = panel({ rows: rows });
  assert.deepEqual(Protocol.validatePartyInventoryPanel(value), value);
  assert.ok(
    Protocol.jsonByteSize(value) <= Protocol.MAX_CANONICAL_JSON_BYTES
  );
});

test("party_inventory rejects an over-envelope payload", () => {
  const rows = [];
  for (let index = 0; index < Protocol.PARTY_INVENTORY_MAX_ROWS; index += 1) {
    rows.push(
      row({
        item_key: ("k" + index).padEnd(64, "x"),
        display_name: "名".repeat(128),
        presentation: {
          kind: "k".repeat(32),
          icon_key: "i".repeat(32),
          rarity: "r".repeat(32),
          summary: "獎".repeat(240),
        },
        use: {
          route: "field_use",
          enabled: false,
          reason: "理".repeat(512),
        },
        toggle: null,
        give: {
          enabled: false,
          reason: "理".repeat(512),
          max_quantity: 999,
        },
      })
    );
  }
  const value = panel({ rows: rows });
  assert.ok(Protocol.jsonByteSize(value) > Protocol.MAX_CANONICAL_JSON_BYTES);
  assert.throws(
    () => Protocol.validatePartyInventoryPanel(value),
    /OOB envelope limit/
  );
});
