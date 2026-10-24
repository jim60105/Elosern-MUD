// shop-window-model (webclient-shop-window, design §4.3/§7): the pure
// projections the shop window reads from the committed `services` v7 `shop`
// section and the `item_holdings` v1 answer. Nothing here computes a rule:
// every price, stock, held count, delta, bound, enablement and reason is a
// server fact. The one client arithmetic is the display-only remaining purse
// (one multiplication and one subtraction or addition of committed integers),
// which the server's next snapshot always replaces.
import { formatDisplayNumber } from "../lib/display_number.js";

// The first-level tabs. `buy` lists the shelf for the recipient, `sell` the
// seller's sellable rows; the member rail chooses who.
export const SHOP_WINDOW_TABS = Object.freeze([
  Object.freeze({ key: "buy", label: "購買", glyph: "reward_copper" }),
  Object.freeze({ key: "sell", label: "出售", glyph: "give" }),
]);

export const SHOP_WINDOW_TAB_KEYS = new Set(SHOP_WINDOW_TABS.map((tab) => tab.key));

const isSafeId = (value) => Number.isSafeInteger(value) && value > 0;
const isCopper = (value) => Number.isSafeInteger(value) && value >= 0;

// The available `shop` section, or null (an unavailable panel or no shop in
// this room).
export function shopSection(services) {
  if (!services || services.available !== true) return null;
  const shop = services.shop;
  return shop && typeof shop === "object" ? shop : null;
}

// The committed recipient/seller id the rows describe, or null.
export function shopMemberId(shop) {
  return isSafeId(shop?.member_id) ? shop.member_id : null;
}

// The party purse the services panel commits (the commander's wallet), or
// null when it is not a non-negative safe integer (render nothing, never 0).
export function servicesPurse(services) {
  if (!services || services.available !== true) return null;
  const wallet = services.player?.wallet;
  return isCopper(wallet) ? wallet : null;
}

// The rows of one view in payload order.
export function viewRows(shop, view) {
  const rows = view === "sell" ? shop?.sellable : shop?.stock;
  return Array.isArray(rows) ? rows : [];
}

export function rowByKey(shop, view, key) {
  if (key === null || key === undefined) return null;
  return viewRows(shop, view).find((row) => row.item_key === key) ?? null;
}

// The row's action descriptor and unit price for its view (one price per
// view: the buy view never reads `sell_copper`, nor the sell view
// `buy_copper`).
export const actionOf = (row, view) => (view === "sell" ? row?.sell : row?.buy) ?? null;
export const unitPriceOf = (row, view) => {
  const price = view === "sell" ? row?.sell_copper : row?.buy_copper;
  return isCopper(price) ? price : null;
};

// The descriptor's committed quantity bounds, or null when it offers none
// (a disabled descriptor carries `quantity: null`).
export function quantityBounds(action) {
  const quantity = action?.quantity;
  if (!quantity || !Number.isSafeInteger(quantity.min) || !Number.isSafeInteger(quantity.max)) return null;
  if (quantity.min < 1 || quantity.max < quantity.min) return null;
  return { min: quantity.min, max: quantity.max };
}

// A typed or stepped value clamped into the bounds; anything that is not an
// integer (empty, `e`, a decimal) falls back to `fallback`, else the minimum.
export function clampQuantity(value, bounds, fallback = null) {
  if (!bounds) return null;
  const number = typeof value === "string" ? (value.trim() === "" ? NaN : Number(value)) : value;
  if (!Number.isInteger(number)) {
    return Number.isInteger(fallback) ? clampQuantity(fallback, bounds) : bounds.min;
  }
  return Math.min(Math.max(number, bounds.min), bounds.max);
}

// The server's signed amount with its shape prefix (▲/▼, never colour alone)
// and a true minus sign; the label is the server's.
export function changeText(change) {
  const shape = change.amount < 0 ? "▼" : "▲";
  const sign = change.amount < 0 ? "−" : "+";
  return `${shape} ${change.label} ${sign}${Math.abs(change.amount)}`;
}

// One committed equipment delta as display facts:
// - null delta: `{ kind: "none" }` (not equipment; the caller shows held);
// - refused: `{ kind: "blocked", code }` — 無法裝備, the stable reason code
//   kept as data only (it is never printed);
// - no change: `{ kind: "same" }` — ±0;
// - changes: `{ kind: "changes", changes: [{ key, label, amount, text, tone }] }`.
export function deltaFacts(delta) {
  if (!delta || typeof delta !== "object") return { kind: "none" };
  if (delta.equippable === false) {
    return { kind: "blocked", code: typeof delta.reason === "string" ? delta.reason : null };
  }
  const changes = Array.isArray(delta.changes) ? delta.changes : [];
  if (changes.length === 0) return { kind: "same" };
  return {
    kind: "changes",
    changes: changes.map((change) => ({
      key: change.key,
      label: change.label,
      amount: change.amount,
      text: changeText(change),
      tone: change.amount < 0 ? "down" : "up",
    })),
  };
}

// The holdings rows for the shown item, only when the committed answer is for
// exactly that item and the member the rows describe; otherwise null.
export function shopHoldings(holdings, memberId, itemKey) {
  if (!holdings || holdings.available !== true || itemKey === null || itemKey === undefined) return null;
  if (holdings.giver_id !== memberId || holdings.item_key !== itemKey) return null;
  return Array.isArray(holdings.rows) ? holdings.rows : null;
}

// The recipient's committed effective value for each changed trait, read from
// the `character` panel only while it describes that member; else null per
// trait. Nothing is added up: the comparison shows the current values beside
// the server's change lines. The value is formatted for display (a percentage
// fold arrives as 5.699999999999999 on the wire and reads 5.7).
export function currentTraitValues(character, memberId, changes) {
  const traits =
    character && character.available === true && character.member_id === memberId && Array.isArray(character.traits)
      ? character.traits
      : [];
  return changes.map((change) => {
    const trait = traits.find((row) => row?.key === change.key);
    const value =
      trait && typeof trait.effective === "number" && Number.isFinite(trait.effective)
        ? formatDisplayNumber(trait.effective)
        : null;
    return { key: change.key, label: change.label, value };
  });
}

const numberFormat = new Intl.NumberFormat("en-US");
export function formatCopper(value) {
  return numberFormat.format(value);
}

// The trade's total and the purse after it, for display only: buying spends
// unit × quantity from the purse, selling adds it. Null when any input is not
// committed.
export function tradePreview(purse, unit, quantity, view) {
  if (!isCopper(unit) || !Number.isSafeInteger(quantity) || quantity < 1) return null;
  const total = unit * quantity;
  if (!Number.isSafeInteger(total)) return null;
  if (!isCopper(purse)) return { total, remaining: null };
  return { total, remaining: view === "sell" ? purse + total : purse - total };
}
