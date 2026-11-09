<script setup>
// LoreCodexTab (handbook-codex-tab, design D4): the handbook's 圖鑑 tab over
// the committed `lore_codex` v2 panel, after the approved prototype
// (docs/design/handbook-codex-titles/CodexTabProto.vue). The rail lists the
// shipped categories with their discovered counts; the wall (CodexTileGrid)
// shows the selected category's groups of tiles; the detail is the shared
// CodexDetail with the entry's art, stage stamp, research track and locked
// fields, and no footer: the codex has no action, so the tab dispatches
// nothing.
//
// The rail category and the per-category selection live in the quest
// drawer's session memory (keys only): a remembered key that is gone falls
// back — to the first category with a discovery, and to the category's first
// entry, else the empty detail — without being overwritten.
import { computed, nextTick, ref, useId, watch } from "vue";
import EmptyState from "../EmptyState.vue";
import IconTabs from "../IconTabs.vue";
import CodexDetail from "./CodexDetail.vue";
import CodexEmblem from "./CodexEmblem.vue";
import CodexTileGrid from "./CodexTileGrid.vue";
import {
  MONSTER_CATEGORY,
  codexDetail,
  codexGroups,
  codexRail,
  defaultCodexCategory,
  firstEntryKey,
  loreCodexStatus,
} from "./lore-codex-model.js";
import { useQuestDrawerMemory } from "../quest-drawer-memory.js";

const props = defineProps({
  // The committed `lore_codex` v2 panel (null before the first commit).
  codex: { type: Object, default: null },
  // `<generation>|<epoch>`: the quest drawer's session memory scope.
  memoryScope: { type: String, default: "" },
  combat: { type: Boolean, default: false },
});

const memory = useQuestDrawerMemory(props.memoryScope);
const uid = useId();
const wallId = `lore-codex-tab-${uid}-wall`;

const status = computed(() => loreCodexStatus(props.codex));

// ── Rail ──────────────────────────────────────────────────────────────
const railEntries = computed(() => codexRail(props.codex));
const category = computed(() => {
  const keys = railEntries.value.map((entry) => entry.key);
  return keys.includes(memory.codexCategory) ? memory.codexCategory : defaultCodexCategory(props.codex);
});
const railTabs = computed(() => railEntries.value.map((entry) => ({ ...entry, controls: wallId })));
const categoryRow = computed(() => props.codex?.categories?.find((row) => row.key === category.value) ?? null);

function selectCategory(key) {
  memory.codexCategory = key;
}

// ── Wall ──────────────────────────────────────────────────────────────
const groups = computed(() => codexGroups(props.codex, category.value));
const memoryKey = computed(() => `codex:${category.value}`);
const entryIds = computed(() =>
  groups.value.flatMap((group) => group.items).filter((item) => item.selectable).map((item) => item.id),
);

const selectedId = computed(() => {
  const remembered = memory.selectedByTab[memoryKey.value];
  return entryIds.value.includes(remembered) ? remembered : firstEntryKey(props.codex, category.value);
});

function selectEntry(id) {
  memory.selectedByTab = { ...memory.selectedByTab, [memoryKey.value]: id };
}

// ── Detail ────────────────────────────────────────────────────────────
const detail = computed(() =>
  selectedId.value ? codexDetail(props.codex, category.value, selectedId.value) : null,
);

// A commit can unmount the focused tile (an entry gone from the panel, or a
// category emptied). Focus then lands on <body>, outside the drawer; return it
// to the rail's selected category so the drawer keeps keyboard ownership
// (Escape still closes it). Only focus that was inside the tab before the
// update is rescued (design D5, kept inside the tab as TitleCodexTab does).
const root = ref(null);
const focusSource = () => [
  status.value,
  category.value,
  selectedId.value,
  groups.value.map((group) => group.items.map((item) => item.id).join(",")).join("|"),
];
let focusWasInside = false;
watch(focusSource, () => {
  focusWasInside = !!root.value?.contains(document.activeElement);
}, { flush: "pre" });
watch(
  focusSource,
  async () => {
    await nextTick();
    if (!focusWasInside) return;
    const active = document.activeElement;
    if (active && active !== document.body) return;
    root.value?.querySelector('[data-testid="handbook__codex-rail"] [role="tab"][tabindex="0"]')?.focus();
  },
  { flush: "post" },
);
</script>

<template>
  <div ref="root" class="lore-codex-tab" :class="`lore-codex-tab--${status}`" role="tabpanel" aria-label="圖鑑" data-testid="handbook__codex">
    <EmptyState
      v-if="status === 'absent'"
      class="lore-codex-tab__state"
      data-testid="handbook__codex-absent"
      glyph="lore"
      headline="圖鑑尚未載入"
    />
    <EmptyState
      v-else-if="status === 'unavailable'"
      class="lore-codex-tab__state"
      data-testid="handbook__codex-unavailable"
      glyph="lore"
      :headline="codex?.reason?.message ?? ''"
    />
    <template v-else>
      <IconTabs
        class="lore-codex-tab__rail"
        data-testid="handbook__codex-rail"
        orientation="vertical"
        aria-label="圖鑑分類"
        show-labels
        :tabs="railTabs"
        :model-value="category"
        @update:model-value="selectCategory"
      >
        <template #icon="{ tab }">
          <CodexEmblem :name="tab.key" />
        </template>
      </IconTabs>

      <CodexTileGrid
        :id="wallId"
        :groups="groups"
        :selected-id="selectedId"
        :category="category"
        :heading="categoryRow?.label ?? ''"
        :discovered="categoryRow?.discovered ?? 0"
        :total="categoryRow?.total ?? 0"
        :legend="category === MONSTER_CATEGORY"
        :panel="codex"
        @select="selectEntry"
      />

      <CodexDetail :detail="detail" :footer="null" :art-panel="codex">
        <template #empty>
          <EmptyState
            class="lore-codex-tab__empty"
            data-testid="handbook__codex-empty"
            glyph="lore"
            headline="尚無記錄"
            guidance="旅途中遭遇的事物會記錄於此"
          />
        </template>
      </CodexDetail>
    </template>
  </div>
</template>

<style scoped>
/* The grid of TitleCodexTab and the quest drawer's book body: rail, wall,
   detail. */
.lore-codex-tab {
  display: grid;
  grid-template-columns: var(--quest-drawer-rail-w, calc(68px * var(--ui-scale))) minmax(calc(360px * var(--ui-scale)), 0.82fr) minmax(0, 1.18fr);
  min-height: 0;
  height: 100%;
}

.lore-codex-tab--absent,
.lore-codex-tab--unavailable {
  grid-template-columns: 1fr;
  place-items: center;
  padding: var(--sp-8) var(--sp-5);
  box-sizing: border-box;
}

.lore-codex-tab__state,
.lore-codex-tab__empty {
  width: min(100%, calc(440px * var(--ui-scale)));
  box-sizing: border-box;
}

/* Eight labelled categories must fit the drawer body at the 1451x790
   reference viewport, so the rail's tabs are a little shorter than the
   default 58px, as on the titles rail. No overflow clip: the tooltips open
   over the wall. */
.lore-codex-tab__rail {
  --icon-tabs-tab-h: calc(52px * var(--ui-scale));
  position: relative;
  z-index: 1;
}
</style>
