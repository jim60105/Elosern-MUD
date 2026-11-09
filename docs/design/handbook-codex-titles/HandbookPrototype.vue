<script setup>
// HandbookPrototype: the quest window renamed 手帳 with four first-level tabs
// (任務簿｜公會櫃檯｜圖鑑｜稱號). The book and counter bodies are the real
// QuestDrawer (its own head hidden here, since the prototype draws the shared
// head); the codex and titles bodies are the prototypes. In combat only the
// 圖鑑 and 稱號 tabs exist (D10). The 稱號 tab shows the full title at the
// head's trailing end. Reference only; see
// docs/superpowers/specs/2026-11-09-handbook-codex-titles-design.md.
import { computed, ref } from "vue";
import HudDrawer from "../../../web/webclient-app/components/HudDrawer.vue";
import IconTabs from "../../../web/webclient-app/components/IconTabs.vue";
import QuestDrawer from "../../../web/webclient-app/components/QuestDrawer.vue";
import { useQuestDrawerMemory } from "../../../web/webclient-app/components/quest-drawer-memory.js";
import { QUEST_LOG_PANEL_SAMPLE, SERVICES_PANEL_GUILD_BOARD_SAMPLE } from "../../../web/webclient-app/stories/fixtures.js";
import CodexTabProto from "./CodexTabProto.vue";
import TitlesTabProto from "./TitlesTabProto.vue";

const props = defineProps({
  tab: { type: String, default: "codex" },
  combat: { type: Boolean, default: false },
  codex: { type: Object, required: true },
  titles: { type: Object, required: true },
  codexCategory: { type: String, default: "monster" },
  codexEntry: { type: String, default: null },
  titlesRail: { type: String, default: "guild" },
  titlesSelection: { type: String, default: null },
  titlesConfirming: { type: Boolean, default: false },
  scope: { type: String, default: "proto" },
});

const tabs = computed(() => [
  ...(props.combat
    ? []
    : [
        { key: "book", label: "任務簿", glyph: "quest_book" },
        { key: "counter", label: "公會櫃檯", glyph: "guild_counter" },
      ]),
  { key: "codex", label: "圖鑑", glyph: "lore" },
  { key: "titles", label: "稱號", glyph: "codex" },
]);

const top = ref(props.combat && ["book", "counter"].includes(props.tab) ? "codex" : props.tab);

const memoryScope = `proto:${props.scope}`;
const memory = useQuestDrawerMemory(memoryScope);
function selectTop(key) {
  top.value = key;
  if (key === "book" || key === "counter") memory.top = key;
}
if (top.value === "book" || top.value === "counter") memory.top = top.value;

const titlesRef = ref(null);
const closeGuard = () => (top.value === "titles" && titlesRef.value ? titlesRef.value.guardClose() : true);

const lastIntent = ref(null);
function onIntent(intent) {
  lastIntent.value = `${intent.action_id} ${JSON.stringify(intent.payload)}`;
}
</script>

<template>
  <HudDrawer open title="手帳" icon="quests" drawer-key="quest" body-flush :close-guard="closeGuard">
    <section class="hb" :data-tab="top" aria-label="手帳">
      <div class="hb__head">
        <IconTabs
          class="hb__top-tabs"
          orientation="horizontal"
          aria-label="手帳分類"
          :tabs="tabs"
          :model-value="top"
          @update:model-value="selectTop"
        />
        <p v-if="lastIntent" class="hb__intent" role="status">送出 {{ lastIntent }}</p>
        <p v-if="top === 'titles'" class="hb__full-title">
          <span class="hb__full-title-kicker">全銜</span>
          <span class="hb__full-title-text">{{ titles.full_title || "（尚無全銜）" }}</span>
        </p>
      </div>

      <div class="hb__body">
        <QuestDrawer
          v-if="top === 'book' || top === 'counter'"
          :key="top"
          class="hb__quest"
          :quest-log="QUEST_LOG_PANEL_SAMPLE"
          :services="SERVICES_PANEL_GUILD_BOARD_SAMPLE"
          :memory-scope="memoryScope"
        />
        <CodexTabProto
          v-else-if="top === 'codex'"
          :codex="codex"
          :initial-category="codexCategory"
          :initial-entry="codexEntry"
        />
        <TitlesTabProto
          v-else
          ref="titlesRef"
          :codex="titles"
          :initial-rail="titlesRail"
          :initial-selection="titlesSelection"
          :initial-confirming="titlesConfirming"
          @intent="onIntent"
        />
      </div>
    </section>
  </HudDrawer>
</template>

<style scoped>
.hb {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
  color: var(--paper-200);
  font-family: var(--f-sans);
  background:
    radial-gradient(120% 80% at 70% 0%, rgba(185, 154, 96, 0.07), transparent 60%),
    linear-gradient(180deg, #16181dfa, #0e1014fa);
}

.hb__head {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: var(--sp-4);
  padding: var(--sp-1) var(--sp-5) 0;
  border-bottom: 1px solid rgba(185, 154, 96, 0.28);
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.25), transparent);
}

.hb__top-tabs {
  align-self: flex-end;
}

.hb__intent {
  margin: 0;
  padding: 2px var(--sp-3);
  color: var(--paper-400);
  font: var(--text-xs) var(--f-mono);
  border: 1px dashed var(--ink-600);
  border-radius: var(--radius-sm);
}

.hb__full-title {
  display: flex;
  align-items: baseline;
  gap: var(--sp-3);
  min-width: 0;
  margin: 0 0 0 auto;
}

.hb__full-title-kicker {
  color: var(--paper-500);
  font: var(--text-xs) var(--f-display);
  letter-spacing: 0.24em;
}

.hb__full-title-text {
  overflow: hidden;
  color: var(--gold-300);
  font: var(--text-lg) var(--f-display);
  letter-spacing: 0.1em;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.hb__body {
  min-height: 0;
}

/* The real QuestDrawer draws its own first-level head; the prototype's shared
   head replaces it, so only its body shows. */
.hb__quest :deep(.quest-drawer__head) {
  display: none;
}

.hb__quest {
  height: 100%;
}
</style>
