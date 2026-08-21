<script setup>
// DockMenu (B2 action family): the framed grid of DockMenuItem cells — the
// `context_actions` v5 menu frame (a root menu or a sub-menu; a target
// selection frame renders through the same component). Passive: the frame
// renders the items plus the parent-owned `focusedKey` slice and emits the
// pointer user intents — `focus-change(key)` on every cell activation and
// `activate({ key, item, intent })` on an enabled cell (the exact OOB action
// intent for action entries, `null` for local navigation/target cells).
// Arrow/Enter/Escape navigation is the preserved KeyboardRouter's job at
// C2/C4; the listbox keeps the preserved single-tab-stop row model
// (`role="listbox"` + `aria-activedescendant`, one `tabindex="-1"` option
// per cell) so the bridge can keep the keyboard/pointer parity contract.
import { computed } from "vue";
import DockMenuItem from "./DockMenuItem.vue";
import { actionIntentForItem, disabledReasonText, dockItemKeys } from "./dock-items.js";

const props = defineProps({
  items: { type: Array, required: true },
  focusedKey: { type: String, default: null },
  idPrefix: { type: String, default: "dock-row" },
  gridCols: { type: Number, default: null },
});

const emit = defineEmits(["activate", "focus-change"]);

const rows = computed(() =>
  dockItemKeys(props.items).map((key, index) => ({
    key,
    item: props.items[index],
    rowId: `${props.idPrefix}-${index}`,
    intent: actionIntentForItem(props.items[index]),
    reason: disabledReasonText(props.items[index]),
  })),
);

const focusedRow = computed(
  () => rows.value.find((row) => row.key === props.focusedKey) ?? null,
);

const gridStyle = computed(() =>
  props.gridCols != null
    ? {
        display: "grid",
        gridTemplateColumns: `repeat(${props.gridCols}, 1fr)`,
      }
    : {},
);

function onCellFocus(key) {
  emit("focus-change", key);
}

function onCellActivate(key, row) {
  if (row.item.enabled !== false) {
    emit("activate", { key: row.key, item: row.item, intent: row.intent });
  }
}
</script>

<template>
  <div
    class="dock-menu"
    role="listbox"
    tabindex="0"
    :aria-activedescendant="focusedRow ? focusedRow.rowId : null"
    :style="gridStyle"
    data-testid="dock-menu"
  >
    <DockMenuItem
      v-for="row in rows"
      :key="row.key"
      :item-key="row.key"
      :label="row.item.label"
      :enabled="row.item.enabled !== false"
      :reason="row.reason"
      :focused="row.key === props.focusedKey"
      :row-id="row.rowId"
      @focus="onCellFocus"
      @activate="(key) => onCellActivate(key, row)"
    />
  </div>
</template>

<style scoped>
/* The framed grid: bounded, context-specific menus (no unbounded room
   enumeration) in an auto-fill geometry per the design draft. */
.dock-menu {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 7px;
}

.dock-menu:focus {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
}
</style>
