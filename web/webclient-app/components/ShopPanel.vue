<script setup>
// ShopPanel (B4 world / services family): the transitional shop drawer over
// the committed `services` v7 `shop` section until the shop window lands.
// The rows describe the session's viewed party member (`shop.member_id`,
// chosen by `party.view_member`, falling back to the commander):
//
// - 貨架 (stock): icon framed by rarity, name, stock level (or 售完), the
//   buy price only, and that member's server facts — the equipment delta
//   (▲/▼ shape plus colour, never colour alone; 無法裝備 when the toggle
//   rule refuses) or the held count for anything that is not equipment.
// - 可出售 (sellable): that member's unequipped copies with the sell price
//   only.
//
// Every trade names `shop.member_id` as its recipient or seller; the server
// reauthorizes it. Currency is integer copper, thousands-separated for
// display only. When the section is absent (`shop === null`) the panel shows
// only an absence marker (no invented stock or sellable rows). The panel
// computes no delta, count, price or enablement.
import { computed, reactive, ref, watch } from "vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";
import { itemIconPath, rarityLabel, unknownItemPath } from "./item-icons.js";
import { itemGlyph } from "./party-bag-model.js";

const props = defineProps({
  // The committed `services` v7 panel payload (or the unavailable form).
  services: { type: Object, required: true },
  // The display name of `shop.member_id` from the committed `party` panel,
  // or null; it only labels the sections.
  memberName: { type: String, default: null },
});

const emit = defineEmits(["buy", "sell"]);

// Integer copper, thousands-separated for display only (no float money).
function formatCopper(value) {
  return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// The registry-owned unavailable form (available: false) carries only the
// reason — no sections, no default wallet (no invented 0-copper value).
const unavailable = computed(() => props.services?.available === false);

const shop = computed(() => (unavailable.value ? null : (props.services?.shop ?? null)));

// The committed recipient/seller: a positive safe integer, else none (the
// exact payloads require one, so a malformed id emits nothing).
const memberId = computed(() => {
  const value = shop.value?.member_id;
  return Number.isSafeInteger(value) && value > 0 ? value : null;
});

const stock = computed(() => {
  const s = shop.value;
  return s && Array.isArray(s.stock) ? s.stock : [];
});

const sellable = computed(() => {
  const s = shop.value;
  return s && Array.isArray(s.sellable) ? s.sellable : [];
});

const stockTitle = computed(() => (props.memberName ? `為${props.memberName}挑選` : "貨架"));
const sellableTitle = computed(() => (props.memberName ? `${props.memberName}可出售的物品` : "可出售的物品"));

// The row's glyph: the bag's local glyph for its committed icon key, else
// the shared item icon, else the neutral unknown icon.
function iconPath(row) {
  const glyph = itemGlyph(row);
  if (glyph) return glyphPath(glyph);
  return (row?.presentation && itemIconPath(row.presentation.icon_key)) || unknownItemPath();
}
function iconAttrs(row) {
  const glyph = itemGlyph(row);
  return glyph ? glyphAttrs(glyph) : {};
}
const rarityOf = (row) => row?.presentation?.rarity || "unknown";
const rarityWord = (row) => (row?.presentation ? rarityLabel(row.presentation.rarity) : null);

// The server's signed amount with its shape prefix and a true minus sign;
// the label is the server's.
function changeText(change) {
  const shape = change.amount < 0 ? "▼" : "▲";
  const sign = change.amount < 0 ? "−" : "+";
  return `${shape} ${change.label} ${sign}${Math.abs(change.amount)}`;
}
const deltaOf = (row) => row?.viewed?.delta ?? null;
const heldOf = (row) => (Number.isSafeInteger(row?.viewed?.held) ? row.viewed.held : null);

// H4 (task 7.1): the shop drawer no longer renders the wallet line; the
// wallet now lives in the CharacterStatusDrawer (the single wallet rendering
// across the drawer layer, task 7.7).

// One quantity entry per item_key, defaulted to the action's own lower
// bound (an invented default is a fabricated value); stock and sellable
// rows for the same item share the entry.
function quantityBounds(action) {
  return { min: action?.quantity?.min ?? 1, max: action?.quantity?.max ?? 1 };
}

const quantities = reactive({});

function resetQuantities() {
  for (const key of Object.keys(quantities)) {
    delete quantities[key];
  }
  for (const row of stock.value) {
    if (!(row.item_key in quantities)) {
      quantities[row.item_key] = quantityBounds(row.buy).min;
    }
  }
  for (const row of sellable.value) {
    if (!(row.item_key in quantities)) {
      quantities[row.item_key] = quantityBounds(row.sell).min;
    }
  }
}
resetQuantities();

// The per-row quantity form (Phase-0 audit §2.3 REMAP-TO-TESTID): the
// `services-quantity` wrapper and `services-quantity-value` display are
// served as `data-testid` on the Vue quantity control. The form is open for
// the activated row only; selection comes from row focus or click only.
// A replaced `services` panel (a reconnect resync, or a new viewed member)
// rebuilds the per-item entries from canonical persistence, re-defaulting
// every entry to its action's own lower bound.
const selectedKey = ref(null);

watch(() => props.services, resetQuantities);

function activateRow(row) {
  selectedKey.value = row.item_key;
}

function clampQuantity(row, action) {
  const { min, max } = quantityBounds(action);
  const raw = Number(quantities[row.item_key]);
  if (!Number.isInteger(raw) || raw < min) {
    quantities[row.item_key] = min;
  } else if (raw > max) {
    quantities[row.item_key] = max;
  }
}

// The buy/sell intents are the exact OOB action envelope (the `action_id`
// and `payload` fields of the `ui_action` envelope; transport-level fields
// are owned by the C1 store): the row's own item_key, a quantity within the
// action's own bounds, and the committed member.
function trade(row, action, memberField, event) {
  if (!action || !action.enabled) return;
  const { min, max } = quantityBounds(action);
  const qty = Number(quantities[row.item_key]);
  if (!Number.isInteger(qty) || qty < min || qty > max) return;
  const member = memberId.value;
  if (member === null) return;
  emit(event, {
    action_id: action.action_id,
    payload: { item_key: row.item_key, quantity: qty, [memberField]: member },
  });
  selectedKey.value = null;
}

const buyNow = (row) => trade(row, row.buy, "recipient_id", "buy");
const sellNow = (row) => trade(row, row.sell, "seller_id", "sell");
</script>

<template>
  <aside class="shop-panel" data-testid="shop-panel">
    <h3 class="shop-panel__title" data-testid="shop-panel__title">商店</h3>

    <p
      v-if="unavailable"
      class="shop-panel__unavailable"
      data-testid="shop-panel__unavailable"
      :data-reason-code="services.reason?.code"
    >
      {{ services.reason?.message }}
    </p>

    <template v-else>
      <p
        v-if="shop"
        class="shop-panel__open"
        data-testid="shop-panel__open"
        :data-open="String(shop.open)"
      >
        {{ shop.open ? "營業中" : "已打烊" }}
      </p>

      <p v-if="shop === null" class="shop-panel__shop-absent" data-testid="shop-panel__shop-absent">
        目前沒有營業中的商店
      </p>

      <div v-if="shop" class="shop-panel__trade">
      <section v-if="stock.length > 0" class="shop-panel__section shop-panel__section--stock" data-testid="shop-panel__stock-section">
        <h4 class="shop-panel__section-title">
          <span data-testid="shop-panel__stock-title">{{ stockTitle }}</span>
          <span class="shop-panel__count">{{ stock.length }}</span>
        </h4>
        <div
          v-for="row in stock"
          :key="row.item_key"
          class="shop-row"
          :class="{ 'is-sold-out': row.stock === 0, 'is-active': selectedKey === row.item_key }"
          :data-testid="`shop-panel__stock--${row.item_key}`"
          @click="activateRow(row)"
          @focusin="activateRow(row)"
        >
          <span class="shop-row__icon" :data-rarity="rarityOf(row)" :title="rarityWord(row) ?? undefined" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none"><path :d="iconPath(row)" stroke="currentColor" stroke-width="1.5" v-bind="iconAttrs(row)" /></svg>
          </span>
          <span class="shop-row__name">{{ row.display_name }}</span>
          <span class="shop-row__sub">
            <span v-if="row.stock > 0" class="shop-row__stock">庫存 {{ row.stock }} / {{ row.max_stock }}</span>
            <span v-else class="shop-row__stock shop-row__stock--out">售完</span>
          </span>
          <span class="shop-row__viewed" data-testid="shop-row__viewed">
            <template v-if="deltaOf(row)?.equippable === false">
              <span class="shop-row__delta shop-row__delta--none" data-testid="shop-row__delta">無法裝備</span>
            </template>
            <template v-else-if="deltaOf(row)">
              <span v-if="deltaOf(row).changes.length === 0" class="shop-row__delta shop-row__delta--none" data-testid="shop-row__delta">±0</span>
              <span
                v-for="change in deltaOf(row).changes"
                :key="change.key"
                class="shop-row__delta"
                :class="change.amount < 0 ? 'is-down' : 'is-up'"
                data-testid="shop-row__delta"
              >{{ changeText(change) }}</span>
            </template>
            <span
              v-if="!deltaOf(row) || heldOf(row) > 0"
              class="shop-row__held"
              data-testid="shop-row__held"
            >持有 {{ heldOf(row) ?? 0 }}</span>
          </span>
          <span class="shop-row__price">{{ formatCopper(row.buy_copper) }} 銅</span>
          <span
            class="shop-row__qty-wrap"
            :data-testid="selectedKey === row.item_key ? 'services-quantity' : undefined"
          >
            <input
              v-model="quantities[row.item_key]"
              class="shop-row__qty"
              type="number"
              :min="quantityBounds(row.buy).min"
              :max="quantityBounds(row.buy).max"
              aria-label="購買數量"
              @change="clampQuantity(row, row.buy)"
              @blur="clampQuantity(row, row.buy)"
            />
            <span
              class="shop-row__qty-value"
              :data-testid="selectedKey === row.item_key ? 'services-quantity-value' : undefined"
            >{{ quantities[row.item_key] }}</span>
          </span>
          <button
            type="button"
            class="shop-row__buy"
            :disabled="!(row.buy && row.buy.enabled)"
            @click.stop="buyNow(row)"
          >
            {{ row.buy?.label ?? "購買" }}
          </button>
          <span
            v-if="row.buy?.disabled_reason?.message"
            class="shop-row__reason"
          >{{ row.buy.disabled_reason.message }}</span>
        </div>
      </section>

      <section v-if="sellable.length > 0" class="shop-panel__section shop-panel__section--sellable" data-testid="shop-panel__sellable-section">
        <h4 class="shop-panel__section-title">
          <span data-testid="shop-panel__sellable-title">{{ sellableTitle }}</span>
          <span class="shop-panel__count">{{ sellable.length }}</span>
        </h4>
        <div
          v-for="row in sellable"
          :key="row.item_key"
          class="shop-row"
          :class="{ 'is-active': selectedKey === row.item_key }"
          :data-testid="`shop-panel__sellable--${row.item_key}`"
          @click="activateRow(row)"
          @focusin="activateRow(row)"
        >
          <span class="shop-row__icon" :data-rarity="rarityOf(row)" :title="rarityWord(row) ?? undefined" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none"><path :d="iconPath(row)" stroke="currentColor" stroke-width="1.5" v-bind="iconAttrs(row)" /></svg>
          </span>
          <span class="shop-row__name">{{ row.display_name }}</span>
          <span class="shop-row__sub">
            <span class="shop-row__held">可售 {{ row.held }}</span>
          </span>
          <span class="shop-row__viewed" />
          <span class="shop-row__price">{{ formatCopper(row.sell_copper) }} 銅</span>
          <span
            class="shop-row__qty-wrap"
            :data-testid="selectedKey === row.item_key ? 'services-quantity' : undefined"
          >
            <input
              v-model="quantities[row.item_key]"
              class="shop-row__qty"
              type="number"
              :min="quantityBounds(row.sell).min"
              :max="quantityBounds(row.sell).max"
              aria-label="賣出數量"
              @change="clampQuantity(row, row.sell)"
              @blur="clampQuantity(row, row.sell)"
            />
            <span
              class="shop-row__qty-value"
              :data-testid="selectedKey === row.item_key ? 'services-quantity-value' : undefined"
            >{{ quantities[row.item_key] }}</span>
          </span>
          <button
            type="button"
            class="shop-row__sell"
            :disabled="!(row.sell && row.sell.enabled)"
            @click.stop="sellNow(row)"
          >
            {{ row.sell?.label ?? "賣出" }}
          </button>
          <span
            v-if="row.sell?.disabled_reason?.message"
            class="shop-row__reason"
          >{{ row.sell.disabled_reason.message }}</span>
        </div>
      </section>
      </div>
    </template>
  </aside>
</template>

<style scoped>
/* Drawer-body surface after the approved shop prototype
   (docs/design/party-member-management/ShopPrototype.vue, prototype.css
   `.pm-sech`, `.pm-row`, `.pm-icon`): charcoal list lines with an icon
   framed by rarity, a fluid name column, the viewed member's facts and one
   right-aligned price column shared by every row. */
.shop-panel {
  --shop-line: rgba(185, 154, 96, 0.28);
  --shop-line-soft: rgba(185, 154, 96, 0.14);
  --rarity-common: #6b665c;
  --rarity-uncommon: #8fb07c;
  --rarity-rare: #6f95e6;
  --rarity-epic: #b27fdb;
  --rarity-legendary: var(--gold-500);
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  min-width: 0;
  box-sizing: border-box;
  font-family: var(--f-sans);
}

/* The drawer spans the workspace: at desktop widths the shelf (the wider
   column, it carries the member's facts) and the sellable list sit side by
   side, and they stack when the drawer is narrow. */
.shop-panel__trade {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: var(--sp-4);
  min-width: 0;
}

/* Bounded so a row's name, facts and price stay one glance apart on a
   wide drawer. */
.shop-panel__section--stock {
  flex: 3 1 calc(440px * var(--ui-scale));
  max-width: calc(760px * var(--ui-scale));
}

.shop-panel__section--sellable {
  flex: 2 1 calc(360px * var(--ui-scale));
  max-width: calc(560px * var(--ui-scale));
}

.shop-panel__title {
  margin: 0;
  color: var(--paper-500);
  font-size: var(--text-xs);
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.shop-panel__open {
  margin: 0;
  color: var(--ok);
  font-size: max(var(--text-xs), 0.85em);
}

.shop-panel__open[data-open="false"] {
  color: var(--paper-500);
}

.shop-panel__unavailable {
  margin: 0;
  padding: var(--sp-1) var(--sp-2);
  color: var(--paper-500);
  font-size: max(var(--text-xs), 0.85em);
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}

.shop-panel__shop-absent {
  margin: 0;
  color: var(--paper-500);
  font-size: max(var(--text-xs), 0.85em);
}

/* One grid per section; rows are subgrids so the facts, price, quantity and
   action columns align across every row as values change. */
.shop-panel__section {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr) max-content max-content;
  gap: 0 var(--sp-3);
  min-width: 0;
  padding: var(--sp-2) var(--sp-3) var(--sp-3);
  background: linear-gradient(130deg, rgba(34, 36, 38, 0.44), rgba(16, 18, 21, 0.75));
  border: var(--line);
  border-radius: var(--radius);
}

.shop-panel__section-title {
  display: flex;
  grid-column: 1 / -1;
  align-items: baseline;
  justify-content: space-between;
  margin: 0 0 var(--sp-1);
  padding: var(--sp-1) 0 var(--sp-2);
  border-bottom: 1px solid var(--shop-line);
  color: var(--gold-400);
  font-family: var(--f-serif);
  font-size: var(--text-base);
  letter-spacing: 0.04em;
}

.shop-panel__count {
  color: var(--paper-500);
  font-family: var(--f-num);
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
}

.shop-row {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: subgrid;
  grid-template-rows: auto auto;
  row-gap: calc(2px * var(--ui-scale));
  align-items: center;
  min-width: 0;
  margin: 0 calc(-1 * var(--sp-2));
  padding: var(--sp-2);
  border-bottom: 1px solid var(--shop-line-soft);
  border-radius: var(--radius-sm);
  font-size: max(var(--text-xs), 0.9em);
  transition: background-color var(--motion-fast) ease;
}

.shop-row:last-child {
  border-bottom: 0;
}

.shop-row:hover,
.shop-row.is-active {
  background: linear-gradient(90deg, rgba(207, 68, 68, 0.14), rgba(228, 200, 142, 0.04));
}

.shop-row.is-active {
  box-shadow: inset calc(3px * var(--ui-scale)) 0 0 var(--seal-500);
}

.shop-row.is-sold-out .shop-row__icon,
.shop-row.is-sold-out .shop-row__name {
  opacity: 0.55;
}

.shop-row__icon {
  display: grid;
  grid-row: 1 / span 2;
  grid-column: 1;
  place-items: center;
  box-sizing: border-box;
  width: calc(34px * var(--ui-scale));
  height: calc(34px * var(--ui-scale));
  color: var(--gold-400);
  background: radial-gradient(circle at 50% 35%, rgba(185, 154, 96, 0.12), rgba(0, 0, 0, 0.3) 75%);
  border: calc(1px * var(--ui-scale)) solid var(--rarity-common);
  border-radius: var(--radius-sm);
}

.shop-row__icon svg {
  width: calc(20px * var(--ui-scale));
  height: calc(20px * var(--ui-scale));
}

/* Rarity is a border pattern as well as a colour (the bag tab's rule). */
.shop-row__icon[data-rarity="uncommon"],
.shop-row__icon[data-rarity="rare"],
.shop-row__icon[data-rarity="epic"],
.shop-row__icon[data-rarity="legendary"] {
  background: radial-gradient(circle at 50% 35%, color-mix(in srgb, var(--icon-rarity) 18%, transparent), rgba(0, 0, 0, 0.3) 75%);
}

.shop-row__icon[data-rarity="uncommon"] { --icon-rarity: var(--rarity-uncommon); border: calc(2px * var(--ui-scale)) dotted var(--rarity-uncommon); }
.shop-row__icon[data-rarity="rare"] { --icon-rarity: var(--rarity-rare); border: calc(2px * var(--ui-scale)) dashed var(--rarity-rare); }
.shop-row__icon[data-rarity="epic"] { --icon-rarity: var(--rarity-epic); border: calc(3px * var(--ui-scale)) double var(--rarity-epic); }
.shop-row__icon[data-rarity="legendary"] { --icon-rarity: var(--rarity-legendary); border: calc(3px * var(--ui-scale)) ridge var(--rarity-legendary); }

.shop-row__name {
  grid-row: 1;
  grid-column: 2;
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--paper-50);
  font-family: var(--f-serif);
  font-size: max(var(--text-sm), 0.95em);
}

.shop-row__sub {
  grid-row: 2;
  grid-column: 2;
  min-width: 0;
}

.shop-row__stock,
.shop-row__held {
  color: var(--paper-500);
  font-family: var(--f-num);
  font-size: var(--text-xs);
  white-space: nowrap;
  font-variant-numeric: tabular-nums lining-nums;
}

.shop-row__stock--out {
  color: var(--debuff);
}

/* The viewed member's facts: delta chips or the held count. */
.shop-row__viewed {
  display: flex;
  flex-wrap: wrap;
  grid-row: 1;
  grid-column: 3;
  gap: calc(2px * var(--ui-scale)) var(--sp-2);
  justify-content: flex-end;
  max-width: calc(180px * var(--ui-scale));
}

.shop-row__delta {
  font-family: var(--f-num);
  font-size: var(--text-xs);
  white-space: nowrap;
  font-variant-numeric: tabular-nums lining-nums;
}

.shop-row__delta.is-up {
  color: var(--buff);
}

.shop-row__delta.is-down {
  color: var(--debuff);
}

.shop-row__delta--none {
  color: var(--paper-500);
}

.shop-row__price {
  grid-row: 1;
  grid-column: 4;
  color: var(--gold-400);
  font-family: var(--f-num);
  white-space: nowrap;
  font-variant-numeric: tabular-nums lining-nums;
  text-align: right;
}

/* The quantity editor rides with the action on the row's second line. */
.shop-row__qty-wrap {
  grid-row: 2;
  grid-column: 3;
  justify-self: end;
}

/* The committed quantity readout stays in the DOM for assistive and
   browser-test reads, while the input itself shows the value. */
.shop-row__qty-value {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.shop-row__qty {
  width: calc(64px * var(--ui-scale));
  padding: calc(2px * var(--ui-scale)) var(--sp-1);
  color: var(--paper-50);
  background: var(--ink-820);
  border: var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--f-num);
  font-size: max(var(--text-xs), 0.9em);
  text-align: right;
  font-variant-numeric: tabular-nums lining-nums;
}

.shop-row__qty:focus-visible,
.shop-row__buy:focus-visible,
.shop-row__sell:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

/* Buy/sell are the row's decisive actions: gold emphasis chrome. */
.shop-row__buy,
.shop-row__sell {
  grid-row: 2;
  grid-column: 4;
  justify-self: end;
  min-height: calc(26px * var(--ui-scale));
  padding: 0 var(--sp-3);
  color: var(--gold-400);
  background: linear-gradient(rgba(185, 154, 96, 0.16), rgba(185, 154, 96, 0.06));
  border: 1px solid var(--gold-500);
  border-radius: var(--radius-sm);
  font-family: var(--f-sans);
  font-size: max(var(--text-xs), 0.85em);
  cursor: pointer;
  white-space: nowrap;
}

.shop-row__buy:hover:not(:disabled),
.shop-row__sell:hover:not(:disabled) {
  color: var(--paper-50);
  border-color: var(--gold-400);
}

.shop-row__buy:disabled,
.shop-row__sell:disabled {
  color: var(--paper-500);
  background: var(--ink-820);
  border-color: var(--ink-700);
  cursor: default;
}

/* Disabled reasons are cautionary guidance, not errors: warn tone. */
.shop-row__reason {
  grid-row: 3;
  grid-column: 2 / -1;
  min-width: 0;
  color: var(--warn);
  font-size: max(var(--text-xs), 0.85em);
  text-align: right;
  overflow-wrap: anywhere;
}
</style>
