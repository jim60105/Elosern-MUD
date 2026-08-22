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
// `focus-change` fires on every pointer activation (pointer parity), so the
// parent may deduplicate an unchanged focused key.
import { computed } from "vue";
import DockMenuItem from "./DockMenuItem.vue";
import { actionIntentForItem, disabledReasonText, dockItemKeys } from "./dock-items.js";

const props = defineProps({
  items: { type: Array, required: true },
  focusedKey: { type: String, default: null },
  idPrefix: { type: String, default: "dock-row" },
  gridCols: { type: Number, default: null },
  // The detail pane's stable hook (Phase-0 audit §2.3 REMAP-TO-TESTID): the
  // pane testid is the legacy identifier string the managed-browser slices
  // retarget to (`combat-detail` in combat mode, `exploration-detail` in
  // exploration mode).
  detailTestId: { type: String, default: "dock-detail" },
  // An optional message (e.g. the rest form's validation error) that
  // overrides the pane's default focused-item content.
  detailMessage: { type: String, default: null },
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
  <div class="dock-menu-layout">
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
    <aside
      v-if="focusedRow || props.detailMessage"
      class="dock-detail"
      :class="{ 'exploration-detail': props.detailTestId === 'exploration-detail' }"
      :data-testid="props.detailTestId"
      tabindex="-1"
      aria-label="項目詳情"
    >
      <template v-if="props.detailMessage">
        <div class="dock-detail__disabled">{{ props.detailMessage }}</div>
      </template>
      <template v-else>
        <div class="dock-detail__label">{{ focusedRow.item.label }}</div>
        <div v-if="focusedRow.item.enabled !== false" class="dock-detail__action">
          Enter → 開啟
        </div>
        <div v-else class="dock-detail__disabled">
          {{ focusedRow.reason || "（無法使用）" }}
        </div>
      </template>
    </aside>
  </div>
</template>

<style scoped>
.dock-menu-layout {
  display: flex;
  gap: var(--sp-3);
  align-items: flex-start;
}

/* The framed grid: bounded, context-specific menus (no unbounded room
   enumeration) in an auto-fill geometry per the design draft. */
.dock-menu {
  flex: 1 1 auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 7px;
}

.dock-menu:focus {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
}

/* The detail pane names the focused item, its availability, and the next
   key action (the webclient-desktop-shell keyboard-routing contract). */
.dock-detail {
  flex: 0 0 220px;
  padding: var(--sp-2) var(--sp-3);
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--paper-100);
}

.dock-detail__label {
  font-weight: 600;
  margin-bottom: var(--sp-1);
}

.dock-detail__action {
  color: var(--paper-500);
}

.dock-detail__disabled {
  color: var(--seal-400);
}
</style>
