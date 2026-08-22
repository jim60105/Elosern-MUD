<script setup>
// ShopPanel (B4 world / services family): renders the `shop` section of
// the committed `services` v1 payload — open/closed status line, stock
// rows with buy/sell copper prices and stock levels, held sellable rows,
// and the player wallet. Currency is integer copper: displayed
// thousands-separated, never float money. When the section is absent
// (`shop === null`) the panel shows only the honest wallet line plus an
// absence marker (design D2: services are hosts, not data sources — no
// invented stock/sellable rows).
import { computed, reactive } from "vue";

const props = defineProps({
  // The committed `services` v1 panel payload (or the unavailable form).
  services: { type: Object, required: true },
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

const stock = computed(() => {
  const s = shop.value;
  return s && Array.isArray(s.stock) ? s.stock : [];
});

const sellable = computed(() => {
  const s = shop.value;
  return s && Array.isArray(s.sellable) ? s.sellable : [];
});

// The wallet renders only when the payload carries a player summary with a
// wallet value; an absent player (unavailable form) must not fabricate 0.
const wallet = computed(() => {
  const w = props.services?.player?.wallet;
  return typeof w === "number" ? Math.max(0, w) : null;
});

// One quantity entry per item_key, defaulted to the action's own lower
// bound (an invented default is a fabricated value); stock and sellable
// rows for the same item share the entry.
const quantities = reactive({});
for (const row of stock.value) {
  if (!(row.item_key in quantities)) {
    quantities[row.item_key] = row.buy?.quantity?.min ?? 1;
  }
}
for (const row of sellable.value) {
  if (!(row.item_key in quantities)) {
    quantities[row.item_key] = row.sell?.quantity?.min ?? 1;
  }
}

function quantityBounds(action) {
  return { min: action?.quantity?.min ?? 1, max: action?.quantity?.max ?? Number.MAX_SAFE_INTEGER };
}

// The buy/sell intents are the exact OOB action envelope (the `action_id`
// and `payload` fields of the `ui_action` envelope; transport-level fields
// are owned by the C1 store). Only payload values are carried: the row's
// own item_key and a quantity validated against the action's quantity.min/
// max bounds.
function buyNow(row) {
  const action = row.buy;
  if (!action || !action.enabled) return;
  const { min, max } = quantityBounds(action);
  const qty = Number(quantities[row.item_key]);
  if (!Number.isInteger(qty) || qty < min || qty > max) return;
  emit("buy", { action_id: action.action_id, payload: { item_key: row.item_key, quantity: qty } });
}

function sellNow(row) {
  const action = row.sell;
  if (!action || !action.enabled) return;
  const { min, max } = quantityBounds(action);
  const qty = Number(quantities[row.item_key]);
  if (!Number.isInteger(qty) || qty < min || qty > max) return;
  emit("sell", { action_id: action.action_id, payload: { item_key: row.item_key, quantity: qty } });
}
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

    <section v-if="shop && stock.length > 0" class="shop-panel__section" data-testid="shop-panel__stock-section">
      <h4 class="shop-panel__section-title">庫存</h4>
      <div
        v-for="row in stock"
        :key="row.item_key"
        class="shop-row"
        :data-testid="`shop-panel__stock--${row.item_key}`"
      >
        <span class="shop-row__name">{{ row.display_name }}</span>
        <span class="shop-row__price">購買 {{ formatCopper(row.buy_copper) }} 銅</span>
        <span class="shop-row__price">出賣 {{ formatCopper(row.sell_copper) }} 銅</span>
        <span class="shop-row__stock">{{ row.stock }} / {{ row.max_stock }}</span>
        <input
          v-model="quantities[row.item_key]"
          class="shop-row__qty"
          type="number"
          min="1"
          :max="row.buy?.quantity?.max ?? 1"
          aria-label="購買數量"
        />
        <button
          type="button"
          class="shop-row__buy"
          :disabled="!(row.buy && row.buy.enabled)"
          @click="buyNow(row)"
        >
          {{ row.buy?.label ?? "購買" }}
        </button>
        <span
          v-if="row.buy?.disabled_reason?.message"
          class="shop-row__reason"
        >{{ row.buy.disabled_reason.message }}</span>
      </div>
    </section>

    <section v-if="shop && sellable.length > 0" class="shop-panel__section" data-testid="shop-panel__sellable-section">
      <h4 class="shop-panel__section-title">可售</h4>
      <div
        v-for="row in sellable"
        :key="row.item_key"
        class="shop-row"
        :data-testid="`shop-panel__sellable--${row.item_key}`"
      >
        <span class="shop-row__name">{{ row.display_name }}</span>
        <span class="shop-row__price">出賣 {{ formatCopper(row.sell_copper) }} 銅</span>
        <span class="shop-row__held">{{ row.held }}</span>
        <input
          v-model="quantities[row.item_key]"
          class="shop-row__qty"
          type="number"
          min="1"
          :max="row.sell?.quantity?.max ?? 1"
          aria-label="賣出數量"
        />
        <button
          type="button"
          class="shop-row__sell"
          :disabled="!(row.sell && row.sell.enabled)"
          @click="sellNow(row)"
        >
          {{ row.sell?.label ?? "賣出" }}
        </button>
        <span
          v-if="row.sell?.disabled_reason?.message"
          class="shop-row__reason"
        >{{ row.sell.disabled_reason.message }}</span>
      </div>
    </section>

    <div v-if="wallet !== null" class="shop-panel__wallet-line">
      <span class="shop-panel__wallet-label">錢包</span>
      <span class="shop-panel__wallet" data-testid="shop-panel__wallet">{{ formatCopper(wallet) }} 銅</span>
    </div>
    </template>
  </aside>
</template>

<style scoped>
.shop-panel {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  box-sizing: border-box;
  padding: var(--sp-3) var(--sp-4);
  background: var(--panel);
  border: var(--line);
  border-radius: var(--radius);
  font-family: var(--f-sans);
}

.shop-panel__title {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: 1em;
}

.shop-panel__open {
  margin: 0;
  color: var(--ok);
  font-size: 0.85em;
}

.shop-panel__open[data-open="false"] {
  color: var(--paper-500);
}

.shop-panel__unavailable {
  margin: 0;
  padding: var(--sp-1) var(--sp-2);
  color: var(--paper-500);
  font-size: 0.85em;
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}

.shop-panel__shop-absent {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.85em;
}

.shop-panel__section {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding-top: var(--sp-2);
  border-top: var(--line);
}

.shop-panel__section-title {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
  font-weight: 700;
}

.shop-row {
  display: grid;
  grid-template-columns: minmax(6em, auto) repeat(6, auto);
  gap: var(--sp-2);
  align-items: center;
  padding: var(--sp-1) 0;
  border-bottom: 1px solid var(--ink-700);
  font-size: 0.9em;
}

.shop-row__name {
  color: var(--paper-50);
}

.shop-row__price {
  color: var(--paper-50);
  font-family: var(--f-mono);
}

.shop-row__stock,
.shop-row__held {
  color: var(--paper-500);
  font-family: var(--f-mono);
}

.shop-row__qty {
  width: 4.5rem;
  padding: 2px var(--sp-1);
  color: var(--paper-50);
  background: var(--ink-820);
  border: var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--f-mono);
  font-size: 0.9em;
  text-align: right;
}

.shop-row__buy,
.shop-row__sell {
  padding: 2px var(--sp-2);
  color: var(--paper-50);
  background: var(--ink-860);
  border: 1px solid var(--seal-500);
  border-radius: var(--radius-sm);
  font-size: 0.85em;
  cursor: pointer;
}

.shop-row__buy:hover:not(:disabled),
.shop-row__sell:hover:not(:disabled) {
  border-color: var(--seal-400);
}

.shop-row__buy:disabled,
.shop-row__sell:disabled {
  color: var(--paper-500);
  border-color: var(--ink-700);
  cursor: default;
}

.shop-row__reason {
  grid-column: 1 / -1;
  color: var(--warn);
  font-size: 0.85em;
}

.shop-panel__wallet-label {
  color: var(--paper-300);
  font-size: 0.9em;
}

.shop-panel__wallet {
  color: var(--gold-500);
  font-family: var(--f-mono);
  font-size: 0.9em;
}
</style>
