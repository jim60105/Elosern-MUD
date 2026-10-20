// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// ---------------------------------------------------------------------------
// webclient-window-primitives: the shared window primitives' offline args.
// ---------------------------------------------------------------------------
// The member rail reads plain props mapped from `party` v3 summary rows
// (commander first, then companions in party order); the holdings strip
// reads `item_holdings` v1 rows verbatim. Names follow the approved
// prototype (docs/design/party-member-management/prototype-data.js).

// `party` v3 summary rows, trimmed to the fields the rail maps.
export const WINDOW_PARTY_ROWS = [
  { identity: 11, display_name: "莉瑟", role: "commander", portrait: "/art/defaults/woman.webp", knocked_out: false, unread: false },
  { identity: 12, display_name: "艾拉", role: "companion", portrait: "/art/defaults/girl.webp", knocked_out: false, unread: true },
  { identity: 13, display_name: "卡恩", role: "companion", portrait: null, knocked_out: true, unread: false },
];

// The rail's plain props (design: id, name, portrait, knockedOut, unread).
export const WINDOW_RAIL_MEMBERS = WINDOW_PARTY_ROWS.map((row) => ({
  id: row.identity,
  name: row.display_name,
  portrait: row.portrait,
  knockedOut: row.knocked_out,
  unread: row.unread,
}));

const receive = (enabled, reason = null) => ({ enabled, reason });

// A consumable (no deltas): 莉瑟 views her own 治療藥水; 卡恩 is in another
// room, so his cell carries the transfer preflight's reason.
export const ITEM_HOLDINGS_CONSUMABLE = {
  schema_version: 1,
  available: true,
  kind: "item_holdings",
  item_key: "potion_heal",
  giver_id: 11,
  rows: [
    { member_id: 11, held: 5, equipped: false, delta: null, receive: receive(false) },
    { member_id: 12, held: 2, equipped: false, delta: null, receive: receive(true) },
    { member_id: 13, held: 0, equipped: false, delta: null, receive: receive(false, "對方不在這裡。") },
  ],
};

// Equipment: 莉瑟's 鋼製短劍 against each member's main-hand occupant — an
// upgrade, a downgrade, and a member who cannot wield it.
export const ITEM_HOLDINGS_EQUIPMENT = {
  schema_version: 1,
  available: true,
  kind: "item_holdings",
  item_key: "steel_shortsword",
  giver_id: 11,
  rows: [
    { member_id: 11, held: 1, equipped: false, delta: { equippable: true, changes: [{ key: "atk_phys", label: "攻擊", amount: 2 }] }, receive: receive(false) },
    {
      member_id: 12,
      held: 0,
      equipped: false,
      delta: { equippable: true, changes: [{ key: "atk_phys", label: "攻擊", amount: 6 }, { key: "agility", label: "敏捷", amount: -1 }] },
      receive: receive(true),
    },
    { member_id: 13, held: 0, equipped: false, delta: { equippable: false, reason: "malformed_equipment" }, receive: receive(true) },
  ],
};

// The same consumable during combat: every receive is disabled with the
// committed combat reason, and the strip shows counts only.
export const ITEM_HOLDINGS_COMBAT = {
  ...ITEM_HOLDINGS_CONSUMABLE,
  rows: ITEM_HOLDINGS_CONSUMABLE.rows.map((row, index) => ({
    ...row,
    receive: index === 0 ? receive(false) : receive(false, "戰鬥中無法交換物品。"),
  })),
};
