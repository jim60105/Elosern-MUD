<script setup>
// TitleCodexTab (handbook-titles-tab, design D7): the handbook's 稱號 tab over
// the committed `title_codex` v1 panel, after the approved prototype
// (docs/design/handbook-codex-titles/TitlesTabProto.vue). The rail lists the
// six fixed-title categories with their unlocked counts, a divider, 異名, and
// 提名 while a ballot is pending. Fixed titles are a medal wall
// (CodexMedalGrid); epithets and nominees are QuestList rows; the detail is
// the shared CodexDetail with its DetailFooter.
//
// The footer carries 裝備, the two-step 移除 (only where the server row says
// `can_remove`) and the ballot answers; every intent is emitted as one
// `action` with the exact `{action_id, payload}`. While removal is armed the
// host's close guard (`guardClose`) cancels it instead of closing. The rail
// and the per-rail selection live in the quest drawer's session memory (keys
// only): a remembered key that is gone falls back without being overwritten.
import { computed, nextTick, ref, useId, watch } from "vue";
import EmptyState from "../EmptyState.vue";
import IconTabs from "../IconTabs.vue";
import QuestList from "../QuestList.vue";
import CodexDetail from "./CodexDetail.vue";
import CodexEmblem from "./CodexEmblem.vue";
import CodexMedalGrid from "./CodexMedalGrid.vue";
import {
  TITLE_CATEGORIES,
  defaultTitleRail,
  defaultTitleSelection,
  medalItems,
  titleCodexStatus,
  titleDetail,
  titleFooter,
  titleIntent,
  titleListRows,
  titleRail,
  titleRailLabel,
} from "./title-codex-model.js";
import { useQuestDrawerMemory } from "../quest-drawer-memory.js";

const props = defineProps({
  // The committed `title_codex` v1 panel (null before the first commit).
  codex: { type: Object, default: null },
  // `<generation>|<epoch>`: the quest drawer's session memory scope.
  memoryScope: { type: String, default: "" },
  combat: { type: Boolean, default: false },
});

const emit = defineEmits(["action"]);

const memory = useQuestDrawerMemory(props.memoryScope);
const uid = useId();
const listId = `title-codex-tab-${uid}-list`;

const status = computed(() => titleCodexStatus(props.codex));

// ── Rail ──────────────────────────────────────────────────────────────
const railEntries = computed(() => titleRail(props.codex));
const rail = computed(() => {
  const keys = railEntries.value.map((entry) => entry.key);
  if (keys.includes(memory.titlesRail)) return memory.titlesRail;
  if (memory.titlesRail === "ballot") return "epithet";
  return defaultTitleRail(props.codex);
});
const railTabs = computed(() => railEntries.value.map((entry) => ({ ...entry, controls: listId })));
const railLabel = computed(() => titleRailLabel(rail.value));
const isFixed = computed(() => TITLE_CATEGORIES.some((category) => category.key === rail.value));

function selectRail(key) {
  memory.titlesRail = key;
}

// ── List ──────────────────────────────────────────────────────────────
const medals = computed(() => medalItems(props.codex, rail.value));
const unlockedCount = computed(() => medals.value.filter((item) => !item.locked).length);
const listRows = computed(() => titleListRows(props.codex, rail.value));
const memoryKey = computed(() => `titles:${rail.value}`);

const selectedId = computed(() => {
  const ids = isFixed.value ? medals.value.map((item) => item.id) : listRows.value.map((row) => row.id);
  const remembered = memory.selectedByTab[memoryKey.value];
  return ids.includes(remembered) ? remembered : defaultTitleSelection(props.codex, rail.value);
});

function selectEntry(id) {
  memory.selectedByTab = { ...memory.selectedByTab, [memoryKey.value]: id };
}

// ── Detail and footer ─────────────────────────────────────────────────
const detail = computed(() => titleDetail(props.codex, rail.value, selectedId.value));

// The display of the epithet whose removal is armed. The effective armed
// state is derived, so a stale value never blocks a close or shows the
// confirmation for another entry.
const armedId = ref(null);
const armed = computed(
  () => armedId.value !== null && detail.value?.kind === "epithet" && detail.value.removable && detail.value.id === armedId.value,
);
watch([rail, selectedId, () => detail.value?.id ?? null], () => {
  armedId.value = null;
});

const footer = computed(() => titleFooter(detail.value, { armed: armed.value }));
const detailRef = ref(null);

async function press(key) {
  const current = detail.value;
  if (!current) return;
  if (key === "remove") {
    if (!current.removable) return;
    armedId.value = current.id;
    await nextTick();
    detailRef.value?.focus("cancel");
    return;
  }
  if (key === "cancel") {
    armedId.value = null;
    await nextTick();
    detailRef.value?.focus("remove");
    return;
  }
  if (key === "confirm-remove" && !armed.value) return;
  const intent = titleIntent(current, key);
  if (key === "confirm-remove") armedId.value = null;
  if (intent) emit("action", intent);
}

// The host's close guard: an armed removal is cancelled instead of closing.
function guardClose() {
  if (armed.value) {
    armedId.value = null;
    return false;
  }
  return true;
}

defineExpose({ guardClose });
</script>

<template>
  <div class="title-codex-tab" :class="`title-codex-tab--${status}`" role="tabpanel" aria-label="稱號" data-testid="handbook__titles">
    <EmptyState
      v-if="status === 'absent'"
      class="title-codex-tab__state"
      data-testid="handbook__titles-absent"
      glyph="codex"
      headline="稱號冊尚未載入"
    />
    <EmptyState
      v-else-if="status === 'unavailable'"
      class="title-codex-tab__state"
      data-testid="handbook__titles-unavailable"
      glyph="codex"
      :headline="codex?.reason?.message ?? ''"
    />
    <template v-else>
      <IconTabs
        class="title-codex-tab__rail"
        data-testid="handbook__titles-rail"
        orientation="vertical"
        aria-label="稱號分類"
        show-labels
        :tabs="railTabs"
        :model-value="rail"
        @update:model-value="selectRail"
      >
        <template #icon="{ tab }">
          <CodexEmblem :name="tab.key" />
        </template>
      </IconTabs>

      <div
        v-if="isFixed"
        :id="listId"
        class="title-codex-tab__col"
        role="tabpanel"
        :aria-label="railLabel"
        data-testid="handbook__medals"
      >
        <header class="title-codex-tab__col-head">
          <span class="title-codex-tab__kicker">{{ railLabel }}</span>
          <span class="title-codex-tab__rule" aria-hidden="true"></span>
          <span class="title-codex-tab__n"><b>{{ unlockedCount }}</b> / {{ medals.length }}</span>
        </header>
        <CodexMedalGrid
          v-if="medals.length"
          :items="medals"
          :selected-id="selectedId"
          :aria-label="`${railLabel}稱號`"
          @select="selectEntry"
        />
        <p v-else class="title-codex-tab__note" data-testid="handbook__medals-empty">這個分類還沒有可收集的稱號。</p>
      </div>
      <QuestList
        v-else
        :id="listId"
        role="tabpanel"
        :aria-label="railLabel"
        :heading="railLabel"
        :rows="listRows"
        :selected-id="selectedId"
        empty-headline="尚未取得任何異名"
        empty-guidance="旅途中的事蹟被眾人傳頌時，會在這裡獲得提名。"
        empty-glyph="codex"
        @select="selectEntry"
      />

      <CodexDetail ref="detailRef" :detail="detail" :footer="footer" @press="press" />
    </template>
  </div>
</template>

<style scoped>
/* The grid of the quest drawer's `.quest-drawer__body--book`, and the
   prototype's `.hb-titles` rail divider and `.hb-col` list column. */
.title-codex-tab {
  display: grid;
  grid-template-columns: var(--quest-drawer-rail-w, calc(68px * var(--ui-scale))) minmax(calc(360px * var(--ui-scale)), 0.82fr) minmax(0, 1.18fr);
  min-height: 0;
  height: 100%;
}

.title-codex-tab--absent,
.title-codex-tab--unavailable {
  grid-template-columns: 1fr;
  place-items: center;
  padding: var(--sp-8) var(--sp-5);
  box-sizing: border-box;
}

.title-codex-tab__state {
  width: min(100%, calc(440px * var(--ui-scale)));
  box-sizing: border-box;
}

.title-codex-tab__rail {
  position: relative;
  z-index: 1;
}

/* The divider before 異名: a hairline above the seventh tab. */
.title-codex-tab__rail :deep([data-tab-key="epithet"]) {
  margin-top: var(--sp-3);
}

.title-codex-tab__rail :deep([data-tab-key="epithet"])::before {
  content: "";
  position: absolute;
  top: calc(-1 * var(--sp-2));
  left: 22%;
  right: 22%;
  height: 1px;
  background: rgba(185, 154, 96, 0.35);
}

.title-codex-tab__col {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding: var(--sp-4);
  background: #15171c;
  border-right: 1px solid rgba(185, 154, 96, 0.28);
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
}

.title-codex-tab__col-head {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.title-codex-tab__kicker {
  color: var(--gold-400);
  font: var(--text-md) var(--f-display);
  letter-spacing: 0.12em;
}

.title-codex-tab__rule {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.28), transparent);
}

.title-codex-tab__n {
  color: var(--paper-500);
  font: var(--text-xs) var(--f-num);
  font-variant-numeric: tabular-nums;
}

.title-codex-tab__n b {
  color: var(--gold-300);
  font-size: var(--text-md);
  font-weight: 500;
}

.title-codex-tab__note {
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-400);
  font-size: var(--text-md);
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}
</style>
