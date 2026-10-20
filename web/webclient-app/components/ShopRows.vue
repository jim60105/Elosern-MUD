<script setup>
// ShopRows (webclient-shop-window, design §7): one shop view's committed rows
// as a listbox — the shop window's list column, and the price column the
// typography review measures on its own. Each row is the rarity-framed icon,
// the server display name, a sub line (庫存 n or 售完 on 購買; 持有 n on 出售)
// and an end column with the view's ONE price (buy_copper on 購買,
// sell_copper on 出售) and, on 購買, the member's committed fact: the delta
// (▲/▼ shape plus colour) or 無法裝備 (its stable code kept as data), ±0
// for a worn copy, or 持有 n for anything that is not equipment.
//
// The listbox keeps one tab stop (the selected row, else the first); the
// arrow keys, Home and End move focus; Enter, Space and click select. It
// renders and emits only: no count, price or fact is computed here.
import { computed, ref } from "vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";
import { itemIconPath, rarityLabel, unknownItemPath } from "./item-icons.js";
import { itemGlyph } from "./party-bag-model.js";
import { deltaFacts, formatCopper, unitPriceOf } from "./shop-window-model.js";

const props = defineProps({
  // The committed rows of this view (`shop.stock` or `shop.sellable`).
  rows: { type: Array, default: () => [] },
  // "buy" or "sell".
  view: { type: String, default: "buy" },
  selectedKey: { type: String, default: null },
  pendingKey: { type: String, default: null },
  // True while the rail's member request is in flight: the facts still
  // describe the previous member, so they are dimmed and marked busy.
  factsStale: { type: Boolean, default: false },
  label: { type: String, default: "商品" },
});

const emit = defineEmits(["select"]);

const listbox = ref(null);
const focusKey = computed(() =>
  props.rows.some((row) => row.item_key === props.selectedKey) ? props.selectedKey : (props.rows[0]?.item_key ?? null),
);

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
const soldOut = (row) => props.view === "buy" && row.stock === 0;
const facts = (row) => deltaFacts(row?.viewed?.delta);
const heldOf = (row) => (Number.isSafeInteger(row?.viewed?.held) ? row.viewed.held : null);
const priceText = (row) => {
  const price = unitPriceOf(row, props.view);
  return price === null ? "—" : formatCopper(price);
};

function onKeydown(event) {
  const options = [...(listbox.value?.querySelectorAll('[role="option"]') ?? [])];
  const index = options.indexOf(document.activeElement);
  if (index === -1) return;
  let next = null;
  if (event.key === "ArrowDown") next = Math.min(index + 1, options.length - 1);
  else if (event.key === "ArrowUp") next = Math.max(index - 1, 0);
  else if (event.key === "Home") next = 0;
  else if (event.key === "End") next = options.length - 1;
  if (next === null) return;
  event.preventDefault();
  options[next].focus();
}
</script>

<template>
  <div
    ref="listbox"
    class="shop-rows"
    role="listbox"
    :aria-label="label"
    :data-view="view"
    data-testid="shop-rows"
    @keydown="onKeydown"
  >
    <button
      v-for="row in rows"
      :key="row.item_key"
      type="button"
      role="option"
      class="shop-rows__row"
      :class="{
        'is-selected': row.item_key === selectedKey,
        'is-pending': row.item_key === pendingKey,
        'is-sold-out': soldOut(row),
      }"
      :data-testid="`shop-rows__row--${row.item_key}`"
      :aria-selected="row.item_key === selectedKey ? 'true' : 'false'"
      :aria-busy="row.item_key === pendingKey ? 'true' : undefined"
      :tabindex="row.item_key === focusKey ? 0 : -1"
      @click="emit('select', row.item_key)"
    >
      <span class="shop-rows__icon" :data-rarity="rarityOf(row)" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none"><path :d="iconPath(row)" stroke="currentColor" stroke-width="1.5" v-bind="iconAttrs(row)" /></svg>
      </span>
      <span class="shop-rows__main">
        <span class="shop-rows__name">{{ row.display_name }}</span>
        <span v-if="rarityWord(row)" class="shop-rows__sr">{{ rarityWord(row) }}</span>
        <span v-if="view === 'buy'" class="shop-rows__sub" :class="{ 'is-out': soldOut(row) }" data-testid="shop-rows__stock">{{
          soldOut(row) ? "售完" : `庫存 ${row.stock}`
        }}</span>
        <span v-else class="shop-rows__sub" data-testid="shop-rows__held">持有 {{ row.held }}</span>
      </span>
      <span class="shop-rows__end">
        <span class="shop-rows__price" data-testid="shop-rows__price"><span class="shop-rows__sr">{{ view === "sell" ? "賣價" : "售價" }} </span>{{ priceText(row) }}</span>
        <span
          v-if="view === 'buy'"
          class="shop-rows__fact"
          :class="{ 'is-stale': factsStale }"
          :aria-busy="factsStale ? 'true' : undefined"
          data-testid="shop-rows__fact"
        >
          <template v-if="facts(row).kind === 'blocked'">
            <span class="shop-rows__delta shop-rows__delta--none" :data-reason-code="facts(row).code || undefined" data-testid="shop-rows__delta">無法裝備</span>
          </template>
          <template v-else-if="facts(row).kind === 'same'">
            <span class="shop-rows__delta shop-rows__delta--none" data-testid="shop-rows__delta">±0</span>
          </template>
          <template v-else-if="facts(row).kind === 'changes'">
            <span
              v-for="change in facts(row).changes"
              :key="change.key"
              class="shop-rows__delta"
              :class="`is-${change.tone}`"
              data-testid="shop-rows__delta"
            >{{ change.text }}</span>
          </template>
          <span v-else class="shop-rows__held" data-testid="shop-rows__member-held">持有 {{ heldOf(row) ?? 0 }}</span>
        </span>
      </span>
    </button>
  </div>
</template>

<style scoped>
/* The approved prototype's `.pm-row`, `.pm-icon`, `.pm-row__end` and
   `.pm-row__price` (docs/design/party-member-management/prototype.css), with
   the bag tab's non-colour rarity border patterns. */
.shop-rows {
  --shop-rows-line-soft: rgba(185, 154, 96, 0.14);
  --rarity-common: #6b665c;
  --rarity-uncommon: #8fb07c;
  --rarity-rare: #6f95e6;
  --rarity-epic: #b27fdb;
  --rarity-legendary: var(--gold-500);
  display: flex;
  flex-direction: column;
  gap: calc(2px * var(--ui-scale));
}

.shop-rows__row {
  position: relative;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: var(--sp-3);
  align-items: center;
  width: 100%;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-100);
  font: var(--text-sm) var(--f-sans);
  text-align: left;
  background: transparent;
  border: calc(1px * var(--ui-scale)) solid transparent;
  border-bottom: calc(1px * var(--ui-scale)) dashed var(--shop-rows-line-soft);
  border-radius: 0;
  cursor: pointer;
  transition: background-color var(--motion-fast) ease, border-color var(--motion-fast) ease;
}

.shop-rows__row:hover {
  background: rgba(255, 255, 255, 0.03);
}

.shop-rows__row:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.shop-rows__row.is-selected {
  background: linear-gradient(90deg, rgba(207, 68, 68, 0.22), rgba(228, 200, 142, 0.05));
  border: calc(1px * var(--ui-scale)) solid var(--seal-700);
  border-radius: var(--radius-sm);
  box-shadow: inset calc(3px * var(--ui-scale)) 0 0 var(--seal-500);
}

.shop-rows__row.is-pending {
  border-style: dashed;
  opacity: 0.8;
}

/* 售完 dims the row but keeps it selectable: its committed reason is still
   readable in the action bar. */
.shop-rows__row.is-sold-out .shop-rows__icon,
.shop-rows__row.is-sold-out .shop-rows__name,
.shop-rows__row.is-sold-out .shop-rows__price {
  opacity: 0.5;
}

.shop-rows__icon {
  display: grid;
  place-items: center;
  box-sizing: border-box;
  width: calc(34px * var(--ui-scale));
  height: calc(34px * var(--ui-scale));
  color: var(--gold-400);
  background: radial-gradient(circle at 50% 35%, rgba(185, 154, 96, 0.12), rgba(0, 0, 0, 0.3) 75%);
  border: calc(1px * var(--ui-scale)) solid var(--rarity-common);
  border-radius: var(--radius-sm);
}

.shop-rows__icon svg {
  width: calc(20px * var(--ui-scale));
  height: calc(20px * var(--ui-scale));
}

.shop-rows__icon[data-rarity="uncommon"],
.shop-rows__icon[data-rarity="rare"],
.shop-rows__icon[data-rarity="epic"],
.shop-rows__icon[data-rarity="legendary"] {
  background: radial-gradient(circle at 50% 35%, color-mix(in srgb, var(--icon-rarity) 18%, transparent), rgba(0, 0, 0, 0.3) 75%);
}

.shop-rows__icon[data-rarity="uncommon"] { --icon-rarity: var(--rarity-uncommon); border: calc(2px * var(--ui-scale)) dotted var(--rarity-uncommon); }
.shop-rows__icon[data-rarity="rare"] { --icon-rarity: var(--rarity-rare); border: calc(2px * var(--ui-scale)) dashed var(--rarity-rare); }
.shop-rows__icon[data-rarity="epic"] { --icon-rarity: var(--rarity-epic); border: calc(3px * var(--ui-scale)) double var(--rarity-epic); }
.shop-rows__icon[data-rarity="legendary"] { --icon-rarity: var(--rarity-legendary); border: calc(3px * var(--ui-scale)) ridge var(--rarity-legendary); }

.shop-rows__main {
  display: grid;
  gap: calc(2px * var(--ui-scale));
  min-width: 0;
}

.shop-rows__name {
  overflow: hidden;
  color: var(--paper-50);
  font: var(--text-sm) var(--f-serif);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.shop-rows__sub {
  color: var(--paper-500);
  font: var(--text-xs) var(--f-sans);
  font-variant-numeric: tabular-nums lining-nums;
}

.shop-rows__sub.is-out {
  color: var(--debuff);
}

.shop-rows__end {
  display: grid;
  justify-items: end;
  gap: calc(2px * var(--ui-scale));
  white-space: nowrap;
}

.shop-rows__price {
  color: var(--gold-300);
  font: var(--text-sm) var(--f-num);
  font-variant-numeric: tabular-nums lining-nums;
  text-align: right;
}

.shop-rows__fact {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0 var(--sp-2);
  max-width: calc(200px * var(--ui-scale));
  transition: opacity var(--motion-fast) ease;
}

.shop-rows__fact.is-stale {
  opacity: 0.35;
}

.shop-rows__delta,
.shop-rows__held {
  color: var(--paper-400);
  font: var(--text-xs) var(--f-num);
  font-variant-numeric: tabular-nums lining-nums;
}

.shop-rows__delta.is-up {
  color: var(--buff);
}

.shop-rows__delta.is-down {
  color: var(--debuff);
}

.shop-rows__delta--none {
  color: var(--paper-500);
}

.shop-rows__sr {
  position: absolute;
  width: calc(1px * var(--ui-scale));
  height: calc(1px * var(--ui-scale));
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

@media (prefers-reduced-motion: reduce) {
  .shop-rows__row,
  .shop-rows__fact {
    transition: none;
  }
}
</style>
