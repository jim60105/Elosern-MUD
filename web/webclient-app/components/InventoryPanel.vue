<script setup>
// InventoryPanel (H4, webclient-hud-04-reference-drawers, tasks 6.1/6.2/6.5;
// relocate-inventory-drawer-essentials): the 背包 · 裝備 drawer body. H4
// removed the old `equipped === true` filter so the full
// `services.inventory.rows` bag is rendered (display_name, held, and an
// equipped marker on the equipped rows). The equipment doll and the single
// drawer-layer wallet moved here from the character-status drawer: the doll
// composes before the held rows, and the header wallet renders only when
// the committed `character` panel is available with a valid integer
// balance. When the listing holds the 32-row ceiling (SERVICES_MAX_INVENTORY_
// ROWS) a worded ceiling note renders; otherwise no total is presented.
// `pagination.inventory_total` is the shipped-row count and is never
// presented as untruncated holdings.
import { computed } from "vue";
import EquipmentDoll from "./EquipmentDoll.vue";

const props = defineProps({
  // The committed `services` v2 panel payload (or the unavailable form).
  services: { type: Object, required: true },
  // The committed `character` v4 panel payload (or the unavailable form). A
  // completely missing panel arrives as `null`; the doll mounts only when a
  // committed character panel exists (never fabricating empty slots for a
  // missing panel).
  character: { type: Object, required: false, default: null },
});

// The registry-owned unavailable form (available: false) carries only the
// reason — no rows, no default wallet value.
const unavailable = computed(() => props.services?.available === false);
const inventory = computed(() => (unavailable.value ? null : (props.services?.inventory ?? null)));

// The equipment doll renders only when the bag itself is available (the
// services panel is not in its unavailable form) AND the inventory section
// is present AND a committed character panel exists. A missing character
// panel (`null`) or an absent inventory section must not fabricate an
// equipment state (no empty-slot boxes, no rows, no count).
const dollVisible = computed(
  () => !unavailable.value && inventory.value !== null && props.character !== null,
);

// The full bag: every committed row, equipped marker only on equipped rows.
const rows = computed(() => {
  const inv = inventory.value;
  return inv && Array.isArray(inv.rows) ? inv.rows : [];
});

// The 32-row ceiling note (task 6.2): only when the listing is at the
// bound, state the ceiling in words.
const INVENTORY_ROW_CEILING = 32;
const atCeiling = computed(() => rows.value.length === INVENTORY_ROW_CEILING);
</script>

<template>
  <aside class="inventory-panel" data-testid="inventory-panel">
    <p
      v-if="unavailable"
      class="inventory-panel__unavailable"
      data-testid="inventory-panel__unavailable"
      :data-reason-code="services.reason?.code"
    >
      {{ services.reason?.message }}
    </p>

    <p v-else-if="inventory === null" class="inventory-panel__absent" data-testid="inventory-panel__absent">
      背包目前是空的。
    </p>

    <!-- The equipment doll (moved here from the character-status drawer):
         it reads the committed `character` panel's equipment rows itself and
         renders its registered unavailable message when that panel is in its
         unavailable form. It mounts before the held-item listing and only
         when the bag is available, the inventory section is present, and a
         committed character panel exists. -->
    <EquipmentDoll v-if="dollVisible" :character="character" />

    <div
      v-for="row in rows"
      :key="row.item_key"
      class="inventory-panel__row"
      :data-testid="`inventory-panel__row--${row.item_key}`"
    >
      <span class="inventory-panel__name" :data-testid="`inventory-panel__row-name--${row.item_key}`">{{ row.display_name }}</span>
      <span v-if="row.equipped" class="inventory-panel__equipped">裝備中</span>
      <span class="inventory-panel__held" :data-testid="`inventory-panel__row-held--${row.item_key}`">{{ row.held }}</span>
    </div>

    <p v-if="atCeiling" class="inventory-panel__ceiling" data-testid="inventory-panel__ceiling">
      背包清單以上限 32 項為限，僅顯示已載入的項目。
    </p>
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

.inventory-panel__ceiling {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.8em;
}
</style>
