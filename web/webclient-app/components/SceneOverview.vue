<script setup>
// SceneOverview (AVG stage design §7; OpenSpec change
// webclient-scene-overview-component, design D4): the exploration root of
// the command panel. It renders the one overview menu of
// `ExplorationMenu.overviewMenu` as labelled chip rows — 出口, 人物, 物件 —
// and a label-less footer (查看房間 · 等待／休息 · 建議), in the menu's
// reading order. Chips wrap inside the panel; an absent section renders no
// row and no label.
//
// Every chip is a `DockMenuItem`, the dock's one shared row renderer, so the
// `data-item-key` identity, the `<idPrefix>-<i>` row id, the focused fill,
// and the focusable disabled state (its `（無法使用）` marker and its
// `aria-describedby` reason) come from one definition. Exit chips carry the
// direction glyph and, while enabled with a canonical direction and a known
// destination, the destination's name (the exit outlet's headline rule).
// The reason strip (`exploration-detail`) shows the focused chip's
// server-authored reason while that chip is disabled.
//
// The listbox is the surface's single tab stop while `active` (it carries
// `data-testid="dock-menu"`); while inactive (a verb popover is open over it)
// the overview is `inert` and hidden from assistive technology. The focused
// chip is scrolled into view with `block: "nearest"`; the component never
// scrolls itself — the dock pane is the single scrolling region.
import { computed, nextTick, ref, watch } from "vue";
import DockMenuItem from "./DockMenuItem.vue";
import { destinationLabel, directionGlyph } from "./dock-exits.js";
import { disabledReasonText, dockItemKeys } from "./dock-items.js";

const props = defineProps({
  // The resolved overview menu: `{items, sections, geometry, title}`.
  menu: { type: Object, required: true },
  focusedKey: { type: String, default: null },
  // The committed `localMapModel`, for exit destination names.
  localMap: { type: Object, default: null },
  idPrefix: { type: String, default: "exploration-row" },
  active: { type: Boolean, default: true },
});

const emit = defineEmits(["focus-change", "activate"]);

const listEl = ref(null);

// The server-authored reason of a disabled exploration row: the dock's
// shared reader first, then the exploration menu's own fields.
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

function chipLabel(item, isExit) {
  if (isExit && item.enabled !== false && directionGlyph(item.direction)) {
    return destinationLabel(item, props.localMap) || item.label;
  }
  return item.label;
}

const chips = computed(() => {
  const items = Array.isArray(props.menu?.items) ? props.menu.items : [];
  const keys = dockItemKeys(items);
  return items.map((item, index) => ({
    key: keys[index],
    item,
    rowId: `${props.idPrefix}-${index}`,
  }));
});

const rows = computed(() => {
  const sections = Array.isArray(props.menu?.sections) ? props.menu.sections : [];
  const out = [];
  let start = 0;
  for (const section of sections) {
    const count = Math.max(0, section.count || 0);
    const isExit = section.key === "exits";
    const slice = chips.value.slice(start, start + count).map((chip) => ({
      ...chip,
      label: chipLabel(chip.item, isExit),
      glyph: isExit ? directionGlyph(chip.item.direction) : null,
      enabled: chip.item.enabled !== false,
      reason: reasonFor(chip.item),
    }));
    start += count;
    if (slice.length > 0) {
      out.push({ key: section.key, label: section.label || null, chips: slice });
    }
  }
  return out;
});

const focusedChip = computed(
  () => chips.value.find((chip) => chip.key === props.focusedKey) ?? null,
);

const reasonText = computed(() => {
  const chip = focusedChip.value;
  return chip ? reasonFor(chip.item) : null;
});

function onFocus(key) {
  emit("focus-change", key);
}

function onActivate(key) {
  const chip = chips.value.find((entry) => entry.key === key);
  if (chip && chip.item.enabled !== false) {
    emit("activate", { key: chip.key, item: chip.item });
  }
}

watch(
  () => props.focusedKey,
  async () => {
    await nextTick();
    const chip = focusedChip.value;
    const el = chip && listEl.value ? listEl.value.querySelector(`[id="${chip.rowId}"]`) : null;
    if (el && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ block: "nearest", inline: "nearest" });
    }
  },
  { flush: "post" },
);
</script>

<template>
  <div
    class="scene-overview"
    data-testid="scene-overview"
    :inert="!active || null"
    :aria-hidden="active ? null : 'true'"
  >
    <div
      ref="listEl"
      class="scene-overview__list"
      role="listbox"
      :aria-label="menu.title || '場景'"
      :aria-activedescendant="focusedChip ? focusedChip.rowId : null"
      :tabindex="active ? 0 : -1"
      v-bind="active ? { 'data-testid': 'dock-menu' } : {}"
    >
      <div
        v-for="row in rows"
        :key="row.key"
        class="scene-overview__row"
        :class="{ 'scene-overview__row--footer': row.key === 'footer' }"
        :data-section="row.key"
        :data-testid="`scene-overview-${row.key}`"
      >
        <span v-if="row.label" class="scene-overview__label">{{ row.label }}</span>
        <div class="scene-overview__chips">
          <span v-for="chip in row.chips" :key="chip.key" class="scene-overview__slot">
            <DockMenuItem
              class="scene-chip"
              :item-key="chip.key"
              :label="chip.label"
              :glyph="chip.glyph"
              :enabled="chip.enabled"
              :reason="chip.reason"
              :focused="chip.key === focusedKey"
              :row-id="chip.rowId"
              @focus="onFocus"
              @activate="onActivate"
            />
          </span>
        </div>
      </div>
    </div>
    <p
      v-if="reasonText"
      class="scene-overview__reason"
      data-testid="exploration-detail"
    >{{ reasonText }}</p>
  </div>
</template>

<style scoped>
.scene-overview {
  display: flex;
  flex-direction: column;
  /* The overview is the pane host's only child and fills its full width
     (webclient-desktop-shell: the scene overview is the direct-child rule's
     one exception for row regions). */
  flex: 1;
  gap: 8px;
  min-width: 0;
}

.scene-overview__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  outline: none;
}

.scene-overview__list:focus-visible {
  box-shadow: 0 0 0 1px var(--gold-500);
  border-radius: var(--radius-sm);
}

.scene-overview__row {
  display: grid;
  grid-template-columns: 3.2em minmax(0, 1fr);
  align-items: start;
  gap: 8px;
  min-width: 0;
}

.scene-overview__label {
  padding-top: 7px;
  color: var(--gold-400);
  font-family: var(--f-serif);
  font-size: 13px;
  letter-spacing: 0.12em;
  white-space: nowrap;
}

.scene-overview__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
}

.scene-overview__slot {
  display: inline-flex;
  align-items: center;
  min-width: 0;
  max-width: 100%;
}

/* The footer: no label, a top rule, and `·` separators between entries. */
.scene-overview__row--footer {
  grid-template-columns: minmax(0, 1fr);
  padding-top: 8px;
  border-top: 1px solid var(--ink-700);
}

.scene-overview__row--footer .scene-overview__slot + .scene-overview__slot::before {
  content: "·";
  margin: 0 4px 0 -2px;
  color: var(--paper-500);
}

/* Compact chips: the shared row renderer's look at chip density. */
.scene-overview .scene-chip {
  min-height: 32px;
  max-width: 100%;
  padding: 4px 10px;
  font-size: 13px;
  line-height: 1.35;
}

.scene-overview__row--footer .scene-chip {
  background: transparent;
  border-color: transparent;
  color: var(--paper-300);
}

.scene-overview__row--footer .scene-chip.dock-menu-item--focused {
  background: var(--gold-glow);
  border-color: var(--gold-500);
  color: var(--paper-50);
}

.scene-overview__reason {
  margin: 0;
  padding: 6px 10px;
  color: var(--paper-300);
  font-size: 12px;
  line-height: 1.5;
  border-left: 2px solid var(--seal-500);
  background: var(--ink-900);
}
</style>
