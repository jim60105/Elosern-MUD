<script setup>
// The NPC 記憶 tab (gm-portal-s3-runtime-state §5).
//
// Three read-only surfaces in one tab, all owner-scoped by the NPC's dbref:
// the filtered effective memory list with each record's complete revision
// history on demand, the newest ten context snapshots with their token
// accounting and S2 evidence links, and the recall preview, which posts a
// query — nothing else — to the authoritative ``fast_recall`` query under the
// NPC's own owner/requester identity.
import { computed, onMounted, reactive, ref } from "vue";
import GmEntityListTable from "./GmEntityListTable.vue";
import GmError from "./GmError.vue";
import GmFilterBar from "./GmFilterBar.vue";
import GmJsonTree from "./GmJsonTree.vue";
import GmPager from "./GmPager.vue";
import GmSectionView from "./GmSectionView.vue";
import { LIST_DEFAULT_LIMIT, RECALL_QUERY_LIMIT, listPath, ownerQuery, recallPath } from "../lib/runtime.js";

const props = defineProps({
  npcDbref: { type: String, required: true },
  api: { type: Object, required: true },
});

const emit = defineEmits(["open-call"]);

const MEMORY_FILTERS = [
  { key: "tier", label: "層級", type: "text", placeholder: "core / working", mono: true },
  { key: "scope", label: "知識範圍", type: "text", placeholder: "witnessed", mono: true },
  { key: "category", label: "類別", type: "text", placeholder: "category", mono: true },
  { key: "include_superseded", label: "包含已被取代", type: "checkbox" },
  { key: "include_inactive", label: "包含已停用", type: "checkbox" },
];

const RECALL_GROUPS = [
  { key: "core", label: "核心" },
  { key: "working", label: "工作" },
  { key: "recalled", label: "召回" },
];

const filters = ref({});
const memories = reactive({ status: "idle", items: [], nextCursor: null, page: 1, limit: LIST_DEFAULT_LIMIT, error: null });
const snapshots = reactive({ status: "idle", items: [], error: null });
const expanded = reactive({ memory: {}, snapshot: {} });
const recall = reactive({ status: "idle", result: null, error: null });
const form = reactive({ query: "", thread: "", include_superseded: false, include_inactive: false });

const owner = computed(() => ({ owner: `#${props.npcDbref}` }));
const refreshing = computed(() => memories.status === "loading" || snapshots.status === "loading");
const queryTooLong = computed(() => form.query.length > RECALL_QUERY_LIMIT);
const recallActive = computed(() => recall.status !== "idle");

function detailOf(id) {
  return (expanded.memory[id] ??= { status: "idle", data: null, error: null });
}

function snapshotOf(id) {
  return (expanded.snapshot[id] ??= { status: "idle", data: null, error: null });
}

async function loadMemories({ cursor = null, append = false } = {}) {
  memories.status = "loading";
  try {
    const data = await props.api.get(
      listPath("memories", { cursor, limit: memories.limit, filters: { ...owner.value, ...filters.value } }),
    );
    memories.items = append ? [...memories.items, ...data.items] : data.items;
    memories.nextCursor = data.next_cursor;
    memories.page = append ? memories.page + 1 : 1;
    memories.status = "ready";
    memories.error = null;
  } catch (error) {
    memories.status = "error";
    memories.error = error;
  }
}

async function loadSnapshots() {
  snapshots.status = "loading";
  try {
    const data = await props.api.get(
      listPath("snapshots", { limit: 10, filters: owner.value }),
    );
    snapshots.items = data.items;
    snapshots.status = "ready";
    snapshots.error = null;
  } catch (error) {
    snapshots.status = "error";
    snapshots.error = error;
  }
}

function onFilters(next) {
  filters.value = next;
  // Any filter change restarts pagination from the first page.
  loadMemories();
}

function onLimit(limit) {
  memories.limit = limit;
  loadMemories();
}

async function toggleMemory(row) {
  const state = detailOf(row.id);
  if (state.status === "ready" || state.status === "loading") {
    state.status = "idle";
    return;
  }
  state.status = "loading";
  try {
    state.data = await props.api.get(
      `/state/memories/${encodeURIComponent(row.id)}?${new URLSearchParams(owner.value)}`,
    );
    state.status = "ready";
    state.error = null;
  } catch (error) {
    state.status = "error";
    state.error = error;
  }
}

async function toggleSnapshot(row) {
  const state = snapshotOf(row.id);
  if (state.status === "ready" || state.status === "loading") {
    state.status = "idle";
    return;
  }
  state.status = "loading";
  try {
    state.data = await props.api.get(
      `/state/snapshots/${encodeURIComponent(row.id)}?${new URLSearchParams(owner.value)}`,
    );
    state.status = "ready";
    state.error = null;
  } catch (error) {
    state.status = "error";
    state.error = error;
  }
}

async function runRecall() {
  if (queryTooLong.value) return;
  recall.status = "loading";
  recall.error = null;
  try {
    recall.result = await props.api.post(recallPath(props.npcDbref), {
      query: form.query,
      thread: form.thread || null,
      include_superseded: form.include_superseded,
      include_inactive: form.include_inactive,
    });
    recall.status = "ready";
  } catch (error) {
    recall.status = "error";
    recall.error = error;
    recall.result = null;
  }
}

onMounted(() => {
  loadMemories();
  loadSnapshots();
});

async function refreshAll() {
  await Promise.all([loadMemories(), loadSnapshots()]);
}
</script>

<template>
  <div class="gm-memory">
    <section class="gm-memory__block" data-block="memories" aria-labelledby="gm-memory-list">
      <div class="gm-memory__head">
        <h3 id="gm-memory-list" class="gm-memory__title">記憶紀錄</h3>
        <button
          type="button"
          class="ui-btn ui-btn--ghost ui-btn--sm gm-memory__refresh"
          :aria-disabled="refreshing ? 'true' : null"
          @click="!refreshing && refreshAll()"
        >
          重新載入
        </button>
      </div>
      <GmFilterBar
        :fields="MEMORY_FILTERS"
        :model-value="filters"
        :busy="memories.status === 'loading'"
        caption="記憶篩選"
        @change="onFilters"
      />
      <p v-if="memories.status === 'loading' && memories.items.length === 0" class="gm-skeleton" style="width: 55%"></p>
      <GmError
        v-else-if="memories.error"
        compact
        live="off"
        title="無法載入記憶"
        :message="memories.error.message"
        :code="memories.error.code"
      />
      <template v-else>
        <GmEntityListTable
          :rows="memories.items"
          kind="memories"
          caption="記憶紀錄"
          extra-column="展開"
          empty-title="沒有符合條件的記憶"
          empty-message="換一組篩選條件，或確認此 NPC 是否已有記憶紀錄。"
          @open-call="emit('open-call', $event)"
        >
          <template #extra="{ row }">
            <button
              type="button"
              class="ui-btn ui-btn--ghost ui-btn--sm"
              :aria-expanded="detailOf(row.id).status !== 'idle' ? 'true' : 'false'"
              @click="toggleMemory(row)"
            >
              {{ detailOf(row.id).status === "idle" ? "展開修訂" : "收合" }}
            </button>
          </template>
        </GmEntityListTable>
        <div v-for="row in memories.items" :key="row.id">
          <template v-if="detailOf(row.id).status !== 'idle'">
            <p v-if="detailOf(row.id).status === 'loading'" class="gm-skeleton" style="width: 40%"></p>
            <GmError
              v-else-if="detailOf(row.id).error"
              compact
              live="off"
              title="無法載入記憶明細"
              :message="detailOf(row.id).error.message"
              :code="detailOf(row.id).error.code"
            />
            <div v-else class="gm-memory__sections">
              <GmSectionView
                v-for="section in detailOf(row.id).data.sections"
                :key="section.key"
                :section="section"
                @open-call="emit('open-call', $event)"
              />
            </div>
          </template>
        </div>
        <GmPager
          :next-cursor="memories.nextCursor"
          :limit="memories.limit"
          :shown="memories.items.length"
          :page="memories.page"
          :busy="memories.status === 'loading'"
          @more="loadMemories({ cursor: memories.nextCursor, append: true })"
          @limit="onLimit"
          @first="loadMemories()"
        />
      </template>
    </section>

    <section class="gm-memory__block" data-block="snapshots" aria-labelledby="gm-memory-snapshots">
      <h3 id="gm-memory-snapshots" class="gm-memory__title">
        情境快照
        <span class="gm-memory__hint">最新十筆</span>
      </h3>
      <GmError
        v-if="snapshots.error"
        compact
        live="off"
        title="無法載入情境快照"
        :message="snapshots.error.message"
        :code="snapshots.error.code"
      />
      <GmEntityListTable
        v-else
        :rows="snapshots.items"
        kind="snapshots"
        caption="情境快照"
        extra-column="展開"
        empty-title="沒有情境快照"
        empty-message="此 NPC 尚未保存任何情境快照。"
        @open-call="emit('open-call', $event)"
      >
        <template #extra="{ row }">
          <button
            type="button"
            class="ui-btn ui-btn--ghost ui-btn--sm"
            :aria-expanded="snapshotOf(row.id).status !== 'idle' ? 'true' : 'false'"
            @click="toggleSnapshot(row)"
          >
            {{ snapshotOf(row.id).status === "idle" ? "檢視" : "收合" }}
          </button>
        </template>
      </GmEntityListTable>
      <div v-for="row in snapshots.items" :key="row.id">
        <template v-if="snapshotOf(row.id).status !== 'idle'">
          <p v-if="snapshotOf(row.id).status === 'loading'" class="gm-skeleton" style="width: 40%"></p>
          <GmError
            v-else-if="snapshotOf(row.id).error"
            compact
            live="off"
            title="無法載入快照明細"
            :message="snapshotOf(row.id).error.message"
            :code="snapshotOf(row.id).error.code"
          />
          <div v-else class="gm-memory__sections">
            <GmSectionView
              v-for="section in snapshotOf(row.id).data.sections"
              :key="section.key"
              :section="section"
              @open-call="emit('open-call', $event)"
            />
          </div>
        </template>
      </div>
    </section>

    <section class="gm-memory__block" data-block="recall" aria-labelledby="gm-memory-recall">
      <h3 id="gm-memory-recall" class="gm-memory__title">
        召回預覽
        <span class="gm-memory__hint">以 NPC 自身為擁有者與請求者，等同正式召回查詢</span>
      </h3>
      <form class="gm-recall" @submit.prevent="runRecall">
        <label class="gm-recall__field">
          <span class="gm-recall__label">查詢文字（最多 {{ RECALL_QUERY_LIMIT }} 字元）</span>
          <textarea
            v-model="form.query"
            class="gm-recall__query"
            rows="3"
            :maxlength="RECALL_QUERY_LIMIT"
            placeholder="輸入要召回的線索"
          ></textarea>
          <span class="gm-recall__count" :class="{ 'is-over': queryTooLong }">
            {{ form.query.length }} / {{ RECALL_QUERY_LIMIT }}
          </span>
        </label>
        <div class="gm-recall__controls">
          <label class="gm-recall__field">
            <span class="gm-recall__label">故事線</span>
            <input v-model="form.thread" class="gm-recall__input gm-mono" type="text" placeholder="thread_id">
          </label>
          <label class="gm-recall__toggle">
            <input v-model="form.include_superseded" type="checkbox">
            <span>包含已被取代</span>
          </label>
          <label class="gm-recall__toggle">
            <input v-model="form.include_inactive" type="checkbox">
            <span>包含已停用</span>
          </label>
          <button
            type="submit"
            class="ui-btn ui-btn--primary ui-btn--sm gm-recall__submit"
            :aria-disabled="queryTooLong ? 'true' : null"
          >
            {{ recall.status === "loading" ? "召回中…" : "執行召回" }}
          </button>
        </div>
        <p v-if="queryTooLong" class="gm-recall__warning" role="alert">
          查詢文字超過 {{ RECALL_QUERY_LIMIT }} 字元，伺服器會拒絕此請求。
        </p>
      </form>

      <div v-if="recall.error" class="gm-recall__failed" role="alert">
        <GmError compact title="召回失敗" :message="recall.error.message" :code="recall.error.code" />
      </div>

      <div v-else-if="recallActive && recall.result" class="gm-recall__result" data-testid="gm-recall-result">
        <dl class="gm-ledger gm-ledger__row">
          <div class="gm-ledger__row">
            <dt>記憶世代</dt>
            <dd class="gm-mono">{{ recall.result.generation }}</dd>
          </div>
          <div class="gm-ledger__row">
            <dt>分詞版本</dt>
            <dd class="gm-mono">{{ recall.result.tokenizer_version }}</dd>
          </div>
          <div class="gm-ledger__row">
            <dt>排序版本</dt>
            <dd class="gm-mono">{{ recall.result.ranker_version }}</dd>
          </div>
          <div class="gm-ledger__row">
            <dt>故事線</dt>
            <dd class="gm-mono">
              {{ recall.result.thread_id || "—" }}
              <template v-if="recall.result.thread_revision">（修訂 {{ recall.result.thread_revision }}）</template>
            </dd>
          </div>
        </dl>
        <div v-for="group in RECALL_GROUPS" :key="group.key" class="gm-recall__group">
          <h4 class="gm-recall__group-title">
            {{ group.label }}
            <span class="gm-recall__group-count">{{ recall.result[group.key].length }} 筆</span>
          </h4>
          <p v-if="!recall.result[group.key].length" class="gm-recall__empty">沒有入選的記憶。</p>
          <ol v-else class="gm-recall__items">
            <li v-for="entry in recall.result[group.key]" :key="`${group.key}-${entry.id}`" class="gm-recall__item">
              <p class="gm-recall__meta">
                <span class="gm-mono">#{{ entry.id }}</span>
                <span class="gm-chip">{{ entry.tier }}</span>
                <span class="gm-chip">{{ entry.category }}</span>
                <span class="gm-mono">顯著度 {{ entry.salience }}</span>
                <span class="gm-mono">信心 {{ entry.confidence }}</span>
                <template v-if="entry.score">
                  <span class="gm-mono">BM25 {{ entry.score.lexical.toFixed(3) }}</span>
                  <span class="gm-mono">最終 {{ entry.score.final.toFixed(3) }}</span>
                </template>
              </p>
              <GmJsonTree :value="entry.content" :open-depth="2" @open-call="emit('open-call', $event)" />
            </li>
          </ol>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.gm-memory {
  display: grid;
  gap: var(--sp-6);
  min-width: 0;
}

.gm-memory__block {
  display: grid;
  gap: var(--sp-3);
  min-width: 0;
}

.gm-memory__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-3);
}

.gm-memory__refresh {
  margin-left: auto;
}

.gm-memory__title {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-3);
  font-family: var(--f-serif);
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--paper-100);
}

.gm-memory__hint {
  font-family: var(--f-sans);
  font-size: var(--text-xs);
  font-weight: 400;
  letter-spacing: 0.06em;
  color: var(--paper-500);
}

.gm-memory__sections {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 380px), 1fr));
  gap: var(--sp-4);
  margin: var(--sp-2) 0 var(--sp-4);
  padding: var(--sp-4);
  background: color-mix(in srgb, var(--ink-820) 60%, transparent);
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}

.gm-recall {
  display: grid;
  gap: var(--sp-3);
  padding: var(--sp-4);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
}

.gm-recall__field {
  display: grid;
  gap: var(--sp-1);
}

.gm-recall__label {
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  color: var(--paper-400);
}

.gm-recall__query,
.gm-recall__input {
  padding: var(--sp-2);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  color: var(--paper-100);
  background: var(--ink-950);
  border: var(--line);
  border-radius: var(--radius-sm);
  resize: vertical;
}

.gm-recall__query:focus-visible,
.gm-recall__input:focus-visible {
  box-shadow: var(--focus);
  outline: none;
}

.gm-recall__count {
  justify-self: end;
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-recall__count.is-over {
  color: var(--warn);
}

.gm-recall__controls {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: var(--sp-3) var(--sp-5);
}

.gm-recall__toggle {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--text-sm);
  color: var(--paper-200);
}

.gm-recall__submit {
  margin-left: auto;
}

.gm-recall__warning {
  font-size: var(--text-sm);
  color: var(--warn);
}

.gm-recall__failed {
  margin: 0;
}

.gm-recall__result {
  display: grid;
  gap: var(--sp-4);
  padding: var(--sp-4);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
}

.gm-recall__group {
  display: grid;
  gap: var(--sp-2);
}

.gm-recall__group-title {
  display: flex;
  align-items: baseline;
  gap: var(--sp-3);
  font-size: var(--text-sm);
  font-weight: 600;
  letter-spacing: 0.08em;
  color: var(--paper-300);
}

.gm-recall__group-count {
  font-weight: 400;
  letter-spacing: 0;
  color: var(--paper-500);
}

.gm-recall__empty {
  font-size: var(--text-sm);
  color: var(--paper-500);
}

.gm-recall__items {
  display: grid;
  gap: var(--sp-3);
  padding: 0;
  list-style: none;
}

.gm-recall__item {
  display: grid;
  gap: var(--sp-1);
  padding: var(--sp-3);
  background: var(--ink-950);
  border: var(--line);
  border-radius: var(--radius-sm);
}

.gm-recall__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2);
  font-size: var(--text-xs);
  color: var(--paper-400);
}
</style>
