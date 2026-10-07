<script setup>
// The runtime entity page shell (gm-portal-s3-runtime-state §6).
//
// One shell for every curated kind: a header with the display name and the
// verbatim identifiers, a 概要 tab rendering the curated sections, a 原始資料
// tab rendering the universal raw inventory, and — for an NPC — the 記憶 and
// 對話 tabs. Loading is manual: the header's 重新載入 button reloads the
// selected tab, and nothing here schedules a timer (unlike the overview
// dashboard's visibility-aware polling).
import { computed, ref, watch } from "vue";
import GmCallDrawer from "./GmCallDrawer.vue";
import GmConsoleDrawer from "./GmConsoleDrawer.vue";
import GmConsoleResult from "./GmConsoleResult.vue";
import GmRawEditor from "./GmRawEditor.vue";
import GmEntityLink from "./GmEntityLink.vue";
import GmError from "./GmError.vue";
import GmJsonTree from "./GmJsonTree.vue";
import GmNpcDialogueTab from "./GmNpcDialogueTab.vue";
import GmNpcMemoryTab from "./GmNpcMemoryTab.vue";
import GmSectionView from "./GmSectionView.vue";
import { formatClock } from "../lib/format.js";
import { detailPath, isDbrefKind, kindLabel, listHref, rawPath } from "../lib/runtime.js";

const props = defineProps({
  kind: { type: String, required: true },
  id: { type: String, required: true },
  // The owner identity a record-backed kind resolves its id under.
  owner: { type: String, default: "" },
  // A requested tab (the cross-link vocabulary points at a collection's tab).
  tab: { type: String, default: "" },
  api: { type: Object, required: true },
});

const detail = ref({ status: "idle", data: null, error: null, loadedAt: null });
const rawState = ref({ status: "idle", data: null, error: null });
const lastRawResult = ref(null);
const activeTab = ref("overview");
const selectedCall = ref(null);
const refreshing = ref(false);
const tabRefs = ref([]);
// The narrative tabs own their own collections and expose a reload, so the
// header's refresh reloads whatever tab is actually selected.
const memoryTab = ref(null);
const dialogueTab = ref(null);

const ownerFilters = computed(() => (props.owner ? { owner: props.owner } : {}));
const dbref = computed(() => detail.value.data?.dbref ?? null);
const tabs = computed(() => {
  // An uncurated object has no curated summary: raw inspection is its page.
  if (props.kind === "object") return [{ key: "raw", label: "原始資料" }];
  const base = [
    { key: "overview", label: "概要" },
    { key: "raw", label: "原始資料" },
  ];
  if (props.kind === "npcs") {
    base.push({ key: "memory", label: "記憶" }, { key: "dialogue", label: "對話" });
  }
  return base;
});
const listTarget = computed(() =>
  props.kind === "object"
    ? null
    : listHref(props.kind, props.kind === "quests" ? ownerFilters.value : {}),
);

async function loadDetail() {
  detail.value = { ...detail.value, status: "loading", error: null };
  try {
    const data = await props.api.get(detailPath(props.kind, props.id, ownerFilters.value));
    detail.value = { status: "ready", data, error: null, loadedAt: Date.now() / 1000 };
  } catch (error) {
    detail.value = { status: "error", data: null, error, loadedAt: null };
  }
}

async function loadRaw() {
  rawState.value = { status: "loading", data: null, error: null };
  try {
    const identity = dbref.value ?? (props.kind === "object" ? props.id : null);
    const payload = isDbrefKind(props.kind) && identity !== null
      ? await props.api.get(rawPath(identity))
      : { raw: detail.value.data?.raw ?? {}, id: props.id, kind: props.kind, label: detail.value.data?.label ?? "" };
    rawState.value = { status: "ready", data: payload, error: null };
    if (props.kind === "object") {
      detail.value = {
        status: "ready",
        data: {
          id: String(payload.id ?? identity),
          kind: "object",
          label: payload.raw?.key ?? payload.label ?? "",
          dbref: payload.raw?.dbref ?? payload.dbref ?? null,
          typeclass: payload.typeclass ?? payload.raw?.typeclass ?? "",
          sections: [],
        },
        error: null,
        loadedAt: Date.now() / 1000,
      };
    } else if (detail.value.status === "ready") {
      // A raw inventory read is a read of this entity: the stamp is current.
      detail.value = { ...detail.value, loadedAt: Date.now() / 1000 };
    }
  } catch (error) {
    rawState.value = { status: "error", data: null, error };
  }
}

async function refresh() {
  refreshing.value = true;
  try {
    if (activeTab.value === "memory") {
      await memoryTab.value?.reload?.();
    } else if (activeTab.value === "dialogue") {
      await dialogueTab.value?.reload?.();
    } else if (activeTab.value === "raw" && isDbrefKind(props.kind)) {
      await loadRaw();
    } else if (activeTab.value === "raw") {
      // A record-backed raw tab reads its detail payload: refresh the detail
      // first so the raw view is not a reread of the previous response.
      await loadDetail();
      rawState.value = { status: "idle", data: null, error: null };
      await loadRaw();
    } else {
      await loadDetail();
    }
  } finally {
    refreshing.value = false;
  }
}

async function afterWrite() {
  // A raw mutation can change every curated section, while a domain mutation
  // can invalidate a previously opened raw tab. Never retain either cache.
  if (props.kind !== "object") await loadDetail();
  rawState.value = { status: "idle", data: null, error: null };
  if (activeTab.value === "raw") await loadRaw();
  if (activeTab.value === "memory") await memoryTab.value?.reload?.();
  if (activeTab.value === "dialogue") await dialogueTab.value?.reload?.();
}

function selectTab(key, focus = false) {
  activeTab.value = key;
  if (focus) {
    const index = tabs.value.findIndex((tab) => tab.key === key);
    tabRefs.value[index]?.focus();
  }
}

function onTabKeydown(event, key) {
  const index = tabs.value.findIndex((tab) => tab.key === key);
  const moves = {
    ArrowRight: index + 1,
    ArrowLeft: index - 1,
    Home: 0,
    End: tabs.value.length - 1,
  };
  if (!(event.key in moves)) return;
  event.preventDefault();
  const next = (moves[event.key] + tabs.value.length) % tabs.value.length;
  selectTab(tabs.value[next].key, true);
}

watch(
  () => [props.kind, props.id, props.owner, props.tab],
  () => {
    lastRawResult.value = null;
    rawState.value = { status: "idle", data: null, error: null };
    selectedCall.value = null;
    if (props.kind === "object") {
      activeTab.value = "raw";
      detail.value = { status: "idle", data: null, error: null, loadedAt: null };
      loadRaw();
    } else {
      activeTab.value = tabs.value.some((tab) => tab.key === props.tab) ? props.tab : "overview";
      loadDetail();
    }
  },
  { immediate: true },
);

watch(activeTab, (tab) => {
  if (tab === "raw" && rawState.value.status === "idle") loadRaw();
});

function onDrawerClose() {
  selectedCall.value = null;
}
</script>

<template>
  <div class="gm-entity">
    <nav class="gm-entity__crumbs" aria-label="位置">
      <a class="gm-entity__crumb" href="/gm/runtime">執行期狀態</a>
      <template v-if="listTarget">
        <span class="gm-entity__crumb-sep" aria-hidden="true">／</span>
        <a class="gm-entity__crumb" :href="listTarget">{{ kindLabel(kind) }}清單</a>
      </template>
    </nav>

    <header class="gm-entity__header">
      <GmConsoleDrawer :kind="kind" :target="`#${dbref ?? id}`" :api="api" @done="lastRawResult = null; afterWrite()" />
      <div class="gm-entity__identity">
        <p class="gm-entity__eyebrow">
          {{ kindLabel(kind) }}
          <span v-if="detail.data?.typeclass" class="gm-entity__typeclass gm-mono">{{ detail.data.typeclass }}</span>
        </p>
        <h2 class="gm-entity__label">{{ detail.data?.label ?? id }}</h2>
        <dl class="gm-entity__ids">
          <div v-if="detail.data?.dbref !== null && detail.data?.dbref !== undefined">
            <dt>識別碼</dt>
            <dd class="gm-mono">#{{ detail.data.dbref }}</dd>
          </div>
          <div v-else>
            <dt>識別碼</dt>
            <dd class="gm-mono">{{ id }}</dd>
          </div>
          <div v-if="owner">
            <dt>擁有者</dt>
            <dd>
              <GmEntityLink :link="{ kind: 'characters', id: owner.replace(/^#/, ''), label: owner }" />
            </dd>
          </div>
        </dl>
      </div>
      <div class="gm-entity__actions">
        <span class="gm-entity__stamp">
          <template v-if="detail.loadedAt !== null">
            最後載入 <time class="gm-mono">{{ formatClock(detail.loadedAt) }}</time>
          </template>
          <template v-else>尚未載入</template>
        </span>
        <button
          type="button"
          class="ui-btn ui-btn--ghost ui-btn--sm"
          :aria-disabled="refreshing ? 'true' : null"
          @click="!refreshing && refresh()"
        >
          <span class="gm-entity__refresh" :class="{ 'is-spinning': refreshing }" aria-hidden="true">↻</span>
          重新載入
        </button>
      </div>
    </header>

    <div class="ui-tabs" role="tablist" aria-label="檢視分頁">
      <button
        v-for="(tab, index) in tabs"
        :id="`gm-entity-tab-${tab.key}`"
        :key="tab.key"
        :ref="(element) => (tabRefs[index] = element)"
        type="button"
        role="tab"
        class="ui-tabs__tab"
        :class="{ 'is-active': activeTab === tab.key }"
        :aria-selected="activeTab === tab.key ? 'true' : 'false'"
        :aria-controls="`gm-entity-panel-${tab.key}`"
        :tabindex="activeTab === tab.key ? 0 : -1"
        @click="selectTab(tab.key)"
        @keydown="onTabKeydown($event, tab.key)"
      >
        {{ tab.label }}
      </button>
    </div>

    <div
      v-if="activeTab === 'overview'"
      id="gm-entity-panel-overview"
      role="tabpanel"
      aria-labelledby="gm-entity-tab-overview"
      class="gm-entity__panel"
      tabindex="0"
    >
      <p v-if="detail.status === 'loading'" class="gm-entity__loading" aria-hidden="true">
        <span v-for="width in ['52%', '30%', '76%', '44%']" :key="width" class="gm-skeleton" :style="{ width }"></span>
      </p>
      <p v-if="detail.status === 'loading'" class="gm-visually-hidden" role="status">載入概要中…</p>
      <GmError
        v-else-if="detail.error"
        :title="detail.error.code === 'object_not_found' ? '找不到指定的物件' : '無法載入概要'"
        :message="detail.error.message"
        :code="detail.error.code"
      >
        <template #actions>
          <button type="button" class="ui-btn ui-btn--sm" @click="loadDetail">重試</button>
        </template>
      </GmError>
      <div v-else-if="detail.data" class="gm-entity__sections">
        <GmSectionView
          v-for="section in detail.data.sections"
          :key="section.key"
          :section="section"
          @open-call="selectedCall = $event"
        />
      </div>
    </div>

    <div
      v-else-if="activeTab === 'raw'"
      id="gm-entity-panel-raw"
      role="tabpanel"
      aria-labelledby="gm-entity-tab-raw"
      class="gm-entity__panel"
      tabindex="0"
    >
      <p v-if="rawState.status === 'loading'" class="gm-skeleton" style="width: 60%"></p>
      <GmError
        v-else-if="rawState.error"
        title="無法載入原始資料"
        :message="rawState.error.message"
        :code="rawState.error.code"
      >
        <template #actions>
          <button type="button" class="ui-btn ui-btn--sm" @click="loadRaw">重試</button>
        </template>
      </GmError>
      <GmRawEditor v-if="rawState.data && isDbrefKind(kind)" :target="`#${dbref ?? id}`" :raw="rawState.data.raw ?? rawState.data" :api="api" @done="lastRawResult = $event; afterWrite()" />
      <GmJsonTree
        v-if="rawState.data"
        :value="rawState.data.raw ?? rawState.data"
        @open-call="selectedCall = $event"
      />
    </div>

    <div
      v-else-if="activeTab === 'memory'"
      id="gm-entity-panel-memory"
      role="tabpanel"
      aria-labelledby="gm-entity-tab-memory"
      class="gm-entity__panel"
      tabindex="0"
    >
      <GmNpcMemoryTab
        ref="memoryTab"
        :npc-dbref="id"
        :api="api"
        @open-call="selectedCall = $event"
      />
    </div>

    <div
      v-else
      id="gm-entity-panel-dialogue"
      role="tabpanel"
      aria-labelledby="gm-entity-tab-dialogue"
      class="gm-entity__panel"
      tabindex="0"
    >
      <GmNpcDialogueTab
        ref="dialogueTab"
        :npc-dbref="id"
        :api="api"
        @open-call="selectedCall = $event"
      />
    </div>

    <GmCallDrawer :call-id="selectedCall" :api="api" @close="onDrawerClose" />
    <GmConsoleResult :result="lastRawResult" />
  </div>
</template>

<style scoped>
.gm-entity {
  display: grid;
  gap: var(--sp-4);
  min-width: 0;
}

.gm-entity__crumbs {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
  font-size: var(--text-xs);
}

.gm-entity__crumb {
  color: var(--paper-500);
  text-decoration: none;
}

.gm-entity__crumb:hover {
  color: var(--gold-300);
  text-decoration: underline;
}

.gm-entity__crumb-sep {
  color: var(--paper-700);
}

.gm-entity__header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-4);
  padding: var(--sp-4) var(--sp-5);
  background:
    linear-gradient(180deg, var(--gold-glow), transparent 70%) no-repeat,
    var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: inset 0 1px 0 color-mix(in srgb, var(--gold-500) 26%, transparent);
}

.gm-entity__identity {
  min-width: 0;
}

.gm-entity__eyebrow {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-3);
  font-size: var(--text-xs);
  letter-spacing: 0.14em;
  color: var(--gold-400);
}

.gm-entity__typeclass {
  letter-spacing: 0;
  font-size: var(--text-xs);
  color: var(--paper-500);
  overflow-wrap: anywhere;
}

.gm-entity__label {
  margin-top: var(--sp-1);
  font-family: var(--f-serif);
  font-size: var(--text-2xl);
  font-weight: 600;
  line-height: 1.2;
  color: var(--paper-50);
  overflow-wrap: anywhere;
}

.gm-entity__ids {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2) var(--sp-5);
  margin-top: var(--sp-2);
}

.gm-entity__ids dt {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-entity__ids dd {
  color: var(--paper-100);
}

.gm-entity__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2) var(--sp-3);
}

.gm-entity__stamp {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-entity__refresh {
  display: inline-block;
  margin-right: var(--sp-1);
}

.gm-entity__refresh.is-spinning {
  animation: gm-entity-spin var(--motion-spin) linear infinite;
}

@keyframes gm-entity-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .gm-entity__refresh.is-spinning {
    animation: none;
  }
}

.gm-entity__panel {
  display: grid;
  gap: var(--sp-4);
  min-width: 0;
  outline: none;
}

.gm-entity__sections {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr));
  gap: var(--sp-4);
  align-items: start;
}

.gm-entity__loading {
  display: grid;
  gap: var(--sp-3);
}
</style>
