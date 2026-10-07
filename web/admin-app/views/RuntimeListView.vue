<script setup>
// A runtime kind list (gm-portal-s3-runtime-state §4/§6): the filter bar, the
// cursor-paged summary table and a manual refresh. The filter set is the
// kind's own vocabulary, so a change restarts pagination instead of replaying
// a cursor against different filters (the server would refuse that anyway).
import { computed, inject, reactive, ref, watch } from "vue";
import GmEntityListTable from "../components/GmEntityListTable.vue";
import GmError from "../components/GmError.vue";
import GmFilterBar from "../components/GmFilterBar.vue";
import GmPager from "../components/GmPager.vue";
import { formatClock } from "../lib/format.js";
import { LIST_DEFAULT_LIMIT, RUNTIME_KIND_BY_KEY, kindLabel, listPath } from "../lib/runtime.js";

const props = defineProps({
  kind: { type: String, required: true },
  // The filters carried in the URL (owner survives a reload/history entry).
  query: { type: Object, default: () => ({}) },
});

const api = inject("gmApi");

const definition = computed(() => RUNTIME_KIND_BY_KEY[props.kind] ?? null);
const filters = ref({ ...props.query });
const state = reactive({
  status: "idle",
  items: [],
  nextCursor: null,
  page: 1,
  limit: LIST_DEFAULT_LIMIT,
  error: null,
  loadedAt: null,
});
const refreshing = ref(false);

const missingRequired = computed(
  () => (definition.value?.filters ?? []).some((field) => field.required && !filters.value[field.key]),
);

async function load({ cursor = null, append = false } = {}) {
  if (!definition.value || missingRequired.value) {
    state.status = "ready";
    state.items = [];
    state.nextCursor = null;
    return;
  }
  state.status = "loading";
  try {
    const data = await api.get(listPath(props.kind, { cursor, limit: state.limit, filters: filters.value }));
    state.items = append ? [...state.items, ...data.items] : data.items;
    state.nextCursor = data.next_cursor;
    state.page = append ? state.page + 1 : 1;
    state.status = "ready";
    state.error = null;
    state.loadedAt = Date.now() / 1000;
  } catch (error) {
    state.status = "error";
    state.error = error;
  }
}

async function refresh() {
  refreshing.value = true;
  try {
    await load();
  } finally {
    refreshing.value = false;
  }
}

function onFilters(next) {
  filters.value = next;
  load();
}

function onLimit(limit) {
  state.limit = limit;
  load();
}

watch(() => [props.kind, props.query], () => {
  filters.value = { ...props.query };
  state.items = [];
  state.nextCursor = null;
  load();
}, { immediate: true, deep: true });
</script>

<template>
  <div class="gm-list-view">
    <header class="gm-list-view__head">
      <div>
        <p class="gm-list-view__eyebrow">執行期狀態</p>
        <h2 class="gm-list-view__title">{{ kindLabel(kind) }}</h2>
        <p v-if="definition" class="gm-list-view__blurb">{{ definition.blurb }}</p>
      </div>
      <div class="gm-list-view__actions">
        <span class="gm-list-view__stamp">
          <template v-if="state.loadedAt !== null">
            最後載入 <time class="gm-mono">{{ formatClock(state.loadedAt) }}</time>
          </template>
          <template v-else>尚未載入</template>
        </span>
        <button
          type="button"
          class="ui-btn ui-btn--ghost ui-btn--sm"
          :aria-disabled="refreshing ? 'true' : null"
          @click="!refreshing && refresh()"
        >
          <span class="gm-list-view__refresh" :class="{ 'is-spinning': refreshing }" aria-hidden="true">↻</span>
          重新載入
        </button>
      </div>
    </header>

    <GmFilterBar
      v-if="definition && definition.filters.length"
      :fields="definition.filters"
      :model-value="filters"
      :busy="state.status === 'loading'"
      :caption="`${kindLabel(kind)}篩選`"
      @change="onFilters"
    />

    <p v-if="missingRequired" class="gm-list-view__hint">
      這個清單需要{{ definition.filters.filter((field) => field.required).map((field) => field.label).join("、") }}才能查詢。
    </p>

    <p v-else-if="state.status === 'loading' && state.items.length === 0" class="gm-skeleton" style="width: 60%"></p>

    <GmError
      v-else-if="state.error"
      title="無法載入清單"
      :message="state.error.message"
      :code="state.error.code"
    >
      <template #actions>
        <button type="button" class="ui-btn ui-btn--sm" @click="load()">重試</button>
      </template>
    </GmError>

    <template v-else>
      <GmEntityListTable
        :rows="state.items"
        :kind="kind"
        :caption="`${kindLabel(kind)}清單`"
        empty-title="沒有符合條件的項目"
        empty-message="調整篩選條件，或確認這個種類是否已經有資料。"
      />
      <GmPager
        :next-cursor="state.nextCursor"
        :limit="state.limit"
        :shown="state.items.length"
        :page="state.page"
        :busy="state.status === 'loading'"
        @more="load({ cursor: state.nextCursor, append: true })"
        @limit="onLimit"
        @first="load()"
      />
    </template>
  </div>
</template>

<style scoped>
.gm-list-view {
  display: grid;
  gap: var(--sp-4);
  min-width: 0;
}

.gm-list-view__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--sp-4);
}

.gm-list-view__eyebrow {
  font-size: var(--text-xs);
  letter-spacing: 0.14em;
  color: var(--gold-400);
}

.gm-list-view__title {
  font-family: var(--f-serif);
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--paper-50);
}

.gm-list-view__blurb {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-list-view__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-3);
}

.gm-list-view__stamp {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-list-view__refresh.is-spinning {
  display: inline-block;
  animation: gm-list-spin var(--motion-spin) linear infinite;
}

@keyframes gm-list-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .gm-list-view__refresh.is-spinning {
    animation: none;
  }
}

.gm-list-view__hint {
  padding: var(--sp-3) var(--sp-4);
  font-size: var(--text-sm);
  color: var(--paper-300);
  background: color-mix(in srgb, var(--warn) 6%, var(--ink-860));
  border-left: 3px dashed var(--warn);
  border-radius: var(--radius-sm);
}
</style>
