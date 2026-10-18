/*
 * item_holdings panel v1 mirror: per-member counts, server-computed equipment
 * deltas against the current slot occupant, transfer verdicts, and shape
 * drift. The client computes neither counts nor deltas.
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
  return fx.validItemHoldingsRow(overrides);
}

function panel(overrides) {
  return fx.validItemHoldingsPanel(overrides);
}

function change(overrides) {
  return fx.validItemHoldingsChange(overrides);
}

test("item_holdings validates its exact available form", () => {
  assert.equal(Protocol.ITEM_HOLDINGS_SCHEMA_VERSION, 1);
  const value = panel();
  assert.deepEqual(Protocol.validateItemHoldingsPanel(value), value);
  assert.equal(Protocol.PANEL_ALLOWLIST.item_holdings, 1);
  // The envelope dispatches the allowlisted name to its own validator.
  assert.deepEqual(
    Protocol.validatePanel("item_holdings", 1, value),
    value
  );
});

test("item_holdings carries counts, deltas and transfer verdicts", () => {
  const value = panel({
    rows: [
      row({
        member_id: 7,
        held: 2,
        receive: fx.validItemHoldingsReceive({ enabled: false, reason: null }),
      }),
      row({
        member_id: 41,
        held: 1,
        equipped: true,
        delta: fx.validItemHoldingsDelta({ changes: [] }),
      }),
    ],
  });
  assert.deepEqual(Protocol.validateItemHoldingsPanel(value), value);
});

test("item_holdings accepts the refused delta form", () => {
  const value = panel({
    rows: [
      row({
        member_id: 7,
        receive: fx.validItemHoldingsReceive({ enabled: false, reason: null }),
      }),
      row({
        member_id: 41,
        delta: { equippable: false, reason: "accessory_slots_full" },
      }),
    ],
  });
  assert.deepEqual(Protocol.validateItemHoldingsPanel(value), value);
});

test("item_holdings rejects shape drift", () => {
  const base = panel();
  const invalid = [
    ["unknown top key", () => Object.assign(panel(), { extra: 1 })],
    ["wrong schema", () => panel({ schema_version: 2 })],
    ["schema boolean", () => panel({ schema_version: true })],
    ["unavailable form", () => panel({ available: false })],
    ["wrong kind", () => panel({ kind: "party_inventory" })],
    ["boolean giver", () => panel({ giver_id: true })],
    ["zero giver", () => panel({ giver_id: 0 })],
    ["blank item key", () => panel({ item_key: "  " })],
    ["non-string item key", () => panel({ item_key: 7 })],
    ["null item with rows", () => panel({ item_key: null })],
    ["item without rows", () => panel({ rows: [] })],
    ["rows missing giver", () => panel({ rows: [row({ member_id: 41 })] })],
    ["duplicate member", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
          row({ member_id: 7 }),
        ],
      })],
    ["unknown row key", () =>
      panel({ rows: [Object.assign(row(), { extra: 1 })] })],
    ["missing delta", () => {
      const value = clone(base);
      delete value.rows[1].delta;
      return value;
    }],
    ["delta not object", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
          row({ member_id: 41, delta: 3 }),
        ],
      })],
    ["delta boolean discriminator", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
          row({ member_id: 41, delta: { equippable: 1, changes: [] } }),
        ],
      })],
    ["equippable with reason", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
          row({
            member_id: 41,
            delta: {
              equippable: true,
              changes: [],
              reason: "accessory_slots_full",
            },
          }),
        ],
      })],
    ["refused with changes", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
          row({
            member_id: 41,
            delta: {
              equippable: false,
              reason: "accessory_slots_full",
              changes: [],
            },
          }),
        ],
      })],
    ["change zero amount", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
          row({
            member_id: 41,
            delta: fx.validItemHoldingsDelta({
              changes: [change({ amount: 0 })],
            }),
          }),
        ],
      })],
    ["change boolean amount", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
          row({
            member_id: 41,
            delta: fx.validItemHoldingsDelta({
              changes: [change({ amount: true })],
            }),
          }),
        ],
      })],
    ["change infinite amount", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
          row({
            member_id: 41,
            delta: fx.validItemHoldingsDelta({
              changes: [change({ amount: Infinity })],
            }),
          }),
        ],
      })],
    ["change unsafe amount", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
          row({
            member_id: 41,
            delta: fx.validItemHoldingsDelta({
              changes: [change({ amount: Protocol.MAX_SAFE_INTEGER + 1 })],
            }),
          }),
        ],
      })],
    ["change blank label", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
          row({
            member_id: 41,
            delta: fx.validItemHoldingsDelta({
              changes: [change({ label: " " })],
            }),
          }),
        ],
      })],
    ["too many changes", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
          row({
            member_id: 41,
            delta: fx.validItemHoldingsDelta({
              changes: Array.from(
                { length: Protocol.ITEM_HOLDINGS_MAX_CHANGES + 1 },
                () => change()
              ),
            }),
          }),
        ],
      })],
    ["enabled receive with reason", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
          row({
            member_id: 41,
            receive: fx.validItemHoldingsReceive({
              enabled: true,
              reason: "戰鬥中無法交換物品。",
            }),
          }),
        ],
      })],
    ["disabled receive without reason", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
          row({
            member_id: 41,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
        ],
      })],
    ["enabled own row", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            receive: fx.validItemHoldingsReceive({ enabled: true, reason: null }),
          }),
          row({ member_id: 41 }),
        ],
      })],
    ["negative held", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            held: -1,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
          row({ member_id: 41 }),
        ],
      })],
    ["boolean held", () =>
      panel({
        rows: [
          row({
            member_id: 7,
            held: true,
            receive: fx.validItemHoldingsReceive({
              enabled: false,
              reason: null,
            }),
          }),
          row({ member_id: 41 }),
        ],
      })],
    ["too many rows", () => {
      const rows = [];
      for (let index = 0; index < Protocol.ITEM_HOLDINGS_MAX_ROWS + 1; index += 1) {
        rows.push(
          row({
            member_id: index + 1,
            receive:
              index === 0
                ? fx.validItemHoldingsReceive({
                    enabled: false,
                    reason: null,
                  })
                : fx.validItemHoldingsReceive(),
          })
        );
      }
      return panel({ giver_id: 1, rows });
    }],
  ];
  for (const [name, build] of invalid) {
    assert.throws(
      () => Protocol.validateItemHoldingsPanel(build()),
      Error,
      name
    );
  }
});

test("item_holdings accepts its maximal bounded form", () => {
  const rows = [];
  for (let index = 0; index < Protocol.ITEM_HOLDINGS_MAX_ROWS; index += 1) {
    const changes = [];
    for (
      let changeIndex = 0;
      changeIndex < Protocol.ITEM_HOLDINGS_MAX_CHANGES;
      changeIndex += 1
    ) {
      changes.push(
        change({
          key: ("k" + changeIndex).padEnd(Protocol.ITEM_HOLDINGS_MAX_KEY, "x"),
          label: "名".repeat(Protocol.ITEM_HOLDINGS_MAX_LABEL),
          amount: 999,
        })
      );
    }
    rows.push(
      row({
        member_id: index + 1,
        held: 99,
        delta: fx.validItemHoldingsDelta({ changes }),
        receive:
          index === 0
            ? fx.validItemHoldingsReceive({ enabled: false, reason: null })
            : fx.validItemHoldingsReceive(),
      })
    );
  }
  const value = panel({
    item_key: "t".padEnd(Protocol.ITEM_HOLDINGS_MAX_KEY, "x"),
    giver_id: 1,
    rows,
  });
  assert.deepEqual(Protocol.validateItemHoldingsPanel(value), value);
  assert.ok(
    Protocol.jsonByteSize(value) <= Protocol.MAX_CANONICAL_JSON_BYTES
  );
});
