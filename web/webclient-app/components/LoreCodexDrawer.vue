<script setup>
// LoreCodexDrawer (webclient-lore-codex-drawer): the world-codex drawer
// body. It renders ONLY the committed `lore_codex` panel (the host-free
// read model from webclient-lore-codex-panel): a category strip with one
// zero-count-honest control per shipped category plus an aggregate control,
// the selected category's entry list, and the selected entry's card. All
// navigation is client-local state — selecting a category or an entry
// dispatches no action and triggers no fetch, because the panel already
// carries every discovered entry and its rendered card. The drawer
// discloses no more than the panel ships: no registry total, no
// denominator, no percentage, no locked/hidden placeholder. The codex is
// opened from the command line's utility strip (not from the quest drawer).
import { computed, ref } from "vue";

const props = defineProps({
  // The committed `lore_codex` panel payload. Null (never committed) renders
  // the honest-absence paragraph; the unavailable form renders the
  // registry-owned reason and no codex content.
  codex: { type: Object, default: null },
  // Showcase/mount convenience: the category selected on first render
  // ("all" is the aggregate control).
  initialCategory: { type: String, default: "all" },
  // Showcase/mount convenience: the entry (composite `category:key`)
  // selected on first render.
  initialEntryKey: { type: String, default: null },
});

// The registry-owned unavailable form carries only `reason` — no codex
// content is fabricated beside it.
const unavailable = computed(() => props.codex?.available === false);

// Missing panel (null): the drawer body renders an honest absence line
// (the quest-board__absent precedent) — never an invented reason.
const absent = computed(() => !props.codex);

const categories = computed(() =>
  unavailable.value || absent.value ? [] : (props.codex?.categories ?? []),
);

// An empty codex is available with every category shipped empty; the
// aggregate count is the panel's own discovered_total.
const discoveredTotal = computed(() => props.codex?.discovered_total ?? 0);
const isEmpty = computed(
  () => !unavailable.value && !absent.value && discoveredTotal.value === 0,
);

// Selected category ("all" = the aggregate control) and selected entry
// (the composite `category:key` — entry keys are unique per category, so
// the composite is unique across the aggregate view). Both are pure local
// state; nothing here dispatches or fetches.
const selectedCategory = ref(
  props.initialCategory === "all" ||
    categories.value.some((c) => c.key === props.initialCategory)
    ? props.initialCategory
    : "all",
);
const selectedEntryKey = ref(props.initialEntryKey);

function onSelectCategory(key) {
  selectedCategory.value = key;
  selectedEntryKey.value = null;
}

function onSelectEntry(compositeKey) {
  selectedEntryKey.value = compositeKey;
}

// The visible entries: the selected category's own entries, or the
// aggregate's flattened discovered entries — each tagged with its category
// so the aggregate view can label provenance. Order is the panel's order
// (categories in mapping order, entries in panel order), never re-sorted.
const visibleEntries = computed(() => {
  const rows = [];
  for (const category of categories.value) {
    if (selectedCategory.value !== "all" && category.key !== selectedCategory.value) {
      continue;
    }
    for (const entry of category.entries ?? []) {
      rows.push({
        categoryKey: category.key,
        categoryLabel: category.label,
        key: entry.key,
        title: entry.title,
        card: entry.card,
        compositeKey: `${category.key}:${entry.key}`,
      });
    }
  }
  return rows;
});

const selectedEntry = computed(
  () => visibleEntries.value.find((row) => row.compositeKey === selectedEntryKey.value) ?? null,
);
</script>

<template>
  <aside class="lore-codex-drawer" data-testid="lore-codex-drawer">
    <p
      v-if="unavailable"
      class="lore-codex-drawer__unavailable"
      data-testid="lore-codex-drawer__unavailable"
      :data-reason-code="codex.reason?.code"
    >
      {{ codex.reason?.message }}
    </p>

    <p v-else-if="absent" class="lore-codex-drawer__absent" data-testid="lore-codex-drawer__absent">
      尚無圖鑑資料
    </p>

    <template v-else>
      <!-- The dr-lore draft's head: the body-level heading under the drawer
           chrome's own 世界圖鑑 title. -->
      <div class="lore-codex-drawer__head" data-testid="lore-codex-drawer__head">
        <h3 class="lore-codex-drawer__title" data-testid="lore-codex-drawer__title">圖鑑</h3>
        <span class="lore-codex-drawer__sub" data-testid="lore-codex-drawer__sub">僅已發現 · 8 類</span>
      </div>

      <!-- Category strip: the aggregate control plus one honest control per
           shipped category — label and discovered count only. -->
      <div class="lore-codex-drawer__strip" role="group" aria-label="圖鑑分類" data-testid="lore-codex-drawer__strip">
        <button
          type="button"
          class="lore-codex-drawer__pill"
          :class="{ on: selectedCategory === 'all' }"
          :aria-pressed="String(selectedCategory === 'all')"
          data-testid="lore-codex-drawer__aggregate"
          @click="onSelectCategory('all')"
        >
          全部 <span class="lore-codex-drawer__pill-count">{{ discoveredTotal }}</span>
        </button>
        <button
          v-for="category in categories"
          :key="category.key"
          type="button"
          class="lore-codex-drawer__pill"
          :class="{ on: selectedCategory === category.key }"
          :aria-pressed="String(selectedCategory === category.key)"
          :data-testid="`lore-codex-drawer__category--${category.key}`"
          @click="onSelectCategory(category.key)"
        >
          {{ category.label }} <span class="lore-codex-drawer__pill-count">{{ category.count }}</span>
        </button>
      </div>

      <p
        v-if="isEmpty"
        class="lore-codex-drawer__empty"
        data-testid="lore-codex-drawer__empty"
      >
        尚未發現任何條目
      </p>

      <!-- Entry list for the selected category (the aggregate lists every
           discovered entry across categories). No rows are fabricated. -->
      <div v-else class="lore-codex-drawer__entries" data-testid="lore-codex-drawer__entries">
        <button
          v-for="row in visibleEntries"
          :key="row.compositeKey"
          type="button"
          class="lore-codex-drawer__entry"
          :class="{ on: selectedEntryKey === row.compositeKey }"
          :data-testid="`lore-codex-drawer__entry--${row.categoryKey}-${row.key}`"
          @click="onSelectEntry(row.compositeKey)"
        >
          <span class="lore-codex-drawer__entry-title">{{ row.title }}</span>
          <span class="lore-codex-drawer__entry-category">{{ row.categoryLabel }}</span>
        </button>
      </div>

      <!-- The selected entry's card: exactly the panel's card fields, in the
           panel's order, unmodified. -->
      <dl v-if="selectedEntry" class="lore-codex-drawer__card" data-testid="lore-codex-drawer__card">
        <dt class="lore-codex-drawer__card-title" data-testid="lore-codex-drawer__card-title">
          {{ selectedEntry.title }}
        </dt>
        <div
          v-for="(field, index) in selectedEntry.card"
          :key="index"
          class="lore-codex-drawer__card-field"
          :data-field="field.name"
        >
          <dt class="lore-codex-drawer__card-field-name">{{ field.name }}</dt>
          <dd class="lore-codex-drawer__card-field-value">{{ field.value }}</dd>
        </div>
      </dl>

      <p class="lore-codex-drawer__note" data-testid="lore-codex-drawer__note">
        尚未發現的條目不列出、不洩露存在性。
      </p>
    </template>
  </aside>
</template>

<style scoped>
.lore-codex-drawer {
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

.lore-codex-drawer__head {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
}

.lore-codex-drawer__title {
  margin: 0;
  font-family: var(--f-display);
  font-size: 1.05em;
  letter-spacing: 0.08em;
  color: var(--paper-100);
}

.lore-codex-drawer__sub {
  font-size: 0.78em;
  color: var(--paper-500);
}

.lore-codex-drawer__strip {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-1);
}

.lore-codex-drawer__pill {
  padding: 3px var(--sp-2);
  color: var(--paper-500);
  background: none;
  border: var(--line);
  border-radius: 999px;
  font-size: 0.82em;
  cursor: pointer;
}

.lore-codex-drawer__pill.on {
  color: var(--paper-50);
  border-color: var(--paper-500);
}

.lore-codex-drawer__pill-count {
  color: var(--paper-300);
  font-family: var(--f-mono);
  font-size: 0.9em;
}

.lore-codex-drawer__entries {
  display: flex;
  flex-direction: column;
}

.lore-codex-drawer__entry {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--sp-2);
  padding: var(--sp-1) var(--sp-2);
  color: var(--paper-200);
  background: none;
  border: none;
  border-bottom: 1px solid var(--ink-800);
  font-size: 0.9em;
  text-align: left;
  cursor: pointer;
}

.lore-codex-drawer__entry.on {
  color: var(--paper-50);
  background: var(--ink-800);
}

.lore-codex-drawer__entry-title {
  color: inherit;
}

.lore-codex-drawer__entry-category {
  flex: none;
  color: var(--paper-500);
  font-size: 0.85em;
}

.lore-codex-drawer__card {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  border: var(--line);
  border-radius: var(--radius-sm);
  background: var(--ink-900);
}

.lore-codex-drawer__card-title {
  margin-bottom: var(--sp-1);
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: 0.95em;
  letter-spacing: 0.06em;
}

.lore-codex-drawer__card-field {
  display: flex;
  gap: var(--sp-2);
  font-size: 0.85em;
}

.lore-codex-drawer__card-field-name {
  flex: none;
  min-width: 4em;
  color: var(--paper-500);
}

.lore-codex-drawer__card-field-value {
  margin: 0;
  color: var(--paper-200);
  white-space: pre-line;
}

.lore-codex-drawer__empty,
.lore-codex-drawer__unavailable,
.lore-codex-drawer__absent {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.88em;
}

.lore-codex-drawer__note {
  margin: 0;
  color: var(--paper-700);
  font-size: 0.75em;
}
</style>
