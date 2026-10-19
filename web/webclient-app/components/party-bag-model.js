// party-bag-model (webclient-party-bag-tab, design §6.2): the pure
// projections the party window's 背包 tab reads from the committed
// `party_inventory` and `item_holdings` panels. Nothing here computes a rule:
// every enablement, reason, count and delta is a server fact, and every
// label is client display copy.

// The doll's four slots in prototype order. `key` is the `party_inventory`
// row `slot` value (and, but for the accessory list, the equipment field).
export const DOLL_SLOTS = Object.freeze([
  Object.freeze({ key: "weapon_main", label: "主手", glyph: "sword" }),
  Object.freeze({ key: "weapon_off", label: "副手", glyph: "shield" }),
  Object.freeze({ key: "armor", label: "盔甲", glyph: "armor" }),
  Object.freeze({ key: "accessory", label: "飾品", glyph: "amulet" }),
]);

const SLOT_LABELS = Object.freeze(Object.fromEntries(DOLL_SLOTS.map((slot) => [slot.key, slot.label])));

// The `party.transfer` payload's quantity bound (MAX_TRANSFER_QUANTITY in
// web/webclient/actions/party_actions.py): a wire limit, not a rule. A give
// never asks for more than one request may carry.
export const TRANSFER_QUANTITY_MAX = 99;

export function slotLabel(slot) {
  return SLOT_LABELS[slot] ?? null;
}

export function bagRows(inventory) {
  return inventory?.available === true && Array.isArray(inventory.rows) ? inventory.rows : [];
}

export function rowByKey(inventory, key) {
  if (key === null || key === undefined) return null;
  return bagRows(inventory).find((row) => row.item_key === key) ?? null;
}

// A worn item's committed display name (its own bag row), else the key.
function wornName(inventory, key) {
  return rowByKey(inventory, key)?.display_name ?? key;
}

// The doll's cells: each slot's committed occupant names (accessories in
// their worn order) and, for the accessory cell, the count out of the limit.
export function dollCells(inventory) {
  const equipment = inventory?.available === true ? inventory.equipment : null;
  if (!equipment) return [];
  return DOLL_SLOTS.map((slot) => {
    const keys =
      slot.key === "accessory"
        ? equipment.accessories
        : equipment[slot.key] === null
          ? []
          : [equipment[slot.key]];
    return {
      ...slot,
      keys,
      names: keys.map((key) => wornName(inventory, key)),
      rarity: keys.length === 1 ? (rowByKey(inventory, keys[0])?.presentation?.rarity ?? null) : null,
      count: slot.key === "accessory" ? `${keys.length}/${equipment.accessory_limit}` : null,
    };
  });
}

// The 裝備 button's label for an equipment row: 卸下 for a worn copy, else
// 裝備 naming the singleton occupant the toggle replaces. An accessory is
// added beside the others, so it never names a client-chosen accessory.
export function toggleLabel(inventory, row) {
  if (!row || row.slot === null) return null;
  if (row.equipped_count > 0) return "卸下";
  if (row.slot === "accessory") return "裝備";
  const occupant = inventory?.equipment?.[row.slot] ?? null;
  if (occupant === null || occupant === row.item_key) return "裝備";
  return `裝備（替換 ${wornName(inventory, occupant)}）`;
}

// How many one give may move: equipment gives one; otherwise the row's
// committed unequipped count, within the request's quantity bound.
export function giveBound(row) {
  if (!row || row.give?.enabled !== true) return 0;
  if (row.slot !== null) return 1;
  return Math.max(0, Math.min(row.give.max_quantity, TRANSFER_QUANTITY_MAX));
}

export function clampQuantity(value, bound) {
  if (bound < 1) return 1;
  const number = Number.isSafeInteger(value) ? value : 1;
  return Math.min(Math.max(number, 1), bound);
}

// The holdings rows for the shown item, only when the committed panel
// answers exactly that item for the viewed member; otherwise null.
export function holdingsFor(holdings, memberId, itemKey) {
  if (!holdings || holdings.available !== true || itemKey === null) return null;
  if (holdings.giver_id !== memberId || holdings.item_key !== itemKey) return null;
  return holdings.rows;
}

// The bag's richer local glyphs (dock-icons.js, the prototype's set) for the
// committed `presentation.icon_key` values that have one; any other key keeps
// the shared item-icons.js map and its neutral unknown fallback.
const ICON_GLYPHS = Object.freeze({
  potion: "potion",
  weapon: "sword",
  armor: "armor",
  accessory: "amulet",
  food: "ration",
  material: "herb",
  ammunition: "bow",
  tool: "hammer",
});

export function itemGlyph(row) {
  const key = row?.presentation?.icon_key;
  return typeof key === "string" ? (ICON_GLYPHS[key] ?? null) : null;
}
