<script setup>
// DockVerbPopover (AVG stage design §7; OpenSpec change
// webclient-scene-overview-component, design D5): a person chip's verb
// menu inside the command panel. A transparent layer fills its positioned
// host; the card is anchored to the host's bottom edge (a bottom sheet, so
// it never needs the chip's geometry and is always fully visible) and holds
// a head naming the target and one listbox of `DockMenuItem` rows in the
// order of `ExplorationMenu.verbMenuFor` — the target's affordances, 查看,
// and the back row last.
//
// A pointer press on the layer outside the card emits `back` (the parent
// frame); presses on the card never reach the layer. The rows emit
// `focus-change` on every click and `activate` for enabled rows only.
import { computed } from "vue";
import DockMenuItem from "./DockMenuItem.vue";
import { disabledReasonText, dockItemKeys } from "./dock-items.js";

const props = defineProps({
  // The resolved verb menu: `{items, target, title}`.
  menu: { type: Object, required: true },
  focusedKey: { type: String, default: null },
  idPrefix: { type: String, default: "exploration-row" },
});

const emit = defineEmits(["focus-change", "activate", "back"]);

const targetName = computed(
  () => props.menu?.target?.display_name || props.menu?.title || "",
);

function reasonFor(item) {
  if (!item || item.enabled !== false) {
    return null;
  }
  return (
    disabledReasonText(item) ||
    (item.disabledReason && item.disabledReason.message) ||
    item.description ||
    null
  );
}

const rows = computed(() => {
  const items = Array.isArray(props.menu?.items) ? props.menu.items : [];
  const keys = dockItemKeys(items);
  return items.map((item, index) => ({
    key: keys[index],
    item,
    rowId: `${props.idPrefix}-${index}`,
    enabled: item.enabled !== false,
    reason: reasonFor(item),
  }));
});

const focusedRowId = computed(
  () => rows.value.find((row) => row.key === props.focusedKey)?.rowId ?? null,
);

function onFocus(key) {
  emit("focus-change", key);
}

function onActivate(key) {
  const row = rows.value.find((entry) => entry.key === key);
  if (row && row.enabled) {
    emit("activate", { key: row.key, item: row.item });
  }
}

function onLayerPress(event) {
  if (event.target === event.currentTarget) {
    emit("back");
  }
}
</script>

<template>
  <div class="verb-popover-layer" data-testid="verb-popover-layer" @pointerdown="onLayerPress">
    <section
      class="verb-popover"
      data-testid="verb-popover"
      role="dialog"
      :aria-label="`${targetName} 的行動`"
      @pointerdown.stop
    >
      <h3 class="verb-popover__head">{{ targetName }}</h3>
      <div
        class="verb-popover__list"
        role="listbox"
        :aria-label="`${targetName} 的行動`"
        :aria-activedescendant="focusedRowId"
        tabindex="0"
        data-testid="dock-menu"
      >
        <DockMenuItem
          v-for="row in rows"
          :key="row.key"
          class="verb-popover__row"
          :item-key="row.key"
          :label="row.item.label"
          :enabled="row.enabled"
          :reason="row.reason"
          :focused="row.key === focusedKey"
          :row-id="row.rowId"
          @focus="onFocus"
          @activate="onActivate"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.verb-popover-layer {
  position: absolute;
  inset: 0;
  z-index: 2;
}

.verb-popover {
  position: absolute;
  left: 8px;
  right: 8px;
  bottom: 8px;
  max-height: calc(100% - 16px);
  box-sizing: border-box;
  overflow-y: auto;
  padding: 10px 12px 12px;
  background: linear-gradient(180deg, var(--panel-hi), var(--panel));
  border: 1px solid var(--gold-500);
  border-radius: var(--radius);
  box-shadow: 0 -10px 28px -12px #000;
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
}

.verb-popover__head {
  margin: 0 0 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--ink-700);
  color: var(--gold-400);
  font: 15px/1.4 var(--f-serif);
  letter-spacing: 0.06em;
  overflow-wrap: anywhere;
}

.verb-popover__list {
  display: grid;
  gap: 6px;
  outline: none;
}

.verb-popover .verb-popover__row {
  justify-content: flex-start;
  width: 100%;
  min-height: 34px;
  text-align: left;
}
</style>
