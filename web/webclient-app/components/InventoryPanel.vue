<script setup>
// InventoryPanel (B4 world / services family): renders the `inventory`
// section of the committed `services` v1 payload. By design D2 (services
// are hosts, not data sources) the panel renders ONLY the equipped rows
// (`equipped === true`); a full inventory bag is deferred (no backing
// read model), so the non-equipped rows never render. Currency is integer
// copper: `inventory.wallet` is displayed thousands-separated, never float
// money. When the section is absent (`inventory === null`) the panel
// renders an honest empty state instead of inventing bag contents.
import { computed } from "vue";

const props = defineProps({
  // The committed `services` v1 panel payload (or the unavailable form).
  services: { type: Object, required: true },
});

// Integer copper, thousands-separated for display only (no float money).
function formatCopper(value) {
  return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// The registry-owned unavailable form (available: false) carries only the
// reason — no rows, no default wallet value.
const unavailable = computed(() => props.services?.available === false);
const inventory = computed(() => (unavailable.value ? null : (props.services?.inventory ?? null)));

// Equipped rows only: the full bag is deferred (design D2 + roadmap §7).
const rows = computed(() => {
  const inv = inventory.value;
  const list = inv && Array.isArray(inv.rows) ? inv.rows : [];
  return list.filter((row) => row.equipped === true);
});

// The wallet renders only when the inventory section carries a wallet
// value; the unavailable form has no inventory section, so no fabricated 0.
const wallet = computed(() => {
  const w = inventory.value?.wallet;
  return typeof w === "number" ? Math.max(0, w) : null;
});
</script>

<template>
  <aside class="inventory-panel" data-testid="inventory-panel">
    <h3 class="inventory-panel__title" data-testid="inventory-panel__title">裝備</h3>

    <p
      v-if="unavailable"
      class="inventory-panel__unavailable"
      data-testid="inventory-panel__unavailable"
      :data-reason-code="services.reason?.code"
    >
      {{ services.reason?.message }}
    </p>

    <p v-else-if="inventory === null" class="inventory-panel__absent" data-testid="inventory-panel__absent">
      尚未有裝備物品
    </p>

    <div
      v-for="row in rows"
      :key="row.item_key"
      class="inventory-panel__row"
      :data-testid="`inventory-panel__row--${row.item_key}`"
    >
      <span class="inventory-panel__name" :data-testid="`inventory-panel__row-name--${row.item_key}`">{{ row.display_name }}</span>
      <span class="inventory-panel__equipped">裝備中</span>
      <span class="inventory-panel__held" :data-testid="`inventory-panel__row-held--${row.item_key}`">{{ row.held }}</span>
    </div>

    <div v-if="wallet !== null" class="inventory-panel__wallet-line">
      <span class="inventory-panel__wallet-label">錢包</span>
      <span class="inventory-panel__wallet" data-testid="inventory-panel__wallet">{{ formatCopper(wallet) }} 銅</span>
    </div>
  </aside>
</template>

<style scoped>
.inventory-panel {
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

.inventory-panel__title {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: 1em;
}

.inventory-panel__unavailable {
  margin: 0;
  padding: var(--sp-1) var(--sp-2);
  color: var(--paper-500);
  font-size: 0.85em;
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}

.inventory-panel__absent {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.85em;
}

.inventory-panel__row {
  display: grid;
  grid-template-columns: minmax(6em, auto) auto auto;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-1) 0;
  border-bottom: 1px solid var(--ink-700);
  font-size: 0.9em;
}

.inventory-panel__name {
  color: var(--paper-50);
}

.inventory-panel__equipped {
  color: var(--ok);
  font-size: 0.85em;
}

.inventory-panel__held {
  color: var(--paper-500);
  font-family: var(--f-mono);
  text-align: right;
}

.inventory-panel__wallet-label {
  color: var(--paper-300);
  font-size: 0.9em;
}

.inventory-panel__wallet {
  color: var(--gold-500);
  font-family: var(--f-mono);
  font-size: 0.9em;
}
</style>
